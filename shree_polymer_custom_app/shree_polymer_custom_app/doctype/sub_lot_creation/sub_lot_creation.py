# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt
# By GOPI
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,getdate
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_details_by_lot_no,generate_batch_no,delete_batches,get_decimal_values_without_roundoff,get_workstation_by_operation

class SubLotCreation(Document):
	""" The function is used in print format 75*75 """
	def get_mould_ref(self):
		if self.first_parent_lot_no:
			exe_mould_ref = frappe.db.get_value("Job Card",{"batch_code":self.first_parent_lot_no,"operation":"Moulding"},"mould_reference")
			if exe_mould_ref:
				item_code = frappe.db.get_value("Asset",exe_mould_ref,"item_code")
				if item_code:
					return item_code
				else:
					return '-'	
			else:
				return '-'
		else:
			return f"MLD-{self.item_code[1:]}"

	def validate(self):
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.qty:
			frappe.throw('Please enter the Qty..!')
		if self.first_parent_lot_no:
			exe_production_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":self.first_parent_lot_no,"docstatus":1})
			if not exe_production_entry:
				frappe.throw("There is no <b>Moulding Production Entry</b> found for the scanned lot..!")
		else:
			if not self.material_receipt_parent and not self.despatch_u1_parent:
				frappe.throw("Parent lot number missing for validate <b>Moulding Production Entry</b>..!")

	def on_submit(self):
		try:
			if update_sublot(self):
				st_resp_ = make_repack_entry(self)
				if st_resp_ and st_resp_.get('status') == "success":
					update_lot_barcode(self)
					if self.lrt_found:
						update_lrt(self,st_resp_.get('batch__no'))
					self.reload()
				else:
					rollback_entries(self,st_resp_.get('message'))
		except Exception:
			rollback_entries(self,"Something went wrong..!")
			frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.sub_lot_creation.sub_lot_creation.on_submit")

def update_lrt(self,batch__no):
	import json
	if self.lrt_details:
		uom__resp = check_uom_bom(self.item_code)
		if uom__resp and uom__resp.get('status') == "success":
			qty = uom__resp.get('conversion_factor') * self.qty
			""" For rounding No's """
			# qty__r = get_decimal_values_without_roundoff(qty,3)
			qty__r = round(qty)
			""" End """
			lrt_data = json.loads(self.lrt_details)
			exe_tags = lrt_data.get('ids').split(",")
			remaining_operations = lrt_data.get('uncompleted_operation_list')
			for opr in remaining_operations:
				exe_doc = frappe.get_doc("Lot Resource Tagging",exe_tags[0]).as_dict()
				new_lrt = frappe.new_doc("Lot Resource Tagging")
				resp_ = check_return_workstation(opr.get('operation'))
				if resp_ and resp_.get('status') == "success":
					exe_doc['workstation'] = resp_.get('message')
					operator_info = None
					if opr.get('emp'):
						exe_doc['operator_id'] = opr.get('emp')
						operator_info = frappe.db.get_value("Employee",opr.get('emp'),['employee_name','barcode_text'],as_dict = 1)
					if exe_doc.get('creation'):del exe_doc['creation'] 
					if exe_doc.get('docstatus'):del exe_doc['docstatus'] 
					if exe_doc.get('doctype'):del exe_doc['doctype'] 
					if exe_doc.get('idx'):del exe_doc['idx'] 
					if exe_doc.get('modified'):del exe_doc['modified'] 
					if exe_doc.get('modified_by'):del exe_doc['modified_by'] 
					if exe_doc.get('name'):del exe_doc['name']
					if exe_doc.get('owner'):del exe_doc['owner'] 
					exe_doc['operation_type'] = opr.get('operation')
					exe_doc['available_qty'] = qty__r
					exe_doc['qtynos'] = qty__r
					exe_doc['batch_no'] = batch__no
					exe_doc['all_operations_completed'] = 1
					exe_doc['spp_batch_no'] = self.sub_lot_no
					exe_doc['scan_lot_no'] = self.sub_lot_no
					if operator_info:
						exe_doc['scan_operator'] = operator_info.barcode_text
						exe_doc['operator_name'] = operator_info.employee_name
					new_lrt.update(exe_doc)
					new_lrt.insert(ignore_permissions = True)
					exe_lrt = frappe.get_doc("Lot Resource Tagging",new_lrt.name)
					exe_lrt.docstatus = 1
					exe_lrt.save(ignore_permissions = True)
				else:
					frappe.throw(resp_.get('message'))
		else:
			frappe.throw(uom__resp.get('message'))
	else:
		frappe.throw("<b>Lot Resource Tagging</b> details not found..!")

