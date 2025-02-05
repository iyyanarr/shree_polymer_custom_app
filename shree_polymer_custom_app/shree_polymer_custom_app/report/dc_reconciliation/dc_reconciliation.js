// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["DC Reconciliation"] = {
	"filters": [
		{
			"fieldname": "stage",
			"fieldtype": "Select",
			"label": __("Stage"),
			"default": "Batches Sent to Mixing Center",
			"options":"\nBatches Sent to Mixing Center\nMat Products Sent to Deflash Vendor"
		},
		{
			"fieldname": "dc_date",
			"fieldtype": "Date",
			"label": __("DC Date"),
			// "default": frappe.datetime.nowdate()
		},
		{
			"fieldname": "deflash_dc_status",
			"fieldtype": "Select",
			"label": __("DC Status"),
			"default": "",
			"options":"\nPending\nPartially Completed\nCompleted",
			"depends_on":"eval:doc.stage == 'Mat Products Sent to Deflash Vendor' "
		},
		{
			"fieldname": "dc_status",
			"fieldtype": "Select",
			"label": __("DC Status"),
			"default": "",
			"options":"\nPending\nPartially Completed\nCompleted",
			"depends_on":"eval:doc.stage == 'Batches Sent to Mixing Center' "
		},
		{
			"fieldname": "dc_no",
			"fieldtype": "Link",
			"label": __("DC No"),
			"options":"Delivery Note",
			"depends_on":"eval:doc.stage == 'Batches Sent to Mixing Center' "

		},
		{
			"fieldname": "deflash_dc_no",
			"fieldtype": "Link",
			"label": __("DC No"),
			"options":"Delivery Note",
			"depends_on":"eval:doc.stage == 'Mat Products Sent to Deflash Vendor' "

		},
		{
			"fieldname": "item",
			"fieldtype": "Link",
			"label": __("Item"),
			"options":"Item",
			get_query: function(txt) {
				 return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.dc_reconciliation.dc_reconciliation.item_filters",
	                "filters": {
	                    
	                }
	            };
			},
			"depends_on":"eval:doc.stage == 'Batches Sent to Mixing Center' "

		},
		{
			"fieldname": "deflashing_item",
			"fieldtype": "Link",
			"label": __("Item"),
			"options":"Item",
			get_query: function(txt) {
				 return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.report.dc_reconciliation.dc_reconciliation.deflashing_item_filters",
	                "filters": {
	                    
	                }
	            };
			},
			"depends_on":"eval:doc.stage == 'Mat Products Sent to Deflash Vendor' "

		},
		{
			"fieldname": "spp_batch_number",
			"fieldtype": "Data",
			"label": __("SPP Batch Number"),
		},
		{
			"fieldname": "lot_no",
			"fieldtype": "Data",
			"label": __("Lot Number"),
			"depends_on":"eval:doc.stage == 'Mat Products Sent to Deflash Vendor' "

		},
		{
			"fieldname": "mixbarcode",
			"fieldtype": "Data",
			"label": __("Mix Barcode"),
			"depends_on":"eval:doc.stage == 'Batches Sent to Mixing Center' "

		},
	]
};
