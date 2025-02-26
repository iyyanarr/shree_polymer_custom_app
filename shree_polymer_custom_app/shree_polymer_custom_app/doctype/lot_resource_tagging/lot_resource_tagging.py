# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import  flt,getdate, nowdate,now,add_to_date
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series,generate_batch_no,delete_batches,get_details_by_lot_no,get_parent_lot,get_workstation_by_operation
 
class LotResourceTagging(Document):
	def validate(self):
		if not self.operation_type:
			frappe.throw("Please select <b>Operation Type</b>..!")
		if not self.scan_operator:
			frappe.throw(f'Please scan <b>Operator ID</b> before save..!')
		if not self.operator_id:
			frappe.throw(f'Operator ID is missing..!')
		if not self.operations:
			frappe.throw("Bom operations fetch failed..!")
		if frappe.db.get_value("Lot Resource Tagging",{"scan_lot_no":self.scan_lot_no,"name":["!=",self.name],"operation_type":self.operation_type,"docstatus":1,"available_qty":self.available_qty}):
			frappe.throw(f" Entry for scanned job card <b>{self.scan_lot_no}</b> and operation <b>{self.operation_type}</b> is already exists. ")
		if self.qtynos and self.qtynos > self.available_qty:
			frappe.throw(f'The Qty - <b>{self.qtynos}</b> should be less than the available qty - <b>{self.available_qty}</b>')
		if not self.product_ref:
			frappe.throw(f'Item to produce not found.')
		
	def on_submit(self):
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE B.item=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":self.product_ref},as_dict=1)
		if bom:
			opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
			operations = []
			opeartion_exe = frappe.db.sql(""" SELECT BP.name,BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1 AND B.name=%(bom)s {condition} ORDER BY BP.idx """.format(condition=opera_con),{"bom":bom[0].name},as_dict=1)
			for k in opeartion_exe:
				# if k.operation in ["Trimming ID","Trimming OD","Dot Marking","Post Curing","Final Inspection"]:
				operations.append(k.operation)
			opt__type = frappe.db.sql(f""" SELECT DISTINCT operation_type FROM `tab{self.doctype}` WHERE scan_lot_no='{self.scan_lot_no}' AND 
			                   CASE WHEN name !='{self.name}' THEN docstatus = 1 ELSE docstatus !=2 END AND available_qty = '{self.available_qty}' """,as_dict = 1)
			if operations:
				if len(opt__type) == len(operations) and opt__type :
					# self.make_wo_stock_entry()
					frappe.db.sql(f""" UPDATE `tab{self.doctype}` SET all_operations_completed = 1 WHERE name = '{self.name}' """)
					frappe.db.commit()
			else:
				frappe.throw("Operations not mapped in BOM...!")
		else:
			frappe.throw(f"No BOM found associated with the item <b>{self.product_ref}</b>")
		self.reload()
		
	def make_wo_stock_entry(self):
		try:
			wo__resp,msg = create_work_order(self)
			if wo__resp:
				st__resp,msg = make_stock_entry(self,msg)
				if not st__resp:
					rollback_wo_se_jc(self,msg)
					return {'status':'failed','message':""}
				else:
					frappe.db.sql(f""" UPDATE `tab{self.doctype}` SET all_operations_completed = 1 WHERE name = '{self.name}' """)
					frappe.db.commit()
					return {'status':'success','message':msg}
			else:
				rollback_wo_se_jc(self,msg)
				return {'status':'failed','message':""}
		except Exception:
			frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.make_wo_stock_entry",message=frappe.get_traceback())
			return {'status':'failed','message':""}
	
	def rollback_____(self):
		rollback_wo_se_jc(self)	

def rollback_wo_se_jc(info,msg = None):
	try:
		info.reload()
		if info.work_order_ref:
			stock__id = frappe.db.get_value("Stock Entry",{"work_order":info.work_order_ref},"name")
			if stock__id:
				frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock__id}' ")
			frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE work_order = '{info.work_order_ref}' ")
			frappe.db.sql(f" DELETE FROM `tabJob Card` WHERE work_order = '{info.work_order_ref}' ")
			frappe.db.sql(f" DELETE FROM `tabWork Order` WHERE name = '{info.work_order_ref}' ")
		# lot__r = frappe.get_doc(info.doctype, info.name)
		# lot__r.db_set("docstatus", 0)
		frappe.db.commit()
		del__resp,batch__no = delete_batches([info.scan_lot_no])
		if not del__resp:
			frappe.msgprint(batch__no)
		# info.reload()
		if msg:
			frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.rollback_wo_se_jc",message=frappe.get_traceback())
		# lot__r = frappe.get_doc(info.doctype, info.name)
		# lot__r.db_set("docstatus", 0)
		# frappe.db.commit()
		# info.reload()
		frappe.msgprint("Something went wrong , Not able to rollback changes..!")