def check_return_workstation(operation_type):
	workstation__resp = get_workstation_by_operation(operation_type)
	if workstation__resp and workstation__resp.get('status') == "success":
		return {"status":"success","message":workstation__resp.get('message')}
	else:
		if workstation__resp:
			return {"status":"failed","message":workstation__resp.get('message')}
		else:
			return {"status":"failed","message":f"Something went wrong while fetching <b>Workstation</b> details.."}

@frappe.whitelist()
def update_lot_barcode(doc):
	try:
		if not doc.barcode_attach and doc.sub_lot_no:
			import code128
			from PIL import Image
			barcode_image = code128.image(doc.sub_lot_no, height=120)
			w, h = barcode_image.size
			margin = 5
			new_h = h +(2*margin) 
			new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
			new_image.paste(barcode_image, (0, margin))
			new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=doc.sub_lot_no), 'PNG')
			frappe.db.set_value(doc.doctype,doc.name,"barcode_attach","/files/" + doc.sub_lot_no + ".png")
			frappe.db.commit()
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.sub_lot_creation.sub_lot_creation.update_lot_barcode",message=frappe.get_traceback())
		frappe.throw("Barcode generation failed..!")

def rollback_entries(self,msg):
	try:
		self.reload()
		if self.stock_entry_reference:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(st_ref)s""",{"st_ref":self.stock_entry_reference})
		del__resp,batch__no = delete_batches([self.sub_lot_no])
		if not del__resp:
			frappe.msgprint(batch__no)
		lot_no = frappe.db.get_value(self.doctype,self.name,"sub_lot_no")
		if lot_no:
			frappe.db.delete("Lot Serial No",{"generated_lot_no":lot_no})
		if self.lrt_found:
			frappe.db.sql(f" DELETE FROM `tabLot Resource Tagging` WHERE scan_lot_no = '{self.sub_lot_no}' ")
		bl_dc = frappe.get_doc(self.doctype, self.name)
		bl_dc.db_set("docstatus", 0)
		frappe.db.commit()
		self.reload()
		frappe.msgprint(msg)
		frappe.enqueue("shree_polymer_custom_app.shree_polymer_custom_app.api.update_stock_balance", queue='default')
	except Exception:
		frappe.db.rollback()
		self.reload()
		frappe.log_error(title="rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def update_sublot(each):
	serial_no = 1
	Lot_no = frappe.db.get_all("Lot Serial No",filters={"source_lot_no":each.scan_lot_no},fields=['serial_no'],order_by="serial_no DESC")
	if Lot_no:
		serial_no = Lot_no[0].serial_no + 1
	sl_no = frappe.new_doc("Lot Serial No")	
	sl_no.serial_no = serial_no
	sl_no.source_lot_no = each.scan_lot_no
	sl_no.generated_lot_no = each.scan_lot_no + '-' + str(serial_no)
	sl_no.insert(ignore_permissions = True)
	each.sub_lot_no = sl_no.generated_lot_no
	frappe.db.set_value(each.doctype,each.name,"sub_lot_no",sl_no.generated_lot_no)
	frappe.db.commit()
	return sl_no.generated_lot_no

def check_uom_bom(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE B.item=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"failed","message":f"Multiple BOM's found for Item - <b>{bom[0].item}</b>"}
			""" End """
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				return {"status":"success","conversion_factor":check_uom[0].conversion_factor}
			else:
				return {"status":"failed","message":"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.sub_lot_creation.sub_lot_creation.check_uom_bom")
		return {"status":"failed","message":"Something went wrong..!"}

def make_repack_entry(self):
	try:
		qty__ = self.qty
		from_qty__ = self.qty
		batch__rep,batch__no = generate_batch_no(batch_id = self.batch_no[:1]+self.sub_lot_no,item = self.item_code,qty = qty__)
		if batch__rep:
			if self.uom == "Nos" and (self.reference_doctype == "Deflashing Receipt Entry" or self.batch_no.lower().startswith('p') or self.item_code.lower().startswith('p')):
				uom__resp = check_uom_bom(self.item_code)
				if uom__resp and uom__resp.get('status') == "success":
					qty = uom__resp.get('conversion_factor') * qty__
					# qty__ = get_decimal_values_without_roundoff(qty,3)
					""" For rounding No's """
					from_qty__ = get_decimal_values_without_roundoff(qty,3)
					qty__ = round(qty)
					""" End """
				else:
					frappe.throw(uom__resp.get('message'))
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Repack"
			stock_entry.company = "SPP"
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			stock_entry.stock_entry_type = "Repack"
			stock_entry.from_warehouse = self.warehouse
			stock_entry.to_warehouse = self.warehouse
			stock_entry.append("items",{
				"item_code":self.item_code,
				"s_warehouse":self.warehouse,
				"stock_uom": self.uom,
				"to_uom": self.uom,
				"uom": self.uom,
				"is_finished_item":0,
				"transfer_qty":from_qty__,
				"qty":from_qty__,
				"batch_no":self.batch_no})
			if self.sub_lot_no:
				bar_dict = generate_barcode(self.sub_lot_no)
				if bar_dict and bar_dict.get('status') == "success":
					stock_entry.append("items",{
						"item_code":self.item_code,
						"t_warehouse":self.warehouse,
						"stock_uom": self.uom,
						"to_uom": self.uom,
						"uom": self.uom,
						"is_finished_item":1,
						"transfer_qty":qty__,
						"qty":qty__,
						"spp_batch_number":self.sub_lot_no,
						"batch_no":batch__no,
						"mix_barcode": bar_dict.get("barcode_text"),
						"barcode_attach":bar_dict.get("barcode"),
						"barcode_text":bar_dict.get("barcode_text"),
						"source_ref_document":self.doctype,
						"source_ref_id":self.name
					})
				else:
					return {"status":"failed","message":"Not able generate barcode..!"}	
			else:
				return {"status":"failed","message":"Not able to update sublot..!"}
			stock_entry.save(ignore_permissions=True)
			""" Update stock entry reference """
			frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
			frappe.db.commit()
			""" End """
			st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			st_entry.docstatus=1
			st_entry.save(ignore_permissions=True)
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{st_entry.name}' ")
			""" End """
			ref_res,batch__no = generate_batch_no(batch_id = batch__no,reference_doctype = "Stock Entry",reference_name = stock_entry.name)
			if ref_res:
				return {"status":"success","st_entry":st_entry,"batch__no":batch__no}
			else:
				return {"status":"failed","message":batch__no}
		else:
			return {"status":"failed","message":batch__no}
	except Exception as e:
		frappe.db.rollback()
		self.reload()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.make_repack_entry")
		return {"status":"failed","message":"Something went wrong, Not able to make <b>Stock Entry</b>"}

