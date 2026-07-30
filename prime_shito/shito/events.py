"""Document event handlers wired in hooks.py."""

import frappe

from prime_shito.shito import notify


def on_order_update(doc, method=None):
	"""Send the status SMS when an order changes state.

	Lives here rather than in the controller so that a workflow action taken in
	Desk and a machine transition from `shito.state` both notify through one
	path. Diffing against the pre-save document means a plain edit (fixing a
	typo in an address, say) does not re-text the customer.
	"""
	before = doc.get_doc_before_save()

	if not before:
		# Insert. The placing endpoint sends the first message itself, because
		# it can say something more useful than a generic status line.
		return

	if before.workflow_state == doc.workflow_state:
		return

	notify.notify_state_change(doc, doc.workflow_state)
