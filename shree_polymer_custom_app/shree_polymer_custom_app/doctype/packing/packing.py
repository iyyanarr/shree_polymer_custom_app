# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt, update_progress_bar,format_time, formatdate, getdate, nowdate,now,get_datetime
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_details_by_lot_no,get_parent_lot

class Packing(Document):
	def validate(self):
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.items:
			frappe.throw("Please add some items before save..!")
		# convert_no_into_kgs(self)
		# self.add_total_kgs_nos()

	def on_submit(self):
		b__resp = generate_barcode_serial_no(self)
		if b__resp and b__resp == 'success':
			res = make_repack_entry(self)
			if res.get('status') == "failed":
				self.reload()
				rollback_entries(self)
				frappe.msgprint(res.get('message'))
			if res.get('status') == "success":
				res.get('st_entry').notify_update()
				self.reload()

	def on_cancel(self):
		rollback_entries(self)

	def add_total_kgs_nos(self):
		total_qty_kgs = 0.0
		total_qty_nos = 0.0
		for k in self.items:
			total_qty_kgs = flt(total_qty_kgs + k.qty__kgs,3)
			total_qty_nos = flt(total_qty_nos + k.qty_nos,3)
		self.total_qty_kgs = total_qty_kgs
		self.total_qty_nos = total_qty_nos

def convert_no_into_kgs(self):
	un_uom_items = ""
	total_qty_kgs = 0
	for i__tem in self.items:
		check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":i__tem.product_ref,"uom":"Kg"},fields=['conversion_factor'])
		if check_uom:
			i__tem.qty_kgs = flt(flt(1/check_uom[0].conversion_factor,3) * flt(i__tem.qty_nos,3),3)
			total_qty_kgs += i__tem.qty_kgs
		else:
			un_uom_items += i__tem.product_ref
	self.total_qty_kgs = flt(total_qty_kgs,3)
	if un_uom_items:
		frappe.msgprint(f"The <b>UOM</b> conversion factor not found for the following items:<br><b>{un_uom_items}</b>")

