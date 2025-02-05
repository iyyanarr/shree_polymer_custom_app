# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now


class DeliveryChallanReceipt(Document):
	def on_submit(self):
		fb_mix = validate_final_batches(self)
		if fb_mix:
			wo = create_wo(self)
			if wo:
				dc_query ="SELECT dc_no ,operation FROM `tabDC Item` WHERE parent='{dc_reciept}' GROUP BY dc_no,operation ".format(dc_reciept=self.name)
				dc_nos = frappe.db.sql(dc_query,as_dict=1)
				for x in dc_nos:
					if frappe.db.get_all("Mixing Center Items",filters={"parent":x.dc_no,"parenttype":"SPP Delivery Challan","is_received":0}):
						frappe.db.set_value("SPP Delivery Challan",x.dc_no,"status","Partially Completed")
						frappe.db.commit()
					else:
						# x.reload()
						frappe.db.set_value("SPP Delivery Challan",x.dc_no,"is_recieved",1)
						frappe.db.set_value("SPP Delivery Challan",x.dc_no,"status","Completed")
						frappe.db.commit()
		else:
			frappe.throw("You can receive only one Final Batch Mixing at a time.")

		
def validate_final_batches(self):
	grouped_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabDC Item` WHERE operation = 'Final Batch Mixing' AND parent = %(rc_id)s GROUP BY item_to_manufacture """,{"rc_id":self.name},as_dict=1)
	if len(grouped_items)>1:
		return False
	for x in grouped_items:
		bom_items = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":x.item_to_manufacture},as_dict=1)
		manf_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabDC Item` WHERE operation = 'Final Batch Mixing' AND parent = %(rc_id)s AND item_to_manufacture=%(item_to_manufacture)s """,{"rc_id":self.name,"item_to_manufacture":x.item_to_manufacture},as_dict=1)
		if not len(manf_items) == len(bom_items):
			return False
	return True

@frappe.whitelist()
def validate_barcode(batch_no,warehouse=None):
	check_item_qty = frappe.db.sql(""" SELECT SD.item_code,SB.qty,DC.name as dc_no,DC.operation,
									   SD.spp_batch_number as spp_batch_no,SD.batch_no,
									   SD.mix_barcode as scan_barcode,SB.stock_uom as qty_uom,
									   SD.t_warehouse as warehouse
									   FROM `tabItem Batch Stock Balance` SB 
									   INNER JOIN `tabStock Entry Detail` SD ON SB.batch_no = SD.batch_no
									   INNER JOIN `tabMixing Center Items` MI ON MI.scan_barcode=SD.mix_barcode
									   INNER JOIN `tabSPP Delivery Challan` DC ON DC.name = MI.parent
									   WHERE SD.mix_barcode = %(bar_code)s 
									   AND DC.status <> 'Completed' ORDER BY SD.creation DESC limit 1""",{"warehouse":warehouse,"bar_code":batch_no},as_dict=1)
	if check_item_qty:
		if check_item_qty[0].qty>0:
			bom  = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND B.is_default=1""",{"item_code":check_item_qty[0].item_code},as_dict=1)
			if bom:
				check_item_qty[0].bom_item = bom[0].item
			return {"status":"Success","stock":check_item_qty}
	return {"status":"Failed","message":"No Stock Available."}



@frappe.whitelist()
def create_wo(dc_rec):
	dc_query ="SELECT dc_no,operation FROM `tabDC Item` WHERE parent='{dc_reciept}' GROUP BY dc_no,operation ".format(dc_reciept=dc_rec.name)
	dc_nos = frappe.db.sql(dc_query,as_dict=1)
	is_fb_created= 0 
	for x in dc_nos:
		if x.operation=="Batch" or x.operation=="Master Batch Mixing":
			spp_settings = frappe.get_single("SPP Settings")
			items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_no,qty,batch_no,sum(qty) as qty FROM `tabDC Item` WHERE dc_no=%(parent_doc)s and parent=%(dc_reciept)s GROUP BY item_code,scan_barcode,spp_batch_no,qty,batch_no""",{"parent_doc":x.dc_no,"dc_reciept":dc_rec.name},as_dict=1)
			dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE dc_no=%(parent_doc)s """,{"parent_doc":x.dc_no},as_dict=1)
			for w_item in items:
				bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":w_item.item_code},as_dict=1)
				if bom:
					actual_weight = w_item.qty
					work_station = None
					if x.operation=="Batch":
						work_station = "Rice Lake"
					if x.operation=="Master Batch Mixing":
						work_station = "Avon Kneader"
					import time
					wo = frappe.new_doc("Work Order")
					wo.naming_series = "MFG-WO-.YYYY.-"
					wo.company = "SPP"
					wo.fg_warehouse = "U3-Store - SPP INDIA"
					wo.use_multi_level_bom = 0
					wo.skip_transfer = 1
					wo.source_warehouse = dc_rec.source_warehouse
					wo.wip_warehouse = spp_settings.wip_warehouse
					wo.transfer_material_against = "Work Order"
					wo.bom_no = bom[0].name
					wo.append("operations",{
						"operation":x.operation,
						"bom":bom[0].name,
						"workstation":work_station,
						"time_in_mins":5,
						})
					wo.referenceid = round(time.time() * 1000)
					wo.production_item =bom[0].item
					wo.qty = w_item.qty
					wo.planned_start_date = getdate()
					wo.docstatus = 1
					try:
						wo.save(ignore_permissions=True)
						update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
						se = make_stock_entry(x,actual_weight,w_item.batch_no,w_item.spp_batch_no,w_item.scan_barcode,dc_rec,spp_settings,wo.name,w_item.item_code,"Manufacture")
					except Exception as e:
						frappe.log_error(frappe.get_traceback(),"DC Receipt Error")
						frappe.db.rollback()
						return False
		if x.operation=="Final Batch Mixing":
			grouped_items = frappe.db.sql(""" SELECT item_to_manufacture FROM `tabDC Item`  WHERE parent=%(dc_reciept)s GROUP BY item_to_manufacture """,{"dc_reciept":dc_rec.name},as_dict=1)
			for g_item in grouped_items:
				if is_fb_created == 0:
					se = create_wo_final_batch_mixing(dc_rec,g_item.item_to_manufacture,x.dc_no)
					is_fb_created = 1
			
	return True
