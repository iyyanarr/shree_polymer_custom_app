# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt,getdate,add_to_date,now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series,generate_batch_no,get_parent_lot

class DeflashingReceiptEntry(Document):
	def validate(self):
		exe_receipt = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":self.lot_number,"docstatus":1,"name":['!=',self.name]})
		if exe_receipt:
			frappe.throw(f"The <b>Deflashing Receipt Entry</b> for the lot number <b>{self.lot_number}</b> is already exists..! - <b>{exe_receipt}</b>")
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		# self.qty_without_scrap_weight = flt(self.qty,3)
		self.parent__lot_number = None
		# if (flt((flt(self.product_weight, 3) + flt(self.scrap_weight, 3)),3)) > flt(self.qty, 3):
		# 	frappe.throw("The <b>Product Weight</b> and <b>Scrap Weight</b> can't be greater than the <b>Available Qty</b>")
		if not self.product_weight:
			frappe.throw("Please enter the <b>Product Weight<b>")
		""" For maintaing the same lot number the source lot number saved in the job card i.e intead of sub lot number the parent lot number saved """
		parent__lot = get_parent_lot(self.lot_number)
		if parent__lot and parent__lot.get('status') == 'success':
			self.parent__lot_number = parent__lot.get('lot_no')
		else:
			self.parent__lot_number = self.lot_number
		""" For avoid no enough stock balance error the scrap stock qty consume from source batch """
		# if self.scrap_weight and self.scrap_weight>0:
		# 	if flt(self.scrap_weight,3) >= flt(self.qty,3):
		# 		frappe.throw("The <b>Scrap Weight</b> can't be greater than or equal to the <b>Available Qty</b>")
		# 	else:
		# 		self.qty_without_scrap_weight = flt((self.qty - self.scrap_weight),3)

	def on_submit(self):
		wo = create_work_order(self)
		if wo and wo.get('status') == 'success':
			mse = make_stock_entry(self,wo)
			if mse and mse.get('status') == 'success':
				self.reload()
				# if self.scrap_weight and self.scrap_weight>0:
					# mmt = make_material_transfer(self)
					# if not mmt:
						# frappe.db.rollback()
						# rollback_entries(self, "Scrap Material Transfer Entry creation error.")	
			else:
				frappe.db.rollback()
				rollback_entries(self, mse.get('message',"Product Manufacture Entry creation error."))
		else:
			frappe.db.rollback()
			rollback_entries(self, wo.get('message',"Work Order creation error..!"))

	def manual_on_submit(self):
		if self.stock_entry_reference:
			try:
				spp_settings = frappe.get_single("SPP Settings")
				if not spp_settings.scrap_warehouse:
					frappe.throw("Scrap warehouse not mapped in SPP Settings..!")
				exe__stentry = frappe.get_doc("Stock Entry",self.stock_entry_reference)
				if exe__stentry.docstatus == 0 and exe__stentry.docstatus !=2 and exe__stentry.docstatus !=1: 
					exe__stentry.docstatus = 1
					exe__stentry.save(ignore_permissions=True)
					if self.posting_date:
						""" Update posting date and time """
						frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{exe__stentry.name}' ")
						""" End """
				submit_inspection_entry(self,exe__stentry,spp_settings.scrap_warehouse)
				update_dc_status(self)
			except Exception:
				manual_rollback_entries(self,"Something went wrong not able to submit stock entries..!")
				frappe.log_error(title="Deflashing Receipt Entry stock submission failed",message=frappe.get_traceback())
		else:
			frappe.throw("Stock Entry Reference not found in <b>Deflashing Receipt Entry</b>")

