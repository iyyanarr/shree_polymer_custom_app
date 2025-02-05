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
	spp_settings = frappe.get_single("SPP Settings")
	# if t_type == "Warming":
	ct_type = "Clip"
	s_warehouse = spp_settings.default_sheeting_warehouse
	clip_mapping = frappe.db.sql(""" SELECT compound,spp_batch_number,qty FROM `tabItem Clip Mapping` CM 
								 INNER JOIN `tabSheeting Clip` SC ON SC.name = CM.sheeting_clip 
								 WHERE SC.barcode_text = %(mix_barcode)s AND CM.is_retired=0""",{"mix_barcode":batch_no},as_dict=1)
	if clip_mapping:
		batch_no = clip_mapping[0].compound+"_"+clip_mapping[0].spp_batch_number.split('-')[0]

	if not clip_mapping:
		# clip_mapping = frappe.db.sql(""" SELECT compound,spp_batch_number,qty FROM `tabItem Bin Mapping` CM 
		# 							 INNER JOIN `tabBlanking Bin` SC ON SC.name = CM.blanking_bin 
		# 							 WHERE SC.barcode_text = %(mix_barcode)s AND CM.is_retired=0""",{"mix_barcode":batch_no},as_dict=1)
		clip_mapping = frappe.db.sql(""" SELECT compound,spp_batch_number,qty FROM `tabItem Bin Mapping` IBM 
									 INNER JOIN `tabAsset` A ON A.name = IBM.blanking__bin 
									 WHERE A.barcode_text = %(mix_barcode)s AND IBM.is_retired=0 """,{"mix_barcode":batch_no},as_dict=1)
		if clip_mapping:
			batch_no = clip_mapping[0].compound+"_"+clip_mapping[0].spp_batch_number.split('-')[0]
			ct_type = "Bin"
			# s_warehouse = spp_settings.default_blanking_warehouse
			s_warehouse = spp_settings.unit_2_warehouse
	stock_details = frappe.db.sql(""" SELECT S.name, SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) AND SD.t_warehouse = %(t_warehouse)s 
					  AND S.docstatus = 1  
					  ORDER BY S.creation DESC limit 1 """,{'mix_barcode':batch_no,'t_warehouse':s_warehouse},as_dict=1)
	if stock_details:
		items = stock_details[0].item_code
		s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,SD.spp_batch_number,SD.mix_barcode,\
					I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I\
					 INNER JOIN `tabBatch` B ON I.batch_no = B.name \
					 INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name\
					 WHERE I.item_code ='{item_codes}' AND  (SD.mix_barcode = '{mix_barcode}' OR SD.barcode_text = '{mix_barcode}')   AND \
					 I.qty >0 AND I.warehouse ='{warehouse}' AND B.expiry_date>=curdate() ".format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,mix_barcode=batch_no,item_codes=items,warehouse=s_warehouse)
		
		st_details = frappe.db.sql(s_query,as_dict=1)
		if not st_details:
			s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,SD.spp_batch_number,SD.mix_barcode,\
					I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I\
					 INNER JOIN `tabBatch` B ON I.batch_no = B.name \
					 INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name\
					 WHERE I.item_code ='{item_codes}' AND  (SD.mix_barcode = '{mix_barcode}' OR SD.barcode_text = '{mix_barcode}')   AND \
					 I.qty >0 AND I.warehouse ='{warehouse}' AND B.expiry_date>=curdate() ".format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,mix_barcode=batch_no,item_codes=items,warehouse=spp_settings.unit_2_warehouse)
			st_details = frappe.db.sql(s_query,as_dict=1)
		if st_details and clip_mapping:
			st_details[0].qty = clip_mapping[0].qty
		return {"status":"Success","stock":st_details,"source_warehouse":s_warehouse}

	return  {"status":"Failed","message":"Scanned "+ct_type+" <b>"+batch_no+"</b> not exist in the <b>"+s_warehouse+"</b>"}

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
	spp_settings = frappe.get_single("SPP Settings")
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = "Repack"
	stock_entry.company = "SPP"
	stock_entry.naming_series = "MAT-STE-.YYYY.-"
	""" For identifying procees name to change the naming series the field is used """
	naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Cut Bit Entry")
	if naming_status:
		stock_entry.naming_series = naming_series
	""" End """
	stock_entry.stock_entry_type = "Repack"
	# accept 0 qty as well
	is_allowed = 0
	# stock_entry.from_warehouse = mt_doc.source_warehouse
	stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse
	for x in mt_doc.items:
		r_batchno = x.batch_no
		ct_batch = "Cutbit_"+x.item_code
		cb_batch = frappe.db.get_all("Batch",filters={"batch_id":ct_batch})
		if cb_batch:
			r_batchno = "Cutbit_"+x.item_code
			is_allowed = 1
		ct_source_warehouse = spp_settings.default_blanking_warehouse
		if frappe.db.get_value("Item",x.item_code,"item_group")=="Compound":
			ct_source_warehouse = spp_settings.default_sheeting_warehouse
		if frappe.db.get_value("Item",x.item_code,"item_group")== spp_settings.blanking_item_group:
			ct_source_warehouse = spp_settings.unit_2_warehouse
		stock_entry.append("items",{
		"item_code":x.item_code,
		"s_warehouse":ct_source_warehouse,
		"stock_uom": "Kg",
		"to_uom": "Kg",
		"uom": "Kg",
		"is_finished_item":0,
		"transfer_qty":x.qty,
		"qty":x.qty,
		"spp_batch_number":x.spp_batch_no,
		"batch_no":x.batch_no,
		})
	for x in mt_doc.items:
		r_batchno = x.batch_no
		ct_batch = "Cutbit_"+x.item_code
		cb_batch = frappe.db.get_all("Batch",filters={"batch_id":ct_batch})
		if cb_batch:
			r_batchno = "Cutbit_"+x.item_code
			is_allowed = 1
		ct_source_warehouse = spp_settings.default_blanking_warehouse
		if frappe.db.get_value("Item",x.item_code,"item_group")=="Compound":
			ct_source_warehouse = spp_settings.default_sheeting_warehouse
		if frappe.db.get_value("Item",x.item_code,"item_group")== spp_settings.blanking_item_group:
			ct_source_warehouse = spp_settings.unit_2_warehouse
		stock_entry.append("items",{
		"item_code":x.item_code,
		"t_warehouse":spp_settings.default_cut_bit_warehouse,
		"stock_uom": "Kg",
		"to_uom": "Kg",
		"uom": "Kg",
		"is_finished_item":0,
		"transfer_qty":x.qty,
		"qty":x.qty,
		"batch_no":r_batchno,
		"source_ref_document":mt_doc.doctype,
		"source_ref_id":mt_doc.name,
		"mix_barcode":"CB_"+x.item_code
		})	
	stock_entry.docstatus = 1
	stock_entry.save(ignore_permissions=True)
	frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
	frappe.db.commit()
	for x in mt_doc.items:
		if frappe.db.get_value("Item",x.item_code,"item_group")== spp_settings.blanking_item_group:
			check_item_bin = frappe.db.get_all("Item Bin Mapping",filters={"compound":x.item_code,"is_retired":0},fields=['name','qty'])
			if check_item_bin:
				if check_item_bin[0].qty == x.qty:
					frappe.db.set_value("Item Bin Mapping",check_item_bin[0].name,"is_retired",1)
				else:
					if check_item_bin[0].qty > x.qty:
						frappe.db.set_value("Item Bin Mapping",check_item_bin[0].name,"qty",check_item_bin[0].qty-x.qty)
				frappe.db.commit()
	
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