"""Order state machine.

There are two ways an order changes state and they cannot share one mechanism:

  * A human clicking Approve in Desk goes through the Frappe Workflow, which
    checks `Workflow Transition.allowed` against `frappe.session.user`.
  * A payment webhook or the expiry scheduler runs as Guest or Administrator
    with no workflow role, so `apply_workflow()` would refuse them.

Rather than weaken the workflow's role checks, machine transitions go through
`transition()` here. ALLOWED mirrors the Workflow record's transitions, and
`test_state.py` asserts the two never drift apart.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

# States
PENDING_PAYMENT = "Pending Payment"
AWAITING_APPROVAL = "Awaiting Approval"
APPROVED = "Approved"
OUT_FOR_DELIVERY = "Out for Delivery"
COMPLETED = "Completed"
CANCELLED = "Cancelled"
EXPIRED = "Expired"

ALL_STATES = (
	PENDING_PAYMENT,
	AWAITING_APPROVAL,
	APPROVED,
	OUT_FOR_DELIVERY,
	COMPLETED,
	CANCELLED,
	EXPIRED,
)

# States an order can still be worked on from.
OPEN_STATES = (PENDING_PAYMENT, AWAITING_APPROVAL, APPROVED, OUT_FOR_DELIVERY)

# States that mean the customer will not receive anything.
DEAD_STATES = (CANCELLED, EXPIRED)

ALLOWED: dict[str, set[str]] = {
	PENDING_PAYMENT: {AWAITING_APPROVAL, EXPIRED, CANCELLED},
	AWAITING_APPROVAL: {APPROVED, CANCELLED},
	APPROVED: {OUT_FOR_DELIVERY, CANCELLED},
	OUT_FOR_DELIVERY: {COMPLETED, CANCELLED},
	COMPLETED: set(),
	# A late payment can arrive after expiry, so Expired must be able to rejoin
	# the flow. Cancelled is final -- staff cancelled it deliberately.
	EXPIRED: {AWAITING_APPROVAL},
	CANCELLED: set(),
}

# Timestamp stamped when an order enters each state.
STATE_TIMESTAMP = {
	AWAITING_APPROVAL: "confirmed_at",
	APPROVED: "approved_at",
	OUT_FOR_DELIVERY: "dispatched_at",
	COMPLETED: "delivered_at",
	CANCELLED: "cancelled_at",
}


class IllegalTransition(frappe.ValidationError):
	pass


def can_transition(from_state: str, to_state: str) -> bool:
	return to_state in ALLOWED.get(from_state, set())


def transition(order, to_state: str, *, actor: str = "system", reason: str | None = None) -> bool:
	"""Move an order to `to_state`, bypassing workflow role checks.

	For code paths with no user context: payment callbacks, the expiry job,
	order placement. Human actions in Desk use the Workflow instead.

	Returns False if the order is already in `to_state` (idempotent, so a
	retried webhook does not double-fire notifications).
	"""
	if isinstance(order, str):
		order = frappe.get_doc("Shito Order", order)

	current = order.workflow_state

	if current == to_state:
		return False

	if to_state not in ALL_STATES:
		frappe.throw(_("Unknown order state: {0}").format(to_state), IllegalTransition)

	if not can_transition(current, to_state):
		frappe.throw(
			_("An order cannot go from {0} to {1}.").format(current, to_state),
			IllegalTransition,
		)

	order.workflow_state = to_state

	stamp = STATE_TIMESTAMP.get(to_state)
	if stamp and not order.get(stamp):
		order.set(stamp, now_datetime())

	if to_state == CANCELLED and reason:
		order.cancellation_reason = reason

	order.flags.ignore_permissions = True

	# Frappe validates every workflow move against the *session user's* roles.
	# These callers have none -- a payment webhook runs as Guest, the expiry job
	# as whoever the worker happens to be -- so the save is performed as
	# Administrator, who holds every role. This is semantically honest: the
	# system, not a person, is making the change, and the comment written below
	# records that.
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		order.save(ignore_permissions=True)
	finally:
		frappe.set_user(original_user)

	note = _("Status changed from {0} to {1} by {2}").format(current, to_state, actor)
	if reason:
		note += f": {reason}"
	order.add_comment("Info", note)

	return True
