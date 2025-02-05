// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */
var flag = false
frappe.query_reports["Finished Product Report"] = {
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
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "lot_no" && data && !data.lot_no) {
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
