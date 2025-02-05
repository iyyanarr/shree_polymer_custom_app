# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_datas(filters)
	return columns, data

def get_columns():
	columns = [
		{"label": _("DC Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130,
		},
		{"label": _("Source Document Type"), "fieldname": "voucher_type", "width": 170},
			{
				"label": _("Source Document name"),
				"fieldname": "voucher_no",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 170,
			},
			{
				"label": _("DC name"),
				"fieldname": "dc_name",
				"fieldtype": "Link",
				"options": "Delivery Note",
				"width": 160,
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 180,
			},
			{
				"label": _("Batch"),
				"fieldname": "batch_no",
				"fieldtype": "Link",
				"options": "Batch",
				"width": 140,
			},
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
		{
			"label": _("SPP Batch No"),
			"fieldname": "spp_batch_no",
			"fieldtype": "Data",
			"width": 120
		},
		{
				"label": _("Stage"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
			{
				"label": _("TAT Time (days)"),
				"fieldname": "tat_time",
				"fieldtype": "Int",
				"width": 130
			},	
			{
				"label": _("Time Taken (days)"),
				"fieldname": "time_taken",
				"fieldtype": "Int",
				"width": 150
			},
	]

	return columns

def get_datas(filters):
	condition = ""
	result = []
	if filters.get('issue_date'):
		condition += f""" AND DATE(DC.posting_date) = '{filters.get('issue_date')}' """
	if filters.get('item_code'):
		condition += f""" AND DNI.item_code = '{filters.get('item_code')}' """
	if filters.get('warehouse'):
		condition += f""" AND DNI.target_warehouse = '{filters.get('warehouse')}' """
	if filters.get('batch_no'):
		condition += f""" AND DNI.batch_no = '{filters.get('batch_no')}' """
	if filters.get('spp_batch_no'):
		condition += f""" AND DNI.spp_batch_no LIKE '%{filters.get('spp_batch_no')}%' """
	if filters.get('item_group'):
		condition += f""" AND DNI.item_group = '{filters.get('item_group')}' """
	parent_warehouse = frappe.db.sql(f""" SELECT STMT.subcontractor FROM `tabSubcontractor TAT Mapping Item` STMT 
	       				WHERE STMT.parent = 'SPP Settings' """, as_dict = 1)
	if parent_warehouse:
		for wareh in parent_warehouse:
			query = f""" SELECT DISTINCT date,item_code,reference_document,reference_name,dc_name,warehouse,
								batch_no,qty,stock_uom,spp_batch_no,item_group,
								CASE 
									WHEN (tat_time IS NULL OR tat_time = '') THEN "Not Defined"
										ELSE 
											tat_time
									END as tat_time,
								CAST(DATEDIFF(now(),date) AS int) as time_taken
							FROM (SELECT DATE(DC.posting_date) date,DNI.item_code,DC.reference_document,DC.reference_name,
									DC.name dc_name,DNI.target_warehouse warehouse,DNI.batch_no,DNI.stock_uom,DNI.qty,DNI.spp_batch_no,
									DNI.item_group,STMT.no_of_days tat_time
								FROM `tabDelivery Note` DC
									INNER JOIN `tabDelivery Note Item` DNI ON DC.name = DNI.parent
									INNER JOIN `tabSubcontractor TAT Mapping Item` STMT ON STMT.parent = 'SPP Settings' 
										AND STMT.subcontractor = '{wareh.subcontractor}' 
										AND DNI.target_warehouse IN ( SELECT AWH.name FROM `tabWarehouse` AWH
											WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = STMT.subcontractor) 
												AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = STMT.subcontractor))
								WHERE 
									DNI.qty> 0 AND DC.reference_document='Material Transfer' AND DNI.is_received != 1 
									AND DC.docstatus = 1 {condition}
						UNION ALL
							SELECT DISTINCT DATE(DC.posting_date) date,DNI.item_code,DC.reference_document,DC.reference_name,
								DC.name dc_name,DNI.target_warehouse warehouse,DNI.batch_no,DNI.stock_uom,DNI.qty,DNI.spp_batch_no,
								DNI.item_group,STMT.no_of_days tat_time
							FROM `tabDelivery Note` DC
								INNER JOIN `tabDelivery Note Item` DNI ON DC.name = DNI.parent
								INNER JOIN `tabDeflashing Despatch Entry Item` DDEI ON DDEI.lot_number = DNI.scan_barcode AND DDEI.item = DNI.item_code
								INNER JOIN `tabSubcontractor TAT Mapping Item` STMT ON STMT.parent = 'SPP Settings' 
										AND STMT.subcontractor = '{wareh.subcontractor}'
										AND DNI.target_warehouse IN ( SELECT AWH.name FROM `tabWarehouse` AWH
											WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = STMT.subcontractor) 
												AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = STMT.subcontractor))
							WHERE 
								DNI.qty> 0 AND DDEI.spp_batch_no = DNI.spp_batch_no AND DDEI.batch_no = DNI.batch_no
								AND DDEI.warehouse_id = DNI.target_warehouse AND 
								DC.reference_document = 'Deflashing Despatch Entry' AND DNI.is_received != 1
								AND DC.docstatus = 1 {condition}) DEMO
						WHERE 
							CASE 
								WHEN (tat_time IS NULL OR tat_time = '') THEN 1 = 1
									ELSE 
										CAST(DATEDIFF(now(),date) AS int) > tat_time
							END """
			result.extend(frappe.db.sql(query, as_list=1))
		return result
	else:
		frappe.throw(f"The <b>Sub contractors<b> not mapped in <b>SPP Settings</b>..!")
	
@frappe.whitelist()
def get_filter_subcontractor(doctype, compound_ref, searchfield, start, page_len, filters):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.subcontractor_parent_warehouse:
			query = f""" SELECT name,lft,rgt,parent FROM `tabWarehouse` WHERE name = '{spp_settings.subcontractor_parent_warehouse}' """
			if res:= frappe.db.sql(query,as_dict=1):
				query = f""" SELECT name FROM `tabWarehouse` WHERE  lft >= {res[0].lft} and rgt <= {res[0].rgt} AND is_group != 1  """
				resp = frappe.db.sql(query)
				return resp
			else:
				frappe.msgprint(f"The <b>Parent Warehouse</b> details not found..!")
		else:
			frappe.msgprint(f"The <b>Parent Warehouse</b> not mapped in <b>SPP Settings</b>..!")
	except Exception:
		frappe.msgprint(f"Something went wrong not able to filter <b>Parent Warehouse</b>..!")
		frappe.log_error(title='Error in get_filter_subcontractor',message = frappe.get_traceback())
		

# LEFT JOIN `tabDC Item` DCR ON DCR.scan_barcode = DNI.scan_barcode AND DCR.item_code = DNI.item_code

# query = f""" SELECT date,item_code,reference_document,reference_name,dc_name,warehouse,
# 						batch_no,qty,stock_uom,spp_batch_no,item_group,
# 						CASE 
# 							WHEN (tat_time IS NULL OR tat_time = '') THEN "Not Defined"
# 								ELSE 
# 									tat_time
# 							END as tat_time,
# 						CAST(DATEDIFF(now(),date) AS int) as time_taken
# 					FROM (SELECT DATE(DC.creation) date,DNI.item_code,DC.reference_document,DC.reference_name,
# 							DC.name dc_name,DNI.target_warehouse warehouse,DNI.batch_no,DNI.stock_uom,DNI.qty,DNI.spp_batch_no,
# 							DNI.item_group,STMT.no_of_days tat_time
# 						FROM `tabDelivery Note` DC
# 							INNER JOIN `tabDelivery Note Item` DNI ON DC.name = DNI.parent
# 							LEFT JOIN `tabDC Item` DCR ON DCR.scan_barcode = DNI.scan_barcode AND DCR.item_code = DNI.item_code
# 							LEFT JOIN `tabSubcontractor TAT Mapping Item` STMT ON STMT.parent = 'SPP Settings' AND
# 								DNI.target_warehouse IN ( SELECT AWH.name FROM `tabWarehouse` AWH
# 									WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = STMT.subcontractor) 
# 										AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = STMT.subcontractor))
# 						WHERE 
# 							DNI.qty> 0 AND DC.reference_document='Material Transfer' AND DNI.is_received != 1 
# 							AND DC.docstatus = 1 {condition}
# 				UNION ALL
# 					SELECT DATE(DC.creation) date,DNI.item_code,DC.reference_document,DC.reference_name,
# 						DC.name dc_name,DNI.target_warehouse warehouse,DNI.batch_no,DNI.stock_uom,DNI.qty,DNI.spp_batch_no,
# 						DNI.item_group,STMT.no_of_days tat_time
# 					FROM `tabDelivery Note` DC
# 						INNER JOIN `tabDelivery Note Item` DNI ON DC.name = DNI.parent
# 						INNER JOIN `tabDeflashing Despatch Entry Item` DDEI ON DDEI.lot_number = DNI.scan_barcode AND DDEI.item = DNI.item_code
# 						LEFT JOIN `tabSubcontractor TAT Mapping Item` STMT ON STMT.parent = 'SPP Settings' AND
# 								DNI.target_warehouse IN ( SELECT AWH.name FROM `tabWarehouse` AWH
# 									WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = STMT.subcontractor) 
# 										AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = STMT.subcontractor))
# 					WHERE 
# 						DNI.qty> 0 AND DDEI.spp_batch_no = DNI.spp_batch_no AND DDEI.batch_no = DNI.batch_no
# 						AND DDEI.warehouse_id = DNI.target_warehouse AND 
# 						DC.reference_document = 'Deflashing Despatch Entry' AND DNI.is_received != 1
# 						AND DC.docstatus = 1 {condition}) DEMO
# 				WHERE 
# 					CASE 
# 						WHEN (tat_time IS NULL OR tat_time = '') THEN 1 = 1
# 							ELSE 
# 								CAST(DATEDIFF(now(),date) AS int) > tat_time
# 					END """
# 	return frappe.db.sql(query, as_list=1)