def generate_barcode(compound):
	import code128
	from PIL import Image
	barcode_param = barcode_text = str(compound)
	barcode_image = code128.image(barcode_param, height=120)
	w, h = barcode_image.size
	margin = 5
	new_h = h +(2*margin) 
	new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
	new_image.paste(barcode_image, (0, margin))
	import re
	barcode_text = re.sub('[!?/]',"-",barcode_text)
	new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=barcode_text), 'PNG')
	barcode = "/files/" + barcode_text + ".png"
	return {"status":"success","barcode":barcode,"barcode_text":barcode_text}
 
def return_response(lot_no,lot_info):
	if lot_info.get('data').get('qty'):
		resp___ = True
		if lot_info.get('data').get('batch_no').lower().startswith('p') or lot_info['data']['item_code'].lower().startswith('p'):
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":lot_info['data']['item_code'],"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				# lot_info['data']['available_qty_in_kgs'] = flt(lot_info['data']['qty'] / check_uom[0].conversion_factor, 3)
				qty = lot_info['data']['qty'] / check_uom[0].conversion_factor
				lot_info['data']['available_qty_in_kgs'] = get_decimal_values_without_roundoff(qty,3)
			else:
				resp___ = False
				frappe.local.response.status = "failed"
				frappe.local.response.message = "Please define UOM for Kgs for the item <b>"+lot_info['data']['item_code']+"</b>"
		if resp___:
			query = f""" SELECT material_receipt_parent,deflashing_receipt_parent FROM `tabSub Lot Creation` WHERE CASE WHEN sub_lot_no = '{lot_no}' THEN  sub_lot_no = '{lot_no}' ELSE scan_lot_no = '{lot_no}' END LIMIT 1 """
			first__p = frappe.db.sql(query, as_dict = 1)
			if first__p and first__p[0].material_receipt_parent:
				lot_info['data']['material_receipt_parent'] = first__p[0].material_receipt_parent
			else:
				lot_info['data']['material_receipt_parent'] = lot_no
			""" For mapping the deflashing recipt lot parent which validate when split the deflashing entries which comes from material receipt type lots not from work flow """
			if first__p and first__p[0].deflashing_receipt_parent:
				lot_info['data']['deflashing_receipt_parent'] = first__p[0].deflashing_receipt_parent
			else:
				validate_deflash_lottagging(lot_info,"Deflashing Receipt Entry")
			frappe.local.response.status = "success"
			frappe.local.response.message = lot_info.get('data')
	else:
		frappe.response.status = "failed"
		frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"

