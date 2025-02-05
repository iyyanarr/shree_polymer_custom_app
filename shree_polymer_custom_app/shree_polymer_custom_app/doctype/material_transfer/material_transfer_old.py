# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt, update_progress_bar,format_time, formatdate, getdate, nowdate,now,get_datetime
import json

class MaterialTransfer(Document):
	def validate(self):
		if self.batches:
			for x in self.batches:
				if not x.qty > 0:
					frappe.throw("Please enter the quantity for the items.")
		if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			for x in self.batches:
				if x.is_cut_bit_item==0:
					cut_percentage_val = 0
					item_aging,cut_percentage = frappe.db.get_value("Item",x.item_code,["item_aging","cut_bit_percentage"])
					if cut_percentage:
						float_precision = 3
						cut_percentage_val = flt(x.qty)*cut_percentage/100
						cut_percentage_val=flt(cut_percentage_val, float_precision)
					self.cutbit_qty =  cut_percentage_val
	# def on_update(self):
	# 	if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
	# 		for x in self.batches:
	# 			if x.is_cut_bit_item==0:
	# 				cut_percentage_val = 0
	# 				item_aging,cut_percentage = frappe.db.get_value("Item",x.item_code,["item_aging","cut_bit_percentage"])
	# 				if cut_percentage:
	# 					float_precision = 3
	# 					cut_percentage_val = flt(x.qty)*cut_percentage/100
	# 					cut_percentage_val=flt(cut_percentage_val, float_precision)
	# 				self.cutbit_qty =  cut_percentage_val
	def on_submit(self):
		if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			if not self.sheeting_clip:
				frappe.throw("Please choose Clips.")
			ct_validation = validate_cut_bit_qty(self)
			if ct_validation.get("status")==False:
				frappe.throw(ct_validation.get("message"))
			qi_validation = validate_qi(self)
			if qi_validation.get("status")==False:
				frappe.throw(qi_validation.get("message"))
			clip_validation = validate_sheeting_clips(self)
			if clip_validation.get("status")==False:
				frappe.throw(clip_validation.get("message"))
		if self.material_transfer_type == "Transfer Batches to Mixing Center":
			create_dc(self)
			create_stock_entry(self)
		if self.material_transfer_type =="Final Batch Mixing":
				v_bom = validate_bom_items(self)
				if v_bom.get("status"):
					if self.source_warehouse != self.target_warehouse:
						create_dc(self)
					create_stock_entry(self)
				else:
					frappe.throw(v_bom.get("message"))
		if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			resp = create_stock_entry(self)
			if resp.get("status")=="Failed":
				self.reload()

