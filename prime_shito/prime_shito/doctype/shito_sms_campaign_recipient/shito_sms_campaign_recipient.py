from frappe.model.document import Document


class ShitoSMSCampaignRecipient(Document):
	"""One row per number in a campaign.

	Written by `campaigns.preview()` and updated in place as the send runs, so
	a job that dies halfway can resume without texting anyone twice.
	"""

	pass