@frappe.whitelist()
def validate_lot(lot_no,name=None):
	try:
		draft_resp = check_draft_entries(lot_no,name)
		if draft_resp:
			u1__resp = check__u1_warehouse(lot_no)
			if not u1__resp:
				lot_info = get_details_by_lot_no(lot_no,ignore_lot_val = True,transfer_other_warehouse = True)
				# frappe.log_error(title='sub lot_info_resp',message=lot_info)
				if lot_info.get("status") == "success":
					if lot_info.get('data'):
						""" This is not covered in work flow , only for material receipt """
						if lot_info.get('data').get('stock_entry_type') == "Material Receipt":
							return_response(lot_no,lot_info)
							""" End """
						else:
							""" For validate the sublot material transfers which means the sublot split from material receipt type lot not from moulding lots """
							query = f""" SELECT material_receipt_parent FROM `tabSub Lot Creation` WHERE sub_lot_no = '{lot_no}' AND docstatus = 1 """
							res_ = frappe.db.sql(query,as_dict = 1)
							if res_ and res_[0].material_receipt_parent:
								return_response(lot_no,lot_info)
								""" End """
							else:
								""" For validate the sublot despatch to u1 lots which means the sublot split from despatch to u1 type lot not from moulding lots or deflahing recipt lots """
								if not validate__u1_sublots(lot_no,lot_info):
									""" For only inspection entry when split moulding and deflashing receipt entry only """
									deflash_validate = validate_inspection_entry(lot_no,initial_validate = True)
									""" End """
									if deflash_validate:
										resp_p_ = attach_parentlot_details(lot_no,lot_info)
										if resp_p_:
											exe_production_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":lot_info['data']['first_parent_lot_no'],"docstatus":1},['stock_entry_reference',"name"],as_dict=1)
											if not exe_production_entry:
												frappe.local.response.status = "failed"
												frappe.local.response.message = "There is no <b>Moulding Production Entry</b> found for the scanned lot..!"
											else:
												if exe_production_entry.stock_entry_reference:
													st_en_docstatus = frappe.db.get_value("Stock Entry",exe_production_entry.stock_entry_reference,"docstatus")
													if st_en_docstatus and st_en_docstatus == 1:
														if lot_info.get('data').get('deflashing_receipt_parent'):
															lot_info['data']["source_ref_document"] = "Deflashing Receipt Entry"
															check_uom__(lot_info)
														else:
															frappe.local.response.status = "success"
															frappe.local.response.message = lot_info.get('data')
													else:
														frappe.local.response.status = "failed"
														frappe.local.response.message = "The Stock Entry for moulding production entry is not submitted..!"
												else:
													frappe.local.response.status = "failed"
													frappe.local.response.message = "Stock Entry reference not found in Moulding Production Entry..!"
					else:
						frappe.response.status = "failed"
						frappe.response.message = lot_info.get('message')
				else:
					frappe.local.response.status = "failed"
					frappe.local.response.message = lot_info.get('message')
	except Exception:
		frappe.local.response.status = "failed"
		frappe.local.response.message = "Something went wrong..!"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.sub_lot_creation.sub_lot_creation.validate_lot")

