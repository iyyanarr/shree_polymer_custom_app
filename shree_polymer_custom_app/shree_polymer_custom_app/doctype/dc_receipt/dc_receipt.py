# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now


class DCReceipt(Document):
	def validate(self):
		if frappe.db.get_value("SPP Delivery Challan",self.dc_no,"is_recieved"):
			frappe.throw("Materials are already recieved for the DC <b>"+self.dc_no+"</b>")

	def on_submit(self):
		batches = frappe.db.get_all("Mixing Center Items",filters={"parent":self.dc_no},fields=['scan_barcode'],order_by='scan_barcode')
		if not len(self.batches)>0:
			frappe.throw("Please select any batches")
		# else:
		c_batches = []
		d_batches = r_batches = []
		for x in batches:
			d_batches.append(x.scan_barcode)
		r_batches = frappe.db.get_all("Mixing Center Items",filters={"parent":self.name},fields=['scan_barcode'],order_by='scan_barcode')
		for x in r_batches:
			c_batches.append(x.scan_barcode)
		wo = create_wo(self)
		# se = create_stock_entry(self)
		if self.dc_no:
			if frappe.db.get_all("Mixing Center Items",filters={"parent":self.dc_no,"parenttype":"SPP Delivery Challan","is_received":0}):
				frappe.db.set_value("SPP Delivery Challan",self.dc_no,"status","Partially Completed")
				frappe.db.commit()
			else:
				# self.reload()
				frappe.db.set_value("SPP Delivery Challan",self.dc_no,"is_recieved",1)
				frappe.db.set_value("SPP Delivery Challan",self.dc_no,"status","Completed")
				frappe.db.commit()
		self.reload()

@frappe.whitelist()
def validate_mix_barocde(batch_no,warehouse):
	check_item_qty = frappe.db.sql(""" SELECT SD.item_code,SB.qty,
									   SD.spp_batch_number as spp_batch_no,SD.batch_no,
									   SD.mix_barcode as scan_barcode,SB.stock_uom as qty_uom
									   FROM `tabItem Batch Stock Balance` SB 
									   INNER JOIN `tabStock Entry Detail` SD ON SB.batch_no = SD.batch_no
									   WHERE SD.mix_barcode = %(bar_code)s AND SD.t_warehouse=%(warehouse)s""",{"warehouse":warehouse,"bar_code":batch_no},as_dict=1)
	if check_item_qty:
		if check_item_qty[0].qty>0:
			return {"status":"Success","stock":check_item_qty}
	return {"status":"Failed","message":"No Stock Available."} 
 
@frappe.whitelist()
def validate_dc_barocde(batch_no,dc_no):
	check_dc = frappe.db.sql('''SELECT I.*,D.is_recieved FROM `tabMixing Center Items` I INNER JOIN\
							  `tabSPP Delivery Challan` D ON I.parent = D.name \
							  WHERE D.name = %(dc_no)s  AND I.scan_barcode = %(b_no)s AND (I.is_received=0 OR I.is_received IS NULL)''',{'b_no':batch_no,'dc_no':dc_no},as_dict=1)
	if check_dc:
		if check_dc[0].is_received == 1:
			return {"status":"Failed","message":"Materials are already recieved for the DC <b>"+dc_no+"</b>"}
		else:
			return {"status":"Success","stock":check_dc}
	else:
		return {"status":"Failed","message":"Scanned Batch not matched with DC"}
