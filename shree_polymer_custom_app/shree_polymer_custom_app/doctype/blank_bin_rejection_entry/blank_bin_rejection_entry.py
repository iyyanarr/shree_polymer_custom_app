# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now

class BlankBinRejectionEntry(Document):
	def on_submit(self):
		make_stock_entry(self)
		self.reload()

@frappe.whitelist()
def validate_bin_barcode(bar_code):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		# bl_bin = frappe.db.sql(""" SELECT BB.bin_weight,BB.name,IBM.compound as item,IBM.is_retired,IBM.qty,IBM.spp_batch_number FROM `tabBlanking Bin` BB INNER JOIN `tabItem Bin Mapping` IBM ON BB.name=IBM.blanking_bin 
		# 						   WHERE barcode_text=%(barcode_text)s order by IBM.creation desc""",{"barcode_text":bar_code},as_dict=1)
		bl_bin = frappe.db.sql(""" SELECT A.bin_weight,A.name,A.asset_name,IBM.compound as item,IBM.is_retired,IBM.qty,IBM.spp_batch_number FROM `tabAsset` A INNER JOIN `tabItem Bin Mapping` IBM ON A.name=IBM.blanking__bin 
								   WHERE A.barcode_text=%(barcode_text)s order by IBM.creation desc""",{"barcode_text":bar_code},as_dict=1)
		if bl_bin:
			if bl_bin[0].is_retired == 1:
				frappe.response.status = 'failed'
				frappe.response.message = "No item found in Scanned Bin."
			else:
				""" Check Bom mapped and get compound """
				stock_status = check_default_bom(bl_bin[0].item,bl_bin[0])
				if stock_status.get('status') == "success":
					# s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,SD.spp_batch_number,SD.mix_barcode,\
					# 	I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I\
					# 	 INNER JOIN `tabBatch` B ON I.batch_no = B.name \
					# 	 INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name\
					# 	 INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent \
					# 	 WHERE SE.bom_no ='{bom_no}'AND SE.stock_entry_type='Manufacture' AND\
					# 	 I.warehouse ='{warehouse}' AND B.expiry_date>=curdate() ORDER BY SE.creation DESC LIMIT 1".format(bom_no=stock_status.get("bom"),warehouse=spp_settings.default_blanking_warehouse)
					s_query = "SELECT I.item_code,I.item_name,I.description,I.batch_no,SD.spp_batch_number,SD.mix_barcode,\
						I.stock_uom as uom,I.qty FROM `tabItem Batch Stock Balance` I\
						 INNER JOIN `tabBatch` B ON I.batch_no = B.name \
						 INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name\
						 INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent \
						 WHERE SE.stock_entry_type='Material Transfer' AND\
						 I.warehouse ='{warehouse}' AND B.expiry_date>=curdate() ORDER BY SE.creation DESC LIMIT 1".format(bom_no=stock_status.get("bom"),warehouse=spp_settings.unit_2_warehouse)
					st_entry = frappe.db.sql(s_query,as_dict=1)
					if st_entry:
						bl_bin[0].spp_batch_number = st_entry[0].spp_batch_number
						bl_bin[0].batch_no = st_entry[0].batch_no
						frappe.response.message = bl_bin[0]
						frappe.response.status = 'success'
					else:
						frappe.response.status = 'failed'
						frappe.response.message = "No Stock."
				else:
					frappe.response.message = stock_status.get('message')
					frappe.response.status = stock_status.get('status')
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Scanned Bin <b>"+bar_code+"</b> not exist."
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.validate_bin_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."
		
def check_default_bom(item,bl_entry):
	try:
		bom = validate_bom(item)
		if bom.get("status"):
			bl_entry.compound_code = bom.get("bom").item_code
			return {"status":"success","message":bl_entry,"bom":bom.get("bom").name}
		else:
			return {"status":"failed","message":bom.get("message")}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.check_stock_entry")

def validate_bom(item_code):
	bom = frappe.db.sql(""" SELECT B.name,BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE B.item=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item_code},as_dict=1)
	if bom:
		""" Multi Bom Validation """
		bom__ = frappe.db.sql(""" SELECT B.name FROM `tabBOM` B WHERE B.item=%(item_code)s AND B.is_active=1 """,{"item_code":item_code},as_dict=1)
		if len(bom__) > 1:
			return {"status":False,"message":f"Multiple BOM's found Item - <b>{item_code}</b>"}
		""" End """
		return {"status":True,"bom":bom[0]}
	return {"status":False,"message":f"BOM is not found."}

def make_stock_entry(self):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Repack"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.stock_entry_type = "Repack"
		stock_entry.remarks = self.reason_for_rejection
		stock_entry.from_warehouse = spp_settings.unit_2_warehouse
		stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse
		from shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry import get_spp_batch_date
		d_spp_batch_no = get_spp_batch_date(self.compound_code)
		stock_entry.append("items",{
			"item_code":self.item,
			"s_warehouse":spp_settings.unit_2_warehouse,
			"stock_uom": "Kg",
			"uom": "Kg",
			"conversion_factor_uom":1,
			"transfer_qty":self.quantity,
			"qty":self.quantity,
			"batch_no":self.batch_code
			})
		r_batchno = ""
		ct_batch = "Cutbit_"+self.compound_code
		cb_batch = frappe.db.get_all("Batch",filters={"batch_id":ct_batch})
		if cb_batch:
			r_batchno = "Cutbit_"+self.compound_code
		stock_entry.append("items",{
		"item_code":self.compound_code,
		"t_warehouse":spp_settings.default_cut_bit_warehouse,
		"stock_uom": "Kg",
		"uom": "Kg",
		"conversion_factor_uom":1,
		"is_finished_item":1,
		"transfer_qty":self.quantity,
		"batch_no":r_batchno,
		"qty":self.quantity,
		"spp_batch_number":d_spp_batch_no,
		"is_compound":1,
		"barcode_text":"CB_"+self.compound_code,
		"mix_barcode": "CB_"+self.compound_code,
		"source_ref_document":self.doctype,
		"source_ref_id":self.name
		})
		stock_entry.insert(ignore_permissions = True)
		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		sub_entry.docstatus=1
		sub_entry.save(ignore_permissions=True)
		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
		frappe.db.commit()
		serial_no = 1
		serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
		if serial_nos:
			serial_no = serial_nos[0].serial_no+1
		sl_no = frappe.new_doc("SPP Batch Serial")
		sl_no.posted_date = getdate()
		sl_no.compound_code = self.compound_code
		sl_no.serial_no = serial_no
		sl_no.insert(ignore_permissions = True)
		check_item_bin = frappe.db.get_all("Item Bin Mapping",filters={"compound":self.item,"is_retired":0},fields=['name','qty'])
		if check_item_bin:
			if self.quantity == check_item_bin[0].qty:
				frappe.db.set_value("Item Bin Mapping",check_item_bin[0].name,"is_retired",1)
				frappe.db.commit()
			if check_item_bin[0].qty > self.quantity:
				new_qty = check_item_bin[0].qty - self.quantity
				frappe.db.set_value("Item Bin Mapping",check_item_bin[0].name,"qty",new_qty)
				frappe.db.commit()
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.make_stock_entry")
		frappe.db.rollback()
		
@frappe.whitelist()
def validate_inspector_barcode(b__code):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		designation = None
		if spp_settings and spp_settings.designation_mapping:
			for desc in spp_settings.designation_mapping:
				if desc.spp_process == "Blank Bin Rejection Inspector":
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.validate_inspector_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."

