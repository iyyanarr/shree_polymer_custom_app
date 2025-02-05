# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns, data = get_columns(filters), get_datas(filters)
	return columns, data

def get_columns(filters):
	c__ = []
	c__.append(_('ID')+':Link/Stock Entry:160')
	c__.append(_('Posting Date')+':Date:130')
	c__.append(_('Default Source Warehouse')+':Link/Warehouse:200')
	c__.append(_('Default Target Warehouse')+':Link/Warehouse:200')
	c__.append(_('SPP Batch Number')+':Data:140')
	c__.append(_('Item Code')+':Link/Item:100')
	c__.append(_('Item Group')+':Link/Item Group:120')
	c__.append(_('Qty')+':Float:120')
	c__.append(_('UOM')+':Data:100')
	c__.append(_('Batch No')+':Link/Batch:160')
	c__.append(_('Rate')+':Currency:80')
	c__.append(_('Amount')+':Currency:80')
	c__.append({"label": _("Source Document Type"), 
				"fieldname": "voucher_type",
				"field_type":"Link",
				"options":"DocType", 
				"width": 200})
	c__.append({"label": _("Source Document name"),
				 "fieldname": "voucher_no",
				 "fieldtype": "Dynamic Link",
				 "options": "voucher_type",
				 "width": 200})
	return c__

def get_datas(filters):
	condition = ""
	item_condition = ""
	result = []
	if filters.get('vendor_category'):
		price_list = frappe.db.get_value("Vendor Category",filters.get('vendor_category'),"price_list")
		if filters.get('from_date'):
			condition += f" AND DATE(SE.posting_date) >= '{filters.get('from_date')}' "
		if filters.get('to_date'):
			condition += f" AND DATE(SE.posting_date) <= '{filters.get('to_date')}' "
		# if filters.get('default_source_warehouse'):
		# 	condition += f" AND SED.s_warehouse = '{filters.get('default_source_warehouse')}' " 
		if filters.get('item'):
			item_condition += f" AND SED.item_code = '{filters.get('item')}' " 
		if not filters.get('default_source_warehouse'):
			source_warehouse = frappe.db.get_all("Vendor Warehouse",{"parent":filters.get('vendor_category'),"parenttype":"Vendor Category"},['vendor'])
			if source_warehouse:
				for war in source_warehouse:
					stock_entry_ids_condition = ""
					stock_entries = frappe.db.sql(f""" SELECT DISTINCT SE.name FROM `tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED ON SE.name = SED.parent
														WHERE SED.s_warehouse IN ( SELECT AWH.name FROM `tabWarehouse` AWH
																			WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = '{war.vendor}') 
																				AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = '{war.vendor}'))
														AND SE.stock_entry_type = 'Manufacture' AND SED.s_warehouse IS NOT NULL AND SED.s_warehouse != "" 
														AND SE.docstatus = 1 {condition} """,as_dict = 1)
					if stock_entries:
						for ids in stock_entries:
							stock_entry_ids_condition += f"'{ids.name}',"
						stock_entry_ids_condition = stock_entry_ids_condition[:-1]
						query = f""" SELECT SE.name id,SED.stock_uom uom,SED.source_ref_document voucher_type,
									SED.source_ref_id voucher_no,DATE(SE.posting_date) posting_date,
										(SELECT SSED.s_warehouse FROM `tabStock Entry Detail` SSED
											WHERE SSED.parent = SE.name AND SSED.s_warehouse IS NOT NULL AND SSED.s_warehouse != "" LIMIT 1)
									default_source_warehouse,
									SED.t_warehouse default_target_warehouse,
									SED.spp_batch_number,SED.item_code,I.item_group,SED.qty,SED.batch_no,
										CASE WHEN IP.price_list_rate IS NOT NULL AND IP.price_list_rate !=0 
											THEN IP.price_list_rate ELSE 0 
									END rate ,
										CASE WHEN IP.price_list_rate IS NOT NULL AND IP.price_list_rate !=0 
											THEN IP.price_list_rate * SED.qty ELSE 0
									END amount 
									FROM 
										`tabStock Entry` SE
										INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
										INNER JOIN `tabItem` I ON I.name = SED.item_code
										LEFT JOIN `tabItem Price` IP ON IP.item_code = SED.item_code AND IP.price_list = '{price_list}'
									WHERE
										SE.docstatus = 1  AND SED.is_finished_item = 1 AND SED.t_warehouse IS NOT NULL 
										AND SE.name IN ({stock_entry_ids_condition}) {item_condition} """
						# frappe.log_error(title="sorce warehouse query",message=query)
						result.extend(frappe.db.sql(query,as_dict = 1))
			else:
				frappe.throw(f" There is no warehouse mapped for this category <b>{filters.get('vendor_category')}</b>..!")
		else:
			stock_entry_ids_condition = ""
			stock_entries = frappe.db.sql(f""" SELECT DISTINCT SE.name FROM `tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED ON SE.name = SED.parent
												WHERE SED.s_warehouse = '{filters.get('default_source_warehouse')}'
													AND SE.stock_entry_type = 'Manufacture' AND SED.s_warehouse IS NOT NULL AND SED.s_warehouse != "" 
													AND SE.docstatus = 1 {condition} """,as_dict = 1)
			if stock_entries:
				for ids in stock_entries:
					stock_entry_ids_condition += f"'{ids.name}',"
				stock_entry_ids_condition = stock_entry_ids_condition[:-1]
				query = f""" SELECT SE.name id,SED.stock_uom uom,SED.source_ref_document voucher_type,
							SED.source_ref_id voucher_no,DATE(SE.posting_date) posting_date,
								(SELECT SSED.s_warehouse FROM `tabStock Entry Detail` SSED
									WHERE SSED.parent = SE.name AND SSED.s_warehouse IS NOT NULL AND SSED.s_warehouse != "" LIMIT 1)
							default_source_warehouse,
							SED.t_warehouse default_target_warehouse,
							SED.spp_batch_number,SED.item_code,I.item_group,SED.qty,SED.batch_no,
								CASE WHEN IP.price_list_rate IS NOT NULL AND IP.price_list_rate !=0 
									THEN IP.price_list_rate ELSE 0 
							END rate ,
								CASE WHEN IP.price_list_rate IS NOT NULL AND IP.price_list_rate !=0 
									THEN IP.price_list_rate * SED.qty ELSE 0
							END amount 
							FROM 
								`tabStock Entry` SE
								INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
								INNER JOIN `tabItem` I ON I.name = SED.item_code
								LEFT JOIN `tabItem Price` IP ON IP.item_code = SED.item_code AND IP.price_list = '{price_list}'
							WHERE
								SE.docstatus = 1  AND SED.is_finished_item = 1 AND SED.t_warehouse IS NOT NULL 
								AND SE.name IN ({stock_entry_ids_condition}) {item_condition} """
				# frappe.log_error(title="sorce warehouse else query",message=query)
				result.extend(frappe.db.sql(query,as_dict = 1))
	return result