def rollback_entries(self,msg):
	try:
		self.reload()
		if self.stock_entry_reference:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(name)s""",{"name":self.stock_entry_reference})
		if self.scrap_stock_entry_ref:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.scrap_stock_entry_ref}' ")
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(name)s""",{"name":self.scrap_stock_entry_ref})
		if self.work_order_ref:
			frappe.db.sql(f""" DELETE FROM `tabJob Card` WHERE work_order='{self.work_order_ref}'""")
			frappe.db.sql(f""" DELETE FROM `tabWork Order` WHERE name='{self.work_order_ref}'""")
		def_rec = frappe.get_doc(self.doctype, self.name)
		def_rec.db_set("docstatus", 0)
		def_rec.db_set("stock_entry_reference", "")
		def_rec.db_set("scrap_stock_entry_ref", "")
		def_rec.db_set("work_order_ref", "")
		frappe.db.commit()
		self.reload()
		frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="manual_rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def submit_inspection_entry(self,st_entry,deflash_scrap_warehouse):
	exe_insp = frappe.db.sql(f" SELECT stock_entry_reference,name,posting_date FROM `tabInspection Entry` WHERE inspection_type IN ('Incoming Inspection','Final Inspection') AND docstatus = 1 AND lot_no='{self.scan_lot_number}' ",as_dict = 1)	
	if exe_insp:
		for ins in exe_insp:
			if ins.stock_entry_reference:
				for st in st_entry.items:
					if st.t_warehouse and st.t_warehouse != deflash_scrap_warehouse :
						frappe.db.sql(f" UPDATE `tabInspection Entry` SET batch_no='{st.batch_no}',spp_batch_number='{st.spp_batch_number}' WHERE name = '{ins.name}' ")
						frappe.db.sql(f" UPDATE `tabStock Entry Detail` SET batch_no='{st.batch_no}' WHERE inspection_ref = '{ins.name}' ")
						frappe.db.commit()
				ins__exe = frappe.get_doc("Stock Entry",ins.stock_entry_reference)
				if ins__exe.docstatus == 0:
					ins__exe.docstatus = 1
					ins__exe.save(ignore_permissions = True)
					if ins.posting_date:
						""" Update posting date and time """
						frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{ins.posting_date}' WHERE name = '{ins__exe.name}' ")
						""" End """
		frappe.db.commit()
	
def update_dc_status(self):
	query = f""" SELECT DDEI.stock_entry_reference, DDEI.lot_number,DDEI.job_card,DDEI.batch_no,DDEI.item,DDEI.spp_batch_no,DDEI.qty,DDEI.warehouse_id
									FROM `tabDeflashing Despatch Entry Item` DDEI INNER JOIN `tabDeflashing Despatch Entry` DDE ON DDE.name=DDEI.parent
									WHERE DDE.docstatus=1 AND DDEI.lot_number='{self.scan_lot_number}'
									AND DDEI.batch_no='{self.batch_no}' AND DDEI.spp_batch_no='{self.spp_batch_no}'
									  AND DDEI.item='{self.item}' AND DDEI.warehouse_id='{self.from_warehouse_id}'  """
	deflashing_desp = frappe.db.sql(query,as_dict=1)
	for x in deflashing_desp:
		frappe.db.sql(f""" UPDATE `tabDelivery Note Item` SET is_received = 1,dc_receipt_no = '{self.name}',
							dc_receipt_date = '{getdate(self.modified) if not self.posting_date else self.posting_date}' 
							WHERE
								scan_barcode = '{x.lot_number}' AND item_code = '{x.item}'
								AND spp_batch_no = '{x.spp_batch_no}' AND batch_no = '{x.batch_no}'
								AND target_warehouse = '{x.warehouse_id}' """)
		frappe.db.commit()
		all_dc_items = frappe.db.sql(f""" SELECT DNI.name,DNI.is_received FROM `tabDelivery Note Item` DNI 
							   				INNER JOIN `tabDelivery Note` DN ON DN.name = DNI.parent 
							   					WHERE DN.name = '{x.stock_entry_reference}' AND DNI.is_received = 0 """)
		if all_dc_items:
			frappe.db.set_value("Delivery Note",x.stock_entry_reference,"received_status","Partially Completed")
		else:
			frappe.db.set_value("Delivery Note",x.stock_entry_reference,"received_status","Completed")
		frappe.db.commit()	

