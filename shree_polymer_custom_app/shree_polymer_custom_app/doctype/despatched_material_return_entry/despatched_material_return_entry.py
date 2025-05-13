# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,getdate
from erpnext.stock.doctype.batch.batch import get_batch_qty

class DespatchedMaterialReturnEntry(Document):
	def validate(self):
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.items:
			frappe.throw(" Scan and add some items before save.")

	def on_submit(self):
		resp_ = make_material_transfer(self)
		if not resp_:
			rollback_entries(self, "Something went wrong not able to submit stock entry..!")
		else:
			self.reload()

def make_material_transfer(self):
	try:
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.stock_entry_type = "Material Transfer"
		for item in self.items:
			stock_entry.append("items",{
				"item_code":item.item,
				"s_warehouse":item.target_warehouse_id,
				"t_warehouse":item.source_warehouse_id,
				"stock_uom": item.uom,
				"uom": item.uom,
				"transfer_qty":item.qty,
				"qty":item.qty,
				"spp_batch_number":item.spp_batch_no,
				"batch_no":item.batch_no,
				"source_ref_document":self.doctype,
				"source_ref_id":self.name
				})
		stock_entry.insert(ignore_permissions=True)
		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
		frappe.db.commit()
		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		sub_entry.docstatus = 1
		sub_entry.save(ignore_permissions=True)
		""" Update posting date and time """
		frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{sub_entry.name}' ")
		""" End """
		return True
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatched_material_return_entry.despatched_material_return_entry.make_material_transfer")
		frappe.db.rollback()
		return False