def make_stock_entry(self,work_order):
	try:
		batch__rep,batch__no = generate_batch_no(batch_id = "F"+self.scan_lot_no,item = work_order.production_item,qty = self.qty_after_rejection_nos)
		if batch__rep:		
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Manufacture"
			stock_entry.work_order = work_order.name
			stock_entry.company = work_order.company
			stock_entry.from_bom = 1
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			stock_entry.bom_no = work_order.bom_no
			stock_entry.set_posting_time = 0
			stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
			stock_entry.stock_entry_type = "Manufacture"
			stock_entry.fg_completed_qty = round(work_order.qty)
			if work_order.bom_no:
				stock_entry.inspection_required = frappe.db.get_value("BOM", work_order.bom_no, "inspection_required")
			stock_entry.from_warehouse = work_order.source_warehouse
			stock_entry.to_warehouse = work_order.fg_warehouse
			# d_spp_batch_no = get_spp_batch_date(self)
			# bcode_resp = generate_barcode("F_"+d_spp_batch_no)
			bcode_resp = generate_barcode(self.scan_lot_no)
			for x in work_order.required_items:
				stock_entry.append("items",{
					"item_code":x.item_code,
					"s_warehouse":work_order.source_warehouse,
					"t_warehouse":None,
					"stock_uom": "Nos",
					"uom": "Nos",
					# "transfer_qty":self.qtynos,
					# "qty":self.qtynos,
					"transfer_qty":self.qty_after_rejection_nos,
					"qty":self.qty_after_rejection_nos,
					"spp_batch_number":self.spp_batch_no,
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
				# """ For rounding No's """
				# "transfer_qty":work_order.qty,
				# "qty":work_order.qty,
				"transfer_qty":round(work_order.qty),
				"qty":round(work_order.qty),
				# End
				# "spp_batch_number": d_spp_batch_no,
				"spp_batch_number": self.scan_lot_no,
				"batch_no":batch__no,
				"mix_barcode":bcode_resp.get("barcode_text"),
				"barcode_attach":bcode_resp.get("barcode"),
				"barcode_text":bcode_resp.get("barcode_text"),
				# "source_ref_document":self.doctype,
				# "source_ref_id":self.name
				"source_ref_document":"Inspection Entry",
				"source_ref_id":frappe.db.get_value("Inspection Entry",{"inspection_type":"Final Visual Inspection","lot_no":self.scan_lot_no,"docstatus":1},'name')
				})
			stock_entry.insert(ignore_permissions=True)
			""" Store stock entry ref in child table """
			frappe.db.set_value(self.doctype,self.name,"stock_entry_ref",stock_entry.name)
			frappe.db.commit()
			""" End """
			sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			sub_entry.docstatus = 1
			sub_entry.save(ignore_permissions=True)
			""" Update posting date and time """
			# frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.posting_date}' WHERE name = '{sub_entry.name}' ")
			""" End """
			ref_res,batch__no = generate_batch_no(batch_id = batch__no,reference_doctype = "Stock Entry",reference_name = sub_entry.name)
			if ref_res:
				frappe.db.set_value("Inspection Entry",{"inspection_type":"Final Visual Inspection","lot_no":self.scan_lot_no,"docstatus":1},"vs_pdir_stock_entry_ref",sub_entry.name)
				frappe.db.commit()
				return True,batch__no
			else:
				return False,"Stock Entry Reference update failed in Batch..!"
		else:
			return False,"Batch No generation failed"
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.make_stock_entry")
		frappe.db.rollback()
		return False,"Stock Entry creation failed."

