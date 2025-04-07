# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt,add_to_date, update_progress_bar,format_time, formatdate, getdate, nowdate,now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series,generate_batch_no,delete_batches

class MouldingProductionEntry(Document):
	updated_batch_details = []
	line_rejection_qty = 0.0
	compound_available_qty = 0.0
	# This function is used to sort the 'Asset' print cards 'check asset print formats for details'
	def sort_bins_for_print(self,values):
		result = []
		splited_series = []
		non_int_series = []
		sorted_values= []
		non_int_values = []
		looped_names = []
		for val_ in values:
			try:
				splited_series.append(int(val_.asset_name.split(' ')[-1]))
			except ValueError:
				non_int_series.append(val_.asset_name.split(' ')[-1])
		if not splited_series:
			return values
		else:
			splited_series.sort()
			for sn in splited_series:
				for ss in values:
					try:
						if int(ss.asset_name.split(' ')[-1]) == sn:
							sorted_values.append(ss)
					except ValueError:
						non_int_values.append(ss)
		sorted_values.extend(non_int_values)
		for res in sorted_values:
			if res.name not in looped_names:
				result.append(res)
				looped_names.append(res.name)
		return result
	
	def validate(self):
		self.validate_get_line_ins_qty()
		if getdate(self.moulding_date) > getdate():
			frappe.throw("The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
		if not self.curing_time:
			frappe.throw(f"Curing Time can't be Empty or Zero..!")
		if not self.no_of_running_cavities:
			frappe.throw(f"No.of running cavities can't be Empty or Zero..!")
		if not self.number_of_lifts:
			frappe.throw(f"No.os lifts can't be Empty or Zero..!")
		ins_resp_ = self.validate_inspection_qty(self.scan_lot_number)
		if ins_resp_.get("status") == "success":
			if self.no_balance_bin == 0:
				# if not flt(self.weight_of_balance_bin,3) > 0:
				if not self.balance_bins:
					frappe.throw("Please scan and add atleast one <b>Balance Bin</b>..!")
			tolerance_val = validate_tolerance(self)
			if tolerance_val.get("status"):
				if tolerance_val.get("message"):
					frappe.msgprint(tolerance_val.get("message"))
			else:
				frappe.throw(tolerance_val.get("message"))
		else:
			frappe.throw(ins_resp_.get("message"))
		if not self.weight:
			frappe.throw(f"Weight can't be Empty or Zero..!")
		if not self.job_card:
			frappe.throw(f"Job Card value is missing..!")
		if not self.compound:
			frappe.throw(f"Compound value is missing..!")
		if not self.batch_details:
			frappe.throw(f"Source batch details not found..!")
		self.cmpr_balbin_get_cmp_qty()
		self.weight = flt(self.weight,3)
		self.weight_without_shell  = flt(flt((self.weight + self.line_rejection_qty),3),3)
		s_resp = validate_shell(self)
		# frappe.log_error(title='--validate shell--',message=s_resp)
		if s_resp.get('status') == 'failed':
			frappe.throw(s_resp.get('message')) 
		else:
			if s_resp.get('is_shell_item_found'):
				if not s_resp.get('warehouse'):
					frappe.throw(f'Shell source warehouse not found..!')
				if not s_resp.get('batch_id'):
					frappe.throw(f'Shell source batch details not found..!')
				if not s_resp.get('total_shell_qty_in_kgs'):
					frappe.throw(f'Shell qty in Kgs not found..!')
				if not s_resp.get('total_shell_qty_in_nos'):
					frappe.throw(f'Shell qty in Nos not found..!')
				if not s_resp.get('shell_item'):
					frappe.throw(f'Shell item not found..!')
				self.s_source_warehouse = s_resp.get('warehouse')
				self.s_batch = s_resp.get('batch_id')
				self.shell_qty_kgs = s_resp.get('total_shell_qty_in_kgs')
				self.shell_qty_nos = s_resp.get('total_shell_qty_in_nos')
				self.shell_item = s_resp.get('shell_item')
				self.weight_without_shell = flt(flt((self.weight + self.line_rejection_qty),3) -  s_resp.get('total_shell_qty_in_kgs'),3)
			else:
				self.weight_without_shell = flt(flt((self.weight + self.line_rejection_qty),3),3)

	def validate_inspection_qty(self,batch_no):
		return {"status":"success"}	
		# spp_settings = frappe.get_single("SPP Settings")
		# if not spp_settings.inspection_rejection_limit:
		# 	return {"message":f"Inspection Rejection limit not found in <b>SPP Settings</b>"}
		# else:
		# 	""" Calculate the rejection limit and validate """
		# 	percen__ = (self.weight / 100 ) * spp_settings.inspection_rejection_limit
		# 	total_rejected_qty = 0.0
		# 	ins__entries = frappe.db.sql(f" SELECT name,total_rejected_qty_kg,inspection_type FROM `tabInspection Entry` WHERE lot_no = '{batch_no}' AND docstatus = 1 AND (inspection_type = 'Line Inspection' OR inspection_type = 'Patrol Inspection' OR inspection_type = 'Lot Inspection') ",as_dict = 1)
		# 	for ins in ins__entries:
		# 		total_rejected_qty += ins.total_rejected_qty_kg
		# 	if total_rejected_qty > percen__:
		# 		return {"message":f"Total Rejected Qty - <b>{total_rejected_qty}</b> is greater than <b>{spp_settings.inspection_rejection_limit}%</b> of the item produced. "}
		# 	if total_rejected_qty > self.weight:
		# 		return {"message":f"Total Rejected Qty - <b>{total_rejected_qty}</b> is greater than the item produced - <b>{self.weight}</b> "}
		# return {"status":"success"}	
	
	def validate_get_line_ins_qty(self):
		ins_info = frappe.db.get_value("Inspection Entry",{"lot_no":self.scan_lot_number,"docstatus":1,"inspection_type":"Line Inspection"},["stock_entry_reference","name"],as_dict = 1)
		if ins_info:
			if ins_info.stock_entry_reference:
				query = f""" SELECT SED.qty FROM `tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name 
							WHERE SED.source_ref_document = "Inspection Entry" AND SED.source_ref_id = '{ins_info.name}' AND SE.name = '{ins_info.stock_entry_reference}' """
				qty_info = frappe.db.sql(query, as_dict = 1)
				if qty_info:
					self.line_rejection_qty = flt(qty_info[0].qty,3)
					# self.weight += flt(self.line_rejection_qty,3)
				else:
					frappe.throw(f"<b>Line Inspection</b> entry stock details not found..!")
	
	def cmpr_balbin_get_cmp_qty(self):
		import json
		self.updated_batch_details = json.loads(self.batch_details)
		for is__bc in self.updated_batch_details:
			if is__bc.get('is_balance_bin'):
				self.compound_available_qty += is__bc.get('consumed__qty')
			else:
				self.compound_available_qty += is__bc.get('qty')

	def on_submit(self):
		cavity_val = validate_cavity(self)
		if cavity_val.get('status') == 'success':
			qty_val_resp = validate_mat_qty(self)
			if qty_val_resp.get('status') == 'success':
				vcd = validate_comsumption_details(self)
				if vcd.get('status') == 'success':
					ins_info = frappe.db.get_value("Inspection Entry",{"lot_no":self.scan_lot_number,"docstatus":1,"inspection_type":"Line Inspection"},["stock_entry_reference","name"],as_dict = 1)
					if ins_info:
						resp_ = make_stock_entry(self)
						if resp_.get('status') == 'failed':
							rollback_entries(self,resp_.get('message'))
						else:
							frappe.db.set_value(self.doctype,self.name,"batch_details",self.updated_batch_details)
							frappe.db.commit()
							self.reload()
					else:
						frappe.throw(f"<b>Stock Entry</b> reference not found in the <b>Line Inspection</b> entry..!")
				else:
					frappe.throw(vcd.get('message'))
			else:
				frappe.throw(qty_val_resp.get('message'))
		else:
			frappe.throw(cavity_val.get('message'))

	def manual_on_submit(self):
		print("\n=== Starting Manual Submit Process ===")
		print(f"Document ID: {self.name}")
		print(f"Stock Entry Reference: {self.stock_entry_reference}")

		if self.stock_entry_reference:
			try:
				print(f"\nFetching Stock Entry: {self.stock_entry_reference}")
				exe__stentry = frappe.get_doc("Stock Entry", self.stock_entry_reference)
				print(f"Stock Entry Status: docstatus={exe__stentry.docstatus}")

				# Check for existing Serial and Batch Bundles
				print("\nChecking existing Serial and Batch Bundles:")
				for idx, item in enumerate(exe__stentry.items, 1):
					print(f"\nItem {idx}:")
					print(f"Item Code: {item.item_code}")
					print(f"Serial No: {item.serial_no}")
					print(f"Batch No: {item.batch_no}")
					print(f"Serial and Batch Bundle: {item.serial_and_batch_bundle}")
					
					# Check if bundle already exists
					if item.serial_and_batch_bundle:
						existing_bundle = frappe.db.exists(
							"Serial and Batch Bundle",
							item.serial_and_batch_bundle
						)
						print(f"Existing bundle found: {existing_bundle}")
						
						if existing_bundle:
							# Clear the serial and batch fields if bundle exists
							print(f"Clearing serial and batch fields for item {item.item_code}")
							item.serial_no = None
							item.batch_no = None
							print("Fields cleared")

				# Update use_serial_batch_fields for all items
				print("\nUpdating use_serial_batch_fields:")
				for item in exe__stentry.items:
					previous_value = item.use_serial_batch_fields
					item.use_serial_batch_fields = 1
					print(f"Item {item.item_code}: {previous_value} -> {item.use_serial_batch_fields}")

				# Submit stock entry if needed
				if exe__stentry.docstatus == 0 and exe__stentry.docstatus != 2 and exe__stentry.docstatus != 1:
					print("\nPreparing to submit Stock Entry...")
					print("Current docstatus:", exe__stentry.docstatus)
					exe__stentry.docstatus = 1
					
					try:
						print("Saving stock entry...")
						exe__stentry.save(ignore_permissions=True)
						print("Stock Entry submitted successfully")
					except Exception as save_error:
						print(f"Error during save: {str(save_error)}")
						raise

				# Update moulding date
				if self.moulding_date:
					print(f"\nUpdating posting date to: {self.moulding_date}")
					update_query = f"""
						UPDATE `tabStock Entry` 
						SET posting_date = '{self.moulding_date}' 
						WHERE name = '{exe__stentry.name}'
					"""
					frappe.db.sql(update_query)
					print("Posting date updated successfully")

				print("\nSubmitting inspection entry...")
				submit_inspection_entry(self, exe__stentry)
				print("Inspection entry submitted successfully")

			except Exception as e:
				error_msg = f"""
	====== Error in Manual Submit ======
	Document: {self.name}
	Stock Entry: {self.stock_entry_reference}
	Error: {str(e)}
	Traceback: {frappe.get_traceback()}
	=================================
	"""
				print(error_msg)
				
				# Check the state of items before rollback
				print("\nCurrent state of items before rollback:")
				for item in exe__stentry.items:
					print(f"""
	Item: {item.item_code}
	Serial No: {item.serial_no}
	Batch No: {item.batch_no}
	Bundle: {item.serial_and_batch_bundle}
	Use Serial Batch Fields: {item.use_serial_batch_fields}
	""")
				
				manual_rollback_entries(self, "Something went wrong not able to submit stock entries..!")
				frappe.log_error(
					title=f"Moulding production entry stock submission failed - {self.name}",
					message=error_msg
				)
		else:
			print(f"No Stock Entry Reference found for document: {self.name}")
			frappe.throw("Stock Entry Reference not found in <b>Moulding Production Entry</b>")

		print("\n=== Manual Submit Process Completed ===")




	def on_cancel(self):
		try:
			se = None
			if self.stock_entry_reference:
				try:
					if frappe.db.get_value("Stock Entry",self.stock_entry_reference,"name"):
						se = frappe.get_doc("Stock Entry",self.stock_entry_reference)
						if se.docstatus == 1:
							se.docstatus = 2
							se.save(ignore_permissions=True)
				except Exception:
					frappe.db.rollback()
					frappe.throw("Can't cancel/change Stock Entry..!")
				if se:
					try:
						frappe.db.sql(f"UPDATE `tabWork Order` SET status='Not Started' WHERE name='{se.work_order}'")
						frappe.db.sql(f"UPDATE `tabWork Order Operation` SET status='Pending' WHERE parent='{se.work_order}' AND parentfield='operations' AND parenttype='Work Order' ")
						frappe.db.sql(f"UPDATE `tabJob Card` SET status='Work In Progress',docstatus=0 WHERE work_order='{se.work_order}'")
					except Exception:
						frappe.db.rollback()
						frappe.throw("Can't cancel/change Work Order,Job card .. !")
			else:
				frappe.throw("Stock Entry reference not found.")
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"{self.doctype }- on cancel failed",message=frappe.get_traceback())
			self.reload()

