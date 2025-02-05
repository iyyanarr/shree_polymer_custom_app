# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt,getdate,add_to_date,now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_details_by_lot_no,get_parent_lot

class DespatchToU1Entry(Document):
	def validate(self):
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if self.items:
			total_lots = 0
			total_weight_no = 0
			total_weight_kg = 0
			for each_item in self.items:
				# exe_rec = frappe.db.sql(f""" SELECT name FROM `tabDespatch To U1 Entry Item` WHERE lot_no='{each_item.lot_no}' AND parent<>'{self.name}' AND docstatus=1 """,as_dict=1)
				# if exe_rec:
				# 	frappe.throw(f"<b>Despatch Entry</b> for scanned lot <b>{each_item.lot_no}</b> in row <b>{each_item.idx}</b> is already exists..!")
				total_lots += 1
				total_weight_no += each_item.qty_nos if each_item.qty_nos else 0
				total_weight_kg += each_item.weight_kgs if each_item.weight_kgs else 0
			self.total_qty_nos = total_weight_no
			self.total_qty_kgs = total_weight_kg
			self.total_lots = total_lots
		else:
			frappe.throw("Please add some items before save.")

	def on_submit(self):
		if self.items:
			# res = make_material_transfer(self)	
			# if not res:
			# 	frappe.throw("Stock Entry creation error.")	
			create_delivery_note(self)	

def create_delivery_note(self):
	try:
		spp_dc = frappe.new_doc("Delivery Note")
		""" Ref """
		spp_dc.reference_document = self.doctype
		spp_dc.reference_name = self.name
		""" End """
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.p_target_warehouse:
			frappe.throw("Value not found for Target Warehouse in SPP Settings")
		spp_dc.posting_date = self.posting_date if self.posting_date else getdate()
		spp_dc.set_warehouse = spp_settings.unit_2_warehouse
		spp_dc.set_target_warehouse = spp_settings.p_target_warehouse
		customer = frappe.db.get_value("Warehouse",spp_settings.p_target_warehouse,"customer")
		if customer:
			# if frappe.db.get_value("Customer",customer,"is_internal_customer"):
				spp_dc.customer = customer
				spp_dc.operation = "Material Transfer"
				for x in self.items:
					spp_dc.append("items",{
						"scan_barcode":x.lot_no,
						"item_code":x.product_ref,
						"item_name":frappe.db.get_value("Item",x.product_ref,"item_name"),
						"spp_batch_no":x.spp_batch_no,
						"batch_no":x.batch_no,
						"qty":x.qty_nos,
						"uom":x.qty_uom,
						"target_warehouse":spp_settings.p_target_warehouse,
						"rate":x.valuation_rate,
						"amount":x.amount
						})
				spp_dc.insert(ignore_permissions = True)
				spp_dc = frappe.get_doc("Delivery Note",spp_dc.name)
				spp_dc.docstatus = 1
				spp_dc.save(ignore_permissions=True)
				""" Update posting date and time """
				frappe.db.sql(f" UPDATE `tabDelivery Note` SET posting_date = '{self.posting_date}' WHERE name = '{spp_dc.name}' ")
				""" End """
				frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",spp_dc.name)
				frappe.db.commit()
			# else:
			# 	frappe.throw("Customer is not internal customer")
		else:
			frappe.throw("Customer not found for the wareshouse <b>"+spp_settings.p_target_warehouse+"</b>")
		self.reload()
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatch_to_u1_entry.despatch_to_u1_entry.create_delivery_note")
		self.reload()
		frappe.msgprint("Something went wrong...!")

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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatch_to_u1_entry.despatch_to_u1_entry.check_available_stock")
		return {"status":"Failed","message":"Something went wrong"}