def rollback_entries(self,msg = None):
	try:
		pass  # Add your logic here
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error in try block")
		frappe.msgprint("An error occurred.")
		if self.stock_entry_reference:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(name)s""",{"name":self.stock_entry_reference})
		exe_pc = frappe.get_doc(self.doctype, self.name)
		if exe_pc.docstatus !=2 :
			exe_pc.db_set("docstatus", 0)
		exe_pc.db_set("stock_entry_reference",'')
		if self.packing_serial_no_id:
			frappe.db.sql(f""" DELETE FROM `tabPacking Serial No` WHERE name IN ('{self.packing_serial_no_id}') """)
		frappe.db.commit()
		if msg:
			frappe.msgprint(msg)
		self.reload()
	except Exception:
		self.reload()
		frappe.log_error(title='packing rollback entrie error',message = frappe.get_traceback())
		frappe.msgprint("Something went wrong, not able to rollback..!")

def generate_barcode_serial_no(self):
	try:
		# for item in self.items:
			new_serial_no = 1
			exe_serial_no = frappe.db.get_all("Packing Serial No",{"date":getdate(now())},["serial_no"],order_by="serial_no DESC")
			if exe_serial_no:
				new_serial_no += exe_serial_no[0].serial_no
			new__doc = frappe.new_doc("Packing Serial No")
			new__doc.date = getdate(now())
			new__doc.serial_no = new_serial_no
			new__doc.insert(ignore_permissions = True)
			# frappe.db.set_value("Packing Item",item.name,"packing_serial_no_id",new__doc.name)
			frappe.db.set_value(self.doctype,self.name,"packing_serial_no_id",new__doc.name)
			bar__resp = generate_barcode(''.join(k[2:] if idx == 0 else k for idx,k in enumerate((str(getdate(now())).split('-'))))+'-'+"{:04d}".format(new_serial_no))
			if bar__resp.get('status') == "success":
				# frappe.db.set_value("Packing Item",item.name,"barcode_text",bar__resp.get("barcode_text"))
				# frappe.db.set_value("Packing Item",item.name,"barcode",bar__resp.get("barcode"))
				frappe.db.set_value(self.doctype,self.name,"barcode_text",bar__resp.get("barcode_text"))
				frappe.db.set_value(self.doctype,self.name,"barcode",bar__resp.get("barcode"))
			else:
				rollback_entries(self,bar__resp.get('message'))
				frappe.db.rollback()
				return 'failed'
			frappe.db.commit()	
			return 'success'
		# return 'success'	
	except Exception:
		frappe.db.rollback()
		rollback_entries(self,"Barcode generation failed..!")
		frappe.log_error(title="barcode generation failed", message = frappe.get_traceback())
		return 'failed'

def make_repack_entry(mt_doc):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.unit_2_warehouse:
			frappe.throw("Target warehouse details not found in <b>SPP Settings</p>")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Repack"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.stock_entry_type = "Repack"
		stock_entry.from_warehouse = spp_settings.unit_2_warehouse
		stock_entry.to_warehouse = spp_settings.unit_2_warehouse
		for x in mt_doc.items:
			stock_entry.append("items",{
				"item_code":x.product_ref,
				"s_warehouse":spp_settings.unit_2_warehouse,
				"stock_uom": "Nos",
				"to_uom": "Nos",
				"uom": "Nos",
				"is_finished_item":0,
				"transfer_qty":flt(x.qty_nos,3),
				"use_serial_batch_fields":1,
				"qty":flt(x.qty_nos,3),
				"batch_no":x.batch_no
				})
		stock_entry.append("items",{
			"item_code":mt_doc.item,
			"t_warehouse":spp_settings.unit_2_warehouse,
			"stock_uom": "Nos",
			"to_uom": "Nos",
			"uom": "Nos",
			"is_finished_item":1,
			"transfer_qty":flt(mt_doc.total_qty_nos,3),
			"use_serial_batch_fields":1,
			"qty":flt(mt_doc.total_qty_nos,3),
			# "spp_batch_number":x.spp_batch_no,
			"mix_barcode": frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode_text"),
			"barcode_attach":frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode"),
			"barcode_text":frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode_text"),
			"source_ref_document":mt_doc.doctype,
			"source_ref_id":mt_doc.name
		})
		stock_entry.insert(ignore_permissions=True)
		frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
		frappe.db.commit()
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save(ignore_permissions=True)
		""" Update posting date and time """
		frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.posting_date}' WHERE name = '{st_entry.name}' ")
		""" End """
		return {"status":"success","st_entry":st_entry}
	except Exception as e:
		frappe.db.rollback()
		mt_doc.reload()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.make_repack_entry")
		return {"status":"failed","message":"Something went wrong, Not able to make <b>Stock Entry</b>"}
	
def generate_w_serial_no(item_code,spp_batch_no):
	try:
		serial_no = 1
		serial_nos = frappe.db.get_all("Warming Batch Serial No",filters={"spp_batch_number":spp_batch_no},fields=['serial_no'],order_by="serial_no DESC")
		if serial_nos:
			serial_no = serial_nos[0].serial_no + 1
		sl_no = frappe.new_doc("Warming Batch Serial No")
		sl_no.posting_date = getdate()
		sl_no.compound = item_code
		sl_no.serial_no = serial_no
		sl_no.spp_batch_number = spp_batch_no
		sl_no.insert(ignore_permissions = True)
		return True,'',spp_batch_no+'-'+str(serial_no)
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.generate_w_serial_no")
		return False,"SPP batch no. generation error..!",''

def get_spp_batch_date(item):
	try:
		serial_no = 1
		serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
		if serial_nos:
			serial_no = serial_nos[0].serial_no+1
		sl_no = frappe.new_doc("SPP Batch Serial")
		sl_no.posted_date = getdate()
		sl_no.compound_code = item
		sl_no.serial_no = serial_no
		sl_no.insert(ignore_permissions=True)
		month_key = getmonth(str(str(getdate()).split('-')[1]))
		l = len(str(getdate()).split('-')[0])
		compound_key = (str(getdate()).split('-')[0])[l - 2:]+month_key+str(str(getdate()).split('-')[2])+"X"+str(serial_no)
		return True,'',compound_key
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.get_spp_batch_date")
		return False,"SPP batch no. generation error..!",''

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
	try:
		import code128
		from PIL import Image
		barcode_param = barcode_text = str(compound)
		barcode_image = code128.image(barcode_param, height=120)
		w, h = barcode_image.size
		margin = 5
		new_h = h +(2*margin) 
		new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
		new_image.paste(barcode_image, (0, margin))
		new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=barcode_text), 'PNG')
		barcode = "/files/" + barcode_text + ".png"
		return {"status":"success","barcode":barcode,"barcode_text":barcode_text}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.generate_barcode")
		return {"status":"failed","message":"Something went wrong"}

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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.check_available_stock")
		return {"status":"failed","message":"Something went wrong"}

def check_customer_item(item):
	try:
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabItem` I ON I.name=B.item  WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND I.default_bom=B.name """,{"item_code":item},as_dict=1)
		if bom:
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B INNER JOIN `tabBOM Item` BI ON BI.parent = B.name WHERE BI.item_code=%(bom_item)s AND B.is_Active = 1 """,{"bom_item":item},as_dict=1)
			items = []
			for b_m in bom__:
				check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":b_m.item,"uom":"Kg"},fields=['conversion_factor'])
				if check_uom:
					items.append({"item_code":b_m.item,"_1kg_eq_nos":check_uom[0].conversion_factor})
				else:
					return {"status":"failed","message":"Please define UOM for Kgs for the item <b>"+b_m.item+"</b>"}
			return {"status":"success","bom":bom[0].name,"items":items}
			# return {"status":"success","bom":bom[0].name,"items":[x.item for x in bom__]}
		else:
			return {"status":"failed","message":"No BOM found associated with the item <b>"+item+"</b>"}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.check_customer_item")

@frappe.whitelist()
def validate_lot_barcode(batch_no,item = None):
	try:
		# Find manufacturing stock entry with 'F' prefixed batch number
		modified_batch_no = 'F' + batch_no
		
		# Updated query to find stock entries containing the specific batch
		stock_entry = frappe.db.sql(f"""
			SELECT DISTINCT SE.name
			FROM `tabStock Entry` SE
			INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
			WHERE SE.stock_entry_type = 'Manufacture' 
			AND SE.docstatus = 1
			AND (SED.batch_no = '{batch_no}' OR SED.batch_no = '{modified_batch_no}')
			LIMIT 1
		""", as_dict=1)
		
		if stock_entry:
			stock_entry_ref = stock_entry[0].name
			
			# Add debug logging to diagnose the issue
			frappe.log_error(
				message=f"Validating lot: {batch_no}, Modified batch: {modified_batch_no}, Stock Entry: {stock_entry_ref}",
				title="Batch Validation Debug"
			)
			
			# Check if any Stock Entry Detail exists with the batch_no
			batch_exists_check = frappe.db.sql(f"""
				SELECT SED.name, SED.batch_no, SED.t_warehouse
				FROM `tabStock Entry Detail` SED 
				INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
				WHERE SE.name='{stock_entry_ref}' AND SE.stock_entry_type='Manufacture'
			""", as_dict=1)
			
			# Log all available batch numbers in this stock entry for debugging
			if batch_exists_check:
				batches_in_entry = [b.get('batch_no') for b in batch_exists_check]
				frappe.log_error(
					message=f"Available batches in stock entry: {batches_in_entry}",
					title="Batch Numbers in Stock Entry"
				)
			
			# Updated to get the actual warehouse from the stock entry detail
			product_details = frappe.db.sql(f""" SELECT SED.t_warehouse as from_warehouse, SED.item_code, SED.batch_no, SED.spp_batch_number 
												FROM `tabStock Entry Detail` SED 
												INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
												WHERE SE.name='{stock_entry_ref}' AND SE.stock_entry_type='Manufacture' 
												AND SED.is_finished_item = 1
												AND (SED.batch_no='{modified_batch_no}' OR SED.batch_no='{batch_no}') """, as_dict=1)
			
			if product_details:
				stock_status = check_available_stock(product_details[0].get("from_warehouse"), product_details[0].get("item_code"), product_details[0].get("batch_no",""))
				if stock_status.get('status') == "success":
					product_details[0].qty_from_item_batch = stock_status.get('qty')
					cust_item = check_customer_item(product_details[0].get("item_code"))
					if cust_item.get('status') == 'success':
						product_details[0]['items'] = cust_item.get('items')
						packing__type_resp = attach_packing_type()
						if packing__type_resp.get('status') == 'success':
							product_details[0]['packing_types'] = packing__type_resp.get('message')
							if item:
								items_ = [x.get('item_code') for x in product_details[0]['items']]
								if item in items_:
									frappe.response.status = "success"
									frappe.response.message = product_details[0]
								else:
									frappe.response.status = 'failed'
									frappe.response.message = f"The Customer item - <b>{item}</b> not matched with any of the scanned lot - <b>{batch_no}</b> customer items..!"	
							else:
								frappe.response.status = "success"
								frappe.response.message = product_details[0]
						else:
							frappe.response.status = packing__type_resp.get('status')
							frappe.response.message = packing__type_resp.get('message')	
					else:
						frappe.response.status = cust_item.get('status')
						frappe.response.message = cust_item.get('message')
				else:
					frappe.response.status = stock_status.get('status')
					frappe.response.message = stock_status.get('message')
			else:
				# More detailed error message showing the searched batch numbers
				frappe.log_error(
					message=f"No Stock Entry details found for batch: {batch_no} or modified batch: {modified_batch_no}",
					title="Batch Not Found in Stock Entry Detail"
				)
				frappe.response.status = 'failed'
				frappe.response.message = f"There is no <b>Stock Entry Detail</b> found for the scanned lot <b>{batch_no}</b>. \
					Searched for batch numbers: {batch_no} and {modified_batch_no}"
		else:
			frappe.log_error(
				message=f"No Manufacturing Stock Entry found for batch: {batch_no} or modified batch: {modified_batch_no}",
				title="No Stock Entry Found for Batch"
			)
			frappe.response.status = 'failed'
			frappe.response.message = f"There is no <b>Manufacturing Stock Entry</b> found for the lot <b>{batch_no}</b>"	
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.validate_lot_barcode")

def attach_packing_type():
	spp_settings = frappe.get_single("SPP Settings")
	if spp_settings.packing_type:
		return {"status":"success","message":spp_settings.packing_type.split(',')}
	else:
		return {"status":"failed","message":"Packing type is not found in <b>SPP Settings</b>"}

@frappe.whitelist()
def get_customer_item_group():
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.packing_item_group:
			frappe.response.status = "success"
			frappe.response.message = spp_settings.packing_item_group
		else:
			frappe.response.status = "failed"
			frappe.response.message = "Packing item group not mapped in <b>SPP Settings</b>"	
	except Exception:
		frappe.log_error(title = "shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.get_customer_item_group",message = frappe.get_traceback())
		frappe.response.status = "failed"
		frappe.response.message = "Somthing went wrong, not able to fetch <b>Customer item group</b>..!"

""" Backup """


# def rollback_entries(self,msg = None):
# 	try:
# 		if self.stock_entry_reference:
# 			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
# 			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  name=%(name)s""",{"name":self.stock_entry_reference})
# 		exe_pc = frappe.get_doc(self.doctype, self.name)
# 		if exe_pc.docstatus !=2 :
# 			exe_pc.db_set("docstatus", 0)
# 		exe_pc.db_set("stock_entry_reference",'')
# 		# serial_ids = ""
# 		# for each_item in self.items:
# 		# 	if each_item.packing_serial_no_id:
# 		# 		serial_ids += f"'{each_item.packing_serial_no_id}',"
# 		# 		each_item.packing_serial_no_id = ''
# 		# if serial_ids:
# 		# 	serial_ids = serial_ids[:-1]
# 		# 	frappe.db.sql(f""" DELETE FROM `tabPacking Serial No` WHERE name IN ({serial_ids}) """)
# 		if self.packing_serial_no_id:
# 			frappe.db.sql(f""" DELETE FROM `tabPacking Serial No` WHERE name IN ('{self.packing_serial_no_id}') """)
# 		frappe.db.commit()
# 		if msg:
# 			frappe.msgprint(msg)
# 		self.reload()
# 	except Exception:
# 		self.reload()
# 		frappe.log_error(title='packing rollback entrie error',message = frappe.get_traceback())
# 		frappe.msgprint("Something went wrong, not able to rollback..!")