def validate_cavity(self):
	if self.no_of_cavity_in_mspec:
		if not float(self.no_of_cavity_in_mspec) >= float(self.no_of_running_cavities):
			return {"message":f"The <b>No.of.Cavitiy - {self.no_of_running_cavities}</b> can't be greater than - <b>{self.no_of_cavity_in_mspec}</b>..! "}
		else:
			return {"status":"success"}
	else:
		return {"message":f"The <b>No.of.Cavities</b> from <b>Job Card</b> not fetched.<br>Please check the Job Card..!"}

def rollback_entries(self,msg):
	try:
		self.reload()
		stock__id = frappe.db.get_value("Stock Entry",{"blanking_dc_no":self.name},"name")
		if stock__id:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock__id}' ")
		frappe.db.sql(""" DELETE FROM `tabStock Entry` WHERE  blanking_dc_no=%(dc_no)s""",{"dc_no":self.name})
		frappe.db.sql(""" UPDATE `tabJob Card` SET docstatus = 0, status = "Work In Progress" WHERE  name=%(name)s""",{"name":self.job_card})
		frappe.db.sql(""" UPDATE `tabWork Order` SET status = "In Process",produced_qty = 0 WHERE  name=%(name)s""",{"name":frappe.db.get_value("Job Card",self.job_card,"work_order")})
		exe_insp = frappe.db.sql(f" SELECT stock_entry_reference FROM `tabInspection Entry` WHERE (inspection_type = 'Line Inspection' OR inspection_type = 'Patrol Inspection' OR inspection_type = 'Lot Inspection') AND docstatus = 1 AND lot_no='{self.scan_lot_number}' ",as_dict = 1)	
		if exe_insp:
			for ins in exe_insp:
				if ins.stock_entry_reference:
					ins__exe = frappe.get_doc("Stock Entry",ins.stock_entry_reference)
					if ins__exe.docstatus == 1:
						ins__exe.db_set("docstatus", 0)
						frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{ins.stock_entry_reference}' ")
		bl_dc = frappe.get_doc(self.doctype, self.name)
		bl_dc.db_set("docstatus", 0)
		bl_dc.db_set("stock_entry_reference",'')
		frappe.db.commit()
		self.reload()
		frappe.msgprint(msg)
		del__resp,batch__no = delete_batches([self.scan_lot_number])
		if not del__resp:
			frappe.msgprint(batch__no)
	except Exception:
		frappe.db.rollback()
		self.reload()
		frappe.log_error(title="rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def manual_rollback_entries(self,msg):
	try:
		stock__id = frappe.db.get_value("Stock Entry",{"blanking_dc_no":self.name},["name","work_order"],as_dict = 1)
		if stock__id:
			frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{stock__id.name}' ")
			if stock__id.work_order:
				frappe.db.set_value("Work Order",stock__id.work_order,"produced_qty",0) 
		frappe.db.sql(""" UPDATE `tabStock Entry` SET docstatus = 0 WHERE blanking_dc_no=%(dc_no)s""",{"dc_no":self.name})
		exe_insp = frappe.db.sql(f" SELECT stock_entry_reference,name FROM `tabInspection Entry` WHERE (inspection_type = 'Line Inspection' OR inspection_type = 'Patrol Inspection' OR inspection_type = 'Lot Inspection') AND docstatus = 1 AND lot_no='{self.scan_lot_number}' ORDER BY inspection_type DESC LIMIT 1 ",as_dict = 1)	
		if exe_insp:
			for ins in exe_insp:
				if ins.stock_entry_reference:
					ins__exe = frappe.get_doc("Stock Entry",ins.stock_entry_reference)
					if ins__exe.docstatus == 1:
						ins__exe.db_set("docstatus", 0)
						frappe.db.sql(f" DELETE FROM `tabStock Ledger Entry` WHERE voucher_type = 'Stock Entry' AND voucher_no = '{ins.stock_entry_reference}' ")
						frappe.db.commit()
					exe_ins = frappe.get_doc("Inspection Entry",ins.name)
					exe_ins.db_set("docstatus", 0)
					frappe.db.commit()
		frappe.msgprint(msg)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="manual_rollback_entries",message=frappe.get_traceback())
		frappe.msgprint("Something went wrong..Not able to rollback..!")

