import frappe
from frappe.model.document import Document
from frappe.utils import (cint,date_diff,flt,get_datetime,get_link_to_form,getdate,nowdate
)
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series,get_details_by_lot_no,get_parent_lot,get_workstation_by_operation,generate_batch_no,delete_batches
# By GOPI
class InspectionEntry(Document):
	def validate(self):
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.lot_no:
			frappe.throw("Could not find the <b>Lot No</b>, Please scan the lot.")
		if not self.inspector_code:
			frappe.throw("Could not find the <b>Inspector Id</b>, Please scan the Inspector.")
		if not self.items:
			frappe.throw("Please add some items before save..!")
		if self.lot_no:
			if not self.inspection_type == "Final Visual Inspection":
				check_exist = frappe.db.get_all("Inspection Entry",filters={"name":("!=",self.name),"docstatus":1,"lot_no":self.lot_no,"inspection_type":self.inspection_type})
				if check_exist:
					frappe.throw(f"Inspection Entry for lot <b>{self.lot_no}</b> already exists..!")
		if self.inspection_type == "Lot Inspection" or self.inspection_type == "Line Inspection" or self.inspection_type == "Patrol Inspection":
			if not int(self.inspected_qty_nos):
				frappe.throw("Total inspected Qty not found..!")
		if self.inspection_type == "Incoming Inspection" or self.inspection_type == "Final Inspection":
			if not int(self.total_inspected_qty_nos):
				frappe.throw("Total inspected Qty not found..!")
		if self.inspection_type == "Final Visual Inspection" or self.inspection_type == "PDIR":
			if self.inspection_type == "Final Visual Inspection":
				if self.vs_pdir_qty:
					# self.vs_pdir_qty_after_rejection = self.vs_pdir_qty - (self.total_rejected_qty if self.total_rejected_qty else 0)
					self.vs_pdir_qty_after_rejection = self.total_inspected_qty_nos - (self.total_rejected_qty if self.total_rejected_qty else 0)

	def on_submit(self):
		if self.inspection_type == "Lot Inspection" or self.inspection_type == "Line Inspection" or self.inspection_type == "Patrol Inspection":
			if self.total_rejected_qty:
				resp_m = make_stock_entry(self)
				if resp_m and resp_m.get('status') == 'failed':
					rollback_entries(self,resp_m.get('message'))
			submit_moulding_entry(self)
		elif self.inspection_type == "Incoming Inspection" or self.inspection_type == "Final Inspection":
			if self.total_rejected_qty:
				resp_inc = make_inc_stock_entry(self)
				if resp_inc and resp_inc.get('status') == 'failed':
					rollback_entries(self,resp_inc.get('message'))
			if self.inspection_type == "Incoming Inspection":
				submit_deflash_receipt_entry(self)
		elif self.inspection_type == "Final Visual Inspection" or self.inspection_type == "PDIR":
			# if self.inspection_type == "PDIR":
			if self.inspection_type == "Final Visual Inspection":
				if self.total_rejected_qty:
					self.submit__vs_pdir()
				else:
					self.submit__vs_pdir_no_rejection()
		self.reload()

	def submit__vs_pdir(self):
		try:
			lrt= None
			psdir = make_vs_pdir_stock_entry(self)
			if psdir and psdir.get('status') == "success":
				exe_lrt = frappe.db.sql(f""" SELECT name FROM `tabLot Resource Tagging` WHERE scan_lot_no='{self.lot_no}' AND 
														docstatus = 1 LIMIT 1 """,as_dict = 1)
				if exe_lrt:
					lrt = frappe.get_doc("Lot Resource Tagging",exe_lrt[0].name)
					lrt__resp = lrt.run_method('make_wo_stock_entry')
					if lrt__resp:
						if lrt__resp.get('status') == "success":
							stock_id = frappe.db.sql(f" SELECT parent FROM `tabStock Entry Detail` WHERE source_ref_document = 'Inspection Entry' AND source_ref_id = '{self.name}' ",as_dict = 1)
							if stock_id:
								""" Update posting date and time """
								frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{stock_id[0].parent}' ")
								""" End """
								lrt.reload()
							else:
								frappe.throw('Stock Entry Reference not found for submiting <b>Visual Inspection Entry</b>..!')
						else:
							rollback_vs_pdir(self,lrt)
					else:
						frappe.throw('Something went wrong, not able to submit <b>Stock Entry</b>..!')
				else:
					submit_vs_entry__only(self)
			else:
				frappe.throw(psdir.get('message'))	
		except Exception:
			frappe.log_error(title="submit visual and pdir error",message=frappe.get_traceback())
			rollback_vs_pdir(self,lrt)
	
	def submit__vs_pdir_no_rejection(self):
		try:
			lrt= None
			exe_lrt = frappe.db.sql(f""" SELECT name,warehouse,batch_no FROM `tabLot Resource Tagging` WHERE scan_lot_no='{self.lot_no}' AND 
														docstatus = 1 LIMIT 1 """,as_dict = 1)
			if exe_lrt:
				bom = frappe.db.sql(""" SELECT B.name,BI.item_code FROM `tabBOM Item` BI 
								INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I 
								ON I.name=BI.item_code  WHERE B.item=%(item_code)s AND B.is_active=1 
								AND B.is_default =1 AND I.item_group = 'Products' """,{"item_code":self.product_ref_no},as_dict=1)
				if bom:
					stock_status = check_available_stock(exe_lrt[0].get("warehouse"),bom[0].item_code,exe_lrt[0].get("batch_no",""))
					if stock_status.get('status') == "Success":
						# update_qty = stock_status.get('qty')
						update_qty = self.total_inspected_qty_nos
						frappe.db.sql(f""" UPDATE `tabLot Resource Tagging` SET qty_after_rejection_nos = {update_qty}  
										WHERE scan_lot_no='{self.lot_no}' AND  docstatus = 1 """,as_dict = 1)
						frappe.db.commit()
						lrt = frappe.get_doc("Lot Resource Tagging",exe_lrt[0].name)
						lrt__resp = lrt.run_method('make_wo_stock_entry')
						if lrt__resp:
							if lrt__resp.get('status') == "success":
								stock_id = frappe.db.sql(f" SELECT parent FROM `tabStock Entry Detail` WHERE source_ref_document = 'Inspection Entry' AND source_ref_id = '{self.name}' ",as_dict = 1)
								if stock_id:
									""" Update posting date and time """
									frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{stock_id[0].parent}' ")
									""" End """
									lrt.reload()
								else:
									frappe.throw('Stock Entry Reference not found for submiting <b>Visual Inspection Entry</b>..!')
							else:
								rollback_vs_pdir(self,lrt)
						else:
							frappe.throw('Something went wrong, not able to submit <b>Stock Entry</b>..!')
					else:
						frappe.throw(stock_status.get('message'))
				else:
					frappe.throw(f"<b>Active and Default Bom</b> not found for the item <b>{self.product_ref_no}</b>..!")
			else:
				submit_vs_entry__only(self)
		except Exception:
			frappe.log_error(title="submit visual and pdir error",message=frappe.get_traceback())
			rollback_vs_pdir(self,lrt)

	def make__vs__pdir(self):
		resp_ = make_vs_pdir_stock_entry(self)
		return resp_

def rollback_vs_pdir(self,lrt = None):
	self.reload()
	def del_st(st_id):
		frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{st_id}' ")
		frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE name = '{st_id}' ")	
	# vu__ins__st_entry = frappe.db.get_value(self.doctype,{"lot_no":self.lot_no,"inspection_type":"Final Visual Inspection"},['name',"stock_entry_reference"],as_dict = 1)
	# if vu__ins__st_entry:
	# 	del_st(vu__ins__st_entry.stock_entry_reference)
	# 	frappe.db.set_value(self.doctype,vu__ins__st_entry.name,"stock_entry_reference","")
	# 	frappe.db.set_value(self.doctype,vu__ins__st_entry.name,"batch_no","")
	if self.stock_entry_reference:
		del_st(self.stock_entry_reference)
	exe_info = frappe.get_doc(self.doctype,self.name)
	exe_info.db_set('docstatus',0)
	exe_info.db_set('stock_entry_reference','')
	# exe_info.db_set('batch_no','')
	frappe.db.commit()
	if lrt:
		lrt.run_method('rollback_____')
			
def submit_moulding_entry(self):
	try:
		exe_insp = frappe.db.sql(f" SELECT name FROM `tabInspection Entry` WHERE (inspection_type = 'Line Inspection' OR inspection_type = 'Lot Inspection') AND docstatus = 1 AND lot_no='{self.lot_no}' ",as_dict = 1)	
		if exe_insp and len(exe_insp)>=2:
			rept_entry = frappe.db.get_all("Moulding Production Entry",{"scan_lot_number":self.lot_no,"docstatus":1},["name"])
			if rept_entry:
				mould__prod = frappe.get_doc("Moulding Production Entry",rept_entry[0].name)
				mould__prod.run_method("manual_on_submit")
			else:
				frappe.throw("There is no <b>Moulding Production Entry</b> found..!")
	except Exception:
		frappe.log_error(title="submit_moulding_entry",message=frappe.get_traceback())
		rollback_entries(self,"Moulding Production Entry Stock submission failed..!")

def submit_deflash_receipt_entry(self):
	try:
		rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"scan_lot_number":self.lot_no,"docstatus":1},["name"])
		if rept_entry:
			mould__prod = frappe.get_doc("Deflashing Receipt Entry",rept_entry[0].name)
			mould__prod.run_method("manual_on_submit")
		else:
			frappe.throw("There is no <b>Deflashing Receipt Entry</b> found..!")
	except Exception:
		frappe.log_error(title="submit_deflash_receipt_entry",message=frappe.get_traceback())
		rollback_entries(self,"Deflashing Receipt Entry Stock submission failed..!")

