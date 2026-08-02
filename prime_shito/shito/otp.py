"""Phone verification.

Every order is placed by an anonymous visitor, so the phone number is the only
identity we have -- and the entire notification chain depends on it being real
and reachable. This module verifies it before an order can be placed.

It is also the single most abusable endpoint in the app: each request spends
real money on an SMS. The defences are layered deliberately, because each one
alone is defeatable:

  * per-phone rate limit  -- stops one number being bombed
  * per-IP rate limit     -- stops one attacker cycling numbers
  * per-phone daily cap   -- stops a slow drip against one number
  * GLOBAL daily budget   -- stops a distributed attack, which defeats both of
                             the per-key limits above
"""

import hashlib
import hmac
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from prime_shito.shito import phone as phone_utils

GLOBAL_BUDGET_CACHE_KEY = "prime_shito_otp_budget"
TOKEN_TTL_MINUTES = 15


def _settings():
	return frappe.get_cached_doc("Prime Shito Settings")


def _hash(salt: str, otp: str) -> str:
	return hashlib.sha256(f"{salt}{otp}".encode()).hexdigest()


def _today_key() -> str:
	return f"{GLOBAL_BUDGET_CACHE_KEY}:{frappe.utils.nowdate()}"


def _check_global_budget(settings) -> None:
	"""Hard stop across all phones and all IPs.

	Without this, an attacker with a botnet defeats both the per-phone and
	per-IP limits simply by spreading the requests.
	"""
	budget = cint(settings.otp_global_daily_budget)
	if budget <= 0:
		return

	key = _today_key()
	spent = cint(frappe.cache.get_value(key))

	if spent >= budget:
		frappe.log_error(
			title="Prime Shito: daily OTP budget exhausted",
			message=f"{spent} verification messages sent today, budget is {budget}.",
		)
		frappe.throw(
			_("We cannot send verification codes right now. Please try again later or contact us."),
			frappe.ValidationError,
		)


def _spend_global_budget() -> None:
	key = _today_key()
	spent = cint(frappe.cache.get_value(key))
	# Expires comfortably after midnight; the key is date-stamped anyway.
	frappe.cache.set_value(key, spent + 1, expires_in_sec=90000)


def _count_today_for_phone(phone: str) -> int:
	return frappe.db.count(
		"Shito Phone Verification",
		{"phone": phone, "creation": (">=", frappe.utils.today())},
	)


def request_otp(raw_phone: str, ip_address: str | None = None) -> dict:
	"""Create and send a verification code. Returns metadata, never the code
	(except in developer mode, so local testing does not burn SMS credit)."""
	settings = _settings()
	phone = phone_utils.normalize(raw_phone)

	if frappe.db.get_value("Shito Customer", phone, "is_blocked"):
		# Deliberately vague: do not confirm to an attacker that a number is known.
		frappe.throw(_("We cannot send a code to that number. Please contact us."))

	# Resend cooldown, so a customer tapping "resend" repeatedly does not bill us.
	cooldown = cint(settings.otp_resend_cooldown_seconds) or 60
	last = frappe.get_all(
		"Shito Phone Verification",
		filters={"phone": phone},
		fields=["creation"],
		order_by="creation desc",
		limit=1,
	)
	if last:
		elapsed = (now_datetime() - last[0].creation).total_seconds()
		if elapsed < cooldown:
			frappe.throw(
				_("Please wait {0} seconds before asking for another code.").format(int(cooldown - elapsed))
			)

	daily_cap = cint(settings.otp_max_per_phone_per_day) or 5
	if _count_today_for_phone(phone) >= daily_cap:
		frappe.throw(_("Too many codes requested for this number today. Please try again tomorrow."))

	_check_global_budget(settings)

	length = cint(settings.otp_length) or 6
	ttl = cint(settings.otp_ttl_seconds) or 300

	otp = "".join(secrets.choice("0123456789") for _ in range(length))
	salt = secrets.token_hex(16)

	doc = frappe.get_doc(
		{
			"doctype": "Shito Phone Verification",
			"phone": phone,
			# Only the hash is stored. A database leak must not hand over live codes.
			"otp_hash": _hash(salt, otp),
			"salt": salt,
			"expires_at": add_to_date(now_datetime(), seconds=ttl),
			"attempts": 0,
			"verified": 0,
			"consumed": 0,
			"ip_address": ip_address,
		}
	).insert(ignore_permissions=True)

	sent = _send_otp(settings, phone, otp, ttl)
	if sent:
		_spend_global_budget()

	response = {
		"ok": True,
		"expires_in": ttl,
		"resend_in": cooldown,
		"masked_phone": phone_utils.mask(phone),
		"verification_id": doc.name,
	}

	# Developer convenience only, and doubly gated.
	if frappe.conf.developer_mode and cint(settings.otp_echo_in_dev):
		response["dev_otp"] = otp

	return response