def validate_comsumption_details(self):
	try:
		import json
		consumed_qty = 0.0
		weight = flt(self.weight_without_shell,3)
		inital_validate = True
		for is__bb in self.updated_batch_details:
			if is__bb.get('is_balance_bin'):
				is__bb['consumed__qty_while_balance_bin'] = is__bb.get('consumed__qty')
				is__bb['balance__qty_while_balance_bin'] = is__bb.get('balance__qty')
				is__bb_compound_qty = flt(flt(is__bb.get('consumed__qty') / self.compound_available_qty,3) * flt(weight,3),3)
				is__bb['consumed__qty'] = is__bb_compound_qty
				consumed_qty = flt(consumed_qty + is__bb_compound_qty,3)
				is__bb["balance__qty"] = flt((flt(is__bb["qty"],3) - is__bb_compound_qty),3) 
		if consumed_qty != weight:
			for k in self.updated_batch_details:
				compound__qty = flt((flt(k["qty"],3) / self.compound_available_qty) * flt(weight,3),3)
				if not k.get('is_balance_bin'): 
					if inital_validate and weight <= compound__qty:
						consumed_qty = weight
						k["consumed__qty"] = weight 
						k["balance__qty"] = flt((compound__qty - weight),3) 
						k["is__consumed"] = 1
						break
					else:
						inital_validate = False
						if weight == flt((consumed_qty + compound__qty),3):
							consumed_qty = flt(consumed_qty + compound__qty,3)
							k["consumed__qty"] = compound__qty
							k["balance__qty"] = 0
							k["is__consumed"] = 1
							break
						elif weight > flt((consumed_qty + compound__qty),3):
							consumed_qty = flt(consumed_qty + compound__qty,3)
							k["consumed__qty"] = compound__qty
							k["balance__qty"] = 0
							k["is__consumed"] = 1
						else:
							required_qty = flt((weight - consumed_qty),3)
							consumed_qty += required_qty
							k["consumed__qty"] = required_qty
							k["balance__qty"] = flt((compound__qty - required_qty),3)
							k["is__consumed"] = 1
							break
		vcwspps = validate_consumption_with_spp_settings(self)
		if vcwspps.get('status') == "success":
			self.updated_batch_details = json.dumps(self.updated_batch_details)
			return {"status":'success'}
		else:
			return vcwspps
	except Exception:
		frappe.log_error(title="validate_comsumption_details",message=frappe.get_traceback())
		return {"status":"failed","message":"Something went wrong, not able to calculate <b>Consumption Qty</b>..!"}