def validate_bom_items(mt_doc):
	status = True
	message = ""
	dc_items = mt_doc.batches
	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.name=%(bom_no)s AND B.is_Active=1""",{"bom_no":mt_doc.bom_no},as_dict=1)
	if bom:
		bom_items = frappe.db.get_all("BOM Item",filters={"parent":bom[0].name},fields=['item_code','qty'])
		b_items = []
		d_items = []
		for x in dc_items:
			d_items.append(x.item_code)
		for x in bom_items:
			if not x.item_code in d_items:
				status =  False
				message = "BOM is not matched with items"
	return {"status":status,"message":message}
@frappe.whitelist()
def validate_sheeting_clips(mt_doc):
	clips = frappe.db.get_all("Sheeting Clip Mapping",filters={"parent":mt_doc.name},fields=['sheeting_clip'])
	for clip in clips:
		check_retired = frappe.db.get_all("Item Clip Mapping",filters={"sheeting_clip":clip.sheeting_clip,"is_retired":0})
		if check_retired:
			return {"status":False,"message":"The sheeting clip <b>{0}</b> is not yet released.".format(clip.sheeting_clip)}
	return {"status":True}
@frappe.whitelist()
def get_cutbit_items(items):
	items_code = ""
	for x in json.loads(items):
		items_code+="'"+x.get("item_code")+"',"
	items_code = items_code[:-1]
	
	spp_settings = frappe.get_single("SPP Settings")
	if spp_settings.default_cut_bit_warehouse:
		# frappe.log_error(spp_settings.default_cut_bit_warehouse,'items_code')
		stock_details_query = """ SELECT  P.quality_inspection_template,SD.creation,SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  INNER JOIN `tabItem` P ON P.name = SD.item_code
					  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
					  WHERE SD.item_code in ({items_code}) AND SD.t_warehouse = '{t_warehouse}' AND SI.warehouse = '{t_warehouse}'
					  AND S.stock_entry_type = 'Material Transfer' AND S.docstatus = 1
					  ORDER BY S.creation  """.format(items_code=items_code,t_warehouse=spp_settings.default_cut_bit_warehouse)
		# frappe.log_error(stock_details_query,'stock_details_query')
		stock_details = frappe.db.sql(stock_details_query,as_dict=1)
		return stock_details
	return []

@frappe.whitelist()
def validate_qi(self):
	message = ""
	status = True
	for x in self.batches:
		if x.qc_template:
			hr_tag = "<hr/>"
			if not x.quality_inspection:
				message+= hr_tag+"Row #"+str(x.idx)+": Quality Inspection is required for Item <b>"+x.item_code+"</br>"
				status = False
			qa_docstatus = frappe.db.get_value("Quality Inspection",x.quality_inspection,"docstatus")
			if not qa_docstatus==1:
				message+= hr_tag+"Row #"+str(x.idx)+": Quality Inspection is not submitted for Item <b>"+x.item_code+"</br>"
				status = False
	return {"status":status,"message":message}
@frappe.whitelist()
def validate_cut_bit_qty(self):
	message = ""
	status = True
	org_qty = 0
	cbt_qty = 0
	for x in self.batches:
		if x.is_cut_bit_item == 0:
			org_qty = x.qty
		if x.is_cut_bit_item == 1:
			cbt_qty = x.qty
	if not cbt_qty<=org_qty:
		status = False
		message = "Cut Bit quantity should not be Fresh Batch quantity"
	return {"status":status,"message":message}
@frappe.whitelist()
def get_employees(doctype, txt, searchfield, start, page_len, filters):
	search_condition = ""
	if txt:
		search_condition = " AND E.name like '%"+txt+"%' or E.employee_name like '%"+txt+"%'"
	query = "SELECT E.name as value,E.employee_name as description FROM `tabEmployee` E INNER JOIN `tabUser` U ON E.user_id = U.name INNER JOIN `tabHas Role` R ON R.parent=U.name WHERE R.role='Employee' AND U.enabled=1 {s_condition} ".format(s_condition=search_condition)
	linked_docs = frappe.db.sql(query)
	return linked_docs

@frappe.whitelist()
def get_minxing_t_warehouses(doctype, txt, searchfield, start, page_len, filters):
	search_condition = ""
	wh_search_condition = ""

	if txt:
		search_condition = " AND name like '%"+txt+"%'"
		wh_search_condition = " AND warehouse like '%"+txt+"%'"
		if filters.get("type") == "Transfer Batches to Mixing Center":
			search_condition = " AND warehouse like '%"+txt+"%'"
	if filters.get("type") == "Transfer Batches to Mixing Center":
		query = "SELECT warehouse FROM `tabMixing Center Target Warehouse` WHERE parent='SPP Settings' AND parentfield='target_warehouse_list' {condition}".format(condition=wh_search_condition)
		frappe.log_error(query,'query')
		linked_docs = frappe.db.sql(query)
		return linked_docs
	elif filters.get("type") == "Transfer Compound to Sheeting Warehouse":
		linked_docs = frappe.db.sql(""" SELECT warehouse FROM `tabMixing Center Target Warehouse` WHERE parent='SPP Settings' AND parentfield='warming_wareshouses' %(condition)s""",{"condition":wh_search_condition})
		return linked_docs
	elif filters.get("type") == "Blanking":
		linked_docs = frappe.db.sql(""" SELECT warehouse FROM `tabMixing Center Target Warehouse` WHERE parent='SPP Settings' AND parentfield='blanking_wareshouses' %(condition)s""",{"condition":wh_search_condition})
		return linked_docs
	else:
		query = "SELECT name FROM `tabWarehouse` WHERE disabled=0  {condition} ORDER BY modified DESC".format(condition=search_condition)
		linked_docs = frappe.db.sql(query)
		return linked_docs

@frappe.whitelist()
def get_minxing_s_warehouses(doctype, txt, searchfield, start, page_len, filters):
	search_condition = ""
	if txt:
		search_condition = " AND name like '%"+txt+"%'"
		if filters.get("type") == "Transfer Batches to Mixing Center":
			search_condition = " AND warehouse like '%"+txt+"%'"
	if filters.get("type") == "Blanking":
		linked_docs = frappe.db.sql(""" SELECT warehouse FROM `tabMixing Center Target Warehouse` WHERE parent='SPP Settings' AND parentfield='warming_wareshouses' %(condition)s""",{"condition":search_condition})
		return linked_docs
	else:
		query = "SELECT name FROM `tabWarehouse` WHERE disabled=0  {condition} ORDER BY modified DESC".format(condition=search_condition)
		linked_docs = frappe.db.sql(query)
		return linked_docs
		
@frappe.whitelist()
def validate_spp_batch_no(batch_no,warehouse,t_warehouse,s_type,t_type):
	sheeting_condition = ""
	spp_settings = frappe.get_single("SPP Settings")
	cut_bit_items = []
	is_cut_bit_item = 0
	cut_percentage_val = 0
	if t_type == "Transfer Compound to Sheeting Warehouse":
		sheeting_condition = " AND SD.is_compound=1"
	stock_details = frappe.db.sql(""" SELECT  P.quality_inspection_template,SD.creation,SD.item_code,SD.item_name,SI.qty as transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  INNER JOIN `tabItem` P ON P.name = SD.item_code
					  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
					  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) AND (SD.t_warehouse = %(t_warehouse)s) 
					  AND S.stock_entry_type = %(type)s   AND S.docstatus = 1 {sheeting_condition}
					  ORDER BY S.creation DESC limit 1 """.format(sheeting_condition=sheeting_condition),{'cut_bit_warehouse':spp_settings.default_cut_bit_warehouse,'sheeting_condition':sheeting_condition,'mix_barcode':batch_no,'t_warehouse':warehouse,'type':s_type},as_dict=1)
	# stock_details = frappe.db.get_all("Stock Entry Detail",fields=['item_code','item_name','transfer_qty','spp_batch_number','batch_no','stock_uom'],filters={"mix_barcode":batch_no,"t_warehouse":warehouse},limit_page_length=1,order_by='creation desc')
	if t_type == "Transfer Compound to Sheeting Warehouse" and not stock_details:
		stock_details = frappe.db.sql(""" SELECT   P.quality_inspection_template,SD.creation,SD.item_code,SD.item_name,SI.qty as transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  INNER JOIN `tabItem` P ON P.name = SD.item_code
					  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
					  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s)   AND (SD.t_warehouse = %(cut_bit_warehouse)s) 
					  AND S.docstatus = 1 
					  ORDER BY S.creation DESC limit 1 """,{'cut_bit_warehouse':spp_settings.default_cut_bit_warehouse,'sheeting_condition':sheeting_condition,'mix_barcode':batch_no,'t_warehouse':warehouse,'type':"Material Transfer"},as_dict=1)
		if stock_details:
			is_cut_bit_item = 1
	if stock_details:
		if t_type != "Transfer Compound to Sheeting Warehouse":
			check_stock_details = frappe.db.sql(""" SELECT  SD.t_warehouse,SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
						  FROM `tabStock Entry Detail` SD
						  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
						  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
						  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s)   AND SD.t_warehouse = %(t_warehouse)s 
						  AND S.stock_entry_type = 'Material Transfer' AND S.docstatus = 1 
						  ORDER BY S.creation DESC limit 1""",{'mix_barcode':batch_no,'t_warehouse':t_warehouse},as_dict=1)
			if check_stock_details:
				return {"status":False,"message":"Material Transfer already created for this batch to Warehouse <b>"+check_stock_details[0].t_warehouse+"</b>"}
			
		if t_type == "Transfer Compound to Sheeting Warehouse" and is_cut_bit_item == 0:
			item_aging,cut_percentage = frappe.db.get_value("Item",stock_details[0].item_code,["item_aging","cut_bit_percentage"])
			if item_aging>0:
				from frappe.utils import add_to_date
				from frappe.utils import time_diff,time_diff_in_hours
				time_diff = get_datetime(now())-get_datetime(str(stock_details[0].creation))
				to_date = add_to_date(stock_details[0].creation,hours = item_aging,as_string=True)
				to_time_diff = get_datetime(to_date)-get_datetime(now())
				if to_time_diff > time_diff:
					return {"status":False,"message":"The maturation time is not completed for the item <b>"+stock_details[0].item_code+"</b> and pending maturation time is <b>"+str((to_time_diff - time_diff )).split('.')[0]+" </b>"}

			# check_cutbit_items_query = """ SELECT  SUM(qty) as qty	 FROM `tabItem Batch Stock Balance` 
			# 		  WHERE warehouse = '{cutbit_warehouse}' AND item_code = '{st_id}' """.format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,st_id=stock_details[0].item_code)
			# cut_bit_items = frappe.db.sql(check_cutbit_items_query,as_dict=1) 
			check_qi_entry = frappe.db.get_all("Quality Inspection",filters={"spp_batch_number":stock_details[0].spp_batch_number,"docstatus":("!=",2)})
			if check_qi_entry:
				stock_details[0].qi_name = check_qi_entry[0].name
			
			# if cut_percentage:
			# 	float_precision = 3
			# 	cut_percentage_val = stock_details[0].transfer_qty*cut_percentage/100
			# 	cut_percentage_val=flt(cut_percentage_val, float_precision)

		return {"cut_percentage_val":cut_percentage_val,"status":True,"stock":stock_details,'is_cut_bit_item':is_cut_bit_item,'cut_bit_items':cut_bit_items}

	else:
		return  {"status":False,"message":"Scanned batch <b>"+batch_no+"</b> not exist in the wareshouse<b> "+warehouse+"</b>"}