def create_work_order(doc_info):
	try:
		import time
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":doc_info.product_ref},as_dict=1)
		if bom:
			ope_wrk_pair = []
			operations = doc_info.operations.split(',') if doc_info.operations else []
			# operations += ["Final Visual Inspection","PDIR"]
			operations += ["Final Visual Inspection"]
			for ope in operations:
				workstation__resp = get_workstation_by_operation(ope)
				if workstation__resp and workstation__resp.get('status') == "success":
					ope_wrk_pair.append({"workstation":workstation__resp.get('message'),"operation":ope})
				else:
					if workstation__resp:
						return False,workstation__resp.get('message')
					else:
						return False,f"Something went wrong while fetching <b>Workstation</b> details.."
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.unit_2_warehouse:
				return False,"Unit-2 warehouse not mapped in <b>SPP Settings</b>"
			if not spp_settings.default_time:
				return False,"Default operation time is not mapped in <b>SPP Settings</b>"
			if not spp_settings.wip_warehouse:
				return False,"Work in progress warehouse is not mapped in <b>SPP Settings</b>"
			wo = frappe.new_doc("Work Order")
			wo.naming_series = "MFG-WO-.YYYY.-"
			wo.company = "SPP"
			wo.fg_warehouse = spp_settings.unit_2_warehouse
			wo.use_multi_level_bom = 0
			wo.skip_transfer = 1
			wo.source_warehouse = doc_info.warehouse
			wo.wip_warehouse = spp_settings.wip_warehouse
			wo.transfer_material_against = "Work Order"
			wo.bom_no = bom[0].name
			for ope in operations:
				wo.append("operations",{
					"operation":ope,
					"bom":bom[0].name,
					"workstation":list(filter(lambda x:x.get('operation') == ope,ope_wrk_pair))[0].get('workstation'),
					# "time_in_mins":frappe.db.get_value("BOM Operation",{"parent":bom[0].name,"operation":ope},"time_in_mins"),
					# "workstation":spp_settings.deflash_workstation,
					"time_in_mins":spp_settings.default_time,
					})
			wo.referenceid = round(time.time() * 1000)
			wo.production_item = bom[0].item
			""" For rounding No's """
			# wo.qty = doc_info.qty_after_rejection_nos
			wo.qty = round(doc_info.qty_after_rejection_nos)
			"""End"""
			wo.insert(ignore_permissions=True)
			frappe.db.set_value(doc_info.doctype,doc_info.name,"work_order_ref",wo.name)
			frappe.db.commit()
			wo_ = frappe.get_doc("Work Order",wo.name)
			wo_.docstatus = 1
			wo_.save(ignore_permissions=True)
			update_job_cards(wo.name,doc_info.qty_after_rejection_nos,doc_info,doc_info.product_ref)
			frappe.db.set_value("Inspection Entry",{"inspection_type":"Final Visual Inspection","lot_no":doc_info.scan_lot_no,"docstatus":1},"vs_pdir_work_order_ref",wo.name)
			frappe.db.commit()
			return True,wo
		else:
			return False,f"Bom is not found for the item to produce - <b>{doc_info.product_ref}</b>"
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.create_work_order")
		return False,"Work order creation failed."

def update_job_cards(wo,actual_weight,doc_info,item):
	spp_settings = frappe.get_single("SPP Settings")
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	operations = frappe.db.get_all("Work Order Operation",filters={"parent":wo},fields=['time_in_mins'])
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		jc.append("time_logs", {
			
			"from_time": now(),"completed_qty": flt(actual_weight,3),
			"time_in_mins": spp_settings.default_time
		})
		for time_log in jc.time_logs:
			""" For rounding No's """
			# time_log.completed_qty = flt("{:.3f}".format(actual_weight))
			time_log.completed_qty = round(actual_weight)
			""" End"""
			if operations:
				time_log.time_in_mins = spp_settings.default_time
		""" For rounding No's """
		# jc.total_completed_qty = flt("{:.3f}".format(actual_weight))
		jc.total_completed_qty = round(actual_weight)
		""" End"""
		""" For mainting single lot number to all process the moulding lot number replaced """
		# jc.batch_code = doc_info.scan_lot_no
		""" For maintaing the same lot number the source lot number saved in the job card i.e intead of sub lot number the parent lot number saved """
		""" For fiind parent and parent of parent the get_parent_lot function two times called """
		parent__lot = get_parent_lot(doc_info.scan_lot_no)
		if parent__lot and parent__lot.get('status') == 'success' and parent__lot.get('lot_no'):
			parent__lot = get_parent_lot(parent__lot.get('lot_no'))
			if parent__lot and parent__lot.get('status') == 'success' and parent__lot.get('lot_no'):
				jc.batch_code = parent__lot.get('lot_no')
			else:
				jc.batch_code = doc_info.scan_lot_no
		else:
			jc.batch_code = doc_info.scan_lot_no
		""" End """
		jc.docstatus = 1
		jc.save(ignore_permissions=True)

