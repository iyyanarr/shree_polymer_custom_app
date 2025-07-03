# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate,flt
from frappe.utils.data import get_time, now

class AddOnWorkPlanning(Document):
	""" Store target item qty and bom for work order creation and validation """
	qty_wt_item = []
	bom_wt_item = []
	""" End """
	def validate(self):
		if not self.shift_series:
			frappe.throw("<b>Shift Series</b> is not found..!")
		if not self.shift_time:
			frappe.throw("<b>Shift Time</b> is not found..!")
		self.validate_amended()
		# self.validate_shift_mould()
		if self.items:
			""" Target Qty Validation """
			item_array = []
			condt = ''
			for each_item in self.items:
				item_array.append(each_item.item)
				condt += f'"{each_item.item}",'
			condt = condt[:-1]
			# query = f"""  SELECT item,target_qty FROM `tabWork Plan Item Target` WHERE item IN ({condt}) AND target_qty != 0 """
			query = f"""  SELECT item,target_qty FROM `tabWork Plan Item Target` WHERE item IN ({condt}) AND shift_type = "{self.shift_time}" AND target_qty != 0 """
			result = frappe.db.sql(query,as_dict=1) 
			unset_qty = result if result else []
			unset_qtys = []
			for u_qty in unset_qty:
				unset_qtys.append(u_qty.item)
				self.qty_wt_item.append({"item":u_qty.item,"qty":u_qty.target_qty})
			if len(item_array) != len(unset_qty):
				not_qty_item = list(filter(lambda x: x not in unset_qtys, item_array))
				if not_qty_item:
					frappe.throw(f"Target qty value of {'items' if len(not_qty_item)>1 else 'item'} <b>{', '.join(not_qty_item)}</b> is not found for the Shift Type <b>{self.shift_type}</b>...!")
		else:
			frappe.throw("Please add items before save.")

	""" Change the job card / work order flag for appending the custom button when amend the form """
	def validate_amended(self):
		if self.is_new() and self.amended_from:
			self.job_card_wo = 0

	def validate_shift_mould(self):
		exe_shift = frappe.db.get_value(self.doctype,{"date":getdate(self.date),"shift_series":self.shift_series,"name":["!=",self.name],"docstatus":1})
		if exe_shift:
			frappe.throw(f"The shift <b>{self.shift_type}</b> already scheduled in the plan <b>{exe_shift}</b>")
		# exe_shift = frappe.db.get_value(self.doctype,{"date":getdate(self.date),"shift_number":self.shift_number,"name":["!=",self.name],"docstatus":1})
		# if exe_shift:
		# 	frappe.throw(f"The shift <b>{self.shift_number}</b> already scheduled in the plan <b>{exe_shift}</b>")

	def on_submit_value(self):
		valididate = validate_bom(self)
		if valididate.get("status"):
			if self.items:
				wo = self.create_work_order()
				""" For custom button api response added """
				if wo:
					frappe.db.set_value(self.doctype,self.name,"job_card_wo",1)
					frappe.db.commit()
					return True
				else:
					self.reload()
					self.on_cancel()
					return False
			else:
				return False
			""" End """ 
		else:
			frappe.throw(valididate.get("message"))
			return False
		
	def on_cancel(self):
		if self.items:
			for jb in self.items:
				lot__no = frappe.db.get_value("Job Card",{"name":jb.job_card},["batch_code","name"],as_dict = 1)
				if lot__no:
					blank_bin_issue = frappe.db.get_value("Blank Bin Issue",{"scan_production_lot":lot__no.batch_code,"docstatus":1})
					if blank_bin_issue:
						frappe.throw(f"Not allowed to cancel the <b>Work Planning</b>..!<br>The <b>Blank Bin Issue Entry</b> is exists for the Job Card <b>{lot__no.name}</b>..!")
					blank_bin_issue = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":lot__no.batch_code,"docstatus":1})
					if blank_bin_issue:
						frappe.throw(f"Not allowed to cancel the <b>Work Planning</b>..!<br>The <b>Moulding Production Entry</b> is exists for the Job Card <b>{lot__no.name}</b>..!")
			try:
				for item in self.items:
					if item.job_card and frappe.db.get_value("Job Card",{"name":item.job_card}):
						jc = frappe.get_doc("Job Card",item.job_card)
						if jc.docstatus == 1:
							jc.db_set("docstatus",2)
							frappe.db.commit()
						wo = frappe.get_doc("Work Order",jc.work_order)
						if wo.docstatus == 1:
							wo.db_set("docstatus",2)
							frappe.db.commit()
						frappe.db.delete("Job Card",{"name":jc.name})
						frappe.db.delete("Work Order",{"name":wo.name})
				self.delete_serial_no()
				for item in self.items:
					item.job_card = ''
					frappe.db.set_value(item.doctype,item.name,"job_card","")
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.add_on_work_planning.add_on_work_planning.on_cancel")
				frappe.throw("Somthing went wrong , Can't Cancel Delete Job Card/Work Order")

	def delete_serial_no(self):
		self.reload()
		for each in self.items:
			if each.job_card:
				frappe.db.delete("Moulding Serial No",{"job_card_reference":each.job_card})
		frappe.db.commit()

	def create_work_order(doc_info):
		try:
			import time
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.target_qty:
				frappe.throw("Value not found for no.of times to add qty in SPP Settings")
			if not spp_settings.default_time:
				frappe.throw("Value not found for default time in SPP Settings")
			for item in doc_info.items:
				# bom = list(filter(lambda x: x.get('item') == item.item,doc_info.bom_wt_item))[0].get('bom')
				bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":item.item},as_dict=1)
				actual_weight = flt(spp_settings.target_qty,3) * flt(list(filter(lambda x: x.get('item') == item.item,doc_info.qty_wt_item))[0].get('qty'),3)
				wo = frappe.new_doc("Work Order")
				wo.naming_series = "MFG-WO-.YYYY.-"
				wo.company = "SPP"
				wo.fg_warehouse = spp_settings.unit_2_warehouse
				wo.use_multi_level_bom = 0
				wo.skip_transfer = 1
				# wo.source_warehouse = spp_settings.unit_2_warehouse
				wo.source_warehouse = spp_settings.default_sheeting_warehouse
				wo.wip_warehouse = spp_settings.wip_warehouse
				wo.transfer_material_against = "Work Order"
				wo.bom_no = bom[0].name if not item.bom else item.bom
				wo.append("operations",{
					"operation":"Moulding",
					"bom":bom[0].name if not item.bom else item.bom,
					"workstation":item.work_station,
					"time_in_mins":spp_settings.default_time,
					})
				wo.referenceid = round(time.time() * 1000)
				wo.production_item = bom[0].item
				wo.qty = actual_weight
				wo.planned_start_date = getdate(doc_info.date)
				wo.docstatus = 1
				wo.save(ignore_permissions=True)
				jo_card = update_job_cards(wo.name,actual_weight,doc_info,item,wo.production_item)
				if not jo_card:
					frappe.db.rollback()
					return False
			frappe.db.commit()
			return True
		except Exception as e:
			frappe.db.rollback()
			frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.add_on_work_planning.add_on_work_planning.create_work_order")
			return False