@frappe.whitelist()
def get_cut_bit_rate(item_code,qty):
	cut_percentage_val = 0
	item_aging,cut_percentage = frappe.db.get_value("Item",item_code,["item_aging","cut_bit_percentage"])
	if cut_percentage:
		float_precision = 3
		cut_percentage_val = flt(qty)*cut_percentage/100
		cut_percentage_val=flt(cut_percentage_val, float_precision)
	return cut_percentage_val
def create_dc(mt_doc):
	spp_dc = frappe.new_doc("SPP Delivery Challan")
	spp_dc.posted_date = getdate()
	spp_dc.source_warehouse = mt_doc.source_warehouse
	spp_dc.target_warehouse = mt_doc.target_warehouse
	spp_dc.purpose = "Material Transfer"
	if mt_doc.material_transfer_type == "Transfer Batches to Mixing Center":
		spp_dc.operation = "Master Batch Mixing"
	if mt_doc.material_transfer_type == "Final Batch Mixing":
		spp_dc.operation = "Final Batch Mixing"
	for x in mt_doc.batches:
		spp_dc.append("items",{
			"scan_barcode":x.scan_barcode,
			"item_code":x.item_code,
			"item_name":x.item_name,
			"spp_batch_no":x.spp_batch_no,
			"batch_no":x.batch_no,
			"qty":x.qty,
			"qty_uom":x.qty_uom,

			})
	spp_dc.save(ignore_permissions=True)
	frappe.db.set_value("Material Transfer",mt_doc.name,"dc_no",spp_dc.name)
	frappe.db.commit()

