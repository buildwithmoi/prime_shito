from frappe.model.document import Document


class ShitoSMSMessage(Document):
	"""One row per outbound SMS.

	Frappe's own SMS Log records a batch, not a message: no per-recipient
	status, no provider id, no cost. Since SMS is a real running cost for this
	business and the owner needs to answer "did the customer actually get
	told?", each message is logged individually here instead.

	Rows are cleared after 180 days by `default_log_clearing_doctypes`.
	"""

	pass
