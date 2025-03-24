# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
	cint,
	date_diff,
	flt,
	get_datetime,
	get_link_to_form,
	getdate,
	nowdate,
	time_diff_in_hours,touch_file
)
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series

class LotInspectionEntry(Document):
	def validate(self):
		if self.lot_no:
			check_exist = frappe.db.get_all("Lot Inspection Entry",filters={"name":("!=",self.name),"docstatus":1,"lot_no":self.lot_no})
			if check_exist:
				frappe.throw(f"Lot Instpection Entry for lot <b>{self.lot_no}</b> already exists..!")
		if self.items:
			for each_item in self.items:
				if self.lot_no and self.lot_no != each_item.lot_no:
					frappe.throw(f"The Lot no. <b>{self.lot_no}</b> mismatch in row {each_item.idx}")
				# query = f"""  SELECT name FROM `tabLot Inspection Entry Item` WHERE lot_no='{each_item.lot_no}' AND parent != '{self.name}' AND docstatus=1 """
				# exe_rec = frappe.db.sql(query,as_dict=1)
				# if exe_rec:
				# 	if each_item.lot_no == self.lot_no:
				# 		frappe.throw(f"Lot Instpection Entry for lot <b>{self.lot_no}</b> already exists..!")
				# 	else:
				# 		frappe.throw(f"Lot Instpection Entry for lot <b>{each_item.lot_no}</b> in row <b>{each_item.idx}</b> already exists..!")

	def on_submit(self):
		make_stock_entry(self)

@frappe.whitelist()
def validate_lot_number(batch_no,docname):
	try:
		check_exist = frappe.db.get_all("Lot Inspection Entry",filters={"name":("!=",docname),"docstatus":1,"lot_no":batch_no})
		if check_exist:
			return {"status":"Failed","message":"Already Lot Inspection Entry is created for this lot number."}

		check_lot_issue = frappe.db.sql(""" SELECT JB.total_completed_qty,JB.workstation,JB.work_order,JB.name as job_card,JB.production_item,JB.batch_code,
						E.employee_name as employee FROM `tabJob Card` JB 
						LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JB.name
						LEFT JOIN `tabEmployee` E ON LG.employee = E.name
						WHERE JB.batch_code=%(lot_no)s
						""",{"lot_no":batch_no},as_dict=1)
		if not check_lot_issue:
			return {"status":"Failed","message":"Could not found Lot Number."}
		user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
		item_batch_no = ""
		st_details = frappe.db.sql(""" SELECT IB.spp_batch_number FROM `tabBlank Bin Issue Item` BI 
					INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
					INNER JOIN `tabItem Bin Mapping` IB ON BI.bin = IB.blanking_bin
					INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
					INNER JOIN `tabBlanking Bin` BB ON IB.blanking_bin=BB.name
					WHERE BI.job_card=%(jb_name)s AND IB.job_card = %(jb_name)s
					""",{"jb_name":check_lot_issue[0].job_card},as_dict=1)
		check_lot_issue[0].spp_batch_no = ""
		if st_details:
			f_spp_batch_no = st_details[0].spp_batch_number
			se_ref = frappe.db.sql(""" SELECT SD.batch_no,SD.parent from `tabStock Entry Detail` SD 
									inner join `tabStock Entry` SE ON SE.name=SD.parent
									where SD.spp_batch_number = %(f_spp_batch_no)s AND SE.stock_entry_type='Manufacture'""",{"f_spp_batch_no":f_spp_batch_no},as_dict=1)
			if se_ref:
				spp_settings = frappe.get_single("SPP Settings")
				s_batch = frappe.db.sql(""" SELECT SD.spp_batch_number from `tabStock Entry Detail` SD 
										inner join `tabStock Entry` SE ON SE.name=SD.parent
										where SD.parent = %(se_name)s AND SE.stock_entry_type='Manufacture' AND SD.s_warehouse = %(sheeting_warehouse)s""",{"sheeting_warehouse":spp_settings.default_sheeting_warehouse,"se_name":se_ref[0].parent},as_dict=1)
				if s_batch:
					check_lot_issue[0].spp_batch_no = s_batch[0].spp_batch_number.split('-')[0] if s_batch[0].spp_batch_number else s_batch[0].spp_batch_number
			chk_st_details = frappe.db.sql(""" SELECT SD.batch_no FROM `tabStock Entry Detail` SD
										INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent
										INNER JOIN `tabWork Order` W ON W.name = SE.work_order
										INNER JOIN `tabJob Card` JB ON JB.work_order = W.name
										WHERE JB.batch_code = %(lot_no)s AND SD.t_warehouse is not null
										""",{"lot_no":batch_no},as_dict=1)
			if chk_st_details:
				item_batch_no = chk_st_details[0].batch_no
		check_lot_issue[0].batch_no = item_batch_no
		check_lot_issue[0].user_name = user_name
		return {"status":"Success","message":check_lot_issue[0]}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_inspection_entry.lot_inspection_entry.validate_lot_number")
		return {"status":"Failed","message":"Something went wrong."}

def make_stock_entry(self):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":self.product_ref_no},as_dict=1)
		if bom:
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				each_no_qty = 1/check_uom[0].conversion_factor
				t_qty = each_no_qty*self.total_rejected_qty
				if flt(t_qty, 3)>0:
					spp_settings = frappe.get_single("SPP Settings")
					stock_entry = frappe.new_doc("Stock Entry")
					stock_entry.purpose = "Material Transfer"
					stock_entry.company = "SPP"
					stock_entry.naming_series = "MAT-STE-.YYYY.-"
					""" For identifying procees name to change the naming series the field is used """
					naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Lot Inspection")
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
						"use_serial_batch_fields": 1,
						"batch_no":self.batch_no,
						"conversion_factor_uom":1,
						"transfer_qty":flt(t_qty, 3),
						"qty":flt(t_qty, 3),
						})
					
					stock_entry.insert()
					sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
					sub_entry.docstatus=1
					sub_entry.save(ignore_permissions=True)
					frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
					frappe.db.commit()
			else:
				frappe.throw("Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>")
		else:
			frappe.throw("No BOM found associated with the item <b>"+self.product_ref_no+"</b>")

	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_inspection_entry.lot_inspection_entry.make_stock_entry")
		frappe.db.rollback()

@frappe.whitelist()
def validate_inspector_barcode(b__code):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		designation = None
		if spp_settings and spp_settings.designation_mapping:
			for desc in spp_settings.designation_mapping:
				if desc.spp_process == "Lot Inspector":
					if desc.designation:
						designation = desc.designation
		if designation:
			check_emp = frappe.db.sql("""SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s AND designation=%(desc)s""",{"barcode":b__code,"desc":designation},as_dict=1)
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_inspection_entry.lot_inspection_entry.validate_inspector_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."