def validate_inspection_entry(lot_no,initial_validate):
	if validate_incoming_inspection(lot_no,initial_validate) and validate_lot_inspection(lot_no):
		return True
	else:
		return False

def validate_lot_inspection(lot_no):
	exe_production_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":lot_no,"docstatus":1},['stock_entry_reference',"name"],as_dict=1)
	if exe_production_entry:
		check_line_inspe_entry = frappe.db.get_value("Inspection Entry",{"lot_no":lot_no,"docstatus":1,"inspection_type":"Line Inspection"})
		if check_line_inspe_entry:
			check_lot_inspe_entry = frappe.db.get_value("Inspection Entry",{"lot_no":lot_no,"docstatus":1,"inspection_type":"Lot Inspection"})
			if check_lot_inspe_entry:
				if exe_production_entry.stock_entry_reference:
					st_en_docstatus = frappe.db.get_value("Stock Entry",exe_production_entry.stock_entry_reference,"docstatus")
					if st_en_docstatus and st_en_docstatus == 1:
						return True
					else:
						frappe.local.response.status = "failed"
						frappe.local.response.message = "The Stock Entry for moulding production entry is not submitted..!"
						return False
				else:
					frappe.local.response.status = "failed"
					frappe.local.response.message = "Stock Entry reference not found in Moulding Production Entry..!"
					return False
			else:
				frappe.response.status = "failed"
				frappe.response.message = f"There is no <b>Lot Inspection Entry</b> found for the scanned lot <b>{lot_no}</b>"
				return False
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"There is no <b>Line Inspection Entry</b> found for the scanned lot <b>{lot_no}</b>"
			return False
	return True

def attach_parentlot_details(lot_no,lot_info):
	query = f""" SELECT first_parent_lot_no,deflashing_receipt_parent,lot_resource_tagging_parent FROM `tabSub Lot Creation` WHERE CASE WHEN sub_lot_no = '{lot_no}' THEN  sub_lot_no = '{lot_no}' ELSE scan_lot_no = '{lot_no}' END LIMIT 1 """
	first__p = frappe.db.sql(query, as_dict = 1)
	if first__p and first__p[0].first_parent_lot_no:
		lot_info['data']['first_parent_lot_no'] = first__p[0].first_parent_lot_no
	else:
		validate_moulding_production(lot_info)
	if first__p and first__p[0].deflashing_receipt_parent:
		lot_info['data']['deflashing_receipt_parent'] = first__p[0].deflashing_receipt_parent
	else:
		validate_deflash_lottagging(lot_info,"Deflashing Receipt Entry")
	if first__p and first__p[0].lot_resource_tagging_parent:
		lot_info['data']['lot_resource_tagging_parent'] = first__p[0].lot_resource_tagging_parent
	else:
		validate_deflash_lottagging(lot_info,"Lot Resource Tagging")
	return True

def validate_moulding_production(lot_info):
	exe_production_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":lot_info['data']['spp_batch_number'],"docstatus":1},['stock_entry_reference',"name"],as_dict=1)
	if exe_production_entry and exe_production_entry.stock_entry_reference:
		lot_info['data']['first_parent_lot_no'] = lot_info['data']['spp_batch_number']