def _send_otp(settings, phone: str, otp: str, ttl: int) -> bool:
	"""Send via Frappe's SMS Settings gateway. Never raises into the caller."""
	if not cint(settings.sms_enabled):
		return False

	from prime_shito.shito import notify

	message = notify.render(
		settings.tpl_otp or "{{ otp }} is your Prime Shito code. Valid {{ mins }} mins. Do not share it.",
		{"otp": otp, "mins": max(ttl // 60, 1)},
	)

	return notify.send_sms(
		phone,
		message,
		template_key="tpl_otp",
		reference_doctype="Shito Phone Verification",
	)


def verify_otp(raw_phone: str, otp: str, ip_address: str | None = None) -> dict:
	"""Check a code and issue a short-lived token that authorises one order."""
	settings = _settings()
	phone = phone_utils.normalize(raw_phone)
	otp = (otp or "").strip()

	max_attempts = cint(settings.otp_max_attempts) or 5

	records = frappe.get_all(
		"Shito Phone Verification",
		filters={"phone": phone, "verified": 0},
		fields=["name", "otp_hash", "salt", "expires_at", "attempts"],
		order_by="creation desc",
		limit=1,
	)

	if not records:
		frappe.throw(_("That code is not valid. Please request a new one."))

	record = records[0]

	if record.attempts >= max_attempts:
		frappe.throw(_("Too many wrong attempts. Please request a new code."))

	if record.expires_at < now_datetime():
		frappe.throw(_("That code has expired. Please request a new one."))

	# Count the attempt before comparing, so a crash mid-check cannot be used
	# to get free guesses.
	frappe.db.set_value(
		"Shito Phone Verification",
		record.name,
		"attempts",
		record.attempts + 1,
		update_modified=False,
	)
	frappe.db.commit()

	if not hmac.compare_digest(record.otp_hash, _hash(record.salt, otp)):
		remaining = max_attempts - (record.attempts + 1)
		if remaining <= 0:
			frappe.throw(_("Too many wrong attempts. Please request a new code."))
		frappe.throw(
			_("That code is not correct. {0} {1} left.").format(
				remaining, "try" if remaining == 1 else "tries"
			)
		)

	token = secrets.token_urlsafe(32)

	frappe.db.set_value(
		"Shito Phone Verification",
		record.name,
		{
			"verified": 1,
			"verified_at": now_datetime(),
			"verification_token": token,
			"token_expires_at": add_to_date(now_datetime(), minutes=TOKEN_TTL_MINUTES),
		},
		update_modified=False,
	)
	frappe.db.commit()

	return {
		"ok": True,
		"verification_token": token,
		"expires_in": TOKEN_TTL_MINUTES * 60,
	}


def consume_token(token: str, phone: str) -> str:
	"""Validate a verification token and burn it. Returns the record name.

	Single-use by design: a token authorises exactly one order.
	"""
	if not token:
		frappe.throw(_("Please verify your phone number."))

	records = frappe.get_all(
		"Shito Phone Verification",
		filters={
			"verification_token": token,
			"phone": phone,
			"verified": 1,
			"consumed": 0,
		},
		fields=["name", "token_expires_at"],
		limit=1,
	)

	if not records:
		frappe.throw(_("Please verify your phone number again."))

	record = records[0]
	if record.token_expires_at < now_datetime():
		frappe.throw(_("Your verification expired. Please verify your phone number again."))

	frappe.db.set_value("Shito Phone Verification", record.name, "consumed", 1, update_modified=False)

	return record.name