@frappe.whitelist()
def validate_lot_number(lot_no,docname):
	try:
		# check_exist = frappe.db.sql(f""" SELECT name FROM `tabDespatch To U1 Entry Item` WHERE lot_no='{lot_no}' AND parent<>'{docname}' AND docstatus=1 """,as_dict=1)
		# if check_exist:
		# 	frappe.response.status = 'failed'
		# 	frappe.response.message = f'<b>Despatch Entry</b> for scanned lot <b>{lot_no}</b> already exists.'
		# else:
			sublot__resp = check_sublot(lot_no)
			if not sublot__resp:
				check_lot_issue = frappe.db.sql(""" SELECT JB.name FROM `tabJob Card` JB WHERE JB.batch_code=%(lot_no)s AND operation="Deflashing" """,{"lot_no":lot_no},as_dict=1)
				if not check_lot_issue:
					frappe.response.status = 'failed'
					frappe.response.message = f"Job Card not found for the scanned lot <b>{lot_no}</b>"
				else:
					inc_lot_insp = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":lot_no,"inspection_type":"Incoming Inspection"})
					if inc_lot_insp:
						deflash_recp_entry = frappe.db.sql(f""" SELECT CASE 
																			WHEN posting_date IS NULL THEN DATE(creation) 
																			ELSE 
					 															DATE(Posting_date) as creation,
					 													stock_entry_reference,scan_deflashing_vendor, from_warehouse_id warehouse,product_weight,item FROM 
																	`tabDeflashing Receipt Entry` WHERE lot_number='{lot_no}' AND docstatus = 1 """,as_dict=1)
						if deflash_recp_entry:
							if deflash_recp_entry[0].stock_entry_reference:				
								bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":deflash_recp_entry[0].item},as_dict=1)
								if bom:
									deflash_recp_entry[0].item = bom[0].item
									query = f""" SELECT SED.t_warehouse as from_warehouse,SED.valuation_rate,SED.amount,SED.batch_no,SED.uom as qty_uom FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE 
										ON SED.parent=SE.name WHERE SE.name='{deflash_recp_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{lot_no}' """
									spp_and_batch = frappe.db.sql(query,as_dict=1)
									if spp_and_batch:
										deflash_recp_entry[0].warehouse = spp_and_batch[0].get("from_warehouse")
										stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),bom[0].item,spp_and_batch[0].get("batch_no",""))
										if stock_status.get('status') == "Success":
											deflash_recp_entry[0].qty_nos = stock_status.get('qty')
											deflash_recp_entry[0].qty_uom = spp_and_batch[0].get("qty_uom")
											deflash_recp_entry[0].batch_no = spp_and_batch[0].get("batch_no")
											deflash_recp_entry[0].valuation_rate = spp_and_batch[0].get("valuation_rate")
											deflash_recp_entry[0].amount = spp_and_batch[0].get("amount")
											check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
											if check_uom:
												deflash_recp_entry[0].product_weight = flt(deflash_recp_entry[0].qty_nos / check_uom[0].conversion_factor,3)
												# deflash_recp_entry[0].qty_nos = check_uom[0].conversion_factor * deflash_recp_entry[0].product_weight
												spp_batch_no = frappe.db.sql(f""" SELECT SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
																				WHERE SE.name='{deflash_recp_entry[0].stock_entry_reference}' AND SED.item_code='{bom[0].item}' """,as_dict=1)
												deflash_recp_entry[0].spp_batch_no = spp_batch_no[0].spp_batch_number if spp_batch_no else ''
												frappe.response.status = 'success'
												frappe.response.message = deflash_recp_entry[0]	
											else:
												frappe.response.status = 'failed'
												frappe.response.message = f'There is no <b>UOM</b> found for the item <b>{ bom[0].item}</b>.'
										else:
											frappe.response.status = stock_status.get('status')
											frappe.response.message = stock_status.get('message')
									else:
										frappe.response.status = 'failed'
										frappe.response.message = f"There is no <b>Stock Entry</b> found for the scanned lot <b>{lot_no}</b>"		
								else:
									frappe.response.status = 'failed'
									frappe.response.message = f'There is no <b>BOM</b> found for the scanned lot.'

							else:
								frappe.response.status = 'failed'
								frappe.response.message = f'There is no <b>Stock Reference</b> found for the scanned lot in <b>Deflashing Receipt Entry</b>.'	
						else:
							frappe.response.status = 'failed'
							frappe.response.message = f'There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{lot_no}</b>'
					else:
						frappe.response.status = 'failed'
						frappe.response.message = f'There is no <b>Incoming Inspection Entry</b> found for the lot <b>{lot_no}</b>'
						# frappe.response.message = f'There is no <b>Incoming Lot Inspection Entry</b> found for the lot <b>{lot_no}</b>'
	except Exception:
		frappe.response.status = 'failed'
		frappe.response.message = 'Something went wrong'
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatch_to_u1_entry.despatch_to_u1_entry.validate_lot_number")
		