def validate_consumption_with_spp_settings(self):
	spp_settings = frappe.get_single("SPP Settings")
	if not spp_settings.mat_percentage:
		return {"status":"failed","message":"Minimum '%' of Compound Consumption not mapped in <p>SPP Settings</p>. "}
	prod_one_perc = flt(self.weight_without_shell/100,3)
	# As per arun instruction when round three precision it will give zero so use 0.001
	if not prod_one_perc:
		prod_one_perc = 0.001
	# frappe.log_error(title="--prod_one_perc",message=prod_one_perc)
	comp_perce_in_prod = flt(flt(self.compound_available_qty,3) / prod_one_perc,3)
	# frappe.log_error(title="--comp_perce_in_prod",message=comp_perce_in_prod)
	if comp_perce_in_prod >= float(spp_settings.mat_percentage):
		return {"status":"success"}
	else:
		# return {"status":"failed","message":f"The <b>Compound Consumption - {comp_perce_in_prod}%</b> is less than the <b>{spp_settings.mat_percentage}%</b> of <b>Produced Qty</b>..!"}
		return {"status":"failed","message":f"The scanned <b>Bin Wt</b> less than the <b>Produced Qty</b>, Check if you have missed scanning any bins."}

def validate_mat_qty(self):
	try:
		total_consumed_qty =  (flt(flt(self.compound_available_qty,3) + flt(self.shell_qty_kgs,3),3)) 
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.maximum__allowed_qty and spp_settings.maximum__allowed_qty !=0:
			return {"status":"failed","message":"The '%' of excess Qty allowed for the <b>Production Entry</b> not mapped in <b>SPP Settings</b>..!"}
		if not total_consumed_qty == flt((self.weight + self.line_rejection_qty),3):
			if flt((self.weight + self.line_rejection_qty),3) > total_consumed_qty :
				if spp_settings.maximum__allowed_qty:
					one_percen = flt(total_consumed_qty / 100,3)
					actual_percen = flt(flt((self.weight + self.line_rejection_qty),3) / one_percen,3)
					allowd_percen =  flt(100.0 + spp_settings.maximum__allowed_qty,3)
					if actual_percen > allowd_percen:
						total_with_extra_qty = flt(spp_settings.maximum__allowed_qty * one_percen,3)
						return {"status":"failed","message":f"The <b>Produced Qty - {flt((self.weight + self.line_rejection_qty),3)} kgs</b> should be less than or equal to total <b>Available Qty -> {str(flt(self.compound_available_qty,3)) + '+ ' + str(total_with_extra_qty) } {' + ' + str(flt(self.shell_qty_kgs,3)) +' = ' +str(flt(total_consumed_qty + total_with_extra_qty,3)) if self.shell_qty_kgs else ' = ' +str(flt(total_consumed_qty + total_with_extra_qty,3))} Kgs</b>"}
				elif spp_settings.maximum__allowed_qty == 0:
					return {"status":"failed","message":f"The <b>Produced Qty - {flt((self.weight + self.line_rejection_qty),3)} kgs</b> should be less than or equal to total <b>Available Qty -> {flt(self.compound_available_qty,3)} {'+ ' + str(flt(self.shell_qty_kgs,3))+ ' = ' +str(total_consumed_qty) if self.shell_qty_kgs else ''} Kgs</b>"}
		return {"status":'success'}
	except Exception:
		frappe.log_error(title="error in validate mat qty",message=frappe.get_traceback())
		return {"status":"failed","message":"Something went wrong, not able to validate <b>Produced Qty</b>..!"}

def validate_shell(self):
	selected_shell_batch = None
	total_shell_qty_in_kgs = 0
	total_shell_qty_in_nos = 0
	shell_item = None
	spp_settings = frappe.get_single("SPP Settings")
	if not spp_settings.unit_2_warehouse:
		frappe.throw(f'<b>Unit - 2 Warehouse</b> is not mapped in <b>SPP Settings</b>..!')
	bom = frappe.db.get_value("Job Card",self.job_card,"bom_no")
	shell_details = frappe.db.sql(f""" SELECT BI.item_code FROM `tabBOM Item` BI 
			       						INNER JOIN `tabBOM` B ON B.name = BI.parent
			       						INNER JOIN `tabItem` I ON I.name = BI.item_code
			       						WHERE I.item_group = 'Shell' AND B.name = '{bom}' """,as_dict = 1)
	if shell_details:
		check_uom = frappe.db.get_all("UOM Conversion Detail",filters={"parent":shell_details[0].item_code,"uom":"Kg"},fields=['conversion_factor'])
		if check_uom:
			shell_item = shell_details[0].item_code
			total_shell_qty_in_nos = self.number_of_lifts * self.no_of_running_cavities
			one_no_shell_qty_kgs = flt(1 / check_uom[0].conversion_factor,3)
			total_shell_qty_in_kgs = flt(one_no_shell_qty_kgs * total_shell_qty_in_nos,3)
			query = f""" SELECT B.batch_id,IBSB.qty batch_qty FROM `tabBatch` B 
							INNER JOIN `tabItem Batch Stock Balance` IBSB ON 
								IBSB.batch_no = B.batch_id AND IBSB.item_code = B.item
							WHERE B.item = '{shell_details[0].item_code}' AND IBSB.warehouse = '{spp_settings.unit_2_warehouse}'
								AND B.disabled = 0 AND B.expiry_date >= CURDATE() """
			stock_info = frappe.db.sql(query , as_dict = 1)
			if stock_info:
				for k in stock_info:
					if k.batch_qty >= total_shell_qty_in_nos:
						selected_shell_batch = k.batch_id
						break
				if not selected_shell_batch:
					return {'status':'failed','message':f'There is no enough <b>Stock</b> is found for the shell item - <b>{shell_details[0].item_code}</b>'}
			else:
				return {'status':'failed','message':f'<b>Stock</b> is not found for the shell item - <b>{shell_details[0].item_code}</b>'}
		else:
			return {'status':'failed','message':f'<b>UOM</b> conversion factor in <b>Kgs</b> not found for the item - <b>{shell_details[0].item_code}</b>'}
		return {'status':'success','is_shell_item_found':True,'warehouse':spp_settings.unit_2_warehouse,'batch_id':selected_shell_batch,'total_shell_qty_in_kgs':total_shell_qty_in_kgs,'total_shell_qty_in_nos':total_shell_qty_in_nos,'shell_item':shell_item}
	return {'status':'success','is_shell_item_found':False}