def undo_dc_status(self):
	query = f""" SELECT DDEI.stock_entry_reference, DDEI.lot_number,DDEI.job_card,DDEI.batch_no,DDEI.item,DDEI.spp_batch_no,DDEI.qty,DDEI.warehouse_id
									FROM `tabDeflashing Despatch Entry Item` DDEI INNER JOIN `tabDeflashing Despatch Entry` DDE ON DDE.name=DDEI.parent
									WHERE DDE.docstatus=1 AND DDEI.lot_number='{self.scan_lot_number}'
									AND DDEI.batch_no='{self.batch_no}' AND DDEI.spp_batch_no='{self.spp_batch_no}'
									  AND DDEI.item='{self.item}' AND DDEI.warehouse_id='{self.from_warehouse_id}'  """
	deflashing_desp = frappe.db.sql(query,as_dict=1)
	for x in deflashing_desp:
		frappe.db.sql(f""" UPDATE `tabDelivery Note Item` SET is_received = 0,dc_receipt_no = ''
							WHERE
								scan_barcode = '{x.lot_number}' AND item_code = '{x.item}'
								AND spp_batch_no = '{x.spp_batch_no}' AND batch_no = '{x.batch_no}'
								AND target_warehouse = '{x.warehouse_id}' """)
		
		frappe.db.set_value("Delivery Note",x.stock_entry_reference,"received_status","Pending")
		frappe.db.commit()	

def manual_rollback_entries(self,msg):
	try:
		if self.stock_entry_reference:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
			frappe.db.sql(""" UPDATE `tabStock Entry` SET docstatus = 0 WHERE name=%(st_entry)s""",{"st_entry":self.stock_entry_reference})
			work_order__ = frappe.db.get_value("Stock Entry",self.stock_entry_reference,"work_order")
			if work_order__:
				frappe.db.set_value("Work Order",work_order__,"produced_qty",0)
		exe_insp = frappe.db.sql(f" SELECT name,stock_entry_reference FROM `tabInspection Entry` WHERE inspection_type IN ('Incoming Inspection','Final Inspection') AND docstatus = 1 AND lot_no='{self.scan_lot_number}' ORDER BY creation DESC LIMIT 1",as_dict = 1)	
		if exe_insp:
			for ins in exe_insp:
				inc__exe = frappe.get_doc("Inspection Entry",ins.name)
				inc__exe.db_set("docstatus", 0)
				if ins.stock_entry_reference:
					ins__exe = frappe.get_doc("Stock Entry",ins.stock_entry_reference)
					if ins__exe.docstatus == 1:
						ins__exe.db_set("docstatus", 0)
						frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{ins.stock_entry_reference}' ")
		undo_dc_status(self)
		frappe.db.commit()
		frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="manual_rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def make_stock_entry(self,work_order):
	try:
		work_order = work_order.get('message')
		batch__rep,batch__no = generate_batch_no(batch_id = "P"+self.scan_lot_number,item = work_order.production_item,qty = flt(self.product_weight, 3))
		if batch__rep:		
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.scrap_warehouse:
				frappe.throw("Value not found for Scrap Warehouse in SPP Settings")
			if not spp_settings.scrap_item:
				frappe.throw("Value not found for Scrap Item in SPP Settings")
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Manufacture"
			stock_entry.work_order = work_order.name
			stock_entry.company = work_order.company
			stock_entry.from_bom = 1
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			""" For identifying procees name to change the naming series the field is used """
			naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Deflashing Receipt (For Internal Vendor)" if self.warehouse == "U3-Store - SPP INDIA" else "Deflashing Receipt (For External Vendor)")
			if naming_status:
				stock_entry.naming_series = naming_series
			""" End """
			stock_entry.bom_no = work_order.bom_no
			stock_entry.set_posting_time = 0
			stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
			stock_entry.stock_entry_type = "Manufacture"
			stock_entry.fg_completed_qty = work_order.qty
			if work_order.bom_no:
				stock_entry.inspection_required = frappe.db.get_value("BOM", work_order.bom_no, "inspection_required")
			stock_entry.from_warehouse = work_order.source_warehouse
			stock_entry.to_warehouse = work_order.fg_warehouse
			# d_spp_batch_no = get_spp_batch_date(work_order.production_item)
			# bcode_resp = generate_barcode("P_"+d_spp_batch_no)
			bcode_resp = generate_barcode(self.scan_lot_number)
			for x in work_order.required_items:
				stock_entry.append("items",{
					"item_code":x.item_code,
					"s_warehouse":work_order.source_warehouse,
					"t_warehouse":None,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":0,
					"use_serial_batch_fields": 1,
					# "transfer_qty":flt(self.qty_without_scrap_weight, 3),
					# "qty":flt(self.qty_without_scrap_weight, 3),
					"transfer_qty":flt(self.qty, 3),
					"qty":flt(self.qty, 3),
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
				# "spp_batch_number": d_spp_batch_no,
				"spp_batch_number": self.scan_lot_number,
				"use_serial_batch_fields": 1,
				"batch_no":batch__no,
				"mix_barcode":bcode_resp.get("barcode_text"),
				"barcode_attach":bcode_resp.get("barcode"),
				"barcode_text":bcode_resp.get("barcode_text"),
				"deflash_receipt_reference":self.lot_number,
				"source_ref_document":self.doctype,
				"source_ref_id":self.name
				})
			if self.scrap_weight:
				# for x in work_order.required_items:
					stock_entry.append("items",{
						# "item_code":x.item_code,
						"item_code":spp_settings.scrap_item,
						"s_warehouse":None,
						"t_warehouse":spp_settings.scrap_warehouse,
						"is_scrap_item":1,
						"stock_uom": "Kg",
						"use_serial_batch_fields": 1,
						"uom": "Kg",
						"is_finished_item":0,
						"transfer_qty":flt(self.scrap_weight, 3),
						"qty":flt(self.scrap_weight, 3),
						# "batch_no":self.batch_no,
						"mix_barcode":None})
			stock_entry.insert(ignore_permissions=True)
			# sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			# sub_entry.docstatus=1
			# sub_entry.save(ignore_permissions=True)
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{stock_entry.name}' ")
			""" End """
			frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
			frappe.db.commit()
			ref_res,batch__no = generate_batch_no(batch_id = batch__no,reference_doctype = "Stock Entry",reference_name = stock_entry.name)
			if ref_res:
				# serial_no = 1
				# serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
				# if serial_nos:
				# 	serial_no = serial_nos[0].serial_no+1
				# sl_no = frappe.new_doc("SPP Batch Serial")
				# sl_no.posted_date = getdate()
				# sl_no.compound_code = work_order.production_item
				# sl_no.serial_no = serial_no
				# sl_no.insert()
				return {"status":"success"}
			else:
				return {"status":"failed","message":batch__no}	
		else:
			return {"status":"failed","message":batch__no}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.make_stock_entry")
		frappe.db.rollback()
		return {"status":"failed","message":"Manufaturing Stock Entry creation error..!"}