def check_sublot(bar_code):
	deflash_recp_entry = frappe.db.sql(f""" SELECT DATE(creation) as creation,stock_entry_reference,scan_deflashing_vendor, from_warehouse_id warehouse,product_weight,item FROM 
															`tabDeflashing Receipt Entry` WHERE lot_number='{bar_code}' AND docstatus = 1 """,as_dict=1)
	if deflash_recp_entry:
		if deflash_recp_entry[0].stock_entry_reference:
			inc_lot_insp = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":bar_code,"inspection_type":"Incoming Inspection"})
			if inc_lot_insp:				
				bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":deflash_recp_entry[0].item},as_dict=1)
				if bom:
					deflash_recp_entry[0].item = bom[0].item
					query = f""" SELECT SED.t_warehouse as from_warehouse,SED.valuation_rate,SED.amount,SED.batch_no,SED.uom as qty_uom FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE 
						ON SED.parent=SE.name WHERE SE.name='{deflash_recp_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{bar_code}' AND SE.docstatus=1 """
					spp_and_batch = frappe.db.sql(query,as_dict=1)
					if spp_and_batch:
						deflash_recp_entry[0].warehouse = spp_and_batch[0].get("from_warehouse")
						deflash_recp_entry[0].qty_uom = spp_and_batch[0].get("qty_uom")
						deflash_recp_entry[0].batch_no = spp_and_batch[0].get("batch_no")
						deflash_recp_entry[0].valuation_rate = spp_and_batch[0].get("valuation_rate")
						deflash_recp_entry[0].amount = spp_and_batch[0].get("amount")
						stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),bom[0].item,spp_and_batch[0].get("batch_no",""))
						if stock_status.get('status') == "Success":
							deflash_recp_entry[0].qty_nos = stock_status.get('qty')
							check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
							if check_uom:
								deflash_recp_entry[0].product_weight = flt(deflash_recp_entry[0].qty_nos / check_uom[0].conversion_factor,3)
								spp_batch_no = frappe.db.sql(f""" SELECT SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
																WHERE SE.name='{deflash_recp_entry[0].stock_entry_reference}'	AND SED.item_code='{bom[0].item}' """,as_dict=1)
								deflash_recp_entry[0].spp_batch_no = spp_batch_no[0].spp_batch_number if spp_batch_no else ''
								frappe.response.status = 'success'
								frappe.response.message = deflash_recp_entry[0]	
							else:
								frappe.response.status = 'failed'
								frappe.response.message = f'There is no <b>UOM</b> found for the item <b>{ bom[0].item}</b>.'
						else:
							frappe.response.status = stock_status.get('status')
							frappe.response.message = stock_status.get('message')
					else:
						frappe.response.status = 'failed'
						frappe.response.message = f"There is no <b>Stock Entry</b> found for the scanned lot <b>{bar_code}</b>"		
				else:
					frappe.response.status = 'failed'
					frappe.response.message = f'There is no <b>BOM</b> found for the scanned lot.'
			else:
				frappe.response.status = 'failed'
				frappe.response.message = f'There is no <b>Incoming Inspection Entry</b> found for the lot <b>{bar_code}</b>'
		else:
			frappe.response.status = 'failed'
			frappe.response.message = f'There is no <b>Stock Reference</b> found for the scanned lot in <b>Deflashing Receipt Entry</b>.'	
		return True
	else:
		if check_sublot__info(bar_code):
			return True
		return False
	
