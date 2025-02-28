# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt
import json
import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import (cint,date_diff,flt,get_datetime,get_link_to_form,getdate,nowdate,time_diff_in_hours,touch_file,add_to_date,now)
import  os

def check_enqueue():
	spp_settings = frappe.get_single("SPP Settings")
	if spp_settings.get('enable_enqueue'):
		return True
	else:
		return False

def verify_enqueue_and_alert(doc,method):
	if not check_enqueue() and doc.doctype != "SPP Settings":
		frappe.msgprint(f""" The <b>Enqueue Job</b> for updating <b>Stock Details</b> was <b>Disabled</b>.<br>
						  To enable this please contact <b>Administrator</b>.<br>
						  So that the <b>Stock</b> Of the Materials can updating properly. """)


def config_and_enqueue_job(doc,batch_info = None):
	frappe.enqueue(get_batch_info_update_qty,queue = 'short',doc = doc,batch_info = batch_info)

@frappe.whitelist()
def on_item_update(doc,method):
	if check_enqueue():
		config_and_enqueue_job(doc)
	
def on_batch_trash(doc,method):
	if check_enqueue():
		if doc.item:
			item_doc = frappe._dict({'name':doc.item})
			config_and_enqueue_job(item_doc,doc)

@frappe.whitelist()
def on_batch_update(doc,method):
	if doc.name.startswith("Cutbit_"):
		generate_batch_barcode(doc)