def make_material_transfer(self):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.scrap_warehouse:
			frappe.throw("Value not found for Scrap Warehouse in SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.from_warehouse = self.from_warehouse_id
		stock_entry.to_warehouse = spp_settings.scrap_warehouse
		stock_entry.append("items",{
			"item_code":self.item,
			"s_warehouse":self.from_warehouse_id,
			"t_warehouse":spp_settings.scrap_warehouse,
			"stock_uom": "Kg",
			"uom": "Kg",
			"use_serial_batch_fields": 1,
			# "conversion_factor_uom":1,
			"transfer_qty":flt(self.scrap_weight, 3),
			"qty":flt(self.scrap_weight, 3),
			"spp_batch_number":self.spp_batch_no,
			"batch_no":self.batch_no,
			"source_ref_document":self.doctype,
			"source_ref_id":self.name
			})
		stock_entry.insert(ignore_permissions=True)
		frappe.db.set_value(self.doctype,self.name,"scrap_stock_entry_ref",stock_entry.name)
		frappe.db.commit()
		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		sub_entry.docstatus=1
		sub_entry.save(ignore_permissions=True)
		""" Update posting date and time """
		frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{sub_entry.name}' ")
		""" End """
		return True
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.make_material_transfer")
		frappe.db.rollback()
		return False

def create_work_order(doc_info):
	wo = None
	try:
		import time
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.deflash_default_time:
			frappe.throw("Value not found for default time in SPP Settings")
		if not spp_settings.deflash_workstation:
			frappe.throw("Value not found for default workstation in SPP Settings")
		if not spp_settings.unit_2_warehouse:
			frappe.throw("Value not found for unit 2 Warehouse in SPP Settings")
		if not spp_settings.wip_warehouse:
			frappe.throw("Value not found for Work in Progress Warehouse in SPP Settings")
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":doc_info.item},as_dict=1)
		if bom:
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				# each_no_qty = 1/check_uom[0].conversion_factor
				t_qty = check_uom[0].conversion_factor * doc_info.product_weight
				""" For rounding No's """
				# actual_weight = t_qty
				actual_weight = round(t_qty)
				""" End """
				# actual_weight = doc_info.product_weight
				wo = frappe.new_doc("Work Order")
				wo.naming_series = "MFG-WO-.YYYY.-"
				wo.company = "SPP"
				wo.fg_warehouse = spp_settings.unit_2_warehouse
				wo.use_multi_level_bom = 0
				wo.skip_transfer = 1
				wo.source_warehouse = doc_info.from_warehouse_id
				wo.wip_warehouse = spp_settings.wip_warehouse
				wo.transfer_material_against = "Work Order"
				wo.bom_no = bom[0].name
				wo.append("operations",{
					"operation":"Deflashing",
					"bom":bom[0].name,
					"workstation":spp_settings.deflash_workstation,
					"time_in_mins":spp_settings.deflash_default_time,
					})
				wo.referenceid = round(time.time() * 1000)
				wo.production_item = bom[0].item
				wo.qty = flt(actual_weight, 3)
				wo.insert(ignore_permissions=True)
				""" Update work order reference """
				frappe.db.set_value(doc_info.doctype,doc_info.name,"work_order_ref",wo.name)
				frappe.db.commit()
				""" end """
				wo_ = frappe.get_doc("Work Order",wo.name)
				wo_.docstatus = 1
				wo_.save(ignore_permissions=True)
				update_job_cards(wo.name,actual_weight,doc_info,doc_info.item)
				return {"status":"success","message":wo}
			else:
				return {"status":"failed","message":"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+doc_info.item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.create_work_order")
		frappe.db.rollback()
		return {"status":"failed","message":"Work order creation error..!"}

def update_job_cards(wo,actual_weight,doc_info,item):
	spp_settings = frappe.get_single("SPP Settings")
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	operations = frappe.db.get_all("Work Order Operation",filters={"parent":wo},fields=['time_in_mins'])
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		jc.append("time_logs",{
			
			"from_time":now(),
			"completed_qty":flt("{:.3f}".format(actual_weight))
			})
		for time_log in jc.time_logs:
			# time_log.employee = employee
			time_log.completed_qty = flt("{:.3f}".format(actual_weight))
			if operations:
				time_log.time_in_mins = spp_settings.default_time
		# if spp_settings.auto_submit_job_cards:
		jc.total_completed_qty = flt("{:.3f}".format(actual_weight))
		""" For mainting single lot number to all process the moulding lot number replaced """
		# jc.batch_code = doc_info.lot_number
		jc.batch_code = doc_info.parent__lot_number
		""" End """
		jc.docstatus = 1
		jc.save(ignore_permissions=True)

def get_spp_batch_date(compound=None):
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.generate_barcode")

def check_uom_bom(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
			""" End """
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				return {"status":"success"}
			else:
				return {"status":"failed","message":"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.check_uom_bom")
		frappe.db.rollback()

def check_available_stock(warehouse,item,batch_no):
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.check_available_stock")
		return {"status":"failed","message":"Something went wrong"}
	
@frappe.whitelist()
def validate_lot_barcode(bar_code,w__barcode):
	try:
		if not frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":bar_code,"docstatus":1}):
			query = f""" SELECT DDEI.stock_entry_reference, DDEI.lot_number,DDEI.job_card,DDEI.batch_no,DDEI.item,DDEI.spp_batch_no,DDEI.qty,DDEI.warehouse_id
										FROM `tabDeflashing Despatch Entry Item` DDEI INNER JOIN `tabDeflashing Despatch Entry` DDE ON DDE.name=DDEI.parent
										WHERE DDE.docstatus=1 AND DDEI.lot_number='{bar_code}' """
			deflashing_desp = frappe.db.sql(query,as_dict=1)
			if deflashing_desp:
					""" Fetch warehouse details and check stock details """
					exe_warehouse = frappe.db.get_value("Warehouse",{"barcode_text":w__barcode},["warehouse_name","name","is_group"],as_dict=1)
					if exe_warehouse:
						if exe_warehouse.get("is_group"):
							frappe.response.status = "failed"
							frappe.response.error_type = "warehouse"
							frappe.response.message = "Group node warehouse is not allowed to select for transactions"
						else:
							frappe.response.status = "success"
							frappe.response.warehouse_name = exe_warehouse.get("warehouse_name")
							frappe.response.name = exe_warehouse.get("name")
							bom_uom_resp = check_uom_bom(deflashing_desp[0].get("item"))
							if bom_uom_resp.get('status') == "success":
								stock_status = check_available_stock(exe_warehouse.get("name"),deflashing_desp[0].get("item"),deflashing_desp[0].get("batch_no",""))
								if stock_status.get('status') == "success":
									frappe.response.job_card = deflashing_desp[0].get("job_card")
									frappe.response.item = deflashing_desp[0].get("item")
									frappe.response.qty = stock_status.get('qty')
									frappe.response.spp_batch_number = deflashing_desp[0].get("spp_batch_no")
									frappe.response.batch_no = deflashing_desp[0].get("batch_no","")
									frappe.response.from_warehouse = exe_warehouse.get("name")
									frappe.response.status = "success"
								else:
									if not check_dc_stocks(deflashing_desp,exe_warehouse.get("name")):
										frappe.response.status = stock_status.get('status')
										frappe.response.message = stock_status.get('message')
							else:
								frappe.response.status = bom_uom_resp.get('status')
								frappe.response.message = bom_uom_resp.get('message')
					else:
						frappe.response.status = "failed"
						frappe.response.error_type = "warehouse"
						frappe.response.message = "There is no warehouse found for scanned vendor code"
			else:
				frappe.response.status = "failed"
				frappe.response.message = "There is no <b>Deflashing Despatch Entry</b> found for the scanned lot"
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"The <b>Deflashing Receipt Entry</b> for the lot - <b>{bar_code}</b> is already exists..!"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.validate_lot_barcode")
	
def check_dc_stocks(dd_despatch_info,warhouseid):
	# query = f""" SELECT SLE.item_code,SLE.warehouse,SLE.batch_no,B.batch_qty qty,SLE.stock_uom FROM `tabStock Ledger Entry` SLE INNER JOIN `tabBatch` B ON B.batch_id = SLE.batch_no WHERE SLE.voucher_type = 'Delivery Note' AND SLE.voucher_no = '{dd_despatch_info[0].stock_entry_reference}' AND warehouse = '{warhouseid}' """
	query = f""" SELECT 
					IBSB.item_code,IBSB.warehouse,IBSB.batch_no,IBSB.qty,IBSB.stock_uom 
				FROM `tabItem Batch Stock Balance` IBSB
					INNER JOIN `tabStock Ledger Entry` SLE ON SLE.batch_no = IBSB.batch_no
						AND SLE.warehouse = IBSB.warehouse
					INNER JOIN `tabBatch` B ON B.batch_id = SLE.batch_no 
				WHERE SLE.voucher_type = 'Delivery Note' 
					AND SLE.voucher_no = '{dd_despatch_info[0].stock_entry_reference}' 
					AND SLE.warehouse = '{warhouseid}' AND SLE.item_code = IBSB.item_code """
	sle_details = frappe.db.sql(query , as_dict = 1)
	if sle_details:
		frappe.response.job_card = dd_despatch_info[0].get("job_card")
		frappe.response.item = dd_despatch_info[0].get("item")
		frappe.response.qty = sle_details[0].get('qty')
		frappe.response.spp_batch_number = dd_despatch_info[0].get("spp_batch_no")
		frappe.response.batch_no = dd_despatch_info[0].get("batch_no","")
		frappe.response.from_warehouse = warhouseid
		frappe.response.status = "success"
		return True
	return False

@frappe.whitelist()
def validate_warehouse(bar_code):
	try:
		exe_warehouse = frappe.db.get_value("Warehouse",{"barcode_text":bar_code},["warehouse_name","name","is_group"],as_dict=1)
		if exe_warehouse:
			if exe_warehouse.get("is_group"):
				frappe.response.status = "failed"
				frappe.response.message = "Group node warehouse is not allowed to select for transactions"
			frappe.response.status = "success"
			frappe.response.warehouse_name = exe_warehouse.get("warehouse_name")
			frappe.response.name = exe_warehouse.get("name")
		else:
			frappe.response.status = "failed"
			frappe.response.message = "There is no warehouse found for scanned vendor code"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.validate_warehouse")
	