def get_spp_batch_date(self):
	spp_no = None
	serial_no = frappe.db.get_all("LRT Serial No",{"lot_number":self.scan_lot_no,"batch_no":self.batch_no},["spp_batch_no"],order_by="creation DESC")
	if serial_no:
		spp_no = self.spp_batch_no + '-' + str(int(serial_no[0].spp_batch_no.split('-').pop()) + 1)
	else:
		spp_no = self.spp_batch_no + '-1'
	n__doc = frappe.new_doc("LRT Serial No")
	n__doc.lot_number = self.scan_lot_no
	n__doc.batch_no = self.batch_no
	n__doc.spp_batch_no = spp_no
	n__doc.insert(ignore_permissions = True)
	return n__doc.spp_batch_no
			
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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.generate_barcode")

def check_uom_bom(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
			""" End """
			# check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":bom[0].item,"uom":"Kg"},fields=['conversion_factor'])
			# if check_uom:
			# 	return {"status":"success"}
			# else:
			# 	return {"status":"failed","message":"Please define UOM for Kgs for the item <b>"+bom[0].item+"</b>"}
			return {"status":"success","bom":bom[0].name,"item":bom[0].item}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.check_uom_bom")

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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.check_available_stock")
		return {"status":"failed","message":"Something went wrong"}

@frappe.whitelist(allow_guest = True)
def validate_lot_number(barcode,operation_type = None):
	try:
		sublot__resp = check_sublot(barcode,operation_type)
		if not sublot__resp:
			rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":barcode,"docstatus":1},["stock_entry_reference"],as_dict = 1)
			if rept_entry:
				check_exist = validate_dre_ins_jc(barcode)
				if check_exist:
					job_card = check_exist.get("job_card")
					if not rept_entry.stock_entry_reference:
						frappe.response.status = 'failed'
						frappe.response.message = f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{barcode}</b>"
					else:
						product_details = frappe.db.sql(f""" SELECT  SED.t_warehouse as from_warehouse,SED.item_code,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
														INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
														LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry.stock_entry_reference}' AND SED.deflash_receipt_reference='{barcode}' """,as_dict=1)
						if product_details:
							stock_status = check_available_stock(product_details[0].get("from_warehouse"),product_details[0].get("item_code"),product_details[0].get("batch_no",""))
							if stock_status.get('status') == "success":
								product_details[0].qty_from_item_batch = stock_status.get('qty')
								bom_uom_resp = check_uom_bom(product_details[0].item_code)
								if bom_uom_resp.get('status') == "success":
									job_card['bom_no'] = bom_uom_resp.get('bom')
									job_card['production_item'] = bom_uom_resp.get('item')
									opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
									opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":job_card.bom_no},as_dict=1)
									product_details[0].bom_operations = opeartion_exe
									job_card.update(product_details[0])
									frappe.response.status = 'success'
									frappe.response.message = job_card
										# opeartion_exe = frappe.db.sql(""" SELECT BP.name FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1 AND BP.operation=%(operation)s AND B.name=%(bom)s""",{"bom":job_card.bom_no,"operation":operation_type},as_dict=1)
										# if opeartion_exe:
										# 	job_card.update(product_details[0])
										# 	frappe.response.status = 'success'
										# 	frappe.response.message = job_card
										# else:
										# 	frappe.response.status = 'failed'
										# 	frappe.response.message = f"The <b>{operation_type}</b> operation is not found in <b>BOM</b>"
								else:
									frappe.response.status = bom_uom_resp.get('status')
									frappe.response.message = bom_uom_resp.get('message')
							else:
								frappe.response.status = stock_status.get('status')
								frappe.response.message = stock_status.get('message')
						else:
							frappe.response.status = 'failed'
							frappe.response.message = f"There is no <b>Stock Entry</b> found for the scanned lot <b>{barcode}</b>"
			else:
				frappe.response.status = 'failed'
				frappe.response.message = f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{barcode}</b>"
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_lot_number")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."

@frappe.whitelist()
def check_return_workstation(operation_type):
	workstation__resp = get_workstation_by_operation(operation_type)
	if workstation__resp and workstation__resp.get('status') == "success":
		return {"status":"success","message":workstation__resp.get('message')}
	else:
		if workstation__resp:
			return {"status":"failed","message":workstation__resp.get('message')}
		else:
			return {"status":"failed","message":f"Something went wrong while fetching <b>Workstation</b> details.."}
	
def check_sublot(bar_code,operation_type):
	u1__resp = check__u1_warehouse(bar_code,operation_type)
	if not u1__resp:
		recept__resp = check__material_recp(bar_code,operation_type)
		if not recept__resp:
			cond__ = f" AND (SE.stock_entry_type = 'Repack' OR SE.stock_entry_type = 'Manufacture') AND (SED.source_ref_document = 'Sub Lot Creation' OR SED.source_ref_document = 'Deflashing Receipt Entry' ) "
			lot_info = get_details_by_lot_no(bar_code,condition__ = cond__,ref_doc = "Lot Resource Tagging")
			# frappe.log_error(title="lot_info",message=lot_info)
			if lot_info.get("status") == "success":
				recept__resp = check__u1_sublot(lot_info,bar_code,operation_type)
				if not recept__resp:
					if lot_info.get('data'):
						""" If there is no sublot created no need to validate directly validate in deflashing receipt entry """
						if lot_info.get('data').get("source_ref_document") == "Deflashing Receipt Entry":
							rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":bar_code,"docstatus":1},"stock_entry_reference")
							if rept_entry:
								return_response(bar_code,lot_info,operation_type)
							else:
								frappe.response.status = 'failed'
								frappe.response.message = f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{bar_code}</b>"
						else:
							""" If sublot spilited for the deflshing receipt entry generated batcheds need to find deflashing source batch then need to find mould batch number for validate inspection entries """
							parent__lot = get_parent_lot(bar_code,field_name="deflashing_receipt_parent")
							if parent__lot and parent__lot.get('status') == 'success':
								return_response(parent__lot.get('lot_no'),lot_info,operation_type)
							else:
								if parent__lot:
									frappe.response.status = "failed"
									frappe.response.message = parent__lot.get('message')
					else:
						frappe.response.status = "failed"
						frappe.response.message = lot_info.get('message')
					return True
				else:
					return True
			else:
				return False
		else:
			return True
	else:
		return True
	
def check__material_recp(bar_code,operation_type):
	#Added on 4/7/2023 for incoming inspection validation for Final visual inspection entry
	# lot_info = get_details_by_lot_no(bar_code,transfer_other_warehouse = True)
	lot_info = get_details_by_lot_no(bar_code,transfer_other_warehouse = True,ref_doc="Incoming Inspection Entry")
	#end
	# frappe.log_error(title="material recpt lot_info",message=lot_info)
	if lot_info.get("status") == "success":
		if lot_info.get('data'):
			""" This is not covered in work flow , this is for material receipt func """
			if lot_info.get('data').get('stock_entry_type') == "Material Receipt":
				material_respt_return_response(lot_info,operation_type)
				return True
				""" End """
			else:
				""" First validate material receipt entry exists """
				parent__lot = get_parent_lot(bar_code,field_name = "material_receipt_parent")
				if parent__lot and parent__lot.get('status') == 'success':
					material_respt_return_response(lot_info,operation_type)
					return True
					""" End """
		else:
			frappe.response.status = "failed"
			frappe.response.message = lot_info.get('message')
			return True
	return False

def material_respt_return_response(lot_info,operation_type = None):
	if lot_info.get('data').get('qty'):
		lot_info['data']['from_warehouse'] = lot_info.get('data').get('t_warehouse')
		lot_info['data']['qty_from_item_batch'] = lot_info.get('data').get('qty')
		bom_uom_resp = check_uom_bom(lot_info['data'].item_code)
		if bom_uom_resp.get('status') == "success":
			lot_info['data']['bom_no'] = bom_uom_resp.get('bom')
			lot_info['data']['production_item'] = bom_uom_resp.get('item')
			opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
			opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_uom_resp.get('bom')},as_dict=1)
			lot_info['data'].bom_operations = opeartion_exe
			frappe.response.status = 'success'
			frappe.response.message = lot_info['data']
				# opeartion_exe = frappe.db.sql(""" SELECT BP.name FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1 AND BP.operation=%(operation)s AND B.name=%(bom)s""",{"bom":bom_uom_resp.get('bom'),"operation":operation_type},as_dict=1)
				# if opeartion_exe:
				# 	frappe.response.status = 'success'
				# 	frappe.response.message = lot_info['data']
				# else:
				# 	frappe.response.status = 'failed'
				# 	frappe.response.message = f"The <b>{operation_type}</b> operation is not found in <b>BOM</b>"
		else:
			frappe.response.status = bom_uom_resp.get('status')
			frappe.response.message = bom_uom_resp.get('message')
	else:
		frappe.response.status = "failed"
		frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"
			