@frappe.whitelist()
def on_sle_update(doc, method):
    try:
        frappe.logger().info("\n=== Starting SLE Update ===")
        frappe.logger().info(f"Document: {doc.as_dict() if hasattr(doc, 'as_dict') else str(doc)}")
        frappe.logger().info(f"Method: {method}")

        # Check if the enqueue function is valid
        try:
            is_enqueued = check_enqueue()
            frappe.logger().info(f"Check enqueue result: {is_enqueued}")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error during enqueue check in on_sle_update")
            frappe.logger().error(f"Failed to check enqueue. Error: {str(e)}")
            raise frappe.ValidationError("Error during enqueue check.")

        if is_enqueued:
            if doc.item_code and doc.serial_and_batch_bundle:
                # Fetch the Serial and Batch Bundle document
                try:
                    batch_bundle = frappe.get_doc("Serial and Batch Bundle", doc.serial_and_batch_bundle)
                    frappe.logger().info(f"Fetched Serial and Batch Bundle: {batch_bundle.name}")
                    
                    # Process each batch entry
                    for entry in batch_bundle.entries:
                        if entry.batch_no:
                            update_item_batch_qty(doc.item_code, entry.batch_no, doc.stock_uom)
                            frappe.logger().info(f"Successfully processed batch: {entry.batch_no} for item: {doc.item_code}")
                        else:
                            frappe.log_error("Batch number missing in batch bundle entry", "Missing Batch Number")
                            frappe.logger().error(f"Entry with missing batch_no: {entry}")
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), "Error fetching or processing Serial and Batch Bundle")
                    frappe.logger().error(f"Error in fetching or processing Serial and Batch Bundle. Details: {str(e)}")
                    raise frappe.ValidationError("Error in processing Serial and Batch Bundle.")
            else:
                frappe.log_error("Missing required fields in SLE update", "Missing Fields in SLE Update")
                frappe.logger().error(
                    f"Missing required fields: "
                    f"Item Code present: {bool(doc.item_code)}, "
                    f"Serial and Batch Bundle present: {bool(doc.serial_and_batch_bundle)}"
                )
        else:
            frappe.log_error("Enqueue check failed - skipping update", "Skipping SLE Update")
            frappe.logger().info("Enqueue check failed - skipping update")
    except Exception as e:
        frappe.logger().error(f"Error in on_sle_update: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "on_sle_update error")



def update_item_batch_qty(item_code, batch_no, stock_uom):
    try:
        from erpnext.stock.doctype.batch.batch import get_batch_qty

        # Fetch batch quantities
        batch_qtys = get_batch_qty(batch_no=batch_no)
        frappe.logger().info(f"Retrieved Batch Quantity for {batch_no}: {batch_qtys}")

        if batch_qtys:
            for b in batch_qtys:
                if b.get("qty") != 0:
                    # Check if entry exists
                    check_exist = frappe.db.get_all(
                        "Item Batch Stock Balance",
                        filters={"item_code": item_code, "batch_no": batch_no, "warehouse": b.get("warehouse")},
                        fields=["name"]
                    )
                    frappe.logger().info(f"Existence check for {item_code} - {batch_no}: {check_exist}")

                    if check_exist:
                        for x in check_exist:
                            frappe.db.set_value("Item Batch Stock Balance", x.name, "qty", b.get("qty"))
                            frappe.logger().info(f"Updated existing Item Batch Stock Balance for {x.name}")
                    else:
                        # Create a new Item Batch Stock Balance entry
                        item_name = frappe.db.get_value("Item", item_code, 'item_name')
                        new_doc = frappe.new_doc("Item Batch Stock Balance")
                        new_doc.item_code = item_code
                        new_doc.item_name = item_name
                        new_doc.description = f"<div> <p>{item_code} - {item_name}</p></div>"
                        new_doc.warehouse = b.get("warehouse")
                        new_doc.qty = b.get("qty")
                        new_doc.stock_uom = stock_uom
                        new_doc.batch_no = batch_no
                        new_doc.insert(ignore_permissions=True)
                        frappe.logger().info(
                            f"Created new Item Batch Stock Balance for item_code: {item_code}, batch_no: {batch_no}, warehouse: {b.get('warehouse')}"
                        )
                else:
                    # Delete entries where quantity is 0
                    frappe.db.sql(
                        """ DELETE FROM `tabItem Batch Stock Balance` 
                            WHERE batch_no = %s AND warehouse = %s AND item_code = %s """,
                        (batch_no, b.get("warehouse"), item_code),
                    )
                    frappe.logger().info(f"Deleted Item Batch Stock Balance for {batch_no}, {b.get('warehouse')}")
        else:
            # Remove batch balance if no quantity exists
            frappe.db.sql(
                """ DELETE FROM `tabItem Batch Stock Balance` WHERE item_code = %s and batch_no = %s """,
                (item_code, batch_no),
            )
            frappe.logger().info(f"Removed Item Batch Stock Balance entirely for {batch_no}")
        
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in update_item_batch_qty")
        frappe.logger().error(f"Error updating Item Batch Stock Balance for item_code: {item_code}, batch_no: {batch_no}. Details: {str(e)}")
        raise

	

# Newly Optimized code on 20/10/23 

@frappe.whitelist()	
def item_update(doc):
	try:
		# frappe.log_error(title='--',message = doc.name)
		items_code = "'"+doc.name+"'"
		bom_items = frappe.db.sql(""" SELECT item_code FROM `tabBOM Item` BI 
								  INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item)s 
			    				  AND B.is_active = 1 """,{"item":doc.name},as_dict=1)
		if bom_items:
			items_code += ","
			for x in bom_items:
				items_code += "'"+x.item_code+"',"
			items_code = items_code[:-1]
		# frappe.log_error("item code", items_code)
		frappe.db.sql(f""" DELETE FROM `tabItem Batch Stock Balance` WHERE item_code IN ({items_code}) """)
		frappe.db.commit()
		item_map = get_item_info(items_code)
		iwb_map = get_item_batch_map(items_code,float_precision=3)
		float_precision = 3
		for item in sorted(iwb_map):
			for wh in sorted(iwb_map[item]):
				for batch in sorted(iwb_map[item][wh]):
					qty_dict = iwb_map[item][wh][batch]
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						allow = False
						if qty_dict.bal_qty>0:
							allow = True
						if frappe.db.get_value("Item",item,"allow_negative_stock")==1:
							allow = True
						if allow:
							ibs_doc = frappe.new_doc("Item Batch Stock Balance")
							ibs_doc.item_code=item
							ibs_doc.item_name=item_map[item]["item_name"]
							ibs_doc.description=item_map[item]["description"]
							ibs_doc.warehouse=wh
							ibs_doc.batch_no=batch
							ibs_doc.qty=flt(qty_dict.bal_qty, float_precision)
							ibs_doc.stock_uom=item_map[item]["stock_uom"]
							ibs_doc.save(ignore_permissions=True)
							frappe.db.commit()
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Item Batch Stock Balance")
		frappe.log_error(title="item details--Item batch stock balance--",message=item_map)
		frappe.log_error(title="sle items--Item batch stock balance--",message=iwb_map)
		frappe.db.rollback()
		return {"status":"Failed"}

def get_item_info(items_code=None):
	item_map = {}
	condition = ""
	if items_code:
		condition = " AND name IN ("+items_code+")"
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem WHERE 1=1  {condition}".format(condition=condition), as_dict=1):
		item_map.setdefault(d.name, d)
	return item_map

def get_item_batch_map(items_code,float_precision):
	sle = get_stock_ledger_info(items_code)
	iwb_map = {}
	from_date = getdate('2021-04-21')
	to_date = getdate()
	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.actual_qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
	return iwb_map

def get_stock_ledger_info(items_code):
	conditions = f"  AND company = 'SPP' AND item_code IN ({items_code}) AND posting_date <= '{getdate()}' "
	return frappe.db.sql("""
		select SL.item_code, SL.batch_no, SL.warehouse, SL.posting_date, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry` SL
		inner join `tabBatch` B ON B.name = SL.batch_no
		where (case when B.expiry_date is not null then B.expiry_date >= CURDATE() else 1=1 end) AND SL.is_cancelled = 0 and SL.docstatus < 2 and ifnull(SL.batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code, warehouse
		order by item_code, warehouse""" %
		conditions, as_dict=1)

# end on 20/10/23

@frappe.whitelist()
def update_consumed_items(doc,method):
	frappe.db.sql(""" UPDATE `tabMaterial Reserved Stock` SET is_consumed=1 WHERE stock_entry_reference=%(stock_entry_reference)s """,{"stock_entry_reference":doc.name})
	frappe.db.commit()
	
def attach_mix_barcode(doc,method):
	update_se_barcode(doc)

def generate_se_mixbarcode(doc,method):
	# This is for testing purpose after test it should remove
	# for x in doc.items:
	# 	item_doc = frappe._dict({'name':x.item_code})
	# 	config_and_enqueue_job(item_doc)
	# end on 20/10/23
	if doc.items and doc.stock_entry_type == "Manufacture":
		allow_save = 0
		for x in doc.items:
			if x.t_warehouse and x.spp_batch_number and not x.barcode_text and not x.barcode_attach:
				if frappe.db.get_value("Item",x.item_code,"item_group") == "Batch":
					allow_save = 1
					bcode_resp = generate_barcode(x.mix_barcode)
					x.barcode_attach = bcode_resp.get("barcode")
					x.barcode_text = bcode_resp.get("barcode_text")
		if allow_save:
			doc.save(ignore_permissions=True)

@frappe.whitelist()	
def update_se_barcode(doc):
	allow_save = 0
	if doc.items and doc.stock_entry_type == "Manufacture":
		for x in doc.items:
			if x.t_warehouse and x.spp_batch_number and not x.barcode_text and not x.mix_barcode:
				if frappe.db.get_value("Item",x.item_code,"item_group")=="Compound":
					allow_save = 1
					d_spp_batch_no = get_spp_batch_date(x.item_code)
					bcode_resp = generate_barcode("C_"+d_spp_batch_no)
					x.mix_barcode = x.item_code+"_"+d_spp_batch_no
					x.is_compound=1
					x.barcode_attach = bcode_resp.get("barcode")
					x.barcode_text = bcode_resp.get("barcode_text")
			if x.t_warehouse and x.spp_batch_number and not x.barcode_text:
				if frappe.db.get_value("Item",x.item_code,"item_group") == "Batch":
					allow_save = 1
					bcode_resp = generate_barcode(x.mix_barcode)
					x.barcode_attach = bcode_resp.get("barcode")
					x.barcode_text = bcode_resp.get("barcode_text")
	elif doc.items and doc.stock_entry_type == "Material Receipt":
		for x in doc.items:
			if x.t_warehouse and not x.barcode_text and x.mix_barcode:
				item_group = frappe.db.get_value("Item",x.item_code,"item_group")
				if item_group == "Compound":
					allow_save = 1
					bcode_resp = generate_barcode(x.mix_barcode)
					x.is_compound = 1
					x.barcode_attach = bcode_resp.get("barcode")
					x.barcode_text =bcode_resp.get("barcode_text")
			elif x.t_warehouse and not x.barcode_text:
				item_group = frappe.db.get_value("Item",x.item_code,"item_group")
				if item_group == "Mat" or item_group == "Products":
					allow_save = 1
					bcode_resp = generate_barcode(x.spp_batch_number)
					x.barcode_attach = bcode_resp.get("barcode")
					x.barcode_text =bcode_resp.get("barcode_text")
	if allow_save:
		doc.save(ignore_permissions=True)

@frappe.whitelist()	
def save_generate_batchwise_report(doc):
	try:
		items_code = ""
		items = frappe.db.sql(""" SELECT item_code FROM `tabStock Entry Detail` WHERE parent=%(st_name)s GROUP BY item_code""",{"st_name":doc.name},as_dict=1)
		for x in items:
			frappe.db.sql("""DELETE FROM `tabItem Batch Stock Balance` WHERE item_code=%(item_code)s""",{"item_code":x.item_code})
			frappe.db.commit()
			items_code += "'"+x.item_code+"',"
		if items:
			items_code = items_code[:-1]
		item_map = get_item_details(items_code)
		if items_code:
			iwb_map = get_item_warehouse_batch_map(items_code,float_precision=3)
			# frappe.log_error(title = '--iwb_map info--',message = item_map)
			data = []
			float_precision = 3
			for item in sorted(iwb_map):
				# if not filters.get("item") or filters.get("item") == item:
				for wh in sorted(iwb_map[item]):
					for batch in sorted(iwb_map[item][wh]):
						qty_dict = iwb_map[item][wh][batch]
						if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
							allow = False
							if qty_dict.bal_qty>0:
								allow = True
							if frappe.db.get_value("Item",item,"allow_negative_stock")==1:
								allow = True
							if allow:
								ibs_doc = frappe.new_doc("Item Batch Stock Balance")
								ibs_doc.item_code=item
								ibs_doc.item_name=item_map[item]["item_name"]
								ibs_doc.description=item_map[item]["description"]
								ibs_doc.warehouse=wh
								ibs_doc.batch_no=batch
								ibs_doc.qty=flt(qty_dict.bal_qty, float_precision)
								ibs_doc.stock_uom=item_map[item]["stock_uom"]
								ibs_doc.save(ignore_permissions=True)
								frappe.db.commit()

	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Item Batch Stock Balance")
		frappe.db.rollback()
		return {"status":"Failed"}
	
def get_conditions(items_code):
	conditions = ""
	conditions += " AND company = 'SPP'"
	conditions += " AND item_code IN ({items_code})".format(items_code=items_code)
	conditions += " AND posting_date <= '%s'" % getdate()
	return conditions

# get all details
def get_stock_ledger_entries(items_code):
	conditions = get_conditions(items_code)
	return frappe.db.sql("""
		select SL.item_code, SL.batch_no, SL.warehouse, SL.posting_date, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry` SL
		inner join `tabBatch` B ON B.name = SL.batch_no
		where (case when B.expiry_date is not null then B.expiry_date >= CURDATE() else 1=1 end) AND SL.is_cancelled = 0 and SL.docstatus < 2 and ifnull(SL.batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code, warehouse
		order by item_code, warehouse""" %
		conditions, as_dict=1)

def get_item_warehouse_batch_map(items_code,float_precision):
	sle = get_stock_ledger_entries(items_code)
	# frappe.log_error(title = '--sle--',message = sle)
	iwb_map = {}
	from_date = getdate('2021-04-21')
	to_date = getdate()
	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.actual_qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
	return iwb_map


def get_item_details(items_code=None):
	item_map = {}
	condition = ""
	if items_code:
		condition = " AND name IN ("+items_code+")"
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem WHERE 1=1  {condition}".format(condition=condition), as_dict=1):
		item_map.setdefault(d.name, d)
	return item_map

@frappe.whitelist()
def update_stock_balance():
	pass
	# item_list = frappe.db.sql(""" SELECT name from `tabItem` WHERE default_bom is not null and name like 'C_%%' and item_group='Compound' and disabled = 0""",as_dict=1)
	# for x in item_list:
	# 	doc = frappe._dict({'name':x.name})
		# config_and_enqueue_job(doc)

@frappe.whitelist()
def get_process_based_employess(doctype, txt, searchfield, start, page_len, filters):
	condition=''
	if txt:
		condition += " and (first_name like '%"+txt+"%' OR name like '%"+txt+"%')"
	if filters.get("process"):	
		desgn_list = frappe.db.get_all("SPP Designation Mapping",filters={"spp_process":filters.get("process")},fields=['designation'])
		if desgn_list:
			rl_list = ""
			for x in desgn_list:
				rl_list+="'"+x.designation+"',"
			rl_list = rl_list[:-1]
			return frappe.db.sql('''SELECT name,CONCAT(first_name,' ',last_name) as description  FROM `tabEmployee` WHERE status='Active' AND designation IN({roles}) {condition}'''.format(condition=condition,roles=rl_list))

	return []

@frappe.whitelist()
def generate_batch_barcode(doc):
	if not doc.barcode_attach:
		import code128
		import io
		from PIL import Image, ImageDraw, ImageFont
		barcode_param = barcode_text = "CB_"+doc.item
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
		doc.barcode_attach = "/files/" + barcode_text + ".png"
		doc.barcode_text = barcode_text
		doc.save(ignore_permissions=True)

@frappe.whitelist()
def update_wh_barcode(doc,method):
	spp_settings = frappe.get_single("SPP Settings")
	if spp_settings.deflashing_vendor:
		condition = []
		for v in spp_settings.deflashing_vendor:
			condition.append(v.vendor)
		if doc.parent_warehouse in condition:
			if not doc.barcode:
				if doc.name.lower().startswith('df'):
					import code128
					import io
					from PIL import Image, ImageDraw, ImageFont
					barcode_param = barcode_text = doc.name.split(':')[0]
					# barcode_param,barcode_text = None,None
					# while True:
					# 	barcode_param = barcode_text = str(randomStringDigits(8))
					# 	if frappe.db.get_all("Warehouse",filters={"barcode_text":barcode_text}):
					# 		continue
					# 	else:
					# 		break
					barcode_image = code128.image(barcode_param, height=120)
					w, h = barcode_image.size
					margin = 5
					new_h = h +(2*margin) 
					new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
					# put barcode on new image
					new_image.paste(barcode_image, (0, margin))
					# object to draw text
					draw = ImageDraw.Draw(new_image)
					file_url_name = remove_spl_characters(barcode_param)
					new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
					doc.barcode = "/files/" + file_url_name + ".png"
					doc.barcode_text = barcode_text
					doc.save(ignore_permissions=True)
	else:
		frappe.throw("Deflashing Vendors group not mapped in SPP Settings.")

def remove_spl_characters(string):
	char = ''.join(e for e in string if e.isalnum())
	return char

@frappe.whitelist()
def update_emp_barcode(doc,method):
	if not doc.barcode:
		import code128
		import io
		from PIL import Image, ImageDraw, ImageFont
		barcode_param = barcode_text = doc.name
		barcode_image = code128.image(barcode_param, height=120)
		w, h = barcode_image.size
		margin = 5
		new_h = h +(2*margin) 
		new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
		# put barcode on new image
		new_image.paste(barcode_image, (0, margin))
		# object to draw text
		draw = ImageDraw.Draw(new_image)
		file_url_name = remove_spl_characters(barcode_param)
		new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
		doc.barcode = "/files/" + file_url_name + ".png"
		doc.barcode_text = barcode_text
		doc.save(ignore_permissions=True)

def randomStringDigits(stringLength=6):
	import random
	import string
	lettersAndDigits = string.ascii_uppercase + string.digits
	return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))

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
	
