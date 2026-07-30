import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate
from frappe.website.utils import cleanup_page_name


class ShitoPack(Document):
	def validate(self):
		self.set_route()
		self.validate_pricing()
		self.validate_quantities()
		self.validate_availability_window()

	def on_update(self):
		frappe.cache.delete_value("prime_shito_storefront")

	def on_trash(self):
		frappe.cache.delete_value("prime_shito_storefront")

	def set_route(self):
		if not self.route:
			self.route = cleanup_page_name(self.pack_name)

		self.route = cleanup_page_name(self.route)

		if not self.route:
			frappe.throw(_("Could not build a URL slug from the pack name. Please set one."))

	def validate_pricing(self):
		if flt(self.price) <= 0:
			frappe.throw(_("Price must be greater than zero."))

		if flt(self.compare_at_price) and flt(self.compare_at_price) <= flt(self.price):
			frappe.throw(
				_(
					"Compare At Price must be higher than the price, or left empty. "
					"It is shown struck through to signal a discount."
				)
			)

	def validate_quantities(self):
		if cint(self.min_order_qty) < 1:
			self.min_order_qty = 1

		if cint(self.max_order_qty) and cint(self.max_order_qty) < cint(self.min_order_qty):
			frappe.throw(_("Maximum Order Quantity cannot be less than Minimum Order Quantity."))

		if cint(self.available_qty) < 0:
			self.available_qty = 0

		if cint(self.reserved_qty) < 0:
			self.reserved_qty = 0

	def validate_availability_window(self):
		if (
			self.available_from
			and self.available_upto
			and getdate(self.available_from) > getdate(self.available_upto)
		):
			frappe.throw(_("Available From cannot be after Available Until."))

	@property
	def free_qty(self) -> int:
		return cint(self.available_qty) - cint(self.reserved_qty)

	def as_storefront_dict(self) -> dict:
		"""Explicit projection for anonymous visitors.

		Never return the document itself: it carries internal quantities and
		the ERPNext link, none of which a shopper should see.
		"""
		return {
			"pack": self.name,
			"pack_name": self.pack_name,
			"route": self.route,
			"description": self.description,
			"long_description": self.long_description,
			"image": self.image,
			"image_alt": self.image_alt,
			"flavour": self.flavour,
			"heat_level": self.heat_level,
			"net_weight_g": cint(self.net_weight_g),
			"price": flt(self.price),
			"compare_at_price": flt(self.compare_at_price),
			"min_order_qty": max(cint(self.min_order_qty), 1),
			"max_order_qty": cint(self.max_order_qty),
			"is_featured": cint(self.is_featured),
			"sold_out": bool(cint(self.track_availability) and self.free_qty <= 0),
		}