# def make_repack_entry(mt_doc):
# 	try:
# 		spp_settings = frappe.get_single("SPP Settings")
# 		if not spp_settings.unit_2_warehouse:
# 			frappe.throw("Target warehouse details not found in <b>SPP Settings</p>")
# 		stock_entry = frappe.new_doc("Stock Entry")
# 		stock_entry.purpose = "Repack"
# 		stock_entry.company = "SPP"
# 		stock_entry.naming_series = "MAT-STE-.YYYY.-"
# 		stock_entry.stock_entry_type = "Repack"
# 		stock_entry.from_warehouse = spp_settings.unit_2_warehouse
# 		stock_entry.to_warehouse = spp_settings.unit_2_warehouse
# 		for x in mt_doc.items:
# 			stock_entry.append("items",{
# 				"item_code":x.product_ref,
# 				"s_warehouse":spp_settings.unit_2_warehouse,
# 				"stock_uom": "Nos",
# 				"to_uom": "Nos",
# 				"uom": "Nos",
# 				"is_finished_item":0,
# 				"transfer_qty":flt(x.qty_nos,3),
# 				"qty":flt(x.qty_nos,3),
# 				"batch_no":x.batch_no
# 				})
# 		stock_entry.append("items",{
# 			"item_code":mt_doc.item,
# 			"t_warehouse":spp_settings.unit_2_warehouse,
# 			"stock_uom": "Nos",
# 			"to_uom": "Nos",
# 			"uom": "Nos",
# 			"is_finished_item":1,
# 			"transfer_qty":flt(mt_doc.total_qty_nos,3),
# 			"qty":flt(mt_doc.total_qty_nos,3),
# 			# "spp_batch_number":x.spp_batch_no,
# 			"mix_barcode": frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode_text"),
# 			"barcode_attach":frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode"),
# 			"barcode_text":frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode_text"),
# 			"source_ref_document":mt_doc.doctype,
# 			"source_ref_id":mt_doc.name
# 		})
# 		# for x in mt_doc.items:
# 		# 	# status,message,sl_no = get_spp_batch_date(x.product_ref)
# 		# 	# status,message,sl_no = generate_w_serial_no(x.product_ref,x.spp_batch_no)
# 		# 	# if status:
# 		# 		# bar_dict = generate_barcode("F_"+sl_no)
# 		# 		# bar_dict = generate_barcode(x.spp_batch_no)
# 		# 		# if bar_dict.get('status') == "success":
# 		# 			stock_entry.append("items",{
# 		# 				"item_code":x.item,
# 		# 				"t_warehouse":spp_settings.unit_2_warehouse,
# 		# 				"stock_uom": "Nos",
# 		# 				"to_uom": "Nos",
# 		# 				"uom": "Nos",
# 		# 				"is_finished_item":1,
# 		# 				"transfer_qty":flt(x.qty_nos,3),
# 		# 				"qty":flt(x.qty_nos,3),
# 		# 				# "spp_batch_number":sl_no,
# 		# 				"spp_batch_number":x.spp_batch_no,
# 		# 				# "batch_no":x.batch_no,
# 		# 				# "mix_barcode": bar_dict.get("barcode_text"),
# 		# 				# "barcode_attach":bar_dict.get("barcode"),
# 		# 				# "barcode_text":bar_dict.get("barcode_text"),
# 		# 				# "mix_barcode": frappe.db.get_value("Packing Item",x.name,"barcode_text"),
# 		# 				# "barcode_attach":frappe.db.get_value("Packing Item",x.name,"barcode"),
# 		# 				# "barcode_text":frappe.db.get_value("Packing Item",x.name,"barcode_text"),
# 		# 				"mix_barcode": frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode_text"),
# 		# 				"barcode_attach":frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode"),
# 		# 				"barcode_text":frappe.db.get_value(mt_doc.doctype,mt_doc.name,"barcode_text"),
# 		# 				"source_ref_document":mt_doc.doctype,
# 		# 				"source_ref_id":mt_doc.name
# 		# 			})
# 				# else:
# 				# 	return {"status":"failed","message":bar_dict.get('message')}	
# 			# else:
# 			# 	return {"status":"failed","message":message}
# 		frappe.log_error(title="ss",message=stock_entry.as_dict())
# 		stock_entry.insert(ignore_permissions=True)
# 		frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
# 		frappe.db.commit()
# 		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
# 		st_entry.docstatus=1
# 		st_entry.save(ignore_permissions=True)
# 		""" Update posting date and time """
# 		frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.posting_date}' WHERE name = '{st_entry.name}' ")
# 		""" End """
# 		return {"status":"success","st_entry":st_entry}
# 	except Exception as e:
# 		frappe.db.rollback()
# 		mt_doc.reload()
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.make_repack_entry")
# 		return {"status":"failed","message":"Something went wrong, Not able to make <b>Stock Entry</b>"}


