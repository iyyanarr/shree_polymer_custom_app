# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series

class DeliveryChallanReceipt(Document):
	def validate(self):
		if self.dc_receipt_date and getdate(self.dc_receipt_date) > getdate():
			frappe.throw("The <b>Mixing Date</b> can't be greater than <b>Today Date</b>..!")

	def on_submit(self):
		try:
			fb_mix = validate_final_batches(self)
			if fb_mix:
				try:
					wo,message = create_wo(self)
					if wo:
						update_over_all_dn_status(self,"Not Hold")
					else:
						frappe.db.rollback()
						rollback_wo_se_jc(self,message)
				except Exception:
					frappe.db.rollback()
					rollback_wo_se_jc(self,"Delivery Note update failed..!")
			self.reload()
		except Exception:
			rollback_wo_se_jc(self,"Stock Entry Creation Error..!")
			frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.delivery_challan_receipt.delivery_challan_receipt.on_submit",message=frappe.get_traceback())
	
	def on_cancel(self):
		self.reload()
		if self.dc_items:
			for dc_items in self.dc_items:
				if dc_items.dc_no:
					m_item = frappe.db.get_all("Delivery Note Item",filters={"parent":dc_items.dc_no,"parenttype":"Delivery Note","scan_barcode":dc_items.scan_barcode,"item_code":dc_items.item_code})
					if m_item:
						for x in m_item:
							frappe.db.set_value("Delivery Note Item",x.name,"is_received",0)
							frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_no","")
			frappe.db.commit()

def update_over_all_dn_status(self,dc_type):
	if dc_type == "Not Hold":
		dc_query ="SELECT dc_no,operation FROM `tabDC Item` WHERE parent='{dc_reciept}' GROUP BY dc_no,operation ".format(dc_reciept=self.name)
		dc_nos = frappe.db.sql(dc_query,as_dict=1)
		for x in dc_nos:
			if frappe.db.get_all("Delivery Note Item",filters={"parent":x.dc_no,"parenttype":"Delivery Note","is_received":0}):
				frappe.db.set_value("Delivery Note",x.dc_no,"received_status","Partially Completed")
			else:
				frappe.db.set_value("Delivery Note",x.dc_no,"received_status","Completed")
		frappe.db.commit()
	elif dc_type == "Hold":
		""" Dc no was not fetch while scanning the barcode before use thid function need to fetch dc no first  """
		for x in self.hld_items:
			m_item = frappe.db.get_all("Delivery Note Item",filters={"parent":x.dc_no,"parenttype":"Delivery Note","scan_barcode":x.mix_barcode,"item_code":x.item_code})
			if m_item:
				for x in m_item:
					frappe.db.set_value("Delivery Note Item",x.name,"is_received",1)
					frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_no",self.name)
					frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_date",(getdate() if not self.dc_receipt_date else self.dc_receipt_date))
		dc_query = " SELECT dc_no,operation FROM `tabMixing Center Holding Item` WHERE parent='{dc_reciept}' GROUP BY dc_no,operation ".format(dc_reciept=self.name)
		dc_nos = frappe.db.sql(dc_query,as_dict=1)
		for x in dc_nos:
			if frappe.db.get_all("Delivery Note Item",filters={"parent":x.dc_no,"parenttype":"Delivery Note","is_received":0}):
				frappe.db.set_value("Delivery Note",x.dc_no,"received_status","Partially Completed")
			else:
				frappe.db.set_value("Delivery Note",x.dc_no,"received_status","Completed")
		frappe.db.commit()

def update_stock_ref(doc_id,stock_id):
	""" Reference """
	store__val = ""
	exe_entries = frappe.db.get_value("Delivery Challan Receipt",doc_id,'stock_entry_reference')
	if exe_entries:
		exe_entries += "," + stock_id
		store__val += exe_entries
	else:
		store__val = stock_id
	frappe.db.set_value("Delivery Challan Receipt",doc_id,'stock_entry_reference',store__val)
	frappe.db.commit()
	""" End """

def update_workorder_ref(work_order,doctype,name):
	frappe.db.sql(f" UPDATE `tab{doctype}` SET work_order_ref='{work_order}' WHERE name='{name}' ")
	frappe.db.commit()

def rollback_wo_se_jc(info,msg):
	try:
		info.reload()
		if info.hld_items:
			for h_items in info.hld_items:
				if h_items.work_order_ref:
					stock__id = frappe.db.get_value("Stock Entry",{"work_order":h_items.work_order_ref},"name")
					frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock__id}' ")
					frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE work_order = '{h_items.work_order_ref}' ")
					frappe.db.sql(f" DELETE FROM `tabJob Card` WHERE work_order = '{h_items.work_order_ref}' ")
					frappe.db.sql(f" DELETE FROM `tabWork Order` WHERE name = '{h_items.work_order_ref}' ")
		if info.dc_items:
			for dc_items in info.dc_items:
				if dc_items.work_order_ref:
					stock__id = frappe.db.get_value("Stock Entry",{"work_order":dc_items.work_order_ref},"name")
					frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock__id}' ")
					frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE work_order = '{dc_items.work_order_ref}' ")
					frappe.db.sql(f" DELETE FROM `tabJob Card` WHERE work_order = '{dc_items.work_order_ref}' ")
					frappe.db.sql(f" DELETE FROM `tabWork Order` WHERE name = '{dc_items.work_order_ref}' ")
				if dc_items.dc_no:
					m_item = frappe.db.get_all("Delivery Note Item",filters={"parent":dc_items.dc_no,"parenttype":"Delivery Note","scan_barcode":dc_items.scan_barcode,"item_code":dc_items.item_code})
					if m_item:
						for x in m_item:
							frappe.db.set_value("Delivery Note Item",x.name,"is_received",0)
							frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_no","")
		if info.stock_entry_reference:
			for stock_id in info.stock_entry_reference.split(','):
				work__order = frappe.db.get_value("Stock Entry",{"name":stock_id},"work_order")
				frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock_id}' ")
				frappe.db.sql(f" DELETE FROM `tabStock Entry` WHERE name = '{stock_id}' ")
				frappe.db.sql(f" DELETE FROM `tabJob Card` WHERE work_order = '{work__order}' ")
				frappe.db.sql(f" DELETE FROM `tabWork Order` WHERE name = '{work__order}' ")
		bl_dc = frappe.get_doc(info.doctype, info.name)
		bl_dc.db_set("docstatus", 0)
		# bl_dc.db_set("stock_entry_reference", '')
		frappe.db.commit()
		info.reload()
		frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.delivery_challan_receipt.delivery_challan_receipt.rollback_wo_se_jc",message=frappe.get_traceback())
		bl_dc = frappe.get_doc(info.doctype, info.name)
		bl_dc.db_set("docstatus", 0)
		frappe.db.commit()
		info.reload()
		frappe.msgprint("Something went wrong , Not able to rollback changes..!")

