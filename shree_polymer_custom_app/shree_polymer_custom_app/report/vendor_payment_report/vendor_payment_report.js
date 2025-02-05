// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vendor Payment Report"] = {
	"filters": [
			{
				label:__("Vendor Category"),
				fieldname:"vendor_category",
				fieldtype:"Link",
				options:"Vendor Category",
				reqd:1	
			},	
			{
				label:__("From Date"),
				fieldname:"from_date",
				fieldtype:"Date",
				'default':frappe.datetime.nowdate()	
			},
			{
				label:__("To Date"),
				fieldname:"to_date",
				fieldtype:"Date",
				'default':frappe.datetime.nowdate()	
			},
			{
				label:__("Default Source Warehouse"),
				fieldname:"default_source_warehouse",
				fieldtype:"Link",
				options:"Warehouse"	
			},
			{
				label:__("Item Code"),
				fieldname:"item",
				fieldtype:"Link",
				options:"Item"	
			}
	]
};

