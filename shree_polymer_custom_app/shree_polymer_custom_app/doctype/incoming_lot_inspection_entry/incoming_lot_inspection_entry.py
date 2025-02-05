# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series

class IncomingLotInspectionEntry(Document):
	def validate(self):
		if self.lot_no:
			check_exist = frappe.db.get_all("Incoming Lot Inspection Entry",filters={"name":("!=",self.name),"docstatus":1,"lot_no":self.lot_no})
			if check_exist:
				frappe.throw(f"Incoming Lot Inspection Entry for lot <b>{self.lot_no}</b> already exists..!")
		if self.items:
			for each_item in self.items:
				if self.lot_no and self.lot_no != each_item.lot_no:
					frappe.throw(f"The Lot no. <b>{self.lot_no}</b> mismatch in row {each_item.idx}")

	def on_submit(self):
		make_stock_entry(self)

def make_stock_entry(self):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		""" For identifying procees name to change the naming series the field is used """
		naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Incoming Inspection")
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
			# "conversion_factor_uom":1,
			"transfer_qty":self.total_rejected_qty,
			"qty":self.total_rejected_qty,
			})
		stock_entry.insert()
		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		sub_entry.docstatus=1
		sub_entry.save(ignore_permissions=True)
		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.incoming_lot_inspection_entry.incoming_lot_inspection_entry.make_stock_entry")
		frappe.db.rollback()

@frappe.whitelist()
def validate_lot_number(batch_no,docname):
	try:
		check_exist = frappe.db.get_all("Incoming Lot Inspection Entry",filters={"name":("!=",docname),"docstatus":1,"lot_no":batch_no})
		if check_exist:
			return {"status":"Failed","message":f"Already Incoming Lot Inspection Entry is created for this lot number <b>{batch_no}</b>."}
		rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":batch_no,"docstatus":1},["stock_entry_reference"])
		if rept_entry:
			if not rept_entry[0].stock_entry_reference:
				return {"status":"Failed","message":f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{batch_no}</b>"}
			else:
				product_details = frappe.db.sql(f""" SELECT  E.employee_name as employee,SED.item_code as production_item,JC.batch_code,JC.workstation,SED.qty,SED.batch_no FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
													 INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
													 LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{batch_no}' """,as_dict=1)
				if product_details:
					return {"status":"Success","message":product_details[0]}
				else:
					return {"status":"Failed","message":f"Detail not found for the lot no <b>{batch_no}</b>"}
		else:
			return {"status":"Failed","message":f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{batch_no}</b>"}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.incoming_lot_inspection_entry.incoming_lot_inspection.validate_lot_number")
		return {"status":"Failed","message":f"Something went wrong"}
	
@frappe.whitelist()
def validate_inspector_barcode(b__code):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		designation = None
		if spp_settings and spp_settings.designation_mapping:
			for desc in spp_settings.designation_mapping:
				if desc.spp_process == "Incoming Lot Inspector":
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.incoming_lot_inspection_entry.incoming_lot_inspection_entry.validate_inspector_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."

	
# @frappe.whitelist()
# def validate_lot_number(batch_no,docname):
# 	try:
# 		check_exist = frappe.db.get_all("Incoming Lot Inspection Entry",filters={"name":("!=",docname),"docstatus":1,"scan_production_lot":batch_no})
# 		if check_exist:
# 			return {"status":"Failed","message":"Already Incoming Lot Inspection Entry is created for this lot number."}
# 		check_lot_issue = frappe.db.sql(""" SELECT JB.workstation,JB.work_order,JB.name as job_card,JB.production_item,JB.batch_code,
# 						E.employee_name as employee FROM `tabJob Card` JB 
# 						LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JB.name
# 						LEFT JOIN `tabEmployee` E ON LG.employee = E.name
# 						WHERE JB.batch_code=%(lot_no)s
# 						""",{"lot_no":batch_no},as_dict=1)
# 		if not check_lot_issue:
# 			return {"status":"Failed","message":"Could not found Lot Number."}
# 		user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
# 		check_lot_issue[0].user_name = user_name
# 		return {"status":"Success","message":check_lot_issue[0]}
# 	except Exception:
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.incoming_lot_inspection_entry.incoming_lot_inspection.validate_lot_number")
# 		frappe.db.rollback()