def rollback_entries(self,msg):
	try:
		self.reload()
		if self.stock_entry_reference:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(name)s""",{"name":self.stock_entry_reference})
			frappe.db.sql(""" DELETE FROM `tabStock Entry Detail` WHERE  parent=%(name)s""",{"name":self.stock_entry_reference})
		undo_dc_status(self)
		def_rec = frappe.get_doc(self.doctype, self.name)
		def_rec.db_set("docstatus", 0)
		def_rec.db_set("stock_entry_reference", "")
		frappe.db.commit()
		self.reload()
		frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="manual_rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def update_dc_status(self):
	for x in self.items:
		frappe.db.sql(f""" UPDATE `tabDelivery Note Item` SET is_return = 1,dc_return_receipt_no = '{self.name}',
							dc_return_date = '{getdate(self.modified) if not self.posting_date else self.posting_date}' 
							WHERE docstatus = 1 AND
								scan_barcode = '{x.lot_number}' AND item_code = '{x.item}'
								AND spp_batch_no = '{x.spp_batch_no}' AND batch_no = '{x.batch_no}'
								AND target_warehouse = '{x.source_warehouse_id}' """)
		frappe.db.commit()

def undo_dc_status(self):
	for x in self.items:
		frappe.db.sql(f""" UPDATE `tabDelivery Note Item` SET is_return = 0,dc_return_receipt_no = '' 
							WHERE docstatus = 1 AND
								scan_barcode = '{x.lot_number}' AND item_code = '{x.item}'
								AND spp_batch_no = '{x.spp_batch_no}' AND batch_no = '{x.batch_no}'
								AND target_warehouse = '{x.source_warehouse_id}' """)
		frappe.db.commit()

def check_available_stock(warehouse,item,batch_no):
	try:
		qty = get_batch_qty(batch_no=batch_no, warehouse=warehouse, item_code=item)
		if qty:
			return {"status": "success", "qty": qty}
		else:
			return {"status": "failed", "message": f"Stock is not available for the item <b>{item}</b>"}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(), title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatched_material_return_entry.despatched_material_return_entry.check_available_stock")
		return {"status": "failed", "message": "Something went wrong"}

# @frappe.whitelist()
# def validate_lot_mix_barcode(bar_code):
# 	try:
# 		if not frappe.db.get_value("Despatched Material Return Entry Item",{"lot_number":bar_code,"docstatus":1}):
# 			query = f""" SELECT 
# 							DNI.batch_no,DNI.amount,DNI.rate valuation_rate,DNI.target_warehouse from_warehouse,DNI.warehouse tar_warehouse,
# 								  DNI.uom,DNI.qty,DNI.spp_batch_no,DNI.item_code,
# 								  	DNI.is_return,DNI.is_received,DN.reference_document,DN.reference_name
# 							FROM `tabDelivery Note Item` DNI INNER JOIN `tabDelivery Note` DN
# 									ON DNI.parent = DN.name
# 						 WHERE DNI.scan_barcode = '{bar_code}' AND DN.docstatus = 1 
# 							AND DNI.is_received != 1 AND DNI.is_return != 1 """
# 			spp_and_batch = frappe.db.sql(query, as_dict = 1)
# 			if spp_and_batch:
# 				stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),spp_and_batch[0].get("item_code"),spp_and_batch[0].get("batch_no",""))
# 				if stock_status.get('status') == "success":
# 					frappe.response.uom = spp_and_batch[0].get("uom")
# 					frappe.response.item = spp_and_batch[0].get("item_code")
# 					frappe.response.qty = stock_status.get('qty')
# 					frappe.response.spp_batch_number = spp_and_batch[0].get("spp_batch_no")
# 					frappe.response.batch_no = spp_and_batch[0].get("batch_no")
# 					frappe.response.from_warehouse = spp_and_batch[0].get("from_warehouse")
# 					frappe.response.to_warehouse = spp_and_batch[0].get("tar_warehouse")
# 					frappe.response.valuation_rate = spp_and_batch[0].get('valuation_rate')
# 					frappe.response.amount = spp_and_batch[0].get('amount')
# 					frappe.response.status = "success"
# 				else:
# 					frappe.response.status = stock_status.get('status')
# 					frappe.response.message = stock_status.get('message')
# 			else:
# 				frappe.response.status = "failed"
# 				frappe.response.message = "There is no valid <b>Delivery Note</b> found for the scanned lot"
# 		else:
# 			frappe.response.status = "failed"
# 			frappe.response.message = f"The <b>Despatched Material Return Entry</b> for the lot - <b>{bar_code}</b> is already exists..!"
# 	except Exception:
# 		frappe.response.status = "failed"
# 		frappe.response.message = "Something went wrong"
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatched_material_return_entry.despatched_material_return_entry.validate_lot_barcode")
@frappe.whitelist()
def validate_lot_mix_barcode(bar_code):
    try:
        # Check if barcode already exists in return entries
        if not frappe.db.get_value("Despatched Material Return Entry Item", 
                                 {"lot_number": bar_code, "docstatus": 1}):
            # Query to get stock entry details
            query = f""" SELECT 
                            SEI.batch_no, SEI.amount, SEI.basic_rate as valuation_rate,
                            SEI.s_warehouse as from_warehouse, SEI.t_warehouse as tar_warehouse,
                            SEI.stock_uom as uom, SEI.qty, SEI.spp_batch_number as spp_batch_no,
                            SEI.item_code, SE.docstatus
                        FROM `tabStock Entry Detail` SEI 
                        INNER JOIN `tabStock Entry` SE ON SEI.parent = SE.name
                        WHERE SEI.spp_batch_number = '{bar_code}' 
                            AND SE.docstatus = 1 """
            
            stock_entry_details = frappe.db.sql(query, as_dict=1)
            
            if stock_entry_details:
                # Check available stock
                stock_status = check_available_stock(
                    stock_entry_details[0].get("tar_warehouse"),
                    stock_entry_details[0].get("item_code"),
                    stock_entry_details[0].get("batch_no", "")
                )
                
                if stock_status.get('status') == "success":
                    # Set response with stock entry details
                    frappe.response.uom = stock_entry_details[0].get("uom")
                    frappe.response.item = stock_entry_details[0].get("item_code")
                    frappe.response.qty = stock_status.get('qty')
                    frappe.response.spp_batch_number = stock_entry_details[0].get("spp_batch_no")
                    frappe.response.batch_no = stock_entry_details[0].get("batch_no")
                    frappe.response.from_warehouse = stock_entry_details[0].get("from_warehouse")
                    frappe.response.to_warehouse = stock_entry_details[0].get("tar_warehouse")
                    frappe.response.valuation_rate = stock_entry_details[0].get('valuation_rate')
                    frappe.response.amount = stock_entry_details[0].get('amount')
                    frappe.response.status = "success"
                else:
                    frappe.response.status = stock_status.get('status')
                    frappe.response.message = stock_status.get('message')
            else:
                frappe.response.status = "failed"
                frappe.response.message = "There is no valid <b>Stock Entry</b> found for the scanned lot"
        else:
            frappe.response.status = "failed"
            frappe.response.message = f"The <b>Despatched Material Return Entry</b> for the lot - <b>{bar_code}</b> already exists!"
    except Exception:
        frappe.response.status = "failed"
        frappe.response.message = "Something went wrong"
        frappe.log_error(
            message=frappe.get_traceback(),
            title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatched_material_return_entry.despatched_material_return_entry.validate_stock_entry_barcode"
        )