"""Transactional SMS.

Sends through Frappe's built-in SMS Settings gateway (Core > SMS Settings),
pointed at Arkesel. No custom gateway hook is needed: configuring SMS Settings
is enough, and the Notification doctype routes through the same path.

Note for later: the built-in sender issues one HTTP request per recipient. That
is right for order notifications, which go to one person, but advertisement
campaigns will want Arkesel's bulk endpoint instead.

Every message is rendered from a Jinja template on Prime Shito Settings, so the
owner can reword any of them without a deploy, and every send is logged to
Shito SMS Message with its segment count -- see shito/gsm.py for why segments
are the thing that actually drives the bill.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, get_url, now_datetime

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


def log_message(
	*,
	to_phone: str,
	message: str,
	status: str,
	template_key: str = "",
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	error: str | None = None,
) -> str:
	"""Record one outbound SMS. Returns the log name."""
	settings = _settings()
	encoding, segments = gsm.count_segments(message)

	doc = frappe.get_doc(
		{
			"doctype": "Shito SMS Message",
			"to_phone": to_phone,
			"message": message,
			"encoding": encoding,
			"segments": segments,
			"cost": flt(segments) * flt(settings.sms_cost_per_segment),
			"status": status,
			"template_key": template_key,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"error": error,
			"sent_at": now_datetime() if status in ("Sent", "Sandbox") else None,
		}
	).insert(ignore_permissions=True)

	return doc.name


def send_sms(
	to_phone: str,
	message: str,
	*,
	template_key: str = "",
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> bool:
	"""Send one SMS and log it. Returns True if handed to the gateway.

	Never raises: a failed notification must not roll back or block the order
	it is describing.
	"""
	settings = _settings()

	if not message:
		return False

	normalized = phone_utils.normalize(to_phone, throw=False)
	if not normalized:
		return False

	log = {
		"to_phone": normalized,
		"message": message,
		"template_key": template_key,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
	}

	if not cint(settings.sms_enabled):
		return False

	if is_suppressed(normalized):
		log_message(status="Suppressed", **log)
		return False

	if cint(settings.sms_sandbox):
		# Logged with a full segment count so the owner can see what a real
		# run would have cost, but nothing is sent and nothing is billed.
		log_message(status="Sandbox", **log)
		return True

	if _over_daily_cap(settings):
		log_message(status="Failed", error="Daily SMS cap reached", **log)
		frappe.log_error(title="Prime Shito: daily SMS cap reached")
		return False

	try:
		from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms

		frappe_send_sms(
			receiver_list=[phone_utils.to_local_international(normalized)],
			msg=message,
			sender_name=settings.arkesel_sender_id or "",
			success_msg=False,
		)
		log_message(status="Sent", **log)
		return True
	except Exception as exc:
		log_message(status="Failed", error=str(exc)[:500], **log)
		frappe.log_error(
			title="Prime Shito: SMS send failed",
			message=f"to={phone_utils.mask(normalized)} key={template_key}",
		)
		return False


def _over_daily_cap(settings) -> bool:
	cap = cint(settings.sms_daily_cap)
	if cap <= 0:
		return False

	sent_today = frappe.db.count(
		"Shito SMS Message",
		{"status": ("in", ["Sent", "Delivered"]), "creation": (">=", frappe.utils.today())},
	)
	return sent_today >= cap


def is_suppressed(phone: str) -> bool:
	"""Numbers that must never be texted again."""
	return bool(frappe.db.get_value("Shito Customer", phone, "is_blocked"))


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
	"""Values available to every order SMS template.

	Money is formatted without a currency symbol -- templates write "GHS {{ total }}"
	-- because the cedi sign is outside GSM-7 and would double the cost of the
	message carrying it.
	"""
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


def already_sent(order_name: str, template_key: str) -> bool:
	return bool(
		frappe.db.exists(
			"Shito SMS Message",
			{
				"reference_doctype": "Shito Order",
				"reference_name": order_name,
				"template_key": template_key,
				"status": ("in", ["Queued", "Sent", "Delivered", "Sandbox"]),
			},
		)
	)


def notify_order(order_name: str, template_key: str) -> bool:
	"""Send one order notification, at most once per (order, template).

	Idempotent so a retried background job, a double save, or an order that
	moves back into a state it already visited cannot text the customer twice
	about the same thing.
	"""
	if already_sent(order_name, template_key):
		return False

	order = frappe.get_doc("Shito Order", order_name)
	settings = _settings()

	template = settings.get(template_key) or settings.get("tpl_status_update")
	if not template:
		return False

	message = render(template, order_context(order))
	if not message:
		return False

	return send_sms(
		order.phone,
		message,
		template_key=template_key,
		reference_doctype="Shito Order",
		reference_name=order.name,
	)


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
	enqueue_order_sms(order, TEMPLATE_FOR_STATE.get(new_state, "tpl_status_update"))


@frappe.whitelist()
def send_test_sms(phone: str) -> dict:
	"""Send one real message to the owner, to prove the gateway is configured.

	The single most common SMS failure is an unapproved Arkesel sender ID,
	which is often rejected silently. Sending a test to your own phone is the
	only reliable way to find out before customers are affected.
	"""
	frappe.only_for(("Shito Manager", "System Manager"))

	settings = _settings()

	if not cint(settings.sms_enabled):
		return {"sent": False, "detail": _("Enable SMS first.")}

	message = f"Prime Shito test message. Sender ID: {settings.arkesel_sender_id or 'default'}."
	sent = send_sms(phone, message, template_key="test")

	if cint(settings.sms_sandbox):
		return {
			"sent": False,
			"detail": _(
				"Sandbox mode is on, so this was logged but not delivered. "
				"Turn off Sandbox Mode to send for real."
			),
		}

	if not sent:
		return {
			"sent": False,
			"detail": _("Sending failed. Check the Shito SMS Message log and the Error Log."),
		}

	return {
		"sent": True,
		"detail": _(
			"Handed to the gateway. If nothing arrives, the usual cause is a sender ID "
			"that Arkesel has not approved."
		),
	}


@frappe.whitelist()
def preview_templates() -> list[dict]:
	"""Show the owner what each template will send, and what it will cost.

	Rendered against the most recent real order so the preview reflects actual
	names and amounts rather than placeholder text.
	"""
	frappe.only_for(("Shito Manager", "System Manager"))

	settings = _settings()
	recent = frappe.get_all("Shito Order", fields=["name"], order_by="creation desc", limit=1)

	if recent:
		context = order_context(frappe.get_doc("Shito Order", recent[0].name))
	else:
		context = {
			"code": "PS-7K2M-9XQD",
			"name": "Ama",
			"n": 2,
			"total": "175.00",
			"paid": "0.00",
			"due": "175.00",
			"status": "Approved",
			"payment_status": "Unpaid",
			"pay_state": "pay on delivery",
			"zone": "Accra Central",
			"reason": "",
			"support": settings.support_phone or "",
			"site": get_url(),
			"url": get_url("/track/PS-7K2M-9XQD"),
			"pay_url": get_url("/track/PS-7K2M-9XQD"),
			"mins": 60,
		}

	context["otp"] = "123456"

	rows = []
	for df in settings.meta.fields:
		if not df.fieldname.startswith("tpl_"):
			continue

		body = render(settings.get(df.fieldname), context)
		encoding, segments = gsm.count_segments(body)

		rows.append(
			{
				"template": df.fieldname,
				"label": _(df.label),
				"message": body,
				"characters": len(body),
				"encoding": encoding,
				"segments": segments,
				"cost": flt(segments) * flt(settings.sms_cost_per_segment),
				"warning": (
					_("Contains characters that force expensive UCS-2 encoding: {0}").format(
						" ".join(gsm.non_gsm7_characters(body))
					)
					if encoding == "UCS-2"
					else None
				),
			}
		)

	return rows
