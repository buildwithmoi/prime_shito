// Desk list view for Shito Order.
//
// The order list is where the business is actually run, so it is tuned for
// working a queue: colour tells you the state at a glance, and the bulk actions
// cover the moves that happen dozens of times a day.

frappe.listview_settings["Shito Order"] = {
	add_fields: [
		"workflow_state",
		"payment_status",
		"payment_method",
		"grand_total",
		"tracking_code",
		"delivery_zone",
	],

	filters: [["workflow_state", "!=", "Completed"]],

	get_indicator(doc) {
		const colours = {
			"Awaiting Approval": "orange",
			Approved: "blue",
			"Out for Delivery": "purple",
			Completed: "green",
			Cancelled: "gray",
			Expired: "gray",
			"Pending Payment": "yellow",
		};

		// Unpaid completed orders are the ones that quietly cost money, so they
		// get called out rather than showing a reassuring green.
		if (doc.workflow_state === "Completed" && doc.payment_status !== "Paid") {
			return [__("Delivered, unpaid"), "red", "payment_status,!=,Paid"];
		}

		return [
			__(doc.workflow_state),
			colours[doc.workflow_state] || "gray",
			`workflow_state,=,${doc.workflow_state}`,
		];
	},

	formatters: {
		tracking_code(value) {
			return value ? `<span class="text-muted" style="font-family:monospace">${value}</span>` : "";
		},
	},

	onload(listview) {
		listview.page.add_action_item(__("Approve"), () => {
			bulk_transition(listview, "Approve", __("Approve these orders?"));
		});

		listview.page.add_action_item(__("Mark Out for Delivery"), () => {
			bulk_transition(listview, "Dispatch", __("Send these orders out for delivery?"));
		});

		listview.page.add_action_item(__("Mark Completed"), () => {
			bulk_transition(listview, "Complete", __("Mark these orders as delivered?"));
		});
	},
};

function bulk_transition(listview, action, message) {
	const docnames = listview.get_checked_items(true);

	if (!docnames.length) {
		frappe.msgprint(__("Select at least one order."));
		return;
	}

	frappe.confirm(message, () => {
		frappe.call({
			method: "prime_shito.api.admin.bulk_workflow_action",
			args: { docnames: JSON.stringify(docnames), action },
			freeze: true,
			freeze_message: __("Updating orders…"),
			callback(r) {
				const result = r.message || {};

				if (result.failed && result.failed.length) {
					// Partial success is the normal case when a selection spans
					// states, so say exactly what did and did not move rather
					// than failing the whole batch.
					frappe.msgprint({
						title: __("Some orders were not updated"),
						indicator: "orange",
						message:
							__("Updated {0}.", [result.updated]) +
							"<br><br>" +
							result.failed.map((f) => `<b>${f.name}</b>: ${f.reason}`).join("<br>"),
					});
				} else {
					frappe.show_alert({
						message: __("Updated {0} order(s)", [result.updated]),
						indicator: "green",
					});
				}

				listview.refresh();
			},
		});
	});
}
