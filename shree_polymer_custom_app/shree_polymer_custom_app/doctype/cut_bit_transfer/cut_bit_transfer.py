# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series

class CutBitTransfer(Document):

	def on_submit(self):
		create_stock_entry(self)
		self.reload()

	# def on_update(self):
	# 	spp_settings = frappe.get_single("SPP Settings")
	# 	items = self.items
	# 	for x in items:
	# 		if frappe.db.get_value("Item",x.item_code,"item_group")=="Compound":
	# 			x.ct_source_warehouse = spp_settings.default_sheeting_warehouse
	# 		else:
	# 			x.ct_source_warehouse = spp_settings.default_blanking_warehouse
	# 	self.items = items

@frappe.whitelist()
def validate_clip_barcode(batch_no,t_type,warehouse):
	print('*****************',batch_no,t_type,warehouse)
	print("Scanned barcode:", batch_no)
	spp_settings = frappe.get_single("SPP Settings")
	ct_type = "Clip"
	s_warehouse = spp_settings.default_sheeting_warehouse
	
	# Find clip mapping
	clip_mapping = frappe.db.sql(""" SELECT compound,spp_batch_number,qty FROM `tabItem Clip Mapping` CM 
								 INNER JOIN `tabSheeting Clip` SC ON SC.name = CM.sheeting_clip 
								 WHERE SC.barcode_text = %(mix_barcode)s AND CM.is_retired=0""",
								 {"mix_barcode":batch_no},as_dict=1)
	
	if clip_mapping:
		print("Found clip mapping:", clip_mapping)
		base_batch_number = clip_mapping[0].spp_batch_number.split('-')[0]
		batch_no = f"{clip_mapping[0].compound}_{base_batch_number}"
		print("Modified batch_no:", batch_no)
		
		# Get the item details directly
		batch_query = """
			SELECT 
				I.item_code,
				I.item_name,
				I.description,
				I.batch_no,
				I.stock_uom as uom,
				I.qty,
				I.warehouse,
				%(spp_batch_number)s as spp_batch_number,
				%(mix_barcode)s as mix_barcode
			FROM `tabItem Batch Stock Balance` I
			INNER JOIN `tabBatch` B ON I.batch_no = B.name 
			WHERE I.item_code = %(item_code)s
			AND I.qty > 0 
			AND I.warehouse = %(warehouse)s
			AND B.expiry_date >= curdate()
		"""
		
		# Try primary warehouse
		params = {
			'item_code': clip_mapping[0].compound,
			'spp_batch_number': clip_mapping[0].spp_batch_number,
			'mix_barcode': batch_no,
			'warehouse': s_warehouse
		}
		
		print("Primary Query Params:", params)
		st_details = frappe.db.sql(batch_query, params, as_dict=1)
		print("Primary Warehouse Results:", st_details)
		
		# If no results, try unit 2 warehouse
		if not st_details:
			params['warehouse'] = spp_settings.unit_2_warehouse
			print("Unit 2 Query Params:", params)
			st_details = frappe.db.sql(batch_query, params, as_dict=1)
			print("Unit 2 Warehouse Results:", st_details)
		
		if st_details:
			st_details[0].qty = clip_mapping[0].qty
			return {"status":"Success", "stock":st_details, "source_warehouse":s_warehouse}
		else:
			return {"status":"Failed", "message":f"No available stock found for item {clip_mapping[0].compound} in warehouses"}

	return {"status":"Failed", "message":f"Scanned {ct_type} <b>{batch_no}</b> not exist in the <b>{s_warehouse}</b>"}