def validate_get_serial_no(self,type__,item = None,job_card = None):
	all_serial_nos = []
	no = 1
	# serial_nos = frappe.db.get_all("Moulding Serial No",filters={"posted_date":getdate(self.date),'shift_no':self.shift_number},fields=['serial_no'])
	serial_nos = frappe.db.get_all("Moulding Serial No",filters={"posted_date":getdate(self.date),'shift_series':self.shift_series},fields=['serial_no'])
	if serial_nos:
		for s_no in serial_nos:
			all_serial_nos.append(s_no.serial_no)
	while True:
		if no not in all_serial_nos:
			if type__ == "Generate":
				return no
			elif type__ == "Save":
				sl_no = frappe.new_doc("Moulding Serial No")
				sl_no.posted_date = getdate(self.date)
				sl_no.compound_code = item.get("item")
				sl_no.serial_no = no
				# sl_no.shift_no = self.shift_number
				sl_no.shift_series = self.shift_series
				sl_no.job_card_reference = job_card.name
				sl_no.insert(ignore_permissions = True)
				return
		no += 1

def update_job_cards(wo,actual_weight,doc_info,item,production_mat_item):
	try:
		job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
		lot_number = get_spp_batch_date(doc_info)
		barcode = generate_barcode(lot_number)
		for job_card in job_cards:
			jc = frappe.get_doc("Job Card",job_card.name)
			jc.append("time_logs",{
				"from_time":now(),
				"completed_qty":flt(actual_weight,3),
				"time_in_mins":1
			})
			for time_log in jc.time_logs:
				time_log.completed_qty =flt(actual_weight,3)
				time_log.time_in_mins = 1
			jc.total_completed_qty =flt(actual_weight,3)
			jc.for_quantity =flt(actual_weight,3)
			jc.batch_code = lot_number
			jc.barcode_image_url = barcode.get('barcode')
			jc.barcode_text = barcode.get('barcode_text')
			# jc.shift_number = doc_info.shift_number
			jc.shift_type = doc_info.shift_type
			jc.shift_supervisor = doc_info.supervisor_id
			asset_id = frappe.db.get_value("Asset",{"item_code":item.get('mould')})
			if asset_id:
				jc.mould_reference = asset_id 
			mould_info = frappe.db.get_all("Mould Specification",filters={"mould_ref":item.get("mould"),"spp_ref":production_mat_item,"mould_status":["in",["ACTIVE","SPARE","DEV"]]},fields=["*"])
			if mould_info:
				jc.no_of_running_cavities = mould_info[0].noof_cavities
				jc.blank_type = mould_info[0].blank_type
				jc.blank_wt = mould_info[0].avg_blank_wtproduct_gms
			press_info = frappe.db.get_all("Press Mould Specification",filters={"mould":item.get("mould"),"press":item.get('work_station')},fields=["*"])
			if press_info:
				jc.bottom_plate_temp = press_info[0].bottom_plate_temp
				jc.top_plate_temp = press_info[0].top_plate_temp
				jc.low_pressure_setting = press_info[0].low_pressure_setting
				jc.high_pressure_setting = press_info[0].high_pressure_setting
			jc.save(ignore_permissions=True)
			""" Update job card reference in child table """
			frappe.db.set_value("Add On Work Plan Item",item.name,{"job_card":jc.name,"lot_number":jc.batch_code})
			""" End """
			validate_get_serial_no(doc_info,"Save",item,job_card)
		frappe.db.commit()
		return True
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.add_on_work_planning.add_on_work_planning.update_job_cards")
		return False