def get_spp_batch_date(compound=None):
	serial_no = 1
	serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
	if serial_nos:
		serial_no = serial_nos[0].serial_no+1
	month_key = getmonth(str(str(getdate()).split('-')[1]))
	l = len(str(getdate()).split('-')[0])
	compound_key = (str(getdate()).split('-')[0])[l - 2:]+month_key+str(str(getdate()).split('-')[2])+"X"+str(serial_no)
	return compound_key

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

def get_lo_no(doc_info):
	serial_no = 1
	serial_nos = frappe.db.get_all("Moulding Serial No",filters={"posted_date":getdate(),'shift_no':doc_info.shift_number},fields=['serial_no'],order_by="serial_no DESC")
	if serial_nos:
		serial_no = serial_nos[0].serial_no+1
	sl_no = frappe.new_doc("Moulding Serial No")
	sl_no.posted_date = getdate()
	sl_no.compound_code = doc_info.production_item
	sl_no.serial_no = serial_no
	sl_no.shift_no = doc_info.shift_number
	sl_no.insert(ignore_permissions = True)
	serial_no = 1
	serial_nos = frappe.db.get_all("Moulding Serial No",filters={"posted_date":getdate(),'shift_no':doc_info.shift_number},fields=['serial_no'],order_by="serial_no DESC")
	if serial_nos:
		serial_no = serial_nos[0].serial_no + 1
	month_key = getmonth(str(str(getdate()).split('-')[1]))
	l = len(str(getdate()).split('-')[0])
	serial_no = f"'X'{30*(int(doc_info.shift_number)-1)+int(serial_no)}"
	compound_key = (str(getdate()).split('-')[0])[l - 2:]+month_key+str(str(getdate()).split('-')[2])+str("{:02d}".format(serial_no))
	return compound_key

