# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours,now,flt,add_to_date,time_diff,get_datetime,getdate

class CompoundInspection(Document):
	def compare_parameters(self,parameter_type):
		if parameter_type == "Hardness":
			hardness_check = False
			if self.min_hardness:
				if not self.hardness_observed >= self.min_hardness:
					self.no_enough_hardness = 1
					hardness_check = True
					if not self.scan_quality_approver:
						frappe.msgprint(f"The <b>Hardness - {self.hardness_observed}</b> is less than the <b>Minimum Hardness - {self.min_hardness}</b>..!")
			else:
				self.no_enough_hardness = 0
			if not hardness_check:
				if self.max_hardness:
					if not self.hardness_observed <= self.max_hardness:
						self.no_enough_hardness = 1
						if not self.scan_quality_approver:
							frappe.msgprint(f"The <b>Hardness - {self.hardness_observed}</b> is greater than the <b>Maximum Hardness - {self.max_hardness}</b>..!") 
					else:
						self.no_enough_hardness = 0
		elif parameter_type == "SG":
			sg_check = False
			if self.sg_min:
				if not self.sg_observed >= self.sg_min:
					self.no_enough_sg = 1
					sg_check = True
					if not self.scan_quality_approver:
						frappe.msgprint(f"The <b>SG - {self.sg_observed}</b> is less than the <b>Minimum SG - {self.sg_min}</b>..!")
			else:
				self.no_enough_sg = 0
			if not sg_check:
				if self.sg_max:
					if not self.sg_observed <= self.sg_max:
						self.no_enough_sg = 1
						if not self.scan_quality_approver:
							frappe.msgprint(f"The <b>SG - {self.sg_observed}</b> is greater than the <b>Maximum SG - {self.sg_max}</b>..!") 
					else:
						self.no_enough_sg = 0
		elif parameter_type == "TS2":
			ts2_check = False
			if self.ts2_min:
				if not self.ts2_observed >= self.ts2_min:
					self.no_enough_ts2 = 1
					ts2_check = True
					if not self.scan_quality_approver:
						frappe.msgprint(f"The <b>TS2 - {self.ts2_observed}</b> is less than the <b>Minimum TS2 - {self.ts2_min}</b>..!")
			else:
				self.no_enough_ts2 = 0
			if not ts2_check:
				if self.ts2_max:
					if not self.ts2_observed <= self.ts2_max:
						self.no_enough_ts2 = 1
						if not self.scan_quality_approver:
							frappe.msgprint(f"The <b>TS2 - {self.ts2_observed}</b> is greater than the <b>Maximum TS2 - {self.ts2_max}</b>..!") 
					else:
						self.no_enough_ts2 = 0
		elif parameter_type == "TC 90":
			tc_90_check = False
			if self.tc_90_min:
				if not flt(self.tc_90_observed,3) >= flt(self.tc_90_min,3):
					self.no_enough_tc90 = 1
					tc_90_check = True
					if not self.scan_quality_approver:
						frappe.msgprint(f"The <b>TC 90 - {self.tc_90_observed}</b> is less than the <b>Minimum TC 90 - {self.tc_90_min}</b>..!")
			else:
				self.no_enough_tc90 = 0
			if not tc_90_check:
				if self.tc_90_max:
					if not self.tc_90_observed <= self.tc_90_max:
						self.no_enough_tc90 = 1
						if not self.scan_quality_approver:
							frappe.msgprint(f"The <b>TC 90 - {self.tc_90_observed}</b> is greater than the <b>Maximum TC 90 - {self.tc_90_max}</b>..!") 
					else:
						self.no_enough_tc90 = 0

	def validate(self):
		if not self.stock_id:
			frappe.throw(f"The <b>Stock Entry</b> reference not found..!")
		if not self.hardness_observed: 
			frappe.throw("Please enter the <b>Hardness Observed</b>..!")
		if not self.sg_observed: 
			frappe.throw("Please enter the <b>SG Observed</b>..!")
		if not self.ts2_observed: 
			frappe.throw("Please enter the <b>TS2 Observed</b>..!")
		if not self.tc_90_observed: 
			frappe.throw("Please enter the <b>TC90 Observed</b>..!")
		if not self.no_enough_aging:
			difference,age_time = self.get_aging_diff()
			if difference > age_time:
				time_diff = get_datetime(difference) - get_datetime(age_time)
				self.no_enough_aging = 1
				if not self.scan_approver:
					frappe.msgprint(f"The <b>Maturation Time</b> is not completed, Please wait <b>{str(time_diff).split('.')[0]} hrs</b>")
			else:
				self.no_enough_aging = 0
		types = ["Hardness","SG","TS2","TC 90"]
		for ty in types:
			self.compare_parameters(ty)
		
	def on_submit(self):
		if self.no_enough_aging and not self.scan_approver:
			frappe.throw('The <b>Maturation Time</b> is not completed.<br>Please Scan <b>Compound Maturation Approver</b> before submit..!')
		difference,age_time = self.get_aging_diff()
		if difference > age_time:
			if not self.scan_approver:
				frappe.throw(f"The <b>Maturation Time</b> is not completed.<br>Please Scan <b>Compound Maturation Approver</b> before submit..!")
		if self.no_enough_hardness or self.no_enough_sg or self.no_enough_ts2 or self.no_enough_tc90:
			if not self.scan_quality_approver:
				if self.no_enough_hardness:
					frappe.throw(f"The <b>Hardness - {self.hardness_observed}</b> is not in specified range <b>{self.min_hardness} - {self.max_hardness}</b>.<br>Please Scan <b>Quality Approver</b> before submit..!")
				elif self.no_enough_sg:
					frappe.throw(f"The <b>SG - {self.sg_observed}</b> is not in specified range <b>{self.sg_min} - {self.sg_max}</b>.<br>Please Scan <b>Quality Approver</b> before submit..!")
				elif self.no_enough_ts2:
					frappe.throw(f"The <b>TS2 - {self.ts2_observed}</b> is not in specified range <b>{self.ts2_min} - {self.ts2_max}</b>.<br>Please Scan <b>Quality Approver</b> before submit..!")
				elif self.self.no_enough_tc90:
					frappe.throw(f"The <b>TC90 - {self.tc_90_observed}</b> is not in specified range <b>{self.tc_90_min} - {self.tc_90_max}</b>.<br>Please Scan <b>Quality Approver</b> before submit..!")
			else:
				self.check_quality_approver_reading()
		if not self.dc_receipt_id:
			frappe.throw(f"The <b>Delivery Challan Receipt</b> reference not found..!")
		submit_dc_receipt_stock(self)

	def get_aging_diff(self):
		age_time = frappe.db.get_value("Item",self.compound_ref,"item_aging")
		if age_time:
			if self.dc_receipt_id:
				dc_mixing_date = frappe.db.get_value("Delivery Challan Receipt",self.dc_receipt_id,["dc_receipt_date","mixing_time"],as_dict = 1)
				if dc_mixing_date:
					date = None
					time = None
					mixing_date_time = None
					if dc_mixing_date.dc_receipt_date:
						date = getdate(dc_mixing_date.dc_receipt_date)
					if dc_mixing_date.mixing_time:
						time = dc_mixing_date.mixing_time
					if not date or not time:
						mixing_date_time = frappe.db.get_value("Stock Entry",self.stock_id,["posting_date","posting_time"],as_dict = 1)
						if not mixing_date_time:
							frappe.throw(f"The <b>Stock Entry - {self.stock_id}</b> is not found..!")
						if not date:
							date = getdate(mixing_date_time.posting_date)
						if not time:
							time = mixing_date_time.posting_time
					if date and time:
						# date_time = f"{date} {time}"
						# time_diff = get_datetime(now()) - get_datetime(date_time)
						# to_date = add_to_date(date_time,hours = age_time,as_string=True)
						# to_time_diff = get_datetime(to_date) - get_datetime(now())
						# return to_time_diff,time_diff
						from datetime import datetime
						datetime_str = f"{date} {time}"
						if len(datetime_str) > 19:
							datetime_str = datetime_str.split('.')[0]
						date_time = str(datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S'))
						to_date = add_to_date(date_time,hours = age_time,as_string=True)
						return to_date,str(now())
					else:
						frappe.throw(f"Not able to fetch <b>Mixing Date & Time</b> .!")
				else:
					frappe.throw(f"The <b>Delivery Challan Receipt - {self.dc_receipt_id}</b>is not found..!")	
			else:
				frappe.throw("The <b>Delivery Challan Receipt</b> reference is not found..!")	
		else:
			frappe.throw("The <b>Maturation Time</b> is not mentioned..!")	
		
	def check_quality_approver_reading(self):
		if not self.q_hardness_observed:
			frappe.throw(f"Please enter <b>Hardness Observed</b> by Quality Approver..!")
		if not self.q_sg_observed:
			frappe.throw(f"Please enter <b>SG Observed</b> by Quality Approver..!")
		if not self.q_ts2_observed:
			frappe.throw(f"Please enter <b>TS2 Observed</b> by Quality Approver..!")
		if not self.q_tc_90_observed:
			frappe.throw(f"Please enter <b>TC90 Observed</b> by Quality Approver..!")
# def rollback_entries(self,q_ins_id,batch_no,st_items_row_id):
# 	try:
# 		flag = False
# 		if q_ins_id:
# 			frappe.db.delete("Quality Inspection",q_ins_id)
# 		if self.stock_id:
# 			exe_stock = frappe.get_doc("Stock Entry",self.stock_id)
# 			if exe_stock.docstatus == 1:
# 				exe_stock.db_set("docstatus",0)
# 				frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{exe_stock.name}' ")
# 				frappe.db.sql(f"UPDATE `tabStock Entry Detail` SET batch_no = '' WHERE name = '{st_items_row_id}' ")
# 			frappe.db.set_value("Work Order",exe_stock.work_order,"produced_qty",0)
# 		if batch_no:
# 			frappe.db.sql(f" DELETE FROM `tabBatch` WHERE name = '{batch_no}' ")
# 		self.db_set('docstatus',0)
# 		frappe.db.commit()
# 		flag = True
# 		frappe.throw("Stock Entry or Quality Inspection submission error..!")
# 	except Exception:
# 		frappe.log_error(title="Error in compound inspection rollback_entries",message = frappe.get_traceback())
# 		if not flag:
# 			frappe.throw("Something went wrong, not able to rollback entries..!")
#     def rollback_entries(self, q_ins_id, batch_no, st_items_row_id):
#         try:
#             if q_ins_id:
#                 frappe.db.delete("Quality Inspection", q_ins_id)
#             if self.stock_id:
#                 exe_stock = frappe.get_doc("Stock Entry", self.stock_id)
#                 if exe_stock.docstatus == 1:
#                     exe_stock.cancel()  # Better to cancel

#                 # Cleanup Serial and Batch Bundles
#                 for item in exe_stock.items:
#                     if item.serial_and_batch_bundle:
#                         frappe.delete_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)

#                 frappe.db.set_value("Work Order", exe_stock.work_order, "produced_qty", 0)

#             if batch_no:
#                 frappe.db.sql(f"DELETE FROM `tabBatch` WHERE name = '{batch_no}'")

#             frappe.db.commit()

#         except Exception:
#             frappe.log_error(title="Error in rollback_entries", message=frappe.get_traceback())

# def submit_dc_receipt_stock(self):
# 	try:
# 		quality_ins_id = None
# 		batch_no = None
# 		st_items_row_id = None
# 		exe_stock = frappe.get_doc("Stock Entry",self.stock_id)
# 		if exe_stock.docstatus == 0:
# 			exe_stock.docstatus = 1
# 			exe_stock.save(ignore_permissions = True)
# 			#""" Update posting date and time """
# 			dc_resp = frappe.db.get_value("Delivery Challan Receipt",self.dc_receipt_id,["dc_receipt_date","mixing_time"],as_dict = 1)
# 			if dc_resp.dc_receipt_date and dc_resp.mixing_time:
# 				frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{dc_resp.dc_receipt_date}',posting_time = '{dc_resp.mixing_time}' WHERE name = '{exe_stock.name}' ")
# 			elif dc_resp.dc_receipt_date :
# 				frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{dc_resp.dc_receipt_date}' WHERE name = '{exe_stock.name}' ")
# 			#"""end"""
# 			batch_no = ""
# 			for item in exe_stock.items:
# 				if item.is_finished_item and item.t_warehouse:
# 					batch_no = item.batch_no
# 					st_items_row_id = item.name
# 			resp_ = create_quality_inspection_entry(self,batch_no)
# 			if resp_:
# 				quality_ins_id = resp_
# 				frappe.db.set_value(self.doctype,self.name,"qc_inspection_ref",quality_ins_id)
# 				frappe.db.commit()
# 		elif exe_stock.docstatus == 2:
# 			frappe.throw(f"The<b>Stock Entry - {self.stock_id}</b> is cancelled..!")
# 		elif exe_stock.docstatus == 1:
# 			frappe.throw(f"The<b>Stock Entry - {self.stock_id}</b> is already submitted..!")
# 	except Exception:
# 		frappe.log_error(title="Error in submit_dc_receipt_stock",message = frappe.get_traceback())
# 		rollback_entries(self,quality_ins_id,batch_no,st_items_row_id)
def submit_dc_receipt_stock(self):
    try:
        quality_ins_id = None
        batch_no = None
        
        exe_stock = frappe.get_doc("Stock Entry", self.stock_id)
        if exe_stock.docstatus == 0:
            # V15 CRITICAL: Clear fields before submission <sup data-citation="3" className="inline select-none [&>a]:rounded-2xl [&>a]:border [&>a]:px-1.5 [&>a]:py-0.5 [&>a]:transition-colors shadow [&>a]:bg-ds-bg-subtle [&>a]:text-xs [&>svg]:w-4 [&>svg]:h-4 relative -top-[2px] citation-shimmer"><a href="https://discuss.frappe.io/c/erpnext/stock/9">3</a></sup><sup data-citation="7" className="inline select-none [&>a]:rounded-2xl [&>a]:border [&>a]:px-1.5 [&>a]:py-0.5 [&>a]:transition-colors shadow [&>a]:bg-ds-bg-subtle [&>a]:text-xs [&>svg]:w-4 [&>svg]:h-4 relative -top-[2px] citation-shimmer"><a href="https://stackoverflow.com/questions/78404336/new-stock-entry-add-get-items-from-purchase-receipt-in-frappe-erpnext-not-wo">7</a></sup>
            for item in exe_stock.items:
                # Reset all bundle-related fields
                item.serial_no = None
                item.batch_no = None
                item.serial_and_batch_bundle = None
            
            # Initial save to clear legacy data
            exe_stock.save(ignore_permissions=True)
            exe_stock.reload()
            
            # Final submission
            exe_stock.docstatus = 1
            exe_stock.save(ignore_permissions=True)
            
            # Rest of your existing workflow... 

        elif exe_stock.docstatus == 1:
            frappe.throw("Stock Entry already submitted")
            
    except Exception as e:
        self.rollback_entries(quality_ins_id, batch_no, None)
        frappe.throw(f"Submission failed: {str(e)}")

def rollback_entries(self, q_ins_id, batch_no, st_items_row_id):
    try:
        # Cancel Quality Inspection
        if q_ins_id and frappe.db.exists("Quality Inspection", q_ins_id):
            frappe.delete_doc("Quality Inspection", q_ins_id)
        
        # Handle Stock Entry
        if self.stock_id and frappe.db.exists("Stock Entry", self.stock_id):
            se = frappe.get_doc("Stock Entry", self.stock_id)
            if se.docstatus == 1:
                se.cancel()
            
            # Cleanup SABB
            for item in se.items:
                if item.serial_and_batch_bundle:
                    bundle = item.serial_and_batch_bundle
                    item.db_set("serial_and_batch_bundle", None)
                    frappe.delete_doc("Serial and Batch Bundle", bundle)
        
        # Cleanup Batch
        if batch_no and frappe.db.exists("Batch", batch_no):
            frappe.db.delete("Batch", {"name": batch_no})
            
        frappe.db.commit()
        
    except Exception:
        frappe.log_error(title="Compound Inspection Rollback Failure",
                        message=frappe.get_traceback())
        raise  # Re-raise for proper error visibility


def create_quality_inspection_entry(self,batch_no):
	inspected_by = frappe.db.get_value("Employee",self.operator_id,"company_email")
	if inspected_by:
		user_ = frappe.db.get_value("User",inspected_by,"name")
		if user_:
			temp_exe = frappe.db.get_value("Item",self.compound_ref,"quality_inspection_template",as_dict = 1)
			if temp_exe and temp_exe.quality_inspection_template:
				quality_ins = frappe.new_doc("Quality Inspection")
				quality_ins.report_date = getdate()
				quality_ins.status = "Accepted"
				quality_ins.inspection_type = "Incoming"
				quality_ins.reference_type = "Stock Entry"
				quality_ins.reference_name = self.stock_id
				quality_ins.item_code = self.compound_ref
				quality_ins.sample_size = 0
				quality_ins.batch_no = batch_no
				quality_ins.quality_inspection_template = temp_exe.quality_inspection_template
				quality_ins.inspected_by = inspected_by
				quality_ins.append("readings",{
					"min_value":self.min_hardness,
					"value":(str(self.min_hardness) if self.min_hardness else "0")  + '-' + (str(self.max_hardness) if self.max_hardness else "0"),
					"max_value":self.max_hardness,
					"reading_value":self.q_hardness_observed if self.q_hardness_observed else self.hardness_observed,
					"specification":"HARDNESS",
					"status":"Accepted"
				})
				quality_ins.append("readings",{
					"min_value":self.sg_min,
					"value":(str(self.sg_min) if self.sg_min else "0") + '-' + (str(self.sg_max) if self.sg_max else "0"),
					"max_value":self.sg_max,
					"reading_value":self.q_sg_observed if self.q_sg_observed else self.sg_observed,
					"specification":"specific gravity",
					"status":"Accepted"
				})
				quality_ins.append("readings",{
					"min_value":self.ts2_min,
					"value":(str(self.ts2_min) if self.ts2_min else "0") + '-' + (str(self.ts2_max) if self.ts2_max else "0"),
					"max_value":self.ts2_max,
					"reading_value":self.q_ts2_observed if self.q_ts2_observed else self.ts2_observed,
					"specification":"Ts2",
					"status":"Accepted"
				})
				quality_ins.append("readings",{
					"min_value":self.tc_90_min,
					"value":(str(self.tc_90_min) if self.tc_90_min else "0") + '-' + (str(self.tc_90_max) if self.tc_90_max else "0"),
					"max_value":self.tc_90_max,
					"reading_value":self.q_tc_90_observed if self.q_tc_90_observed else self.tc_90_observed,
					"specification":"TC 90",
					"status":"Accepted"
				})
				quality_ins.insert(ignore_permissions = True)
				exe_doc = frappe.get_doc("Quality Inspection",quality_ins.name)
				exe_doc.docstatus = 1
				exe_doc.save(ignore_permissions = True)
				return exe_doc.name
			else:
				frappe.throw(f"The <b>Quality Inspection Template</b> is not mapped in the compound <b>{self.compound_ref}</b>..!")
		else:
			frappe.throw(f"The <b>User</b> is not found for the email <b>{inspected_by}</b>..!")
	else:
		frappe.throw(f"The <b>Inspector Company E-mail</b> is not found..!")
 
@frappe.whitelist()
def validate_compound_barcode(barcode,docname):
	try:
		exe_cmp_ins = frappe.db.get_value("Compound Inspection",{"scan_compound":barcode,"docstatus":["!=",2],"name":["!=",docname]})
		if not exe_cmp_ins:
			c_info = frappe.db.get_all("Stock Entry Detail",filters={"mix_barcode":barcode},fields=['parent',"docstatus","item_code","spp_batch_number","qty","uom","source_ref_document","source_ref_id","batch_no"])
			if c_info:
				if c_info[0].docstatus == 0:
					dc_inifo = frappe.db.get_value(c_info[0].source_ref_document,c_info[0].source_ref_id,["docstatus"],as_dict = 1)
					if dc_inifo:
						if dc_inifo.docstatus == 1:
							ins_resp = get_quality_template_info(c_info[0])
							if ins_resp:
								frappe.response.status = 'success'
								frappe.response.message = c_info[0]
						else:
							if dc_inifo.docstatus == 0:
								frappe.response.status = 'failed'
								frappe.response.message = f"The <b>Delivery Challan Receipt - {c_info[0].source_ref_id}</b> for the scanned <b>Compound</b> is not Submitted..!"
							else:
								frappe.response.status = 'failed'
								frappe.response.message = f"The <b>Delivery Challan Receipt - {c_info[0].source_ref_id}</b> for the scanned <b>Compound</b> is Cancelled..!"
					else:
						frappe.response.status = 'failed'
						frappe.response.message = f"The <b>Delivery Challan Receipt</b> for the scanned <b>Compound</b> is not exists..!"
				else:
					if c_info[0].docstatus == 1:
						frappe.response.status = 'failed'
						frappe.response.message = f"The <b>Stock Entry - {c_info[0].parent}</b> for the scanned <b>Compound</b> is already submitted..!"
					elif c_info[0].docstatus == 2:
						frappe.response.status = 'failed'
						frappe.response.message = f"The <b>Stock Entry - {c_info[0].parent}</b> for the scanned <b>Compound</b> is cancelled..!"
			else:
				frappe.response.status = 'failed'
				frappe.response.message = f"There is no data found in <b>Stock Entry</b> for the scanned <b>Compound Barcode</b>..!"
		else:
			frappe.response.status = 'failed'
			frappe.response.message = f"The <b>Compound Inspection</b> entry for the barcode - <b>{barcode}</b> is already exists..!"
	except Exception:
		frappe.response.status = 'failed'
		frappe.response.message = f"Something went wrong not able to fetch <b>Compound</b> data..!"
		frappe.log_error(title = "validate_compound_barcode",message = frappe.get_traceback())

def get_quality_template_info(compound_info):
	temp_exe = frappe.db.get_value("Item",compound_info.item_code,"quality_inspection_template",as_dict = 1)
	if temp_exe and temp_exe.quality_inspection_template:
		parameters = frappe.db.get_all("Item Quality Inspection Parameter",{"parent":temp_exe.quality_inspection_template},["*"])
		if parameters:
			compound_info.update({"parameters":parameters})
			return True
		else:
			frappe.response.status = 'failed'
			frappe.response.message = f"The <b>Quality Inspection Template</b> not having any parameters..!"
	else:
		frappe.response.status = 'failed'
		frappe.response.message = f"The <b>Quality Inspection Template</b> is not found for the scanned <b>Compound - {compound_info.item_code}</b>..!"
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