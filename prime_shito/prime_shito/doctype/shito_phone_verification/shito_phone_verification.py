from frappe.model.document import Document


class ShitoPhoneVerification(Document):
	"""A short-lived OTP challenge.

	Stored as a DocType rather than purely in Redis so it survives a cache
	flush and leaves an auditable trail of SMS-bombing attempts. Redis still
	holds the cheap counters (the global daily budget); this holds the record.

	`otp_hash` is sha256(salt + code): the plaintext code is never persisted,
	so a database leak does not hand over live codes. Rows are cleared after 7
	days by `default_log_clearing_doctypes` in hooks.py.
	"""

	pass
