import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class ShitoDeliveryZone(Document):
	def validate(self):
		if flt(self.delivery_fee) < 0:
			frappe.throw(_("Delivery Fee cannot be negative."))

		if flt(self.free_delivery_over) and flt(self.free_delivery_over) < flt(self.min_order_amount):
			frappe.throw(
				_(
					"Free Delivery Over cannot be less than the zone's Minimum Order Amount, "
					"or no order could ever qualify."
				)
			)

		if cint(self.estimated_days) < 0:
			self.estimated_days = 0

	def on_update(self):
		frappe.cache.delete_value("prime_shito_storefront")

	def on_trash(self):
		frappe.cache.delete_value("prime_shito_storefront")

	def as_storefront_dict(self) -> dict:
		return {
			"zone": self.name,
			"zone_name": self.zone_name,
			"region": self.region,
			"delivery_fee": flt(self.delivery_fee),
			"free_delivery_over": flt(self.free_delivery_over),
			"min_order_amount": flt(self.min_order_amount),
			"estimated_days": cint(self.estimated_days),
			"delivery_days": self.delivery_days,
		}
