import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_url

from prime_shito.shito import gsm, phone

WEBHOOK_METHOD = "prime_shito.api.webhooks.paystack"

TEMPLATE_PREFIX = "tpl_"
MAX_SENDER_ID = 11


class PrimeShitoSettings(Document):
	def validate(self):
		self.validate_templates()
		self.validate_sender_id()
		self.validate_whatsapp_number()
		self.set_webhook_url()

	def on_update(self):
		# Business name, hours and payment toggles are all baked into the
		# cached storefront payload.
		frappe.cache.delete_value("prime_shito_storefront")

	def validate_templates(self):
		"""Reject characters that would silently double the SMS bill.

		A single non-GSM-7 character drops the message from 160 characters per
		segment to 70. The cedi sign is the one people reach for by instinct,
		so this check pays for itself immediately.
		"""
		for df in self.meta.fields:
			if not df.fieldname.startswith(TEMPLATE_PREFIX):
				continue

			value = self.get(df.fieldname)
			if not value:
				continue

			bad = gsm.non_gsm7_characters(value)
			if bad:
				frappe.throw(
					_(
						"{0} contains characters that cannot be sent cheaply by SMS: {1}<br><br>"
						"These force the message into UCS-2 encoding, which cuts each segment "
						"from 160 characters to 70 and roughly doubles the cost of every "
						"message. Write GHS instead of the cedi symbol."
					).format(frappe.bold(_(df.label)), frappe.bold(" ".join(bad))),
					title=_("Expensive characters in template"),
				)

	def validate_sender_id(self):
		if self.arkesel_sender_id and len(self.arkesel_sender_id) > MAX_SENDER_ID:
			frappe.throw(_("Sender ID must be {0} characters or fewer.").format(MAX_SENDER_ID))

	def validate_whatsapp_number(self):
		for fieldname in ("whatsapp_number", "support_phone"):
			value = self.get(fieldname)
			if value:
				self.set(fieldname, phone.normalize(value))

	def set_webhook_url(self):
		self.paystack_webhook_url = get_url(f"/api/method/{WEBHOOK_METHOD}")


def get_settings():
	"""Cached settings accessor used across the app."""
	return frappe.get_cached_doc("Prime Shito Settings")


def storefront_context() -> dict:
	"""The subset of settings that is safe to expose to an anonymous visitor.

	Deliberately explicit: secrets live on the same doctype, so this must never
	become a loop over all fields.
	"""
	s = get_settings()
	return {
		"business_name": s.business_name or "Prime Shito",
		"tagline": s.tagline,
		"about_text": s.about_text,
		"logo": s.logo,
		"hero_image": s.hero_image,
		"meta_description": s.meta_description,
		"og_image": s.og_image,
		"support_phone": s.support_phone,
		"support_email": s.support_email,
		"whatsapp_number": phone.to_local_international(s.whatsapp_number or ""),
		"currency": s.currency or "GHS",
		"is_store_open": cint(s.is_store_open),
		"store_closed_message": s.store_closed_message,
		"min_order_amount": s.min_order_amount,
		"max_qty_per_line": cint(s.max_qty_per_line) or 50,
		"allow_online_payment": cint(s.allow_online_payment and s.paystack_enabled),
		"allow_pay_on_delivery": cint(s.allow_pay_on_delivery),
		"delivery_lead_days": cint(s.delivery_lead_days),
		"paystack_public_key": s.paystack_public_key if cint(s.paystack_enabled) else None,
	}