# def create_stock_entry(mt_doc):
# 	spp_settings = frappe.get_single("SPP Settings")
# 	stock_entry = frappe.new_doc("Stock Entry")
# 	stock_entry.purpose = "Material Issue"
# 	stock_entry.company = "SPP"
# 	stock_entry.naming_series = "MAT-STE-.YYYY.-"
# 	stock_entry.stock_entry_type = "Material Issue"
# 	# accept 0 qty as well
# 	is_allowed = 0
# 	# stock_entry.from_warehouse = mt_doc.source_warehouse
# 	stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse
# 	for x in mt_doc.items:
# 		r_batchno = x.batch_no
# 		ct_batch = "Cutbit_"+x.item_code
# 		cb_batch = frappe.db.get_all("Batch",filters={"batch_id":ct_batch})
# 		if cb_batch:
# 			r_batchno = "Cutbit_"+x.item_code
# 			is_allowed = 1
# 		ct_source_warehouse = spp_settings.default_blanking_warehouse
# 		if frappe.db.get_value("Item",x.item_code,"item_group")=="Compound":
# 			ct_source_warehouse = spp_settings.default_sheeting_warehouse
# 		if frappe.db.get_value("Item",x.item_code,"item_group")== spp_settings.blanking_item_group:
# 			ct_source_warehouse = spp_settings.unit_2_warehouse
# 		stock_entry.append("items",{
# 		"item_code":x.item_code,
# 		"t_warehouse":spp_settings.default_cut_bit_warehouse,
# 		"s_warehouse":ct_source_warehouse,
# 		"stock_uom": "Kg",
# 		"to_uom": "Kg",
# 		"uom": "Kg",
# 		"is_finished_item":0,
# 		"transfer_qty":x.qty,
# 		"qty":x.qty,
# 		"spp_batch_number":x.spp_batch_no,
# 		"batch_no":x.batch_no,
# 		"mix_barcode":x.scan_barcode
	
# 		})
# 	if is_allowed==0:
# 		stock_entry.purpose = "Material Transfer"
# 		stock_entry.stock_entry_type = "Material Transfer"
# 	stock_entry.docstatus = 1
# 	stock_entry.save(ignore_permissions=True)
# 	for x in mt_doc.items:
# 		if frappe.db.get_value("Item",x.item_code,"item_group")== spp_settings.blanking_item_group:
# 			check_item_bin = frappe.db.get_all("Item Bin Mapping",filters={"compound":x.item_code,"is_retired":0},fields=['name','qty'])
# 			if check_item_bin:
# 				if check_item_bin[0].qty == x.qty:
# 					frappe.db.set_value("Item Bin Mapping",check_item_bin[0].name,"is_retired",1)
# 				else:
# 					if check_item_bin[0].qty > x.qty:
# 						frappe.db.set_value("Item Bin Mapping",check_item_bin[0].name,"qty",check_item_bin[0].qty-x.qty)
# 				frappe.db.commit()
# 	stock_entry_issue = frappe.new_doc("Stock Entry")
# 	stock_entry_issue.purpose = "Material Receipt"
# 	stock_entry_issue.company = "SPP"
# 	stock_entry_issue.naming_series = "MAT-STE-.YYYY.-"
# 	stock_entry_issue.stock_entry_type = "Material Receipt"
# 	# stock_entry_issue.from_warehouse = mt_doc.source_warehouse
# 	is_allowed = 0
# 	for x in mt_doc.items:
# 		r_batchno = x.batch_no
# 		ct_batch = "Cutbit_"+x.item_code
# 		cb_batch = frappe.db.get_all("Batch",filters={"batch_id":ct_batch})
# 		if cb_batch:
# 			is_allowed = 1
# 			r_batchno = "Cutbit_"+x.item_code
# 		stock_entry_issue.append("items",{
# 		"item_code":x.item_code,
# 		"t_warehouse":spp_settings.default_cut_bit_warehouse,
# 		# "s_warehouse":spp_settings.default_cut_bit_warehouse,
# 		"stock_uom": "Kg",
# 		"to_uom": "Kg",
# 		"uom": "Kg",
# 		"is_finished_item":0,
# 		"transfer_qty":x.qty,
# 		"qty":x.qty,
# 		"spp_batch_number":x.spp_batch_no,
# 		"batch_no":r_batchno,
# 		"mix_barcode":"CB_"+x.item_code
	
