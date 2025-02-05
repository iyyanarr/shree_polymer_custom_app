// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Summary Report"] = {
	"filters": [
		{
			"fieldname":"item_code",
			"fieldtype":"Link",
			"options": "Item",
			"label":__("Item"),
		},
		// {
		// 	"fieldname":"posting_from_date",
		// 	"fieldtype":"Date",
		// 	"label":__("From Date"),
		// 	"default": frappe.datetime.add_days(frappe.datetime.get_today(), -1),
		// 	"reqd":1
		// },
		{
			"fieldname": "posting_to_date",
			"fieldtype": "Date",
			"label": __("Date"),
			"reqd":1,
			'default':frappe.datetime.nowdate()
		},
		{
			"fieldname":"item_group",
			"fieldtype":"Link",
			"options": "Item Group",
			"label":__("Stage"),
		},
		{
			"fieldname":"warehouse",
			"fieldtype":"Link",
			"options": "Warehouse",
			"label":__("Warehouse"),
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "out_qty" && data && data.out_qty > 0) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		else if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}

		return value;
	}
};

erpnext.utils.add_inventory_dimensions('Stock Balance', 8);