def check__u1_warehouse(bar_code,operation_type):
	exe_u1 = frappe.db.sql(f""" SELECT DU.stock_entry_reference,DUI.product_ref FROM `tabDespatch To U1 Entry` DU INNER JOIN `tabDespatch To U1 Entry Item` DUI 
	                            ON DUI.parent = DU.name WHERE DUI.lot_no = '{bar_code}' AND DU.docstatus = 1 LIMIT 1 """,as_dict = 1)
	if exe_u1:
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.p_target_warehouse:
			frappe.response.status = "failed"
			frappe.response.message = "U1 warehouse not mapped in SPP Settings..!"
		else:
			# cond__ = f" AND IBSB.warehouse = '{spp_settings.p_target_warehouse}' "
			# cond__ = f" AND SLE.warehouse = '{spp_settings.p_target_warehouse}' AND SLE.voucher_no = '{exe_u1[0].stock_entry_reference}' AND SLE.voucher_type = 'Delivery Note'  "
			cond__ = f" AND IBSB.warehouse = '{spp_settings.p_target_warehouse}' AND IBSB.item_code='{exe_u1[0].product_ref}' "
			lot_info = get_details_by_lot_no(bar_code,condition__ = cond__,from_ledger_entry = True,ignore_lot_val = True)
			# frappe.log_error(title='u1 lot info',message=lot_info)
			if lot_info.get("status") == "success":
				if lot_info.get('data'):
					if lot_info.get('data').get('qty'):
						lot_info['data']['from_warehouse'] = lot_info.get('data').get('warehouse')
						lot_info['data']['qty_from_item_batch'] = lot_info.get('data').get('qty')
						bom_uom_resp = check_uom_bom(lot_info['data'].item_code)
						if bom_uom_resp.get('status') == "success":
							lot_info['data']['bom_no'] = bom_uom_resp.get('bom')
							lot_info['data']['production_item'] = bom_uom_resp.get('item')
							opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
							opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_uom_resp.get('bom')},as_dict=1)
							lot_info['data'].bom_operations = opeartion_exe
							frappe.response.status = 'success'
							frappe.response.message = lot_info['data']
								# opeartion_exe = frappe.db.sql(""" SELECT BP.name FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1 AND BP.operation=%(operation)s AND B.name=%(bom)s""",{"bom":bom_uom_resp.get('bom'),"operation":operation_type},as_dict=1)
								# if opeartion_exe:
								# 	frappe.response.status = 'success'
								# 	frappe.response.message = lot_info['data']
								# else:
								# 	frappe.response.status = 'failed'
								# 	frappe.response.message = f"The <b>{operation_type}</b> operation is not found in <b>BOM</b>"
						else:
							frappe.response.status = bom_uom_resp.get('status')
							frappe.response.message = bom_uom_resp.get('message')
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

