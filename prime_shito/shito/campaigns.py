"""Advertisement SMS campaigns.

Two rules govern everything here.

**Consent.** Ghana's Data Protection Act 2012 requires consent for marketing.
Order notifications are contractual and go to everyone; these do not. Every
audience query filters on `marketing_opt_in` in SQL rather than in Python, so
there is no code path where forgetting a check leaks a message to someone who
never agreed. Blocked numbers are excluded the same way.

**Cost.** A campaign is the one place in this app that can spend a lot of money
in one click. Nothing sends until the owner has seen the recipient count, the
segment count and the estimated total, and confirmed by typing SEND.

Note on throughput: Frappe's SMS gateway issues one HTTP request per recipient.
That is fine for the list sizes this business has and keeps us on the built-in
SMS Settings the owner already configured. Arkesel's bulk endpoint would be the
optimisation if lists grow into the thousands.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, now_datetime

from prime_shito.shito import gsm, notify
from prime_shito.shito import phone as phone_utils

# Appended to every marketing message. Roughly 22 characters, which is budgeted
# for in the segment estimate because the customer is charged for it too.
OPT_OUT_SUFFIX = " Txt STOP to opt out"

MAX_RECIPIENTS = 5000


def _settings():
	return frappe.get_cached_doc("Prime Shito Settings")


def build_message(campaign) -> str:
	"""The exact text that will be sent, opt-out footer included."""
	body = (campaign.message or "").strip()
	if not body:
		return ""
	if "STOP" in body.upper():
		return body
	return f"{body}{OPT_OUT_SUFFIX}"


def resolve_audience(campaign) -> list[dict]:
	"""Return [{phone, customer_name}] for the campaign's audience.

	Consent and blocking are enforced in the SQL itself. A caller cannot get an
	unfiltered list out of this module.
	"""
	audience = campaign.audience

	if audience == "Manual List":
		return _manual_list(campaign)

	conditions = ["c.marketing_opt_in = 1", "c.is_blocked = 0", "c.phone IS NOT NULL"]
	values: dict = {}
	joins = ""

	if audience == "Past Customers":
		conditions.append("c.total_orders > 0")

	elif audience == "By Delivery Zone":
		if not campaign.zone:
			frappe.throw(_("Choose a delivery zone."))
		joins = " INNER JOIN `tabShito Order` o ON o.shito_customer = c.name "
		conditions.append("o.delivery_zone = %(zone)s")
		values["zone"] = campaign.zone

	elif audience == "By Pack":
		if not campaign.pack:
			frappe.throw(_("Choose a pack."))
		joins = (
			" INNER JOIN `tabShito Order` o ON o.shito_customer = c.name "
			" INNER JOIN `tabShito Order Item` i ON i.parent = o.name "
		)
		conditions.append("i.pack = %(pack)s")
		values["pack"] = campaign.pack

	elif audience == "Inactive 60 Days":
		conditions.append("c.total_orders > 0")
		conditions.append(
			"(c.last_order_date IS NULL OR c.last_order_date < DATE_SUB(CURDATE(), INTERVAL 60 DAY))"
		)

	if cint(campaign.min_orders) > 0:
		conditions.append("c.total_orders >= %(min_orders)s")
		values["min_orders"] = cint(campaign.min_orders)

	if campaign.from_date:
		conditions.append("c.last_order_date >= %(from_date)s")
		values["from_date"] = campaign.from_date

	if campaign.to_date:
		conditions.append("c.last_order_date <= %(to_date)s")
		values["to_date"] = campaign.to_date

	rows = frappe.db.sql(
		f"""
		SELECT DISTINCT c.name AS phone, c.full_name AS customer_name
		FROM `tabShito Customer` c
		{joins}
		WHERE {" AND ".join(conditions)}
		ORDER BY c.name
		LIMIT {MAX_RECIPIENTS}
		""",
		values,
		as_dict=True,
	)

	return rows


def _manual_list(campaign) -> list[dict]:
	"""Hand-typed numbers, still filtered against consent.

	A manual list is not a way around opt-out: a number that has unsubscribed
	stays unsubscribed no matter how it reaches us.
	"""
	raw = (campaign.manual_numbers or "").splitlines()
	seen: dict[str, dict] = {}

	for line in raw:
		line = line.strip()
		if not line:
			continue
		normalized = phone_utils.normalize(line, throw=False)
		if not normalized:
			continue

		customer = frappe.db.get_value(
			"Shito Customer",
			normalized,
			["full_name", "marketing_opt_in", "is_blocked"],
			as_dict=True,
		)

		# Known customers must have opted in. Numbers we have never seen have
		# given no consent at all, so they are not marketed to either.
		if not customer or not cint(customer.marketing_opt_in) or cint(customer.is_blocked):
			continue

		seen[normalized] = {"phone": normalized, "customer_name": customer.full_name}

	return list(seen.values())[:MAX_RECIPIENTS]


@frappe.whitelist()
def preview(campaign_name: str) -> dict:
	"""Resolve the audience and price it, without sending anything.

	Populates the recipient table so the owner can see exactly who is in scope
	before committing money.
	"""
	frappe.only_for(("Shito Manager", "System Manager"))

	campaign = frappe.get_doc("Shito SMS Campaign", campaign_name)
	campaign.check_permission("write")

	message = build_message(campaign)
	if not message:
		frappe.throw(_("Write the message first."))

	encoding, segments = gsm.count_segments(message)
	recipients = resolve_audience(campaign)

	settings = _settings()
	cost = flt(len(recipients)) * segments * flt(settings.sms_cost_per_segment)

	campaign.set("recipients", [])
	for row in recipients:
		campaign.append(
			"recipients",
			{"phone": row["phone"], "customer_name": row.get("customer_name"), "status": "Pending"},
		)

	campaign.recipient_count = len(recipients)
	campaign.encoding = encoding
	campaign.segments = segments
	campaign.estimated_cost = cost
	campaign.save(ignore_permissions=True)

	return {
		"count": len(recipients),
		"encoding": encoding,
		"segments": segments,
		"estimated_cost": cost,
		"message": message,
		"characters": len(message),
		"sample": [phone_utils.mask(r["phone"]) for r in recipients[:5]],
		"warning": (
			_("Contains characters that force expensive UCS-2 encoding: {0}").format(
				" ".join(gsm.non_gsm7_characters(message))
			)
			if encoding == "UCS-2"
			else None
		),
	}


@frappe.whitelist()
def send(campaign_name: str, confirm: str = "") -> dict:
	"""Queue the campaign. Requires a typed confirmation."""
	frappe.only_for(("Shito Manager", "System Manager"))

	if (confirm or "").strip().upper() != "SEND":
		frappe.throw(_("Type SEND to confirm."))

	campaign = frappe.get_doc("Shito SMS Campaign", campaign_name)
	campaign.check_permission("write")

	if campaign.status in ("Sending", "Sent"):
		frappe.throw(_("This campaign has already been sent."))

	if not cint(_settings().sms_enabled):
		frappe.throw(_("SMS is turned off in Prime Shito Settings."))

	if not campaign.recipient_count:
		frappe.throw(_("Preview the recipients first."))

	campaign.db_set("status", "Sending", update_modified=False)

	frappe.enqueue(
		"prime_shito.shito.campaigns.run",
		queue="long",
		timeout=3600,
		enqueue_after_commit=True,
		deduplicate=True,
		job_id=f"shitocampaign::{campaign.name}",
		campaign_name=campaign.name,
	)

	return {"ok": True, "queued": campaign.recipient_count}


def run(campaign_name: str) -> None:
	"""Send the campaign. Runs in the background; never raises into a request."""
	campaign = frappe.get_doc("Shito SMS Campaign", campaign_name)
	settings = _settings()
	message = build_message(campaign)

	sent = failed = suppressed = 0

	for row in campaign.recipients:
		if row.status == "Sent":
			continue  # resumable: a retried job does not re-text anyone

		# Re-checked at send time, not just at preview. Someone may have opted
		# out between the two, and that answer must win.
		customer = frappe.db.get_value(
			"Shito Customer", row.phone, ["marketing_opt_in", "is_blocked"], as_dict=True
		)
		if not customer or not cint(customer.marketing_opt_in) or cint(customer.is_blocked):
			row.db_set("status", "Suppressed", update_modified=False)
			suppressed += 1
			continue

		ok = notify.send_sms(
			row.phone,
			message,
			template_key="campaign",
			reference_doctype="Shito SMS Campaign",
			reference_name=campaign.name,
		)

		if ok:
			row.db_set("status", "Sent", update_modified=False)
			sent += 1
		else:
			row.db_set("status", "Failed", update_modified=False)
			failed += 1

		# Commit as we go so a crash halfway does not lose the record of what
		# was already sent -- and therefore does not resend it.
		frappe.db.commit()

	status = "Sent" if not failed else ("Failed" if not sent else "Partially Sent")

	frappe.db.set_value(
		"Shito SMS Campaign",
		campaign.name,
		{
			"status": status,
			"sent_count": sent,
			"failed_count": failed,
			"suppressed_count": suppressed,
			"sent_at": now_datetime(),
			"sender_id": settings.arkesel_sender_id,
		},
		update_modified=False,
	)
	frappe.db.commit()


# --------------------------------------------------------------------------
# Opt-out
# --------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="phone", limit=5, seconds=3600)
@rate_limit(limit=30, seconds=3600)
def unsubscribe(phone: str, token: str | None = None) -> dict:
	"""Stop marketing to a number.

	Guest-accessible on purpose: an opt-out that requires signing in is not an
	opt-out. It only ever clears a flag, never reveals whether the number is
	known, and the response is identical either way so it cannot be used to
	test whether someone has ordered.
	"""
	normalized = phone_utils.normalize(phone, throw=False)

	if normalized and frappe.db.exists("Shito Customer", normalized):
		doc = frappe.get_doc("Shito Customer", normalized)
		if cint(doc.marketing_opt_in):
			doc.marketing_opt_in = 0
			doc.opt_out_source = "STOP SMS" if token else "Web"
			doc.save(ignore_permissions=True)

	return {"ok": True, "message": _("You will not receive marketing messages from us again.")}
