import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from prime_shito.shito import phone as phone_utils


class ShitoCustomer(Document):
	"""One record per phone number.

	The document name IS the normalised E.164 number, so duplicate customers
	for the same phone are impossible at the database level rather than by
	convention.
	"""

	def before_naming(self):
		"""Normalise the phone number BEFORE the name is derived from it.

		`autoname: field:phone` runs ahead of validate(), so normalising there
		would be too late: a staff member typing "024 111 2223" in Desk would
		get a record named with the raw string, while the storefront creates
		"+233241112223" -- two records for one person, defeating the whole point
		of making the phone number the primary key.
		"""
		self.phone = phone_utils.normalize(self.phone)

	def validate(self):
		self.normalise_phones()
		self.track_opt_out()

	def normalise_phones(self):
		# Runs again on every save: before_naming only fires on insert, and an
		# edit could still introduce a loosely formatted number.
		self.phone = phone_utils.normalize(self.phone)

		if self.alt_phone:
			self.alt_phone = phone_utils.normalize(self.alt_phone, throw=False) or None

	def track_opt_out(self):
		"""Record when consent was withdrawn.

		Ghana's Data Protection Act requires consent for marketing, and being
		able to show when someone opted out is the point of keeping this.
		"""
		if self.is_new():
			return

		was_opted_in = cint(self.get_doc_before_save().marketing_opt_in)

		if was_opted_in and not cint(self.marketing_opt_in):
			self.opted_out_at = now_datetime()
			if not self.opt_out_source:
				self.opt_out_source = "Admin"
		elif cint(self.marketing_opt_in) and not was_opted_in:
			self.opted_out_at = None
			self.opt_out_source = None

	@property
	def can_receive_marketing(self) -> bool:
		return bool(cint(self.marketing_opt_in) and not cint(self.is_blocked))
