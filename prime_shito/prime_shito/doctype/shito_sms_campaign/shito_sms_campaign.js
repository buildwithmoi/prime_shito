// Campaign form.
//
// This is the one screen in the app that can spend a lot of money in a single
// click, so the flow is deliberately two-step: see exactly who is in scope and
// what it costs, then confirm by typing.

frappe.ui.form.on("Shito SMS Campaign", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (["Sent", "Sending"].includes(frm.doc.status)) {
			frm.dashboard.set_headline(
				__("Sent {0} · failed {1} · suppressed {2}", [
					frm.doc.sent_count || 0,
					frm.doc.failed_count || 0,
					frm.doc.suppressed_count || 0,
				]),
				frm.doc.failed_count ? "orange" : "green"
			);
			return;
		}

		frm.add_custom_button(__("Preview Recipients"), () => preview(frm)).addClass(
			"btn-default"
		);

		if (frm.doc.recipient_count > 0) {
			frm.add_custom_button(__("Send Campaign"), () => confirm_send(frm)).addClass(
				"btn-primary"
			);
		}
	},

	audience(frm) {
		// The old count belongs to the old audience; showing it against a new one
		// would be worse than showing nothing.
		reset_estimate(frm);
	},

	message(frm) {
		reset_estimate(frm);
	},
});

function reset_estimate(frm) {
	if (!frm.doc.recipient_count) return;
	frm.set_value("recipient_count", 0);
	frm.set_value("estimated_cost", 0);
	frm.set_value("segments", 0);
	frm.clear_table("recipients");
	frm.refresh_field("recipients");
}

function preview(frm) {
	frm.save().then(() =>
		frappe.call({
			method: "prime_shito.shito.campaigns.preview",
			args: { campaign_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Working out who this reaches…"),
			callback(r) {
				const d = r.message || {};
				frm.reload_doc();

				if (!d.count) {
					frappe.msgprint({
						title: __("Nobody to send to"),
						indicator: "orange",
						message: __(
							"No customer matches this audience. Only customers who opted in to marketing are ever included."
						),
					});
					return;
				}

				const warn = d.warning
					? `<p class="text-danger"><b>⚠ ${frappe.utils.escape_html(d.warning)}</b></p>`
					: "";

				frappe.msgprint({
					title: __("Campaign preview"),
					indicator: d.warning ? "orange" : "blue",
					message: `
						<p><b>${d.count}</b> ${__("recipients")}</p>
						<div style="background:var(--fg-color);border:1px solid var(--border-color);
						            border-radius:6px;padding:10px;white-space:pre-wrap;margin:8px 0">${frappe.utils.escape_html(
													d.message
												)}</div>
						<p class="text-muted small">
							${d.characters} ${__("characters")} · ${d.encoding} ·
							${d.segments} ${__("segment(s) each")}
						</p>
						${warn}
						<p><b>${__("Estimated cost")}: GHS ${(d.estimated_cost || 0).toFixed(2)}</b></p>
						<p class="text-muted small">${__("For example")}: ${d.sample.join(", ")}</p>`,
				});
			},
		})
	);
}

function confirm_send(frm) {
	const cost = (frm.doc.estimated_cost || 0).toFixed(2);

	const dialog = new frappe.ui.Dialog({
		title: __("Send this campaign?"),
		fields: [
			{
				fieldtype: "HTML",
				options: `
					<p>${__("This sends")} <b>${frm.doc.recipient_count}</b> ${__("messages")}
					${__("and costs about")} <b>GHS ${cost}</b>.</p>
					<p class="text-muted">${__("It cannot be undone once it starts.")}</p>`,
			},
			{
				fieldname: "confirm",
				fieldtype: "Data",
				label: __("Type SEND to confirm"),
				reqd: 1,
			},
		],
		primary_action_label: __("Send now"),
		primary_action(values) {
			frappe.call({
				method: "prime_shito.shito.campaigns.send",
				args: { campaign_name: frm.doc.name, confirm: values.confirm },
				freeze: true,
				callback(r) {
					dialog.hide();
					frm.reload_doc();
					frappe.show_alert({
						message: __("Queued {0} messages", [(r.message || {}).queued || 0]),
						indicator: "green",
					});
				},
			});
		},
	});

	dialog.show();
}
