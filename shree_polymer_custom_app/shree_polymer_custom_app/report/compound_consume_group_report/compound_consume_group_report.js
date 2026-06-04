// Copyright (c) 2026, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Compound Consume Group Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"fieldtype": "Date",
			"label": __("Date"),
			"default": frappe.datetime.nowdate()
		},
		{
			"fieldname": "shift",
			"fieldtype": "Link",
			"options": "Shift Type",
			"label": __("Shift")
		},
		{
			"fieldname": "press_no",
			"fieldtype": "Link",
			"options": "Workstation",
			"label": __("Press"),
			get_query: function () {
				return {
					"query": "shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_group_report.compound_consume_group_report.get_filter_pressno",
					"filters": {}
				};
			}
		},
		{
			"fieldname": "product_ref",
			"fieldtype": "Link",
			"options": "Item",
			"label": __("Product Ref"),
			get_query: function () {
				return {
					"query": "shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_group_report.compound_consume_group_report.get_filter_product_ref",
					"filters": {}
				};
			}
		},
		{
			"fieldname": "mould_number",
			"fieldtype": "Link",
			"options": "Item",
			"label": __("Mould Number"),
			get_query: function () {
				return {
					"query": "shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_group_report.compound_consume_group_report.get_filter_mould_number",
					"filters": {}
				};
			}
		},
		{
			"fieldname": "compound_ref",
			"fieldtype": "Link",
			"options": "Item",
			"label": __("Compound Ref"),
			get_query: function () {
				return {
					"query": "shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_group_report.compound_consume_group_report.get_filter_compound_ref",
					"filters": {}
				};
			}
		}
	],

	"onload": function (report) {
		report.page.add_inner_button(__("Print Report"), function () {
			const filters = report.get_filter_values(true);
			frappe.call({
				method: "shree_polymer_custom_app.shree_polymer_custom_app.report.compound_consume_group_report.compound_consume_group_report.get_print_html",
				args: { filters: filters },
				freeze: true,
				freeze_message: __("Preparing print..."),
				callback: function (r) {
					if (!r || !r.message) {
						frappe.msgprint(__("Unable to build print preview."));
						return;
					}
					const win = window.open("", "_blank");
					if (!win) {
						frappe.msgprint(__("Pop-up blocked. Allow pop-ups for this site to print."));
						return;
					}
					win.document.open();
					win.document.write(r.message);
					win.document.close();
					win.focus();
					setTimeout(function () { win.print(); }, 400);
				}
			});
		});
	}
};