def get_spp_batch_date(doc_info,compound=None):
	serial_no = validate_get_serial_no(doc_info,"Generate")
	month_key = getmonth(str(str(getdate(doc_info.date)).split('-')[1]))
	l = len(str(getdate(doc_info.date)).split('-')[0])
	# compound_key = (str(getdate(doc_info.date)).split('-')[0])[l - 2:] + month_key + str(str(getdate(doc_info.date)).split('-')[2]) + doc_info.shift_number + str("{:02d}".format(serial_no))
	compound_key = (str(getdate(doc_info.date)).split('-')[0])[l - 2:] + month_key + str(str(getdate(doc_info.date)).split('-')[2]) + doc_info.shift_series + str("{:02d}".format(serial_no))
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

def validate_bom(self):
	for x in self.items:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":x.item},as_dict=1)
		if not bom:
			return {"status":False,"message":"BOM not found for item <b>"+x.item+"</b>"}
	return {"status":True}

@frappe.whitelist()
def get_validate_bom(self):
	import json
	self = json.loads(self)
	resp__arry = []
	for x in self.get('items'): 
		x = frappe._dict(x)
		bom__info = {}
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE  B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":x.item},as_dict=1)
		if not bom:
			return {"status":False,"message":"BOM not found for item <b>"+x.item+"</b>"}
		else:
			bom__info[f"{x.item}__default_bom"] = bom[0].name
			""" Get Multi Bom """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if bom__:
				bom__info[f"{x.item}__all_bom"] = bom__
			""" End """
			resp__arry.append(bom__info)
	return {"status":True,"message":resp__arry}

@frappe.whitelist()
def get_work_mould_filters():
	try:
		frappe.response.message = frappe.get_single("SPP Settings")
		frappe.response.status = 'success'
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.add_on_work_planning.add_on_work_planning.get_work_mould_filters")
		frappe.response.status = 'failed'
		
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
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.generate_barcode",message=frappe.get_traceback())		

@frappe.whitelist()
def submit_workplan(docname,doctype):
	try:
		wp = frappe.get_doc(doctype,docname)
		wp.run_method("validate")
		res = wp.run_method("on_submit_value")
		if res:
			frappe.local.response.status = "success"
		else:
			frappe.local.response.status = "failed"	
	except Exception:
		frappe.local.response.status = "failed"
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.submit_workplan",message=frappe.get_traceback())		

@frappe.whitelist()
def validate_supervisor(supervisor):
	spp_settings = frappe.get_single("SPP Settings")
	designation = ""
	if spp_settings and spp_settings.designation_mapping:
		for desc in spp_settings.designation_mapping:
			if desc.spp_process == "Moulding Supervisor":
				if desc.designation:
					designation += f"'{desc.designation}',"
	if designation:
		designation = designation[:-1]
		check_emp = frappe.db.sql(f"""SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s AND designation IN ({designation}) """,{"barcode":supervisor},as_dict=1)
		if check_emp:
			return {"status":"Success","message":check_emp[0]}
		else:
			return {"status":"Failed","message":"Employee not found."}
	else:
		return {"status":"Failed","message":"Designation not mapped in SPP Settings."}
	
@frappe.whitelist()
def get_mould_list(mat):
	try:
		mould_ref_list = frappe.db.get_all("Mould Specification",{"spp_ref":mat},["mould_ref"])
		if mould_ref_list:
			frappe.response.status = "success"
			frappe.response.message = mould_ref_list
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"There is no <b>Mould Specification</b> found for the Mat <b>{mat}</b>..!"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong not able to fetch mould details..!"
		frappe.log_error(title="error in get_mould_list",message=frappe.get_traceback())