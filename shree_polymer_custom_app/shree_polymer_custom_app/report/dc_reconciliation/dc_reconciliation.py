# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	columns =  [
		_("Sl No") + ":Data",
		_("DC Date") + ":Date:110",
		_("DC No") + ":Link/Delivery Note:180",
		_("Compound REF") + ":Link/Item:120",
		_("Batch Code") + ":Data:110",
		_("Mix Barcode") + ":Data:130",
		_("Quantity Kgs") + ":Data:110"]
	# if filters.get('stage') == "Batches Sent to Mixing Center":
	# 	columns.append(_("From Hold Receipt") + ":Data:140")
	columns += [
	_("Receipt Status") + ":Data:120",
	_("Receipt DC No") + ":Link/Delivery Challan Receipt:200",
	_("Receipt Date") + ":Date:120",
	_("Receipt Quantity Kgs") + ":Data:170",
	]
	return columns

@frappe.whitelist()
def item_filters(doctype, txt, searchfield, start, page_len, filters):
	search_condition = ""
	if txt:
		search_condition = " AND name like '%"+txt+"%'"
	query = "SELECT name as value,Concat(item_name,',',item_group,description) as description FROM `tabItem` WHERE disabled=0 AND item_group IN('Compound','Batch')  {condition} ORDER BY modified DESC".format(condition=search_condition)
	linked_docs = frappe.db.sql(query)
	return linked_docs
 
@frappe.whitelist()
def deflashing_item_filters(doctype, txt, searchfield, start, page_len, filters):
	search_condition = ""
	if txt:
		search_condition = " AND name like '%"+txt+"%'"
	query = "SELECT name as value,Concat(item_name,',',item_group,description) as description FROM `tabItem` WHERE disabled=0 AND item_group IN('Mat')  {condition} ORDER BY modified DESC".format(condition=search_condition)
	linked_docs = frappe.db.sql(query)
	return linked_docs

