"""Staff-only endpoints.

Nothing here is guest-accessible. Every method runs the caller through the same
Workflow role checks Desk applies, so a Dispatch user cannot approve orders by
calling the API directly.
"""

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow

MAX_BULK = 100


@frappe.whitelist(methods=["POST"])
def bulk_workflow_action(docnames: str, action: str) -> dict:
	"""Apply one workflow action to several orders.

	Uses `apply_workflow`, not the internal state machine, precisely so the
	caller's roles are enforced. Each order is committed independently: a
	selection spanning several states is normal, and one order that cannot move
	must not roll back the ones that can.
	"""
	names = frappe.parse_json(docnames)

	if not isinstance(names, list) or not names:
		frappe.throw(_("Select at least one order."))

	if len(names) > MAX_BULK:
		frappe.throw(_("Please select {0} orders or fewer at a time.").format(MAX_BULK))

	updated = 0
	failed = []

	for name in names:
		try:
			doc = frappe.get_doc("Shito Order", name)
			doc.check_permission("write")
			apply_workflow(doc, action)
			frappe.db.commit()
			updated += 1
		except Exception as exc:
			frappe.db.rollback()
			failed.append({"name": name, "reason": str(exc)[:200]})

	return {"updated": updated, "failed": failed}


@frappe.whitelist()
def get_order_stats() -> dict:
	"""Headline numbers, for anywhere a Number Card will not fit."""
	frappe.only_for(("Shito Manager", "Shito Sales", "System Manager"))

	live = ("not in", ["Cancelled", "Expired"])

	return {
		"awaiting_approval": frappe.db.count("Shito Order", {"workflow_state": "Awaiting Approval"}),
		"out_for_delivery": frappe.db.count("Shito Order", {"workflow_state": "Out for Delivery"}),
		"unpaid": frappe.db.count("Shito Order", {"payment_status": "Unpaid", "workflow_state": live}),
		"customers": frappe.db.count("Shito Customer"),
	}