def validate_deflash_lottagging(lot_info,parent_type):
	if parent_type == "Deflashing Receipt Entry":
		rept_entry = frappe.db.get_all(parent_type,{"lot_number":lot_info['data']['spp_batch_number'],"docstatus":1},["stock_entry_reference"])
		if rept_entry and rept_entry[0].stock_entry_reference:
			lot_info['data']['deflashing_receipt_parent'] = lot_info['data']['spp_batch_number']
	if parent_type == "Lot Resource Tagging":
		rept_entry = frappe.db.get_all(parent_type,{"scan_lot_no":lot_info['data']['spp_batch_number'],"docstatus":1},["stock_entry_ref"])
		if rept_entry and rept_entry[0].stock_entry_ref:
			lot_info['data']['lot_resource_tagging_parent'] = lot_info['data']['spp_batch_number']
	return True

def check_uom__(lot_info):
	check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":lot_info['data']['item_code'],"uom":"Kg"},fields=['conversion_factor'])
	if check_uom:
		# lot_info['data']['available_qty_in_kgs'] = flt(lot_info['data']['qty'] / check_uom[0].conversion_factor, 3)
		qty = lot_info['data']['qty'] / check_uom[0].conversion_factor
		lot_info['data']['available_qty_in_kgs'] = get_decimal_values_without_roundoff(qty,3)
		ins_inpt = validate_incoming_inspection(lot_info['data']['deflashing_receipt_parent'])
		if ins_inpt:
			lrt = check_lot_resource_tagging(lot_info)
			if lrt:
				frappe.local.response.status = "success"
				frappe.local.response.message = lot_info.get('data')
	else:
		frappe.local.response.status = "failed"
		frappe.local.response.message = "Please define UOM for Kgs for the item <b>"+lot_info['data']['item_code']+"</b>"
	
def validate_incoming_inspection(lot_info,initial_validate = None):
	if not initial_validate:
		check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":lot_info,"inspection_type":"Incoming Inspection"})
		if check_exist:
			rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":lot_info,"docstatus":1},["stock_entry_reference"])
			if rept_entry and rept_entry[0].stock_entry_reference:
				exe__st = frappe.get_doc("Stock Entry",rept_entry[0].stock_entry_reference)
				if exe__st.docstatus == 1:
					return True
				else:
					frappe.local.response.status = "failed"
					frappe.local.response.message = "The Stock Entry for Deflashing Receipt Entry is not submitted..!"
					return False
			else:
				frappe.local.response.status = "failed"
				frappe.local.response.message = f"The Stock Entry for Deflashing Receipt Entry not found for the lot <b>{lot_info}</b>"
				return False
		else:
			frappe.local.response.status = "failed"
			frappe.local.response.message = f"Incoming Inspection not found for the scanned lot <b>{lot_info}</b>"
			return False
	else:
		rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":lot_info,"docstatus":1},["stock_entry_reference"])
		if rept_entry:
			check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":lot_info,"inspection_type":"Incoming Inspection"})
			if check_exist:
				if rept_entry[0].stock_entry_reference:
					exe__st = frappe.get_doc("Stock Entry",rept_entry[0].stock_entry_reference)
					if exe__st.docstatus == 1:
						return True
					else:
						frappe.local.response.status = "failed"
						frappe.local.response.message = "The Stock Entry for Deflashing Receipt Entry is not submitted..!"
						return False
				else:
					frappe.local.response.status = "failed"
					frappe.local.response.message = f"The Stock Entry for Deflashing Receipt Entry not found for the lot <b>{lot_info}</b>"
					return False
			else:
				frappe.local.response.status = "failed"
				frappe.local.response.message = f"Incoming Inspection not found for the scanned lot <b>{lot_info}</b>"
				return False
	return True
	
