import frappe
from frappe.tests import IntegrationTestCase

from prime_shito.shito import campaigns, gsm

# Keeps Frappe's recursive test-record generation away from ERPNext, whose
# tests/utils.py builds BootStrapTestData at import time.
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Shito Delivery Zone",
	"Shito Pack",
	"Shito Order",
	"Shito SMS Message",
	"Customer",
	"Item",
	"UOM",
]

OPTED_IN = "+233240000801"
OPTED_OUT = "+233240000802"
BLOCKED = "+233240000803"
NEVER_ORDERED = "+233240000804"
UNKNOWN = "+233240000899"


def _customer(phone, **kwargs):
	if frappe.db.exists("Shito Customer", phone):
		frappe.delete_doc("Shito Customer", phone, force=True, ignore_permissions=True)
	return frappe.get_doc(
		{
			"doctype": "Shito Customer",
			"phone": phone,
			"full_name": f"Test {phone[-3:]}",
			**kwargs,
		}
	).insert(ignore_permissions=True)


def _campaign(**kwargs):
	doc = frappe.get_doc(
		{
			"doctype": "Shito SMS Campaign",
			"campaign_name": "Test Campaign",
			"audience": "All Opted-In",
			"message": "New batch of shito is ready. Order at primeshito.com",
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestAudienceConsent(IntegrationTestCase):
	"""Consent is the whole point of this module.

	Ghana's Data Protection Act requires it for marketing, and the filtering
	happens in SQL precisely so that no code path can forget it.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_customer(OPTED_IN, marketing_opt_in=1, total_orders=3, total_spent=500)
		_customer(OPTED_OUT, marketing_opt_in=0, total_orders=5, total_spent=900)
		_customer(BLOCKED, marketing_opt_in=1, is_blocked=1, total_orders=2)
		_customer(NEVER_ORDERED, marketing_opt_in=1, total_orders=0)
		frappe.db.commit()

	def test_opted_in_customer_is_included(self):
		phones = [r["phone"] for r in campaigns.resolve_audience(_campaign())]
		self.assertIn(OPTED_IN, phones)

	def test_opted_out_customer_is_never_included(self):
		phones = [r["phone"] for r in campaigns.resolve_audience(_campaign())]
		self.assertNotIn(OPTED_OUT, phones)

	def test_blocked_customer_is_never_included(self):
		phones = [r["phone"] for r in campaigns.resolve_audience(_campaign())]
		self.assertNotIn(BLOCKED, phones)

	def test_past_customers_excludes_those_who_never_ordered(self):
		phones = [r["phone"] for r in campaigns.resolve_audience(_campaign(audience="Past Customers"))]
		self.assertIn(OPTED_IN, phones)
		self.assertNotIn(NEVER_ORDERED, phones)

	def test_manual_list_still_respects_opt_out(self):
		"""Typing a number by hand is not a way around unsubscribing."""
		campaign = _campaign(
			audience="Manual List",
			manual_numbers="\n".join([OPTED_IN, OPTED_OUT, BLOCKED, UNKNOWN]),
		)
		phones = [r["phone"] for r in campaigns.resolve_audience(campaign)]

		self.assertEqual(phones, [OPTED_IN])
		self.assertNotIn(OPTED_OUT, phones)
		self.assertNotIn(BLOCKED, phones)
		# A number we have never seen has given no consent at all.
		self.assertNotIn(UNKNOWN, phones)

	def test_min_orders_filter(self):
		campaign = _campaign(min_orders=4)
		self.assertNotIn(OPTED_IN, [r["phone"] for r in campaigns.resolve_audience(campaign)])


class TestCampaignMessage(IntegrationTestCase):
	def test_opt_out_footer_is_appended(self):
		campaign = _campaign(message="Fresh batch today")
		self.assertIn("STOP", campaigns.build_message(campaign))

	def test_footer_not_duplicated(self):
		campaign = _campaign(message="Fresh batch today. Reply STOP to unsubscribe")
		self.assertEqual(campaigns.build_message(campaign).upper().count("STOP"), 1)

	def test_message_with_cedi_symbol_is_rejected(self):
		"""One cedi sign doubles the cost of every message in the campaign."""
		with self.assertRaises(frappe.ValidationError):
			_campaign(message="Everything is ₵50 today")

	def test_shipped_message_stays_gsm7(self):
		campaign = _campaign(message="New batch ready. Classic 250g is GHS 45.00")
		self.assertTrue(gsm.is_gsm7(campaigns.build_message(campaign)))

	def test_empty_message_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			_campaign(message="   ")


class TestUnsubscribe(IntegrationTestCase):
	def test_unsubscribe_clears_consent(self):
		_customer(OPTED_IN, marketing_opt_in=1, total_orders=1)
		frappe.db.commit()

		campaigns.unsubscribe(OPTED_IN)

		self.assertFalse(frappe.db.get_value("Shito Customer", OPTED_IN, "marketing_opt_in"))
		self.assertTrue(frappe.db.get_value("Shito Customer", OPTED_IN, "opted_out_at"))

	def test_unsubscribe_answers_identically_for_an_unknown_number(self):
		"""Otherwise it becomes a way to test whether someone has ever ordered."""
		known = campaigns.unsubscribe(OPTED_IN)
		unknown = campaigns.unsubscribe(UNKNOWN)
		self.assertEqual(known, unknown)

	def test_unsubscribed_customer_drops_out_of_the_audience(self):
		_customer(OPTED_IN, marketing_opt_in=1, total_orders=1)
		frappe.db.commit()

		campaigns.unsubscribe(OPTED_IN)
		frappe.db.commit()

		phones = [r["phone"] for r in campaigns.resolve_audience(_campaign())]
		self.assertNotIn(OPTED_IN, phones)
