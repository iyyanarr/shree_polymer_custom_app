# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now


class BlankBinInwardEntry(Document):
	def validate(self):
		if self.items:
			for item in self.items:
				if not item.bin_gross_weight:
					frappe.throw(f"Enter the gross weight for the item {item.compound_code} in row {item.idx}.")
		else:
			frappe.throw("Please add items before save.")

	def on_submit(self):
		try:
			spp_settings = frappe.get_single("SPP Settings")
			if self.move_to_cut_bit_warehouse:
				make_stock_entry(self)
			else:
				for item in self.items:
					asset_movement(spp_settings,item,"update")
			self.reload()
		except Exception:
			frappe.log_error(title="Blank bin inward entry error", message = frappe.get_traceback())
			rollback_entries(self,spp_settings)

def rollback_entries(self,spp_settings):
	for item in self.items:
		if self.move_to_cut_bit_warehouse:
			frappe.db.sql(""" UPDATE `tabItem Bin Mapping` SET is_retired=0,qty=%(qty)s WHERE name =%(name)s """,{"qty":item.get('available_qty'),"name":item.get('ibm_id')})
		else:
			frappe.db.sql(""" UPDATE `tabItem Bin Mapping` SET qty=%(qty)s WHERE name =%(name)s """,{"qty":item.get('available_qty'),"name":item.get('ibm_id')})
		last_mov = frappe.db.sql(f" SELECT AMI.target_location FROM `tabAsset Movement` AM INNER JOIN `tabAsset Movement Item` AMI ON AM.name = AMI.parent WHERE AMI.asset = '{item.get('bin_code')}' ORDER BY AMI.creation DESC LIMIT 1 ",as_dict = 1)
		if last_mov:
			if not last_mov[0].target_location == spp_settings.to_location:
				make_asset_movement(spp_settings,item,m_type="from_to")
	
	refs = frappe.db.get_value("Blank Bin Inward Entry",self.name,"stock_entry_reference")
	if refs:
		for k in refs.split(","):
			frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE name = '{k}' ")
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{k}' ")
	doc = frappe.get_doc(self.doctype,self.name)
	doc.db_set("docstatus",0)
	frappe.db.commit()
	frappe.msgprint("Something went wrong..!")
	self.reload()

def asset_movement(spp_settings,c__bin,update_type):
	if update_type == "update":
		frappe.db.sql(""" UPDATE `tabItem Bin Mapping` SET qty=%(qty)s WHERE name =%(name)s """,{"qty":c__bin.get('bin_net_weight'),"name":c__bin.get('ibm_id')})
	elif update_type == "release":
		frappe.db.sql(""" UPDATE `tabItem Bin Mapping` SET is_retired=1,qty=%(qty)s WHERE name =%(name)s """,{"qty":c__bin.get('bin_net_weight'),"name":c__bin.get('ibm_id')})
	last_mov = frappe.db.sql(f" SELECT AMI.target_location FROM `tabAsset Movement` AM INNER JOIN `tabAsset Movement Item` AMI ON AM.name = AMI.parent WHERE AMI.asset = '{c__bin.get('bin_code')}' ORDER BY AMI.creation DESC LIMIT 1 ",as_dict = 1)
	if last_mov:
		if not last_mov[0].target_location == spp_settings.from_location:
			make_asset_movement(spp_settings,c__bin,"to_from")
	else:
		make_asset_movement(spp_settings,c__bin,"to_from")

def make_asset_movement(spp_settings,x,m_type):
	asset__mov = frappe.new_doc("Asset Movement")
	asset__mov.company = "SPP"
	asset__mov.transaction_date = now()
	asset__mov.purpose = "Transfer"
	if m_type == "to_from":
		asset__mov.append("assets",{
			"asset":x.get('bin_code'),
			"source_location":spp_settings.to_location,
			"target_location":spp_settings.from_location,
		})
	else:
		asset__mov.append("assets",{
			"asset":x.get('bin_code'),
			"source_location":spp_settings.from_location,
			"target_location":spp_settings.to_location,
		})
	asset__mov.insert(ignore_permissions=True)
	ass__doc = frappe.get_doc("Asset Movement",asset__mov.name)
	ass__doc.docstatus = 1
	ass__doc.save(ignore_permissions=True)