def return_response(parent__lot,lot_info,operation_type):
	jc_ins_resp_ = validate_dre_ins_jc(parent__lot,ignore_jobcard = True)
	if jc_ins_resp_ :
		if lot_info.get('data').get('qty'):
			lot_info['data']['from_warehouse'] = lot_info.get('data').get('t_warehouse')
			lot_info['data']['qty_from_item_batch'] = lot_info.get('data').get('qty')
			bom_uom_resp = check_uom_bom(lot_info['data'].item_code)
			if bom_uom_resp.get('status') == "success":
				lot_info['data']['bom_no'] = bom_uom_resp.get('bom')
				lot_info['data']['production_item'] = bom_uom_resp.get('item')
				opera_con = "  AND BP.operation NOT IN ('PDIR','Final Visual Inspection') "
				opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":bom_uom_resp.get('bom')},as_dict=1)
				lot_info['data'].bom_operations = opeartion_exe
				frappe.response.status = 'success'
				frappe.response.message = lot_info['data']
					# opeartion_exe = frappe.db.sql(""" SELECT BP.name FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1 AND BP.operation=%(operation)s AND B.name=%(bom)s""",{"bom":bom_uom_resp.get('bom'),"operation":operation_type},as_dict=1)
					# if opeartion_exe:
					# 	frappe.response.status = 'success'
					# 	frappe.response.message = lot_info['data']
					# else:
					# 	frappe.response.status = 'failed'
					# 	frappe.response.message = f"The <b>{operation_type}</b> operation is not found in <b>BOM</b>"
			else:
				frappe.response.status = bom_uom_resp.get('status')
				frappe.response.message = bom_uom_resp.get('message')
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"
	