def make_stock_entry(self):
	try:
		production__item =  frappe.db.get_value("Work Order",frappe.db.get_value("Job Card",self.job_card,"work_order"),"production_item")
		batch__rep,batch__no = generate_batch_no(batch_id = "T"+self.scan_lot_number,item = production__item,qty = flt(flt((self.weight + self.line_rejection_qty),3),3))
		if batch__rep:
			jc = frappe.get_doc("Job Card",self.job_card)
			for time_log in jc.time_logs:
				time_log.completed_qty = flt(flt((self.weight + self.line_rejection_qty),3),3)
				time_log.time_in_mins = 1
				time_log.employee = self.employee
			jc.total_completed_qty = flt(flt((self.weight + self.line_rejection_qty),3),3)
			jc.for_quantity = flt(flt((self.weight + self.line_rejection_qty),3),3)
			jc.number_of_lifts = self.number_of_lifts
			jc.no_of_running_cavities = self.no_of_running_cavities
			jc.cure_time = self.curing_time
			# jc.shift_supervisor = self.supervisor_id
			# jc.docstatus = 1
			if self.special_instructions:
				jc.remarks = self.special_instructions
			jc.save(ignore_permissions=True)
			spp_settings = frappe.get_single("SPP Settings")
			if not spp_settings.from_location:
				frappe.throw("Asset Movement <b>From location</b> not mapped in SPP settings")
			if not spp_settings.to_location:
				frappe.throw("Asset Movement <b>To location</b> not mapped in SPP settings")
			work_order_id = frappe.db.get_value("Job Card",self.job_card,"work_order")
			work_order = frappe.get_doc("Work Order", work_order_id)
			if work_order.operations:
				for operation in work_order.operations:
					frappe.db.set_value("Work Order Operation",operation.name,"completed_qty",flt(flt((self.weight + self.line_rejection_qty),3),3))
					frappe.db.commit()
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Manufacture"
			stock_entry.work_order = work_order_id
			stock_entry.company = work_order.company
			stock_entry.from_bom = 1
			stock_entry.naming_series = "MAT-STE-.YYYY.-"
			""" For identifying procees name to change the naming series the field is used """
			naming_status,naming_series = get_stock_entry_naming_series(spp_settings,"Moulding Entry")
			if naming_status:
				stock_entry.naming_series = naming_series
			""" End """
			stock_entry.bom_no = work_order.bom_no
			stock_entry.set_posting_time = 0
			stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
			stock_entry.stock_entry_type = "Manufacture"
			stock_entry.fg_completed_qty = flt(flt((self.weight + self.line_rejection_qty),3),3)
			if work_order.bom_no:
				stock_entry.inspection_required = frappe.db.get_value(
					"BOM", work_order.bom_no, "inspection_required"
				)
			stock_entry.from_warehouse = work_order.source_warehouse
			stock_entry.to_warehouse = work_order.fg_warehouse
			# d_spp_batch_no = get_spp_batch_date(work_order.production_item)
			bcode_resp = generate_barcode(self.scan_lot_number)
			# for x in work_order.required_items:
			# 	stock_entry.append("items",{
			# 		"item_code":x.item_code,
			resp__s = append_source_details(stock_entry,self,work_order)
			if resp__s:
				stock_entry.append("items",{
					"item_code":work_order.production_item,
					"s_warehouse":None,
					"t_warehouse":work_order.fg_warehouse,
					"stock_uom": "Kg",
					"uom": "Kg",
					"conversion_factor_uom":1,
					"is_finished_item":1,
					#"transfer_qty":flt(flt((self.weight + self.line_rejection_qty),3),3),
					"transfer_qty":flt(flt(self.weight ,3),3),
					#"qty":flt(flt((self.weight + self.line_rejection_qty),3),3),
					"qty":flt(flt(self.weight,3),3),
					"use_serial_batch_fields": 1,
					# "spp_batch_number":d_spp_batch_no,
					"spp_batch_number":self.scan_lot_number,
					"mix_barcode":bcode_resp.get("barcode_text"),
					"barcode_attach":bcode_resp.get("barcode"),
					"barcode_text":bcode_resp.get("barcode_text"),
					"source_ref_document":self.doctype,
					"source_ref_id":self.name,
					"batch_no":batch__no,
					#For avaoiding the child table only submitted issue which means the parent docstatus = 0 but child docstatus = 1
					"docstatus":0
					})
				stock_entry.blanking_dc_no = self.name
				stock_entry.insert(ignore_permissions=True)
				""" Update posting date and time """
				frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{self.moulding_date}' WHERE name = '{stock_entry.name}' ")
				""" End """
				""" Update stock entry reference """
				frappe.db.set_value(self.doctype,self.name,"stock_entry_reference",stock_entry.name)
				frappe.db.commit()
				""" End """
				# sub_entry = frappe.get_doc("Stock Entry",stock_entry.name)
				# sub_entry.docstatus = 1
				# sub_entry.save(ignore_permissions=True)
				ref_res,batch__no = generate_batch_no(batch_id = batch__no,reference_doctype = "Stock Entry",reference_name = stock_entry.name)
				if ref_res:
					update_bins(self,resp__s,spp_settings)
					# serial_no = 1
					# serial_nos = frappe.db.get_all("SPP Batch Serial",filters={"posted_date":getdate()},fields=['serial_no'],order_by="serial_no DESC")
					# if serial_nos:
					# 	serial_no = serial_nos[0].serial_no + 1
					# sl_no = frappe.new_doc("SPP Batch Serial")
					# sl_no.posted_date = getdate()
					# sl_no.compound_code = work_order.production_item
					# sl_no.serial_no = serial_no
					# sl_no.insert(ignore_permissions=True)
					frappe.db.commit()
					return {"status":"success"}
				else:
					return {"status":"failed","message":batch__no}
			else:
				return {"status":"failed","message":f'<b>Batch Details</b> with <b>Compound</b> consumption qty not found..! '}		
		else:
			return {"status":"failed","message":batch__no}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(),title="Moulding SE Error")
		return {"status":"failed","message":"Stock Entry Creation Failed"}	