@frappe.whitelist()
def create_wo(mt_doc):
	if mt_doc.operation=="Batch" or mt_doc.operation=="Master Batch Mixing":
		spp_settings = frappe.get_single("SPP Settings")
		items = frappe.db.sql(""" SELECT item_code FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s GROUP BY item_code""",{"parent_doc":mt_doc.name},as_dict=1)
		dc_items = frappe.db.sql(""" SELECT * FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s """,{"parent_doc":mt_doc.name},as_dict=1)
		for w_item in items:
			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":w_item.item_code},as_dict=1)
			if bom:
				actual_weight = sum(flt(e_item.qty) for e_item in dc_items if e_item.item_code == w_item.item_code)
				work_station = None
				if mt_doc.operation=="Batch":
					work_station = "Rice Lake"
				if mt_doc.operation=="Master Batch Mixing":
					work_station = "Avon Kneader"
				import time
				wo = frappe.new_doc("Work Order")
				wo.naming_series = "MFG-WO-.YYYY.-"
				wo.company = "SPP"
				wo.fg_warehouse = mt_doc.target_warehouse
				wo.use_multi_level_bom = 0
				wo.skip_transfer = 1
				wo.source_warehouse = mt_doc.source_warehouse
				wo.wip_warehouse = spp_settings.wip_warehouse
				wo.transfer_material_against = "Work Order"
				wo.bom_no = bom[0].name
				wo.append("operations",{
					"operation":mt_doc.operation,
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
					se = make_stock_entry(mt_doc,spp_settings,wo.name,w_item.item_code,"Manufacture")
					if se.get("status")=="Success":
						return True
					else:
						return False
				except Exception as e:
					frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Error")
					frappe.db.rollback()
					return False
	if mt_doc.operation=="Final Batch Mixing":
		se = create_wo_final_batch_mixing(mt_doc)
		if se.get("status")=="Success":
			return True
		else:
			return False

def update_job_cards(wo,actual_weight,employee,spp_settings):
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	operations = frappe.db.get_all("Work Order Operation",filters={"parent":wo},fields=['time_in_mins'])
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		for time_log in jc.time_logs:
			time_log.employee = employee
			if operations:
				time_log.from_time = now()
				time_log.to_time = add_to_date(now(),minutes=operations[0].time_in_mins,as_datetime=True)
			time_log.completed_qty = flt("{:.3f}".format(actual_weight))
			time_log.time_in_mins = 20
		# if spp_settings.auto_submit_job_cards:
		jc.total_completed_qty = flt("{:.3f}".format(actual_weight))
		jc.docstatus = 1
		jc.save(ignore_permissions=True)

def make_stock_entry(mt_doc,spp_settings,work_order_id,compound_code, purpose, qty=None):
	try:
		items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_no,qty,batch_no FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s GROUP BY item_code,scan_barcode,spp_batch_no,qty""",{"parent_doc":mt_doc.name},as_dict=1)
		dc_items = frappe.db.sql(""" SELECT * FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s """,{"parent_doc":mt_doc.name},as_dict=1)
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
			stock_entry.fg_completed_qty = sp_item.qty
			if work_order.bom_no:
				stock_entry.inspection_required = frappe.db.get_value(
					"BOM", work_order.bom_no, "inspection_required"
				)
			stock_entry.from_warehouse = work_order.source_warehouse
			stock_entry.to_warehouse = work_order.fg_warehouse
			stock_entry.remarks = mt_doc.dc_no
			for x in work_order.required_items:
				stock_entry.append("items",{
					"item_code":x.item_code,
					"s_warehouse":work_order.source_warehouse,
					"t_warehouse":None,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":0,
					"transfer_qty":sp_item.qty,
					"qty":sp_item.qty,
					"batch_no":sp_item.batch_no,
					"spp_batch_number":None,
					"mix_barcode":None,
					})

				bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1  """,{"item_code":x.item_code},as_dict=1)
				if bom:
					is_compound = 0
					if mt_doc.operation=="Final Batch Mixing":
						is_compound = 1
					stock_entry.append("items",{
						"item_code":bom[0].item,
						"s_warehouse":None,
						"t_warehouse":work_order.fg_warehouse,
						"stock_uom": "Kg",
						"uom": "Kg",
						"conversion_factor_uom":1,
						"is_finished_item":1,
						"transfer_qty":sp_item.qty,
						"qty":sp_item.qty,
						"spp_batch_number":sp_item.spp_batch_no,
						"mix_barcode":sp_item.scan_barcode,
						"is_compound":is_compound,
						"source_ref_document":mt_doc.doctype,
						"source_ref_id":mt_doc.name
						})
			if spp_settings.auto_submit_stock_entries:
				stock_entry.docstatus=1
			stock_entry.insert()
			frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
			frappe.db.commit()
		for x in items:
			m_item = frappe.db.get_all("Mixing Center Items",filters={"parent":mt_doc.dc_no,"parenttype":"SPP Delivery Challan","scan_barcode":x.scan_barcode,"item_code":x.item_code})
			if m_item:
				for x in m_item:
					frappe.db.set_value("Mixing Center Items",x.name,"is_received",1)
					frappe.db.commit()
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.db.rollback()
		# frappe.throw(e)
		return {"status":"Failed"}

def rollback_transaction():
	frappe.db.rollback()
def validate_bom_items(mt_doc):
	dc_items = mt_doc.batches
	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_Active=1""",{"item_code":dc_items[0].item_code},as_dict=1)
	if mt_doc.continue_without_dc:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_Active=1 AND B.item=%(manufacturer_item)s""",{"item_code":dc_items[0].item_code,"manufacturer_item":mt_doc.compound},as_dict=1)
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
def create_wo_final_batch_mixing(mt_doc):
	if validate_bom_items(mt_doc):
		spp_settings = frappe.get_single("SPP Settings")
		dc_items = frappe.db.sql(""" SELECT * FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s """,{"parent_doc":mt_doc.name},as_dict=1)
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_Active=1""",{"item_code":dc_items[0].item_code},as_dict=1)
		if bom:
			actual_weight = sum(flt(e_item.qty) for e_item in dc_items)
			work_station = None
			work_station = "Two Roll Mixing Mill"
			import time
			wo = frappe.new_doc("Work Order")
			wo.naming_series = "MFG-WO-.YYYY.-"
			wo.company = "SPP"
			wo.fg_warehouse = mt_doc.target_warehouse
			wo.use_multi_level_bom = 0
			wo.skip_transfer = 1
			wo.source_warehouse = mt_doc.source_warehouse
			wo.wip_warehouse = spp_settings.wip_warehouse
			wo.transfer_material_against = "Work Order"
			wo.bom_no = bom[0].name
			wo.append("operations",{
				"operation":mt_doc.operation,
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
				se = make_stock_entry_final_batch(mt_doc,spp_settings,wo.name,dc_items[0].item_code,"Manufacture")
				return se
			except Exception as e:
				frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Error")
				frappe.db.rollback()
				# frappe.throw(e)
				return {"status":"Failed"}
	else:
		frappe.throw("BOM is not matched with items")
def make_stock_entry_final_batch(mt_doc,spp_settings,work_order_id,compound_code, purpose, qty=None):
	try:
		# items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_no,qty FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s GROUP BY item_code,scan_barcode,spp_batch_no,qty""",{"parent_doc":mt_doc.name},as_dict=1)
		dc_items = frappe.db.sql(""" SELECT * FROM `tabMixing Center Items` WHERE parent=%(parent_doc)s """,{"parent_doc":mt_doc.name},as_dict=1)
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
		stock_entry.remarks = mt_doc.dc_no
		for x in work_order.required_items:
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":x.required_qty,
				"qty":x.required_qty,
				"spp_batch_number":None,
				"mix_barcode":"",
				})
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_Active=1""",{"item_code":dc_items[0].item_code},as_dict=1)
		if bom:
			d_spp_batch_no = get_spp_batch_date(bom[0].item)
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
				"source_ref_document":mt_doc.doctype,
				"source_ref_id":mt_doc.name
				})
		if spp_settings.auto_submit_stock_entries:
			stock_entry.docstatus=1
		stock_entry.insert()
		# for x in items:
		m_item = frappe.db.get_all("Mixing Center Items",filters={"parent":mt_doc.dc_no,"parenttype":"SPP Delivery Challan"})
		if m_item:
			for x in m_item:
				frappe.db.set_value("Mixing Center Items",x.name,"is_received",1)
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
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Error")
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
