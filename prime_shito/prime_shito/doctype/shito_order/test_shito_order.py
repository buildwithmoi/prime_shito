import json

import frappe
from frappe.tests import IntegrationTestCase

from prime_shito.api import orders as orders_api
from prime_shito.install import WORKFLOW_NAME, WORKFLOW_TRANSITIONS
from prime_shito.prime_shito.doctype.shito_order.shito_order import new_tracking_code
from prime_shito.shito import state

# Shito Order links to several ERPNext doctypes. Letting Frappe auto-generate
# test records for them imports ERPNext's test modules, whose utils.py builds
# BootStrapTestData at import time and fails on a site that already has a
# chart of accounts. None of these tests touch those doctypes.
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Sales Order",
	"Payment Entry",
	"Customer",
	"Item",
	"UOM",
	"Currency",
	"Workflow State",
]

TEST_PACK = "_TEST-ORDER-PACK"
TEST_ZONE = "_Test Order Zone"


def _ensure_masters():
	if not frappe.db.exists("Shito Pack", TEST_PACK):
		frappe.get_doc(
			{
				"doctype": "Shito Pack",
				"pack_code": TEST_PACK,
				"pack_name": "Test Order Pack",
				"price": 50.00,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Shito Delivery Zone", TEST_ZONE):
		frappe.get_doc(
			{
				"doctype": "Shito Delivery Zone",
				"zone_name": TEST_ZONE,
				"delivery_fee": 20.00,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()


def _make_order(phone="+233240000001", payment_method="Pay on Delivery", qty=2):
	return frappe.get_doc(
		{
			"doctype": "Shito Order",
			"customer_name": "Test Buyer",
			"phone": phone,
			"fulfilment_type": "Delivery",
			"delivery_zone": TEST_ZONE,
			"delivery_address": "1 Test Street, Accra",
			"payment_method": payment_method,
			"items": [{"pack": TEST_PACK, "qty": qty}],
		}
	).insert(ignore_permissions=True)


class TestWorkflowParity(IntegrationTestCase):
	"""The Workflow record and shito.state.ALLOWED describe the same graph.

	They must agree: humans move orders through the Workflow in Desk, machines
	through state.transition(). If they drift, a payment webhook could reach a
	state the owner can never reach by hand, or vice versa.
	"""

	def test_workflow_transitions_match_state_machine(self):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)

		for row in workflow.transitions:
			self.assertIn(
				row.next_state,
				state.ALLOWED.get(row.state, set()),
				f"Workflow allows {row.state} -> {row.next_state} but the state machine does not",
			)

	def test_install_table_matches_installed_workflow(self):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
		installed = {(r.state, r.action, r.next_state) for r in workflow.transitions}
		declared = {(f, a, t) for f, a, t, _role in WORKFLOW_TRANSITIONS}
		self.assertEqual(installed, declared)

	def test_first_workflow_state_is_where_orders_start(self):
		"""Frappe refuses on insert to set any state but the first, and that
		check ignores roles, so this ordering is load-bearing."""
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
		self.assertEqual(workflow.states[0].state, state.AWAITING_APPROVAL)


class TestTrackingCode(IntegrationTestCase):
	def test_format(self):
		code = new_tracking_code()
		self.assertRegex(code, r"^PS-[2-9A-Z]{4}-[2-9A-Z]{4}$")

	def test_excludes_ambiguous_characters(self):
		"""Codes get read aloud and retyped, so 0/O and 1/I/L must not appear."""
		blob = "".join(new_tracking_code() for _ in range(200))
		for ch in "01ILOU":
			self.assertNotIn(ch, blob.replace("PS-", ""))

	def test_codes_are_unique_and_unpredictable(self):
		codes = {new_tracking_code() for _ in range(500)}
		self.assertEqual(len(codes), 500)

		# make_autoname("hash") would share a timestamp-derived prefix between
		# codes generated together. secrets must not.
		prefixes = {c[3:7] for c in codes}
		self.assertGreater(len(prefixes), 400)


class TestShitoOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_masters()

	def test_totals_are_computed_server_side(self):
		order = _make_order(phone="+233240000010", qty=2)
		self.assertEqual(order.items_total, 100.00)
		self.assertEqual(order.delivery_fee, 20.00)
		self.assertEqual(order.grand_total, 120.00)
		self.assertEqual(order.grand_total_pesewas, 12000)

	def test_supplied_rates_are_overwritten(self):
		"""read_only in the DocType JSON does not stop an API caller. Only the
		unconditional recompute in validate() does."""
		order = frappe.get_doc(
			{
				"doctype": "Shito Order",
				"customer_name": "Tamperer",
				"phone": "+233240000011",
				"fulfilment_type": "Delivery",
				"delivery_zone": TEST_ZONE,
				"delivery_address": "1 Test Street",
				"payment_method": "Pay on Delivery",
				"grand_total": 1.00,
				"items_total": 1.00,
				"items": [{"pack": TEST_PACK, "qty": 2, "rate": 1.00, "amount": 2.00}],
			}
		).insert(ignore_permissions=True)

		self.assertEqual(order.items[0].rate, 50.00)
		self.assertEqual(order.grand_total, 120.00)

	def test_order_starts_awaiting_approval(self):
		order = _make_order(phone="+233240000012")
		self.assertEqual(order.workflow_state, state.AWAITING_APPROVAL)
		self.assertTrue(order.tracking_code)
		self.assertTrue(order.confirmed_at)

	def test_delivery_requires_zone_and_address(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Shito Order",
					"customer_name": "No Address",
					"phone": "+233240000013",
					"fulfilment_type": "Delivery",
					"payment_method": "Pay on Delivery",
					"items": [{"pack": TEST_PACK, "qty": 1}],
				}
			).insert(ignore_permissions=True)

	def test_pickup_clears_zone_and_fee(self):
		order = frappe.get_doc(
			{
				"doctype": "Shito Order",
				"customer_name": "Pickup Buyer",
				"phone": "+233240000014",
				"fulfilment_type": "Pickup",
				"delivery_zone": TEST_ZONE,
				"payment_method": "Pay on Delivery",
				"items": [{"pack": TEST_PACK, "qty": 1}],
			}
		).insert(ignore_permissions=True)

		self.assertFalse(order.delivery_zone)
		self.assertEqual(order.delivery_fee, 0.00)

	def test_machine_transition_works_without_workflow_roles(self):
		order = _make_order(phone="+233240000015")

		original = frappe.session.user
		try:
			frappe.set_user("Guest")
			self.assertTrue(state.transition(order, state.APPROVED, actor="test"))
		finally:
			frappe.set_user(original)

		order.reload()
		self.assertEqual(order.workflow_state, state.APPROVED)
		self.assertTrue(order.approved_at)

	def test_transition_is_idempotent(self):
		order = _make_order(phone="+233240000016")
		state.transition(order, state.APPROVED)
		self.assertFalse(state.transition(order, state.APPROVED))

	def test_illegal_transition_is_blocked(self):
		order = _make_order(phone="+233240000017")
		with self.assertRaises(frappe.ValidationError):
			state.transition(order, state.COMPLETED)

	def test_tracking_projection_redacts_personal_data(self):
		order = _make_order(phone="+233240000018")
		payload = order.as_tracking_dict()

		self.assertNotIn("phone", payload)
		self.assertNotIn("delivery_address", payload)
		self.assertNotIn("email", payload)
		self.assertNotIn("ip_address", payload)

		self.assertIn("***", payload["masked_phone"])
		self.assertEqual(payload["customer_first_name"], "Test")


class TestTrackOrderSecurity(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_masters()

	def test_wrong_last4_and_unknown_code_are_indistinguishable(self):
		order = _make_order(phone="+233240000020")

		wrong_digits = None
		unknown_code = None

		try:
			orders_api.track_order(order.tracking_code, "0000")
		except Exception as exc:
			wrong_digits = str(exc)

		try:
			orders_api.track_order("PS-ZZZZ-ZZZZ", "0020")
		except Exception as exc:
			unknown_code = str(exc)

		self.assertIsNotNone(wrong_digits)
		self.assertEqual(wrong_digits, unknown_code)

	def test_correct_credentials_return_the_order(self):
		order = _make_order(phone="+233240000021")
		payload = orders_api.track_order(order.tracking_code, "0021")
		self.assertEqual(payload["tracking_code"], order.tracking_code)

	def test_malformed_input_is_rejected(self):
		for code, digits in (("", "1234"), ("PS-AAAA-AAAA", "12"), ("PS-AAAA-AAAA", "abcd")):
			with self.assertRaises(Exception):
				orders_api.track_order(code, digits)


class TestPlaceOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_masters()

	def test_honeypot_silently_drops_bots(self):
		result = orders_api.place_order(
			customer_name="Bot",
			phone="+233240000030",
			verification_token="irrelevant",
			items=json.dumps([{"pack": TEST_PACK, "qty": 1}]),
			delivery_zone=TEST_ZONE,
			delivery_address="1 Test Street",
			hp="i am a bot",
		)

		# Looks like success to the bot, but nothing was written.
		self.assertTrue(result["ok"])
		self.assertIsNone(result["order_id"])
		self.assertFalse(frappe.db.exists("Shito Order", {"phone": "+233240000030"}))

	def test_order_requires_phone_verification(self):
		with self.assertRaises(frappe.ValidationError):
			orders_api.place_order(
				customer_name="Unverified",
				phone="+233240000031",
				verification_token="not-a-real-token",
				items=json.dumps([{"pack": TEST_PACK, "qty": 1}]),
				delivery_zone=TEST_ZONE,
				delivery_address="1 Test Street",
			)