def update_stock_ref(doc_id,stock_id):
	store__val = ""
	exe_entries = frappe.db.get_value("Blank Bin Inward Entry",doc_id,'stock_entry_reference')
	if exe_entries:
		exe_entries += "," + stock_id
		store__val += exe_entries
	else:
		store__val = stock_id
	frappe.db.set_value("Blank Bin Inward Entry",doc_id,'stock_entry_reference',store__val)
	frappe.db.commit()

def make_stock_entry(self):
	try:
		for x in self.items:
			spp_settings = frappe.get_single("SPP Settings")
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Repack"
			stock_entry.company = "SPP"
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			stock_entry.stock_entry_type = "Repack"
			stock_entry.from_warehouse = spp_settings.default_sheeting_warehouse
			stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse
			stock_entry.append("items",{
				"item_code":x.get("compound_code"),
				"s_warehouse":spp_settings.default_sheeting_warehouse,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"transfer_qty":x.get("bin_net_weight"),
				"qty":x.get("bin_net_weight"),
				"use_serial_batch_fields": 1,
				"batch_no":x.get("batch_no"),
				})
			stock_entry.append("items",{
				"item_code":x.get("compound_code"),
				"t_warehouse":spp_settings.default_cut_bit_warehouse,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":1,
				"use_serial_batch_fields": 1,
				"transfer_qty":x.get("bin_net_weight"),
				"batch_no":x.cut_bit_batch,
				"qty":x.get("bin_net_weight"),
				"is_compound":1,
				"source_ref_document":self.doctype,
				"source_ref_id":self.name })
			asset_movement(spp_settings,x,"release")
			stock_entry.insert(ignore_permissions = True)
			update_stock_ref(self.name,stock_entry.name)
			sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
			sub_entry.docstatus = 1
			sub_entry.save(ignore_permissions=True)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.make_stock_entry")
		
@frappe.whitelist()
def validate_bin_barcode(bar_code):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.default_sheeting_warehouse:
			bl_bin = frappe.db.sql(""" SELECT A.bin_weight,A.name,A.asset_name,IBM.compound as item,
											IBM.is_retired,IBM.qty,IBM.spp_batch_number,IBM.name item_bin_mapping_id
												FROM `tabAsset` A INNER JOIN `tabItem Bin Mapping` IBM ON A.name=IBM.blanking__bin 
									WHERE A.barcode_text=%(barcode_text)s order by IBM.creation desc""",{"barcode_text":bar_code},as_dict=1)
			if bl_bin:
				if bl_bin[0].is_retired == 1:
					frappe.response.status = 'failed'
					frappe.response.message = "No item found in Scanned Bin."
				else:
					""" Check Bom mapped and get compound """
					stock_status = check_default_bom(bl_bin[0].item,bl_bin[0])
					if stock_status.get('status') == "success":
						istb_query = """ SELECT 
											I.batch_no,I.stock_uom as uom,I.qty,SD.spp_batch_number
											FROM `tabItem Batch Stock Balance` I
												INNER JOIN `tabBatch` B ON B.name = I.batch_no 
												INNER JOIN  `tabStock Entry Detail` SD ON SD.batch_no = B.name
												INNER JOIN `tabStock Entry` SE ON SE.name = SD.parent 
											WHERE SE.stock_entry_type="Repack" 
												AND SD.spp_batch_number = '{spp_b_no}' AND SD.t_warehouse = '{t_warehouse}'
												AND I.warehouse ='{t_warehouse}' AND B.expiry_date >= curdate() 
											ORDER BY SE.creation DESC LIMIT 1 """.format(spp_b_no = bl_bin[0].spp_batch_number,t_warehouse=spp_settings.default_sheeting_warehouse)
						istb_entry = frappe.db.sql(istb_query,as_dict=1)
						if istb_entry:
							bl_bin[0].spp_batch_number = istb_entry[0].spp_batch_number
							bl_bin[0].batch_no = istb_entry[0].batch_no
							if bl_bin[0].qty > istb_entry[0].qty:
								frappe.response.message = f'The bin qty - <b>{bl_bin[0].qty}</b> is greater than the batch ({istb_entry[0].batch_no}) qty - <b>{istb_entry[0].qty}</b>'
								frappe.response.status =  "failed"
							else:
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
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Default Sheeting warehouse not mapped in <b>SPP Settings</b>..!"
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.validate_bin_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."
	
