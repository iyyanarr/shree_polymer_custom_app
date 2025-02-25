# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,getdate
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series,get_details_by_lot_no,get_parent_lot

class DeflashingDespatchEntry(Document):
	def validate(self):
		if getdate(self.posting_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.items:
			frappe.throw(" Scan and add some items before save.")

	def on_submit(self):
		create_stock_entry(self)
		# make_stock_entry(self)
		# make_delivery_note_entry(self)

def create_stock_entry(self):
    try:
        # Initialize source and target warehouses
        source_warehouse = None
        target_warehouse = None

        # Query to fetch consolidated item details from Deflashing Despatch Entry Items
        ddei__items = frappe.db.sql(f""" 
            SELECT 
                DDEI.valuation_rate, 
                DDEI.amount,
                DDEI.name,
                DDEI.lot_number,
                DDEI.source_warehouse_id,
                DDEI.warehouse_id,
                DDEI.item,
                SUM(DDEI.qty) AS qty,
                DDEI.batch_no,
                DDEI.spp_batch_number 
            FROM `tabDeflashing Despatch Entry Item` DDEI 
            INNER JOIN `tabDeflashing Despatch Entry` DDE ON DDE.name = DDEI.parent 
            WHERE DDE.name = '{self.name}' 
            GROUP BY 
                DDEI.source_warehouse_id,
                DDEI.warehouse_id,
                DDEI.item,
                DDEI.batch_no,
                DDEI.spp_batch_number,
                DDEI.lot_number 
        """, as_dict=1)

        # Determine source and target warehouses from the first item
        for each__item in ddei__items:
            source_warehouse = each__item.source_warehouse_id
            target_warehouse = each__item.warehouse_id
            break

        # Create a new Stock Entry document
        stock_entry = frappe.new_doc("Stock Entry")

        # Set basic fields
        stock_entry.stock_entry_type = "Material Transfer"
        stock_entry.from_warehouse = source_warehouse
        stock_entry.to_warehouse = target_warehouse
        stock_entry.posting_date = self.posting_date if self.posting_date else getdate()

        # Log warehouse configurations
        frappe.logger().debug(f"Werehouses configured: From {source_warehouse}, To {target_warehouse}")

        # Add items to the Stock Entry
        for each__item in ddei__items:
            stock_entry.append("items", {
                "item_code": each__item.item,
                "s_warehouse": source_warehouse,
                "t_warehouse": target_warehouse,
                "qty": flt(each__item.qty, 3),
                "uom": "Kg",
				"use_serial_batch_fields": 1,
                "batch_no": each__item.batch_no,
                "spp_batch_number": each__item.spp_batch_no,
                "basic_rate": each__item.valuation_rate,
                "amount": each__item.amount,
                "scan_barcode": each__item.lot_number
            })

        # Insert Stock Entry
        stock_entry.insert(ignore_permissions=True)

        # Setting stock entry to submitted
        stock_entry.docstatus = 1
        stock_entry.save(ignore_permissions=True)

        # Update reference in the original document
        frappe.db.set_value(self.doctype, self.name, "stock_entry_reference", stock_entry.name)
        frappe.db.commit()

        # Reference tracking
        store_reference(self, stock_entry)

        # Reload the current document
        self.reload()

        frappe.msgprint(f"Successfully created Stock Entry: {stock_entry.name}")
        return stock_entry.name

    except Exception as e:
        # Rollback in case of any error
        frappe.db.rollback()
        rollback__entries(self)
        frappe.log_error(message=frappe.get_traceback(), title="Stock Entry Creation Error")
        self.reload()
        frappe.msgprint(f"Failed to create Stock Entry: {str(e)}")

def make_delivery_note_entry(self):
	try:
		source_warehouse = None
		target_warehouse = None
		ddei__items = frappe.db.sql(f""" SELECT DDEI.valuation_rate,DDEI.amount,DDEI.name,DDEI.lot_number,DDEI.source_warehouse_id,DDEI.warehouse_id,DDEI.item,SUM(DDEI.qty) qty,DDEI.batch_no,DDEI.spp_batch_no 
						   FROM `tabDeflashing Despatch Entry Item` DDEI INNER JOIN `tabDeflashing Despatch Entry` DDE ON DDE.name = DDEI.parent WHERE DDE.name = '{self.name}' GROUP BY DDEI.source_warehouse_id,DDEI.warehouse_id,DDEI.item,DDEI.batch_no,DDEI.spp_batch_no,DDEI.lot_number """, as_dict = 1)
		for each__item in ddei__items:
			source_warehouse = each__item.source_warehouse_id
			target_warehouse = each__item.warehouse_id
			break
		spp_dc = frappe.new_doc("Delivery Note")
		""" Ref """
		spp_dc.reference_document = self.doctype
		spp_dc.reference_name = self.name
		""" End """
		spp_dc.posting_date = self.posting_date if self.posting_date else getdate()
		spp_dc.set_warehouse = source_warehouse
		spp_dc.set_target_warehouse = target_warehouse
		customer = frappe.db.get_value("Warehouse",target_warehouse,"customer")
		if customer:
			spp_dc.customer = customer
			spp_dc.operation = "Material Transfer"
			for each__item in ddei__items:
				spp_dc.append("items",{
					"scan_barcode":each__item.lot_number,
					"item_code":each__item.item,
					"item_name":frappe.db.get_value("Item",each__item.item,"item_name"),
					"spp_batch_number":each__item.spp_batch_no,
					"batch_no":each__item.batch_no,
					"qty":flt(each__item.qty, 3),
					"uom":"Kg",
					"target_warehouse":each__item.warehouse_id,
					"rate":each__item.valuation_rate,
					"amount":each__item.amount
					})
			# frappe.log_error(title="dc", message = spp_dc.as_dict())
			spp_dc.insert(ignore_permissions = True)
			spp_dc = frappe.get_doc("Delivery Note",spp_dc.name)
			spp_dc.docstatus = 1
			spp_dc.save(ignore_permissions=True)
			""" Update posting date and time """
			frappe.db.sql(f" UPDATE `tabDelivery Note` SET posting_date = '{self.posting_date}' WHERE name = '{spp_dc.name}' ")
			""" End """
			store_reference(self,spp_dc)
			for each__item in ddei__items:
				frappe.db.set_value("Deflashing Despatch Entry Item",each__item.name,"stock_entry_reference",spp_dc.name)
				frappe.db.commit()
		else:
			frappe.throw("Customer not found for the wareshouse <b>"+target_warehouse+"</b>")
		self.reload()
	except Exception as e:
		frappe.db.rollback()
		rollback__entries(self)
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflahing_despatch_entry.deflahing_despatch_entry.make_delivery_note")
		self.reload()

def set_missing_values(doc):
	doc.run_method("set_missing_values")
	doc.run_method("set_po_nos")
	doc.run_method("calculate_taxes_and_totals")

def store_reference(self,spp_dc):
	""" Reference """
	store__val = ""
	exe_entries = frappe.db.get_value(self.doctype,self.name,'stock_entry_reference')
	if exe_entries:
		exe_entries += "," + spp_dc.name
		store__val += exe_entries
	else:
		store__val = spp_dc.name
	frappe.db.set_value(self.doctype,self.name,'stock_entry_reference',store__val)
	frappe.db.commit()
	""" End """

def rollback__entries(self):
	try:
		self.reload()
		if self.stock_entry_reference:
			ref = self.stock_entry_reference.split(',')
			for st__ref in ref:
				frappe.db.sql(""" DELETE FROM `tabDelivery Note` WHERE name=%(name)s""",{"name":st__ref})
				frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Delivery Note' AND voucher_no = '{st__ref}' ")
		dde = frappe.get_doc(self.doctype, self.name)
		dde.db_set("docstatus", 0)
		dde.db_set("stock_entry_reference", '')
		frappe.db.commit()
		self.reload()
		frappe.msgprint("Something went wrong, not able to make <b>Delivery Note</b>..!")
	except Exception:
		frappe.msgprint('Something went wrong not able to rollback..!')
		frappe.log_error(title='rollback__entries error',message = frappe.get_traceback())		

def make_stock_entry(self):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.company = "SPP"
		stock_entry.naming_series = "MAT-STE-.YYYY.-"
		""" For identifying procees name to change the naming series the field is used """
		naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Deflashing")
		if naming_status:
			stock_entry.naming_series = naming_series
		""" End """
		stock_entry.stock_entry_type = "Material Transfer"
		# stock_entry.from_warehouse = self.items[0].source_warehouse_id 
		# stock_entry.to_warehouse = self.items[0].warehouse_id
		for each in self.items:
			stock_entry.append("items",{
				"item_code":each.item,
				"s_warehouse": each.source_warehouse_id ,
				"t_warehouse":each.warehouse_id,
				"stock_uom": "Kg",
				"uom": "Kg",
				"conversion_factor_uom":1,
				"transfer_qty":flt(each.qty, 3),
				"qty":flt(each.qty, 3),
				"batch_no":each.batch_no,
				"spp_batch_number":each.spp_batch_no,
				"source_ref_document":self.doctype,
				"source_ref_id":self.name
				})
		stock_entry.insert()
		""" Update stock entry reference in child table """
		frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
		""" End """
		sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
		sub_entry.docstatus=1
		sub_entry.save(ignore_permissions=True)
		frappe.db.commit()
		self.reload()
	except Exception as e:
		self.reload()
		if self.stock_entry_reference:
			frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE name=%(name)s""",{"name":self.stock_entry_reference})
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{self.stock_entry_reference}' ")
		dde = frappe.get_doc(self.doctype, self.name)
		dde.db_set("docstatus", 0)
		dde.db_set("stock_entry_reference", '')
		frappe.db.commit()
		self.reload()
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.make_stock_entry")
		frappe.msgprint("Something went wrong, not able to make <b>Stock Entry</b>..!")

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
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.check_available_stock")
		return {"status":"failed","message":"Something went wrong"}

@frappe.whitelist()
def validate_lot_barcode(bar_code):
	try:
		if not frappe.db.get_value("Deflashing Despatch Entry Item",{"lot_number":bar_code,"docstatus":1}):
			sublot__resp = check_sublot(bar_code)
			if not sublot__resp:
				ins__prod_resp = validate_ins_production(bar_code)
				if ins__prod_resp and ins__prod_resp.get('status') == 'success':
					job_card = ins__prod_resp.get('job_card')
					card_details = frappe.db.get_value("Job Card",job_card,["production_item","total_completed_qty","work_order"],as_dict=1)
					query = f""" SELECT SED.t_warehouse as from_warehouse,SED.valuation_rate,SED.amount,SED.spp_batch_number,SED.mix_barcode,SED.batch_no,SED.qty FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE 
								ON SED.parent=SE.name WHERE SED.item_code='{card_details.get("production_item")}' AND SE.work_order='{card_details.get("work_order")}' """
					spp_and_batch = frappe.db.sql(query,as_dict=1)
					if spp_and_batch:
						stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),card_details.get("production_item"),spp_and_batch[0].get("batch_no",""))
						if stock_status.get('status') == "success":
							frappe.response.job_card = job_card
							frappe.response.item = card_details.get("production_item")
							frappe.response.qty = stock_status.get('qty')
							frappe.response.spp_batch_number = spp_and_batch[0].get("spp_batch_number")
							frappe.response.mix_barcode = spp_and_batch[0].get("mix_barcode")
							frappe.response.batch_no = spp_and_batch[0].get("batch_no","")
							frappe.response.from_warehouse = spp_and_batch[0].get("from_warehouse")
							frappe.response.valuation_rate = spp_and_batch[0].get('valuation_rate')
							frappe.response.amount = spp_and_batch[0].get('amount')
							frappe.response.status = "success"
						else:
							frappe.response.status = stock_status.get('status')
							frappe.response.message = stock_status.get('message')
					else:
						frappe.response.status = "failed"
						frappe.response.message = "There is no <b>Stock Entry</b> found for the scanned lot"
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"The <b>Deflashing Despatch Entry</b> for the lot - <b>{bar_code}</b> is already exists..!"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_lot_barcode")

def check_sublot(bar_code):
	lot_info = get_details_by_lot_no(bar_code,transfer_other_warehouse = True)
	# frappe.log_error(title="lot_info",message=lot_info)
	if lot_info.get("status") == "success":
		if lot_info.get('data'):
			""" This is not covered in work flow , this for despatch any items to another warehouse, as per arun request implemented """
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
					parent__lot = get_parent_lot(bar_code)
					if parent__lot and parent__lot.get('status') == 'success':
						pro_ins_val = validate_ins_production(parent__lot.get('lot_no'))
						if pro_ins_val and pro_ins_val.get('status') == 'success':
							return_response(lot_info)
					else:
						if parent__lot:
							frappe.response.status = "failed"
							frappe.response.message = parent__lot.get('message')
		else:
			frappe.response.status = "failed"
			frappe.response.message = lot_info.get('message')
		return True
	else:
		return False
	
def return_response(lot_info):
	if lot_info.get('data').get('qty'):
		frappe.local.response.status = "success"
		frappe.response.item = lot_info.get('data').get('item_code')
		frappe.response.qty = lot_info.get('data').get('qty')
		frappe.response.spp_batch_number = lot_info.get('data').get('spp_batch_number')
		frappe.response.mix_barcode = lot_info.get('data').get('mix_barcode')
		frappe.response.batch_no = lot_info.get('data').get('batch_no')
		frappe.response.from_warehouse = lot_info.get('data').get('t_warehouse')
		frappe.response.valuation_rate = lot_info.get('data').get('valuation_rate')
		frappe.response.amount = lot_info.get('data').get('amount')
	else:
		frappe.response.status = "failed"
		frappe.response.message = f"Stock is not available for the item <b>{lot_info.get('data').get('item_code')}</b>"

def validate_ins_production(bar_code):
	job_card = frappe.db.get_value("Job Card",{"batch_code":bar_code,"operation":"Moulding"},['docstatus','name'],as_dict = 1)
	if job_card:
		if job_card.docstatus == 1:
			exe_production_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":bar_code,"docstatus":1})
			if exe_production_entry:
				check_line_inspe_entry = frappe.db.get_value("Inspection Entry",{"lot_no":bar_code,"docstatus":1,"inspection_type":"Line Inspection"})
				if check_line_inspe_entry:
					check_lot_inspe_entry = frappe.db.get_value("Inspection Entry",{"lot_no":bar_code,"docstatus":1,"inspection_type":"Lot Inspection"})
					if check_lot_inspe_entry:
						return {"status":"success","job_card":job_card.name}
					else:
						frappe.response.status = "failed"
						frappe.response.message = "There is no <b>Lot Inspection Entry</b> for the scanned lot"
				else:
					frappe.response.status = "failed"
					frappe.response.message = "There is no <b>Line Inspection Entry</b> for the scanned lot"
			else:
				frappe.response.status = "failed"
				frappe.response.message = "There is no <b>Moulding Production Entry</b> for the scanned lot"
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"The <b>Job Card - {job_card.name}</b> is not submitted."
	else:
		frappe.response.status = "failed"
		frappe.response.message = f"The <b>Lot Number - {bar_code}</b> is invalid..!"

@frappe.whitelist()
def validate_warehouse(bar_code):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.deflashing_vendor:
			condition = ""
			for v in spp_settings.deflashing_vendor:
				condition += f"'{v.vendor}',"
			condition = condition[:-1]
			exe_warehouse = frappe.db.sql(f" SELECT warehouse_name,name,is_group FROM `tabWarehouse` WHERE barcode_text='{bar_code}' AND disabled=0 AND parent_warehouse IN ({condition}) ",as_dict = 1)
			if exe_warehouse:
				exe_warehouse = exe_warehouse[0]
				if exe_warehouse.get("is_group"):
					frappe.response.status = "failed"
					frappe.response.message = "Group node warehouse is not allowed to select for transactions"
				frappe.response.status = "success"
				frappe.response.warehouse_name = exe_warehouse.get("warehouse_name")
				frappe.response.name = exe_warehouse.get("name")
			else:
				frappe.response.status = "failed"
				frappe.response.message = "There is no warehouse found for scanned vendor code"
		else:
			frappe.response.status = "failed"
			frappe.response.message = "Deflashing Vendors filters not mapped in SPP Settings."
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong"
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_warehouse")
	



""" Back up """

# def make_delivery_note_entry(self):
# 	try:
# 		ddei__items = frappe.db.sql(f""" SELECT DDEI.valuation_rate,DDEI.amount,DDEI.name,DDEI.lot_number,DDEI.source_warehouse_id,DDEI.warehouse_id,DDEI.item,SUM(DDEI.qty) qty,DDEI.batch_no,DDEI.spp_batch_no 
# 						   FROM `tabDeflashing Despatch Entry Item` DDEI INNER JOIN `tabDeflashing Despatch Entry` DDE ON DDE.name = DDEI.parent WHERE DDE.name = '{self.name}' GROUP BY DDEI.source_warehouse_id,DDEI.warehouse_id,DDEI.item,DDEI.batch_no,DDEI.spp_batch_no,DDEI.lot_number """, as_dict = 1)
# 		for each__item in ddei__items:
# 			spp_dc = frappe.new_doc("Delivery Note")
# 			""" Ref """
# 			spp_dc.reference_document = self.doctype
# 			spp_dc.reference_name = self.name
# 			""" End """
# 			spp_dc.posting_date = getdate()
# 			spp_dc.set_warehouse = each__item.source_warehouse_id
# 			spp_dc.set_target_warehouse = each__item.warehouse_id
# 			customer = frappe.db.get_value("Warehouse",each__item.warehouse_id,"customer")
# 			if customer:
# 				# if frappe.db.get_value("Customer",customer,"is_internal_customer"):
# 					spp_dc.customer = customer
# 					spp_dc.operation = "Material Transfer"
# 					spp_dc.append("items",{
# 						"scan_barcode":each__item.lot_number,
# 						"item_code":each__item.item,
# 						"item_name":frappe.db.get_value("Item",each__item.item,"item_name"),
# 						"spp_batch_no":each__item.spp_batch_no,
# 						"batch_no":each__item.batch_no,
# 						"qty":flt(each__item.qty, 3),
# 						"uom":"Kg",
# 						"target_warehouse":each__item.warehouse_id,
# 						"rate":each__item.valuation_rate,
# 						"amount":each__item.amount
# 						})
# 					# set_missing_values(spp_dc)
# 					spp_dc.insert(ignore_permissions = True)
# 					spp_dc = frappe.get_doc("Delivery Note",spp_dc.name)
# 					spp_dc.docstatus = 1
# 					spp_dc.save(ignore_permissions=True)
# 					""" Update posting date and time """
# 					frappe.db.sql(f" UPDATE `tabDelivery Note` SET posting_date = '{self.posting_date}' WHERE name = '{spp_dc.name}' ")
# 					""" End """
# 					store_reference(self,spp_dc)
# 					frappe.db.set_value("Deflashing Despatch Entry Item",each__item.name,"stock_entry_reference",spp_dc.name)
# 					frappe.db.commit()
# 				# else:
# 				# 	frappe.throw(f"The Customer - <b>{customer}</b> is not internal customer in the warehouse - <b>{each__item.warehouse_id}</b>")
# 			else:
# 				frappe.throw("Customer not found for the wareshouse <b>"+each__item.warehouse_id+"</b>")
# 		self.reload()
# 	except Exception as e:
# 		frappe.db.rollback()
# 		rollback__entries(self)
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflahing_despatch_entry.deflahing_despatch_entry.make_delivery_note")
# 		self.reload()



# @frappe.whitelist()
# def validate_lot_barcode(bar_code):
# 	try:
# 		sublot__resp = check_sublot(bar_code)
# 		if not sublot__resp:
# 			exe_production_entry = frappe.db.get_value("Moulding Production Entry",{"scan_lot_number":bar_code,"docstatus":1})
# 			if exe_production_entry:
# 				# check_lot_inspe_entry = frappe.db.get_value("Lot Inspection Entry",{"lot_no":bar_code,"docstatus":1})
# 				check_lot_inspe_entry = frappe.db.get_value("Inspection Entry",{"lot_no":bar_code,"docstatus":1,"inspection_type":"Lot Inspection"})
# 				if check_lot_inspe_entry:
# 					job_card = frappe.db.get_value("Job Card",{"batch_code":bar_code,"docstatus":1,"operation":"Moulding"})
# 					if job_card:
# 						card_details = frappe.db.get_value("Job Card",job_card,["production_item","total_completed_qty","work_order"],as_dict=1)
# 						query = f""" SELECT SED.t_warehouse as from_warehouse,SED.spp_batch_number,SED.mix_barcode,SED.batch_no,SED.qty FROM `tabStock Entry Detail` SED INNER JOIN `tabStock Entry` SE 
# 									ON SED.parent=SE.name WHERE SED.item_code='{card_details.get("production_item")}' AND SE.work_order='{card_details.get("work_order")}' """
# 						spp_and_batch = frappe.db.sql(query,as_dict=1)
# 						if spp_and_batch:
# 							stock_status = check_available_stock(spp_and_batch[0].get("from_warehouse"),card_details.get("production_item"),spp_and_batch[0].get("batch_no",""))
# 							if stock_status.get('status') == "success":
# 								frappe.response.job_card = job_card
# 								frappe.response.item = card_details.get("production_item")
# 								frappe.response.qty = stock_status.get('qty')
# 								frappe.response.spp_batch_number = spp_and_batch[0].get("spp_batch_number")
# 								frappe.response.mix_barcode = spp_and_batch[0].get("mix_barcode")
# 								frappe.response.batch_no = spp_and_batch[0].get("batch_no","")
# 								frappe.response.from_warehouse = spp_and_batch[0].get("from_warehouse")
# 								frappe.response.status = "success"
# 							else:
# 								frappe.response.status = stock_status.get('status')
# 								frappe.response.message = stock_status.get('message')
# 						else:
# 							frappe.response.status = "failed"
# 							frappe.response.message = "There is no <b>Stock Entry</b> found for the scanned lot"
# 					else:
# 						frappe.response.status = "failed"
# 						frappe.response.message = "There is no <b>Job Card</b> found for the scanned lot"
# 				else:
# 					frappe.response.status = "failed"
# 					frappe.response.message = "There is no <b>Lot Inspection Entry</b> for the scanned lot"
# 			else:
# 				frappe.response.status = "failed"
# 				frappe.response.message = "There is no <b>Moulding Production Entry</b> for the scanned lot"
# 	except Exception:
# 		frappe.response.status = "failed"
# 		frappe.response.message = "Something went wrong"
# 		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_lot_barcode")