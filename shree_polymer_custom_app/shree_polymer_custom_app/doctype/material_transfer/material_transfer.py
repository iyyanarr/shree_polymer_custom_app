# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt, update_progress_bar,format_time, formatdate, getdate, nowdate,now,get_datetime,add_to_date
import json
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series

class MaterialTransfer(Document):
	def validate(self):
		if getdate(self.transfer_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.batches:
			frappe.throw(f'Please Scan and add some items before submit..!')
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
		if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			if not self.sheeting_clip:
				frappe.throw("Please choose Clips.")
	
	def on_submit(self):
		if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			if not self.sheeting_clip:
				frappe.throw("Please choose Clips.")
			# ct_validation = validate_cut_bit_qty(self)
			# if ct_validation.get("status")==False:
			# 	frappe.throw(ct_validation.get("message"))
			# qi_validation = validate_qi(self)
			# if qi_validation.get("status")==False:
			# 	frappe.throw(qi_validation.get("message"))
			clip_validation = validate_sheeting_clips(self)
			if clip_validation.get("status")==False:
				frappe.throw(clip_validation.get("message"))
		if self.material_transfer_type == "Transfer Batches to Mixing Center":
			if self.source_warehouse != self.target_warehouse:
				# create_dc(self)
				create_delivery_note(self)
			else:
				create_stock_entry(self)
			# else:
				# frappe.throw(v_bom.get("message"))
		if self.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
			resp = create_sheeting_stock_entry(self)
			if resp.get("status")=="Failed":
				self.reload()
		self.reload()

def validate_bom_items(mt_doc):
	status = True
	message = ""
	dc_items = mt_doc.batches
	g_items =  frappe.db.sql(""" SELECT B.item_code,B.item_produced FROM `tabMaterial Transfer Item` B WHERE parent=%(parent_name)s GROUP BY B.item_code,B.item_produced """,{"parent_name":mt_doc.name},as_dict=1)
	for g_item in g_items:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(bom_item)s AND B.is_Active=1""",{"bom_item":g_item.item_produced},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":g_item.item_produced},as_dict=1)
			if len(bom__) > 1:
				return {"status":False,"message":f"Multiple BOM's found for Item to Produce - <b>{g_item.item_produced}</b>"}
			""" End """
			bom_items = frappe.db.get_all("BOM Item",filters={"parent":bom[0].name},fields=['item_code','qty'])
			dc_items = frappe.db.sql(""" SELECT B.item_code,B.item_produced FROM `tabMaterial Transfer Item` B WHERE parent=%(parent_name)s and item_produced=%(item_produced)s""",{"parent_name":mt_doc.name,'item_produced':g_item.item_produced},as_dict=1)
			b_items = []
			d_items = []
			for x in dc_items:
				if not x.item_code in d_items:
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
		stock_details_query = """ SELECT  P.quality_inspection_template,SD.creation,SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  INNER JOIN `tabItem` P ON P.name = SD.item_code
					  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
					  WHERE SD.item_code in ({items_code}) AND SD.t_warehouse = '{t_warehouse}' AND SI.warehouse = '{t_warehouse}'
					  AND S.stock_entry_type = 'Material Transfer' AND S.docstatus = 1
					  ORDER BY S.creation  """.format(items_code=items_code,t_warehouse=spp_settings.default_cut_bit_warehouse)
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
		query = "SELECT warehouse FROM `tabMixing Operation` WHERE parent='SPP Settings' AND parentfield='mixing_operations' {condition}".format(condition=wh_search_condition)
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
		# sheeting_condition = " AND SD.is_compound=1"
		sheeting_condition = ""
	stock_details = frappe.db.sql(""" SELECT S.posting_date,S.posting_time,S.name stock__id,S.stock_entry_type,S.docstatus doc__status,P.quality_inspection_template,SD.creation,SD.item_code,SD.item_name,SI.qty as transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  INNER JOIN `tabItem` P ON P.name = SD.item_code
					  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
					  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) AND (SD.t_warehouse = %(t_warehouse)s) 
					  AND (S.stock_entry_type = %(type)s OR S.stock_entry_type ='Material Receipt') AND S.docstatus = 1  {sheeting_condition}
					  ORDER BY S.creation DESC limit 1 """.format(sheeting_condition=sheeting_condition),{'cut_bit_warehouse':spp_settings.default_cut_bit_warehouse,'sheeting_condition':sheeting_condition,'mix_barcode':batch_no,'t_warehouse':warehouse,'type':s_type},as_dict=1)
	# stock_details = frappe.db.get_all("Stock Entry Detail",fields=['item_code','item_name','transfer_qty','spp_batch_number','batch_no','stock_uom'],filters={"mix_barcode":batch_no,"t_warehouse":warehouse},limit_page_length=1,order_by='creation desc')
	if t_type == "Transfer Compound to Sheeting Warehouse" and not stock_details:
		stock_details = frappe.db.sql(""" SELECT S.posting_date,S.posting_time,S.name stock__id,S.stock_entry_type,S.docstatus doc__status,P.quality_inspection_template,SD.creation,SD.item_code,SD.item_name,SI.qty as transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  INNER JOIN `tabItem` P ON P.name = SD.item_code
					  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
					  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) AND (SD.t_warehouse = %(cut_bit_warehouse)s) 
					  AND S.docstatus = 1
					  ORDER BY S.creation DESC limit 1 """,{'cut_bit_warehouse':spp_settings.default_cut_bit_warehouse,'sheeting_condition':sheeting_condition,'mix_barcode':batch_no,'t_warehouse':warehouse,'type':"Material Transfer"},as_dict=1)
		if stock_details:
			is_cut_bit_item = 1
	if stock_details:
	# Hided for old compounds not able to scan on 1/8/23
		# if stock_details[0].stock_entry_type == "Manufacture":
		# 	item_group = frappe.db.get_value("Item",stock_details[0].item_code,'item_group')
		# 	if item_group == "Compound":
		# 		compound_ins = frappe.db.get_value("Compound Inspection",{"stock_id":stock_details[0].stock__id},["docstatus"],as_dict  = 1)
		# 		if compound_ins:
		# 			if compound_ins.docstatus == 0:
		# 				return  {"status":False,"message":f"The <b>Compound Inspection Entry</b> is not <b>Submitted</b> for the <b>Compound - {stock_details[0].item_code}</b>..!"}		
		# 			elif compound_ins.docstatus == 2:
		# 				return  {"status":False,"message":f"The <b>Compound Inspection Entry</b> is <b>Cancelled</b> for the <b>Compound - {stock_details[0].item_code}</b>..!"}		
		# 		else:
		# 			return  {"status":False,"message":f"The <b>Compound Inspection Entry</b> is not found for the <b>Compound - {stock_details[0].item_code}</b>..!"}
	# end
		# if t_type != "Transfer Compound to Sheeting Warehouse":
		# 	check_stock_details = frappe.db.sql(""" SELECT  SD.t_warehouse,SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
		# 				  FROM `tabStock Entry Detail` SD
		# 				  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
		# 				  INNER JOIN `tabItem Batch Stock Balance` SI ON SI.batch_no = SD.batch_no
		# 				  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s)   AND SD.t_warehouse = %(t_warehouse)s 
		# 				  AND S.stock_entry_type = 'Material Transfer' AND S.docstatus = 1 
		# 				  ORDER BY S.creation DESC limit 1""",{'mix_barcode':batch_no,'t_warehouse':t_warehouse},as_dict=1)
		# 	if check_stock_details:
		# 		return {"status":False,"message":"Material Transfer already created for this batch to Warehouse <b>"+check_stock_details[0].t_warehouse+"</b>"}
			
		if t_type == "Transfer Compound to Sheeting Warehouse" and is_cut_bit_item == 0:
		# Temporarly disabled as per arun req on 8/2/23
			## wrong calculation so below code changed on 8/2/23
			# item_aging = frappe.db.get_value("Item",stock_details[0].item_code,["item_aging"])
			# if item_aging and item_aging > 0:
				# from frappe.utils import add_to_date
				# from frappe.utils import time_diff,time_diff_in_hours
				# time_diff = get_datetime(now())-get_datetime(str(stock_details[0].creation))
				# to_date = add_to_date(stock_details[0].creation,hours = item_aging,as_string=True)
				# to_time_diff = get_datetime(to_date)-get_datetime(now())
				# if to_time_diff > time_diff:
				# 	return {"status":False,"message":"The maturation time is not completed for the item <b>"+stock_details[0].item_code+"</b> and pending maturation time is <b>"+str((to_time_diff - time_diff )).split('.')[0]+" </b>"}
			## right code
			# item_aging = frappe.db.get_value("Item",stock_details[0].item_code,["item_aging"])
			# if item_aging and item_aging > 0:
			# 	from datetime import datetime
			# 	datetime_str = f"{getdate(stock_details[0].posting_date)} {stock_details[0].posting_time}"
			# 	if len(datetime_str)>19:
			# 		datetime_str = datetime_str.split('.')[0]
			# 	date_time = str(datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S'))
			# 	to_date = add_to_date(date_time,hours = item_aging,as_string=True)
			# 	if to_date > str(now()):
			# 		time_diff = get_datetime(to_date) - get_datetime(now())
			# 		return {"status":False,"message":"The <b>Maturation time</b> is not completed for the item <b>"+stock_details[0].item_code+"</b> and pending maturation time is <b>"+str(time_diff).split('.')[0]+" hrs</b>"}
			## end
		# End
			# check_cutbit_items_query = """ SELECT  SUM(qty) as qty	 FROM `tabItem Batch Stock Balance` 
			# 		  WHERE warehouse = '{cutbit_warehouse}' AND item_code = '{st_id}' """.format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,st_id=stock_details[0].item_code)
			# cut_bit_items = frappe.db.sql(check_cutbit_items_query,as_dict=1) 
			check_qi_entry = frappe.db.get_all("Quality Inspection",filters={"spp_batch_number":stock_details[0].spp_batch_number,"docstatus":("!=",2)})
			if check_qi_entry:
				stock_details[0].qi_name = check_qi_entry[0].name
		if t_type != "Transfer Compound to Sheeting Warehouse":
			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_Active=1 """,{"item_code":stock_details[0].item_code},as_dict=1)
			if not bom:
				return  {"status":False,"message":"No BOM found for scanned batch item."}
			else:
				""" Multi Bom Validation """
				bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
				if len(bom__) > 1:
					return {"status":False,"message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
				""" End """
				stock_details[0].item_produced = bom[0].item
			# if cut_percentage:
			# 	float_precision = 3
			# 	cut_percentage_val = stock_details[0].transfer_qty*cut_percentage/100
			# 	cut_percentage_val=flt(cut_percentage_val, float_precision)

		return {"cut_percentage_val":cut_percentage_val,"status":True,"stock":stock_details,'is_cut_bit_item':is_cut_bit_item,'cut_bit_items':cut_bit_items}

	else:
	# Temporarly disabled as per arun req on 8/2/23
		resp = check_compound_inspection(batch_no,warehouse,s_type)
		if resp:
			return resp
		else:
	# End
			if batch_no.lower().startswith('cb'):
				warehouse = spp_settings.default_cut_bit_warehouse
			return  {"status":False,"message":"Scanned batch <b>"+batch_no+"</b> not exist in the wareshouse<b> "+warehouse+"</b>"}

def check_compound_inspection(batch_no,warehouse,s_type):
	stock_details = frappe.db.sql(""" SELECT S.name stock__id,S.stock_entry_type,S.docstatus doc__status,SD.item_code
									FROM `tabStock Entry Detail` SD
									INNER JOIN `tabStock Entry` S ON SD.parent = S.name
									INNER JOIN `tabItem` P ON P.name = SD.item_code
									WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) 
			       					AND (SD.t_warehouse = %(t_warehouse)s) 
									AND (S.stock_entry_type = %(type)s OR S.stock_entry_type ='Material Receipt') 
									ORDER BY S.creation DESC limit 1 """,
										{'mix_barcode':batch_no,'t_warehouse':warehouse,'type':s_type},as_dict=1)
	if stock_details:
		if stock_details[0].doc__status !=1:
			if stock_details[0].stock_entry_type == "Manufacture":
				if stock_details[0].doc__status == 0:
					item_group = frappe.db.get_value("Item",stock_details[0].item_code,'item_group')
					if item_group == "Compound":
						compound_ins = frappe.db.get_value("Compound Inspection",{"stock_id":stock_details[0].stock__id},["docstatus"],as_dict  = 1)
						if compound_ins:
							if compound_ins.docstatus == 0:
								return  {"status":False,"message":f"The <b>Compound Inspection Entry</b> is not <b>Submitted</b> for the <b>Compound - {stock_details[0].item_code}</b>..!"}		
							elif compound_ins.docstatus == 2:
								return  {"status":False,"message":f"The <b>Compound Inspection Entry</b> is <b>Cancelled</b> for the <b>Compound - {stock_details[0].item_code}</b>..!"}		
						else:
							return  {"status":False,"message":f"The <b>Compound Inspection Entry</b> is not found for the <b>Compound - {stock_details[0].item_code}</b>..!"}
	return False

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
		# spp_dc.operation = "Master Batch Mixing"
		if mt_doc.source_warehouse == mt_doc.target_warehouse:
			spp_dc.operation = "Mixing"
		if mt_doc.source_warehouse != mt_doc.target_warehouse:
			spp_dc.operation = "Kneader Mixing"
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

def create_delivery_note(mt_doc):
	spp_dc = frappe.new_doc("Delivery Note")
	""" Ref """
	spp_dc.reference_document = mt_doc.doctype
	spp_dc.reference_name = mt_doc.name
	spp_dc.driver_name = mt_doc.driver_name
	spp_dc.vehicle_no = mt_doc.vehicle_number
	spp_settings = frappe.get_single("SPP Settings")
	# spp_dc.posting_date = getdate()
	""" Update posting date and time """
	spp_dc.posting_date = mt_doc.transfer_date
	""" End """
	spp_dc.set_warehouse = mt_doc.source_warehouse
	spp_dc.set_target_warehouse = mt_doc.target_warehouse
	naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Transfer Batches to Mixing Center")
	if naming_status:
		spp_dc.naming_series = naming_series
	customer = frappe.db.get_value("Warehouse",mt_doc.target_warehouse,"customer")
	if customer:
		# if frappe.db.get_value("Customer",customer,"is_internal_customer"):
			spp_dc.customer = customer
			if mt_doc.material_transfer_type == "Transfer Batches to Mixing Center":
				# spp_dc.operation = "Master Batch Mixing"
				if mt_doc.source_warehouse == mt_doc.target_warehouse:
					spp_dc.operation = "Mixing"
				if mt_doc.source_warehouse != mt_doc.target_warehouse:
					spp_dc.operation = "Kneader Mixing"
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
					"uom":x.qty_uom,
					"target_warehouse":mt_doc.target_warehouse
					})
			spp_dc.docstatus = 1
			spp_dc.save(ignore_permissions=True)
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabDelivery Note` SET posting_date = '{mt_doc.transfer_date}' WHERE name = '{spp_dc.name}' ")
			""" End """
			frappe.db.set_value("Material Transfer",mt_doc.name,"dc_no",spp_dc.name)
			frappe.db.commit()
			# frappe.db.sql("DELETE FROM `tabStock Ledger Entry` WHERE voucher_no=%(voucher_no)s",{"voucher_no":spp_dc.name})
			# frappe.db.commit()
		# else:
		# 	frappe.throw("Customer is not internal customer")
	else:
		frappe.throw("Customer not found for the wareshouse "+mt_doc.target_warehouse)

def create_stock_entry(mt_doc):
	try:
		# clips = frappe.db.get_all("Sheeting Clip Mapping",filters={"parent":mt_doc.name},fields=['sheeting_clip'])
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		""" Update posting date and time """
		stock_entry.posting_date = mt_doc.transfer_date
		""" End """
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		""" For identifying procees name to change the naming series the field is used """
		naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Transfer Batches to Mixing Center")
		if naming_status:
			stock_entry.naming_series = naming_series
		""" End """
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
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
				mix_barcode = x.scan_barcode
				if mt_doc.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
					sl_no = generate_w_serial_no(x.item_code,spp_batch_no,mt_doc)
					spp_batch_no = spp_batch_no+"-"+str(sl_no.serial_no)
					mix_barcode = x.item_code+"_"+x.spp_batch_no
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
					"use_serial_batch_fields":1,
					"spp_batch_number":spp_batch_no,
					"batch_no":x.batch_no,
					"mix_barcode":mix_barcode,
					"source_ref_document":mt_doc.doctype,
					"source_ref_id":mt_doc.name
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
							"use_serial_batch_fields":1,
							"qty":s_qty,
							# "spp_batch_number":x.spp_batch_number,
							"batch_no":batch.batch_no,
							"source_ref_document":mt_doc.doctype,
							"source_ref_id":mt_doc.name
							})
					if not remaining_qty > 0:
						break
		stock_entry.save(ignore_permissions=True)
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save()
		""" Update posting date and time """
		frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.transfer_date}' WHERE name = '{st_entry.name}' ")
		""" End """
		frappe.db.set_value("Material Transfer",mt_doc.name,"stock_entry_ref",st_entry.name)
		frappe.db.commit()
		if mt_doc.sheeting_clip:
			t_qty = 0
			for batch in mt_doc.batches:
				t_qty += batch.qty
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
		frappe.log_error(message=frappe.get_traceback(),title="Material Transfer Failed")
		frappe.db.rollback()
		return {"status":"Failed"}

def create_sheeting_stock_entry(mt_doc):
    try:
        spp_settings = frappe.get_single("SPP Settings")
        
        # First, validate available cut bit quantities
        cut_bit_items_to_process = []
        skipped_items = []
        
        for x in mt_doc.batches:
            if x.is_cut_bit_item == 1:
                # Check available quantity
                available_qty = frappe.db.get_value("Item Batch Stock Balance", 
                    {"batch_no": x.batch_no, "warehouse": spp_settings.default_cut_bit_warehouse}, 
                    "qty") or 0
                
                if available_qty >= x.qty:
                    cut_bit_items_to_process.append(x)
                else:
                    skipped_items.append({
                        "item_code": x.item_code,
                        "batch_no": x.batch_no,
                        "requested": x.qty,
                        "available": available_qty
                    })
        
        # If any items are skipped due to insufficient stock, notify user and stop
        if skipped_items:
            error_msg = "Insufficient stock for the following cut bit items:<br>"
            for item in skipped_items:
                error_msg += f"- Item: {item['item_code']}, Batch: {item['batch_no']}, " \
                            f"Requested: {item['requested']} kg, Available: {item['available']} kg<br>"
            frappe.throw(error_msg)
        
        # If all checks pass, proceed with creating the stock entry
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.posting_date = mt_doc.transfer_date
        stock_entry.purpose = "Repack"
        stock_entry.company = "SPP"
        stock_entry.naming_series = "MAT-STE-.YYYY.-"
        
        naming_status, naming_series = get_stock_entry_naming_series(spp_settings, "Transfer Compound to Sheeting Warehouse")
        if naming_status:
            stock_entry.naming_series = naming_series
            
        stock_entry.stock_entry_type = "Repack"
        stock_entry.from_warehouse = mt_doc.source_warehouse
        stock_entry.to_warehouse = mt_doc.target_warehouse
        
        if mt_doc.material_transfer_type == "Transfer Compound to Sheeting Warehouse":
            stock_entry.employee = mt_doc.employee
            sheeting_clips = ""
            for clip in mt_doc.sheeting_clip:
                sheeting_clips += clip.sheeting_clip + ","
            stock_entry.sheeting_clip = sheeting_clips[:-1]
            
        cl_spp_no = None
        total_qty = 0
        org_batch_no = ""
        mix_barcode = None
        compound_code = None
        compound_spp_code = None
        create_issue_entry = 0
        
        # Add regular items
        for x in mt_doc.batches:
            if x.is_cut_bit_item == 0:
                spp_batch_no = x.spp_batch_no
                cl_spp_no = spp_batch_no
                org_batch_no = x.batch_no
                stock_entry.append("items", {
                    "item_code": x.item_code,
                    "s_warehouse": mt_doc.source_warehouse,
                    "stock_uom": "Kg",
                    "to_uom": "Kg",
                    "uom": "Kg",
                    "is_finished_item": 0,
                    "use_serial_batch_fields": 1,
                    "transfer_qty": x.qty,
                    "qty": x.qty,
                    "spp_batch_number": spp_batch_no,
                    "batch_no": x.batch_no,
                    "mix_barcode": mix_barcode,
                })
                compound_code = x.item_code
                compound_spp_code = x.spp_batch_no
                total_qty += x.qty
        
        # Add cut bit items (already validated)
        for x in cut_bit_items_to_process:
            create_issue_entry = 1
            stock_entry.append("items", {
                "item_code": x.item_code,
                "s_warehouse": spp_settings.default_cut_bit_warehouse,
                "stock_uom": "Kg",
                "to_uom": "Kg",
                "uom": "Kg",
                "is_finished_item": 0,
                "use_serial_batch_fields": 1,
                "transfer_qty": x.qty,
                "qty": x.qty,
                "batch_no": x.batch_no,
                "mix_barcode": mix_barcode,
            })
            total_qty += x.qty
            
        # Create serial number and add the destination item
        sl_no = generate_w_serial_no(compound_code, compound_spp_code, mt_doc)
        spp_batch_no = compound_spp_code + "-" + str(sl_no.serial_no)
        mix_barcode = compound_code + "_" + compound_spp_code
        
        stock_entry.append("items", {
            "item_code": compound_code,
            "t_warehouse": mt_doc.target_warehouse,
            "stock_uom": "Kg",
            "to_uom": "Kg",
            "uom": "Kg",
            "is_finished_item": 1,
            "transfer_qty": total_qty,
            "qty": total_qty,
            "use_serial_batch_fields": 1,
            "spp_batch_number": spp_batch_no,
            "mix_barcode": mix_barcode,
            "source_ref_document": mt_doc.doctype,
            "source_ref_id": mt_doc.name
        })
        
        # Save and submit the stock entry with proper transactions
        stock_entry.save(ignore_permissions=True)
        st_entry = frappe.get_doc("Stock Entry", stock_entry.name)
        st_entry.docstatus = 1
        st_entry.save(ignore_permissions=True)
        
        # Update posting date and time
        frappe.db.sql(f"UPDATE `tabStock Entry` SET posting_date = '{mt_doc.transfer_date}' WHERE name = '{st_entry.name}'")
        frappe.db.set_value("Material Transfer", mt_doc.name, "stock_entry_ref", st_entry.name)
        frappe.db.commit()
        
        # Create clip mappings
        if mt_doc.sheeting_clip:
            t_qty = 0
            for batch in mt_doc.batches:
                t_qty += batch.qty
            for clip in mt_doc.sheeting_clip:
                clip_mapping = frappe.get_doc({
                    "doctype": "Item Clip Mapping",
                    "compound": mt_doc.batches[0].item_code,
                    "qty": t_qty,
                    "is_retired": 0,
                    "sheeting_clip": clip.sheeting_clip,
                    "spp_batch_number": spp_batch_no
                })
                clip_mapping.save(ignore_permissions=True)
            frappe.db.commit()
            
        return {"status": "Success", "st_entry": st_entry}
        
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Material Transfer Failed")
        frappe.db.rollback()
        return {"status": "Failed", "error_message": str(e)}

def create_sheeting_issue_entry(mt_doc,org_batch_no):
	spp_settings = frappe.get_single("SPP Settings")
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = "Material Issue"
	stock_entry.company = "SPP"
	stock_entry.naming_series = "MAT-STE-.YYYY.-"
	stock_entry.stock_entry_type = "Material Issue"
	stock_entry.from_warehouse = spp_settings.default_cut_bit_warehouse
	for x in mt_doc.batches:
		if x.is_cut_bit_item==1:
			stock_entry.append("items",{
			"item_code":x.item_code,
			"s_warehouse":spp_settings.default_cut_bit_warehouse,
			"stock_uom": "Kg",
			"to_uom": "Kg",
			"uom": "Kg",
			"is_finished_item":0,
			"transfer_qty":x.qty,
			"qty":x.qty,
			"use_serial_batch_fields":1,
			# "spp_batch_number":x.spp_batch_number,
			"batch_no":"Cutbit_"+x.item_code,
			"source_ref_document":mt_doc.doctype,
			"source_ref_id":mt_doc.name
			})
	stock_entry.docstatus = 1
	stock_entry.save(ignore_permissions=True)
	stock_entry_rc = frappe.new_doc("Stock Entry")
	stock_entry_rc.purpose = "Material Receipt"
	stock_entry_rc.company = "SPP"
	stock_entry_rc.naming_series = "MAT-STE-.YYYY.-"
	stock_entry_rc.stock_entry_type = "Material Receipt"
	stock_entry_rc.to_warehouse = spp_settings.default_sheeting_warehouse
	for x in mt_doc.batches:
		if x.is_cut_bit_item==1:
			stock_entry_rc.append("items",{
			"item_code":x.item_code,
			"t_warehouse":spp_settings.default_sheeting_warehouse,
			"stock_uom": "Kg",
			"to_uom": "Kg",
			"uom": "Kg",
			"is_finished_item":0,
			"transfer_qty":x.qty,
			"qty":x.qty,
			"use_serial_batch_fields":1,
			# "spp_batch_number":x.spp_batch_number,
			"batch_no":org_batch_no,
			"source_ref_document":mt_doc.doctype,
			"source_ref_id":mt_doc.name
			})
	stock_entry_rc.docstatus = 1
	stock_entry_rc.save(ignore_permissions=True)
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
	sl_no.insert(ignore_permissions = True)
	return sl_no
@frappe.whitelist()
def get_scanned_warehouse(scanned_loc):
	return frappe.db.sql(""" SELECT name FROM `tabWarehouse` WHERE name=%(scanned_loc)s OR barcode_text=%(scanned_loc)s """,{"scanned_loc":scanned_loc},as_dict=1)

@frappe.whitelist()
def get_scanned_clip(scan_clip):
	return frappe.db.sql(""" SELECT name FROM `tabSheeting Clip` WHERE name=%(scan_clip)s OR barcode_text=%(scan_clip)s """,{"scan_clip":scan_clip},as_dict=1)