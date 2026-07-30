"""Ghanaian phone number normalisation.

Frappe ships `frappe.utils.validate_phone_number_with_country_code`, but it only
asks libphonenumber whether the number is valid *somewhere*. That would happily
accept an international premium-rate number, which on an OTP endpoint is a way
for an attacker to bill us. Everything here is deliberately Ghana-only.
"""

import frappe
import phonenumbers
from frappe import _
from phonenumbers import NumberParseException, PhoneNumberType

REGION = "GH"

# Mobile numbers only. Landlines cannot receive SMS, and accepting them means
# silently dropping every notification for that customer.
ALLOWED_TYPES = (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)


class InvalidPhoneNumber(frappe.ValidationError):
	pass


def normalize(raw: str, *, throw: bool = True) -> str | None:
	"""Return a Ghanaian mobile number in E.164 form, e.g. "+233241234567".

	Accepts the shapes customers actually type: 0241234567, 233241234567,
	+233 24 123 4567, 024-123-4567.
	"""
	if not raw or not str(raw).strip():
		if throw:
			frappe.throw(_("Please enter your phone number."), InvalidPhoneNumber)
		return None

	candidate = str(raw).strip()

	# "233..." without a plus parses as a national number and fails. Add the plus.
	digits = "".join(ch for ch in candidate if ch.isdigit())
	if not candidate.startswith("+") and digits.startswith("233") and len(digits) > 9:
		candidate = f"+{digits}"

	try:
		parsed = phonenumbers.parse(candidate, REGION)
	except NumberParseException:
		if throw:
			frappe.throw(_("{0} is not a valid phone number.").format(raw), InvalidPhoneNumber)
		return None

	if not phonenumbers.is_valid_number(parsed):
		if throw:
			frappe.throw(_("{0} is not a valid phone number.").format(raw), InvalidPhoneNumber)
		return None

	if phonenumbers.region_code_for_number(parsed) != REGION:
		if throw:
			frappe.throw(_("Please enter a Ghanaian phone number."), InvalidPhoneNumber)
		return None

	if phonenumbers.number_type(parsed) not in ALLOWED_TYPES:
		if throw:
			frappe.throw(
				_("Please enter a mobile number so we can text you about your order."),
				InvalidPhoneNumber,
			)
		return None

	return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def is_valid(raw: str) -> bool:
	return normalize(raw, throw=False) is not None


def to_local_international(e164: str) -> str:
	"""Strip the leading plus: "+233241234567" -> "233241234567".

	This is the form Arkesel's API expects in its recipients array.
	"""
	return (e164 or "").lstrip("+")


def last4(e164: str) -> str:
	digits = "".join(ch for ch in (e164 or "") if ch.isdigit())
	return digits[-4:]


def mask(e164: str) -> str:
	"""Redact for display: "+233241234567" -> "+233 24 *** **67"."""
	if not e164:
		return ""
	digits = "".join(ch for ch in e164 if ch.isdigit())
	if len(digits) < 6:
		return "***"
	return f"+{digits[:3]} {digits[3:5]} *** **{digits[-2:]}"


def format_national(e164: str) -> str:
	"""Display form for the customer's own number, e.g. "024 123 4567"."""
	try:
		parsed = phonenumbers.parse(e164, REGION)
	except NumberParseException:
		return e164
	return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