def update_job_cards(wo,actual_weight,employee,spp_settings):
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	operations = frappe.db.get_all("Work Order Operation",filters={"parent":wo},fields=['time_in_mins'])
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		frappe.log_error(jc.as_dict(),"jc")
		for time_log in jc.time_logs:
			time_log.employee = employee
			time_log.completed_qty = flt("{:.3f}".format(actual_weight))
			if operations:
				time_log.from_time = now()
				time_log.to_time = add_to_date(now(),minutes=0,as_datetime=True)
				time_log.time_in_mins = 0
		# if spp_settings.auto_submit_job_cards:
		jc.total_completed_qty = flt("{:.3f}".format(actual_weight))
		jc.docstatus = 1
		jc.save(ignore_permissions=True)

def make_stock_entry(w_item,sp_item_qty,sp_item_batch_no,sp_item_spp_batch_no,sp_item_scan_barcode,mt_doc,spp_settings,work_order_id,compound_code, purpose, qty=None):
	try:
		# items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_no,qty,batch_no FROM `tabDC Item` WHERE parent=%(parent_doc)s and dc_no=%(dc_no)s GROUP BY item_code,scan_barcode,spp_batch_no,qty""",{"parent_doc":mt_doc.name,"dc_no":w_item.dc_no},as_dict=1)
		# frappe.log_error(work_order_id,'work_order_id')
		dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  dc_no=%(parent_doc)s and parent=%(dc_rec)s """,{"parent_doc":w_item.dc_no,'dc_rec':mt_doc.name},as_dict=1)
		# for sp_item in items:
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
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.remarks = w_item.dc_no
		for x in work_order.required_items:
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":sp_item_qty,
				"qty":sp_item_qty,
				"batch_no":sp_item_batch_no,
				"spp_batch_number":None,
				"mix_barcode":None,
				})
			frappe.log_error(x.item_code,"item_code")
			frappe.log_error(sp_item_batch_no,"sp_item_batch_no")

			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1  """,{"item_code":x.item_code},as_dict=1)
			if bom:
				is_compound = 0
				bcode_resp = generate_barcode(sp_item_scan_barcode)
				stock_entry.append("items",{
					"item_code":bom[0].item,
					"s_warehouse":None,
					"t_warehouse":work_order.fg_warehouse,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":1,
					"transfer_qty":sp_item_qty,
					"qty":sp_item_qty,
					"spp_batch_number":sp_item_spp_batch_no,
					"mix_barcode":sp_item_scan_barcode,
					"is_compound":is_compound,
					"barcode_attach":bcode_resp.get("barcode"),
					"barcode_text":bcode_resp.get("barcode_text"),
					})
		# if spp_settings.auto_submit_stock_entries:
		
		stock_entry.insert()
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save(ignore_permissions=True)
		for dc_item in dc_items:
			m_item = frappe.db.get_all("Mixing Center Items",filters={"parent":w_item.dc_no,"parenttype":"SPP Delivery Challan","scan_barcode":dc_item.scan_barcode,"item_code":dc_item.item_code})
			if m_item:
				for x in m_item:
					frappe.db.set_value("Mixing Center Items",x.name,"is_received",1)
					frappe.db.set_value("Mixing Center Items",x.name,"dc_receipt_no",mt_doc.name)
					frappe.db.set_value("Mixing Center Items",x.name,"dc_receipt_date",getdate())
					frappe.db.commit()
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(),"DC Receipt Stock Entry Error")
		frappe.db.rollback()
		return {"status":"Failed"}

def rollback_transaction():
	frappe.db.rollback()

