// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Material Delayed Report"] = {
	"filters": [
		{
			"fieldname":"item_code",
			"fieldtype":"Link",
			"options": "Item",
			"label":__("Item"),
		},
		{
			"fieldname": "issue_date",
			"fieldtype": "Date",
			"label": __("Issued Date"),
			"reqd":1,
			'default':frappe.datetime.nowdate()
		},
		{
			"label":__("Warehouse"),
			"fieldname":"warehouse",
			"fieldtype":"Link",
			"options":"Warehouse",
			"get_query":() =>{
				return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.material_delayed_report.material_delayed_report.get_filter_subcontractor",
	            };
			}

		},
		{
			"fieldname":"batch_no",
			"fieldtype":"Link",
			"options": "Batch",
			"label":__("Batch"),
		},
		{
			"fieldname":"spp_batch_no",
			"fieldtype":"Data",
			"label":__("SPP Batch No"),
		},
		{
			"fieldname":"item_group",
			"fieldtype":"Link",
			"options": "Item Group",
			"label":__("Stage"),
		}
	]
};