def validate_dre_ins_jc(barcode,ignore_jobcard = None):
	# frappe.log_error(title="b code",message=barcode)
	if ignore_jobcard:
		check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":barcode,"inspection_type":"Incoming Inspection"})
		if check_exist:
			return {"status":"success"}
		else:
			frappe.response.status = 'failed'
			frappe.response.message = f'There is no <b>Incoming Inspection Entry</b> found for the scanned lot <b>{barcode}</b>'	
	else:
		job_card = frappe.db.get_value("Job Card",{"batch_code":barcode,"operation":"Deflashing"},["name","production_item","bom_no","moulding_lot_number"],as_dict=1)
		if job_card:
			# return {"status":"success","job_card":job_card}
			check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":barcode,"inspection_type":"Incoming Inspection"})
			if check_exist:
				return {"status":"success","job_card":job_card}
			else:
				frappe.response.status = 'failed'
				frappe.response.message = f'There is no <b>Incoming Inspection Entry</b> found for the scanned lot <b>{barcode}</b>'	
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Job Card not found for the lot <b>"+barcode+"</b>"	

def check__u1_sublot(lot_info,bar_code,operation_type):
	query = f""" SELECT despatch_u1_parent FROM `tabSub Lot Creation` WHERE CASE WHEN sub_lot_no = '{bar_code}' THEN  sub_lot_no = '{bar_code}' ELSE scan_lot_no = '{bar_code}' END LIMIT 1 """
	first__p = frappe.db.sql(query, as_dict = 1)
	if first__p and first__p[0].despatch_u1_parent:
		material_respt_return_response(lot_info,operation_type)
		return True
	return False

@frappe.whitelist()
def validate_inspector_barcode(b__code,operation_type):
	try:
		check_emp = frappe.db.sql(""" SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s """,{"barcode":b__code},as_dict=1)
		if check_emp:
			spp_settings = frappe.get_single("SPP Settings")
			designation = ""
			if spp_settings and spp_settings.designation_mapping:
				for desc in spp_settings.designation_mapping:
					if desc.spp_process == operation_type:
						if desc.designation:
							designation += f"'{desc.designation}',"
					elif operation_type.lower().startswith('final inspect'):
						if "Final Inspection" == operation_type:
							if desc.designation:
								designation += f"'{desc.designation}',"
			if designation:
				designation = designation[:-1]
				check_emp = frappe.db.sql(f"""SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s AND designation IN ({designation}) """,{"barcode":b__code},as_dict=1)
				if check_emp:
					frappe.response.status = 'success'
					frappe.response.message = check_emp[0]
				else:
					frappe.response.status = 'failed'
					frappe.response.message = f"The Employee is not allowed to perform the operation <b>{operation_type}</b>..!"
			else:
				frappe.response.status = 'failed'
				frappe.response.message = "Designation not mapped in SPP Settings."
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Invalid Employee ID or Employee is not active..!"
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_inspector_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."


# @frappe.whitelist()
# def validate_inspector_barcode(b__code,operations):
# 	try:
# 		check_emp = frappe.db.sql(f"""SELECT designation,name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s """,{"barcode":b__code},as_dict=1)
# 		if check_emp:
# 			check_emp[0].operation = []
# 			operations_ = operations.split(',')
# 			spp_settings = frappe.get_single("SPP Settings")
# 			if spp_settings and spp_settings.designation_mapping:
# 				for desc in spp_settings.designation_mapping:
# 					if desc.spp_process in operations_:
# 						if desc.designation:
# 							if check_emp[0].designation == desc.designation:
# 								if desc.spp_process not in check_emp[0].operation:
# 									check_emp[0].operation.append(desc.spp_process)
# 				if check_emp[0].operation:
# 					frappe.response.status = 'success'
# 					frappe.response.message = check_emp[0]
# 				else:
# 					frappe.response.status = 'failed'
# 					frappe.response.message = "The Employee is not allowed to do any operation..!"
# 			else:
# 				frappe.response.status = 'failed'
# 				frappe.response.message = "Designation not mapped in SPP Settings."
# 		else:
# 			frappe.response.status = 'failed'
# 			frappe.response.message = f"Employee not found for the scanned barcode <b>{b__code}</b>"
# 	except Exception:
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_inspector_barcode")
# 		frappe.response.status = 'failed'
# 		frappe.response.message = "Something went wrong."