def generate_lot_number(doc,event):
	try:
		if not doc.batch_code and doc.operation == "Moulding":
			production_lot_number = get_lo_no(doc)
			barcode = generate_barcode(production_lot_number)
			query = f" UPDATE `tab{doc.doctype}` SET batch_code='{production_lot_number}',barcode_image_url='{barcode.get('barcode')}' WHERE name='{doc.name}' "
			frappe.db.sql(query)
			frappe.db.commit()
		# update_qty(doc)
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.generate_lot_number",message=frappe.get_traceback())
		frappe.throw("Barcode generation failed..!")

def get_stock_entry_naming_series(spp_settings,stock_entry_type):
	try:
		if spp_settings and spp_settings.spp_naming_series:
			naming_series = list(filter(lambda x : x.stock_entry_type == stock_entry_type,spp_settings.spp_naming_series))
			if naming_series and naming_series[0].spp_naming_series:
				return True,naming_series[0].spp_naming_series
			else:
				return False,""
		else:
			return False,""
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.get_stock_entry_naming_series",message=frappe.get_traceback())

@frappe.whitelist()
def update_asset_barcode(doc,method):
	try:
		if not doc.barcode:
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.bin_category:
				frappe.throw('Bin Category not mapped in SPP settings..!')
			elif doc.asset_category and spp_settings.bin_category == doc.asset_category:
				import code128
				from PIL import Image, ImageDraw, ImageFont
				b__code = ""
				a__name = doc.asset_name.split(" ")
				if len(a__name) > 1:
					for idx,k in enumerate(a__name):
						if idx !=0:
							b__code += f"{k} "
					if b__code:
						b__code = b__code[:-1]
				else:
					b__code = a__name[0]
				barcode_param = barcode_text = b__code
				# barcode_param,barcode_text = None,None
				# while True:
				# 	barcode_param = barcode_text = str(randomStringDigits(8))
				# 	if frappe.db.get_all(doc.doctype,filters={"barcode_text":barcode_text}):
				# 		continue
				# 	else:
				# 		break
				barcode_image = code128.image(barcode_param, height=120)
				w, h = barcode_image.size
				margin = 5
				new_h = h +(2*margin) 
				new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
				new_image.paste(barcode_image, (0, margin))
				file_url_name = remove_spl_characters(barcode_param)
				new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
				frappe.db.set_value("Asset",doc.name,"barcode","/files/" + file_url_name + ".png")
				frappe.db.set_value("Asset",doc.name,"barcode_text",barcode_text)
				frappe.db.commit()
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.update_asset_barcode",message=frappe.get_traceback())
		frappe.throw("Barcode generation failed..!")

@frappe.whitelist()
def update_all_asset_barcodes():
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.bin_category:
			assets = frappe.db.get_all("Asset",
					 filters={"asset_category":spp_settings.bin_category,"docstatus":1},
					 fields=['barcode','name',"asset_name"])
			for asset in assets:
				# if not asset.barcode:
					import code128
					from PIL import Image, ImageDraw, ImageFont
					b__code = ""
					a__name = asset.asset_name.split(" ")
					if len(a__name) > 1:
						for idx,k in enumerate(a__name):
							if idx !=0:
								b__code += f"{k} "
						if b__code:
							b__code = b__code[:-1]
					else:
						b__code = a__name[0]
					barcode_param,barcode_text = b__code,b__code
					# barcode_param,barcode_text = None,None
					# while True:
					# 	barcode_param = barcode_text = str(randomStringDigits(8))
					# 	if frappe.db.get_all("Asset",filters={"barcode_text":barcode_text}):
					# 		continue
					# 	else:
					# 		break
					barcode_image = code128.image(barcode_param, height=120)
					w, h = barcode_image.size
					margin = 5
					new_h = h +(2*margin) 
					new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
					new_image.paste(barcode_image, (0, margin))
					file_url_name = remove_spl_characters(barcode_param)
					new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
					frappe.db.set_value("Asset",asset.name,"barcode","/files/" + file_url_name + ".png")
					frappe.db.set_value("Asset",asset.name,"barcode_text",barcode_text)
					frappe.db.commit()
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.update_all_asset_barcodes",message=frappe.get_traceback())
		frappe.throw("Barcode generation failed..!")

@frappe.whitelist()
def update_all_emp_barcode():
	import code128
	import io
	from PIL import Image, ImageDraw, ImageFont
	emp = frappe.db.get_all("Employee",filters={"status":"Active","company":"SPP"},fields=['name'])
	for e_emp in emp:
		barcode_param = barcode_text = e_emp.name
		barcode_image = code128.image(barcode_param, height=120)
		w, h = barcode_image.size
		margin = 5
		new_h = h +(2*margin) 
		new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
		new_image.paste(barcode_image, (0, margin))
		file_url_name = remove_spl_characters(barcode_param)
		new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
		frappe.db.set_value("Employee",e_emp.name,"barcode","/files/" + file_url_name + ".png")
		frappe.db.set_value("Employee",e_emp.name,"barcode_text",barcode_text)
		frappe.db.commit()

@frappe.whitelist()
def update_all_wh_barcode():
	spp_settings = frappe.get_single("SPP Settings")
	if spp_settings.deflashing_vendor:
		condition = []
		for v in spp_settings.deflashing_vendor:
			condition.append(v.vendor)
		warehouse = frappe.db.get_all("Warehouse",filters={"disabled":0},fields=['name',"parent_warehouse"])
		for war in warehouse:
			if war.parent_warehouse in condition:
				if war.name.lower().startswith('df'):
					import code128
					import io
					from PIL import Image, ImageDraw, ImageFont
					barcode_param = barcode_text = war.name.split(':')[0]
					# barcode_param,barcode_text = None,None
					# while True:
					# 	barcode_param = barcode_text = str(randomStringDigits(8))
					# 	if frappe.db.get_all("Warehouse",filters={"barcode_text":barcode_text}):
					# 		continue
					# 	else:
					# 		break
					barcode_image = code128.image(barcode_param, height=120)
					w, h = barcode_image.size
					margin = 5
					new_h = h +(2*margin) 
					new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
					# put barcode on new image
					new_image.paste(barcode_image, (0, margin))
					# object to draw text
					draw = ImageDraw.Draw(new_image)
					file_url_name = remove_spl_characters(barcode_param)
					new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
					frappe.db.set_value("Warehouse",war.name,"barcode","/files/" + file_url_name + ".png")
					frappe.db.set_value("Warehouse",war.name,"barcode_text",barcode_text)
					frappe.db.commit()
	else:
		frappe.throw("Deflashing Vendors group not mapped in SPP Settings.")
	
def update_qty(doc):
	try:
		if not doc.total_qty_after_inspection:
			frappe.db.sql(" UPDATE `tabJob Card` SET total_qty_after_inspection = {0} WHERE name = '{1}'".format(doc.total_completed_qty,doc.name))
			frappe.db.commit()
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.update_qty",message=frappe.get_traceback())

def generate_batch_no(batch_id,item = None,qty = None,reference_doctype = None,reference_name = None):
	try:
		if not frappe.db.get_value("Batch",batch_id,"name"):
			res,msg =  gen_batch(batch_id,item,qty,reference_doctype,reference_name)
			return res,msg
		else:
			if not reference_doctype and not reference_name:
				frappe.db.sql(f""" UPDATE `tabBatch` SET item = '{item}',batch_qty = {qty} WHERE name = '{batch_id}' """)
				frappe.db.commit()
			else:
				res,msg = gen_batch(batch_id,item,qty,reference_doctype,reference_name)
				return res,msg
			return True,batch_id
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.generate_batch_no",message=frappe.get_traceback())
		return False,"Not able to generate batch"

def gen_batch(batch_id,item,qty,reference_doctype,reference_name):
	if not reference_doctype and not reference_name:
		if not batch_id:
			return False,f"Batch ID is missing for generate batch."
		if not item:
			return False,f"Item is missing for generate batch."
		if not qty:
			return False,f"Quantity is missing for generate batch."
		batch__ = frappe.new_doc("Batch")
		batch__.batch_id = batch_id
		batch__.item = item
		batch__.manufacturing_date = nowdate()
		batch__.expiry_date = add_to_date(nowdate(), years=1)
		batch__.batch_qty = qty
		batch__.insert(ignore_permissions = True)
		return True,batch__.name
	else:
		frappe.db.sql(f""" UPDATE `tabBatch` SET reference_doctype='{reference_doctype}',reference_name='{reference_name}' WHERE name='{batch_id}' """)
		frappe.db.commit()
		return True,batch_id
	
def delete_batches(batch_ids):
	try:
		cond_ = ""
		for b_ in batch_ids:
			cond_ += f"'{b_}',"
		cond_ = cond_[:-1]
		frappe.db.sql(f""" DELETE FROM `tabBatch` WHERE name IN ({cond_}) """)
		frappe.db.commit()
		return True,""
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.delete_batch",message=frappe.get_traceback())
		return False,"Not able to delete batches"
	
def find_material_trns_entry(lot_no):
	query = f""" SELECT 
					SE.stock_entry_type,SED.valuation_rate,SED.amount,SED.source_ref_document,
					SED.creation,SED.mix_barcode,SED.t_warehouse,SED.item_code,SED.spp_batch_number,
					IBSB.qty,IBSB.stock_uom,SED.batch_no
				FROM 
					`tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name = SED.parent 
					LEFT JOIN `tabItem Batch Stock Balance` IBSB ON IBSB.batch_no = SED.batch_no 
					AND IBSB.warehouse = SED.t_warehouse 
				WHERE 
					SE.docstatus = 1 AND SED.spp_batch_number = '{lot_no}' 
					AND SED.t_warehouse IS NOT NULL AND SE.stock_entry_type = 'Material Receipt' LIMIT 1 """
	result__ = frappe.db.sql(query,as_dict = 1)
	if result__:
		if result__[0].qty:
			result__[0].creation = getdate(result__[0].creation)
			return {"status":"success","data":result__[0]}
		else:
			return {"status":"success","message":"Stock is not available for the scanned lot..!"}
	else:
		return {"status":"success","message":"Stock is not available for the scanned lot..!"}

def get_details_by_lot_no(lot_no,st_type = None,source_doctype = None,ware__house = None,ignore_lot_val = None,condition__ = "",ref_doc = None,transfer_other_warehouse = None,from_ledger_entry = None):
	try:
		""" This function is used to tranfer the material which is not in current work flow which means any warehouse """
		if transfer_other_warehouse:
			material__resp = find_material_trns_entry(lot_no)
			if material__resp:
				if material__resp.get('data'):
					return {"status":"success","data":material__resp.get('data')}
				# elif material__resp.get('message'):
				# 	return material__resp
		""" End """
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.scrap_warehouse:
			return {"status":"failed","message":"Scrap warehouse not mapped in SPP Settings..!"}
		if spp_settings.sub_lot_source_warehouse:
			w__cond = ""
			for w_house in spp_settings.sub_lot_source_warehouse:
				w__cond += f"'{w_house.warhouse}',"
			w__cond = w__cond[:-1]
			query = f""" SELECT name FROM `tabSub Lot Creation` WHERE sub_lot_no = '{lot_no}' AND docstatus = 1 """
			res_ = frappe.db.sql(query,as_dict = 1)
			if res_ or ignore_lot_val:
				if ref_doc:
					resp__ = validate_nessaery_data(ref_doc,lot_no)
					if resp__ and resp__.get('status') == "failed":
						return {"status":resp__.get('resp_status'),"message":resp__.get('resp_message',None),"data":resp__.get('resp_data',None)}
				condition = f" AND SED.t_warehouse != '{spp_settings.scrap_warehouse}' "
				if st_type:
					condition += f" AND SE.stock_entry_type = '{st_type}' "
				if source_doctype:
					condition += f" AND SED.source_ref_document = '{source_doctype}' "
				if ware__house:
					condition += f" AND SED.t_warehouse = '{ware__house}' "
				if from_ledger_entry:
					query = f""" SELECT IBSB.item_code,IBSB.warehouse,IBSB.batch_no,IBSB.qty,IBSB.stock_uom FROM `tabItem Batch Stock Balance` IBSB WHERE batch_no= 'P{lot_no}' {condition__} LIMIT 1 """
					# query = f""" SELECT SLE.item_code,SLE.warehouse,SLE.batch_no,SLE.actual_qty qty,SLE.stock_uom FROM `tabStock Ledger Entry` SLE INNER JOIN `tabBatch` B ON B.batch_id = SLE.batch_no WHERE SLE.batch_no = 'P{lot_no}' {condition__} """
				else:
					spp_warehouse_condition = f" AND SED.t_warehouse IN ({w__cond}) "
					# frappe.db.sql(" SET SQL_BIG_SELECTS = 1 ")
					#  ORDER BY SE.creation DESC
					# on 28/3/24 optimized query
					# query = f""" SELECT SE.name as st_entry_id,SE.stock_entry_type,SED.valuation_rate,SED.amount,SED.source_ref_document,SED.creation, SED.mix_barcode,SED.t_warehouse,SED.item_code,SED.spp_batch_number,IBSB.qty,IBSB.stock_uom,SED.batch_no
					# 			FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name = SED.parent LEFT JOIN `tabItem Batch Stock Balance` IBSB ON IBSB.batch_no = SED.batch_no WHERE 
					# 			IBSB.warehouse = SED.t_warehouse AND SE.docstatus = 1 AND SED.spp_batch_number = '{lot_no}' {spp_warehouse_condition} AND SED.t_warehouse IS NOT NULL {condition} {condition__} LIMIT 1 """
					""" Query 1 """
					# query = f""" SELECT 
					# 				SE.name as st_entry_id,SE.stock_entry_type,SED.valuation_rate,SED.amount,
					# 				SED.source_ref_document,SED.creation, SED.mix_barcode,SED.t_warehouse,
					# 				SED.item_code,SED.spp_batch_number,IBSB.qty,IBSB.stock_uom,SED.batch_no
					# 			FROM 
					# 				`tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
					# 				LEFT JOIN `tabItem Batch Stock Balance` IBSB ON IBSB.batch_no = SED.batch_no AND
					# 																	IBSB.warehouse = SED.t_warehouse 
					# 			WHERE 
					# 				SE.docstatus = 1 AND SED.spp_batch_number = '{lot_no}' {spp_warehouse_condition} 
					# 				AND SED.t_warehouse IS NOT NULL {condition} {condition__} LIMIT 1 """
					""" Query 2 """
					query = f""" SELECT 
									SED.parent as st_entry_id,SED.valuation_rate,SED.amount,
									SED.source_ref_document,SED.creation, SED.mix_barcode,SED.t_warehouse,
									SED.item_code,SED.spp_batch_number,IBSB.qty,IBSB.stock_uom,SED.batch_no
								FROM 
									`tabStock Entry Detail` SED 
									INNER JOIN `tabItem Batch Stock Balance` IBSB ON IBSB.batch_no = SED.batch_no AND
																						IBSB.warehouse = SED.t_warehouse 
								WHERE 
									SED.docstatus = 1 AND SED.spp_batch_number = '{lot_no}' {spp_warehouse_condition} 
									{condition} {condition__} LIMIT 1 """
				
					# end
				# frappe.log_error(title="api file -- sub lot query",message=query)
				result__ = frappe.db.sql(query,as_dict = 1)
				if result__:
					# modified on 28/3/24
					valid_result = None
					for res in result__:
						if valid_stock := frappe.db.get_value("Stock Entry",{"name":res.st_entry_id,"docstatus":1},["stock_entry_type"],as_dict = 1):
							res.stock_entry_type = valid_stock.stock_entry_type
							valid_result = res
							break
					if valid_result and valid_result.qty:
						valid_result.creation = getdate(valid_result.creation)
						return {"status":"success","data":valid_result}
					else:
						return {"status":"success","message":"Stock is not available for the scanned lot..!"}
					
					# frappe.log_error(title="api file -- sub lot response",message = result__)
					# if result__[0].qty:
					# 	result__[0].creation = getdate(result__[0].creation)
					# 	return {"status":"success","data":result__[0]}
					# else:
					# 	return {"status":"success","message":"Stock is not available for the scanned lot..!"}
					
					# end
				else:
					return {"status":"success","message":"Stock is not available for the scanned lot..!"}
			else:
				return {"status":"failed","message":"Data not found for the scanned lot..!"}
		else:
			return {"status":"failed","message":"Source warehouses not mapped in SPP Settings..!"}
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.get_details_by_lot_no",message=frappe.get_traceback())
		return {"status":"failed","message":"No data found for the scanned lot..!"}
	
def validate_nessaery_data(ref_doc,lot_no):
	if ref_doc == "Lot Resource Tagging":
		rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":lot_no,"docstatus":1},"name")
		if rept_entry:
			check_exist = frappe.db.get_value("Inspection Entry",{"docstatus":1,"lot_no":lot_no,"inspection_type":"Incoming Inspection"},"name")
			if check_exist:
				return False
			else:
				return {"status":"failed","resp_status":"success","resp_message":f"There is no <b>Incoming Inspection entry</b> found for the lot <b>{lot_no}</b>"}
	elif ref_doc == "Incoming Inspection Entry":
		rept_entry = frappe.db.get_value("Deflashing Receipt Entry",{"lot_number":lot_no,"docstatus":1},["name","stock_entry_reference"],as_dict = 1)
		if rept_entry:
			if rept_entry.stock_entry_reference:
				#Added on 4/7/2023 for incoming inspection validation for Final visual inspection entry
				# query = f""" SELECT SE.stock_entry_type,SED.valuation_rate,SED.amount,SED.source_ref_document,SED.creation, SED.mix_barcode,SED.t_warehouse,SED.item_code,SED.spp_batch_number,SED.qty,SED.stock_uom,SED.batch_no
				# 			FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name = SED.parent WHERE 
				# 			SE.docstatus = 0 AND SED.t_warehouse IS NOT NULL AND SE.name='{rept_entry.stock_entry_reference}' """
				query = f""" SELECT SE.stock_entry_type,SED.valuation_rate,SED.amount,SED.source_ref_document,SED.creation, SED.mix_barcode,SED.t_warehouse,SED.item_code,SED.spp_batch_number,SED.qty,SED.stock_uom,SED.batch_no
							FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE ON SE.name = SED.parent WHERE 
							(SE.docstatus = 0 OR SE.docstatus = 1) AND SED.t_warehouse IS NOT NULL AND SE.name='{rept_entry.stock_entry_reference}' AND SED.deflash_receipt_reference = '{lot_no}' LIMIT 1 """
				#End
				result__ = frappe.db.sql(query,as_dict = 1)
				if result__:
					return {"status":"failed","resp_status":"success","resp_data":result__[0]}
				else:
					return {"status":"failed","resp_status":"success","resp_message":"Stock Entry for Deflahing Receipt not found (Draft)..!"}
			else:
				return {"status":"failed","resp_status":"success","resp_message":"Stock Entry for Deflahing Receipt not found (Draft)..!"}
	return False

