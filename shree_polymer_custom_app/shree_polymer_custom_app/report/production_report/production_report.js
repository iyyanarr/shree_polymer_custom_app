// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */
var flag = false
frappe.query_reports["Production Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": __("From Date"),
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			"reqd":1
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": __("To Date"),
			'default':frappe.datetime.nowdate(),
			"reqd":1
		},
		{
			"fieldname":"spp_batch_no",
			"fieldtype":"Data",
			"label":__("SPP Batch No")
		},
		{
			"fieldname":"shift",
			"fieldtype":"Link",
			"options":"Shift Type",
			"label":__("Shift")
		},
		{
			"fieldname":"press",
			"fieldtype":"Link",
			"options":"Workstation",
			"label":__("Press"),
			get_query: function(txt) {
				return {
				   "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.production_report.production_report.item_filters"
			   };
		   }
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "compound_code" && data && !data.compound_code) {
			flag = true
		}
		if (flag){
			value = "<b>"+value+"</b>"
		}
		return value;
	},
	"after_datatable_render":function(s){
		flag = false
	}
};

