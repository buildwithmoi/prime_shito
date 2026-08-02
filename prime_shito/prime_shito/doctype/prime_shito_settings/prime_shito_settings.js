// Prime Shito Settings form.
//
// SMS is a real running cost, so the owner gets to see exactly what each
// message says, how many segments it burns and what it costs -- before any of
// it is sent to a customer.

frappe.ui.form.on("Prime Shito Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Preview SMS Templates"), () => preview_templates(frm), __("SMS"));

		frm.add_custom_button(__("Send Test SMS"), () => send_test_sms(frm), __("SMS"));

		if (frm.doc.sms_enabled && frm.doc.sms_sandbox) {
			frm.dashboard.set_headline(
				__(
					"SMS is in sandbox mode. Messages are logged with their cost but never sent. Turn off Sandbox Mode to text customers for real."
				),
				"orange"
			);
		} else if (!frm.doc.sms_enabled) {
			frm.dashboard.set_headline(
				__("SMS is off. Customers will not be notified about their orders."),
				"red"
			);
		}

		if (frm.doc.paystack_webhook_url) {
			frm.set_df_property(
				"paystack_webhook_url",
				"description",
				__("Register this exact URL in your Paystack dashboard.")
			);
		}
	},

	sms_enabled(frm) {
		frm.trigger("refresh");
	},

	sms_sandbox(frm) {
		frm.trigger("refresh");
	},
});

function preview_templates(frm) {
	frappe.call({
		method: "prime_shito.shito.notify.preview_templates",
		freeze: true,
		callback(r) {
			const rows = r.message || [];

			const total = rows.reduce((sum, row) => sum + (row.cost || 0), 0);

			const body = rows
				.map((row) => {
					const warn = row.warning
						? `<div class="text-danger small mt-1">⚠ ${frappe.utils.escape_html(row.warning)}</div>`
						: "";
					const badge = row.encoding === "GSM-7" ? "green" : "red";

					return `
						<div style="padding:10px 0;border-bottom:1px solid var(--border-color)">
							<div class="d-flex justify-content-between">
								<b>${frappe.utils.escape_html(row.label)}</b>
								<span>
									<span class="indicator-pill ${badge}">${row.encoding}</span>
									<span class="text-muted small">
										${row.characters} chars · ${row.segments} segment(s) · GHS ${row.cost.toFixed(2)}
									</span>
								</span>
							</div>
							<div class="text-muted" style="white-space:pre-wrap;margin-top:4px">${frappe.utils.escape_html(
								row.message
							)}</div>
							${warn}
						</div>`;
				})
				.join("");

			new frappe.ui.Dialog({
				title: __("SMS Template Preview"),
				size: "large",
				fields: [
					{
						fieldtype: "HTML",
						options: `
							<p class="text-muted">
								${__("Rendered against your most recent order. Cost is per message sent.")}
							</p>
							${body}
							<p class="mt-3"><b>${__("One of each")}: GHS ${total.toFixed(2)}</b></p>`,
					},
				],
			}).show();
		},
	});
}

function send_test_sms(frm) {
	if (!frm.doc.sms_enabled) {
		frappe.msgprint(__("Turn on Enable SMS first."));
		return;
	}

	frappe.prompt(
		[
			{
				fieldname: "phone",
				label: __("Your phone number"),
				fieldtype: "Data",
				reqd: 1,
				description: __("Ghanaian mobile number, e.g. 0244123456"),
			},
		],
		(values) => {
			frappe.call({
				method: "prime_shito.shito.notify.send_test_sms",
				args: { phone: values.phone },
				freeze: true,
				callback(r) {
					const res = r.message || {};
					frappe.msgprint({
						title: res.sent ? __("Sent") : __("Not sent"),
						indicator: res.sent ? "green" : "orange",
						message: res.detail,
					});
				},
			});
		},
		__("Send Test SMS"),
		__("Send")
	);
}