def check_sublot__info(bar_code):
	lot_info = get_details_by_lot_no(bar_code,transfer_other_warehouse = True)
	# frappe.log_error(title="lot_info",message=lot_info)
	if lot_info.get("status") == "success":
		if lot_info.get('data'):
			""" This is not covered in work flow , for material receipt entries """
			if lot_info.get('data').get('stock_entry_type') == "Material Receipt":
				return_response(lot_info)
				""" End """
			else:
				""" First validate material receipt entry exists """
				parent__lot = get_parent_lot(bar_code,field_name = "material_receipt_parent")
				if parent__lot and parent__lot.get('status') == 'success':
					return_response(lot_info)
					""" End """
				else:
					parent__lot = get_parent_lot(bar_code,field_name = "deflashing_receipt_parent")
					if parent__lot and parent__lot.get('status') == 'success':
						return_response(lot_info)
					else:
						""" if There is no matches found, the lot must be a production lot / split from production lot no we can throw no defalshing receipt  """
						frappe.response.status = "failed"
						frappe.response.message = f"There is no <b>Deflahing Receipt Entry</b> found..!"
		else:
			frappe.response.status = "failed"
			frappe.response.message = lot_info.get('message')
		return True
	else:
		return False
	
def return_response(lot_info):
	if lot_info.get('data').get('qty'):
		deflash_recp_entry = {}
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":lot_info.get('data').get('item_code')},as_dict=1)
		if bom:
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				deflash_recp_entry['product_weight'] = flt(lot_info.get('data').get('qty') / check_uom[0].conversion_factor,3)
				deflash_recp_entry['item'] = lot_info.get('data').get('item_code')
				deflash_recp_entry['warehouse'] = lot_info.get('data').get('t_warehouse')
				deflash_recp_entry['qty_uom'] = lot_info.get('data').get("stock_uom")
				deflash_recp_entry['batch_no'] = lot_info.get('data').get('batch_no')
				deflash_recp_entry['qty_nos'] = lot_info.get('data').get('qty')
				deflash_recp_entry['spp_batch_no'] = lot_info.get('data').get('spp_batch_number') 
				deflash_recp_entry['creation'] = lot_info.get('data').get('creation') 
				deflash_recp_entry['valuation_rate'] = lot_info.get('data').get("valuation_rate")
				deflash_recp_entry['amount'] = lot_info.get('data').get("amount")	
				frappe.response.status = 'success'
				frappe.response.message = deflash_recp_entry
			else:
				frappe.response.status = 'failed'
				frappe.response.message = "Please define UOM for Kgs for the item <b>"+lot_info['data']['item_code']+"</b>"
		else:
			frappe.response.status = 'failed'
			frappe.response.message = f'There is no <b>BOM</b> found for the scanned lot.'
	else:
		frappe.response.status = "failed"
		frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"






""" Backup """
# def make_material_transfer(self):
# 	try:
# 		spp_settings = frappe.get_single("SPP Settings")
# 		if not spp_settings.p_target_warehouse:
# 			frappe.throw("Value not found for Target Warehouse in SPP Settings")
# 		stock_entry = frappe.new_doc("Stock Entry")
# 		stock_entry.purpose = "Material Transfer"
# 		stock_entry.company = "SPP"
# 		stock_entry.naming_series = "MAT-STE-.YYYY.-"
# 		stock_entry.stock_entry_type = "Material Transfer"
# 		stock_entry.from_warehouse = spp_settings.unit_2_warehouse
# 		stock_entry.to_warehouse = spp_settings.p_target_warehouse
# 		for e_entry in self.items:
# 			stock_entry.append("items",{
# 				"item_code":e_entry.product_ref,
# 				"s_warehouse":spp_settings.unit_2_warehouse,
# 				"t_warehouse":spp_settings.p_target_warehouse,
# 				"stock_uom": "Nos",
# 				"uom": "Nos",
# 				"conversion_factor_uom":1,
# 				"is_finished_item":1,
# 				"transfer_qty":e_entry.qty_nos,
# 				"qty":e_entry.qty_nos,
# 				"spp_batch_number":e_entry.spp_batch_no,
# 				"source_ref_document":self.doctype,
# 				"source_ref_id":self.name
# 				})
# 		stock_entry.insert(ignore_permissions=True)
# 		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
# 		sub_entry.docstatus=1
# 		sub_entry.save(ignore_permissions=True)
# 		""" Store stock entry ref in child table """
# 		frappe.db.set_value("Despatch To U1 Entry Item",e_entry.name,"stock_entry_reference",stock_entry.name)
# 		""" End """
# 		frappe.db.commit()
# 		return True
# 	except Exception as e:
# 		frappe.db.rollback()
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatch_to_u1_entry.despatch_to_u1_entry.make_material_transfer")
# 		return False