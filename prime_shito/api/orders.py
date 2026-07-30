"""Public order endpoints.

`place_order` is the only way an anonymous visitor creates data, and
`track_order` is the only way one reads it back. Both are written defensively:

  * No amount is ever read from the request. See shito/pricing.py.
  * The tracking response is an explicit redacted projection, never the doc.
  * Wrong-code and wrong-phone answers are identical in both text and timing,
    so the endpoint cannot be used to discover which codes exist.
"""

import time

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, now_datetime

from prime_shito.shito import notify, otp, pricing, state
from prime_shito.shito import phone as phone_utils

# Field length caps, applied before anything is written.
MAX_NAME = 140
MAX_ADDRESS = 500
MAX_NOTES = 500
MAX_LANDMARK = 140

# Wrong lookups are padded to this long so a valid-but-wrong-phone answer cannot
# be distinguished from a nonexistent code by response time.
LOOKUP_FLOOR_SECONDS = 0.15


def _settings():
	return frappe.get_cached_doc("Prime Shito Settings")


def _client_ip() -> str | None:
	return getattr(frappe.local, "request_ip", None)


def _user_agent() -> str | None:
	"""Read the User-Agent, tolerating no HTTP request at all.

	Orders are also created from the console and from tests, where
	`frappe.request` is unbound and touching it raises.
	"""
	try:
		if not getattr(frappe.local, "request", None):
			return None
		return (frappe.get_request_header("User-Agent") or "")[:500] or None
	except RuntimeError:
		return None


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="phone", limit=3, seconds=900)
@rate_limit(limit=20, seconds=3600)
def request_otp(phone: str) -> dict:
	"""Send a verification code to a Ghanaian mobile number."""
	return otp.request_otp(phone, ip_address=_client_ip())


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="phone", limit=10, seconds=900)
def verify_otp(phone: str, otp_code: str) -> dict:
	"""Exchange a correct code for a single-use token that authorises one order."""
	return otp.verify_otp(phone, otp_code, ip_address=_client_ip())


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="phone", limit=10, seconds=3600)
def place_order(
	customer_name: str,
	phone: str,
	verification_token: str,
	items: str,
	payment_method: str = "Pay on Delivery",
	fulfilment_type: str = "Delivery",
	delivery_zone: str | None = None,
	delivery_address: str | None = None,
	landmark: str | None = None,
	delivery_notes: str | None = None,
	preferred_delivery_date: str | None = None,
	alt_phone: str | None = None,
	email: str | None = None,
	marketing_consent: int = 0,
	hp: str = "",
) -> dict:
	settings = _settings()

	# Honeypot. A real browser leaves this empty; scripted spam fills every
	# field it finds. Return a plausible success so the bot stops retrying.
	if (hp or "").strip():
		return {"ok": True, "tracking_code": "PS-0000-0000", "order_id": None}

	if not cint(settings.is_store_open):
		frappe.throw(
			settings.store_closed_message or _("We are not taking orders right now."),
		)

	normalized_phone = phone_utils.normalize(phone)

	if payment_method not in ("Pay on Delivery", "Pay Online"):
		frappe.throw(_("Choose a valid payment method."))

	if payment_method == "Pay on Delivery" and not cint(settings.allow_pay_on_delivery):
		frappe.throw(_("Pay on delivery is not available right now."))

	if payment_method == "Pay Online" and not cint(settings.allow_online_payment):
		frappe.throw(_("Online payment is not available right now."))

	if fulfilment_type not in ("Delivery", "Pickup"):
		fulfilment_type = "Delivery"

	if frappe.db.get_value("Shito Customer", normalized_phone, "is_blocked"):
		frappe.throw(_("We cannot accept an order from this number. Please contact us."))

	# Burn the verification token. Single use, bound to this phone.
	otp.consume_token(verification_token, normalized_phone)

	quote = pricing.compute(
		items,
		delivery_zone=delivery_zone,
		fulfilment_type=fulfilment_type,
	)

	if quote.blocking_errors:
		frappe.throw("<br>".join(quote.blocking_errors))

	if not quote.lines:
		frappe.throw(_("Your basket is empty."))

	pod_cap = float(settings.pod_max_order_amount or 0)
	if payment_method == "Pay on Delivery" and pod_cap and quote.grand_total > pod_cap:
		frappe.throw(_("Orders above GHS {0} must be paid online.").format(pricing.money(pod_cap)))

	customer = _upsert_customer(
		phone=normalized_phone,
		full_name=customer_name,
		email=email,
		alt_phone=alt_phone,
		zone=delivery_zone,
		address=delivery_address,
		marketing_consent=cint(marketing_consent),
	)

	order = frappe.get_doc(
		{
			"doctype": "Shito Order",
			"customer_name": (customer_name or "").strip()[:MAX_NAME],
			"phone": normalized_phone,
			"alt_phone": phone_utils.normalize(alt_phone, throw=False) if alt_phone else None,
			"email": (email or "").strip()[:140] or None,
			"shito_customer": customer,
			"phone_verified": 1,
			"fulfilment_type": fulfilment_type,
			"delivery_zone": delivery_zone if fulfilment_type == "Delivery" else None,
			"delivery_address": (delivery_address or "").strip()[:MAX_ADDRESS],
			"landmark": (landmark or "").strip()[:MAX_LANDMARK] or None,
			"delivery_notes": (delivery_notes or "").strip()[:MAX_NOTES] or None,
			"preferred_delivery_date": preferred_delivery_date or None,
			"payment_method": payment_method,
			"marketing_consent": cint(marketing_consent),
			"source": "Website",
			"ip_address": _client_ip(),
			"user_agent": _user_agent(),
			# Rates are deliberately omitted: validate() recomputes every amount.
			"items": [{"pack": line.pack, "qty": line.qty} for line in quote.lines],
		}
	).insert(ignore_permissions=True)

	notify.notify_state_change(order, order.workflow_state)

	return {
		"ok": True,
		"order_id": order.name,
		"tracking_code": order.tracking_code,
		"status": order.workflow_state,
		"payment_status": order.payment_status,
		"payment_method": order.payment_method,
		"grand_total": order.grand_total,
		"currency": order.currency,
		"phone_last4": phone_utils.last4(normalized_phone),
	}


def _upsert_customer(
	*,
	phone: str,
	full_name: str,
	email: str | None,
	alt_phone: str | None,
	zone: str | None,
	address: str | None,
	marketing_consent: int,
) -> str:
	"""Find or create the customer record. The phone number is the primary key,
	so duplicates are impossible by construction."""
	name = (full_name or "").strip()[:MAX_NAME]

	if frappe.db.exists("Shito Customer", phone):
		doc = frappe.get_doc("Shito Customer", phone)
		doc.full_name = name or doc.full_name
		doc.email = (email or "").strip()[:140] or doc.email
		doc.default_zone = zone or doc.default_zone
		doc.default_address = (address or "").strip()[:MAX_ADDRESS] or doc.default_address
		# Consent is only ever turned on here. Withdrawal happens through
		# unsubscribe or admin action, and must not be silently reversed by a
		# later order with the box unticked.
		if marketing_consent:
			doc.marketing_opt_in = 1
		doc.save(ignore_permissions=True)
		return doc.name

	return (
		frappe.get_doc(
			{
				"doctype": "Shito Customer",
				"phone": phone,
				"full_name": name,
				"email": (email or "").strip()[:140] or None,
				"alt_phone": phone_utils.normalize(alt_phone, throw=False) if alt_phone else None,
				"default_zone": zone,
				"default_address": (address or "").strip()[:MAX_ADDRESS] or None,
				"marketing_opt_in": cint(marketing_consent),
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="code", limit=10, seconds=600)
@rate_limit(limit=30, seconds=600)
def track_order(code: str, phone_last4: str) -> dict:
	"""Look up an order by tracking code plus the last four digits of the phone.

	Both factors are required. The code alone is unguessable, but a forwarded
	SMS screenshot would leak it, so the phone digits keep a stranger holding
	the code from seeing a delivery address.
	"""
	started = time.monotonic()

	code = (code or "").strip().upper()
	digits = "".join(ch for ch in (phone_last4 or "") if ch.isdigit())

	def _reject():
		# Identical message and duration whether the code is unknown or the
		# digits are wrong, so neither can be enumerated.
		elapsed = time.monotonic() - started
		if elapsed < LOOKUP_FLOOR_SECONDS:
			time.sleep(LOOKUP_FLOOR_SECONDS - elapsed)
		frappe.throw(_("We could not find that order. Check the code and the last 4 digits of your phone."))

	if not code or len(digits) != 4:
		_reject()

	name = frappe.db.get_value("Shito Order", {"tracking_code": code}, "name")
	if not name:
		_reject()

	order = frappe.get_doc("Shito Order", name)

	import hmac

	if not hmac.compare_digest(phone_utils.last4(order.phone), digits):
		_reject()

	return order.as_tracking_dict()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="phone", limit=3, seconds=86400)
def resend_tracking_sms(phone: str) -> dict:
	"""Text a customer the tracking codes of their open orders.

	Always reports success, whether or not the number has any orders: a
	differing response would turn this into a way to test whether a phone
	number has ever ordered.
	"""
	normalized = phone_utils.normalize(phone)

	orders = frappe.get_all(
		"Shito Order",
		filters={"phone": normalized, "workflow_state": ("in", state.OPEN_STATES)},
		fields=["name", "tracking_code"],
		order_by="creation desc",
		limit=3,
	)

	for row in orders:
		notify.enqueue_order_sms(frappe.get_doc("Shito Order", row.name), "tpl_status_update")

	return {"ok": True}
