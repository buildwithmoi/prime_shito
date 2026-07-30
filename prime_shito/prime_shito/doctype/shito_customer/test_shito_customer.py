import frappe
from frappe.tests import IntegrationTestCase

# Frappe walks test-record dependencies recursively, reading this list from each
# doctype's OWN test module. Without it here, Shito Customer's erp_customer link
# pulls in ERPNext's test modules, whose utils.py builds BootStrapTestData at
# import time and fails on a site that already has a chart of accounts.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Shito Order", "Shito Delivery Zone"]

TEST_PHONE = "+233240000900"


class TestShitoCustomer(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shito Customer", {"name": TEST_PHONE})
		frappe.db.commit()

	def _make(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "Shito Customer",
				"phone": TEST_PHONE,
				"full_name": "Test Customer",
				**kwargs,
			}
		).insert(ignore_permissions=True)

	def test_phone_is_the_primary_key(self):
		"""Duplicate customers per phone are impossible at the database level,
		not merely discouraged by application code."""
		doc = self._make()
		self.assertEqual(doc.name, TEST_PHONE)

		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{"doctype": "Shito Customer", "phone": TEST_PHONE, "full_name": "Impostor"}
			).insert(ignore_permissions=True)

	def test_phone_is_normalised_to_e164(self):
		frappe.db.delete("Shito Customer", {"name": "+233241112223"})
		doc = frappe.get_doc(
			{"doctype": "Shito Customer", "phone": "024 111 2223", "full_name": "Loose Format"}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.phone, "+233241112223")

	def test_non_ghanaian_numbers_are_rejected(self):
		"""A premium-rate international number on an SMS endpoint is a way to
		run up someone else's bill."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Shito Customer", "phone": "+1 900 555 0199", "full_name": "Premium Rate"}
			).insert(ignore_permissions=True)

	def test_opt_out_is_timestamped(self):
		doc = self._make(marketing_opt_in=1)
		self.assertFalse(doc.opted_out_at)

		doc.marketing_opt_in = 0
		doc.save(ignore_permissions=True)

		self.assertTrue(doc.opted_out_at)
		self.assertEqual(doc.opt_out_source, "Admin")

	def test_opting_back_in_clears_the_record(self):
		doc = self._make(marketing_opt_in=1)
		doc.marketing_opt_in = 0
		doc.save(ignore_permissions=True)

		doc.marketing_opt_in = 1
		doc.save(ignore_permissions=True)

		self.assertFalse(doc.opted_out_at)
		self.assertTrue(doc.can_receive_marketing)

	def test_blocked_customer_cannot_receive_marketing(self):
		doc = self._make(marketing_opt_in=1, is_blocked=1)
		self.assertFalse(doc.can_receive_marketing)