# @frappe.whitelist()
# def validate_lot_barcode(batch_no):
# 	try:
# 		""" Validate job card """
# 		check_lot_issue = frappe.db.sql(""" SELECT JB.name FROM `tabJob Card` JB WHERE JB.batch_code=%(lot_no)s AND operation="Deflashing" """,{"lot_no":batch_no},as_dict=1)
# 		if not check_lot_issue:
# 			frappe.response.status = 'failed'
# 			frappe.response.message = f"Job Card not found for the scanned lot <b>{batch_no}</b>"
# 		else:
# 			check_exist = frappe.db.get_all("Inspection Entry",filters={"docstatus":1,"lot_no":batch_no,"inspection_type":"Incoming Inspection"})
# 			if check_exist:
# 				rept_entry = frappe.db.get_all("Deflashing Receipt Entry",{"lot_number":batch_no,"docstatus":1},["stock_entry_reference"])
# 				if rept_entry:
# 					if not rept_entry[0].stock_entry_reference:
# 						frappe.response.status = 'failed'
# 						frappe.response.message = f"Stock Entry Reference not found in <b>Deflashing Receipt Entry</b> for the lot <b>{batch_no}</b>"
# 					else:
# 						product_details = frappe.db.sql(f""" SELECT  SED.t_warehouse as from_warehouse,SED.item_code,SED.batch_no,SED.spp_batch_number FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name=SED.parent
# 															INNER JOIN `tabJob Card` JC ON JC.work_order=SE.work_order LEFT JOIN `tabJob Card Time Log` LG ON LG.parent = JC.name 
# 															LEFT JOIN `tabEmployee` E ON LG.employee = E.name WHERE SE.name='{rept_entry[0].stock_entry_reference}' AND SED.deflash_receipt_reference='{batch_no}' """,as_dict=1)
# 						if product_details:
# 							stock_status = check_available_stock(product_details[0].get("from_warehouse"),product_details[0].get("item_code"),product_details[0].get("batch_no",""))
# 							if stock_status.get('status') == "success":
# 								product_details[0].qty_from_item_batch = stock_status.get('qty')
# 								frappe.response.status = "success"
# 								frappe.response.message = product_details[0]
# 							else:
# 								frappe.response.status = stock_status.get('status')
# 								frappe.response.message = stock_status.get('message')
# 						else:
# 							frappe.response.status = 'failed'
# 							frappe.response.message = f"There is no <b>Stock Entry</b> found for the scanned lot <b>{batch_no}</b>"
# 				else:
# 					frappe.response.status = 'failed'
# 					frappe.response.message = f"There is no <b>Deflashing Receipt Entry</b> found for the lot <b>{batch_no}</b>"
# 			else:
# 				frappe.response.status = 'failed'
# 				frappe.response.message = f'There is no <b>Incoming Inspection Entry</b> found for the lot <b>{batch_no}</b>'	
# 	except Exception:
# 		frappe.response.status = "failed"
# 		frappe.response.message = "Something went wrong"
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.validate_lot_barcode")