def validate_final_batches(self):
	if self.inward_material_type == "Compound":
		batch_item_found = False
		for k in self.dc_items:
			if k.is_batch_item:
				batch_item_found = True
		if batch_item_found:
			grouped_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  parent = %(rc_id)s GROUP BY item_to_manufacture,operation """,{"rc_id":self.name},as_dict=1)
			if len(grouped_items) == 2 :
				for x in grouped_items:
					if x.operation != "Batching":
						if x.is_batch_item:
							wo,message = create_master_batch_stock(self,x)
							if wo:
								break
							else:
								rollback_wo_se_jc(self,message)
								return False
				for x in grouped_items:
					if x.operation != "Batching":
						if not x.is_batch_item:
							wo,message = create_compound_stock(self,x)
							if wo:
								break
							else:
								rollback_wo_se_jc(self,message)
								return False
			else:
				rollback_wo_se_jc(self,f"You can receive only one Batch & Final Batch Mixing at a time.")
			return False
		else:
			grouped_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  parent = %(rc_id)s GROUP BY item_to_manufacture,operation """,{"rc_id":self.name},as_dict=1)
			if len(grouped_items) == 1 :
				for x in grouped_items:
					bom_items = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":x.item_to_manufacture},as_dict=1)
					if len(bom_items)>1:
						manf_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabDC Item` WHERE  parent = %(rc_id)s AND item_to_manufacture=%(item_to_manufacture)s """,{"rc_id":self.name,"item_to_manufacture":x.item_to_manufacture},as_dict=1)
						if not len(manf_items) == len(bom_items):
							rollback_wo_se_jc(self,f"You can receive only one Master Batch & Final Batch Mixing at a time.")
							return False
				return True
			else:
				rollback_wo_se_jc(self,f"You can receive only one Master Batch & Final Batch Mixing at a time.")
				return False
	else:
		return True

@frappe.whitelist()
def get_batch_items(item_code,warehouse=None):
	try:
		""" Multi Bom Validation """
		bom__ = frappe.db.sql(""" SELECT B.name FROM `tabBOM` B WHERE B.item=%(item_code)s AND B.is_active=1 """,{"item_code":item_code},as_dict=1)
		if bom__ and len(bom__) > 1:
			return {"status":"failed","message":f"Multiple BOM's found for Item to Produce - {item_code}."}
		""" End """
		batch_items = []
		# bom_items = frappe.db.get_all("BOM Item",filters={"parent":item_code},fields=['item_code'])
		bom_items = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":item_code},as_dict=1)
		for x in bom_items:
			items = frappe.db.sql(""" SELECT SD.item_code,SB.qty,
										SD.spp_batch_number as spp_batch_no,SD.batch_no,
										SB.item_name,
										SD.mix_barcode as scan_barcode,SB.stock_uom as qty_uom
										FROM `tabItem Batch Stock Balance` SB 
										INNER JOIN `tabStock Entry Detail` SD ON SB.batch_no = SD.batch_no
										WHERE SD.item_code = %(bar_code)s and SB.warehouse=%(warehouse)s
										and SD.spp_batch_number IS NOT NULL GROUP BY SD.item_code,SB.qty,
										SD.spp_batch_number,SD.batch_no,
										SD.mix_barcode,SB.stock_uom
										ORDER BY SD.creation""",{"warehouse":warehouse,"bar_code":x.item_code},as_dict=1)
			for item in items:
				batch_items.append(item)
		return {"status":"failed","message":batch_items}
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.delivery_challan_receipt.delivery_challan_receipt.get_batch_items",message=frappe.get_traceback())
		return {"status":"failed","message":"something went wrong"}

@frappe.whitelist()
def validate_barcode(batch_no,warehouse=None,is_internal_mixing=0,batch_type=None):
	try:
		check_item_qty = None
		if cint(is_internal_mixing)==0: 
			check_item_qty = frappe.db.sql(""" SELECT SD.item_code,SB.qty,DC.name as dc_no,DC.operation,
											SD.spp_batch_number as spp_batch_no,SD.batch_no,
											SD.mix_barcode as scan_barcode,SB.stock_uom as qty_uom,
											SB.item_name,
											DC.set_target_warehouse as warehouse
											FROM `tabItem Batch Stock Balance` SB 
											INNER JOIN `tabStock Entry Detail` SD ON SB.batch_no = SD.batch_no
											INNER JOIN `tabDelivery Note Item` MI ON MI.scan_barcode=SD.mix_barcode
											INNER JOIN `tabDelivery Note` DC ON DC.name = MI.parent
				  								AND SB.warehouse = DC.set_target_warehouse
											WHERE SD.mix_barcode = %(bar_code)s AND SB.qty>0
											AND (MI.is_received=0 OR MI.is_received IS NULL) ORDER BY SD.creation DESC limit 1 """,{"warehouse":warehouse,"bar_code":batch_no},as_dict=1)
			# frappe.log_error(message=check_item_qty,title='check_item_qty--1--')
		if cint(is_internal_mixing)==0 and not check_item_qty:
			check_item_qty = frappe.db.sql(""" SELECT SD.item_code,SB.qty,'' as dc_no,'Mixing' as operation,
										SD.spp_batch_number as spp_batch_no,SD.batch_no,
										SD.mix_barcode as scan_barcode,SB.stock_uom as qty_uom,
											SB.item_name,
										SD.t_warehouse as warehouse
										FROM `tabItem Batch Stock Balance` SB 
										INNER JOIN `tabStock Entry Detail` SD ON SB.batch_no = SD.batch_no
											AND SB.warehouse = SD.t_warehouse
										WHERE SD.mix_barcode = %(bar_code)s AND SB.qty>0 AND SD.t_warehouse='U3-Store - SPP INDIA'
										ORDER BY SD.creation DESC limit 1""",{"warehouse":warehouse,"bar_code":batch_no},as_dict=1)
		if cint(is_internal_mixing)==0 and not check_item_qty:
			check_item_qty = frappe.db.sql(""" SELECT SD.item_code,SB.qty,'' as dc_no,'Kneader Mixing' as operation,
										SD.spp_batch_number as spp_batch_no,SD.batch_no,
										SD.mix_barcode as scan_barcode,SB.stock_uom as qty_uom,
											SB.item_name,
										SD.t_warehouse as warehouse
										FROM `tabItem Batch Stock Balance` SB 
										INNER JOIN `tabStock Entry Detail` SD ON SB.batch_no = SD.batch_no
											AND SB.warehouse = SD.t_warehouse
										WHERE SD.mix_barcode = %(bar_code)s AND SB.qty>0
										ORDER BY SD.creation DESC limit 1""",{"warehouse":warehouse,"bar_code":batch_no},as_dict=1)
		if check_item_qty:
			if check_item_qty[0].qty>0:
				bom  = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_active=1 AND B.is_default=1""",{"item_code":check_item_qty[0].item_code},as_dict=1)
				if bom:
					""" Multi Bom Validation """
					bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
					if len(bom__) > 1:
						return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - <b>{bom[0].item}</b>"}
					""" End """
					if batch_type:
						if batch_type == "Master Batch":
							it__gp = frappe.db.get_value('Item',bom[0].item,'item_group')
							if it__gp == batch_type:
								check_item_qty[0].bom_item = bom[0].item
							else:
								return {"status":"Failed","message":f"BOM Item - <b>{bom[0].item}</b> is not a <b>{batch_type}</b>..!"}
						elif batch_type == "Compound":
							it__gp = frappe.db.get_value('Item',bom[0].item,'item_group')
							if it__gp == "Compound" or it__gp == "Master Batch":
								check_item_qty[0].bom_item = bom[0].item
								if it__gp == "Master Batch":
									check_item_qty[0].is_batch_item = 1
							else:
								return {"status":"Failed","message":f"BOM Item - <b>{bom[0].item}</b> is not a <b>{batch_type}</b> or <b>Master Batch</b>..!"}
						else:
							check_item_qty[0].bom_item = bom[0].item
					else:
						check_item_qty[0].bom_item = bom[0].item
				else:
					return {"status":"Failed","message":"BOM is not found for Item to Produce"}
				return {"status":"Success","stock":check_item_qty}
		return {"status":"Failed","message":"No Stock Available."}
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.delivery_challan_receipt.delivery_challan_receipt.validate_barcode",message=frappe.get_traceback())	
		return {"status":"Failed","message":"Somthing Went Wrong."}

def update_job_cards(wo_name, actual_weight, employee, spp_settings):
    # 🎯 Debug 1: Initial parameters check
    print(f"\n🔥🔥🔥 DEBUG START [Work Order: {wo_name}] 🔥🔥🔥")
    print(f"🔸 SPP Settings WIP Warehouse: {getattr(spp_settings, 'wip_warehouse', 'NOT CONFIGURED!')}")
    print(f"🔸 Actual Weight: {actual_weight}, Employee: {employee}")

    job_cards = frappe.get_all("Job Card", filters={"work_order": wo_name})
    operations = frappe.get_all("Work Order Operation", filters={"parent": wo_name}, fields=["time_in_mins"])

    # 🎯 Debug 2: Job card status
    print(f"\n🔎 Found {len(job_cards)} Job Cards")
    print(f"🔹 Job Card IDs: {[jc['name'] for jc in job_cards]}")

    # 📦 Process each Job Card
    for job_card_dict in job_cards:
        jc = frappe.get_doc("Job Card", job_card_dict.name)
        
        # ⚠️ Mandatory: Create time logs if missing
        if not jc.time_logs:
            print(f"\n🚩 No Time Logs Found - Creating New Time Log")
            jc.append('time_logs', {
                'employee': employee,
                'completed_qty': actual_weight,
                'from_time': now(),
                'to_time': add_to_date(now(), minutes=0),
                'time_in_mins': 0
            })
            print("✅ Created new time log entry")

        # 🎯 Time Log Updates 
        print(f"\n⏳ Updating {len(jc.time_logs)} Time Log Entries")
        for idx, time_log in enumerate(jc.time_logs):
            print(f"🔧 Updating Time Log #{idx + 1}")
            time_log.employee = employee
            time_log.completed_qty = flt(actual_weight, precision=3)
            
            if operations:
                time_log.time_in_mins = 0
                time_log.from_time = now()
                time_log.to_time = add_to_date(now(), minutes=0)
                print(f"🕒 Reset timing for Operation #{idx + 1}")
            
            print(f"⏲️ Completed Qty: {time_log.completed_qty} | Employee: {time_log.employee}")

        # 🔄 WIP Warehouse Resolution
        print(f"\n🏗️ Checking WIP Warehouse for {jc.name}")
        if not jc.wip_warehouse:
            print("⚠️ Missing WIP - Starting resolution process")
            try:
                wo_doc = frappe.get_doc("Work Order", wo_name)
                if wo_doc and wo_doc.wip_warehouse:
                    jc.wip_warehouse = wo_doc.wip_warehouse
                    print(f"✅ Set WIP from Work Order: {jc.wip_warehouse}")
                else:
                    jc.wip_warehouse = spp_settings.wip_warehouse
                    print(f"✅ Fallback to SPP Settings: {jc.wip_warehouse}")
            except Exception as e:
                print(f"🚨 Error fetching Work Order: {str(e)}")
                frappe.log_error(title="WIP Resolution Error", message=f"{e}\n\n{jc.as_dict()}")

        # 🛡️ Pre-Save Validation
        print(f"\n📋 Validation Checks:")
        validation_errors = []
        
        if not jc.wip_warehouse:
            validation_errors.append("❌ Missing WIP Warehouse")
            
        if not jc.time_logs:
            validation_errors.append("❌ No Time Log Entries")
            
        if validation_errors:
            error_msg = " | ".join(validation_errors)
            frappe.throw(f"Job Card {jc.name} save blocked: {error_msg}")
            
        print("✅ All validations passed")

        # 💾 Save Attempt
        try:
            print(f"\n💾 Saving Job Card {jc.name}...")
            jc.total_completed_qty = flt(actual_weight, precision=3)
            jc.docstatus = 1
            jc.save(ignore_permissions=True)
            print(f"✅✅✅ Successfully saved {jc.name}")
        except Exception as e:
            print(f"\n❌❌❌ Critical Save Error:")
            print(f"🔴 Error Type: {type(e).__name__}")
            print(f"🔴 Error Message: {str(e)}")
            print(f"🔴 Current WIP: {jc.wip_warehouse}")
            print(f"🔴 Time Logs Count: {len(jc.time_logs) if jc.time_logs else 0}")
            
            frappe.log_error(
                title="Job Card Save Error",
                message=f"""Error saving {jc.name}:
                - WIP Warehouse: {jc.wip_warehouse}
                - Time Logs: {len(jc.time_logs)}
                - Error: {frappe.get_traceback()}"""
            )

@frappe.whitelist()
def create_wo(dc_rec):
	try:
		if dc_rec.hold_receipt == 0:
			dc_query ="SELECT name,dc_no,operation,item_to_manufacture FROM `tabDC Item` WHERE parent='{dc_reciept}' GROUP BY dc_no,operation,item_to_manufacture ".format(dc_reciept=dc_rec.name)
			dc_nos = frappe.db.sql(dc_query,as_dict=1)
			is_compound_created = 0 
			# frappe.log_error(title="--dc_nos--",message = dc_nos)
			for x in dc_nos:
				# frappe.log_error(title="--dc_no--",message = x)
				if frappe.db.get_value("Item",x.item_to_manufacture,"item_group") != "Compound":
				# if x.operation=="Batch" or x.operation=="Master Batch Mixing":
					spp_settings = frappe.get_single("SPP Settings")
					items = frappe.db.sql(""" SELECT name,item_code,scan_barcode,spp_batch_no,qty,batch_no,sum(qty) as qty FROM `tabDC Item` WHERE dc_no=%(parent_doc)s and parent=%(dc_reciept)s and item_to_manufacture=%(item_to_manufacture)s GROUP BY item_code,scan_barcode,spp_batch_no,batch_no""",{"parent_doc":x.dc_no,"dc_reciept":dc_rec.name,"item_to_manufacture":x.item_to_manufacture},as_dict=1)
					# frappe.log_error(title="--dcc items--",message = items)
					# dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE dc_no=%(parent_doc)s """,{"parent_doc":x.dc_no},as_dict=1)
					for w_item in items:
						bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":w_item.item_code},as_dict=1)
						if bom:
							""" Multi Bom Validation """
							bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
							if len(bom__) > 1:
								return False,f"Multiple BOM's found for Item to Produce - {bom[0].item}"
							""" End """
							actual_weight = w_item.qty
							work_station = None
							operation = "Batch"
							if x.operation=="Batch":
								work_station = "Rice Lake"
							if x.operation !="Batch":
								w_stations = frappe.db.get_all("Mixing Operation",filters={"warehouse":dc_rec.source_warehouse},fields=['operation','workstation'])
								if w_stations:
									work_station = w_stations[0].workstation
									operation = w_stations[0].operation
							import time
							wo = frappe.new_doc("Work Order")
							wo.naming_series = "MFG-WO-.YYYY.-"
							wo.company = "SPP"
							""" For c and cb items moved to incoming warehouse so updated as per arun instruction 18/05/23 """
							if w_item.item_code.lower().startswith("c") and spp_settings.cb_target_warehouse:
								wo.fg_warehouse = spp_settings.cb_target_warehouse	
							else:
								wo.fg_warehouse = spp_settings.target_warehouse
							""" end """
							wo.use_multi_level_bom = 0
							wo.skip_transfer = 1
							if dc_rec.is_internal_mixing == 0:
								wo.source_warehouse = dc_rec.source_warehouse
							wo.wip_warehouse = spp_settings.wip_warehouse
							wo.transfer_material_against = "Work Order"
							wo.bom_no = bom[0].name
							wo.append("operations",{
								"operation":operation,
								"bom":bom[0].name,
								"workstation":work_station,
								"time_in_mins":5,
								})
							wo.referenceid = round(time.time() * 1000)
							wo.production_item =bom[0].item
							wo.qty = w_item.qty
							wo.planned_start_date = getdate()
							wo.docstatus = 1
							try:
								wo.save(ignore_permissions=True)
								# frappe.log_error(title=f"--{wo.name}",message=wo.name)
								# frappe.log_error(title=f"--{w_item.batch_no}",message=w_item.batch_no)
								update_workorder_ref(wo.name,"DC Item",w_item.name)
								update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
								# if dc_rec.is_internal_mixing == 1:
								# 	se = make_internal_stock_entry(x,actual_weight,w_item.batch_no,w_item.spp_batch_no,w_item.scan_barcode,dc_rec,spp_settings,wo.name,w_item.item_code,"Manufacture")
								# else:
								se = make_stock_entry(x,actual_weight,w_item.batch_no,w_item.spp_batch_no,w_item.scan_barcode,dc_rec,spp_settings,wo.name,w_item.item_code,"Manufacture")
								if se and se.get('status') == "Failed":
									return False,se.get('message')
							except Exception as e:
								frappe.log_error(message=frappe.get_traceback(),title="create_wo")
								frappe.db.rollback()
								return False,"Work Order or Job Card update failed..!"
				else:
					if is_compound_created == 0:
						is_compound_created = 1
						grouped_items = frappe.db.sql(""" SELECT dc_no,operation,name,item_to_manufacture FROM `tabDC Item`  WHERE parent=%(dc_reciept)s GROUP BY item_to_manufacture """,{"dc_reciept":dc_rec.name},as_dict=1)
						for g_item in grouped_items:
							se = create_wo_final_batch_mixing(g_item.name,dc_rec,g_item.item_to_manufacture,g_item.operation)
							if se and se.get('status') == "Failed":
								return False,se.get('message')
		else:
			status,message = create_hold_wos(dc_rec)
			if not status:
				return status,message
		return True,""
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="create_wo")
		return False,"Work Order or Job Card update failed..!"
	
def make_stock_entry(w_item,sp_item_qty,sp_item_batch_no,sp_item_spp_batch_no,sp_item_scan_barcode,mt_doc,spp_settings,work_order_id,compound_code, purpose, qty=None):
	try:
		naming_flag = True
		# items = frappe.db.sql(""" SELECT item_code,scan_barcode,spp_batch_no,qty,batch_no FROM `tabDC Item` WHERE parent=%(parent_doc)s and dc_no=%(dc_no)s GROUP BY item_code,scan_barcode,spp_batch_no,qty""",{"parent_doc":mt_doc.name,"dc_no":w_item.dc_no},as_dict=1)
		# frappe.log_error(work_order_id,'work_order_id')
		dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  dc_no=%(parent_doc)s and parent=%(dc_rec)s """,{"parent_doc":w_item.dc_no,'dc_rec':mt_doc.name},as_dict=1)
		# for sp_item in items:
		work_order = frappe.get_doc("Work Order", work_order_id)
		if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
			wip_warehouse = work_order.wip_warehouse
		else:
			wip_warehouse = None
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = purpose
		stock_entry.work_order = work_order_id
		stock_entry.company = work_order.company
		stock_entry.from_bom = 1
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.bom_no = work_order.bom_no
		stock_entry.set_posting_time = 0
		stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
		stock_entry.stock_entry_type = "Manufacture"
		# accept 0 qty as well
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.remarks = w_item.dc_no
		for x in work_order.required_items:
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":sp_item_qty,
				"use_serial_batch_fields":1,
				"qty":sp_item_qty,
				"batch_no":sp_item_batch_no,
				"spp_batch_number":None,
				"mix_barcode":None,
				})
			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1  """,{"item_code":x.item_code},as_dict=1)
			if bom:
				""" Multi Bom Validation """
				bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
				if len(bom__) > 1:
					return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - {bom[0].item}"}
				""" End """
				""" For identifying procees name to change the naming series the field is used """
				if naming_flag:
					naming_flag = False
					item_group = frappe.db.get_value("Item",bom[0].item,"item_group")
					if item_group != "Compound":
						naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (FB and MB) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (FB and MB) For External Mixing")
						if naming_status:
							stock_entry.naming_series = naming_series
					elif item_group == "Compound":
						naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (C) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (C) For External Mixing")
						if naming_status:
							stock_entry.naming_series = naming_series
				""" End """
		is_compound = 0
		bcode_resp = generate_barcode(sp_item_scan_barcode)
		stock_entry.append("items",{
			"item_code":bom[0].item,
			"s_warehouse":None,
			"t_warehouse":work_order.fg_warehouse,
			"stock_uom": "Kg",
			"uom": "Kg",
			"conversion_factor_uom":1,
			"is_finished_item":1,
			"transfer_qty":sp_item_qty,
			"qty":sp_item_qty,
			"use_serial_batch_fields":1,
			"spp_batch_number":sp_item_spp_batch_no,
			# "mix_barcode":sp_item_scan_barcode,
			"mix_barcode":bcode_resp.get("barcode_text"),
			"is_compound":is_compound,
			"barcode_attach":bcode_resp.get("barcode"),
			"barcode_text":bcode_resp.get("barcode_text"),
			"source_ref_document":mt_doc.doctype,
			"source_ref_id":mt_doc.name
			})
		# if spp_settings.auto_submit_stock_entries:		
		stock_entry.insert(ignore_permissions=True)
		update_stock_ref(mt_doc.name,stock_entry.name)
		# frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
		# frappe.db.commit()
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save(ignore_permissions=True)
		""" Update creation date"""
		if mt_doc.dc_receipt_date:
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}' WHERE name = '{st_entry.name}' ")
			""" End """
			# frappe.db.sql(f" UPDATE `tabStock Entry` SET creation = '{mt_doc.dc_receipt_date } { now().split(' ')[1]}' WHERE name = '{st_entry.name}' ")
		""" End """
		for dc_item in dc_items:
			m_item = frappe.db.get_all("Delivery Note Item",filters={"parent":w_item.dc_no,"parenttype":"Delivery Note","scan_barcode":dc_item.scan_barcode,"item_code":dc_item.item_code})
			if m_item:
				for x in m_item:
					frappe.db.set_value("Delivery Note Item",x.name,"is_received",1)
					frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_no",mt_doc.name)
					frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_date",(getdate() if not mt_doc.dc_receipt_date else mt_doc.dc_receipt_date))
		frappe.db.commit()
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Stock Entry Error")
		frappe.db.rollback()
		return {"status":"Failed","message":"Stock Entry creation failed...!"}

@frappe.whitelist()
def create_wo_final_batch_mixing(child_name,mt_doc,item_code,operation):
	try:
		bom_resp,fn_resp,msg = validate_bom_items(mt_doc,item_code)
		if not fn_resp:
			if bom_resp:
				spp_settings = frappe.get_single("SPP Settings")
				dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE parent=%(parent_doc)s  AND item_to_manufacture=%(item_code)s """,{"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
				bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
				if bom:
					""" Multi Bom Validation """
					bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
					if len(bom__) > 1:
						return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - {bom[0].item}."}
					""" End """
					actual_weight = sum(flt(e_item.qty) for e_item in dc_items)
					# frappe.log_error(actual_weight,'actual_weight')
					work_station = "Two Roll Mixing Mill"
					w_stations = frappe.db.get_all("Mixing Operation",filters={"warehouse":mt_doc.source_warehouse},fields=['operation','workstation'])
					if w_stations:
						work_station = w_stations[0].workstation
						operation = w_stations[0].operation
						# if mt_doc.source_warehouse == "U3-Store - SPP INDIA":
						# 	work_station = "Two Roll Mixing Mill"
						# if mt_doc.source_warehouse != "U3-Store - SPP INDIA":
						# 	work_station= "Avon Kneader"
					import time
					wo = frappe.new_doc("Work Order")
					wo.naming_series = "MFG-WO-.YYYY.-"
					wo.company = "SPP"
					wo.fg_warehouse = spp_settings.target_warehouse
					wo.use_multi_level_bom = 0
					wo.skip_transfer = 1
					wo.source_warehouse = mt_doc.source_warehouse
					wo.wip_warehouse = spp_settings.wip_warehouse
					wo.transfer_material_against = "Work Order"
					wo.bom_no = bom[0].name
					wo.append("operations",{
						"operation":operation,
						"bom":bom[0].name,
						"workstation":work_station,
						"time_in_mins":20,
						})
					wo.referenceid = round(time.time() * 1000)
					wo.production_item =bom[0].item
					wo.qty = actual_weight
					wo.planned_start_date = getdate()
					wo.docstatus = 1
					try:
						wo.save(ignore_permissions=True)
						update_workorder_ref(wo.name,"DC Item",child_name)
						update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
						se = make_stock_entry_final_batch(mt_doc,item_code,spp_settings,wo.name,"Manufacture")
						if se and se.get('status') == "Failed":
							return {"status":se.get('status'),"message":se.get('message')}
						return se
					except Exception as e:
						frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Error")
						frappe.db.rollback()
						# frappe.throw(e)
						return {"status":"Failed","message":"Work Order or Job Card update failed..!"}
			else:
				return {"status":"Failed","message":"BOM is not matched with items"}
		else:
			return {"status":"Failed","message":msg}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="create_wo_final_batch_mixing")
		return {"status":"Failed","message":"Work Order or Job Card update failed..!"}

def rollback_transaction():
	frappe.db.rollback()

def validate_bom_items(mt_doc,item_code):
	try:
		# dc_items = mt_doc.batches
		dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  parent=%(parent_doc)s  AND item_to_manufacture=%(item_code)s """,{"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
		# if mt_doc.is_internal_mixing:
		# 	bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE   B.is_active=1 AND B.item=%(manufacturer_item)s""",{"manufacturer_item":item_code},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return "",True,f"Multiple BOM's found for Item to Produce - {bom[0].item}."
			""" End """
			bom_items = frappe.db.get_all("BOM Item",filters={"parent":bom[0].name},fields=['item_code'])
			d_items = []
			for x in dc_items:
				d_items.append(x.item_code)
			for x in bom_items:
				if not x.item_code in d_items:
					return False,False,""
		return True,False,""
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="validate_bom_items")
		return "",True,"Validate BOM items failed...!"
		
def make_stock_entry_final_batch(mt_doc,item_code,spp_settings,work_order_id,purpose):
	try:
		naming_flag = True
		st_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE parent=%(parent_doc)s  AND item_to_manufacture=%(item_code)s""",{"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
		work_order = frappe.get_doc("Work Order", work_order_id)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = purpose
		stock_entry.work_order = work_order_id
		stock_entry.company = work_order.company
		stock_entry.from_bom = 1
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.bom_no = work_order.bom_no
		stock_entry.use_multi_level_bom = 0
		stock_entry.set_posting_time = 0
		stock_entry.stock_entry_type = "Manufacture"
		# accept 0 qty as well
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		dc_nos = ""
		for dc__n in mt_doc.dc_items:
			dc_nos += dc__n.dc_no if dc__n.dc_no else ""
		stock_entry.remarks = dc_nos
		for x in st_items:
			sp_item_batch_no = None
			batch_nos = frappe.db.get_all("DC Item",filters={"parent":mt_doc.name,"item_code":x.item_code},fields=['batch_no'])
			if batch_nos:
				sp_item_batch_no = batch_nos[0].batch_no
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"use_serial_batch_fields":1,
				"transfer_qty":x.qty,
				"qty":x.qty,
				"spp_batch_number":None,
				"batch_no":sp_item_batch_no,
				"mix_barcode":"",
				})
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - {bom[0].item}"}
			""" End """
			""" For identifying procees name to change the naming series the field is used """
			if naming_flag:
				naming_flag = False
				item_group = frappe.db.get_value("Item",bom[0].item,"item_group")
				if item_group != "Compound":
					naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (FB and MB) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (FB and MB) For External Mixing")
					if naming_status:
						stock_entry.naming_series = naming_series
				elif item_group == "Compound":
					naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (C) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (C) For External Mixing")
					if naming_status:
						stock_entry.naming_series = naming_series
			""" End """
			d_spp_batch_no = get_spp_batch_date(bom[0].item)
			bcode_resp = generate_barcode("C_"+d_spp_batch_no)
			stock_entry.append("items",{
				"item_code":bom[0].item,
				"s_warehouse":None,
				"t_warehouse":work_order.fg_warehouse,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":1,
				"transfer_qty":work_order.qty,
				"qty":work_order.qty,
				"use_serial_batch_fields":1,
				"spp_batch_number":d_spp_batch_no,
				# "mix_barcode":bom[0].item+"_"+d_spp_batch_no,
				"mix_barcode":bcode_resp.get("barcode_text"),
				"is_compound":1,
				"barcode_attach":bcode_resp.get("barcode"),
				"barcode_text":bcode_resp.get("barcode_text"),
				"source_ref_document":mt_doc.doctype,
				"source_ref_id":mt_doc.name
				})
		stock_entry.insert(ignore_permissions=True)
		update_stock_ref(mt_doc.name,stock_entry.name)
		# Temporarly enabled as per arun req on 8/2/23
		# st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		# st_entry.docstatus=1
		# st_entry.save(ignore_permissions=True)
		if mt_doc.dc_receipt_date and mt_doc.mixing_time:
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}',posting_time = '{mt_doc.mixing_time}' WHERE name = '{stock_entry.name}' ")
			""" End """
		elif mt_doc.dc_receipt_date :
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}' WHERE name = '{stock_entry.name}' ")
		# End
		update_receive_status(mt_doc)
		if bom:
			serial_no = 1
			serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
			if serial_nos:
				serial_no = serial_nos[0].serial_no+1
			sl_no = frappe.new_doc("SPP Batch Serial")
			sl_no.posted_date = getdate()
			sl_no.compound_code = bom[0].item
			sl_no.serial_no = serial_no
			sl_no.insert(ignore_permissions = True)
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Error.!")
		frappe.db.rollback()
		return {"status":"Failed","message":"Stock Entry Creation Failed..!"}

def update_receive_status(mt_doc):
	for x in mt_doc.dc_items:
		m_item = frappe.db.get_all("Delivery Note Item",filters={"parent":x.dc_no,"parenttype":"Delivery Note","item_code":x.item_code,"scan_barcode":x.scan_barcode})
		if m_item:
			for x in m_item:
				frappe.db.set_value("Delivery Note Item",x.name,"is_received",1)
				frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_no",mt_doc.name)
				frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_date",(getdate() if not mt_doc.dc_receipt_date else mt_doc.dc_receipt_date))
			frappe.db.commit()

def create_hold_wos(dc_rec):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		items  = frappe.db.get_all("Mixing Center Holding Item",filters={"parent":dc_rec.name},fields=['*'])
		for w_item in items:
			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":w_item.item_code},as_dict=1)
			if bom:
				""" Multi Bom Validation """
				bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
				if len(bom__) > 1:
					return False,f"Multiple BOM's found for Item to Produce - {bom[0].item}"
				""" End """
				actual_weight = w_item.qty
				work_station = None
				operation = "Mixing"
				w_stations = frappe.db.get_all("Mixing Operation",filters={"warehouse":dc_rec.hld_warehouse},fields=['operation','workstation'])
				if w_stations:
					work_station = w_stations[0].workstation
					operation = w_stations[0].operation
				import time
				wo = frappe.new_doc("Work Order")
				wo.naming_series = "MFG-WO-.YYYY.-"
				wo.company = "SPP"
				wo.fg_warehouse = dc_rec.hld_warehouse
				wo.use_multi_level_bom = 0
				wo.skip_transfer = 1
				if dc_rec.is_internal_mixing == 0:
					wo.source_warehouse = dc_rec.hld_warehouse
				wo.wip_warehouse = spp_settings.wip_warehouse
				wo.transfer_material_against = "Work Order"
				wo.bom_no = bom[0].name
				wo.append("operations",{
					"operation":operation,
					"bom":bom[0].name,
					"workstation":work_station,
					"time_in_mins":5,
					})
				wo.referenceid = round(time.time() * 1000)
				wo.production_item =bom[0].item
				wo.qty = w_item.qty
				wo.planned_start_date = getdate()
				wo.docstatus = 1
				try:
					wo.save(ignore_permissions=True)
					update_workorder_ref(wo.name,"Mixing Center Holding Item",w_item.name)
					update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
					# if dc_rec.is_internal_mixing == 1:
					# 	se = make_internal_stock_entry(x,actual_weight,w_item.batch_no,w_item.spp_batch_no,w_item.scan_barcode,dc_rec,spp_settings,wo.name,w_item.item_code,"Manufacture")
					# else:
					se = make_hold_stock_entry(w_item,actual_weight,w_item.batch_no,w_item.spp_batch_no,w_item.mix_barcode,dc_rec,spp_settings,wo.name,w_item.item_code,"Manufacture")
					if se and se.get('status') == "Failed":
						return False,se.get('message')
				except Exception as e:
					frappe.log_error(message=frappe.get_traceback(),title="create_hold_wos")
					frappe.db.rollback()
					return False,"Work Order or Job Card update failed..!"
		# update_over_all_dn_status(dc_rec,"Hold")
		return True,''
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="create_hold_wos")
		return False,"Work Order or Job Card update failed..!"

def make_hold_stock_entry(w_item,sp_item_qty,sp_item_batch_no,sp_item_spp_batch_no,sp_item_scan_barcode,mt_doc,spp_settings,work_order_id,compound_code, purpose, qty=None):
	try:
		naming_flag = True
		work_order = frappe.get_doc("Work Order", work_order_id)
		if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
			wip_warehouse = work_order.wip_warehouse
		else:
			wip_warehouse = None
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = purpose
		stock_entry.work_order = work_order_id
		stock_entry.company = work_order.company
		stock_entry.from_bom = 1
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.bom_no = work_order.bom_no
		stock_entry.set_posting_time = 0
		stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
		stock_entry.stock_entry_type = "Manufacture"
		# accept 0 qty as well
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.remarks = "hold"
		for x in work_order.required_items:
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"use_serial_batch_fields":1,
				"transfer_qty":sp_item_qty,
				"qty":sp_item_qty,
				"batch_no":sp_item_batch_no,
				"spp_batch_number":None,
				"mix_barcode":None,
				})
			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1  """,{"item_code":x.item_code},as_dict=1)
			if bom:
				""" Multi Bom Validation """
				bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
				if len(bom__) > 1:
					return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - {bom[0].item}"}
				""" End """
				""" For identifying procees name to change the naming series the field is used """
				if naming_flag:
					naming_flag = False
					item_group = frappe.db.get_value("Item",bom[0].item,"item_group")
					if item_group != "Compound":
						naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (FB and MB) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (FB and MB) For External Mixing")
						if naming_status:
							stock_entry.naming_series = naming_series
					elif item_group == "Compound":
						naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (C) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (C) For External Mixing")
						if naming_status:
							stock_entry.naming_series = naming_series
				""" End """
				stock_entry.append("items",{
					"item_code":bom[0].item,
					"s_warehouse":None,
					"t_warehouse":work_order.fg_warehouse,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":1,
					"use_serial_batch_fields":1,
					"transfer_qty":sp_item_qty,
					"qty":sp_item_qty,
					"spp_batch_number":sp_item_spp_batch_no,
					"mix_barcode":sp_item_scan_barcode,
					"source_ref_document":mt_doc.doctype,
					"source_ref_id":mt_doc.name
					})
		stock_entry.insert(ignore_permissions=True)
		update_stock_ref(mt_doc.name,stock_entry.name)
		# frappe.db.set_value(mt_doc.doctype,mt_doc.name,"stock_entry_reference",stock_entry.name)
		# frappe.db.commit()
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save(ignore_permissions=True)
		""" Update creation date"""
		if mt_doc.dc_receipt_date:
			if mt_doc.dc_receipt_date:
				""" Update posting date and time """
				frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}' WHERE name = '{st_entry.name}' ")
				""" End """
			# frappe.db.sql(f" UPDATE `tabStock Entry` SET creation = '{mt_doc.dc_receipt_date } { now().split(' ')[1]}' WHERE name = '{st_entry.name}' ")
		""" End """
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Stock Entry Error")
		frappe.db.rollback()
		return {"status":"Failed","message":"Stock Entry creation error..!"}

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
def filter_get_vendors(doctype, txt, searchfield, start, page_len, filters):
	search_condition = ""
	if txt:
		search_condition = " AND name like '%"+txt+"%'"
	query = " SELECT name FROM `tabWarehouse` WHERE disabled = 0  AND (parent_warehouse = 'Mixing Centers - SPP INDIA' OR name = 'Mixing Centers - SPP INDIA' OR name = 'U3-Store - SPP INDIA' ) {condition} ORDER BY modified DESC ".format(condition=search_condition)
	linked_docs = frappe.db.sql(query)
	return linked_docs

def create_master_batch_stock(self,x):
	try:
		status,message = create_mb_wo(self,x)
		if not status:
			return status,message
		return True,""
	except Exception:
		frappe.log_error(title="error in create_master_batch_stock",message = frappe.get_traceback())
		return False,"Mater Batch Work Order or Job Card update failed..!"
		
def create_mb_wo(dc_rec,w_item):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":w_item.item_code},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return False,f"Multiple BOM's found for Item to Produce - {bom[0].item}"
			""" End """
			actual_weight = w_item.qty
			work_station = None
			operation = "Mixing"
			w_stations = frappe.db.get_all("Mixing Operation",filters={"warehouse":dc_rec.source_warehouse},fields=['operation','workstation'])
			if w_stations:
				work_station = w_stations[0].workstation
				operation = w_stations[0].operation
			import time
			wo = frappe.new_doc("Work Order")
			wo.naming_series = "MFG-WO-.YYYY.-"
			wo.company = "SPP"
			wo.fg_warehouse = dc_rec.source_warehouse
			wo.use_multi_level_bom = 0
			wo.skip_transfer = 1
			if dc_rec.is_internal_mixing == 0:
				wo.source_warehouse = dc_rec.source_warehouse
			wo.wip_warehouse = spp_settings.wip_warehouse
			wo.transfer_material_against = "Work Order"
			wo.bom_no = bom[0].name
			wo.append("operations",{
				"operation":operation,
				"bom":bom[0].name,
				"workstation":work_station,
				"time_in_mins":5,
				})
			wo.referenceid = round(time.time() * 1000)
			wo.production_item =bom[0].item
			wo.qty = w_item.qty
			wo.planned_start_date = getdate()
			wo.docstatus = 1
			try:
				wo.save(ignore_permissions=True)
				update_workorder_ref(wo.name,"DC Item",w_item.name)
				update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
				se = make_mb_stock_entry(actual_weight,w_item.batch_no,w_item.spp_batch_no,w_item.scan_barcode,dc_rec,spp_settings,wo.name,"Manufacture",w_item)
				if se and se.get('status') == "Failed":
					return False,se.get('message')
			except Exception as e:
				frappe.log_error(message=frappe.get_traceback(),title="create_mb_wo")
				frappe.db.rollback()
				return False,"Mater Batch  Work Order or Job Card update failed..!"
		return True,''
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="create_mb_wo")
		return False,"Mater Batch Work Order or Job Card update failed..!"

def make_mb_stock_entry(sp_item_qty,sp_item_batch_no,sp_item_spp_batch_no,sp_item_scan_barcode,mt_doc,spp_settings,work_order_id, purpose,w_item):
	try:
		naming_flag = True
		work_order = frappe.get_doc("Work Order", work_order_id)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = purpose
		stock_entry.work_order = work_order_id
		stock_entry.company = work_order.company
		stock_entry.from_bom = 1
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.bom_no = work_order.bom_no
		stock_entry.set_posting_time = 0
		stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
		stock_entry.stock_entry_type = "Manufacture"
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.remarks = "hold"
		for x in work_order.required_items:
			stock_entry.append("items",{
				"item_code":x.item_code,
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":sp_item_qty,
				"qty":sp_item_qty,
				"batch_no":sp_item_batch_no,
				"spp_batch_number":None,
				"mix_barcode":None,
				})
			bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code=%(item_code)s AND B.is_default=1 AND B.is_active=1  """,{"item_code":x.item_code},as_dict=1)
			if bom:
				""" Multi Bom Validation """
				bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
				if len(bom__) > 1:
					return {"status":"Failed","message":f"Multiple BOM's found for Item to Produce - {bom[0].item}"}
				""" End """
				""" For identifying procees name to change the naming series the field is used """
				if naming_flag:
					naming_flag = False
					item_group = frappe.db.get_value("Item",bom[0].item,"item_group")
					if item_group != "Compound":
						naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (FB and MB) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (FB and MB) For External Mixing")
						if naming_status:
							stock_entry.naming_series = naming_series
					elif item_group == "Compound":
						naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (C) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (C) For External Mixing")
						if naming_status:
							stock_entry.naming_series = naming_series
				""" End """
				stock_entry.append("items",{
					"item_code":bom[0].item,
					"s_warehouse":None,
					"t_warehouse":work_order.fg_warehouse,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":1,
					"transfer_qty":sp_item_qty,
					"qty":sp_item_qty,
					"spp_batch_number":sp_item_spp_batch_no,
					"mix_barcode":sp_item_scan_barcode,
					"source_ref_document":mt_doc.doctype,
					"source_ref_id":mt_doc.name
					})
		stock_entry.insert(ignore_permissions = True)
		update_stock_ref(mt_doc.name,stock_entry.name)
		st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		st_entry.docstatus=1
		st_entry.save(ignore_permissions=True)
		""" Update creation date"""
		if mt_doc.dc_receipt_date:
			if mt_doc.dc_receipt_date:
				""" Update posting date and time """
				frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}' WHERE name = '{st_entry.name}' ")
				""" End """
		""" End """
		update_master_batch_details(stock_entry,mt_doc,w_item)
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Mater Batch DC Receipt Stock Entry Error")
		frappe.db.rollback()
		return {"status":"Failed","message":"Mater Batch  Stock Entry creation error..!"}

def update_master_batch_details(stock_entry,mt_doc,w_item):
	exe_info = frappe.db.sql(f""" SELECT batch_no,spp_batch_number,mix_barcode,t_warehouse,item_code
			  						FROM `tabStock Entry Detail` WHERE parent = '{stock_entry.name}'
									  AND t_warehouse IS NOT NULL AND t_warehouse != ''  """,as_dict = 1)
	if exe_info:
		w_item.mb_batch_code = exe_info[0].batch_no
		w_item.mb_item_code = exe_info[0].item_code
		w_item.mb_warehouse = exe_info[0].t_warehouse
		frappe.db.sql(f"""  UPDATE `tabDC Item` SET mb_batch_code = '{exe_info[0].batch_no}',
								mb_item_code = '{exe_info[0].item_code}',mb_warehouse = '{exe_info[0].t_warehouse}'
							WHERE name = '{w_item.name}' """)
		frappe.db.commit()
		bom_items = frappe.db.sql(""" SELECT B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE BI.item_code = %(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":exe_info[0].item_code},as_dict=1)
		if bom_items:
			for k in mt_doc.dc_items:
				if not k.is_batch_item:
					if k.item_to_manufacture == bom_items[0].item:
						frappe.db.sql(f"""  UPDATE `tabDC Item` SET mb_item_to_manufacture = '{bom_items[0].item}'
							WHERE parent = '{mt_doc.name}' """)
						frappe.db.commit()
					else:
						frappe.throw(f"The Master batch compound - {bom_items[0].item} is differ from final batch compound - {k.item_to_manufacture}..!")
		else:
			frappe.throw(f'Master Batch <b>BOM</b> is not found..!')
	else:
		frappe.throw(f'Master Batch stock details not found..!')

def create_compound_stock(self,x):
	try:
		dc_query =" SELECT * FROM `tabDC Item` WHERE parent='{dc_reciept}' ".format(dc_reciept=self.name)
		dc_nos = frappe.db.sql(dc_query,as_dict=1)
		if dc_nos:
			se = create_wo_c(dc_nos[0].name,self,dc_nos[0].mb_item_to_manufacture,dc_nos,dc_nos[0].operation)
			if se and se.get('status') == "Failed":
				return False,se.get('message')
		else:
			return False,"DC Item details is not found..!"
		return True,""
	except Exception:
		frappe.log_error(title="error in create_compound_stock",message = frappe.get_traceback())
		return False,"Compound Work Order or Job Card update failed..!"

def validate_bom_items_c(mt_doc,item_code):
	try:
		dc_items = frappe.db.sql(""" SELECT * FROM `tabDC Item` WHERE  parent=%(parent_doc)s  AND mb_item_to_manufacture=%(item_code)s """,{"parent_doc":mt_doc.name,'item_code':item_code},as_dict=1)
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
		if bom:
			""" Multi Bom Validation """
			bom__ = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM` B WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":bom[0].item},as_dict=1)
			if len(bom__) > 1:
				return "",True,f"Multiple BOM's found for Item to Produce - {bom[0].item}."
			""" End """
			bom_items = frappe.db.get_all("BOM Item",filters={"parent":bom[0].name},fields=['item_code'])
			d_items = []
			for x in dc_items:
				if x.is_batch_item:
					d_items.append(x.mb_item_code)
				else:
					d_items.append(x.item_code)
			for x in bom_items:
				if not x.item_code in d_items:
					return False,False,""
		return True,False,""
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="validate_bom_items_c")
		return "",True,"Validate BOM items failed...!"