def update_bins(self,resp__s,spp_settings):
	for c__bin in resp__s:
		if c__bin.get('is__consumed') and c__bin.get('is_balance_bin'):
			frappe.db.sql(f""" UPDATE `tabBlank Bin Issue Item` set is_completed=1 where name = '{c__bin.get('blank_bin_issue_item_name')}' """)
			frappe.db.sql(""" UPDATE `tabItem Bin Mapping` set qty=(%(qty)s),job_card = %(job_card)s where name=%(name)s """,{"qty":c__bin.get('balance__qty'),'job_card':c__bin.get('job_card'),"name":c__bin.get('item_bin_mapping_name')})
		elif c__bin.get('is__consumed') and not c__bin.get('is_balance_bin'):
			frappe.db.sql(""" UPDATE `tabItem Bin Mapping` set is_retired=1 , job_card = %(job_card)s where name =%(name)s """,{'job_card':c__bin.get('job_card'),"name":c__bin.get('item_bin_mapping_name')})
			frappe.db.sql(f""" UPDATE `tabBlank Bin Issue Item` set is_completed=1 where name = '{c__bin.get('blank_bin_issue_item_name')}' """)
			last_mov = frappe.db.sql(f" SELECT AMI.target_location FROM `tabAsset Movement` AM INNER JOIN `tabAsset Movement Item` AMI ON AM.name = AMI.parent WHERE AMI.asset = '{c__bin.get('bin')}' ORDER BY AMI.creation DESC LIMIT 1 ",as_dict = 1)
			if last_mov:
				if not last_mov[0].target_location == spp_settings.from_location:
					make_asset_movement(spp_settings,c__bin)
			else:
				make_asset_movement(spp_settings,c__bin)
	
def append_source_details(stock_entry,self,work_order):
	import json
	final_batch_details = []
	batch_details = json.loads(self.updated_batch_details)
	for b__ in batch_details:
		if b__.get('is__consumed'):
			match_found = False
			for exe_b in final_batch_details:
				if exe_b.get('batch_no__') == b__.get('batch_no__') and exe_b.get('spp_batch_number') == b__.get('spp_batch_number'):
					match_found = True
					exe_b['consumed__qty'] = flt((exe_b['consumed__qty'] + b__['consumed__qty']),3)
			if not match_found:
				final_batch_details.append(b__)
	for f__b in final_batch_details:
		stock_entry.append("items",{
						"item_code":self.compound,
						"s_warehouse": work_order.source_warehouse,
						"t_warehouse":None,
						"stock_uom": "Kg",
						"uom": "Kg",
						"conversion_factor_uom":1,
						"is_finished_item":0,
                        "use_serial_batch_fields": 1,
						"transfer_qty":flt(f__b.get('consumed__qty'),3),
						"qty":flt(f__b.get('consumed__qty'),3),
						"spp_batch_number":f__b.get('spp_batch_number'),
						"batch_no":f__b.get('batch_no__'),
						#For avaoiding the child table only submitted issue which means the parent docstatus = 0 but child docstatus = 1
						"docstatus":0
					})
	if self.shell_qty_nos:
		stock_entry.append("items",{
						"item_code":self.shell_item,
						"s_warehouse": self.s_source_warehouse,
						"t_warehouse":None,
						"stock_uom": "Nos",
						"uom": "Nos",
						"conversion_factor_uom":1,
						"is_finished_item":0,
						"transfer_qty":self.shell_qty_nos,
						"use_serial_batch_fields": 1,
						"qty":self.shell_qty_nos,
						"batch_no":self.s_batch,
						#For avaoiding the child table only submitted issue which means the parent docstatus = 0 but child docstatus = 1
						"docstatus":0
					})
	return batch_details

def make_asset_movement(spp_settings,x):
	asset__mov = frappe.new_doc("Asset Movement")
	asset__mov.company = "SPP"
	asset__mov.transaction_date = now()
	asset__mov.purpose = "Transfer"
	asset__mov.append("assets",{
		"asset":x.get('bin'),
		"source_location":spp_settings.to_location,
		"target_location":spp_settings.from_location,
	})
	asset__mov.insert(ignore_permissions=True)
	ass__doc = frappe.get_doc("Asset Movement",asset__mov.name)
	ass__doc.docstatus = 1
	ass__doc.save(ignore_permissions=True)

def submit_inspection_entry(self, st_entry):
    exe_insp = frappe.db.sql(f" SELECT stock_entry_reference,name,posting_date FROM `tabInspection Entry` WHERE (inspection_type = 'Line Inspection' OR inspection_type = 'Patrol Inspection' OR inspection_type = 'Lot Inspection') AND docstatus = 1 AND lot_no='{self.scan_lot_number}' ",as_dict = 1)    
    if exe_insp:
        for ins in exe_insp:
            if ins.stock_entry_reference:
                # Find the target batch number from stock entry
                target_batch = None
                for st in st_entry.items:
                    if st.t_warehouse:  # This identifies the target/output item
                        target_batch = st.batch_no
                        break
                
                if not target_batch:
                    frappe.throw("Target batch number not found in stock entry")

                # Update batch details in stock entry detail and inspection entry
                frappe.db.sql(f" UPDATE `tabStock Entry Detail` SET batch_no='{target_batch}' WHERE source_ref_document = 'Inspection Entry' AND source_ref_id = '{ins.name}' ")
                frappe.db.sql(f" UPDATE `tabInspection Entry` SET batch_no='{target_batch}',spp_batch_number='{self.scan_lot_number}' WHERE name = '{ins.name}' ")
                frappe.db.commit()

                # Get and submit the inspection entry's stock entry
                ins__exe = frappe.get_doc("Stock Entry", ins.stock_entry_reference)
                if ins__exe.docstatus == 0:
                    # Update batch numbers in all items
                    for item in ins__exe.items:
                        item.use_serial_batch_fields = 1
                        if not item.batch_no:
                            item.batch_no = target_batch
                    
                    ins__exe.docstatus = 1
                    ins__exe.save(ignore_permissions = True)
                    
                    if ins.posting_date:
                        """ Update posting date and time """
                        frappe.db.sql(f" UPDATE `tabStock Entry` SET posting_date = '{ins.posting_date}' WHERE name = '{ins__exe.name}' ")
                        """ End """

    # Update work order and job card status
    work_order_id = frappe.db.get_value("Job Card", self.job_card, "work_order")
    frappe.db.set_value("Work Order", work_order_id, "status", "Completed")
    frappe.db.set_value("Job Card", self.job_card, "docstatus", 1)
    frappe.db.set_value("Job Card", self.job_card, "status", 'Completed')
    frappe.db.commit()
	
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
def validate_operator(operator,supervisor = None):
	if supervisor:
		spp_settings = frappe.get_single("SPP Settings")
		designation = ""
		if spp_settings and spp_settings.designation_mapping:
			for desc in spp_settings.designation_mapping:
				if desc.spp_process == "Moulding Supervisor":
					if desc.designation:
						designation += f"'{desc.designation}',"
		if designation:
			designation = designation[:-1]
			check_emp = frappe.db.sql(f"""SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s AND designation IN ({designation}) """,{"barcode":operator},as_dict=1)
			if check_emp:
				return {"status":"Success","message":check_emp[0]}
			else:
				return {"status":"Failed","message":"Employee not found."}
		else:
			return {"status":"Failed","message":"Designation not mapped in SPP Settings."}
	else:
		check_emp = frappe.db.sql("""SELECT employee_name,name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s""",{"barcode":operator},as_dict=1)
		if check_emp:
			return {"status":"Success","message":check_emp[0]}
	return {"status":"Failed","message":"Employee not found."}
	
