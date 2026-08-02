import frappe
from frappe.tests import IntegrationTestCase

from prime_shito.shito import gsm, notify

# Keeps Frappe's recursive test-record generation away from ERPNext, whose
# tests/utils.py builds BootStrapTestData at import time.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Shito Order", "DocType"]

TEST_PHONE = "+233240000700"


def _settings():
	return frappe.get_cached_doc("Prime Shito Settings")


class TestSmsSending(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shito SMS Message", {"to_phone": TEST_PHONE})

		settings = frappe.get_single("Prime Shito Settings")
		settings.sms_enabled = 1
		# Never send for real from a test run.
		settings.sms_sandbox = 1
		settings.sms_cost_per_segment = 0.03
		settings.save(ignore_permissions=True)
		frappe.db.commit()

	def test_sandbox_logs_without_sending(self):
		self.assertTrue(notify.send_sms(TEST_PHONE, "Prime Shito: test message", template_key="t"))

		log = frappe.get_last_doc("Shito SMS Message", filters={"to_phone": TEST_PHONE})
		self.assertEqual(log.status, "Sandbox")
		self.assertEqual(log.encoding, "GSM-7")
		self.assertEqual(log.segments, 1)

	def test_cost_tracks_segments_not_messages(self):
		"""The bill is per segment, so a long message must cost more."""
		notify.send_sms(TEST_PHONE, "a" * 400, template_key="long")

		log = frappe.get_last_doc("Shito SMS Message", filters={"to_phone": TEST_PHONE})
		self.assertEqual(log.segments, 3)
		self.assertAlmostEqual(log.cost, 0.09, places=2)

	def test_cedi_sign_is_recorded_as_expensive(self):
		"""The exact mistake the GSM-7 guard exists to catch, priced out."""
		notify.send_sms(TEST_PHONE, "Total is 120.00 cedis", template_key="cheap")
		cheap = frappe.get_last_doc("Shito SMS Message", filters={"to_phone": TEST_PHONE})

		notify.send_sms(TEST_PHONE, "Total is ₵120.00", template_key="pricey")
		pricey = frappe.get_last_doc("Shito SMS Message", filters={"to_phone": TEST_PHONE})

		self.assertEqual(cheap.encoding, "GSM-7")
		self.assertEqual(pricey.encoding, "UCS-2")

	def test_blocked_customer_is_suppressed(self):
		if not frappe.db.exists("Shito Customer", TEST_PHONE):
			frappe.get_doc(
				{
					"doctype": "Shito Customer",
					"phone": TEST_PHONE,
					"full_name": "Blocked Person",
					"is_blocked": 1,
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Shito Customer", TEST_PHONE, "is_blocked", 1)
		frappe.db.commit()

		self.assertFalse(notify.send_sms(TEST_PHONE, "Should not go out", template_key="t"))

		log = frappe.get_last_doc("Shito SMS Message", filters={"to_phone": TEST_PHONE})
		self.assertEqual(log.status, "Suppressed")

		frappe.db.set_value("Shito Customer", TEST_PHONE, "is_blocked", 0)
		frappe.db.commit()

	def test_sms_disabled_sends_nothing(self):
		settings = frappe.get_single("Prime Shito Settings")
		settings.sms_enabled = 0
		settings.save(ignore_permissions=True)
		frappe.db.commit()

		self.assertFalse(notify.send_sms(TEST_PHONE, "Nope", template_key="t"))
		self.assertFalse(frappe.db.exists("Shito SMS Message", {"to_phone": TEST_PHONE}))

		settings.sms_enabled = 1
		settings.save(ignore_permissions=True)
		frappe.db.commit()

	def test_invalid_number_is_dropped(self):
		self.assertFalse(notify.send_sms("not-a-number", "Hello", template_key="t"))


class TestTemplates(IntegrationTestCase):
	def test_every_shipped_template_is_gsm7(self):
		"""Default copy must not silently double the SMS bill.

		A single non-GSM-7 character cuts the segment from 160 characters to
		70, so this asserts the shipped defaults stay cheap.
		"""
		settings = _settings()

		for df in settings.meta.fields:
			if not df.fieldname.startswith("tpl_"):
				continue

			body = settings.get(df.fieldname) or ""
			if not body:
				continue

			bad = gsm.non_gsm7_characters(body)
			self.assertEqual(
				bad,
				[],
				f"{df.fieldname} contains expensive characters: {bad}",
			)

	def test_no_template_uses_the_cedi_symbol(self):
		settings = _settings()
		for df in settings.meta.fields:
			if df.fieldname.startswith("tpl_"):
				self.assertNotIn("₵", settings.get(df.fieldname) or "")

	def test_preview_renders_every_template(self):
		frappe.set_user("Administrator")
		rows = notify.preview_templates()

		self.assertTrue(rows)
		for row in rows:
			self.assertTrue(row["message"], f"{row['template']} rendered empty")
			self.assertIsNone(row["warning"], f"{row['template']}: {row['warning']}")
			# Order notifications should fit one segment; more is a cost smell.
			self.assertLessEqual(row["segments"], 2, f"{row['template']} needs {row['segments']} segments")

	def test_render_survives_a_broken_template(self):
		"""An owner mid-edit must not be able to break order placement."""
		out = notify.render("{% this is not valid jinja", {"code": "X"})
		self.assertTrue(out)