def find_parent_lot(lot_no,field_name):
	try:
		query = None
		if field_name:
			query = f""" SELECT {field_name} FROM `tabSub Lot Creation` 
						WHERE CASE WHEN sub_lot_no = '{lot_no}' THEN  sub_lot_no = '{lot_no}' 
						ELSE scan_lot_no = '{lot_no}' END AND docstatus = 1 LIMIT 1 """
		else:
			query = f""" SELECT first_parent_lot_no FROM `tabSub Lot Creation` 
						WHERE CASE WHEN sub_lot_no = '{lot_no}' THEN  sub_lot_no = '{lot_no}' 
						ELSE scan_lot_no = '{lot_no}' END AND docstatus = 1 LIMIT 1 """
		res_ = frappe.db.sql(query,as_dict = 1)
		if res_:
			if field_name:
				if res_[0][field_name]:
					return {"status":"success","lot_no":res_[0][field_name]}
				else:
					return {"status":"failed","message":f"Source lot not found for the scanned lot <b>{lot_no}</b>"}
			else:
				if res_[0].first_parent_lot_no:
					return {"status":"success","lot_no":res_[0].first_parent_lot_no}
				else:
					return {"status":"failed","message":f"Source lot not found for the scanned lot <b>{lot_no}</b>"}
		else:
			return {"status":"failed","message":f"Source lot not found for the scanned lot <b>{lot_no}</b>"}
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.api.find_parent_lot",message=frappe.get_traceback())
		return {"status":"failed","message":"Not able to find lot ..!"}

def get_parent_lot(bar_code,field_name = None):
	p__lot_res = find_parent_lot(bar_code,field_name)
	if p__lot_res and p__lot_res.get('status') == "success":
		return {"status":"success","lot_no":p__lot_res.get('lot_no')}
	else:
		if p__lot_res and p__lot_res.get('message'):
			return {"status":"failed","message":p__lot_res.get('message')}
		else:
			return {"status":"failed","message":"Something went wrong."}

def update_raw_materials(doc,event):
	try:
		if doc.item and doc.item.lower().startswith('t'):
			set__values = ""
			if doc.items:
				for item in doc.items:
					set__values +=f"{item.item_code} - {item.item_name},"
				set__values = set__values[:-1]
				frappe.db.set_value(doc.doctype,doc.name,"raw_materials",set__values)
				frappe.db.commit()
	except Exception:
		frappe.log_error(title = "Error while updating raw materials for link field options",message = frappe.get_traceback())

@frappe.whitelist()
def update_all_raw_materials():
	try:
		boms__ = frappe.db.get_all("BOM",fields=["name"])
		for b in boms__:
			doc = frappe.get_doc("BOM",b)
			if doc.item and doc.item.lower().startswith('t'):
				set__values = ""
				if doc.items:
					for item in doc.items:
						set__values +=f"{item.item_code} - {item.item_name},"
					set__values = set__values[:-1]
					frappe.db.set_value(doc.doctype,doc.name,"raw_materials",set__values)
					frappe.db.commit()
	except Exception:
		frappe.log_error(title = "Error while updating all raw materials for link field options",message = frappe.get_traceback())

def validate_and_update_am_naming(doc,event):
	try:
		return 
		limit = 1
		while True:
			last_naming = frappe.db.sql(f""" SELECT name FROM `tab{doc.doctype}` ORDER BY creation DESC LIMIT {limit - 1},{limit} """,as_dict = 1)
			limit += 1
			if last_naming:
				name_array = last_naming[len(last_naming) - 1].name.split('-')
				name_array[len(name_array) - 1] =  str("{:05d}".format(int(name_array[len(name_array) - 1]) + 1))
				new__name = '-'.join(name_array)
				exe_ = frappe.db.get_value(doc.doctype,{'name':new__name}) 
				if exe_:
					continue
				else:
					doc.name = new__name
					break
			else:
				break
	except Exception:
		frappe.log_error(title = 'validate_and_update_am_naming error',message = frappe.get_traceback())

def get_workstation_by_operation(operation):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.workstation_mapping:
			result__ = list(filter(lambda x:x.operation == operation,spp_settings.workstation_mapping)) 
			if result__:
				return {"status":"success","message":result__[0].workstation}
			else:
				return {'status':"failed","message":f"<b>Workstation</b> not mapped in <b>SPP Settings</b> for the operation <b>{operation}</b>..!"}	
		else:
			return {'status':"failed","message":f"<b>Workstation</b> not mapped in <b>SPP Settings</b> for the operation <b>{operation}</b>..!"}
	except Exception:
		frappe.log_error(title = "get_workstation_by_operation failed", message = frappe.get_traceback())
		return {'status':"failed","message":f"Something went wrong not able to fetch <b>Workstation</b> details..!"}
	
@frappe.whitelist()	
def update_exe_sheeting_text_to_barcode():
	l = []
	for k in frappe.db.get_all("Sheeting Clip",['name','barcode_text']):
		l.append(k)
		generate_barcode__sc(k)
	return l

def generate_barcode__sc(self):
	import code128
	import io
	from PIL import Image, ImageDraw, ImageFont
	barcode_param = barcode_text = self.barcode_text
	barcode_image = code128.image(barcode_param, height=120)
	w, h = barcode_image.size
	margin = 5
	new_h = h +(2*margin) 
	new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
	new_image.paste(barcode_image, (0, margin))
	ImageDraw.Draw(new_image)
	file_url_name = remove_spl_characters(barcode_param)
	new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
	frappe.db.set_value("Sheeting Clip",self.name,"barcode","/files/" + file_url_name + ".png")
	frappe.db.commit()

@frappe.whitelist()	
def update_exe_blank_bin_text_to_barcode():
	l = []
	for k in frappe.db.get_all("Asset",filters={'barcode_text':("!=", "null"),'barcode_text':("!=", "")},fields=['name','barcode_text']):
		l.append(k)
		generate_barcode__bb(k)
	return l

def generate_barcode__bb(self):
	if self.barcode_text:
		import code128
		import io
		from PIL import Image, ImageDraw, ImageFont
		barcode_param = barcode_text = self.barcode_text
		barcode_image = code128.image(barcode_param, height=120)
		w, h = barcode_image.size
		margin = 5
		new_h = h +(2*margin) 
		new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
		new_image.paste(barcode_image, (0, margin))
		ImageDraw.Draw(new_image)
		file_url_name = remove_spl_characters(barcode_param)
		new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
		frappe.db.set_value("Asset",self.name,"barcode","/files/" + file_url_name + ".png")
		frappe.db.commit()