def get_data(filters):
	if filters.get('stage') == "Batches Sent to Mixing Center":
		conditions = " "
		h_conditions =""
		if filters.get("dc_date"):
			conditions += " AND DATE(DC.posting_date) = '"+filters.get("dc_date")+"'"
			h_conditions += " AND DATE(HDC.modified) = '"+filters.get("dc_date")+"'"
		if filters.get("dc_status"):
			if not filters.get("dc_status") == 'Pending': 
				conditions += " AND DC.received_status = '"+filters.get("dc_status")+"'"
				if filters.get("dc_status") == "Completed":
					h_conditions += " AND HDC.docstatus = 1 "
				else:
					h_conditions += " AND 1 != 1 "
			elif filters.get("dc_status") == 'Pending':
				conditions += " AND DC.received_status != 'Completed' AND (DC.received_status != 'Patially Completed' OR DC.received_status IS Null) " 
				h_conditions += " AND 1 != 1 "
		if filters.get("dc_no"):
			conditions += " AND DC.name = '"+filters.get("dc_no")+"'"
			h_conditions += " AND 1 != 1 "
		if filters.get("item"):
			# conditions += " AND DCI.item_code = '"+filters.get("item")+"'"
			conditions += " AND DNI.item_code = '"+filters.get("item")+"'"
			h_conditions += f""" AND HDCI.item_code = '{filters.get("item")}' """
		if filters.get("spp_batch_number"):
			# conditions += " AND DCI.spp_batch_no like '%"+filters.get("spp_batch_number")+"%'"
			conditions += " AND DNI.spp_batch_no like '%"+filters.get("spp_batch_number")+"%'"
			h_conditions += f" AND HDCI.spp_batch_no LIKE '%"+filters.get("spp_batch_number")+"%'"
		if filters.get("mixbarcode"):
			# conditions += " AND DCI.scan_barcode like '%"+filters.get("mixbarcode")+"%'"
			conditions += " AND DNI.scan_barcode like '%"+filters.get("mixbarcode")+"%'"
			h_conditions += " AND HDCI.mix_barcode like '%"+filters.get("mixbarcode")+"%'"
		if not filters.get("dc_date") and not filters.get("dc_status") and not filters.get("dc_no") and not filters.get("item") and not filters.get("spp_batch_number") and not filters.get("mixbarcode"):
			conditions += " AND DNI.is_received != 1 "
			h_conditions += " AND 1 != 1 "
		query = """ SELECT ROW_NUMBER() OVER(ORDER BY dc_date DESC) AS sl_no,dc_date,name dc_no,item_code compound_ref,
						spp_batch_no batch_code,scan_barcode mix_barcode,ROUND(qty,3) quantity_kgs,r_status receipt_status,dcr_name receipt_dc_no,dcr_date receipt_date,ROUND(dcr_qty,3) receipt_quantity_kgs
						FROM (SELECT DC.creation sort_creation, DATE(DC.posting_date) dc_date,DC.name,
							DNI.item_code,DNI.spp_batch_no,DNI.scan_barcode,DNI.qty,'No' hold_receipt,
							CASE 
								WHEN DNI.is_received = 1 THEN 'Received'
								WHEN DNI.is_return = 1 THEN 'Returned'
								ELSE  'Not  Received'
							END as r_status,
							CASE 
								WHEN DNI.is_received = 1 THEN (SELECT RDCR.parent FROM `tabDC Item` RDCR WHERE RDCR.scan_barcode = DNI.scan_barcode AND RDCR.item_code = DNI.item_code LIMIT 1)
								WHEN DNI.is_return = 1 
									THEN DNI.dc_return_receipt_no
								ELSE  ''
							END as dcr_name,
							CASE 
								WHEN DNI.is_received = 1
									THEN (SELECT CASE
												WHEN DCHR.dc_receipt_date IS NOT NULL 
												THEN DCHR.dc_receipt_date
											ELSE
												DATE(DCHR.creation) END as receipt_date
										FROM `tabDC Item` DDCR 
											INNER JOIN `tabDelivery Challan Receipt` DCHR ON DCHR.name = DDCR.parent 
										WHERE DDCR.scan_barcode = DNI.scan_barcode AND DDCR.item_code = DNI.item_code LIMIT 1)
								WHEN DNI.is_return = 1 
									THEN DNI.dc_return_date
								ELSE  ''
							END as dcr_date,
							CASE 
								WHEN DNI.is_received = 1 
									THEN (SELECT QDCR.qty FROM `tabDC Item` QDCR 
										WHERE  QDCR.scan_barcode = DNI.scan_barcode AND QDCR.item_code = DNI.item_code LIMIT 1)
								ELSE  ''
							END as dcr_qty
						FROM `tabDelivery Note` DC
							INNER JOIN `tabDelivery Note Item` DNI ON DC.name = DNI.parent
							LEFT JOIN `tabDC Item` DCR ON DCR.scan_barcode = DNI.scan_barcode 
								AND DCR.item_code = DNI.item_code AND DCR.docstatus = 1
						WHERE DNI.qty> 0 AND DC.reference_document='Material Transfer' 
								AND DC.docstatus = 1 {conditions} 
					UNION ALL
						SELECT HDC.creation sort_creation,DATE(HDC.modified) dc_date,
								'',
								HDCI.item_code,HDCI.spp_batch_no,HDCI.mix_barcode,HDCI.qty,'Yes' hold_receipt,
									'Received'
								r_status,
									HDC.name
								dcr_name,
								CASE WHEN HDC.dc_receipt_date IS NOT NULL 
										THEN HDC.dc_receipt_date
											ELSE
												DATE(HDC.modified) END
									as dcr_date,
									HDCI.qty
								as dcr_qty
						FROM `tabDelivery Challan Receipt` HDC
							INNER JOIN `tabMixing Center Holding Item` HDCI ON HDC.name = HDCI.parent
						WHERE HDCI.qty> 0 AND HDC.hold_receipt = 1 
							AND HDC.docstatus = 1 {h_conditions} 
						) DEMO ORDER BY dc_date DESC """.format(conditions=conditions,h_conditions=h_conditions)
		resp_data = frappe.db.sql(query, as_dict=1)
		add_total_qtys(resp_data)
		return resp_data
	else:
		conditions = " "
		if filters.get("dc_date"):
			conditions += " AND DATE(DC.posting_date) = '"+filters.get("dc_date")+"'"
		if filters.get("deflash_dc_status"):
			if filters.get("deflash_dc_status") and not filters.get("deflash_dc_status") == 'Pending': 
				conditions += " AND DC.received_status = '"+filters.get("deflash_dc_status")+"'"
			elif filters.get("deflash_dc_status") == 'Pending':
				conditions += " AND DC.received_status != 'Partially Completed' AND (DC.received_status != 'Completed' OR DC.received_status IS Null)"
		if filters.get("deflash_dc_no"):
			conditions += " AND DC.name = '"+filters.get("deflash_dc_no")+"'"
		if filters.get("deflashing_item"):
			conditions += " AND DNI.item_code = '"+filters.get("deflashing_item")+"'"
		if filters.get("spp_batch_number"):
			conditions += " AND DNI.spp_batch_no like '%"+filters.get("spp_batch_number")+"%'"
		if filters.get("lot_no"):
			conditions += " AND DNI.scan_barcode like '%"+filters.get("lot_no")+"%'"
		if not filters.get("dc_date") and not filters.get("deflash_dc_status") and not filters.get("deflash_dc_no") and not filters.get("deflashing_item") and not filters.get("spp_batch_number") and not filters.get("spp_batch_number"):
			conditions += " AND DNI.is_received != 1 "
		query = f""" SELECT ROW_NUMBER() OVER(ORDER BY dc_date DESC) AS sl_no,DATE(DC.posting_date) dc_date,DC.name dc_no,
							DNI.item_code compound_ref,DNI.spp_batch_no batch_code,DNI.scan_barcode mix_barcode,ROUND(DNI.qty,3) quantity_kgs,
							CASE 
								WHEN DNI.is_received = 1 THEN 'Received'
								WHEN DNI.is_return = 1 THEN 'Returned'
								ELSE  'Not  Received'
							END as receipt_status,
							CASE 
								WHEN DNI.is_received = 1 THEN DNI.dc_receipt_no
								WHEN DNI.is_return = 1 
									THEN DNI.dc_return_receipt_no
								ELSE  ''
							END as receipt_dc_no,
							CASE 
								WHEN DNI.is_received = 1
									THEN DNI.dc_receipt_date
								WHEN DNI.is_return = 1 
									THEN DNI.dc_return_date
								ELSE  ''
							END as receipt_date,
							CASE 
								WHEN DNI.is_received = 1 
									THEN ROUND(((SELECT DFRE.product_weight + DFRE.qty FROM `tabDeflashing Receipt Entry` DFRE 
										WHERE DFRE.name = DNI.dc_receipt_no AND DFRE.docstatus = 1)),3)
								ELSE  ''
							END as receipt_quantity_kgs,DC.creation sort_creation
						FROM `tabDelivery Note` DC
							INNER JOIN `tabDelivery Note Item` DNI ON DC.name = DNI.parent
							INNER JOIN `tabDeflashing Despatch Entry Item` DDEI ON DDEI.lot_number = DNI.scan_barcode AND DDEI.item = DNI.item_code
						WHERE DNI.qty> 0 AND DDEI.spp_batch_no = DNI.spp_batch_no AND DDEI.batch_no = DNI.batch_no
						AND DDEI.warehouse_id = DNI.target_warehouse AND DC.reference_document = 'Deflashing Despatch Entry' 
						AND DC.docstatus = 1 AND DDEI.docstatus = 1 {conditions} ORDER BY dc_date DESC """
		resp_ = frappe.db.sql(query, as_dict = 1)
		add_total_qtys(resp_)
		return resp_