@frappe.whitelist()
def create_wo_c(child_name,mt_doc,item_code,dc_nos,operation):
	try:
		bom_resp,fn_resp,msg = validate_bom_items_c(mt_doc,item_code)
		if not fn_resp:
			if bom_resp:
				bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
				spp_settings = frappe.get_single("SPP Settings")
				actual_weight = sum(flt(e_item.qty) for e_item in dc_nos)
				work_station = "Two Roll Mixing Mill"
				w_stations = frappe.db.get_all("Mixing Operation",filters={"warehouse":mt_doc.source_warehouse},fields=['operation','workstation'])
				if w_stations:
					work_station = w_stations[0].workstation
					operation = w_stations[0].operation
				import time
				wo = frappe.new_doc("Work Order")
				wo.naming_series = "MFG-WO-.YYYY.-"
				wo.company = "SPP"
				wo.fg_warehouse = spp_settings.target_warehouse
				wo.use_multi_level_bom = 0
				wo.skip_transfer = 1
				wo.source_warehouse = mt_doc.source_warehouse
				wo.wip_warehouse = spp_settings.wip_warehouse
				wo.transfer_material_against = "Work Order"
				wo.bom_no = bom[0].name
				wo.append("operations",{
					"operation":operation,
					"bom":bom[0].name,
					"workstation":work_station,
					"time_in_mins":20,
					})
				wo.referenceid = round(time.time() * 1000)
				wo.production_item =bom[0].item
				wo.qty = actual_weight
				wo.planned_start_date = getdate()
				wo.docstatus = 1
				try:
					wo.save(ignore_permissions=True)
					update_workorder_ref(wo.name,"DC Item",child_name)
					update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
					se = make_stock_entry_c(mt_doc,item_code,dc_nos,spp_settings,wo.name,"Manufacture")
					if se and se.get('status') == "Failed":
						return {"status":se.get('status'),"message":se.get('message')}
					return se
				except Exception as e:
					frappe.log_error(message=frappe.get_traceback(),title="DC Receipt Error")
					frappe.db.rollback()
					return {"status":"Failed","message":"Compound Work Order or Job Card update failed..!"}
			else:
				return {"status":"Failed","message":"BOM is not matched with items"}
		else:
			return {"status":"Failed","message":msg}
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="create_wo_create_wo_c")
		return {"status":"Failed","message":"Compound Work Order or Job Card update failed..!"}
			
def make_stock_entry_c(mt_doc,item_code,dc_nos,spp_settings,work_order_id,purpose):
	try:
		naming_flag = True
		work_order = frappe.get_doc("Work Order", work_order_id)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = purpose
		stock_entry.work_order = work_order_id
		stock_entry.company = work_order.company
		stock_entry.from_bom = 1
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		stock_entry.bom_no = work_order.bom_no
		stock_entry.use_multi_level_bom = 0
		stock_entry.set_posting_time = 0
		stock_entry.stock_entry_type = "Manufacture"
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		dc_nos_ = ""
		for dc__n in mt_doc.dc_items:
			dc_nos_ += dc__n.dc_no if dc__n.dc_no else ""
		stock_entry.remarks = dc_nos_
		for x in mt_doc.dc_items:
			stock_entry.append("items",{
				"item_code":x.item_code if not x.is_batch_item else frappe.db.get_value(x.doctype,x.name,"mb_item_code"),
				"s_warehouse":work_order.source_warehouse,
				"t_warehouse":None,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":0,
				"transfer_qty":x.qty,
				"qty":x.qty,
				"spp_batch_number":None,
				"batch_no":x.batch_no if not x.is_batch_item else frappe.db.get_value(x.doctype,x.name,"mb_batch_code"),
				"mix_barcode":"",
				})
		bom = frappe.db.sql(""" SELECT B.name,B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_active=1""",{"item_code":item_code},as_dict=1)
		if bom:
			""" For identifying procees name to change the naming series the field is used """
			if naming_flag:
				naming_flag = False
				item_group = frappe.db.get_value("Item",bom[0].item,"item_group")
				if item_group != "Compound":
					naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (FB and MB) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (FB and MB) For External Mixing")
					if naming_status:
						stock_entry.naming_series = naming_series
				elif item_group == "Compound":
					naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"DC Receipt (C) For Internal Mixing" if mt_doc.is_internal_mixing else "DC Receipt (C) For External Mixing")
					if naming_status:
						stock_entry.naming_series = naming_series
			""" End """
			d_spp_batch_no = get_spp_batch_date(bom[0].item)
			bcode_resp = generate_barcode("C_"+d_spp_batch_no)
			stock_entry.append("items",{
				"item_code":bom[0].item,
				"s_warehouse":None,
				"t_warehouse":work_order.fg_warehouse,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"is_finished_item":1,
				"transfer_qty":work_order.qty,
				"qty":work_order.qty,
				"spp_batch_number":d_spp_batch_no,
				# "mix_barcode":bom[0].item+"_"+d_spp_batch_no,
				"mix_barcode":bcode_resp.get("barcode_text"),
				"is_compound":1,
				"barcode_attach":bcode_resp.get("barcode"),
				"barcode_text":bcode_resp.get("barcode_text"),
				"source_ref_document":mt_doc.doctype,
				"source_ref_id":mt_doc.name
				})
		stock_entry.insert(ignore_permissions = True)
		# Temporarly enabled as per arun req on 8/2/23
		# st_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		# st_entry.docstatus=1
		# st_entry.save(ignore_permissions=True)
		if mt_doc.dc_receipt_date and mt_doc.mixing_time:
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}',posting_time = '{mt_doc.mixing_time}' WHERE name = '{stock_entry.name}' ")
			""" End """
		elif mt_doc.dc_receipt_date :
			frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{mt_doc.dc_receipt_date}' WHERE name = '{stock_entry.name}' ")
		# End
		update_receive_status_c(mt_doc,dc_nos)
		update_stock_ref(mt_doc.name,stock_entry.name)
		if bom:
			serial_no = 1
			serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
			if serial_nos:
				serial_no = serial_nos[0].serial_no+1
			sl_no = frappe.new_doc("SPP Batch Serial")
			sl_no.posted_date = getdate()
			sl_no.compound_code = bom[0].item
			sl_no.serial_no = serial_no
			sl_no.insert(ignore_permissions=True)
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Compound DC Receipt Error.!")
		frappe.db.rollback()
		return {"status":"Failed","message":"Stock Entry Creation Failed..!"}

def update_receive_status_c(mt_doc,dc_nos):
	for x in mt_doc.dc_items:
		m_item = frappe.db.get_all("Delivery Note Item",filters={"parent":x.dc_no,"parenttype":"Delivery Note","item_code":x.item_code,"scan_barcode":x.scan_barcode})
		if m_item:
			for x in m_item:
				frappe.db.set_value("Delivery Note Item",x.name,"is_received",1)
				frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_no",mt_doc.name)
				frappe.db.set_value("Delivery Note Item",x.name,"dc_receipt_date",(getdate() if not mt_doc.dc_receipt_date else mt_doc.dc_receipt_date))
			frappe.db.commit()
	update_over_all_dn_status(mt_doc,"Not Hold")





# def validate_final_batches(self):
# 	grouped_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabDC Item` WHERE  parent = %(rc_id)s GROUP BY item_to_manufacture,operation """,{"rc_id":self.name},as_dict=1)
# 	# if len(grouped_items)>1:
# 		# return False
# 	for x in grouped_items:
# 		if x.operation != "Batching":
# 			""" Multi Bom Validation """
# 			bom__ = frappe.db.sql(""" SELECT B.name FROM `tabBOM` B WHERE B.item=%(item_code)s AND B.is_active=1 """,{"item_code":x.item_to_manufacture},as_dict=1)
# 			if bom__ and len(bom__) > 1:
# 				frappe.throw(f"Multiple BOM's found for Item to Produce - {x.item_to_manufacture}. at row {x.idx}")
# 			""" End """
# 			bom_items = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(item_code)s AND B.is_default=1 AND B.is_active=1 """,{"item_code":x.item_to_manufacture},as_dict=1)
# 			if len(bom_items)>1:
# 				manf_items = frappe.db.sql(""" SELECT item_to_manufacture,operation FROM `tabDC Item` WHERE  parent = %(rc_id)s AND item_to_manufacture=%(item_to_manufacture)s """,{"rc_id":self.name,"item_to_manufacture":x.item_to_manufacture},as_dict=1)
# 				if not len(manf_items) == len(bom_items):
# 					return False
# 	return True