""" Backup """
# @frappe.whitelist()
# def validate_lot_number(barcode,docname,operation_type):
# 	try:
# 		# if not frappe.db.get_value("Lot Resource Tagging",{"scan_lot_no":barcode,"name":["!=",docname],"operation_type":operation_type,"docstatus":1}):
# 			job_card = frappe.db.get_value("Job Card",{"batch_code":barcode,"operation":"Deflashing"},["name","production_item","bom_no","moulding_lot_number"],as_dict=1)
# 			if job_card:
# 				check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":barcode,"inspection_type":"Incoming Inspection"})
# 				if check_exist:
# 					rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":barcode,"docstatus":1},["stock_entry_reference"])
# 					if rept_entry:
# 						if not rept_entry[0].stock_entry_reference:
# 							frappe.response.status = 'failed'
# 							frappe.response.message = f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{barcode}</b>"
# 						else:
# 							product_details = frappe.db.sql(f""" SELECT  SED.t_warehouse as from_warehouse,SED.item_code,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
# 															INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
# 															LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{barcode}' """,as_dict=1)
# 							if product_details:
# 								stock_status = check_available_stock(product_details[0].get("from_warehouse"),product_details[0].get("item_code"),product_details[0].get("batch_no",""))
# 								if stock_status.get('status') == "success":
# 									product_details[0].qty_from_item_batch = stock_status.get('qty')
# 									# if not frappe.db.get_value("Lot Resource Tagging",{"scan_lot_no":barcode,"name":["!=",docname],"operation_type":operation_type,"docstatus":1,"available_qty":product_details[0].qty_from_item_batch}):
# 									bom_uom_resp = check_uom_bom(product_details[0].item_code)
# 									if bom_uom_resp.get('status') == "success":
# 										job_card['bom_no'] = bom_uom_resp.get('bom')
# 										job_card['production_item'] = bom_uom_resp.get('item')
# 										if frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":barcode,"docstatus":1}):
# 											opeartion_exe = frappe.db.sql(""" SELECT BP.name FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1 AND BP.operation=%(operation)s AND B.name=%(bom)s""",{"bom":job_card.bom_no,"operation":operation_type},as_dict=1)
# 											if opeartion_exe:
# 												job_card.update(product_details[0])
# 												frappe.response.status = 'success'
# 												frappe.response.message = job_card
# 											else:
# 												frappe.response.status = 'failed'
# 												frappe.response.message = f"The <b>{operation_type}</b> operation is not found in <b>BOM</b>"
# 										else:
# 											frappe.response.status = 'failed'
# 											frappe.response.message = "<b>Deflashing Receipt Entry</b> not found for the Scanned job card <b>"+barcode+"</b>."
# 									else:
# 										frappe.response.status = bom_uom_resp.get('status')
# 										frappe.response.message = bom_uom_resp.get('message')
# 									# else:
# 									# 	frappe.response.status = 'failed'
# 									# 	frappe.response.message = f" Entry for scanned job card <b>{barcode}</b> and operation <b>{operation_type}</b> is already exists. "
# 								else:
# 									frappe.response.status = stock_status.get('status')
# 									frappe.response.message = stock_status.get('message')
# 							else:
# 								frappe.response.status = 'failed'
# 								frappe.response.message = f"There is no <b>Stock Entry</b> found for the scanned lot <b>{barcode}</b>"
# 					else:
# 						frappe.response.status = 'failed'
# 						frappe.response.message = f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{barcode}</b>"
# 				else:
# 					frappe.response.status = 'failed'
# 					frappe.response.message = f'There is no <b>Incoming Inspection Entry</b> found for the lot <b>{barcode}</b>'	
# 			else:
# 				frappe.response.status = 'failed'
# 				frappe.response.message = "Scanned job card <b>"+barcode+"</b> not exist."
# 		# else:
# 		# 	frappe.response.status = 'failed'
# 		# 	frappe.response.message = f" Entry for scanned job card <b>{barcode}</b> and operation <b>{operation_type}</b> is already exists. "
# 	except Exception:
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_lot_number")
# 		frappe.response.status = 'failed'
# 		frappe.response.message = "Something went wrong."


# if not product_details[0].bom_operations:
# 	opera_con = "  AND BP.operation IN ('PDIR','Final Visual Inspection') "
# 	opeartion_exe = frappe.db.sql(""" SELECT BP.operation FROM `tabBOM Operation` BP INNER JOIN `tabBOM` B ON BP.parent = B.name WHERE B.is_default=1 AND B.is_active=1  AND B.name=%(bom)s {condition} """.format(condition = opera_con),{"bom":job_card.bom_no},as_dict=1)
# 	if opeartion_exe:
# 		frappe.response.status = "failed"
# 		frappe.response.message = f"The <b>{job_card.bom_no}</b> having only {','.join([k.operation for k in opeartion_exe])}"
# 	else:
# 		frappe.response.status = "failed"
# 		frappe.response.message = "<b>Operations</b> not mapped in BOM..!"
# else: