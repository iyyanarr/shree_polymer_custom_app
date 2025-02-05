# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt
import json
import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import (
	cint,
	date_diff,
	flt,
	get_datetime,
	get_link_to_form,
	getdate,
	nowdate,
	time_diff_in_hours,
)



class SPPProductionEntry(Document):
	def validate(self):
		if self.type == "Final Batch Mixing":
			if not self.qty>0:
				frappe.throw("Please enter the quantity.")

	def on_submit(self):
		if self.type == "Final Batch Mixing":
			if not self.qty>0:
				frappe.throw("Please enter the quantity.")
			if not self.item:
				frappe.throw("Please choose compound.")
			if not self.bom_no:
				frappe.throw("BOM not found for the selected compound.")
			# fb_mix = validate_final_batches(self)
			v_bom = validate_bom_items(self)
			if v_bom.get("status"):
				if self.source_warehouse != self.target_warehouse:
					create_dc(self)
				create_stock_entry(self)
			else:
				frappe.throw(v_bom.get("message"))
		if self.type == "Blanking":
			if not self.blanking_bins:
				frappe.throw("Please choose Bins.")
			tolerance_validation = validate_sheeting_tolerance(self)
			if tolerance_validation.get("status")==False:
				frappe.throw(tolerance_validation.get("message"))
			create_blanking_wo(self)

	@frappe.whitelist()
	def get_items_and_operations_from_bom(self):
		self.set_required_items()

	def set_required_items(self, reset_only_qty=False):
		"""set required_items for production to keep track of reserved qty"""
		if not reset_only_qty:
			self.required_items = []
		operation = "Final Batch Mixing"
		if self.bom_no:
			bom_items = frappe.db.get_all("BOM Item",filters={"parent":self.bom_no},fields=["item_code"],order_by="idx")
			items = ''
			for x in bom_items:
				items+= "'"+x.item_code+"',"
			if items:
				items = items[:-1]
			st_entries_array = []
			total_qty = 0
			s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I INNER JOIN `tabBatch` B ON I.batch_no = B.name WHERE item_code IN ({item_codes}) AND  warehouse ='{warehouse}' AND B.expiry_date>=curdate()".format(item_codes=items,warehouse=self.source_warehouse)
			# frappe.log_error(s_query,'s_query')
			st_items = frappe.db.sql(s_query,as_dict=1)
			# for item in st_entries_array:
			has_cmb = 0
			cmb_code = None
			cmb_spp_batches = []
			for item in st_items:
				spp_batch_number = mix_barcode = ""
				check_spps = frappe.db.get_all("Stock Entry Detail",filters={"batch_no":item.get("batch_no"),"t_warehouse":self.source_warehouse},fields=['spp_batch_number','mix_barcode'])
				if check_spps:
					spp_batch_number = check_spps[0].spp_batch_number
					mix_barcode = check_spps[0].mix_barcode
				mix_barcode = ""
				if not mix_barcode:
					b_list = frappe.db.sql(""" SELECT mix_barcode FROM `tabImported Batches` WHERE mixbatchno like '%{code}%' """.format(code=spp_batch_number),as_dict=1)
					if b_list:
						mix_barcode = b_list[0].mix_barcode
				
				self.append(
					"required_items",
					{
						"operation": "Final Batch Mixing",
						"item_code": item.get("item_code"),
						"item_name": item.get("item_name"),
						"description": item.get("description"),
						"qty": item.get("qty"),
						"transfer_qty": item.get("qty"),
						"source_warehouse": self.source_warehouse,
						"spp_batch_number":spp_batch_number,
						"uom":item.get("uom"),
						"stock_uom":item.get("uom"),
						"batch_no":item.get("batch_no"),
						"scan_barcode":mix_barcode
					},
				)
				total_qty+=item.get("qty")
			
			self.qty = total_qty
			if total_qty == 0:
				self.qty = 1

def validate_sheeting_tolerance(mt_doc):
	spp_settings = frappe.get_single("SPP Settings")
	for x in mt_doc.required_items:
		clips = frappe.db.get_all("Item Clip Mapping",filters={"spp_batch_number":x.spp_batch_number,'compound':x.item_code,'is_retired':0},fields=['qty'])
		if clips:
			if not ((clips[0].qty-x.qty)<=spp_settings.tolerance_band):
				return {"status":False,"message":"Sheeting stock entry related to this set of clips for that batch is moved out from sheeting warehouse within a tolerance band of <b>"+"%.3f" %(spp_settings.tolerance_band)+" Kgs </b>."}
	return{"status":True}

def validate_final_batches(self):
	grouped_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabMixing Item` WHERE operation = 'Final Batch Mixing' AND parent = %(rc_id)s GROUP BY item_to_manufacture """,{"rc_id":self.name},as_dict=1)
	if len(grouped_items)>1:
		return False
	for x in grouped_items:
		bom_items = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":x.item_to_manufacture},as_dict=1)
		manf_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabMixing Item` WHERE operation = 'Final Batch Mixing' AND parent = %(rc_id)s AND item_to_manufacture=%(item_to_manufacture)s """,{"rc_id":self.name,"item_to_manufacture":x.item_to_manufacture},as_dict=1)
		if not len(manf_items) == len(bom_items):
			return False
	return True
@frappe.whitelist()
def validate_item_spp_barcode(item,batch_no,warehouse,bom_no,p_type):
	if p_type=="Final Batch Mixing":
		bom_items = frappe.db.get_all("BOM Item",filters={"parent":bom_no},fields=['item_code'])
		stock_details = frappe.db.sql(""" SELECT  SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
						  FROM `tabStock Entry Detail` SD
						  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
						  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) AND SD.t_warehouse = %(t_warehouse)s 
						  AND S.stock_entry_type = 'Manufacture' AND S.docstatus = 1 
						  ORDER BY S.creation DESC limit 1 """,{'mix_barcode':batch_no,'t_warehouse':warehouse},as_dict=1)
		if stock_details:
			items = stock_details[0].item_code
			b_items = []
			for x in bom_items:
				b_items.append(x.item_code)
			if not items in b_items:
				return {"status":"Failed","message":"Item "+stock_details[0].item_name+" not matched with BOM of "+item}
			s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,SD.spp_batch_number,\
						 I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I\
						 INNER JOIN `tabBatch` B ON I.batch_no = B.name \
						 INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name\
						 WHERE  (SD.mix_barcode = '{mix_barcode}' OR SD.barcode_text = '{mix_barcode}')  AND \
						 I.warehouse ='{warehouse}' AND B.expiry_date>=curdate()".format(mix_barcode=batch_no,item_codes=items,warehouse=warehouse)
			st_details = frappe.db.sql(s_query,as_dict=1)
			if st_details:
				bom  = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND B.is_default=1""",{"item_code":st_details[0].item_code},as_dict=1)
				if bom:
					st_details[0].bom_item = bom[0].item
				return {"status":"Success","stock":st_details}
			else:
				return {"status":"Failed","message":"Stock is not available for the item <b>"+stock_details[0].item_code+"</b> in the wareshouse <b>"+warehouse+"</b>"}


		return  {"status":"Failed","message":"Scanned batch <b>"+batch_no+"</b> not exist in the wareshouse<b> "+warehouse+"</b>"}
	
	elif p_type=="Blanking":
		return validate_blanking_spp_barcode(batch_no,warehouse)
@frappe.whitelist()
def validate_blanking_spp_barcode(batch_no,warehouse):
	spp_settings = frappe.get_single("SPP Settings")
	stock_details = frappe.db.sql(""" SELECT S.name, SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) AND SD.t_warehouse = %(t_warehouse)s 
					  AND S.stock_entry_type = 'Material Transfer' AND S.docstatus = 1  
					  ORDER BY S.creation DESC limit 1 """,{'mix_barcode':batch_no,'t_warehouse':warehouse},as_dict=1)
	if stock_details:
		items = stock_details[0].item_code
		bom_items = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabBOM Operation` BO ON BO.parent=B.name WHERE BO.operation ='Blanking' AND BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":items},as_dict=1)
		if not bom_items:
			return {"status":"Failed","message":"No BOM found associated with the item <b>"+stock_details[0].item_code+"</b>"}
		s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,SD.spp_batch_number,\
					I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I\
					 INNER JOIN `tabBatch` B ON I.batch_no = B.name \
					 INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name\
					 WHERE I.item_code ='{item_codes}' AND  (SD.mix_barcode = '{mix_barcode}' OR SD.barcode_text = '{mix_barcode}')   AND \
					 I.warehouse ='{warehouse}' AND B.expiry_date>=curdate() AND SD.s_warehouse <> '{cutbit_warehouse}'".format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,mix_barcode=batch_no,item_codes=items,warehouse=warehouse)
		st_details = frappe.db.sql(s_query,as_dict=1)
		check_cutbit_items_query = """ SELECT  SD.item_code,SD.item_name,SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  WHERE SD.s_warehouse = '{cutbit_warehouse}' AND S.name = '{st_id}' """.format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,st_id=stock_details[0].name)
		# check_cutbit_items_query = """ SELECT  SUM(qty) FROM `tabItem Batch Stock Balance` 
		# 			  WHERE warehouse = '{cutbit_warehouse}' AND item_dode = '{st_id}' """.format(cutbit_warehouse=spp_settings.default_cut_bit_warehouse,st_id=items)
		cutbit_items = frappe.db.sql(check_cutbit_items_query,as_dict=1)
		return {"status":"Success","stock":st_details,'cutbit_items':cutbit_items}

	return  {"status":"Failed","message":"Scanned batch <b>"+batch_no+"</b> not exist in the wareshouse<b> "+warehouse+"</b>"}

def validate_bom_items(mt_doc):
	status = True
	message = ""
	dc_items = mt_doc.required_items
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
		# for x in bom_items:
		# 	p_qty = flt((mt_doc.qty*x.qty),3)
		# 	for dc_item in dc_items:
		# 		if dc_item.item_code == x.item_code:
		# 			frappe.log_error(x.item_code,"item_code")
		# 			frappe.log_error(p_qty,"p_qty")
		# 			frappe.log_error(dc_item.qty,"dc_item.qty")
		# 			if (p_qty)!=dc_item.qty:
		# 				status =  False
		# 				message = "Items qty proportion not matched with BOM."
	return {"status":status,"message":message}
@frappe.whitelist()
def get_compounds(doctype, txt, searchfield, start, page_len, filters):
	condition=''
	if txt:
		condition += " and item_code like '%"+txt+"%'"	
	return frappe.db.sql('''SELECT name,CONCAT(item_name,description) as description  FROM `tabItem` WHERE item_group='Compound' AND item_code like 'C_%'  {condition}'''.format(condition=condition))

def create_dc(mt_doc):
	spp_dc = frappe.new_doc("SPP Delivery Challan")
	spp_dc.posted_date = getdate()
	spp_dc.source_warehouse = mt_doc.source_warehouse
	spp_dc.target_warehouse = mt_doc.target_warehouse
	spp_dc.operation = mt_doc.type
	spp_dc.purpose = "Material Transfer"
	for x in mt_doc.required_items:
		scan_barcode = x.scan_barcode
		if not x.scan_barcode:
			b_list = frappe.db.sql(""" SELECT mix_barcode FROM `tabImported Batches` WHERE mixbatchno like '%{code}%' """.format(code=x.spp_batch_number),as_dict=1)
			if b_list:
				scan_barcode = b_list[0].mix_barcode
		spp_dc.append("items",{
			"scan_barcode":scan_barcode,
			"item_code":x.item_code,
			"item_name":x.item_name,
			"spp_batch_no":x.spp_batch_number,
			"batch_no":x.batch_no,
			"qty":x.qty,
			"qty_uom":x.uom,

			})
	spp_dc.save(ignore_permissions=True)

def create_stock_entry(mt_doc):
	try:
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.stock_entry_type = "Material Transfer"
		# accept 0 qty as well
		stock_entry.from_warehouse = mt_doc.source_warehouse
		stock_entry.to_warehouse = mt_doc.target_warehouse
		for x in mt_doc.required_items:
			scan_barcode = x.scan_barcode
			if not x.scan_barcode:
				b_list = frappe.db.sql(""" SELECT mix_barcode FROM `tabImported Batches` WHERE mixbatchno like '%{code}%' """.format(code=x.spp_batch_number),as_dict=1)
				if b_list:
					scan_barcode = b_list[0].mix_barcode
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
				"spp_batch_number":x.spp_batch_number,
				"batch_no":x.batch_no,
				"mix_barcode":scan_barcode,
				})
		stock_entry.insert()
		# st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		# st_entry.insert()
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Material Transfer Failed")
		frappe.db.rollback()
		return {"status":"Failed"}

# Blanking Process

def create_blanking_wo(sp_entry):
	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabBOM Operation` BO ON BO.parent=B.name WHERE BO.operation ='Blanking' AND BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":sp_entry.required_items[0].item_code},as_dict=1)
	if bom:
		actual_weight = sum(flt(e_item.qty) for e_item in sp_entry.required_items)
		spp_settings = frappe.get_single("SPP Settings")
		work_station = None
		w_stations = frappe.db.get_all("BOM Operation",filters={"parent":bom[0].name},fields=['workstation'])
		if w_stations:
			work_station = w_stations[0].workstation
		import time
		wo = frappe.new_doc("Work Order")
		wo.naming_series = "MFG-WO-.YYYY.-"
		wo.company = "SPP"
		wo.fg_warehouse = sp_entry.target_warehouse
		wo.use_multi_level_bom = 0
		wo.skip_transfer = 1
		wo.source_warehouse = sp_entry.source_warehouse
		wo.wip_warehouse = spp_settings.wip_warehouse
		wo.transfer_material_against = "Work Order"
		wo.bom_no = bom[0].name
		wo.append("operations",{
			"operation":sp_entry.type,
			"bom":bom[0].name,
			"workstation":work_station,
			"time_in_mins":20,
			})
		wo.referenceid = round(time.time() * 1000)
		wo.production_item =bom[0].item
		wo.qty = actual_weight
		wo.planned_start_date = getdate()
		wo.docstatus = 1
		try:
			wo.save(ignore_permissions=True)
			update_job_cards(wo.name,actual_weight)
			se = make_blanking_stock_entry(sp_entry,wo.name,sp_entry.required_items[0].item_code,"Manufacture")
			if se.get("status")=="Success":
				return True
			else:
				return False
		except Exception as e:
			frappe.log_error(message=frappe.get_traceback(),title="Blanking WO Error")
			frappe.db.rollback()
			return False
	else:
		frappe.throw("No BOM found.")
def update_job_cards(wo,actual_weight):
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		for time_log in jc.time_logs:
			time_log.completed_qty = flt("{:.3f}".format(actual_weight))
			# time_log.time_in_mins = 20
		jc.total_completed_qty = flt("{:.3f}".format(actual_weight))
		jc.docstatus = 1
		jc.save(ignore_permissions=True)
def make_blanking_stock_entry(mt_doc,work_order_id,compound_code, purpose, qty=None):
	try:
		items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_number,qty,batch_no FROM `tabMixing Item` WHERE parent=%(parent_doc)s AND is_cut_bit_item=0""",{"parent_doc":mt_doc.name},as_dict=1)
		for sp_item in items:
			work_order = frappe.get_doc("Work Order", work_order_id)
			if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
				wip_warehouse = work_order.wip_warehouse
			else:
				wip_warehouse = None
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = purpose
			stock_entry.work_order = work_order_id
			stock_entry.company = work_order.company
			stock_entry.from_bom = 1
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			stock_entry.bom_no = work_order.bom_no
			stock_entry.set_posting_time = 0
			stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
			stock_entry.stock_entry_type = "Manufacture"
			# accept 0 qty as well
			stock_entry.employee = mt_doc.employee
			stock_entry.fg_completed_qty = work_order.qty
			if work_order.bom_no:
				stock_entry.inspection_required = frappe.db.get_value(
					"BOM", work_order.bom_no, "inspection_required"
				)
			stock_entry.from_warehouse = work_order.source_warehouse
			stock_entry.to_warehouse = work_order.fg_warehouse
			prod_item = None
			prod_item_qty = 0
			cl_spp_no = None
			# for x in work_order.required_items:
			if mt_doc.items:
				for b_bin in mt_doc.items:
					stock_entry.append("bins",{"blanking_bin":b_bin.blanking_bin})
			stock_entry.append("items",{
				"item_code":sp_item.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":sp_item.qty,
				"qty":sp_item.qty,
				"batch_no":sp_item.batch_no,
				"spp_batch_number":sp_item.spp_batch_number,
				"mix_barcode":sp_item.mix_barcode,
				})
			cut_bit_items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_number,qty,batch_no FROM `tabMixing Item` WHERE parent=%(parent_doc)s AND is_cut_bit_item=1""",{"parent_doc":mt_doc.name},as_dict=1)
			t_qty = sp_item.qty
			for cut_bit_item in cut_bit_items:
				stock_entry.append("items",{
				"item_code":cut_bit_item.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":cut_bit_item.qty,
				"qty":cut_bit_item.qty,
				"batch_no":cut_bit_item.batch_no,
				"spp_batch_number":cut_bit_item.spp_batch_number,
				"mix_barcode":cut_bit_item.mix_barcode,
				})
				t_qty += cut_bit_item.qty

			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name  INNER JOIN `tabBOM Operation` BO ON BO.parent=B.name WHERE BO.operation ='Blanking' AND BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1  """,{"item_code":sp_item.item_code},as_dict=1)
			if bom:
				stock_entry.append("items",{

					"item_code":bom[0].item,
					"s_warehouse":None,
					"t_warehouse":work_order.fg_warehouse,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":1,
					"transfer_qty":t_qty,
					"qty":t_qty,
					"spp_batch_number":sp_item.spp_batch_number,
					"mix_barcode":bom[0].item+"_"+sp_item.spp_batch_number.split("-")[0],
					})
				prod_item = bom[0].item
				prod_item_qty = t_qty
				cl_spp_no = sp_item.spp_batch_number
			stock_entry.insert()
			sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			sub_entry.docstatus=1
			sub_entry.save(ignore_permissions=True)
			c_stock_query = frappe.db.sql(""" SELECT SD.transfer_qty,SD.spp_batch_number,SD.batch_no,SD.stock_uom 
					  FROM `tabStock Entry Detail` SD
					  INNER JOIN `tabStock Entry` S ON SD.parent = S.name
					  WHERE SD.spp_batch_number = %(mix_barcode)s AND SD.t_warehouse = %(t_warehouse)s 
					  AND S.stock_entry_type = 'Material Transfer' AND S.docstatus = 1 AND SD.spp_batch_number is not null
					  ORDER BY S.creation DESC limit 1 """,{'mix_barcode':sp_item.spp_batch_number,'t_warehouse':work_order.source_warehouse},as_dict=1)		
			
			if c_stock_query:
				if c_stock_query[0].transfer_qty>work_order.qty:
					d_spp_batch_no = get_spp_batch_date(sp_item.item_code)
					spp_settings = frappe.get_single("SPP Settings")
					r_stock_entry = frappe.new_doc("Stock Entry")
					r_stock_entry.purpose = "Material Transfer"
					r_stock_entry.company = "SPP"
					r_stock_entry.naming_series = "MAT-STE-.YYYY.-"
					r_stock_entry.stock_entry_type = "Material Transfer"
					r_stock_entry.from_warehouse = mt_doc.source_warehouse
					r_stock_entry.to_warehouse = mt_doc.target_warehouse
					r_stock_entry.append("items",{
						"item_code":sp_item.item_code,
						"t_warehouse":spp_settings.default_cut_bit_warehouse,
						"s_warehouse":mt_doc.source_warehouse,
						"stock_uom": "Kg",
						"to_uom": "Kg",
						"uom": "Kg",
						"is_finished_item":0,
						"transfer_qty":c_stock_query[0].transfer_qty-work_order.qty,
						"qty":c_stock_query[0].transfer_qty-work_order.qty,
						"spp_batch_number":sp_item.spp_batch_number,
						"batch_no":sp_item.batch_no,
						"mix_barcode":"CB_"+sp_item.item_code,
						})
					# r_stock_entry.docstatus=1
					r_stock_entry.insert()
					# serial_no = 1
					# serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
					# if serial_nos:
					# 	serial_no = serial_nos[0].serial_no+1
					# sl_no = frappe.new_doc("SPP Batch Serial")
					# sl_no.posted_date = getdate()
					# sl_no.compound_code = sp_item.item_code
					# sl_no.serial_no = serial_no
					# sl_no.insert()
			# frappe.log_error(sp_item.item_code,'sp_item.item_code')
			# frappe.log_error(sp_item.spp_batch_number,'sp_item.spp_batch_number')
			frappe.db.sql(""" UPDATE `tabItem Clip Mapping` set is_retired = 1 WHERE compound=%(compound)s AND spp_batch_number=%(spp_batch_number)s""",{"spp_batch_number":sp_item.spp_batch_number,"compound":sp_item.item_code})
			frappe.db.commit()
			if mt_doc.blanking_bins:
				for clip in mt_doc.blanking_bins:
					clip_mapping = frappe.get_doc({
						"doctype":"Item Bin Mapping",
						"compound":prod_item,
						"qty":prod_item_qty,
						"is_retired":0,
						"blanking_bin":clip.blanking_bin,
						"spp_batch_number":cl_spp_no
						})
					clip_mapping.save(ignore_permissions=True)
					frappe.db.commit()
			return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Blanking SE Error")
		frappe.db.rollback()

		# frappe.throw(e)
		return {"status":"Failed"}

def get_spp_batch_date(compound):
	serial_no = 1
	serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
	if serial_nos:
		serial_no = serial_nos[0].serial_no+1
	month_key = getmonth(str(str(getdate()).split('-')[1]))
	l = len(str(getdate()).split('-')[0])
	compound_key = (str(getdate()).split('-')[0])[l - 2:]+month_key+str(str(getdate()).split('-')[2])+"X"+str(serial_no)
	return compound_key
def getmonth(code):
	if code == "01":
		return "A"
	if code == "02":
		return "B"
	if code == "03":
		return "C"
	if code == "04":
		return "D"
	if code == "05":
		return "E"
	if code == "06":
		return "F"
	if code == "07":
		return "G"
	if code == "08":
		return "H"
	if code == "09":
		return "I"
	if code == "10":
		return "J"
	if code == "11":
		return "K"
	if code == "12":
		return "L"
@frappe.whitelist()
def get_settings():
	return frappe.get_single("SPP Settings")