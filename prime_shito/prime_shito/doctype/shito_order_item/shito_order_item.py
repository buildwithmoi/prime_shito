from frappe.model.document import Document


class ShitoOrderItem(Document):
	"""A line on a Shito Order.

	`rate` and `amount` are written exclusively by
	`prime_shito.shito.pricing.apply_to_order`, which runs on every save of the
	parent. Nothing here should compute money.
	"""

	pass