@frappe.whitelist()
def validate_lot_number(batch_no):
	try:
		job_card = frappe.db.get_value("Job Card",{"batch_code":batch_no,"operation":"Moulding"},'status')
		if not job_card:
			return {"status":"Failed","message":"The scanned lot barcode is <b>invalid</b>..!."}
		if job_card == "Completed":
			return {"status":"Failed","message":"The <b>Moulding Operation</b> for the scanned lot was completed..!"}
		check_line_inspe_entry = frappe.db.get_value("Inspection Entry",{"lot_no":batch_no,"docstatus":1,"inspection_type":"Line Inspection"})
		if check_line_inspe_entry:
			check_lot_issue = frappe.db.sql(""" SELECT BI.bin,BI.name as blank_bin_issue_item_name,B.name as blank_bin_issue_name,
							B.job_card,JB.name as job_card,B.scan_bin,JB.mould_reference,JB.no_of_running_cavities
							FROM `tabBlank Bin Issue Item` BI 
							INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
							INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
							WHERE BI.is_completed = 0 AND JB.batch_code=%(lot_no)s 
							AND B.docstatus = 1 ORDER BY B.creation ASC """,{"lot_no":batch_no},as_dict=1)
			if not check_lot_issue:
				return {"status":"Failed","message":"There is no entry for Blank Bin Issue for the scanned lot number."}
			else:
				if not check_lot_issue[0].mould_reference:
					return {"status":"Failed","message":f"The <b>Mould Referenece</b> not found in <b>Job Card - {check_lot_issue[0].job_card}</b>"}
				else:
					mould_ref = frappe.db.get_value("Asset",check_lot_issue[0].mould_reference,"item_code")
					if mould_ref:
						if check_lot_issue[0].no_of_running_cavities: 
							check_lot_issue[0].mould_reference = mould_ref
						else:
							return {"status":"Failed","message":f"The <b>No.Of.Cavity</b> not found in the <b>Job Card - {check_lot_issue[0].job_card}</b>"}
					else:
						return {"status":"Failed","message":f"The <b>Mould Referenece</b> not found in <b>Asset - {check_lot_issue[0].mould_reference}</b>"}
				all_blank__bins = []
				for bin__ in check_lot_issue:
					check_bin_release = frappe.db.sql(f" SELECT name item_bin_mapping_name,compound,spp_batch_number,qty FROM `tabItem Bin Mapping` WHERE blanking__bin = '{bin__.bin}' AND is_retired = 0 ",as_dict = 1)
					if not check_bin_release:
						return {"status":"Failed","message":f"The bin <b>{bin__.bin}</b> is already released manually, Please check <b>Item Bin Mapping</b>..!"}
					else:
						bin__.update(check_bin_release[0])
						if not bin__.compound:
							return {"status":"Failed","message":f"There is no <b>Compound</b> found in bin <b>{bin__.bin}</b>."}	
					batch_no = frappe.db.sql(f""" SELECT batch_no,docstatus,parenttype FROM `tabDelivery Note Item` WHERE spp_batch_no = '{bin__.spp_batch_number}'  """,as_dict=1)
					if not batch_no:
						spp_settings = frappe.get_single("SPP Settings")
						if not spp_settings.unit_2_warehouse:
							return {"status":"Failed","message":f"The default <b>Unit - 1 Warehouse</b> not found in <b>SPP Settings</b>..!"}	
						if not spp_settings.default_sheeting_warehouse:
							return {"status":"Failed","message":f"The default <b>Sheeting Warehouse</b> not found in <b>SPP Settings</b>..!"}	
						batch_no = frappe.db.sql(f""" SELECT SED.batch_no,SED.parenttype,SED.docstatus FROM `tabStock Entry` SE 
													INNER JOIN `tabStock Entry Detail` SED ON SED.parent=SE.name WHERE SE.stock_entry_type="Material Transfer" 
													AND SED.spp_batch_number = '{bin__.spp_batch_number}' AND SED.s_warehouse = '{spp_settings.default_sheeting_warehouse}' AND SED.t_warehouse = '{spp_settings.unit_2_warehouse}'  """,as_dict=1)
						if not batch_no:
							batch_no = frappe.db.sql(f""" SELECT SED.batch_no,SED.parenttype,SED.docstatus FROM `tabStock Entry` SE 
													INNER JOIN `tabStock Entry Detail` SED ON SED.parent=SE.name WHERE SE.stock_entry_type="Repack" 
													AND SED.spp_batch_number = '{bin__.spp_batch_number}' AND SED.t_warehouse = '{spp_settings.default_sheeting_warehouse}'  """,as_dict=1)
					if batch_no:
						if batch_no[0].docstatus == 1:
							bin__.batch_no__ =  batch_no[0].batch_no
						else:
							return {"status":"Failed","message":f"The <b>{batch_no[0].parenttype}</b> is not <b>submitted or cancelled</b>..!"}	
					else:
						""" For get f name from bom """
						f__name = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabJob Card` J ON J.bom_no = B.name WHERE J.name=%(name)s AND B.is_active=1""",{"name":bin__.job_card},as_dict=1)
						if f__name:
							return {"status":"Failed","message":f"The Batch No. not found for the item - <b>{f__name[0].item_code}</b>..!"}	
						else:
							return {"status":"Failed","message":f"The Batch No. not found for the source item..!"}
					all_blank__bins.append(bin__)
					""" End """
				f__name = frappe.db.sql(""" SELECT B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabJob Card` J ON J.bom_no = B.name WHERE J.name=%(name)s AND B.is_active=1""",{"name":bin__.job_card},as_dict=1)
				if f__name:
					bom__ = frappe.db.sql(""" SELECT B.name,BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(bom_item)s AND B.is_Active=1 """,{"bom_item":f__name[0].item},as_dict=1)
					boms__item = []
					for bm in bom__:
						boms__item.append(bm.item_code)
					for c__bin in all_blank__bins:
						c__bin.item_to_produce =  f__name[0].item
						if not c__bin.compound in boms__item:
							return {"status":"Failed","message":f"There is no active BOM found for the bin <b>Compound - {check_lot_issue[0].compound}</b>"}
				else:
					return {"status":"Failed","message":f"BOM is not found for <b>Item to Produce</b>"}
				return {"status":"Success","message":all_blank__bins}
		else:
			return {"status":"Failed","message":f"{frappe.bold('Line Inspection')} for the scanned lot was not found..!"}
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.moulding_production_entry.validate_lot_number",message=frappe.get_traceback())

@frappe.whitelist()
def validate_bin(batch_no,job_card):
	# check_retired = frappe.db.sql(""" SELECT IB.name FROM `tabItem Bin Mapping` IB
	# 							  INNER JOIN `tabBlanking Bin` BB ON IB.blanking_bin=BB.name
	# 							  WHERE BB.barcode_text=%(barcode)s AND IB.is_retired=0""",{"barcode":batch_no},as_dict=1)
	check_retired = frappe.db.sql(""" SELECT IB.name FROM `tabItem Bin Mapping` IB
								  INNER JOIN `tabAsset` A ON IB.blanking__bin=A.name
								  WHERE A.barcode_text=%(barcode)s AND IB.is_retired=0""",{"barcode":batch_no},as_dict=1)
	if not check_retired:
		return {"status":"Failed","message":"The Scanned bin already released."}

	# check_lot_issue = frappe.db.sql(""" SELECT IB.spp_batch_number,BB.bin_weight,BI.name,B.job_card,BB.name as blanking_bin FROM `tabBlank Bin Issue Item` BI 
	# 				INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
	# 				INNER JOIN `tabItem Bin Mapping` IB ON BI.bin = IB.blanking__bin
	# 				INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
	# 				INNER JOIN `tabBlanking Bin` BB ON IB.blanking_bin=BB.name
	# 				WHERE BI.is_completed = 0 AND BB.barcode_text=%(barcode)s AND IB.is_retired=0
	# 				 """,{"barcode":batch_no},as_dict=1)
	check_lot_issue = frappe.db.sql(""" SELECT IB.spp_batch_number,A.bin_weight,BI.name,B.job_card,A.name as blanking_bin,A.asset_name FROM `tabBlank Bin Issue Item` BI 
					INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
					INNER JOIN `tabItem Bin Mapping` IB ON BI.bin = IB.blanking__bin
					INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
					INNER JOIN `tabAsset` A ON IB.blanking__bin=A.name
					WHERE BI.is_completed = 0 AND A.barcode_text=%(barcode)s AND IB.is_retired=0 AND B.docstatus = 1
					 """,{"barcode":batch_no},as_dict=1)
	if not check_lot_issue:
		return {"status":"Failed","message":"The Scanned bin not issued for the Job Card "+job_card+"."}
	else:
		return {"status":"Success","bin_weight":check_lot_issue[0].bin_weight,"blanking_bin":check_lot_issue[0].blanking_bin,"asset_name":check_lot_issue[0].asset_name}	

