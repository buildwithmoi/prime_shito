import frappe
from frappe.tests import IntegrationTestCase

from prime_shito.shito import gsm, pricing

# Shito Pack links to UOM and Item. Frappe would otherwise auto-generate test
# records for both, which imports ERPNext's test modules -- and
# erpnext/tests/utils.py instantiates BootStrapTestData() at module scope, which
# tries to recreate the Standard Buying price list in INR and blows up on any
# site that already has one. None of these tests touch UOM or Item.
IGNORE_TEST_RECORD_DEPENDENCIES = ["UOM", "Item"]

TEST_PACK = "_TEST-SHITO-PACK"
TEST_ZONE = "_Test Shito Zone"


class TestShitoPack(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not frappe.db.exists("Shito Pack", TEST_PACK):
			frappe.get_doc(
				{
					"doctype": "Shito Pack",
					"pack_code": TEST_PACK,
					"pack_name": "Test Shito Pack",
					"price": 50.00,
					"min_order_qty": 1,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Shito Delivery Zone", TEST_ZONE):
			frappe.get_doc(
				{
					"doctype": "Shito Delivery Zone",
					"zone_name": TEST_ZONE,
					"delivery_fee": 20.00,
					"free_delivery_over": 200.00,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_route_is_generated_from_name(self):
		pack = frappe.get_doc("Shito Pack", TEST_PACK)
		self.assertEqual(pack.route, "test-shito-pack")

	def test_price_must_be_positive(self):
		pack = frappe.get_doc("Shito Pack", TEST_PACK)
		pack.price = 0
		self.assertRaises(frappe.ValidationError, pack.save)
		pack.reload()

	def test_compare_at_price_must_exceed_price(self):
		pack = frappe.get_doc("Shito Pack", TEST_PACK)
		pack.compare_at_price = 10.00  # lower than the 50.00 price
		self.assertRaises(frappe.ValidationError, pack.save)
		pack.reload()


class TestPricing(IntegrationTestCase):
	"""The pricing engine is the only thing standing between a tampered request
	and a wrong charge, so it carries the heaviest test coverage."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestShitoPack.setUpClass()

	def test_totals(self):
		quote = pricing.compute([{"pack": TEST_PACK, "qty": 2}], delivery_zone=TEST_ZONE)
		self.assertEqual(quote.items_total, 100.00)
		self.assertEqual(quote.delivery_fee, 20.00)
		self.assertEqual(quote.grand_total, 120.00)
		self.assertEqual(quote.grand_total_pesewas, 12000)
		self.assertTrue(quote.is_orderable)

	def test_client_supplied_rate_is_ignored(self):
		"""A caller must not be able to set its own price."""
		quote = pricing.compute(
			[{"pack": TEST_PACK, "qty": 2, "rate": 1, "amount": 1, "price": 1}],
			delivery_zone=TEST_ZONE,
		)
		self.assertEqual(quote.lines[0].rate, 50.00)
		self.assertEqual(quote.grand_total, 120.00)

	def test_free_delivery_threshold(self):
		quote = pricing.compute([{"pack": TEST_PACK, "qty": 4}], delivery_zone=TEST_ZONE)
		self.assertEqual(quote.items_total, 200.00)
		self.assertTrue(quote.free_delivery_applied)
		self.assertEqual(quote.delivery_fee, 0.00)

	def test_negative_and_zero_quantities_are_dropped(self):
		for qty in (-5, 0):
			quote = pricing.compute([{"pack": TEST_PACK, "qty": qty}], delivery_zone=TEST_ZONE)
			self.assertEqual(quote.lines, [])
			self.assertEqual(quote.grand_total, 0.00)

	def test_duplicate_lines_are_merged(self):
		quote = pricing.compute(
			[{"pack": TEST_PACK, "qty": 2}, {"pack": TEST_PACK, "qty": 3}],
			delivery_zone=TEST_ZONE,
		)
		self.assertEqual(len(quote.lines), 1)
		self.assertEqual(quote.lines[0].qty, 5)

	def test_unknown_pack_blocks_the_order(self):
		quote = pricing.compute([{"pack": "_NOPE", "qty": 1}], delivery_zone=TEST_ZONE)
		self.assertFalse(quote.is_orderable)
		self.assertTrue(quote.blocking_errors)

	def test_unknown_zone_blocks_the_order(self):
		quote = pricing.compute([{"pack": TEST_PACK, "qty": 1}], delivery_zone="_Atlantis")
		self.assertFalse(quote.is_orderable)

	def test_pickup_has_no_delivery_fee(self):
		quote = pricing.compute(
			[{"pack": TEST_PACK, "qty": 1}], delivery_zone=TEST_ZONE, fulfilment_type="Pickup"
		)
		self.assertEqual(quote.delivery_fee, 0.00)

	def test_customer_facing_messages_stay_gsm7(self):
		"""Error copy can reach an SMS. One non-GSM-7 character there cuts the
		segment size from 160 characters to 70 and doubles the cost."""
		quote = pricing.compute([{"pack": "_NOPE", "qty": 1}], delivery_zone=TEST_ZONE)
		for message in quote.blocking_errors:
			self.assertTrue(
				gsm.is_gsm7(message),
				f"Non-GSM-7 characters in customer message: {gsm.non_gsm7_characters(message)}",
			)


class TestGsm(IntegrationTestCase):
	def test_segment_counting(self):
		self.assertEqual(gsm.count_segments("Hello"), ("GSM-7", 1))
		self.assertEqual(gsm.count_segments("a" * 160), ("GSM-7", 1))
		self.assertEqual(gsm.count_segments("a" * 161), ("GSM-7", 2))

	def test_cedi_sign_forces_ucs2(self):
		"""The exact failure this guard exists to prevent."""
		encoding, _ = gsm.count_segments("Total GHS 120.00")
		self.assertEqual(encoding, "GSM-7")

		encoding, _ = gsm.count_segments("Total ₵120.00")
		self.assertEqual(encoding, "UCS-2")
		self.assertFalse(gsm.is_gsm7("₵"))