def add_total_qtys(resp_data):
	if resp_data:
		__total_qty = frappe.bold(round((sum(float(x.quantity_kgs) if x.quantity_kgs else 0.0 for x in resp_data)),3))
		__total_receipt_qty = frappe.bold(round((sum(float(x.receipt_quantity_kgs) if x.receipt_quantity_kgs else 0 for x in resp_data)),3))
		resp_data.append({"mix_barcode":"<b>Total</b>","quantity_kgs":__total_qty,"receipt_quantity_kgs":__total_receipt_qty})



# conditions += f""" AND CASE WHEN DC.dc_receipt_date IS NOT NULL AND DC.dc_receipt_date != '' 
			# 				  THEN DC.dc_receipt_date = '{filters.get("dc_date")}' 
			# 				  ELSE  DATE(DC.creation) = '{filters.get("dc_date")}' END """
			# h_conditions +=  f""" AND CASE WHEN HDC.dc_receipt_date IS NOT NULL AND HDC.dc_receipt_date != '' 
			# 				  THEN HDC.dc_receipt_date = '{filters.get("dc_date")}' 
			# 				  ELSE  DATE(HDC.creation) = '{filters.get("dc_date")}' END """


# query = "SELECT ROW_NUMBER() OVER(ORDER BY DC.creation DESC) AS row_num  ,DATE(DC.creation),DC.name,\
	# 		DCI.item_code,DCI.spp_batch_no,DCI.scan_barcode,DCI.qty,\
	# 		CASE \
	# 			WHEN DCI.is_received = 1 THEN 'Received'\
	# 			ELSE  'Not  Received'\
	# 		END as r_status,\
	# 		CASE \
	# 			WHEN DCI.is_received = 1 THEN (SELECT DCR.parent FROM `tabDC Item` DCR WHERE DCR.operation = DC.operation AND DCR.scan_barcode = DCI.scan_barcode AND DCR.item_code = DCI.item_code LIMIT 1)\
	# 			ELSE  ''\
	# 		END as dcr_name,\
	# 		CASE \
	# 			WHEN DCI.is_received = 1 THEN (SELECT DATE(DCR.creation) FROM `tabDC Item` DCR WHERE DCR.operation = DC.operation AND DCR.scan_barcode = DCI.scan_barcode AND DCR.item_code = DCI.item_code LIMIT 1)\
	# 			ELSE  ''\
	# 		END as dcr_date,\
	# 		CASE \
	# 			WHEN DCI.is_received = 1 THEN (SELECT DCR.qty FROM `tabDC Item` DCR WHERE DCR.operation = DC.operation AND DCR.scan_barcode = DCI.scan_barcode AND DCR.item_code = DCI.item_code LIMIT 1)\
	# 			ELSE  ''\
	# 		END as dcr_qty\
	# 		FROM `tabSPP Delivery Challan` DC\
	# 		INNER JOIN `tabMixing Center Items` DCI ON DC.name = DCI.parent\
	# 		LEFT JOIN `tabDC Item` DCR ON DCR.scan_barcode = DCI.scan_barcode AND DCR.item_code = DCI.item_code\
	# 		WHERE DCI.qty> 0 {conditions} ORDER BY DC.creation DESC\
	# 		".format(conditions=conditions)


	# query = """SELECT ROW_NUMBER() OVER(ORDER BY DC.creation DESC) AS row_num  ,DATE(DC.creation),DC.name,
	# 		DNI.item_code,DNI.spp_batch_no,DNI.scan_barcode,DNI.qty,
	# 		CASE 
	# 			WHEN DNI.is_received = 1 THEN 'Received'
	# 			ELSE  'Not  Received'
	# 		END as r_status,
	# 		CASE 
	# 			WHEN DNI.is_received = 1 THEN (SELECT DCR.parent FROM `tabDelivery Note Item` DCR WHERE DCR.scan_barcode = DNI.scan_barcode AND DCR.item_code = DNI.item_code LIMIT 1)
	# 			ELSE  ''
	# 		END as dcr_name,
	# 		CASE 
	# 			WHEN DNI.is_received = 1 THEN (SELECT DATE(DCR.creation) FROM `tabDelivery Note Item` DCR WHERE  DCR.scan_barcode = DNI.scan_barcode AND DCR.item_code = DNI.item_code LIMIT 1)
	# 			ELSE  ''
	# 		END as dcr_date,
	# 		CASE 
	# 			WHEN DNI.is_received = 1 THEN (SELECT DCR.qty FROM `tabDelivery Note Item` DCR WHERE  DCR.scan_barcode = DNI.scan_barcode AND DCR.item_code = DNI.item_code LIMIT 1)
	# 			ELSE  ''
	# 		END as dcr_qty
	# 		FROM `tabDelivery Challan Receipt` DC
	# 		INNER JOIN `tabDC Item` DCR ON DC.name = DCR.parent
	# 		LEFT JOIN `tabDelivery Note Item` DNI ON DCR.scan_barcode = DNI.scan_barcode AND DCR.item_code = DNI.item_code
	# 		WHERE DNI.qty> 0 {conditions} ORDER BY DC.creation DESC
	# 		""".format(conditions=conditions)