def create_stock_entry(mt_doc):
	try:
		# clips = frappe.db.get_all("Sheeting Clip Mapping",filters={"parent":mt_doc.name},fields=['sheeting_clip'])
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.stock_entry_type = "Material Transfer"
		# accept 0 qty as well
		stock_entry.from_warehouse = mt_doc.source_warehouse
		stock_entry.to_warehouse = mt_doc.target_warehouse
		if mt_doc.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			stock_entry.employee = mt_doc.employee
			sheeting_clips = ""
			for clip in mt_doc.sheeting_clip:
				sheeting_clips += clip.sheeting_clip+","
			stock_entry.sheeting_clip = sheeting_clips[:-1]
		cl_spp_no = None
		for x in mt_doc.batches:
			if x.is_cut_bit_item==0:
				spp_batch_no = x.spp_batch_no
				if mt_doc.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
					sl_no = generate_w_serial_no(x.item_code,spp_batch_no,mt_doc)
					spp_batch_no = spp_batch_no+"-"+str(sl_no.serial_no)
				cl_spp_no = spp_batch_no
				stock_entry.append("items",{
					"item_code":x.item_code,
					"t_warehouse":mt_doc.target_warehouse,
					"s_warehouse":mt_doc.source_warehouse,
					"stock_uom": "Kg",
					"to_uom": "Kg",
					"uom": "Kg",
					"is_finished_item":0,
					"transfer_qty":x.qty,
					"qty":x.qty,
					"spp_batch_number":spp_batch_no,
					"batch_no":x.batch_no,
					"mix_barcode":x.item_code+"_"+x.spp_batch_no,
					})
		for x in mt_doc.batches:
			if x.is_cut_bit_item==1:
				batch_wise_stock = frappe.db.sql(""" SELECT SB.batch_no,SB.qty  FROM `tabItem Batch Stock Balance` SB 
														INNER JOIN `tabBatch` B ON SB.batch_no = B.name
														WHERE SB.item_code = %(item_code)s AND B.expiry_date >= CURDATE() AND SB.warehouse=%(warehouse)s
														ORDER BY B.creation """
														,{"item_code":x.item_code,"warehouse":spp_settings.default_cut_bit_warehouse},as_dict=1)
				for batch in batch_wise_stock:
					s_qty = 0
					remaining_qty = x.qty
					if batch.qty>0:
						if batch.qty > remaining_qty:
							s_qty = remaining_qty
						else:
							s_qty = batch.qty
						remaining_qty = remaining_qty - s_qty
						if round(s_qty,3)>0:
							stock_entry.append("items",{
							"item_code":x.item_code,
							"t_warehouse":mt_doc.target_warehouse,
							"s_warehouse":spp_settings.default_cut_bit_warehouse,
							"stock_uom": "Kg",
							"to_uom": "Kg",
							"uom": "Kg",
							"is_finished_item":0,
							"transfer_qty":s_qty,
							"qty":s_qty,
							# "spp_batch_number":x.spp_batch_number,
							"batch_no":batch.batch_no,
							})
					if not remaining_qty > 0:
						break
		stock_entry.save(ignore_permissions=True)
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save()
		frappe.db.set_value("Material Transfer",mt_doc.name,"stock_entry_ref",st_entry.name)
		frappe.db.commit()
		if mt_doc.sheeting_clip:
			t_qty = 0
			for batch in mt_doc.batches:
				t_qty+=batch.qty
			for clip in mt_doc.sheeting_clip:
				clip_mapping = frappe.get_doc({
					"doctype":"Item Clip Mapping",
					"compound":mt_doc.batches[0].item_code,
					"qty":t_qty,
					"is_retired":0,
					"sheeting_clip":clip.sheeting_clip,
					"spp_batch_number":cl_spp_no
					})
				clip_mapping.save(ignore_permissions=True)
				frappe.db.commit()
		return {"status":"Success","st_entry":st_entry}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(),"Material Transfer Failed")
		frappe.db.rollback()
		return {"status":"Failed"}

