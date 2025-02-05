// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */
var flag = false
frappe.query_reports["Summary Report"] = {
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
			"fieldname": "group_by",
			"fieldtype": "Select",
			"label": __("Group By"),
			'options':["Mat Product","Compound","Shift","Mould","Press","Operator"],
			"default":"Mat Product"
		},
		{
			"fieldname": "mould",
			"fieldtype": "Link",
			"label": __("Mould"),
			"options": "Item",
			"depends_on":"eval:doc.group_by == 'Mould'",
			get_query:() =>
			{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.summary_report.summary_report.get_moulds",
	                "filters":{
						
					}
	            };
			}
		},
		{
			"fieldname": "operator",
			"fieldtype": "Link",
			"label": __("Operator"),
			"options": "Employee",
			"depends_on":"eval:doc.group_by == 'Operator'",
			"get_query": () => {
				return {
					"query":"shree_polymer_custom_app.shree_polymer_custom_app.report.summary_report.summary_report.get_moulding_operator_info",
					"filters":{
						"designation":"Moulding Supervisor"
					}
				}
			},
		},
		{
			"fieldname":"shift",
			"fieldtype":"Link",
			"options":"Shift Type",
			"depends_on":"eval:doc.group_by == 'Shift'",
			"label":__("Shift")
		},
		{
			"fieldname": "press",
			"fieldtype": "Link",
			"label": __("Press"),
			"options": "Workstation",
			"depends_on":"eval:doc.group_by == 'Press'",
			"get_query": () => {
				return {
					"query":"shree_polymer_custom_app.shree_polymer_custom_app.report.summary_report.summary_report.get_press_info",
				}
			},
		},
		{
			"fieldname":"compound_ref",
			"fieldtype":"Link",
			"options":"Item",
			"label":__("Compound Ref"),
			"depends_on":"eval:doc.group_by == 'Compound'",
			get_query:function(compound_ref)
			{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.summary_report.summary_report.get_filter_compound_ref",
	                "filters":{
						"item_group":"Compound"
					}
	            };
			}
		},
		{
			"fieldname":"product_ref",
			"fieldtype":"Link",
			"options":"Item",
			"label":__("SPP Ref"),
			"depends_on":"eval:doc.group_by == 'Mat Product'",
			get_query:function(product_ref)
			{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.summary_report.summary_report.get_filter_product_ref",
	                "filters":{
						
					}
	            };
			}
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "spp_ref" && data && !data.spp_ref) {
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

