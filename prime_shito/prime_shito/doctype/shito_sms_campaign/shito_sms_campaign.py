import frappe
from frappe import _
from frappe.model.document import Document

from prime_shito.shito import campaigns, gsm


class ShitoSMSCampaign(Document):
	"""A bulk marketing send.

	Audience resolution, consent filtering and sending all live in
	`prime_shito.shito.campaigns`; this class only guards the document itself.
	"""

	def validate(self):
		self.validate_message()
		self.validate_audience()

	def validate_message(self):
		if not (self.message or "").strip():
			frappe.throw(_("Write a message."))

		# The opt-out footer is part of what gets sent, so it is part of what
		# gets checked -- and paid for.
		full = campaigns.build_message(self)
		bad = gsm.non_gsm7_characters(full)

		if bad:
			frappe.throw(
				_(
					"The message contains characters that cannot be sent cheaply by SMS: {0}<br><br>"
					"These force UCS-2 encoding, which cuts each segment from 160 characters to 70 "
					"and roughly doubles the cost of every message in this campaign. "
					"Write GHS instead of the cedi symbol."
				).format(frappe.bold(" ".join(bad))),
				title=_("Expensive characters in message"),
			)

	def validate_audience(self):
		if self.audience == "By Delivery Zone" and not self.zone:
			frappe.throw(_("Choose a delivery zone."))
		if self.audience == "By Pack" and not self.pack:
			frappe.throw(_("Choose a pack."))
		if self.audience == "Manual List" and not (self.manual_numbers or "").strip():
			frappe.throw(_("Add at least one phone number."))

	def on_trash(self):
		if self.status in ("Sending", "Sent", "Partially Sent"):
			frappe.throw(_("A campaign that has been sent cannot be deleted."))