# frappe.log_error(title="stock_entries",message=stock_entries)
# frappe.log_error(title="st cond",message=f""" SELECT DISTINCT SE.name FROM `tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED ON SE.name = SED.parent
# 									WHERE SED.s_warehouse IN ( SELECT AWH.name FROM `tabWarehouse` AWH
# 														WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = '{war.vendor}') 
# 															AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = '{war.vendor}'))
# 									AND SE.stock_entry_type = 'Manufacture' AND SED.s_warehouse IS NOT NULL AND SED.s_warehouse != "" 
# 									AND SE.docstatus = 1 {condition}""")
# frappe.log_error(title="warehouse",message=frappe.db.sql(f"""SELECT AWH.name FROM `tabWarehouse` AWH
# 														WHERE AWH.lft >= (SELECT PIWH.lft FROM `tabWarehouse` PIWH WHERE PIWH.name = '{war.vendor}') 
# 															AND AWH.rgt <= (SELECT PIIWH.rgt FROM `tabWarehouse` PIIWH WHERE PIIWH.name = '{war.vendor}')"""))



# def execute(filters=None):
# 	columns, data = get_columns(filters), get_datas(filters)
# 	return columns, data

# def get_columns(filters):
# 	c__ = []
# 	c__.append(_('ID')+':Link/Stock Entry:130')
# 	c__.append(_('Deflashing ID')+':Link/Deflashing Receipt Entry:120')
# 	c__.append(_('Posting Date')+':Date:130')
# 	c__.append(_('Default Source Warehouse')+':Link/Warehouse:190')
# 	c__.append(_('Default Target Warehouse')+':Link/Warehouse:190')
# 	c__.append(_('SPP Batch Number')+':Data:140')
# 	c__.append(_('Item Code')+':Link/Item:100')
# 	c__.append(_('Item Group')+':Link/Item Group:100')
# 	c__.append(_('Qty')+':Float:120')
# 	c__.append(_('Batch No')+':Link/Batch:160')
# 	c__.append(_('Rate')+':Currency:80')
# 	c__.append(_('Amount')+':Currency:80')
# 	return c__

# def get_datas(filters):
# 	condition = ""
# 	if filters.get('from_date'):
# 		condition += f" AND DATE(SE.posting_date) >= '{filters.get('from_date')}' "
# 	if filters.get('to_date'):
# 		condition += f" AND DATE(SE.posting_date) <= '{filters.get('to_date')}' "
# 	if filters.get('default_source_warehouse'):
# 		condition += f" AND DFR.from_warehouse_id = '{filters.get('default_source_warehouse')}' " 
# 	if filters.get('item'):
# 		condition += f" AND SED.item_code = '{filters.get('item')}' " 
# 	query = f""" SELECT DFR.stock_entry_reference id,DFR.name deflashing_id,DATE(DFR.creation) posting_date,
# 	 			 DFR.from_warehouse_id default_source_warehouse,DFR.warehouse default_target_warehouse,
# 				 SED.spp_batch_number,SED.item_code,I.item_group,SED.qty,SED.batch_no,
# 				 CASE WHEN IP.price_list_rate IS NOT NULL AND IP.price_list_rate !=0 
# 				 THEN IP.price_list_rate ELSE 0 END rate ,
# 				 CASE WHEN IP.price_list_rate IS NOT NULL AND IP.price_list_rate !=0 
# 				 THEN IP.price_list_rate * SED.qty ELSE 0 END amount 
# 				 FROM 
# 					`tabDeflashing Receipt Entry` DFR 
# 					INNER JOIN `tabStock Entry` SE ON DFR.stock_entry_reference = SE.name
# 					INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 					INNER JOIN `tabItem` I ON I.name = SED.item_code
# 					LEFT JOIN `tabItem Price` IP ON IP.item_code = SED.item_code AND IP.price_list = 'Job Work'
# 				WHERE
# 				  	DFR.docstatus = 1 AND SE.docstatus = 1  AND SED.is_finished_item = 1 AND SED.t_warehouse IS NOT NULL {condition} """
# 	return frappe.db.sql(query,as_dict = 1)