def check__u1_warehouse(bar_code):
	exe_u1 = frappe.db.sql(f""" SELECT DU.stock_entry_reference FROM `tabDespatch To U1 Entry` DU INNER JOIN `tabDespatch To U1 Entry Item` DUI 
	                            ON DUI.parent = DU.name WHERE DUI.lot_no = '{bar_code}' AND DU.docstatus = 1 LIMIT 1 """,as_dict = 1)
	if exe_u1:
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.p_target_warehouse:
			frappe.response.status = "failed"
			frappe.response.message = "U1 warehouse not mapped in SPP Settings..!"
		else:
			# cond__ = f" AND SLE.warehouse = '{spp_settings.p_target_warehouse}' AND SLE.voucher_no = '{exe_u1[0].stock_entry_reference}' AND SLE.voucher_type = 'Delivery Note'  "
			cond__ = f" AND IBSB.warehouse = '{spp_settings.p_target_warehouse}' "
			lot_info = get_details_by_lot_no(bar_code,condition__ = cond__,from_ledger_entry = True,ignore_lot_val = True)
			# frappe.log_error(title='sublot u1 lot info',message=lot_info)
			if lot_info.get("status") == "success":
				if lot_info.get('data'):
					if lot_info.get('data').get('qty'):
						check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":lot_info['data']['item_code'],"uom":"Kg"},fields=['conversion_factor'])
						if check_uom:
							# lot_info['data']['available_qty_in_kgs'] = flt(lot_info['data']['qty'] / check_uom[0].conversion_factor, 3)
							qty = lot_info['data']['qty'] / check_uom[0].conversion_factor
							lot_info['data']['available_qty_in_kgs'] = get_decimal_values_without_roundoff(qty,3)
							lot_info['data']['t_warehouse'] = lot_info['data']['warehouse']
							del lot_info['data']['warehouse']
							attach__u1_parent(bar_code,lot_info)
							lrt = check_lot_resource_tagging(lot_info)
							if lrt:
								frappe.response.status = 'success'
								frappe.response.message = lot_info['data']
						else:
							frappe.local.response.status = "failed"
							frappe.local.response.message = "Please define UOM for Kgs for the item <b>"+lot_info['data']['item_code']+"</b>"
					else:
						frappe.response.status = "failed"
						frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"
				else:
					frappe.response.status = "failed"
					frappe.response.message = lot_info.get('message')
			else:
				frappe.response.status = "failed"
				frappe.response.message = lot_info.get('message')
		return True
	else:
		return False

def attach__u1_parent(lot_no,lot_info):
	query = f""" SELECT despatch_u1_parent FROM `tabSub Lot Creation` WHERE CASE WHEN sub_lot_no = '{lot_no}' THEN  sub_lot_no = '{lot_no}' ELSE scan_lot_no = '{lot_no}' END LIMIT 1 """
	first__p = frappe.db.sql(query, as_dict = 1)
	if first__p and first__p[0].despatch_u1_parent:
		lot_info['data']['despatch_u1_parent'] = first__p[0].despatch_u1_parent
	else:
		lot_info['data']['despatch_u1_parent'] = lot_no
	
def validate__u1_sublots(lot_no,lot_info):
	if lot_info.get('data').get('qty'):
		query = f""" SELECT despatch_u1_parent FROM `tabSub Lot Creation` WHERE sub_lot_no = '{lot_no}' AND docstatus = 1 """
		res_ = frappe.db.sql(query,as_dict = 1)
		if res_ and res_[0].despatch_u1_parent:
			check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":lot_info['data']['item_code'],"uom":"Kg"},fields=['conversion_factor'])
			if check_uom:
				# lot_info['data']['available_qty_in_kgs'] = flt(lot_info['data']['qty'] / check_uom[0].conversion_factor, 3)
				qty = lot_info['data']['qty'] / check_uom[0].conversion_factor
				lot_info['data']['available_qty_in_kgs'] = get_decimal_values_without_roundoff(qty,3)
				attach__u1_parent(lot_no,lot_info)
				lrt = check_lot_resource_tagging(lot_info)
				if lrt:
					frappe.response.status = 'success'
					frappe.response.message = lot_info['data']
			else:
				frappe.local.response.status = "failed"
				frappe.local.response.message = "Please define UOM for Kgs for the item <b>"+lot_info['data']['item_code']+"</b>"
			return True
		else:
			return False
	else:
		frappe.response.status = "failed"
		frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"
		return True
	