@frappe.whitelist()
def validate_bin_weight(weight,bin,bin_Weight,prod_weight):
	item_bin = frappe.db.get_all("Item Bin Mapping",filters={"blanking__bin":bin,"is_retired":0},fields=['qty'])
	if item_bin:
		if flt(weight) <= flt(bin_Weight):
			return {"status":"Failed","message":f"The <b>Gross Weight</b> of balance bin  can't be less than the <b>Bin Weight - {bin_Weight}</b>..!"}
		if (flt(weight) - flt(bin_Weight))>(flt(item_bin[0].qty) - flt(prod_weight)):
			return {"status":"Failed","message":"The quantity in the bin <b>"+bin+"</b> is <b>"+str('%.3f' %(flt(item_bin[0].qty) - flt(prod_weight)))+"</b>"}
	else:
		return {"status":"Failed","message":f"The bin is already <b>Released</b>..!"}
	return  {"status":"Success"}

@frappe.whitelist()
def validate_tolerance(self):
	spp_settings = frappe.get_single("SPP Settings")
	total_bins_weight = frappe.db.sql(""" SELECT sum(IB.qty) as total_qty FROM `tabItem Bin Mapping` IB
						INNER JOIN `tabBlank Bin Issue Item` BI ON IB.blanking__bin = BI.bin
						INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
						WHERE IB.is_retired = 0 AND BI.is_completed=0 AND BI.docstatus = 1 AND JB.name=%(job_card)s""",{"job_card":self.job_card}
						,as_dict=1)
	if spp_settings.production_tolerance!=0 and total_bins_weight and total_bins_weight[0].total_qty:
		from_wt = total_bins_weight[0].total_qty-((total_bins_weight[0].total_qty * spp_settings.production_tolerance)/100)
		to_wt = total_bins_weight[0].total_qty + ((total_bins_weight[0].total_qty * spp_settings.production_tolerance)/100)
		if not self.weight>=from_wt and self.weight<to_wt:
			return {"status":True,"message":"Mat bin weight should be between <b>"+str('%.3f' %(from_wt))+"</b> to <b>"+'%.3f' %(to_wt)+"</b>"}
	return {"status":True}
