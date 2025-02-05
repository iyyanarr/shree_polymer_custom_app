# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate, nowdate, today,add_months,cint,flt

class Billing(Document):
	def validate(self):
		if not self.items:
			frappe.throw("Please add some items before save..!")
			
	def on_submit(self):
		if not self.customer:
			frappe.throw("Please select the customer before submit...!")
		else:
			resp_ = generate_invoice(self)
			if not resp_.get('status'):
				self.reload()
				if resp_.get('type__') and resp_.get('type__') == "submit":
					if self.sales_invoice_reference:
						frappe.db.sql(f" DELETE FROM `tabSales Invoice` WHERE name='{self.sales_invoice_reference}' ")
						frappe.db.sql(f" UPDATE `tab{self.doctype}` SET sales_invoice_reference='' WHERE name='{self.name}' ")
						frappe.db.commit()
					self.reload()
				frappe.throw(resp_.get("message"))
			else:
				self.reload()

def generate_invoice(self):
	try:
		sales__inv = frappe.new_doc("Sales Invoice")
		sales__inv.due_date = add_months(nowdate(),1)
		sales__inv.customer = self.customer
		sales__inv.update_stock = 1
		sales__inv.company = "SPP"
		sales__inv.asn_number = self.asn_number
		sales__inv.driver_name = self.driver_name
		sales__inv.vehicle_number = self.vehicle_number
		for each_item in self.items:
			each_item__ = each_item.as_dict()
			each_item__['rate'] = each_item__.get('valuation_rate')
			if each_item__.get('doctype'):del each_item__['doctype']
			if each_item__.get('parenttype'):del each_item__['parenttype']
			if each_item__.get('parentfield'):del each_item__['parentfield']
			if each_item__.get('parent'):del each_item__['parent']
			if each_item__.get('spp_batch_no'):del each_item__['spp_batch_no']
			if each_item__.get('batch_no'):del each_item__['batch_no']
			if each_item__.get('package_barcode_text'):del each_item__['package_barcode_text']
			if each_item__.get('docstatus'):del each_item__['docstatus']
			if each_item__.get('modified_by'):del each_item__['modified_by']
			if each_item__.get('modified'):del each_item__['modified']
			if each_item__.get('creation'):del each_item__['creation']
			if each_item__.get('owner'):del each_item__['owner']
			if each_item__.get('name'):del each_item__['name']
			if each_item__.get('__unsaved'):del each_item__['__unsaved']
			if each_item__.get('idx'):del each_item__['idx']
			sales__inv.append("items",each_item__)
		sales__inv.insert(ignore_permissions = True,ignore_mandatory = True)
		frappe.db.set_value(self.doctype,self.name,"sales_invoice_reference",sales__inv.name)
		frappe.db.commit()
		try:
			exe__sales = frappe.get_doc("Sales Invoice",sales__inv.name)
			exe__sales.docstatus = 1
			exe__sales.save(ignore_permissions = True)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.billing.billing.generate_invoice")
			return {"status":False,"message":"Invoice Generation Failed..!","type__":"submit"}
		return {"status":True}
	except Exception:	
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.billing.billing.generate_invoice")
		return {"status":False,"message":"Invoice Generation Failed..!"}
	
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.billing.billing.check_available_stock")
		return {"status":"failed","message":"Something went wrong"}

def check_uom_bom(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE B.item=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
			""" End """
			return {"status":"success"}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.billing.billing.check_uom_bom")
		frappe.db.rollback()

@frappe.whitelist()
def validate_lot_barcode(bar__code):
	try:
		exe_ste = frappe.db.sql(f""" SELECT SED.valuation_rate,SED.amount,SED.uom,SED.spp_batch_number,SED.item_name,SED.qty,SED.item_code,SED.batch_no,
									SED.t_warehouse as from_warehouse,SE.name FROM `tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED 
									ON SED.parent = SE.name WHERE SED.mix_barcode='{bar__code}' AND SE.stock_entry_type='Repack' AND 
									SED.t_warehouse IS NOT NULL AND SED.source_ref_document='Packing' """,as_dict = 1)
		if exe_ste:
			exe_pack = frappe.db.get_value("Packing",{"stock_entry_reference":exe_ste[0].name,'docstatus':1},'name')
			if exe_pack:
				stock_status = check_available_stock(exe_ste[0].get("from_warehouse"),exe_ste[0].get("item_code"),exe_ste[0].get("batch_no",""))
				if stock_status.get('status') == "success":
					if exe_ste[0].get("qty") > stock_status.get('qty'):
						frappe.response.status = 'failed'
						frappe.response.message = f'Stock is not available for the item <b>{exe_ste[0].get("item_code")}</b>'
					else:
						bom_uom_resp = check_uom_bom(exe_ste[0].get("item_code"))
						if bom_uom_resp.get('status') == "success":
							pck__details = frappe.db.sql(f""" SELECT name FROM `tabPacking` WHERE docstatus = 1 AND barcode_text = '{bar__code}' """)
							if pck__details:
								frappe.response.status = "success"
								frappe.response.message = exe_ste[0]
							else:
								frappe.response.status = 'failed'
								frappe.response.message = f'Item - {exe_ste[0].get("item_code")} not found in the <b>Packing Entry</b> list.'
						else:
							frappe.response.status = bom_uom_resp.get('status')
							frappe.response.message = bom_uom_resp.get('message')
				else:
					frappe.response.status = stock_status.get('status')
					frappe.response.message = stock_status.get('message')
			else:
				frappe.response.status = "failed"
				frappe.response.message = "There is no <b>Packing Entry</b> found for scanned barcode."
		else:
			frappe.response.status = "failed"
			frappe.response.message = "Could not find <b>Stock Entry</b> for scanned barcode."
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.billing.billing.validate_lot_barcode")
