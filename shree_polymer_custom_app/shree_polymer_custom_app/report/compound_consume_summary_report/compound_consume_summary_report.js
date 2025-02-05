// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Compound Consume Summary Report"] = {
	"filters": [
		{
			"fieldname":"date",
			"fieldtype":"Date",
			"label":__("Date"),
			"default":frappe.datetime.nowdate()
		},
		// {
		// 	"fieldname":"shift",
		// 	"fieldtype":"Select",
		// 	"options":"\n1\n2\n3",
		// 	"label":__("Shift")
		// },
		{
			"fieldname":"shift",
			"fieldtype":"Link",
			"options":"Shift Type",
			"label":__("Shift")
		},
		{
			"fieldname":"compound_ref",
			"fieldtype":"Link",
			"options":"Item",
			"label":__("Compound Ref"),
			get_query:function(compound_ref)
			{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_summary_report.compound_consume_summary_report.get_filter_compound_ref",
	                "filters":{
						
					}
	            };
			}
		}
	],
	"onload": function (report) {
		report.page.add_inner_button(__("Send Report"), function () {
			var dialog = new frappe.ui.Dialog({
				title: "Share Report",
				fields: [
					{
						"fieldname": "email",
						"fieldtype": "Data",
						"label": "Enter Email ID",
						"description": "* Enter each email in comma(,) separate."
					}
				]
			});
			dialog.set_primary_action(__('Send'), function () {
				var values = dialog.get_values();
				if (!values.email) {
					show_alert('There is no email id found , Please type <b>To</b> email from the dialog', 5);
				}
				else {
					dialog.hide()
					get_file_attachment(values.email)
				}
			});
			dialog.show();
		})
		function get_file_attachment(email_ids) {
			 frappe.call({
				method: 'frappe.core.doctype.access_log.access_log.make_access_log',
				args: {
					doctype: '',
					report_name: "Compound Consume Report",
					filters: {},
					file_type: "Excel",
					method: "Export"
				},
				freeze: true,
				callback: function (r) { download_file(email_ids) }
			});
			function download_file(email_ids) {
				let filters = report.get_filter_values(true);
				if (frappe.urllib.get_dict("prepared_report_name")) {
					filters = Object.assign(
						frappe.urllib.get_dict("prepared_report_name"),
						filters
					);
				}
				const visible_idx = report.datatable.bodyRenderer.visibleRowIndices;
				if (visible_idx.length + 1 === report.data.length) {
					visible_idx.push(visible_idx.length);
				}
				let include_indentation;
				const args = {
					report_name: report.report_name,
					custom_columns: report.custom_columns.length ? report.custom_columns : [],
					file_format_type: 'Excel',
					filters: filters,
					visible_idx,
					include_indentation,
					email_ids: email_ids
				};
				// open_url_post(frappe.request.url, args);
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_summary_report.compound_consume_summary_report.get_file_data',
					args: args,
					freeze: true,
					callback: function (r) {
						if (r && r.status == 'success') {
							frappe.msgprint(r.message)
						}
						else if (r && r.status == 'failed') {
							frappe.msgprint(r.message)
						}
						else {
							frappe.msgprint("Not able to fetch report data..!")
						}
					}
				});
			}
		}
	}
};
