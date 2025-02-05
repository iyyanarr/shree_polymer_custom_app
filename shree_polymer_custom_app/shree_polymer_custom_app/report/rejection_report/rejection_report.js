// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */
var flag = false
frappe.query_reports["Rejection Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"fieldtype": "Date",
			"label": __("Date"),
			"reqd":1,
			'default':frappe.datetime.nowdate()
		},
		{
			"fieldname":"report_type",
			"fieldtype":"Select",
			"options":"Line Rejection Report\nDeflashing Rejection Report\nFinal Rejection Report",
			"default":"Line Rejection Report",
			"label":__("Report Type")
		},
		{
			"fieldname":"t_item",
			"fieldtype":"Link",
			"options": "Item",
			"label":__("Item"),
			"get_query": () => {
					return {
						"filters": {
							"item_group": 'Mat'
						}
					}
			},
			"depends_on":"eval:doc.report_type == 'Line Rejection Report' "
		},
		{
			"fieldname":"p_item",
			"fieldtype":"Link",
			"options": "Item",
			"label":__("Item"),
			"get_query": () => {
					return {
						"filters": {
							"item_group": 'Products'
						}
					}
			},
			"depends_on":"eval:doc.report_type == 'Deflashing Rejection Report' "
		},
		{
			"fieldname":"f_item",
			"fieldtype":"Link",
			"options": "Item",
			"label":__("Item"),
			"get_query": () => {
					return {
						"filters": {
							"item_group": 'Finished Goods'
						}
					}
			},
			"depends_on":"eval:doc.report_type == 'Final Rejection Report' "
		},
		{
			"fieldname":"compound_bom_no",
			"fieldtype":"Link",
			"options": "BOM",
			"label":__("Compound BOM No"),
		},
		{
			"fieldname":"press_no",
			"fieldtype":"Link",
			"options": "Workstation",
			"label":__("Press No"),
			"get_query": () => {
				return {
					"query":"shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_press_info",
				}
			},
		},
		{
			"fieldname":"moulding_operator",
			"fieldtype":"Link",
			"options": "Employee",
			"label":__("Moulding Operator"),
			"get_query": () => {
				return {
					"query":"shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulding_operator_info",
					"filters":{
						"designation":"Moulding Supervisor"
					}
				}
			},
		},
		{
			"fieldname":"deflashing_operator",
			"fieldtype":"Link",
			"options": "Warehouse",
			"label":__("Deflashing Operator"),
			"depends_on":"eval:doc.report_type == 'Deflashing Rejection Report' || doc.report_type == 'Final Rejection Report' ",
			get_query:() =>
			{
				return {
	                "filters":{
						'parent_warehouse':"Deflashing Vendors - SPP INDIA"
					}
	            };
			}
		},
		{
			"fieldname":"mould_ref",
			"fieldtype":"Link",
			"options":"Item",
			"label":__("Mould Ref"),
			get_query:() =>
			{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulds",
	                "filters":{
						
					}
	            };
			}
		},
		{
			"fieldname":"trimming_id__operator",
			"fieldtype":"Link",
			"options": "Employee",
			"label":__("Trimming ID Operator"),
			"depends_on":"eval:doc.report_type == 'Final Rejection Report' ",
			"get_query": () => {
				return {
					"query":"shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulding_operator_info",
					"filters":{
						"designation":"ID Trimming,OD Trimming"
					}
				}
			},
			
		},
		{
			"fieldname":"trimming_od_operator",
			"fieldtype":"Link",
			"options": "Employee",
			"label":__("Trimming OD Operator"),
			"depends_on":"eval:doc.report_type == 'Final Rejection Report' ",
			"get_query": () => {
				return {
					"query":"shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulding_operator_info",
					"filters":{
						"designation":"ID Trimming,OD Trimming"
					}
				}
			},
		},
		{
			"fieldname":"show_rejection_qty",
			"fieldtype":"Check",
			"label":__("Show Rejection Qty")
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "item" && data && !data.item) {
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