def check_default_bom(item,bl_entry):
	try:
		bom = validate_bom(item)
		if bom.get("status"):
			bl_entry.compound_code = bom.get("bom").item
			return {"status":"success","message":bl_entry,"bom":bom.get("bom").name}
		else:
			return {"status":"failed","message":bom.get("message")}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.check_stock_entry")

def validate_bom(item_code):
	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE B.item=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item_code},as_dict=1)
	if bom:
		""" Multi Bom Validation """
		bom__ = frappe.db.sql(""" SELECT B.name FROM `tabBOM` B WHERE B.item=%(item_code)s AND B.is_active=1 """,{"item_code":item_code},as_dict=1)
		if len(bom__) > 1:
			return {"status":False,"message":f"Multiple BOM's found Item - <b>{item_code}</b>"}
		""" End """
		return {"status":True,"bom":bom[0]}
	return {"status":False,"message":f"BOM is not found."}

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
	
def generate_barcode(compound):
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

@frappe.whitelist()
def validate_cutbit_batch_barcode(bar_code,compound):
	try:
		resp_ = frappe.db.sql(f""" SELECT name,item FROM `tabBatch` WHERE barcode_text = '{bar_code}' """, as_dict = 1)
		if resp_:
			if resp_[0].item == compound:
				frappe.response.status = "success"
				frappe.response.message = resp_[0].name
			else:
				frappe.response.status = "failed"
				frappe.response.message = f"The Compound <b>{compound}</b> not matched with batch item <b>{resp_[0].item}</b>..!"
		else:
			frappe.response.status = "failed"
			frappe.response.status = "There is no <b>Cut Bit Batch</b> found for the scanned barcode..!"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.status = "Something went wrong not able to fetch batch details..!"
		frappe.log_error(title="Error in scan cut bit batch",message = frappe.get_traceback())








# def make_stock_entry(self):
# 	try:
# 		spp_settings = frappe.get_single("SPP Settings")
# 		stock_entry = frappe.new_doc("Stock Entry")
# 		stock_entry.purpose = "Repack"
# 		stock_entry.company = "SPP"
# 		stock_entry.naming_series = "MAT-STE-.YYYY.-"
# 		stock_entry.stock_entry_type = "Repack"
# 		stock_entry.from_warehouse = spp_settings.default_sheeting_warehouse
# 		stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse
# 		for x in self.items:
# 			# d_spp_batch_no = get_spp_batch_date(x.get("compound_code"))
# 			stock_entry.append("items",{
# 				"item_code":x.get("compound_code"),
# 				"s_warehouse":spp_settings.default_sheeting_warehouse,
# 				"stock_uom": "Kg",
# 				"uom": "Kg",
# 				"conversion_factor_uom":1,
# 				"transfer_qty":x.get("bin_net_weight"),
# 				"qty":x.get("bin_net_weight"),
# 				"batch_no":x.get("batch_no"),
# 				})
# 			stock_entry.append("items",{
# 				"item_code":x.get("compound_code"),
# 				"t_warehouse":spp_settings.default_cut_bit_warehouse,
# 				"stock_uom": "Kg",
# 				"uom": "Kg",
# 				"conversion_factor_uom":1,
# 				"is_finished_item":1,
# 				"transfer_qty":x.get("bin_net_weight"),
# 				"batch_no":x.cut_bit_batch,
# 				"qty":x.get("bin_net_weight"),
# 				# "spp_batch_number":d_spp_batch_no,
# 				"is_compound":1,
# 				# "barcode_text":"CB_"+d_spp_batch_no,
# 				# "mix_barcode":"CB_"+d_spp_batch_no,
# 				"source_ref_document":self.doctype,
# 				"source_ref_id":self.name })
# 			asset_movement(spp_settings,x,"release")
# 		stock_entry.insert(ignore_permissions = True)
# 		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
# 		frappe.db.commit()
# 		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
# 		sub_entry.docstatus=1
# 		sub_entry.save(ignore_permissions=True)
# 		# for x in self.items:
# 		# 	serial_no = 1
# 		# 	serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
# 		# 	if serial_nos:
# 		# 		serial_no = serial_nos[0].serial_no+1
# 		# 	sl_no = frappe.new_doc("SPP Batch Serial")
# 		# 	sl_no.posted_date = getdate()
# 		# 	sl_no.compound_code = x.get("compound_code")
# 		# 	sl_no.serial_no = serial_no
# 		# 	sl_no.insert(ignore_permissions = True)
# 	except Exception as e:
# 		frappe.db.rollback()
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.make_stock_entry")
		