# 		})
# 	stock_entry_issue.docstatus = 1
# 	if is_allowed:
# 		stock_entry_issue.save(ignore_permissions=True)
def create_stock_entry(mt_doc):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Repack"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		
		# Get naming series
		naming_status, naming_series = get_stock_entry_naming_series(spp_settings, "Cut Bit Entry")
		if naming_status:
			stock_entry.naming_series = naming_series
			
		stock_entry.stock_entry_type = "Repack"
		stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse

		# Clear any existing serial/batch bundle references
		stock_entry.serial_and_batch_bundle = None
		
		for x in mt_doc.items:
			r_batchno = x.batch_no
			ct_batch = "Cutbit_" + x.item_code
			cb_batch = frappe.db.get_all("Batch", filters={"batch_id": ct_batch})
			
			if cb_batch:
				r_batchno = "Cutbit_" + x.item_code
			
			ct_source_warehouse = spp_settings.default_blanking_warehouse
			if frappe.db.get_value("Item", x.item_code, "item_group") == "Compound":
				ct_source_warehouse = spp_settings.default_sheeting_warehouse
			if frappe.db.get_value("Item", x.item_code, "item_group") == spp_settings.blanking_item_group:
				ct_source_warehouse = spp_settings.unit_2_warehouse
				
			# Source item
			stock_entry.append("items", {
				"item_code": x.item_code,
				"s_warehouse": ct_source_warehouse,
				"stock_uom": "Kg",
				"to_uom": "Kg",
				"uom": "Kg",
				"is_finished_item": 0,
				"transfer_qty": x.qty,
				"qty": x.qty,
				# Clear serial and batch fields
				"serial_no": None,
				"batch_no": None,
				"serial_and_batch_bundle": None
			})

			# Target item
			stock_entry.append("items", {
				"item_code": x.item_code,
				"t_warehouse": spp_settings.default_cut_bit_warehouse,
				"stock_uom": "Kg",
				"to_uom": "Kg",
				"uom": "Kg",
				"is_finished_item": 0,
				"transfer_qty": x.qty,
				"qty": x.qty,
				"batch_no": r_batchno,
				"source_ref_document": mt_doc.doctype,
				"source_ref_id": mt_doc.name,
				"mix_barcode": "CB_" + x.item_code,
				# Clear serial fields
				"serial_no": None,
				"serial_and_batch_bundle": None
			})

		# Save without submit first
		stock_entry.save(ignore_permissions=True)
		
		# Now submit
		stock_entry.submit()
		
		frappe.db.set_value(mt_doc.doctype, mt_doc.name, "stock_entry_reference", stock_entry.name)
		frappe.db.commit()

		# Handle bin mapping if needed
		for x in mt_doc.items:
			if frappe.db.get_value("Item", x.item_code, "item_group") == spp_settings.blanking_item_group:
				check_item_bin = frappe.db.get_all("Item Bin Mapping", 
					filters={"compound": x.item_code, "is_retired": 0},
					fields=['name', 'qty'])
					
				if check_item_bin:
					if check_item_bin[0].qty == x.qty:
						frappe.db.set_value("Item Bin Mapping", check_item_bin[0].name, "is_retired", 1)
					elif check_item_bin[0].qty > x.qty:
						frappe.db.set_value("Item Bin Mapping", check_item_bin[0].name, "qty", check_item_bin[0].qty - x.qty)
					frappe.db.commit()
					
		return stock_entry

	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Cut Bit Transfer Failed")
		frappe.db.rollback()
		frappe.throw(f"Failed to create stock entry: {str(e)}")

@frappe.whitelist()
def get_process_based_employess(doctype, txt, searchfield, start, page_len, filters):
	condition=''
	if txt:
		condition += " and (first_name like '%"+txt+"%' OR name like '%"+txt+"%')"
	if filters.get("process"):	
		desgn_list = frappe.db.get_all("SPP Designation Mapping",filters={"spp_process":filters.get("process")},fields=['designation'])
		if desgn_list:
			rl_list = ""
			for x in desgn_list:
				rl_list+="'"+x.designation+"',"
			rl_list = rl_list[:-1]
			return frappe.db.sql('''SELECT name,CONCAT(first_name,' ',last_name) as description  FROM `tabEmployee` WHERE status='Active' AND designation IN({roles}) {condition}'''.format(condition=condition,roles=rl_list))

	return []