def validate_bom_items(mt_doc,item_code,dc_no):
	# dc_items = mt_doc.batches
	dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  parent=%(parent_doc)s AND operation='Final Batch Mixing' AND item_to_manufacture=%(item_code)s """,{"dc_no":dc_no,"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
	# if mt_doc.is_internal_mixing:
	# 	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE   B.is_active=1 AND B.item=%(manufacturer_item)s""",{"manufacturer_item":item_code},as_dict=1)
	if bom:
		bom_items = frappe.db.get_all("BOM Item",filters={"parent":bom[0].name},fields=['item_code'])
		b_items = []
		d_items = []
		for x in dc_items:
			d_items.append(x.item_code)
		for x in bom_items:
			if not x.item_code in d_items:
				return False
	return True
@frappe.whitelist()
def create_wo_final_batch_mixing(mt_doc,item_code,dc_no):
	if validate_bom_items(mt_doc,item_code,dc_no):
		spp_settings = frappe.get_single("SPP Settings")
		dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE parent=%(parent_doc)s AND operation='Final Batch Mixing' AND item_to_manufacture=%(item_code)s """,{"dc_no":dc_no,"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
		if bom:
			actual_weight = sum(flt(e_item.qty) for e_item in dc_items)
			# work_station = None
			# w_stations = frappe.db.get_all("Workstation",filters={"warehouse":mt_doc.source_warehouse})
			work_station = "Two Roll Mixing Mill"
			import time
			wo = frappe.new_doc("Work Order")
			wo.naming_series = "MFG-WO-.YYYY.-"
			wo.company = "SPP"
			wo.fg_warehouse =  "U3-Store - SPP INDIA"
			wo.use_multi_level_bom = 0
			wo.skip_transfer = 1
			wo.source_warehouse = mt_doc.source_warehouse
			wo.wip_warehouse = spp_settings.wip_warehouse
			wo.transfer_material_against = "Work Order"
			wo.bom_no = bom[0].name
			wo.append("operations",{
				"operation":"Final Batch Mixing",
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
				update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
				se = make_stock_entry_final_batch(mt_doc,item_code,dc_no,spp_settings,wo.name,dc_items[0].item_code,"Manufacture")
				return se
			except Exception as e:
				frappe.log_error(frappe.get_traceback(),"DC Receipt Error")
				frappe.db.rollback()
				# frappe.throw(e)
				return {"status":"Failed"}
	else:
		frappe.throw("BOM is not matched with items")
def make_stock_entry_final_batch(mt_doc,item_code,dc_no,spp_settings,work_order_id,compound_code, purpose, qty=None):
	try:
		st_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE parent=%(parent_doc)s AND operation='Final Batch Mixing' AND item_to_manufacture=%(item_code)s""",{"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
		dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE parent=%(parent_doc)s AND operation='Final Batch Mixing' AND item_code=%(item_code)s """,{"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
		# for sp_item in items:
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
		stock_entry.use_multi_level_bom = 0
		stock_entry.set_posting_time = 0
		stock_entry.stock_entry_type = "Manufacture"
		# accept 0 qty as well
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.remarks = dc_no
		for x in st_items:
			sp_item_batch_no = None
			batch_nos = frappe.db.get_all("DC Item",filters={"parent":mt_doc.name,"item_code":x.item_code},fields=['batch_no'])
			if batch_nos:
				sp_item_batch_no = batch_nos[0].batch_no
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":x.qty,
				"qty":x.qty,
				"spp_batch_number":None,
				"batch_no":sp_item_batch_no,
				"mix_barcode":"",
				})
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
		if bom:
			d_spp_batch_no = get_spp_batch_date(bom[0].item)
			bcode_resp = generate_barcode("C_"+d_spp_batch_no)
			stock_entry.append("items",{
				"item_code":bom[0].item,
				"s_warehouse":None,
				"t_warehouse":work_order.fg_warehouse,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":1,
				"transfer_qty":work_order.qty,
				"qty":work_order.qty,
				"spp_batch_number":d_spp_batch_no,
				"mix_barcode":bom[0].item+"_"+d_spp_batch_no,
				"is_compound":1,
				"barcode_attach":bcode_resp.get("barcode"),
				"barcode_text":bcode_resp.get("barcode_text"),
				})
		# if spp_settings.auto_submit_stock_entries:
		# stock_entry.docstatus=1
		stock_entry.insert()
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save(ignore_permissions=True)
		frappe.db.commit()
		# for x in items:
		for x in st_items:
			m_item = frappe.db.get_all("Mixing Center Items",filters={"parent":dc_no,"parenttype":"SPP Delivery Challan","item_code":x.item_code,"scan_barcode":x.scan_barcode})
			if m_item:
				for x in m_item:
					frappe.db.set_value("Mixing Center Items",x.name,"is_received",1)
					frappe.db.set_value("Mixing Center Items",x.name,"dc_receipt_no",mt_doc.name)
					frappe.db.set_value("Mixing Center Items",x.name,"dc_receipt_date",getdate())
					frappe.db.commit()
		if bom:
			serial_no = 1
			serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
			if serial_nos:
				serial_no = serial_nos[0].serial_no+1
			sl_no = frappe.new_doc("SPP Batch Serial")
			sl_no.posted_date = getdate()
			sl_no.compound_code = bom[0].item
			sl_no.serial_no = serial_no
			sl_no.insert()
		frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
		frappe.db.commit()
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(),"DC Receipt Error")
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

def generate_barcode(compound):
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