def rollback_entries(self,msg):
	try:
		self.reload()
		if self.stock_entry_reference:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(name)s""",{"name":self.stock_entry_reference})
			bl_dc = frappe.get_doc(self.doctype, self.name)
			bl_dc.db_set("docstatus", 0)
			frappe.db.commit()
			self.reload()
			frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		self.reload()
		frappe.log_error(title="rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def rollback__vs_entry__only(self,msg):
	try:
		self.reload()
		if self.vs_pdir_work_order_ref:
			stock__id = frappe.db.get_value("Stock Entry",{"work_order":self.vs_pdir_work_order_ref},"name")
			if stock__id:
				frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock__id}' ")
			frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE work_order = '{self.vs_pdir_work_order_ref}' ")
			frappe.db.sql(f" DELETE FROM `tabJob Card` WHERE work_order = '{self.vs_pdir_work_order_ref}' ")
			frappe.db.sql(f" DELETE FROM `tabWork Order` WHERE name = '{self.vs_pdir_work_order_ref}' ")
		lot__r = frappe.get_doc(self.doctype, self.name)
		lot__r.db_set("docstatus", 0)
		lot__r.db_set("vs_pdir_stock_entry_ref", '')
		frappe.db.commit()
		del__resp,batch__no = delete_batches([self.lot_no])
		if not del__resp:
			frappe.msgprint(batch__no)
		if msg:
			frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		self.reload()
		frappe.log_error(title="rollback__vs_entry__only error",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def submit_vs_entry__only(self):
	try:
		wo__resp,msg = create_work_order_vs_entry__only(self)
		if wo__resp:
			st__resp,msg = make_stock_entry_vs_entry__only(self,msg)
			if not st__resp:
				rollback__vs_entry__only(self,msg)
			else:
				self.reload()
		else:
			rollback__vs_entry__only(self,msg)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.submit_vs_entry__only")
		rollback__vs_entry__only(self,"Something went wrong not able to make <b>F/G</b> and <b>Rejection Stock Entry</b>..!")
		rollback_vs_pdir(self)

def make_stock_entry_vs_entry__only(self,work_order):
	try:
		batch__rep,batch__no = generate_batch_no(batch_id = "F"+self.lot_no,item = work_order.production_item,qty = self.vs_pdir_qty_after_rejection)
		if batch__rep:		
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Manufacture"
			stock_entry.work_order = work_order.name
			stock_entry.company = work_order.company
			stock_entry.from_bom = 1
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			stock_entry.bom_no = work_order.bom_no
			stock_entry.set_posting_time = 0
			stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
			stock_entry.stock_entry_type = "Manufacture"
			stock_entry.fg_completed_qty = work_order.qty
			if work_order.bom_no:
				stock_entry.inspection_required = frappe.db.get_value("BOM", work_order.bom_no, "inspection_required")
			stock_entry.from_warehouse = work_order.source_warehouse
			stock_entry.to_warehouse = work_order.fg_warehouse
			# d_spp_batch_no = get_spp_batch_date(self)
			# bcode_resp = generate_barcode("F_"+d_spp_batch_no)
			bcode_resp = generate_barcode(self.lot_no)
			for x in work_order.required_items:
				stock_entry.append("items",{
					"item_code":x.item_code,
					"s_warehouse":work_order.source_warehouse,
					"t_warehouse":None,
					"stock_uom": "Nos",
					"uom": "Nos",
					"use_serial_batch_fields":1,
					"transfer_qty":self.vs_pdir_qty_after_rejection,
					"qty":self.vs_pdir_qty_after_rejection,
					"spp_batch_number":self.spp_batch_number,
					"batch_no":self.batch_no,
					"mix_barcode":None})
			stock_entry.append("items",{
				"item_code":work_order.production_item,
				"s_warehouse":None,
				"t_warehouse":work_order.fg_warehouse,
				"stock_uom": "Nos",
				"uom": "Nos",
				"conversion_factor_uom":1,
				"is_finished_item":1,
				"transfer_qty":work_order.qty,
				"qty":work_order.qty,
				"use_serial_batch_fields":1,
				# "spp_batch_number": d_spp_batch_no,
				"spp_batch_number": self.lot_no,
				"batch_no":batch__no,
				"mix_barcode":bcode_resp.get("barcode_text"),
				"barcode_attach":bcode_resp.get("barcode"),
				"barcode_text":bcode_resp.get("barcode_text"),
				"source_ref_document":self.doctype,
				"source_ref_id":self.name
				})
			stock_entry.insert(ignore_permissions=True)
			""" Store stock entry ref in child table """
			frappe.db.set_value(self.doctype,self.name,"vs_pdir_stock_entry_ref",stock_entry.name)
			frappe.db.commit()
			""" End """
			sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			sub_entry.docstatus = 1
			sub_entry.save(ignore_permissions=True)
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{sub_entry.name}' ")
			""" End """
			ref_res,batch__no = generate_batch_no(batch_id = batch__no,reference_doctype = "Stock Entry",reference_name = sub_entry.name)
			if ref_res:
				return True,batch__no
			else:
				return False,"Stock Entry Reference update failed in Batch..!"
		else:
			return False,"Batch No generation failed"
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.make_stock_entry_vs_entry__only")
		frappe.db.rollback()
		return False,"Stock Entry creation failed."

def generate_barcode(compound):
	try:
		import code128
		import io
		from PIL import Image, ImageDraw, ImageFont
		barcode_param = barcode_text = str(compound)
		barcode_image = code128.image(barcode_param, height=120)
		w, h = barcode_image.size
		margin = 5
		new_h = h +(2*margin) 
		new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
		# put barcode on new image
		new_image.paste(barcode_image, (0, margin))
		# object to draw text
		draw = ImageDraw.Draw(new_image)
		new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=barcode_text), 'PNG')
		barcode = "/files/" + barcode_text + ".png"
		return {"barcode":barcode,"barcode_text":barcode_text}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.generate_barcode")

def create_work_order_vs_entry__only(doc_info):
	try:
		import time
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":doc_info.product_ref_no},as_dict=1)
		if bom:
			ope_wrk_pair = []
			operations = ["Final Visual Inspection"]
			for ope in operations:
				workstation__resp = get_workstation_by_operation(ope)
				if workstation__resp and workstation__resp.get('status') == "success":
					ope_wrk_pair.append({"workstation":workstation__resp.get('message'),"operation":ope})
				else:
					if workstation__resp:
						return False,workstation__resp.get('message')
					else:
						return False,f"Something went wrong while fetching <b>Workstation</b> details.."
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.unit_2_warehouse:
				return False,"Unit-2 warehouse not mapped in <b>SPP Settings</b>"
			if not spp_settings.default_time:
				return False,"Default operation time is not mapped in <b>SPP Settings</b>"
			if not spp_settings.wip_warehouse:
				return False,"Work in progress warehouse is not mapped in <b>SPP Settings</b>"
			wo = frappe.new_doc("Work Order")
			wo.naming_series = "MFG-WO-.YYYY.-"
			wo.company = "SPP"
			wo.fg_warehouse = spp_settings.unit_2_warehouse
			wo.use_multi_level_bom = 0
			wo.skip_transfer = 1
			wo.source_warehouse = doc_info.source_warehouse
			wo.wip_warehouse = spp_settings.wip_warehouse
			wo.transfer_material_against = "Work Order"
			wo.bom_no = bom[0].name
			for ope in operations:
				wo.append("operations",{
					"operation":ope,
					"bom":bom[0].name,
					"workstation":list(filter(lambda x:x.get('operation') == ope,ope_wrk_pair))[0].get('workstation'),
					"time_in_mins":spp_settings.default_time,
					})
			wo.referenceid = round(time.time() * 1000)
			wo.production_item = bom[0].item
			wo.qty = doc_info.vs_pdir_qty_after_rejection
			wo.insert(ignore_permissions=True)
			frappe.db.set_value(doc_info.doctype,doc_info.name,"vs_pdir_work_order_ref",wo.name)
			frappe.db.commit()
			wo_ = frappe.get_doc("Work Order",wo.name)
			wo_.docstatus = 1
			wo_.save(ignore_permissions=True)
			update_job_cards_vs_entry__only(wo.name,doc_info.vs_pdir_qty_after_rejection,doc_info,doc_info.product_ref_no)
			return True,wo
		else:
			return False,f"Bom is not found for the item to produce - <b>{doc_info.product_ref_no}</b>"
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.create_work_order_vs_entry__only")
		return False,"Work order creation failed."

def update_job_cards_vs_entry__only(wo,actual_weight,doc_info,item):
	spp_settings = frappe.get_single("SPP Settings")
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	operations = frappe.db.get_all("Work Order Operation",filters={"parent":wo},fields=['time_in_mins'])
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		jc.append("time_logs", {
			"from_time": now(),
			"completed_qty": flt(actual_weight,3),
			"time_in_mins": spp_settings.default_time
		})
		for time_log in jc.time_logs:
			time_log.completed_qty = flt("{:.3f}".format(actual_weight))
			if operations:
				time_log.time_in_mins = spp_settings.default_time
		jc.total_completed_qty = flt("{:.3f}".format(actual_weight))
		jc.batch_code = doc_info.lot_no
		jc.docstatus = 1
		jc.save(ignore_permissions=True)

def make_vs_pdir_stock_entry(self):
	try:
		# Find p - product item by f-item
		bom = frappe.db.sql(""" SELECT B.name,BI.item_code FROM `tabBOM Item` BI 
								INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I 
								ON I.name=BI.item_code  WHERE B.item=%(item_code)s AND B.is_active=1 
								AND B.is_default =1 AND I.item_group = 'Products' """,{"item_code":self.product_ref_no},as_dict=1)
		if bom:
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.unit_2_warehouse:
				frappe.throw("<b>Unit-2 Warehouse</b> is not mapped in <b>SPP Settings</b>..!")
			if not spp_settings.pdir_visual_t__warehouse:
				frappe.throw("<b>PDIR & Final Visual Inspection Rejection Warehouse</b> is not mapped in <b>SPP Settings</b>..!")
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Material Transfer"
			stock_entry.company = "SPP"
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			stock_entry.stock_entry_type = "Material Transfer"
			stock_entry.from_warehouse = self.source_warehouse if self.source_warehouse else spp_settings.unit_2_warehouse
			stock_entry.to_warehouse = spp_settings.pdir_visual_t__warehouse
			stock_entry.append("items",{
				"item_code":bom[0].item_code,
				"s_warehouse":self.source_warehouse if self.source_warehouse else spp_settings.unit_2_warehouse,
				"t_warehouse":spp_settings.pdir_visual_t__warehouse,
				"stock_uom": "Nos",
				"uom": "Nos",
				"use_serial_batch_fields":1,
				"spp_batch_number":self.spp_batch_number,
				"batch_no":self.batch_no,
				"transfer_qty":self.total_rejected_qty,
				"qty":self.total_rejected_qty,
				"source_ref_document":self.doctype,
				"source_ref_id":self.name
				})
			stock_entry.insert(ignore_permissions = True)
			frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
			frappe.db.commit()
			sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			sub_entry.docstatus=1
			sub_entry.save(ignore_permissions=True)
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{sub_entry.name}' ")
			""" End """
			exe_lrt = frappe.db.sql(f""" SELECT name,warehouse,batch_no FROM `tabLot Resource Tagging` WHERE scan_lot_no='{self.lot_no}' AND 
														docstatus = 1 LIMIT 1 """,as_dict = 1)
			if exe_lrt:
				stock_status = check_available_stock(exe_lrt[0].get("warehouse"),bom[0].item_code,exe_lrt[0].get("batch_no",""))
				if stock_status.get('status') == "Success":
					# update_qty = stock_status.get('qty') - self.total_rejected_qty
					update_qty = self.total_inspected_qty_nos - self.total_rejected_qty
					frappe.db.sql(f""" UPDATE `tabLot Resource Tagging` SET qty_after_rejection_nos = {update_qty}  
										WHERE scan_lot_no='{self.lot_no}' AND  docstatus = 1 """,as_dict = 1)
				else:
					return {"status":'failed',"message":stock_status.get('message')}
			frappe.db.commit()
			return {"status":"success"}
		else:
			return {"status":"failed","message":f"<b>Active and Default Bom</b> not found for the item <b>{self.product_ref_no}</b>..!"}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.make_vs_pdir_stock_entry")
		return {"status":"failed","message":"Something went wrong, not able to submit <b>Final Visual Inspection</b> stock entry..!"}

def make_stock_entry(self):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":self.product_ref_no},as_dict=1)
		if bom:
			# check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			# if check_uom:
			# 	each_no_qty = 1 / check_uom[0].conversion_factor
			moulding_ref = frappe.db.get_value("Job Card",{"batch_code":self.lot_no},["mould_reference","production_item"],as_dict = 1)
			if moulding_ref:
				# on 8/3/23
				# wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":frappe.db.get_value("Asset",moulding_ref.mould_reference,"item_code")},"avg_blank_wtproduct_gms")
				wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":frappe.db.get_value("Asset",moulding_ref.mould_reference,"item_code"),"spp_ref":moulding_ref.production_item,"mould_status":"ACTIVE"},"avg_blank_wtproduct_gms")
				# end
				# each_no_qty = flt(float(wt_per_pi_gms) / 1000 , 3) 
				each_no_qty = float(wt_per_pi_gms) / 1000 
				t_qty = each_no_qty * self.total_rejected_qty
				if flt(t_qty, 3)>0:
					spp_settings = frappe.get_single("SPP Settings")
					stock_entry = frappe.new_doc("Stock Entry")
					stock_entry.purpose = "Material Transfer"
					stock_entry.company = "SPP"
					stock_entry.naming_series = "MAT-STE-.YYYY.-"
					""" For identifying procees name to change the naming series the field is used """
					naming_status,naming_series = get_stock_entry_naming_series(spp_settings,self.inspection_type)
					if naming_status:
						stock_entry.naming_series = naming_series
					""" End """
					stock_entry.stock_entry_type = "Material Transfer"
					stock_entry.from_warehouse = spp_settings.unit_2_warehouse
					stock_entry.to_warehouse = spp_settings.rejection_warehouse
					stock_entry.append("items",{
						"item_code":self.product_ref_no,
						"s_warehouse":spp_settings.unit_2_warehouse,
						"t_warehouse":spp_settings.rejection_warehouse,
						"stock_uom": "Kg",
						"uom": "Kg",
						# "batch_no":self.batch_no if self.batch_no else "",
						"conversion_factor_uom":1,
						"transfer_qty":flt(t_qty, 3),
						"qty":flt(t_qty, 3),
						"inspection_ref":self.name,
						"source_ref_document":self.doctype,
						"source_ref_id":self.name
						})
					
					stock_entry.insert(ignore_permissions=True)
					frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
					frappe.db.commit()
					""" Restrict stock entry submission for line and patrol respections """
					# if self.inspection_type == "Line Inspection" or self.inspection_type == "Patrol Inspection":
					# 	if int(self.moulding_production_completed) == 1:
					# 		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
					# 		sub_entry.docstatus=1
					# 		sub_entry.save(ignore_permissions=True)
					# else:
					# 	sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
					# 	sub_entry.docstatus=1
					# 	sub_entry.save(ignore_permissions=True)
					return {"status":"success"}
			else:
				frappe.throw("Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>")
		else:
			frappe.throw("No BOM found associated with the item <b>"+self.product_ref_no+"</b>")
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.make_stock_entry")
		return {"status":"failed","message":"Stock Entry creation error..!"}

def make_inc_stock_entry(self):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		""" For identifying procees name to change the naming series the field is used """
		naming_status,naming_series = get_stock_entry_naming_series(spp_settings,self.inspection_type)
		if naming_status:
			stock_entry.naming_series = naming_series
		""" End """
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.from_warehouse = spp_settings.unit_2_warehouse
		stock_entry.to_warehouse = spp_settings.rejection_warehouse
		stock_entry.append("items",{
			"item_code":self.product_ref_no,
			"s_warehouse":spp_settings.unit_2_warehouse,
			"t_warehouse":spp_settings.rejection_warehouse,
			"stock_uom": "Nos",
			"uom": "Nos",
			"spp_batch_number":self.spp_batch_number,
			# "batch_no":self.batch_no,
			"transfer_qty":self.total_rejected_qty,
			"qty":self.total_rejected_qty,
			"inspection_ref":self.name,
			"source_ref_document":self.doctype,
			"source_ref_id":self.name
			})
		stock_entry.insert(ignore_permissions = True)
		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
		frappe.db.commit()
		""" Restrict stock entry submission """
		# sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		# sub_entry.docstatus=1
		# sub_entry.save(ignore_permissions=True)
		return {"status":"success"}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.make_inc_stock_entry")
		return {"status":"failed","message":"Stock Entry creation error..!"}


def check_available_stock(warehouse,item,batch_no):
	try:
		if batch_no:
			query = f""" SELECT qty FROM `tabItem Batch Stock Balance` WHERE item_code='{item}' AND warehouse='{warehouse}' AND batch_no='{batch_no}' """
		else:
			query = f""" SELECT qty FROM `tabItem Batch Stock Balance` WHERE item_code='{item}' AND warehouse='{warehouse}' """
		qty = frappe.db.sql(query,as_dict=1)
		if qty:
			if qty[0].qty:
				return {"status":"Success","qty":qty[0].qty}
			else:
				return {"status":"Failed","message":f"Stock is not available for the item <b>{item}</b>"}	
		else:
			return {"status":"Failed","message":f"Stock is not available for the item <b>{item}</b>"}
	except Exception:	
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.check_available_stock")
		return {"status":"Failed","message":"Something went wrong"}

@frappe.whitelist(allow_guest=True)
def validate_lot_number(batch_no,docname,inspection_type):
	try:
		if inspection_type == "Line Inspection" or inspection_type == "Patrol Inspection":
			check_exist = frappe.db.get_value("Inspection Entry",{"name":("!=",docname),"docstatus":1,"lot_no":batch_no,"inspection_type":inspection_type},"name")
			if check_exist:
				return {"status":"Failed","message":"Already Inspection Entry is created for this lot number."}
			else:
				check_lot_issue = frappe.db.sql(""" 
							SELECT 
								JB.mould_reference,JB.total_completed_qty,JB.workstation,
								JB.work_order,JB.name as job_card,JB.production_item,JB.batch_code,
								E.employee_name as employee 
							FROM `tabJob Card` JB 
								LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JB.name
								LEFT JOIN `tabEmployee` E ON LG.employee = E.name
							WHERE 
								JB.batch_code=%(lot_no)s LIMIT 1 """,{"lot_no":batch_no},as_dict = 1)
				if not check_lot_issue:
					return {"status":"Failed","message":f"Job Card not found for the scanned lot <b>{batch_no}</b>"}
				else:
					rept_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":batch_no,"docstatus":1},"stock_entry_reference")
					if rept_entry:
						check_lot_issue[0].moulding_production_entry = 1
					else:
						check_lot_issue[0].moulding_production_entry = 0
					check_lot_issue[0].qty_from_item_batch = 0
					""" Multi Bom Validation """
					bom = frappe.db.sql(""" 
						 		SELECT
						 			 B.name,B.item 
						 		FROM 
						 			`tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name 
						 			INNER JOIN `tabItem` I ON I.name=B.item  
						 		WHERE 
						 			BI.item_code=%(item_code)s AND B.is_active=1 AND 
						 			I.default_bom=B.name LIMIT 1 """,{"item_code":check_lot_issue[0].production_item},as_dict = 1)
					if bom:
						bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
						if len(bom__) > 1:
							return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
						""" Add UOM for rejection in No's """
						if check_lot_issue[0].mould_reference:
							wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":frappe.db.get_value("Asset",check_lot_issue[0].mould_reference,"item_code"),"spp_ref":check_lot_issue[0].production_item,"mould_status":"ACTIVE"},"avg_blank_wtproduct_gms")
							if wt_per_pi_gms and float(wt_per_pi_gms):
								""" This is equal to 1 No's """
								check_lot_issue[0].one_no_qty_equal_kgs = float(wt_per_pi_gms) / 1000 
							else:
								return {"status":"Failed","message":f"Avg Blank Wt/Product not found in <b>Mould Specification</b>"}
						else:
							return {"status":"Failed","message":f" Mould Reference not found for the scanned lot <b>{batch_no}</b> for finding UOM "}
						""" End """
					else:
						return {"status":"Failed","message":f"BOM is not found for <b>Item to Produce</b>"}
					""" End """ 
					user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
					item_batch_no = ""
					st_details = frappe.db.sql(""" 
								SELECT 
									IB.spp_batch_number 
								FROM 
									`tabJob Card` JB 
									INNER JOIN `tabBlank Bin Issue` B ON B.job_card = JB.name
									INNER JOIN `tabItem Bin Mapping` IB ON B.bin = IB.blanking__bin
									INNER JOIN `tabAsset` A ON IB.blanking__bin = A.name
								WHERE 
									JB.name = %(jb_name)s AND IB.is_retired = 0
								LIMIT 1 
								""",{"jb_name":check_lot_issue[0].job_card},as_dict = 1)
					check_lot_issue[0].spp_batch_no = ""
					if st_details:
						check_lot_issue[0].spp_batch_no = st_details[0].spp_batch_number
					chk_st_details = frappe.db.sql(""" 
									SELECT 
										SD.batch_no 
									FROM 
										`tabStock Entry Detail` SD
										INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent
										INNER JOIN `tabWork Order` W ON W.name = SE.work_order
										INNER JOIN `tabJob Card` JB ON JB.work_order = W.name
									WHERE 
										JB.batch_code = %(lot_no)s AND SD.t_warehouse IS NOT NULL
									LIMIT 1 
									""",{"lot_no":batch_no},as_dict = 1)
					if chk_st_details:
						item_batch_no = chk_st_details[0].batch_no
					check_lot_issue[0].batch_no = item_batch_no
					check_lot_issue[0].user_name = user_name
					return {"status":"Success","message":check_lot_issue[0]}
						
		elif inspection_type == "Lot Inspection":
			check_exist = frappe.db.get_value("Inspection Entry",{"name":("!=",docname),"docstatus":1,"lot_no":batch_no,"inspection_type":inspection_type},"name")
			if check_exist:
				return {"status":"Failed","message":"Already Inspection Entry is created for this lot number."}
			else:
				check_lot_issue = frappe.db.sql(""" 
									SELECT 
										JB.mould_reference,JB.total_qty_after_inspection,JB.total_completed_qty,
										JB.workstation,JB.work_order,JB.name as job_card,JB.production_item,
										JB.batch_code,E.employee_name as employee 
									FROM 
										`tabJob Card` JB 
										LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JB.name
										LEFT JOIN `tabEmployee` E ON LG.employee = E.name
									WHERE 
										JB.batch_code=%(lot_no)s LIMIT 1 """,{"lot_no":batch_no},as_dict = 1)
				if not check_lot_issue:
					return {"status":"Failed","message":f"Job Card not found for the scanned lot <b>{batch_no}</b>"}
				else:
					rept_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":batch_no,"docstatus":1},"stock_entry_reference")
					if not rept_entry:
						return {"status":"Failed","message":f"There is no <b>Moulding Production Entry</b> found for the lot <b>{batch_no}</b>"}
					else:
						""" Multi Bom Validation """
						bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name LIMIT 1 """,{"item_code":check_lot_issue[0].production_item},as_dict=1)
						if bom:
							bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
							if len(bom__) > 1:
								return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
							""" Add UOM for rejection in No's """
							if check_lot_issue[0].mould_reference:
								item = frappe.db.get_value("Asset",check_lot_issue[0].mould_reference,"item_code")
								if item:
									wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":item,"spp_ref":check_lot_issue[0].production_item,"mould_status":"ACTIVE"},"avg_blank_wtproduct_gms")
									if wt_per_pi_gms and float(wt_per_pi_gms):
										""" This is equal to 1 No's """
										check_lot_issue[0].one_no_qty_equal_kgs = float(wt_per_pi_gms) / 1000 
									else:
										return {"status":"Failed","message":f"Avg Blank Wt/Product not found in <b>Mould Specification</b>"}
								else:
									return {"status":"Failed","message":f"Mould item not found..!"}
							else:
								return {"status":"Failed","message":f" Mould Reference not found for the scanned lot <b>{batch_no}</b> for finding UOM "}
							""" End """
						else:
							return {"status":"Failed","message":f"BOM is not found for <b>Item to Produce</b>"}
						""" End """
						user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
						item_batch_no = ""
						st_details = frappe.db.sql(""" 
								SELECT 
									IB.spp_batch_number 
								FROM 
									`tabJob Card` JB 
									INNER JOIN `tabBlank Bin Issue` B ON B.job_card = JB.name
									INNER JOIN `tabItem Bin Mapping` IB ON B.bin = IB.blanking__bin
									INNER JOIN `tabAsset` A ON IB.blanking__bin = A.name
								WHERE 
									JB.name = %(jb_name)s AND IB.is_retired = 0 LIMIT 1 
								""",{"jb_name":check_lot_issue[0].job_card},as_dict = 1)
						check_lot_issue[0].spp_batch_no = ""
						if st_details:
							check_lot_issue[0].spp_batch_no = st_details[0].spp_batch_number
						chk_st_details = frappe.db.sql(""" SELECT SD.batch_no FROM `tabStock Entry Detail` SD
													INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent
													INNER JOIN `tabWork Order` W ON W.name = SE.work_order
													INNER JOIN `tabJob Card` JB ON JB.work_order = W.name
													WHERE JB.batch_code = %(lot_no)s AND SD.t_warehouse is not null
									 				LIMIT 1 
													""",{"lot_no":batch_no},as_dict=1)
						if chk_st_details:
							item_batch_no = chk_st_details[0].batch_no
						check_lot_issue[0].batch_no = item_batch_no
						check_lot_issue[0].user_name = user_name
						return {"status":"Success","message":check_lot_issue[0]}
		elif inspection_type == "Incoming Inspection" or inspection_type == "Final Inspection":
			check_exist = frappe.db.get_value("Inspection Entry",{"lot_no":batch_no,"docstatus":1,"inspection_type":inspection_type,"name":("!=",docname)})
			if check_exist:
				return {"status":"Failed","message":f" Already {inspection_type} Entry is created for this lot number <b>{batch_no}</b>."}
			""" Validate job card """
			sublot__resp = check_sublot(batch_no)
			if not sublot__resp:
				check_lot_issue = frappe.db.sql(""" SELECT JB.name FROM `tabJob Card` JB WHERE JB.batch_code=%(lot_no)s AND operation="Deflashing" LIMIT 1 """,{"lot_no":batch_no},as_dict=1)
				if not check_lot_issue:
					return {"status":"Failed","message":f"Job Card not found for the scanned lot <b>{batch_no}</b>"}
				else:
					rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":batch_no,"docstatus":1},["stock_entry_reference"],as_dict = 1)
					if rept_entry:
						if not rept_entry.stock_entry_reference:
							return {"status":"Failed","message":f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{batch_no}</b>"}
						else:
							product_details = frappe.db.sql(f""" SELECT  JC.work_order,E.employee_name as employee,SED.item_code as production_item,JC.batch_code,JC.workstation,SED.qty as total_completed_qty,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
																INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
																LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry.stock_entry_reference}' AND SED.deflash_receipt_reference='{batch_no}' LIMIT 1 """,as_dict=1)
							if product_details:
								""" Multi Bom Validation """
								bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":product_details[0].get("production_item")},as_dict=1)
								if len(bom__) > 1:
									return {"status":"Failed","message":f"Multiple BOM's found for the Item - <b>{product_details[0].get('production_item')}</b>"}
								query = f""" SELECT 
												SED.t_warehouse as from_warehouse,SED.batch_no 
											FROM `tabStock Entry Detail` SED 
												INNER JOIN `tabStock Entry` SE ON SED.parent=SE.name 
											WHERE 
												SED.item_code='{product_details[0].get("production_item")}' 
												AND SE.work_order='{product_details[0].get("work_order")}' LIMIT 1 """
								spp_and_batch = frappe.db.sql(query,as_dict=1)
								if spp_and_batch:
									return {"status":"Success","message":product_details[0]}
								else:
									return {"status":"Failed","message":f"There is no <b>Stock Entry</b> found for the scanned lot <b>{batch_no}</b>"}
							else:
								return {"status":"Failed","message":f"Detail not found for the lot no <b>{batch_no}</b>"}
					else:
						return {"status":"Failed","message":f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{batch_no}</b>"}
		
		elif inspection_type == "Final Visual Inspection" or inspection_type == "PDIR":
			rept_entry = frappe.db.get_value("Lot Resource Tagging",{"scan_lot_no":batch_no,"docstatus":1},["available_qty","name","batch_no","bom_no","product_ref as production_item","warehouse","scan_lot_no as batch_code","scan_lot_no as spp_batch_number","job_card"],as_dict = 1)
			if rept_entry:	
				work_station__ = check_return_workstation(rept_entry.bom_no,inspection_type)
				if work_station__ and work_station__.get('status') == 'success':
					rept_entry.workstation = work_station__.get('message')
					if inspection_type == "PDIR":
						check_exist = frappe.db.get_value("Inspection Entry",{"lot_no":batch_no,"docstatus":1,"inspection_type":"Final Visual Inspection"})
						if not check_exist:
							return {"status":"Failed","message":f"Please complete the <b>Final Visual Inspection</b> before <b>PDIR</b> operation for the scanned lot number <b>{batch_no}</b>."}
					bom_resp__ = check_multi_bom_vls(rept_entry.production_item)
					if bom_resp__ and bom_resp__.get('status') == 'Success':
						opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
						opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_resp__.get('bom_no')},as_dict=1)
						if not opeartion_exe:
							return {"status":"Failed","message":f"Operations not found in the BOM <b>{bom_resp__.get('bom_no')}</b>"}
						else:
							opt__type = frappe.db.sql(f""" SELECT DISTINCT operation_type FROM `tabLot Resource Tagging` WHERE scan_lot_no='{batch_no}' AND 
														docstatus = 1 """,as_dict = 1)
							if not opt__type:
								return {"status":"Failed","message":f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k.operation for k in opeartion_exe)}</b>,<br>Before the start of operation <b>{inspection_type}</b>."}
							else:
								if len(opt__type) == len(opeartion_exe):
									stock_status = check_available_stock(rept_entry.get("warehouse"),bom_resp__.get("item__code"),rept_entry.get("batch_no",""))
									if stock_status.get('status') == "Success":
										rept_entry.available_qty = stock_status.get('qty')
										rept_entry._1kg_eq_nos = bom_resp__.get('_1kg_eq_nos')
										rept_entry.available_qty_nos = stock_status.get('qty')
										_lno_eq_kgs = 1 / bom_resp__.get('_1kg_eq_nos')
										rept_entry.available_qty_kgs = round(_lno_eq_kgs * stock_status.get('qty'),2)
										return {"status":"Success","message":rept_entry}
									else:
										return {"status":stock_status.get('status'),"message":stock_status.get('message')}
								else:
									exe_operations = [x.operation_type for x in opt__type]
									not_completed_oper = list(filter(lambda x : x.operation not in exe_operations,opeartion_exe))
									return {"status":"Failed","message":f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k.operation for k in not_completed_oper)}.</b><br>Before the start of operation <b>{inspection_type}</b>."}
					else:
						if bom_resp__:
							return {"status":bom_resp__.get('status'),"message":bom_resp__.get('message')}
						else:
							return {"status":"Failed","message":f"Something went wrong not able to fetch <b>BOM</b> details..!"}
				else:
					return {"status":"Failed","message":work_station__.get('message')	}
			else:
				vs_ins__resp = check_vs_only_exists(batch_no,inspection_type)
				if vs_ins__resp and vs_ins__resp.get('status') == "not exists":
					return {"status":"Failed","message":f"There is no data found for the scanned lot <b>{batch_no}</b>"}
				elif not vs_ins__resp:
					return {"status":"Failed","message":f"Not able to fetch details of the lot <b>{batch_no}</b>"}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.validate_lot_number")
		return {"status":"Failed","message":"Something went wrong."}

def check_multi_bom_vls(item_code):
	bom_res = frappe.db.sql(""" SELECT B.name,B.item,BI.item_code item__code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":item_code},as_dict=1)
	if bom_res:
		""" Multi Bom Validation """
		bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_active=1 """,{"item_code":item_code},as_dict=1)
		if len(bom__) > 1:
			return {"status":"Failed","message":f"Multiple BOM's found for the Item - <b>{item_code}</b>"}
		check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":item_code,"uom":"Kg"},fields=['conversion_factor'])
		if check_uom:
			return {"status":"Success","bom_no":bom_res[0].name,"item__code":bom_res[0].item__code,"_1kg_eq_nos":check_uom[0].conversion_factor}
		else:
			return {"status":"Failed","message":"Please define UOM for Kgs for the item <b>"+item_code+"</b>"}
	else:
		return {"status":"Failed","message":f"Active and Default <b>BOM</b> is not found for the Item - <b>{item_code}</b>"}

def check_return_workstation(bom_no,operation_type):
	workstation__resp = get_workstation_by_operation(operation_type)
	if workstation__resp and workstation__resp.get('status') == "success":
		return {"status":"success","message":workstation__resp.get('message')}
	else:
		if workstation__resp:
			return {"status":"failed","message":workstation__resp.get('message')}
		else:
			return {"status":"failed","message":f"Something went wrong while fetching <b>Workstation</b> details.."}

# on 28/3/24 for optimization

def lrt_check_available_stock(warehouse,item,batch_no):
	try:
		if batch_no:
			query = f""" SELECT qty FROM `tabItem Batch Stock Balance` WHERE item_code='{item}' AND warehouse='{warehouse}' AND batch_no='{batch_no}' """
		else:
			query = f""" SELECT qty FROM `tabItem Batch Stock Balance` WHERE item_code='{item}' AND warehouse='{warehouse}' """
		qty = frappe.db.sql(query,as_dict=1)
		if qty:
			if qty[0].qty:
				return {"status":"success","qty":qty[0].qty}
			else:
				return {"status":"failed","message":f"Stock is not available for the item <b>{item}</b>"}	
		else:
			return {"status":"failed","message":f"Stock is not available for the item <b>{item}</b>"}
	except Exception:	
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.check_available_stock")
		return {"status":"failed","message":"Something went wrong"}

def lrt_check_uom_bom(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
			""" End """
			return {"status":"success","bom":bom[0].name,"item":bom[0].item}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.check_uom_bom")
		return {"status":"failed","message":"Something went wrong"}

def lrt_check__u1_warehouse(bar_code,operation_type):
	exe_u1 = frappe.db.sql(f""" SELECT DU.stock_entry_reference,DUI.product_ref FROM `tabDespatch To U1 Entry` DU INNER JOIN `tabDespatch To U1 Entry Item` DUI 
	                            ON DUI.parent = DU.name WHERE DUI.lot_no = '{bar_code}' AND DU.docstatus = 1 LIMIT 1 """,as_dict = 1)
	if exe_u1:
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.p_target_warehouse:
			return {"status":"failed","message": "U1 warehouse not mapped in SPP Settings..!"}
		else:
			cond__ = f" AND IBSB.warehouse = '{spp_settings.p_target_warehouse}' AND IBSB.item_code='{exe_u1[0].product_ref}' "
			lot_info = get_details_by_lot_no(bar_code,condition__ = cond__,from_ledger_entry = True,ignore_lot_val = True)
			if lot_info.get("status") == "success":
				if lot_info.get('data'):
					if lot_info.get('data').get('qty'):
						lot_info['data']['from_warehouse'] = lot_info.get('data').get('warehouse')
						lot_info['data']['qty_from_item_batch'] = lot_info.get('data').get('qty')
						bom_uom_resp = lrt_check_uom_bom(lot_info['data'].item_code)
						if bom_uom_resp.get('status') == "success":
							lot_info['data']['bom_no'] = bom_uom_resp.get('bom')
							lot_info['data']['production_item'] = bom_uom_resp.get('item')
							opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
							opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_uom_resp.get('bom')},as_dict=1)
							lot_info['data'].bom_operations = opeartion_exe
							return {"status":'success',"message": lot_info['data']}
						else:
							return {"status":bom_uom_resp.get('status'),"message": bom_uom_resp.get('message')}
					else:
						return {"status":"failed","message": f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"}
				else:
					return {"status":"failed","message":lot_info.get('message')}
			else:
				return {"status":"failed","message":lot_info.get('message')}
	else:
		return False

def lrt_check__material_recp(bar_code,operation_type):
	lot_info = get_details_by_lot_no(bar_code,transfer_other_warehouse = True,ref_doc="Incoming Inspection Entry")
	if lot_info.get("status") == "success":
		if lot_info.get('data'):
			""" This is not covered in work flow , this is for material receipt func """
			if lot_info.get('data').get('stock_entry_type') == "Material Receipt":
				return lrt_material_respt_return_response(lot_info,operation_type)
				""" End """
			else:
				""" First validate material receipt entry exists """
				parent__lot = get_parent_lot(bar_code,field_name = "material_receipt_parent")
				if parent__lot and parent__lot.get('status') == 'success':
					return lrt_material_respt_return_response(lot_info,operation_type)
				""" End """
		else:
			return {"status":"failed","message":lot_info.get('message')}
	return False

def lrt_material_respt_return_response(lot_info,operation_type = None):
	if lot_info.get('data').get('qty'):
		lot_info['data']['from_warehouse'] = lot_info.get('data').get('t_warehouse')
		lot_info['data']['qty_from_item_batch'] = lot_info.get('data').get('qty')
		bom_uom_resp = lrt_check_uom_bom(lot_info['data'].item_code)
		if bom_uom_resp.get('status') == "success":
			lot_info['data']['bom_no'] = bom_uom_resp.get('bom')
			lot_info['data']['production_item'] = bom_uom_resp.get('item')
			opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
			opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_uom_resp.get('bom')},as_dict=1)
			lot_info['data'].bom_operations = opeartion_exe
			return {"status":"success","message":lot_info['data']}
		else:
			return {"status": bom_uom_resp.get('status'),"message":bom_uom_resp.get('message')}
	else:
		return {"status": "failed","message":f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"}

def lrt_check__u1_sublot(lot_info,bar_code,operation_type):
	query = f""" SELECT despatch_u1_parent FROM `tabSub Lot Creation` WHERE CASE WHEN sub_lot_no = '{bar_code}' THEN  sub_lot_no = '{bar_code}' ELSE scan_lot_no = '{bar_code}' END LIMIT 1 """
	first__p = frappe.db.sql(query, as_dict = 1)
	if first__p and first__p[0].despatch_u1_parent:
		return lrt_material_respt_return_response(lot_info,operation_type)
	return False	

def lrt_return_response(parent__lot,lot_info,operation_type):
	jc_ins_resp_ = lrt_validate_dre_ins_jc(parent__lot,ignore_jobcard = True)
	if jc_ins_resp_.get("status") == "success":
		if lot_info.get('data').get('qty'):
			lot_info['data']['from_warehouse'] = lot_info.get('data').get('t_warehouse')
			lot_info['data']['qty_from_item_batch'] = lot_info.get('data').get('qty')
			bom_uom_resp = lrt_check_uom_bom(lot_info['data'].item_code)
			if bom_uom_resp.get('status') == "success":
				lot_info['data']['bom_no'] = bom_uom_resp.get('bom')
				lot_info['data']['production_item'] = bom_uom_resp.get('item')
				opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
				opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_uom_resp.get('bom')},as_dict=1)
				lot_info['data'].bom_operations = opeartion_exe
				return {"status":"success","message":lot_info['data']}
			else:
				return {"status": bom_uom_resp.get('status'),"message":bom_uom_resp.get('message')}
		else:
			return {"status": "failed","message":f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"}
	else:
		return jc_ins_resp_

def lrt_check_sublot(bar_code,operation_type):
	u1__resp = lrt_check__u1_warehouse(bar_code,operation_type)
	if not u1__resp:
		recept__resp = lrt_check__material_recp(bar_code,operation_type)
		if not recept__resp:
			cond__ = f" AND (SE.stock_entry_type = 'Repack' OR SE.stock_entry_type = 'Manufacture') AND (SED.source_ref_document = 'Sub Lot Creation' OR SED.source_ref_document = 'Deflashing Receipt Entry' ) "
			lot_info = get_details_by_lot_no(bar_code,condition__ = cond__,ref_doc = "Lot Resource Tagging")
			if lot_info.get("status") == "success":
				recept__resp = lrt_check__u1_sublot(lot_info,bar_code,operation_type)
				if not recept__resp:
					if lot_info.get('data'):
						""" If there is no sublot created no need to validate directly validate in deflashing receipt entry """
						if lot_info.get('data').get("source_ref_document") == "Deflashing Receipt Entry":
							rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":bar_code,"docstatus":1},"stock_entry_reference")
							if rept_entry:
								return lrt_return_response(bar_code,lot_info,operation_type)
							else:
								return {"status":'failed',"message":f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{bar_code}</b>"}
						else:
							""" If sublot spilited for the deflshing receipt entry generated batcheds need to find deflashing source batch then need to find mould batch number for validate inspection entries """
							parent__lot = get_parent_lot(bar_code,field_name="deflashing_receipt_parent")
							if parent__lot and parent__lot.get('status') == 'success':
								return lrt_return_response(parent__lot.get('lot_no'),lot_info,operation_type)
							else:
								if parent__lot:
									return {"status":'failed',"message":parent__lot.get('message')}
					else:
						return {"status":'failed',"message":lot_info.get('message')}
				else:
					return recept__resp
			else:
				return False
		else:
			return recept__resp
	else:
		return u1__resp

def lrt_validate_dre_ins_jc(barcode,ignore_jobcard = None):
	if ignore_jobcard:
		check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":barcode,"inspection_type":"Incoming Inspection"})
		if check_exist:
			return {"status":"success"}
		else:
			return {"status":'failed',"message":f'There is no <b>Incoming Inspection Entry</b> found for the scanned lot <b>{barcode}</b>'}
	else:
		job_card = frappe.db.get_value("Job Card",{"batch_code":barcode,"operation":"Deflashing"},["name","production_item","bom_no","moulding_lot_number"],as_dict=1)
		if job_card:
			check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":barcode,"inspection_type":"Incoming Inspection"})
			if check_exist:
				return {"status":"success","job_card":job_card}
			else:
				return {"status":'failed',"message":f'There is no <b>Incoming Inspection Entry</b> found for the scanned lot <b>{barcode}</b>'}
		else:
			return {"status":'failed',"message":"Job Card not found for the lot <b>"+barcode+"</b>"}

def lrt_validate_lot_number(barcode,operation_type = None):
	try:
		sublot__resp = lrt_check_sublot(barcode,operation_type)
		if not sublot__resp:
			rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":barcode,"docstatus":1},["stock_entry_reference"],as_dict = 1)
			if rept_entry:
				check_exist = lrt_validate_dre_ins_jc(barcode)
				if check_exist.get("status") == "success":
					job_card = check_exist.get("job_card")
					if not rept_entry.stock_entry_reference:
						return {"status":'failed',"message":f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{barcode}</b>"}
					else:
						product_details = frappe.db.sql(f""" SELECT  SED.t_warehouse as from_warehouse,SED.item_code,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
														INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
														LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry.stock_entry_reference}' AND SED.deflash_receipt_reference='{barcode}' """,as_dict=1)
						if product_details:
							stock_status = lrt_check_available_stock(product_details[0].get("from_warehouse"),product_details[0].get("item_code"),product_details[0].get("batch_no",""))
							if stock_status.get('status') == "success":
								product_details[0].qty_from_item_batch = stock_status.get('qty')
								bom_uom_resp = lrt_check_uom_bom(product_details[0].item_code)
								if bom_uom_resp.get('status') == "success":
									job_card['bom_no'] = bom_uom_resp.get('bom')
									job_card['production_item'] = bom_uom_resp.get('item')
									opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
									opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":job_card.bom_no},as_dict=1)
									product_details[0].bom_operations = opeartion_exe
									job_card.update(product_details[0])
									return {"status":'success',"message":job_card}
								else:
									return {"status":bom_uom_resp.get('status'),"message":bom_uom_resp.get('message')}
							else:
								return {"status":stock_status.get('status'),"message":stock_status.get('message')}
						else:
							return {"status":'failed',"message":f"There is no <b>Stock Entry</b> found for the scanned lot <b>{barcode}</b>"}
				else:
					return check_exist
			else:
				return {"status":'failed',"message":f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{barcode}</b>"}
		else:
			return sublot__resp
	except Exception:
		frappe.log_error(message = frappe.get_traceback(),title = "shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_lot_number")
		return {"status":'failed',"message":"Something went wrong."}

def check_vs_only_exists(batch_no,inspection_type):
	lot_resp = lrt_validate_lot_number(batch_no,inspection_type)
	# frappe.log_error("--lot_resp",lot_resp)
	if lot_resp:
		if lot_resp.get('status') == "success":
			work_station__ = check_return_workstation(lot_resp.get('message').get('bom_no'),inspection_type)
			if work_station__ and work_station__.get('status') == 'success':
				resp__msg = lot_resp
				opera_con = f"  AND BP.operation NOT IN ('PDIR') "
				opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":resp__msg.get('message').get('bom_no')},as_dict=1)
				if not opeartion_exe:
					frappe.local.response['message'] = {}
					frappe.local.response['message']['status']= "Failed"
					frappe.local.response['message']['message'] = f"Operation <b>{inspection_type}</b> not found in the BOM <b>{resp__msg.get('message').get('bom_no')}</b>"
				else:
					not_cmp_ope = [k.operation for k in opeartion_exe]
					if 'Final Visual Inspection' not in not_cmp_ope:
						frappe.local.response['message'] = {}
						frappe.local.response['message']['status']= "Failed"
						frappe.local.response['message']['message'] = f"Operation <b>{inspection_type}</b> not found in the BOM <b>{resp__msg.get('message').get('bom_no')}</b>"
					else:
						if len(not_cmp_ope) > 1:
							not_cmp_ope.remove("Final Visual Inspection")
							frappe.local.response['message'] = {}
							frappe.local.response['message']['status']= "Failed"
							frappe.local.response['message']['message'] = f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k for k in not_cmp_ope)}.</b><br>Before the start of operation <b>{inspection_type}</b>."
						else:
							bom_resp__ = check_multi_bom_vls(resp__msg.get('message').get('production_item'))
							if bom_resp__ and bom_resp__.get('status') == 'Success':
								resp__msg.get('message')['available_qty'] = resp__msg.get('message').get('qty_from_item_batch')
								resp__msg.get('message')['_1kg_eq_nos'] = bom_resp__.get('_1kg_eq_nos')
								resp__msg.get('message')['available_qty_nos'] = resp__msg.get('message').get('qty_from_item_batch')
								_lno_eq_kgs = 1 / bom_resp__.get('_1kg_eq_nos')
								resp__msg.get('message')['available_qty_kgs'] = round(_lno_eq_kgs * resp__msg.get('message').get('qty_from_item_batch'),2)
								resp__msg['message']['workstation']= work_station__.get('message')
								resp__msg['message']['batch_code'] = batch_no
								resp__msg.get('message')['warehouse'] = resp__msg.get('message').get('from_warehouse')
								frappe.local.response['message'] = {}
								frappe.local.response['message']['status']= resp__msg.get('status').capitalize()
								frappe.local.response['message']['message'] = resp__msg.get('message')
							else:
								frappe.local.response['message'] = {}
								if bom_resp__:
									frappe.local.response['message']['status'] = bom_resp__.get('status')
									frappe.local.response['message']['message'] = bom_resp__.get('message')
								else:
									frappe.local.response['message']['status'] = "Failed"
									frappe.local.response['message']['message'] = f"Something went wrong not able to fetch <b>BOM</b> details..!"
			else:
				frappe.local.response['message'] = {}
				frappe.local.response['message']['status']= "Failed"
				frappe.local.response['message']['message'] = work_station__.get('message')
		else:
			frappe.local.response['message'] = {}
			frappe.local.response['message']['status']= "Failed"
			frappe.local.response['message']['message'] = lot_resp.get('message')
		return {"status":"exists"}
	else:
		return {"status":"not exists"}
	
# def check_vs_only_exists(batch_no,inspection_type):
# 	import requests
# 	domain = str(frappe.utils.get_url())
# 	headers = {"Content-Type": "application/json"}
# 	url = domain + f'/api/method/shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_lot_number?barcode={batch_no}&operation_type={inspection_type}'
# 	get_exe_doc = requests.get(url,headers=headers)
# 	if get_exe_doc and get_exe_doc.status_code == 200 and get_exe_doc.json():
# 		if get_exe_doc.json().get('status') == "success":
# 			work_station__ = check_return_workstation( get_exe_doc.json().get('message').get('bom_no'),inspection_type)
# 			if work_station__ and work_station__.get('status') == 'success':
# 				resp__msg = get_exe_doc.json()
# 				opera_con = f"  AND BP.operation NOT IN ('PDIR') "
# 				opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":resp__msg.get('message').get('bom_no')},as_dict=1)
# 				if not opeartion_exe:
# 					frappe.local.response['message'] = {}
# 					frappe.local.response['message']['status']= "Failed"
# 					frappe.local.response['message']['message'] = f"Operation <b>{inspection_type}</b> not found in the BOM <b>{resp__msg.get('message').get('bom_no')}</b>"
# 				else:
# 					not_cmp_ope = [k.operation for k in opeartion_exe]
# 					if 'Final Visual Inspection' not in not_cmp_ope:
# 						frappe.local.response['message'] = {}
# 						frappe.local.response['message']['status']= "Failed"
# 						frappe.local.response['message']['message'] = f"Operation <b>{inspection_type}</b> not found in the BOM <b>{resp__msg.get('message').get('bom_no')}</b>"
# 					else:
# 						if len(not_cmp_ope) > 1:
# 							not_cmp_ope.remove("Final Visual Inspection")
# 							frappe.local.response['message'] = {}
# 							frappe.local.response['message']['status']= "Failed"
# 							frappe.local.response['message']['message'] = f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k for k in not_cmp_ope)}.</b><br>Before the start of operation <b>{inspection_type}</b>."
# 						else:
# 							bom_resp__ = check_multi_bom_vls(resp__msg.get('message').get('production_item'))
# 							if bom_resp__ and bom_resp__.get('status') == 'Success':
# 								resp__msg.get('message')['available_qty'] = resp__msg.get('message').get('qty_from_item_batch')
# 								resp__msg.get('message')['_1kg_eq_nos'] = bom_resp__.get('_1kg_eq_nos')
# 								resp__msg.get('message')['available_qty_nos'] = resp__msg.get('message').get('qty_from_item_batch')
# 								_lno_eq_kgs = 1 / bom_resp__.get('_1kg_eq_nos')
# 								resp__msg.get('message')['available_qty_kgs'] = round(_lno_eq_kgs * resp__msg.get('message').get('qty_from_item_batch'),2)
# 								resp__msg['message']['workstation']= work_station__.get('message')
# 								resp__msg['message']['batch_code'] = batch_no
# 								resp__msg.get('message')['warehouse'] = resp__msg.get('message').get('from_warehouse')
# 								frappe.local.response['message'] = {}
# 								frappe.local.response['message']['status']= resp__msg.get('status').capitalize()
# 								frappe.local.response['message']['message'] = resp__msg.get('message')
# 							else:
# 								frappe.local.response['message'] = {}
# 								if bom_resp__:
# 									frappe.local.response['message']['status'] = bom_resp__.get('status')
# 									frappe.local.response['message']['message'] = bom_resp__.get('message')
# 								else:
# 									frappe.local.response['message']['status'] = "Failed"
# 									frappe.local.response['message']['message'] = f"Something went wrong not able to fetch <b>BOM</b> details..!"
# 			else:
# 				frappe.local.response['message'] = {}
# 				frappe.local.response['message']['status']= "Failed"
# 				frappe.local.response['message']['message'] = work_station__.get('message')
# 		else:
# 			frappe.local.response['message'] = {}
# 			frappe.local.response['message']['status']= "Failed"
# 			frappe.local.response['message']['message'] = get_exe_doc.json().get('message')
# 		return {"status":"exists"}
# 	else:
# 		return {"status":"not exists"}

# end on 28/3/24

def check_uom_bom(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
			""" End """
			# check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			# if check_uom:
			# 	return {"status":"Success"}
			# else:
			# 	return {"status":"Failed","message":"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
			return {"status":"Success","bom":bom[0].name,"item":bom[0].item}
		else:
			return {"status":"Failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.check_uom_bom")

def check_sublot(bar_code):
	cond__ = f" AND (SE.stock_entry_type = 'Repack' OR SE.stock_entry_type = 'Manufacture') AND (SED.source_ref_document = 'Sub Lot Creation' OR SED.source_ref_document = 'Deflashing Receipt Entry' ) "
	lot_info = get_details_by_lot_no(bar_code,condition__ = cond__,ref_doc = "Incoming Inspection Entry")
	# frappe.log_error(title='sulot info',message=lot_info)
	if lot_info.get("status") == "success":
		if lot_info.get('data'):
			""" If there is no sublot created no need to validate directly validate in deflashing receipt entry """
			if lot_info.get('data').get("source_ref_document") == "Deflashing Receipt Entry":
				validate_ins_receipt_return(bar_code,lot_info,bar_code)
			else:
				""" If sublot spilited for the deflshing receipt entry generated batches need to find deflashing source batch then need to find mould batch number for validate inspection entries """
				# parent__lot = get_parent_lot(bar_code,field_name="deflashing_receipt_parent")
				# if parent__lot and parent__lot.get('status') == 'success':
				# 	validate_ins_receipt_return(bar_code,lot_info,parent__lot.get('lot_no'))
				# else:
				# 	if parent__lot:
				# 		frappe.local.response['message'] = {}
				# 		frappe.local.response['message']['status']= "Failed"
				# 		frappe.local.response['message']['message'] = parent__lot.get('message')
				""" After split the inspection entry not occured so i hidded the codes but working well """
				frappe.local.response['message'] = {}
				frappe.local.response['message']['status']= 'Failed'
				frappe.local.response['message']['message'] = f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{bar_code}</b>"
		else:
			frappe.local.response['message'] = {}
			frappe.local.response['message']['status'] = "Failed"
			frappe.local.response['message']['message'] = lot_info.get('message')
		return True
	else:
		return False

def validate_ins_receipt_return(bar_code,lot_info,parent_lot):
	rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":parent_lot,"docstatus":1},["stock_entry_reference"])
	if rept_entry:
		product_details = frappe.db.sql(f""" SELECT  JC.work_order,E.employee_name as employee,JC.workstation FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
											INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
											LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{parent_lot}' """,as_dict=1)
	
		if product_details:
			product_details[0]['production_item'] = lot_info['data']['item_code']
			product_details[0]['batch_code'] = bar_code
			# product_details[0]['qty_from_item_batch'] = lot_info['data']['qty']
			product_details[0]['batch_no'] = lot_info['data']['batch_no']
			product_details[0]['spp_batch_number'] = lot_info['data']['spp_batch_number']
			frappe.local.response['message'] = {}
			frappe.local.response['message']['status']= "Success"
			frappe.local.response['message']['message'] = product_details[0]
		else:
			frappe.local.response['message'] = {}
			frappe.local.response['message']['status']= 'Failed'
			frappe.local.response['message']['message'] = f"Detail not found for the lot no <b>{bar_code}</b>"
	else:
		frappe.local.response['message'] = {}
		frappe.local.response['message']['status']= 'Failed'
		frappe.local.response['message']['message'] = f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{bar_code}</b>"

@frappe.whitelist()
def validate_inspector_barcode(b__code,inspection_type):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		designation = ""
		if spp_settings and spp_settings.designation_mapping:
			for desc in spp_settings.designation_mapping:
				if desc.spp_process == f"{inspection_type.split(' ')[0]} Inspector":
					if desc.designation:
						designation += f"'{desc.designation}',"
		if designation:
			designation = designation[:-1]
			check_emp = frappe.db.sql(f"""SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s AND designation IN ({designation}) """,{"barcode":b__code},as_dict=1)
			if check_emp:
				frappe.response.status = 'success'
				frappe.response.message = check_emp[0]
			else:
				frappe.response.status = 'failed'
				frappe.response.message = "Employee not found."
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Designation not mapped in SPP Settings."
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.validate_inspector_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."













# def visual_pedir_resp(batch_no,inspection_type,bom_no):
# 	rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":batch_no,"docstatus":1},["stock_entry_reference"])
# 	if rept_entry:
# 		if not rept_entry[0].stock_entry_reference:
# 			return {"status":"Failed","message":f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{batch_no}</b>"}
# 		else:
# 			product_details = frappe.db.sql(f""" SELECT JC.work_order,E.employee_name as employee,SED.item_code as production_item,JC.batch_code,JC.workstation,SED.qty as total_completed_qty,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
# 												INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
# 												LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{batch_no}' """,as_dict=1)
# 			if product_details:
# 				bom_uom_resp = check_uom_bom(product_details[0].production_item)
# 				if bom_uom_resp.get('status') == "Success":
# 					product_details[0]['bom_no'] = bom_uom_resp.get('bom')
# 					product_details[0]['production_item'] = bom_uom_resp.get('item')
# 					opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
# 					opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":product_details[0]['bom_no']},as_dict=1)
# 					if not opeartion_exe:
# 						return {"status":"Failed","message":f"Operations not found in the BOM <b>{product_details[0]['bom_no']}</b>"}
# 					else:
# 						opt__type = frappe.db.sql(f""" SELECT DISTINCT operation_type FROM `tabLot Resource Tagging` WHERE scan_lot_no='{batch_no}' AND 
# 													docstatus = 1 """,as_dict = 1)
# 						if not opt__type:
# 							return {"status":"Failed","message":f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k.operation for k in opeartion_exe)}</b>,<br>Before the start of operation <b>{inspection_type}</b>."}
# 						else:
# 							if len(opt__type) == len(opeartion_exe):
# 								return {"status":"Success","message":product_details[0]}
# 							else:
# 								exe_operations = [x.operation_type for x in opt__type]
# 								not_completed_oper = list(filter(lambda x : x.operation not in exe_operations,opeartion_exe))
# 								return {"status":"Failed","message":f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k.operation for k in not_completed_oper)}.</b><br>Before the start of operation <b>{inspection_type}</b>."}
# 				else:
# 					return {"status":bom_uom_resp.get('status'),"message":bom_uom_resp.get('message')}	
# 			else:
# 				return {"status":"Failed","message":f"Detail not found for the lot no <b>{batch_no}</b>"}
# 	else:
# 		return {"status":"Failed","message":f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{batch_no}</b>"}


# backup on 19/03/2024 working fine 
		
# @frappe.whitelist(allow_guest=True)
# def validate_lot_number(batch_no,docname,inspection_type):
# 	try:
# 		if inspection_type == "Line Inspection" or inspection_type == "Patrol Inspection":
# 			check_exist = frappe.db.get_all("Inspection Entry",filters={"name":("!=",docname),"docstatus":1,"lot_no":batch_no,"inspection_type":inspection_type})
# 			if check_exist:
# 				return {"status":"Failed","message":"Already Inspection Entry is created for this lot number."}
# 			else:
# 				check_lot_issue = frappe.db.sql(""" SELECT JB.mould_reference,JB.total_completed_qty,JB.workstation,JB.work_order,JB.name as job_card,JB.production_item,JB.batch_code,
# 								E.employee_name as employee FROM `tabJob Card` JB 
# 								LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JB.name
# 								LEFT JOIN `tabEmployee` E ON LG.employee = E.name
# 								WHERE JB.batch_code=%(lot_no)s
# 								""",{"lot_no":batch_no},as_dict=1)
# 				if not check_lot_issue:
# 					return {"status":"Failed","message":f"Job Card not found for the scanned lot <b>{batch_no}</b>"}
# 				else:
# 					rept_entry = frappe.db.get_all("Moulding Production Entry",{"scan_lot_number":batch_no,"docstatus":1},["stock_entry_reference"])
# 					if rept_entry:
# 						# return {"status":"Failed","message":f"<b>Moulding Production Entry</b> was completed for the lot <b>{batch_no}</b>"}
# 						check_lot_issue[0].moulding_production_entry = 1
# 					else:
# 						check_lot_issue[0].moulding_production_entry = 0
# 					check_lot_issue[0].qty_from_item_batch = 0
# 					""" Multi Bom Validation """
# 					bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":check_lot_issue[0].production_item},as_dict=1)
# 					if bom:
# 						bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
# 						if len(bom__) > 1:
# 							return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
# 						""" Add UOM for rejection in No's """
# 						# check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
# 						# if check_uom:
# 						# 	""" This is equal to 1 No's """
# 						# 	check_lot_issue[0].one_no_qty_equal_kgs = flt(1 / check_uom[0].conversion_factor , 3)
# 						# else:
# 						# 	return {"status":"Failed","message":f"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
# 						if check_lot_issue[0].mould_reference:
# 							# on 8/3/23
# 							# wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":frappe.db.get_value("Asset",check_lot_issue[0].mould_reference,"item_code")},"avg_blank_wtproduct_gms")
# 							wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":frappe.db.get_value("Asset",check_lot_issue[0].mould_reference,"item_code"),"spp_ref":check_lot_issue[0].production_item,"mould_status":"ACTIVE"},"avg_blank_wtproduct_gms")
# 							# end
# 							if wt_per_pi_gms and float(wt_per_pi_gms):
# 								""" This is equal to 1 No's """
# 								# check_lot_issue[0].one_no_qty_equal_kgs = flt(float(wt_per_pi_gms) / 1000 , 3)
# 								check_lot_issue[0].one_no_qty_equal_kgs = float(wt_per_pi_gms) / 1000 
# 							else:
# 								return {"status":"Failed","message":f"Avg Blank Wt/Product not found in <b>Mould Specification</b>"}
# 						else:
# 							return {"status":"Failed","message":f" Mould Reference not found for the scanned lot <b>{batch_no}</b> for finding UOM "}
# 						""" End """
# 					else:
# 						return {"status":"Failed","message":f"BOM is not found for <b>Item to Produce</b>"}
# 					""" End """ 
# 					user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
# 					item_batch_no = ""
# 					st_details = frappe.db.sql(""" SELECT IB.spp_batch_number FROM `tabBlank Bin Issue Item` BI 
# 								INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
# 								INNER JOIN `tabItem Bin Mapping` IB ON BI.bin = IB.blanking__bin
# 								INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
# 								INNER JOIN `tabAsset` A ON IB.blanking__bin=A.name
# 								WHERE BI.job_card=%(jb_name)s OR IB.job_card = %(jb_name)s
# 								""",{"jb_name":check_lot_issue[0].job_card},as_dict=1)
# 					check_lot_issue[0].spp_batch_no = ""
# 					if st_details:
# 						check_lot_issue[0].spp_batch_no = st_details[0].spp_batch_number
# 						# check_lot_issue[0].spp_batch_no = st_details[0].spp_batch_number.split('-')[0] if st_details[0].spp_batch_number else st_details[0].spp_batch_number
# 					chk_st_details = frappe.db.sql(""" SELECT SD.batch_no FROM `tabStock Entry Detail` SD
# 												INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent
# 												INNER JOIN `tabWork Order` W ON W.name = SE.work_order
# 												INNER JOIN `tabJob Card` JB ON JB.work_order = W.name
# 												WHERE JB.batch_code = %(lot_no)s AND SD.t_warehouse is not null
# 												""",{"lot_no":batch_no},as_dict=1)
# 					if chk_st_details:
# 						item_batch_no = chk_st_details[0].batch_no
# 					check_lot_issue[0].batch_no = item_batch_no
# 					check_lot_issue[0].user_name = user_name
# 					return {"status":"Success","message":check_lot_issue[0]}
						
# 		elif inspection_type == "Lot Inspection":
# 			check_exist = frappe.db.get_all("Inspection Entry",filters={"name":("!=",docname),"docstatus":1,"lot_no":batch_no,"inspection_type":inspection_type})
# 			if check_exist:
# 				return {"status":"Failed","message":"Already Inspection Entry is created for this lot number."}
# 			else:
# 				check_lot_issue = frappe.db.sql(""" SELECT JB.mould_reference,JB.total_qty_after_inspection,JB.total_completed_qty,JB.workstation,JB.work_order,JB.name as job_card,JB.production_item,JB.batch_code,
# 								E.employee_name as employee FROM `tabJob Card` JB 
# 								LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JB.name
# 								LEFT JOIN `tabEmployee` E ON LG.employee = E.name
# 								WHERE JB.batch_code=%(lot_no)s
# 								""",{"lot_no":batch_no},as_dict=1)
# 				if not check_lot_issue:
# 					return {"status":"Failed","message":f"Job Card not found for the scanned lot <b>{batch_no}</b>"}
# 				else:
# 					rept_entry = frappe.db.get_all("Moulding Production Entry",{"scan_lot_number":batch_no,"docstatus":1},["stock_entry_reference"])
# 					if not rept_entry:
# 						return {"status":"Failed","message":f"There is no <b>Moulding Production Entry</b> found for the lot <b>{batch_no}</b>"}
# 					else:
# 						# query = f""" SELECT SED.t_warehouse as from_warehouse,SED.batch_no FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE 
# 						# 			ON SED.parent=SE.name WHERE SED.item_code='{check_lot_issue[0].get("production_item")}' AND SE.work_order='{check_lot_issue[0].get("work_order")}' """
# 						# spp_and_batch = frappe.db.sql(query,as_dict=1)
# 						# if spp_and_batch:
# 						# 	stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),check_lot_issue[0].get("production_item"),spp_and_batch[0].get("batch_no",""))
# 						# 	if stock_status.get('status') == "Success":
# 						# 		check_lot_issue[0].qty_from_item_batch = stock_status.get('qty')
# 								""" Multi Bom Validation """
# 								bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":check_lot_issue[0].production_item},as_dict=1)
# 								if bom:
# 									bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
# 									if len(bom__) > 1:
# 										return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
# 									""" Add UOM for rejection in No's """
# 									# check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
# 									# if check_uom:
# 									# 	""" This is equal to 1 No's """
# 									# 	check_lot_issue[0].one_no_qty_equal_kgs = flt(1 / check_uom[0].conversion_factor , 3)
# 									# else:
# 									# 	return {"status":"Failed","message":f"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
# 									if check_lot_issue[0].mould_reference:
# 										item = frappe.db.get_value("Asset",check_lot_issue[0].mould_reference,"item_code")
# 										if item:
# 											# on 8/3/23
# 											# wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":item},"avg_blank_wtproduct_gms")
# 											wt_per_pi_gms = frappe.db.get_value("Mould Specification",{"mould_ref":item,"spp_ref":check_lot_issue[0].production_item,"mould_status":"ACTIVE"},"avg_blank_wtproduct_gms")
# 											# end
# 											if wt_per_pi_gms and float(wt_per_pi_gms):
# 												""" This is equal to 1 No's """
# 												# check_lot_issue[0].one_no_qty_equal_kgs = flt(float(wt_per_pi_gms) / 1000 , 3)
# 												check_lot_issue[0].one_no_qty_equal_kgs = float(wt_per_pi_gms) / 1000 
# 											else:
# 												return {"status":"Failed","message":f"Avg Blank Wt/Product not found in <b>Mould Specification</b>"}
# 										else:
# 											return {"status":"Failed","message":f"Mould item not found..!"}
# 									else:
# 										return {"status":"Failed","message":f" Mould Reference not found for the scanned lot <b>{batch_no}</b> for finding UOM "}
# 									""" End """
# 								else:
# 									return {"status":"Failed","message":f"BOM is not found for <b>Item to Produce</b>"}
# 								""" End """
# 								user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
# 								item_batch_no = ""
# 								# st_details = frappe.db.sql(""" SELECT IB.spp_batch_number FROM `tabBlank Bin Issue Item` BI 
# 								# 			INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
# 								# 			INNER JOIN `tabItem Bin Mapping` IB ON BI.bin = IB.blanking_bin
# 								# 			INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
# 								# 			INNER JOIN `tabBlanking Bin` BB ON IB.blanking_bin=BB.name
# 								# 			WHERE BI.job_card=%(jb_name)s AND IB.job_card = %(jb_name)s
# 								# 			""",{"jb_name":check_lot_issue[0].job_card},as_dict=1)
# 								st_details = frappe.db.sql(""" SELECT IB.spp_batch_number FROM `tabBlank Bin Issue Item` BI 
# 											INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
# 											INNER JOIN `tabItem Bin Mapping` IB ON BI.bin = IB.blanking__bin
# 											INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
# 											INNER JOIN `tabAsset` A ON IB.blanking__bin=A.name
# 											WHERE BI.job_card=%(jb_name)s OR IB.job_card = %(jb_name)s
# 											""",{"jb_name":check_lot_issue[0].job_card},as_dict=1)
# 								check_lot_issue[0].spp_batch_no = ""
# 								if st_details:
# 									check_lot_issue[0].spp_batch_no = st_details[0].spp_batch_number
# 									# check_lot_issue[0].spp_batch_no = st_details[0].spp_batch_number.split('-')[0] if st_details[0].spp_batch_number else st_details[0].spp_batch_number
# 									# f_spp_batch_no = st_details[0].spp_batch_number
# 									# se_ref = frappe.db.sql(""" SELECT SD.batch_no,SD.parent from `tabStock Entry Detail` SD 
# 									# 						inner join `tabStock Entry` SE ON SE.name=SD.parent
# 									# 						where SD.spp_batch_number = %(f_spp_batch_no)s AND SE.stock_entry_type='Manufacture'""",{"f_spp_batch_no":f_spp_batch_no},as_dict=1)
# 									# if se_ref:
# 									# 	spp_settings = frappe.get_single("SPP Settings")
# 									# 	s_batch = frappe.db.sql(""" SELECT SD.spp_batch_number from `tabStock Entry Detail` SD 
# 									# 							inner join `tabStock Entry` SE ON SE.name=SD.parent
# 									# 							where SD.parent = %(se_name)s AND SE.stock_entry_type='Material Transfer' AND SD.s_warehouse = %(sheeting_warehouse)s""",{"sheeting_warehouse":spp_settings.default_sheeting_warehouse,"se_name":se_ref[0].parent},as_dict=1)
# 									# 	if s_batch:
# 									# 		check_lot_issue[0].spp_batch_no = s_batch[0].spp_batch_number.split('-')[0] if s_batch[0].spp_batch_number else s_batch[0].spp_batch_number
# 								chk_st_details = frappe.db.sql(""" SELECT SD.batch_no FROM `tabStock Entry Detail` SD
# 															INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent
# 															INNER JOIN `tabWork Order` W ON W.name = SE.work_order
# 															INNER JOIN `tabJob Card` JB ON JB.work_order = W.name
# 															WHERE JB.batch_code = %(lot_no)s AND SD.t_warehouse is not null
# 															""",{"lot_no":batch_no},as_dict=1)
# 								if chk_st_details:
# 									item_batch_no = chk_st_details[0].batch_no
# 								check_lot_issue[0].batch_no = item_batch_no
# 								check_lot_issue[0].user_name = user_name
# 								return {"status":"Success","message":check_lot_issue[0]}
# 						# 	else:
# 						# 		return {"status":stock_status.get('status'),"message":stock_status.get('message')}	
# 						# else:
# 						# 	return {"status":"Failed","message":"There is no <b>Stock Entry</b> found for the scanned lot"}
		
# 		elif inspection_type == "Incoming Inspection" or inspection_type == "Final Inspection":
# 			check_exist = frappe.db.get_value("Inspection Entry",{"lot_no":batch_no,"docstatus":1,"inspection_type":inspection_type,"name":("!=",docname)})
# 			if check_exist:
# 				return {"status":"Failed","message":f" Already {inspection_type} Entry is created for this lot number <b>{batch_no}</b>."}
# 			""" Validate job card """
# 			sublot__resp = check_sublot(batch_no)
# 			if not sublot__resp:
# 				check_lot_issue = frappe.db.sql(""" SELECT JB.name FROM `tabJob Card` JB WHERE JB.batch_code=%(lot_no)s AND operation="Deflashing" """,{"lot_no":batch_no},as_dict=1)
# 				if not check_lot_issue:
# 					return {"status":"Failed","message":f"Job Card not found for the scanned lot <b>{batch_no}</b>"}
# 				else:
# 					rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":batch_no,"docstatus":1},["stock_entry_reference"])
# 					if rept_entry:
# 						if not rept_entry[0].stock_entry_reference:
# 							return {"status":"Failed","message":f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{batch_no}</b>"}
# 						else:
# 							product_details = frappe.db.sql(f""" SELECT  JC.work_order,E.employee_name as employee,SED.item_code as production_item,JC.batch_code,JC.workstation,SED.qty as total_completed_qty,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
# 																INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
# 																LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{batch_no}' """,as_dict=1)
# 							if product_details:
# 								""" Multi Bom Validation """
# 								bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":product_details[0].get("production_item")},as_dict=1)
# 								if len(bom__) > 1:
# 									return {"status":"Failed","message":f"Multiple BOM's found for the Item - <b>{product_details[0].get('production_item')}</b>"}
# 								query = f""" SELECT SED.t_warehouse as from_warehouse,SED.batch_no FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE 
# 											ON SED.parent=SE.name WHERE SED.item_code='{product_details[0].get("production_item")}' AND SE.work_order='{product_details[0].get("work_order")}' """
# 								spp_and_batch = frappe.db.sql(query,as_dict=1)
# 								if spp_and_batch:
# 									""" After incoming inspection the stock will be submit so , can't validate stock details 'HIDED' """
# 									return {"status":"Success","message":product_details[0]}
# 									# stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),product_details[0].get("production_item"),spp_and_batch[0].get("batch_no",""))
# 									# if stock_status.get('status') == "Success":
# 									# 	product_details[0].qty_from_item_batch = stock_status.get('qty')
# 									# 	return {"status":"Success","message":product_details[0]}
# 									# else:
# 									# 	return {"status":stock_status.get('status'),"message":stock_status.get('message')}	
# 								else:
# 									return {"status":"Failed","message":f"There is no <b>Stock Entry</b> found for the scanned lot <b>{batch_no}</b>"}
# 							else:
# 								return {"status":"Failed","message":f"Detail not found for the lot no <b>{batch_no}</b>"}
# 					else:
# 						return {"status":"Failed","message":f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{batch_no}</b>"}
		
# 		elif inspection_type == "Final Visual Inspection" or inspection_type == "PDIR":
# 			# check_exist = frappe.db.get_value("Inspection Entry",{"lot_no":batch_no,"docstatus":1,"inspection_type":inspection_type,"name":("!=",docname)})
# 			# if check_exist:
# 			# 	return {"status":"Failed","message":f" Already {inspection_type} Entry is created for this lot number <b>{batch_no}</b>."}
# 			# else:
# 				rept_entry = frappe.db.get_all("Lot Resource Tagging",{"scan_lot_no":batch_no,"docstatus":1},["available_qty","name","batch_no","bom_no","product_ref as production_item","warehouse","scan_lot_no as batch_code","scan_lot_no as spp_batch_number","job_card"])
# 				if rept_entry:	
# 					work_station__ = check_return_workstation(rept_entry[0].bom_no,inspection_type)
# 					if work_station__ and work_station__.get('status') == 'success':
# 						rept_entry[0].workstation = work_station__.get('message')
# 						if inspection_type == "PDIR":
# 							check_exist = frappe.db.get_value("Inspection Entry",{"lot_no":batch_no,"docstatus":1,"inspection_type":"Final Visual Inspection"})
# 							if not check_exist:
# 								return {"status":"Failed","message":f"Please complete the <b>Final Visual Inspection</b> before <b>PDIR</b> operation for the scanned lot number <b>{batch_no}</b>."}
# 						bom_resp__ = check_multi_bom_vls(rept_entry[0].production_item)
# 						if bom_resp__ and bom_resp__.get('status') == 'Success':
# 							opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
# 							opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_resp__.get('bom_no')},as_dict=1)
# 							if not opeartion_exe:
# 								return {"status":"Failed","message":f"Operations not found in the BOM <b>{bom_resp__.get('bom_no')}</b>"}
# 							else:
# 								opt__type = frappe.db.sql(f""" SELECT DISTINCT operation_type FROM `tabLot Resource Tagging` WHERE scan_lot_no='{batch_no}' AND 
# 															docstatus = 1 """,as_dict = 1)
# 								if not opt__type:
# 									return {"status":"Failed","message":f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k.operation for k in opeartion_exe)}</b>,<br>Before the start of operation <b>{inspection_type}</b>."}
# 								else:
# 									if len(opt__type) == len(opeartion_exe):
# 										stock_status = check_available_stock(rept_entry[0].get("warehouse"),bom_resp__.get("item__code"),rept_entry[0].get("batch_no",""))
# 										if stock_status.get('status') == "Success":
# 											rept_entry[0].available_qty = stock_status.get('qty')
# 											rept_entry[0]._1kg_eq_nos = bom_resp__.get('_1kg_eq_nos')
# 											rept_entry[0].available_qty_nos = stock_status.get('qty')
# 											_lno_eq_kgs = 1 / bom_resp__.get('_1kg_eq_nos')
# 											rept_entry[0].available_qty_kgs = round(_lno_eq_kgs * stock_status.get('qty'),2)
# 											return {"status":"Success","message":rept_entry[0]}
# 										else:
# 											return {"status":stock_status.get('status'),"message":stock_status.get('message')}
# 									else:
# 										exe_operations = [x.operation_type for x in opt__type]
# 										not_completed_oper = list(filter(lambda x : x.operation not in exe_operations,opeartion_exe))
# 										return {"status":"Failed","message":f"Please complete the following operations:<br>&nbsp&nbsp<b>{','.join(k.operation for k in not_completed_oper)}.</b><br>Before the start of operation <b>{inspection_type}</b>."}
# 						else:
# 							if bom_resp__:
# 								return {"status":bom_resp__.get('status'),"message":bom_resp__.get('message')}
# 							else:
# 								return {"status":"Failed","message":f"Something went wrong not able to fetch <b>BOM</b> details..!"}
# 					else:
# 						return {"status":"Failed","message":work_station__.get('message')	}
# 				else:
# 					vs_ins__resp = check_vs_only_exists(batch_no,inspection_type)
# 					if vs_ins__resp and vs_ins__resp.get('status') == "not exists":
# 						return {"status":"Failed","message":f"There is no data found for the scanned lot <b>{batch_no}</b>"}
# 					elif not vs_ins__resp:
# 						return {"status":"Failed","message":f"Not able to fetch details of the lot <b>{batch_no}</b>"}
# 	except Exception:
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.validate_lot_number")
# 		return {"status":"Failed","message":"Something went wrong."}