import secrets

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from prime_shito.shito import pricing, state

# Crockford-style alphabet with the ambiguous characters removed, so a code read
# aloud over the phone or copied off an SMS cannot be mistyped.
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 8


def new_tracking_code() -> str:
	"""Generate an unguessable customer-facing order code.

	Uses `secrets`, not `frappe.model.naming.make_autoname("hash")`: the latter
	derives its first characters from the timestamp, so codes created close
	together share a prefix. Order lookup is public, so the code has to carry
	real entropy -- 30**8 is about 6.6e11.
	"""
	body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
	return f"PS-{body[:4]}-{body[4:]}"


class ShitoOrder(Document):
	def before_insert(self):
		self.assign_tracking_code()

		# Every order starts here. Frappe refuses on insert to set any workflow
		# state other than the first one defined, and that check ignores roles,
		# so this cannot vary by payment method.
		#
		# That is not a compromise: payment progress is tracked separately in
		# `payment_status`, which describes it more precisely anyway. An unpaid
		# online order is (Awaiting Approval, Pending), not a third thing.
		self.workflow_state = state.AWAITING_APPROVAL

		if not self.confirmed_at:
			self.confirmed_at = now_datetime()

	def validate(self):
		self.validate_items()
		self.validate_fulfilment()

		# Unconditional, on every save including staff edits in Desk. Marking a
		# field read_only in the DocType JSON does not stop an API caller from
		# setting it; only recomputing does.
		pricing.apply_to_order(self)

		self.sync_payment_status()

	def on_update(self):
		self.update_customer_rollup()

	def assign_tracking_code(self):
		if self.tracking_code:
			return

		# Collisions are vanishingly unlikely, but a duplicate would surface as
		# an opaque unique-constraint error at insert, so retry a few times.
		for _attempt in range(5):
			code = new_tracking_code()
			if not frappe.db.exists("Shito Order", {"tracking_code": code}):
				self.tracking_code = code
				return

		frappe.throw(_("Could not allocate a tracking code. Please try again."))

	def validate_items(self):
		if not self.items:
			frappe.throw(_("An order needs at least one pack."))

		for row in self.items:
			if not row.pack:
				frappe.throw(_("Every line needs a pack."))
			if int(row.qty or 0) <= 0:
				frappe.throw(_("Quantity must be at least 1 for {0}.").format(row.pack))

	def validate_fulfilment(self):
		if self.fulfilment_type == "Delivery":
			if not self.delivery_zone:
				frappe.throw(_("Please choose a delivery area."))
			if not self.delivery_address:
				frappe.throw(_("Please enter a delivery address."))
		else:
			# Pickup orders must not carry a stale zone, or the fee would reappear.
			self.delivery_zone = None

	def sync_payment_status(self):
		"""Keep payment_status and amount_due consistent with amount_paid."""
		paid = flt(self.amount_paid)
		total = flt(self.grand_total)

		self.amount_due = flt(total - paid, pricing.PRECISION)

		if self.payment_status in ("Refunded", "Failed"):
			return

		if paid <= 0:
			# "Pending" means a payment was started but not confirmed; do not
			# overwrite it just because nothing has landed yet.
			if self.payment_status != "Pending":
				self.payment_status = "Unpaid"
		elif paid < total:
			self.payment_status = "Partially Paid"
		else:
			self.payment_status = "Paid"
			if not self.paid_at:
				self.paid_at = now_datetime()

	def update_customer_rollup(self):
		"""Refresh the customer's order history counters.

		Written with db_set rather than a save to avoid recursing through
		validation on a document nobody is editing.
		"""
		if not self.shito_customer:
			return

		rows = frappe.get_all(
			"Shito Order",
			filters={
				"shito_customer": self.shito_customer,
				"workflow_state": ("not in", state.DEAD_STATES),
			},
			fields=["name", "grand_total", "creation"],
			order_by="creation desc",
		)

		frappe.db.set_value(
			"Shito Customer",
			self.shito_customer,
			{
				"total_orders": len(rows),
				"total_spent": sum(flt(r.grand_total) for r in rows),
				"last_order_date": rows[0].creation.date() if rows else None,
				"last_order": rows[0].name if rows else None,
			},
			update_modified=False,
		)

	# ------------------------------------------------------------------
	# Presentation
	# ------------------------------------------------------------------

	def as_tracking_dict(self) -> dict:
		"""Redacted projection for the public order-tracking page.

		Anyone holding a tracking code plus the last four phone digits sees
		this, so it deliberately withholds the full phone number and address.
		"""
		from prime_shito.shito import phone as phone_utils

		first_name = (self.customer_name or "").strip().split(" ")[0]

		address_preview = None
		if self.delivery_address:
			flat = " ".join(self.delivery_address.split())
			address_preview = flat[:18] + "…" if len(flat) > 18 else flat

		return {
			"tracking_code": self.tracking_code,
			"status": self.workflow_state,
			"status_note": STATUS_NOTES.get(self.workflow_state, ""),
			"payment_status": self.payment_status,
			"payment_method": self.payment_method,
			"placed_on": self.creation,
			"currency": self.currency or pricing.CURRENCY,
			"items_total": flt(self.items_total),
			"delivery_fee": flt(self.delivery_fee),
			"grand_total": flt(self.grand_total),
			"amount_paid": flt(self.amount_paid),
			"amount_due": flt(self.amount_due),
			"fulfilment_type": self.fulfilment_type,
			"delivery_zone": self.delivery_zone,
			"preferred_delivery_date": self.preferred_delivery_date,
			"customer_first_name": first_name,
			"masked_phone": phone_utils.mask(self.phone),
			"address_preview": address_preview,
			"items": [
				{
					"pack_name": row.pack_name,
					"qty": row.qty,
					"rate": flt(row.rate),
					"amount": flt(row.amount),
					"image": row.image,
				}
				for row in self.items
			],
			"timeline": self.build_timeline(),
			"is_open": self.workflow_state in state.OPEN_STATES,
		}

	def build_timeline(self) -> list[dict]:
		steps = [
			("Order placed", self.confirmed_at or self.creation),
			("Approved", self.approved_at),
			("Out for delivery", self.dispatched_at),
			("Delivered", self.delivered_at),
		]

		if self.workflow_state == state.CANCELLED:
			steps.append(("Cancelled", self.cancelled_at))
		elif self.workflow_state == state.EXPIRED:
			steps.append(("Expired unpaid", self.modified))

		return [{"label": label, "at": at, "done": bool(at)} for label, at in steps]


STATUS_NOTES = {
	state.PENDING_PAYMENT: "Waiting for your payment.",
	state.AWAITING_APPROVAL: "We have your order and will confirm it shortly.",
	state.APPROVED: "Confirmed. We are making your shito.",
	state.OUT_FOR_DELIVERY: "On the way to you today.",
	state.COMPLETED: "Delivered. Enjoy!",
	state.CANCELLED: "This order was cancelled.",
	state.EXPIRED: "This order expired before payment.",
}
