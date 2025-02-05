// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */
var flag = false
frappe.query_reports["Compound Inspection Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"fieldtype":"Date",
			"label":__("From Date"),
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			"reqd":1
		},
		{
			"fieldname":"to_date",
			"fieldtype":"Date",
			"label":__("To Date"),
			"default":frappe.datetime.nowdate(),
			"reqd":1
		},
		{
			"fieldname":"compound_ref",
			"fieldtype":"Link",
			"options":"Item",
			"label":__("Compound Ref"),
			get_query:function(compound_ref)
			{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.compound_inspection_report.compound_inspection_report.get_filter_compound_ref",
	                "filters":{
						"item_group":'Compound'
					}
	            };
			}
		},
		{
			"fieldname":"batch_no",
			"fieldtype":"Data",
			"label":__("Batch No")
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "date" && data && !data.date) {
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