def check_draft_entries(lot_no,name=None):
	doc_list = [{"doctype":"Deflashing Despatch Entry Item","fieldname":"lot_number","select":"parent name"},
	     		{"doctype":"Despatch To U1 Entry","fieldname":"lot_no","select":"name"},
				{"doctype":"Lot Resource Tagging","fieldname":"scan_lot_no","select":"name"},
				{"doctype":"Inspection Entry","fieldname":"lot_no","select":"name"},
				{"doctype":"Sub Lot Creation","fieldname":"scan_lot_no","select":"name"}]
	for docs in doc_list:
		if docs.get('doctype') == 'Inspection Entry':
			query = f""" SELECT {docs.get('select')} FROM `tab{docs.get('doctype')}` WHERE {docs.get('fieldname')} = '{lot_no}' AND docstatus = 0 AND inspection_type = 'Final Visual Inspection' """
		else:
			if name and docs.get('doctype') == "Sub Lot Creation":
				query = f""" SELECT {docs.get('select')} FROM `tab{docs.get('doctype')}` WHERE {docs.get('fieldname')} = '{lot_no}' AND docstatus = 0 AND name != '{name}' """
			else:
				query = f""" SELECT {docs.get('select')} FROM `tab{docs.get('doctype')}` WHERE {docs.get('fieldname')} = '{lot_no}' AND docstatus = 0 """
		if res:=frappe.db.sql(query , as_dict =1):
			frappe.response.status = "failed"
			frappe.response.message = f"The <b>{docs.get('doctype')} - {res[0].name}</b> entry for the lot - <b>{lot_no}</b> is in <b>Draft</b>, Please complete the entry before split..! "
			return False
	return True

def check_multi_bom_vls(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
			return {"status":"success","bom_no":bom[0].name,"item":bom[0].item}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.sub_lot_creation.sub_lot_creation.check_uom_bom")

def check_lot_resource_tagging(lot_info):
	opt__type = frappe.db.sql(f""" SELECT DISTINCT operator_id,operation_type,name FROM `tabLot Resource Tagging` WHERE (scan_lot_no='{lot_info.get('data').get('spp_batch_number')}' OR scan_lot_no='{lot_info.get('data').get('despatch_u1_parent')}') AND 
										docstatus = 1 """,as_dict = 1)
	if opt__type:
		bom_resp__ = check_multi_bom_vls(lot_info.get('data').get('item_code'))
		if bom_resp__ and bom_resp__.get('status') == 'success':
			opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
			opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_resp__.get('bom_no')},as_dict=1)
			if not opeartion_exe:
				frappe.response.status = "failed"
				frappe.response.message = f"<b>Lot Resource Tagging</b> Operations not found in the BOM <b>{bom_resp__.get('bom_no')}</b>"
			else:
				def attach_emp(ele):
					match_found = False
					for oper in opt__type:
						if ele.operation == oper.operation_type:
							match_found = True
							return {"operation":ele.operation,"emp":oper.operator_id}
					if not match_found:
						return {"operation":ele.operation}
				not_completed_oper = list(map(attach_emp,opeartion_exe))
				attach_lrt_info(lot_info,opt__type,not_completed_oper)
				return True
		else:
			if bom_resp__:
				frappe.response.status = bom_resp__.get('status')
				frappe.response.message = bom_resp__.get('message')
			else:
				frappe.response.status = "failed"
				frappe.response.message = f"Something went wrong not able to fetch <b>BOM</b> details..!"
		return False
	return True

def attach_lrt_info(lot_info,opt__type,uncompleted_ope_list):
	import json
	lot_info['data']['containing_lrt_sublot'] = 1
	lot_info['data']['lrt_datas'] = {}
	for e_lrt in opt__type:
		update_stock_ref(lot_info,e_lrt.name)
	lot_info['data']['lrt_datas']['uncompleted_operation_list'] = uncompleted_ope_list
	lot_info['data']['lrt_datas'] = json.dumps(lot_info['data']['lrt_datas'])

def update_stock_ref(lot_info,name):
	if lot_info.get('data').get('lrt_datas').get('ids'):
		lot_info['data']['lrt_datas']['ids'] += "," + name
	else:
		lot_info['data']['lrt_datas']['ids'] = name