def generate_w_serial_no(item_code,spp_batch_no,mt_doc):
	serial_no = 1
	serial_nos = frappe.db.get_all("Warming Batch Serial No",filters={"spp_batch_number":spp_batch_no},fields=['serial_no'],order_by="serial_no DESC")
	if serial_nos:
		serial_no = serial_nos[0].serial_no+1
	sl_no = frappe.new_doc("Warming Batch Serial No")
	sl_no.posting_date = getdate()
	sl_no.compound = item_code
	sl_no.serial_no = serial_no
	sl_no.spp_batch_number = spp_batch_no
	for x in mt_doc.sheeting_clip:
		sl_no.append("sheeting_clips",{"sheeting_clip":x.sheeting_clip})
	sl_no.insert()
	return sl_no
@frappe.whitelist()
def get_scanned_warehouse(scanned_loc):
	return frappe.db.sql(""" SELECT name FROM `tabWarehouse` WHERE name=%(scanned_loc)s OR barcode_text=%(scanned_loc)s """,{"scanned_loc":scanned_loc},as_dict=1)

@frappe.whitelist()
def get_scanned_clip(scan_clip):
	return frappe.db.sql(""" SELECT name FROM `tabSheeting Clip` WHERE name=%(scan_clip)s OR barcode_text=%(scan_clip)s """,{"scan_clip":scan_clip},as_dict=1)