def get_decimal_values_without_roundoff(f, n):
    import math
    return math.floor(f * 10 ** n) / 10 ** n

def update_total_work_hrs(doc,method):
	try:		
		if doc.start_time and doc.end_time:
			from datetime import datetime
			start_time = doc.start_time
			end_time = doc.end_time
			t1 = datetime.strptime(start_time, "%H:%M:%S")
			t2 = datetime.strptime(end_time, "%H:%M:%S")
			delta = str(t2 - t1).split(',')[-1]
			doc.total_time = delta
	except Exception:
		frappe.log_error(title="Error in update_total_work_hrs", message = frappe.get_traceback())
		frappe.throw("Somthing went wrong not able to update <b>Total Time</b>..!")

@frappe.whitelist(allow_guest = True)
def validate_document_submission(doc_type,doc_name,stock_details):
	try:
		item,mixbarcode,status,message = None,None,'success',None
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.validate_stock_submission:
			st_details = json.loads(stock_details)
			if st_details.get('items'):
				for it in st_details.get('items'):
					if it.get('t_warehouse') and it.get('is_finished_item'):
						item = it.get('item_code')
						mixbarcode = it.get('mix_barcode')
			if doc_type == "Delivery Challan Receipt":
				item_group = frappe.db.get_value("Item",item,"item_group")
				if item_group == "Compound":
					doc_status = frappe.db.get_value("Compound Inspection",{"scan_compound":mixbarcode},"docstatus")
					if doc_status != 1:
						status = "failed"
						message = f"Please Complete the <b>Compound Inspection</b> before submit the <b>Stock Entry</b>..!"
					else:
						status = "success"
			elif doc_type == "Inspection Entry":
				inspection_type = frappe.db.get_value("Inspection Entry",doc_name,"inspection_type")
				if inspection_type and inspection_type == "Line Inspection":
					status = "failed"
					message = f"Please Complete the <b>Moulding Production Entry</b> before submit the <b>Stock Entry</b>..!"
				else:
					if not inspection_type:
						status = "failed"
						message = f"The <b>Inspection Entry</b> is not found for the lot <b>{mixbarcode}</b>..!"
			elif doc_type == "Moulding Production Entry":
				status = "failed"
				message = f"Please Complete the <b>Lot Inspection Entry</b> before submit the <b>Stock Entry</b>..!"
			elif doc_type == "Deflashing Receipt Entry":
				status = "failed"
				message = f"Please Complete the <b>Incoming Inspection Entry</b> before submit the <b>Stock Entry</b>..!"
		frappe.response.status = status
		frappe.response.message = message
	except Exception:
		frappe.log_error(title="error in validate_document_submission",message = frappe.get_traceback())
		frappe.response.status = "failed"
		frappe.response.message = f"Something went wrong not able to validate <b>{doc_type}</b> submission status..!"


@frappe.whitelist(allow_guest = True)
def validate_dc_document_cancellation(doc_type,doc_name,ref_document):
	try:
		status,message = 'success',None
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.validate_dn_cancellation:
			docstatus = frappe.db.get_value(doc_type,doc_name,["docstatus","name"], as_dict = 1)
			if docstatus:
				if int(docstatus.docstatus) == 1:
					status = "failed"
					message = f"Please cancel the <b>{doc_type}</b> - <b>{doc_name}</b> before cancel the <b>{ref_document}</b>..!"
				elif doc_type == "Batch ERP Entry" and int(docstatus.docstatus) == 0:
					status = "failed"
					message = f"Please delete the <b>{doc_type}</b> - <b>{doc_name}</b> before cancel the <b>{ref_document}</b>..!"
		frappe.response.status = status
		frappe.response.message = message
	except Exception:
		frappe.log_error(title="error in validate_dc_document_cancellation",message = frappe.get_traceback())
		frappe.response.status = "failed"
		frappe.response.message = f"Something went wrong not able to validate <b>{doc_type}</b> document status..!"

@frappe.whitelist()
def validate_stock_entry(st_ids):
	cond = ""
	for sten in st_ids:
		cond += f"'{sten}',"
	cond = cond[:-1]
	query = f" SELECT name FROM `tabStock Entry` WHERE name IN ({cond}) AND docstatus != 2 "
	res = frappe.db.sql(query, as_dict = 1)
	if res:
		html = f""" The Following <b>Stock Entries</b> were not <b>Cancelled</b> or in <b>Draft</b>.<br>
		 		    Please cancel or delete the entries before delete the document.<br>"""
		for idx,k in enumerate(res):
			html += f"{idx+1}. <b>{k.name}</b><br>"
		frappe.throw(html)
		return {"status":"failed"}
	else:
		return {"status":"success"}
def create_serial_batch_bundle(item_code, batch_no, warehouse, qty, voucher_type, parent_doc):
    """ERPNext v14+ compliant bundle creation with audit trail"""
    bundle = frappe.new_doc("Serial and Batch Bundle")
    bundle.voucher_type = voucher_type
    bundle.voucher_no = parent_doc.name if parent_doc else None
    bundle.item_code = item_code
    bundle.warehouse = warehouse
    bundle.type_of_transaction = "Outward" if warehouse == parent_doc.from_warehouse else "Inward"
    
    bundle.append("entries", {
        "batch_no": batch_no,
        "qty": qty,
        "warehouse": warehouse,
        "incoming_rate": frappe.db.get_value("Item", item_code, "last_purchase_rate"),
        "reference_doctype": parent_doc.doctype if parent_doc else None,
        "reference_name": parent_doc.name if parent_doc else None
    })
    
    bundle.flags.ignore_permissions = True
    bundle.insert()
    return bundle.name

def validate_bundle_uniqueness(items):
    seen = set()
    for item in items:
        if not item.serial_and_batch_bundle:
            continue
        if item.serial_and_batch_bundle in seen:
            frappe.throw(
                f"Duplicate bundle {item.serial_and_batch_bundle} found at row {item.idx}",
                title="Inventory Bundle Conflict"
            )
        seen.add(item.serial_and_batch_bundle)
		
@frappe.whitelist()
def get_item_details(batch_number):
    item = frappe.get_doc('Batch', batch_number)
    item_code = item.item
    item_name = frappe.db.get_value('Item', item_code, 'item_name')
    item_group = frappe.db.get_value('Item', item_code, 'item_group')
    warehouse = frappe.db.get_value('Item', item_code, 'default_warehouse')
    current_stock = frappe.db.get_value('Bin', {'item_code': item_code, 'warehouse': warehouse}, 'actual_qty')

    return {
        'item_code': item_code,
        'item_name': item_name,
        'item_group': item_group,
        'warehouse': warehouse,
        'current_stock': current_stock
    }