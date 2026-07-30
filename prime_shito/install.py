import frappe

ROLES = (
	("Shito Manager", "Full access to the Prime Shito storefront, orders, settings and SMS."),
	("Shito Sales", "Takes and edits orders. No access to settings or deletion."),
	("Shito Dispatch", "Sees approved orders and moves them through delivery."),
)

# Modes of Payment the storefront needs but a stock ERPNext install does not ship.
MODES_OF_PAYMENT = ("Mobile Money", "Pay on Delivery")


def after_install():
	create_roles()
	create_modes_of_payment()
	frappe.db.commit()


def create_roles():
	"""Idempotently create the Shito roles.

	Must run before any DocType whose permissions reference them is imported,
	otherwise the DocPerm link validation fails during migrate.
	"""
	for role_name, desc in ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
				"is_custom": 0,
				"description": desc,
			}
		).insert(ignore_permissions=True)


DEMO_PACKS = (
	{
		"pack_code": "SHITO-CLASSIC-250",
		"pack_name": "Classic Shito 250g",
		"description": "Our original recipe. Deep, smoky and properly hot.",
		"flavour": "Classic",
		"heat_level": "Hot",
		"net_weight_g": 250,
		"price": 45.00,
		"shelf_life_days": 180,
		"is_featured": 1,
		"display_order": 1,
	},
	{
		"pack_code": "SHITO-BEEF-250",
		"pack_name": "Beef Shito 250g",
		"description": "Slow-fried with shredded beef. Rich and filling.",
		"flavour": "Beef",
		"heat_level": "Medium",
		"net_weight_g": 250,
		"price": 65.00,
		"shelf_life_days": 150,
		"is_featured": 1,
		"display_order": 2,
	},
	{
		"pack_code": "SHITO-FISH-500",
		"pack_name": "Dried Fish Shito 500g",
		"description": "Loaded with dried herring and prawns. The family jar.",
		"flavour": "Dried Fish",
		"heat_level": "Extra Hot",
		"net_weight_g": 500,
		"price": 110.00,
		"compare_at_price": 130.00,
		"shelf_life_days": 180,
		"display_order": 3,
	},
)

DEMO_ZONES = (
	{
		"zone_name": "Accra Central",
		"region": "Greater Accra",
		"delivery_fee": 20.00,
		"free_delivery_over": 200.00,
		"estimated_days": 1,
		"delivery_days": "Monday to Saturday",
		"display_order": 1,
	},
	{
		"zone_name": "Greater Accra (Outskirts)",
		"region": "Greater Accra",
		"delivery_fee": 35.00,
		"free_delivery_over": 300.00,
		"estimated_days": 2,
		"delivery_days": "Monday to Saturday",
		"display_order": 2,
	},
	{
		"zone_name": "Kumasi",
		"region": "Ashanti",
		"delivery_fee": 50.00,
		"min_order_amount": 100.00,
		"estimated_days": 3,
		"delivery_days": "Saturdays only",
		"display_order": 3,
	},
)


def create_demo_data():
	"""Seed a browsable catalog. Safe to re-run; existing records are left alone."""
	create_roles()
	create_modes_of_payment()

	for pack in DEMO_PACKS:
		if frappe.db.exists("Shito Pack", pack["pack_code"]):
			continue
		frappe.get_doc({"doctype": "Shito Pack", **pack}).insert(ignore_permissions=True)

	for zone in DEMO_ZONES:
		if frappe.db.exists("Shito Delivery Zone", zone["zone_name"]):
			continue
		frappe.get_doc({"doctype": "Shito Delivery Zone", **zone}).insert(ignore_permissions=True)

	settings = frappe.get_single("Prime Shito Settings")
	if not settings.business_name:
		settings.business_name = "Prime Shito"
	if not settings.tagline:
		settings.tagline = "Ghana's finest shito, made fresh in small batches"
	if not settings.about_text:
		settings.about_text = (
			"We make shito the slow way, in small batches, using dried fish and "
			"prawns from Ghanaian markets. Order ahead and we make yours fresh."
		)
	if not settings.meta_description:
		settings.meta_description = (
			"Order Prime Shito online. Classic, beef and dried fish shito made "
			"fresh in Ghana. Pay by Mobile Money or on delivery."
		)
	if not settings.min_order_amount:
		settings.min_order_amount = 45.00
	settings.save(ignore_permissions=True)

	frappe.db.commit()
	print(f"Seeded {len(DEMO_PACKS)} packs and {len(DEMO_ZONES)} delivery zones.")


def create_modes_of_payment():
	"""ERPNext ships Cash/Cheque/Credit Card/Wire Transfer/Bank Draft only.

	Ghana sells on Mobile Money, and pay-on-delivery needs its own mode so the
	two settle to different accounts.
	"""
	if not frappe.db.exists("DocType", "Mode of Payment"):
		return

	for mode in MODES_OF_PAYMENT:
		if frappe.db.exists("Mode of Payment", mode):
			continue
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode,
				"enabled": 1,
				"type": "Bank" if mode == "Mobile Money" else "Cash",
			}
		).insert(ignore_permissions=True)