# def make_stock_entry(self):
# 	try:
# 		spp_settings = frappe.get_single("SPP Settings")
# 		stock_entry = frappe.new_doc("Stock Entry")
# 		stock_entry.purpose = "Repack" if self.move_to_cut_bit_warehouse else "Material Transfer"
# 		stock_entry.company = "SPP"
# 		stock_entry.naming_series = "MAT-STE-.YYYY.-"
# 		stock_entry.stock_entry_type = "Repack" if self.move_to_cut_bit_warehouse else "Material Transfer"
# 		stock_entry.from_warehouse = spp_settings.unit_2_warehouse
# 		stock_entry.to_warehouse = spp_settings.target_warehouse if not self.move_to_cut_bit_warehouse else spp_settings.default_cut_bit_warehouse
# 		for x in self.items:
# 			from shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry import get_spp_batch_date
# 			d_spp_batch_no = get_spp_batch_date(x.get("compound_code"))
# 			stock_entry.append("items",{
# 				"item_code":x.get("item"),
# 				"s_warehouse":spp_settings.unit_2_warehouse,
# 				"stock_uom": "Kg",
# 				"uom": "Kg",
# 				"conversion_factor_uom":1,
# 				"transfer_qty":x.get("bin_net_weight"),
# 				"qty":x.get("bin_net_weight"),
# 				"batch_no":x.get("batch_no"),
# 				})
# 			bcode_resp = generate_barcode("C_"+d_spp_batch_no)
# 			if self.move_to_cut_bit_warehouse == 0:
# 				stock_entry.append("items",{
# 					"item_code":x.get("item"),
# 					"t_warehouse":spp_settings.default_blanking_warehouse,
# 					"stock_uom": "Kg",
# 					"uom": "Kg",
# 					"conversion_factor_uom":1,
# 					"is_finished_item":1,
# 					"transfer_qty":x.get("bin_net_weight"),
# 					"qty":x.get("bin_net_weight"),
# 					"batch_no":x.get("batch_no"),
# 					"spp_batch_number":x.get("spp_batch_number"),
# 					"barcode_text":x.get("item")+"_"+x.get("spp_batch_number"),
# 					"mix_barcode":bcode_resp.get("barcode_text"),
# 					"source_ref_document":self.doctype,
# 					"source_ref_id":self.name
# 					})
# 			else:
# 				r_batchno = ""
# 				ct_batch = "Cutbit_"+x.get("compound_code")
# 				cb_batch = frappe.db.get_all("Batch",filters={"batch_id":ct_batch})
# 				if cb_batch:
# 					r_batchno = "Cutbit_"+x.get("compound_code")
# 				stock_entry.append("items",{
# 				"item_code":x.get("compound_code"),
# 				"t_warehouse":spp_settings.target_warehouse if not self.move_to_cut_bit_warehouse else spp_settings.default_cut_bit_warehouse,
# 				"stock_uom": "Kg",
# 				"uom": "Kg",
# 				"conversion_factor_uom":1,
# 				"is_finished_item":1,
# 				"transfer_qty":x.get("bin_net_weight"),
# 				"batch_no":r_batchno,
# 				"qty":x.get("bin_net_weight"),
# 				"spp_batch_number":d_spp_batch_no,
# 				"is_compound":1,
# 				"barcode_text":"CB_"+x.get("compound_code"),
# 				"mix_barcode":x.get("compound_code")+"_"+d_spp_batch_no if not self.move_to_cut_bit_warehouse else "CB_"+x.get("compound_code"),
# 				"source_ref_document":self.doctype,
# 				"source_ref_id":self.name
# 				})
# 		stock_entry.insert()
# 		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
# 		sub_entry.docstatus=1
# 		sub_entry.save(ignore_permissions=True)
# 		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
# 		frappe.db.commit()
# 		for x in self.items:
# 			serial_no = 1
# 			serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
# 			if serial_nos:
# 				serial_no = serial_nos[0].serial_no+1
# 			sl_no = frappe.new_doc("SPP Batch Serial")
# 			sl_no.posted_date = getdate()
# 			sl_no.compound_code = x.get("compound_code")
# 			sl_no.serial_no = serial_no
# 			sl_no.insert()
# 	except Exception as e:
# 		frappe.db.rollback()
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.make_stock_entry")
		