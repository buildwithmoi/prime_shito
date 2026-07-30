"""Transactional SMS.

Sends through Frappe's built-in SMS Settings gateway (Core > SMS Settings),
pointed at Arkesel. No custom gateway hook: configuring SMS Settings is enough.

Note for later: the built-in sender issues one HTTP request per recipient. That
is right for order notifications, which go to one person, but advertisement
campaigns will want Arkesel's bulk endpoint instead.

Every message is rendered from a Jinja template on Prime Shito Settings, so the
owner can reword any of them without a deploy. Templates are validated as GSM-7
on save -- see shito/gsm.py for why that matters to the bill.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_url

from prime_shito.shito import gsm
from prime_shito.shito import phone as phone_utils
from prime_shito.shito.pricing import money


def _settings():
	return frappe.get_cached_doc("Prime Shito Settings")


def render(template: str, context: dict) -> str:
	"""Render a template, falling back to the raw string if it will not compile.

	An owner mid-edit must never be able to break order placement.
	"""
	if not template:
		return ""
	try:
		return frappe.render_template(template, context).strip()
	except Exception:
		frappe.log_error(title="Prime Shito: SMS template failed to render")
		return template


def send_sms(to_phone: str, message: str, *, template_key: str = "", reference: str | None = None) -> bool:
	"""Send one SMS. Returns True if handed to the gateway.

	Never raises: a failed notification must not roll back or block the order
	it is describing.
	"""
	settings = _settings()

	if not cint(settings.sms_enabled):
		return False

	if not message:
		return False

	to_phone = phone_utils.normalize(to_phone, throw=False)
	if not to_phone:
		return False

	if is_suppressed(to_phone):
		return False

	encoding, segments = gsm.count_segments(message)

	if cint(settings.sms_sandbox):
		# Log what would have been sent, and bill nothing.
		frappe.logger("prime_shito").info(
			f"[sms-sandbox] to={phone_utils.mask(to_phone)} "
			f"key={template_key} enc={encoding} segments={segments} msg={message!r}"
		)
		return True

	try:
		from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms

		frappe_send_sms(
			receiver_list=[phone_utils.to_local_international(to_phone)],
			msg=message,
			sender_name=settings.arkesel_sender_id or "",
			success_msg=False,
		)
		return True
	except Exception:
		frappe.log_error(
			title="Prime Shito: SMS send failed",
			message=f"to={phone_utils.mask(to_phone)} key={template_key} reference={reference}",
		)
		return False


def is_suppressed(phone: str) -> bool:
	"""Numbers that must never be texted again."""
	if frappe.db.exists("Shito Customer", {"name": phone, "is_blocked": 1}):
		return True
	return False


# --------------------------------------------------------------------------
# Order notifications
# --------------------------------------------------------------------------

TEMPLATE_FOR_STATE = {
	"Awaiting Approval": "tpl_order_received",
	"Approved": "tpl_order_approved",
	"Out for Delivery": "tpl_out_for_delivery",
	"Completed": "tpl_order_completed",
	"Cancelled": "tpl_order_cancelled",
	"Expired": "tpl_order_expired",
	"Pending Payment": "tpl_payment_pending",
}


def order_context(order) -> dict:
	settings = _settings()
	return {
		"code": order.tracking_code,
		"name": (order.customer_name or "").split(" ")[0],
		"n": len(order.items or []),
		"total": money(order.grand_total),
		"paid": money(order.amount_paid),
		"due": money(order.amount_due) if order.amount_due else "",
		"status": order.workflow_state,
		"payment_status": order.payment_status,
		"pay_state": "paid" if order.payment_status == "Paid" else "pay on delivery",
		"zone": order.delivery_zone or "",
		"reason": order.cancellation_reason or "",
		"support": settings.support_phone or "",
		"site": get_url().replace("https://", "").replace("http://", ""),
		"url": get_url(f"/track/{order.tracking_code}"),
		"pay_url": get_url(f"/track/{order.tracking_code}"),
		"mins": cint(settings.unpaid_order_expiry_minutes) or 60,
	}


def notify_order(order_name: str, template_key: str) -> bool:
	"""Send one order notification, at most once per (order, template).

	Idempotent so a retried background job or a double save cannot text the
	customer twice about the same thing.
	"""
	order = frappe.get_doc("Shito Order", order_name)
	settings = _settings()

	template = settings.get(template_key) or settings.get("tpl_status_update")
	if not template:
		return False

	message = render(template, order_context(order))
	if not message:
		return False

	sent = send_sms(
		order.phone,
		message,
		template_key=template_key,
		reference=order.name,
	)

	if sent:
		order.add_comment("Info", _("SMS sent: {0}").format(template_key))

	return sent


def enqueue_order_sms(order, template_key: str) -> None:
	"""Queue a notification to fire only once the order actually commits.

	`enqueue_after_commit=True` is essential: without it a rolled-back order
	still texts the customer.
	"""
	frappe.enqueue(
		"prime_shito.shito.notify.notify_order",
		queue="short",
		enqueue_after_commit=True,
		deduplicate=True,
		job_id=f"shitosms::{order.name}::{template_key}",
		order_name=order.name,
		template_key=template_key,
	)


def notify_state_change(order, new_state: str) -> None:
	template_key = TEMPLATE_FOR_STATE.get(new_state, "tpl_status_update")
	enqueue_order_sms(order, template_key)
