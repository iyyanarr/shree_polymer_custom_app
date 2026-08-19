# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, duration_to_seconds, flt, add_to_date, update_progress_bar, format_time, formatdate, getdate, nowdate, now
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series,generate_batch_no,delete_batches,delete_stock_entry_safely
from erpnext.stock.doctype.batch.batch import get_batch_qty


class MouldingProductionEntry(Document):
    updated_batch_details = []
    line_rejection_qty = 0.0
    compound_available_qty = 0.0
    # This function is used to sort the 'Asset' print cards 'check asset print formats for details'

    def sort_bins_for_print(self, values):
        result = []
        splited_series = []
        non_int_series = []
        sorted_values = []
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
        # Detect Injection Moulding press from workstation name
        if self.job_card:
            workstation = frappe.db.get_value("Job Card", self.job_card, "workstation")
            if workstation:
                ws_name = frappe.db.get_value("Workstation", workstation, "workstation_name") or ""
                # Check for "INJECTION" or "INJUCTION" (handle typo in database)
                self.is_injection_moulding = 1 if ("INJECTION" in ws_name.upper() or "INJUCTION" in ws_name.upper()) else 0
            else:
                self.is_injection_moulding = 0
        else:
            self.is_injection_moulding = 0
        
        self.validate_get_line_ins_qty()
        if getdate(self.moulding_date) > getdate():
            frappe.throw(
                "The <b>Posting Date</b> can't be greater than <b>Today Date</b>..!")
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
                    frappe.throw(
                        "Please scan and add atleast one <b>Balance Bin</b>..!")
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
        self.weight = flt(self.weight, 3)
        
        # Calculate total output weight (Produced + Rejection + Purge + Leakage)
        total_output_weight = flt(self.weight + self.line_rejection_qty + flt(self.purged_compound) + flt(self.compound_leakage), 3)
        self.weight_without_shell = total_output_weight

        s_resp = validate_shell(self)
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
                self.weight_without_shell = flt(total_output_weight - s_resp.get('total_shell_qty_in_kgs'), 3)
            else:
                self.weight_without_shell = total_output_weight

    def validate_inspection_qty(self, batch_no):
        return {"status": "success"}
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
        # Fetch theoretical rejection weight instead of weighed rejection
        ins_info = frappe.db.get_all("Inspection Entry", {"lot_no": self.scan_lot_number, "docstatus": 1, "inspection_type": ["in", ["Line Inspection", "Patrol Inspection"]]}, [
            "name", "total_rejected_qty"])

        total_rejected_qty_nos = 0
        if ins_info:
            for ins in ins_info:
                total_rejected_qty_nos += flt(ins.total_rejected_qty, 3)

        # Get Avg Blank Weight from Mould Specification
        avg_blank_weight_kg = 0.0
        mould_spec = frappe.db.get_value("Mould Specification", 
            {"mould_ref": self.mould_reference, "compound_code": self.compound, "mould_status": "ACTIVE"}, 
            "avg_blank_wtproduct_gms")
        
        if mould_spec:
            avg_blank_weight_kg = flt(mould_spec, 3) / 1000
        else:
            # Fallback to 0 if not found, but log it
            frappe.log_error(title="Mould Spec Missing", message=f"No Active Mould Spec found for {self.mould_reference}")

        self.line_rejection_qty = flt(total_rejected_qty_nos * avg_blank_weight_kg, 3)

    def cmpr_balbin_get_cmp_qty(self):
        import json
        self.updated_batch_details = json.loads(self.batch_details)
        # Reset before recomputing so this is idempotent across multiple validate
        # passes. validate() runs on both insert and submit; when a caller does
        # doc.insert() then doc.submit() on the SAME in-memory object (the bridge
        # does exactly this), the un-reset "+=" accumulated compound_available_qty
        # twice (e.g. 0.9 -> 1.8), which then HALVED the recomputed consumed qty in
        # validate_comsumption_details (live: MLDPE-32460 consumed 0.255 vs the
        # 0.51 Console sent). The native form submits via two separate requests so
        # it never doubled and never surfaced this. Reset makes it correct for both.
        self.compound_available_qty = 0
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
                    # 🆕 NEW VALIDATION: Check actual warehouse stock before creating Stock Entry
                    stock_val = validate_actual_warehouse_stock(self)
                    if stock_val.get('status') == 'failed':
                        frappe.throw(stock_val.get('message'))
                    
                    # Only proceed if stock validation passed
                    ins_info = frappe.db.get_value("Inspection Entry", {"lot_no": self.scan_lot_number, "docstatus": 1, "inspection_type": "Line Inspection"}, [
                                                   "stock_entry_reference", "name"], as_dict=1)
                    if ins_info:
                        resp_ = make_stock_entry(self)
                        if resp_.get('status') == 'failed':
                            rollback_entries(self, resp_.get('message'))
                            # rollback_entries() resets docstatus to 0 and
                            # commits, but Frappe only aborts a submit when
                            # on_submit() raises. Without this throw, the
                            # submit continues and this MPE ends up
                            # docstatus=1 — "Success" — with no Stock Entry.
                            frappe.throw(resp_.get('message') or "Stock Entry creation failed")
                        else:
                            frappe.db.set_value(
                                self.doctype, self.name, "batch_details", self.updated_batch_details)
                            # frappe.db.commit() (Removed for atomicity)
                            self.reload()
                    else:
                        frappe.throw(
                            f"<b>Stock Entry</b> reference not found in the <b>Line Inspection</b> entry..!")
                else:
                    frappe.throw(vcd.get('message'))
            else:
                frappe.throw(qty_val_resp.get('message'))
        else:
            frappe.throw(cavity_val.get('message'))

    def manual_on_submit(self):
        """
        ⚠️ DEPRECATED: This function is no longer used in the new flow.
        Stock Entry is now submitted immediately in make_stock_entry().
        
        This function is kept for backward compatibility and will be removed in future versions.
        """
        print("\n⚠️ WARNING: manual_on_submit() was called but is deprecated!")
        print("Stock Entry should already be submitted by make_stock_entry()")
        
        if self.stock_entry_reference:
            try:
                exe__stentry = frappe.get_doc("Stock Entry", self.stock_entry_reference)
                
                # Check if already submitted
                if exe__stentry.docstatus == 1:
                    print(f"✅ Stock Entry {self.stock_entry_reference} already submitted")
                    print("No action needed - new flow working correctly")
                    return
                
                # If somehow still draft, submit it (fallback)
                print(f"⚠️ Stock Entry still in draft - submitting as fallback")
                
                # Check for existing Serial and Batch Bundles
                for item in exe__stentry.items:
                    if item.serial_and_batch_bundle:
                        existing_bundle = frappe.db.exists(
                            "Serial and Batch Bundle",
                            item.serial_and_batch_bundle
                        )
                        if existing_bundle:
                            item.serial_no = None
                            item.batch_no = None
                
                # Update use_serial_batch_fields for all items
                for item in exe__stentry.items:
                    item.use_serial_batch_fields = 1
                
                # Submit stock entry
                exe__stentry.docstatus = 1
                exe__stentry.save(ignore_permissions=True)
                
                # Update moulding date
                if self.moulding_date:
                    frappe.db.sql(f"""
                        UPDATE `tabStock Entry` 
                        SET posting_date = '{self.moulding_date}' 
                        WHERE name = '{exe__stentry.name}'
                    """)
                
                frappe.db.commit()
                print("Fallback submission complete")
                
            except Exception as e:
                error_msg = f"""
====== Error in Manual Submit (Deprecated) ======
Document: {self.name}
Stock Entry: {self.stock_entry_reference}
Error: {str(e)}
Traceback: {frappe.get_traceback()}
=================================
"""
                frappe.log_error(
                    title=f"Moulding production entry manual_on_submit (deprecated) failed - {self.name}",
                    message=error_msg
                )
        else:
            frappe.throw("Stock Entry Reference not found in <b>Moulding Production Entry</b>")

    def on_cancel(self):
        try:
            se = None
            if self.stock_entry_reference:
                try:
                    if frappe.db.get_value("Stock Entry", self.stock_entry_reference, "name"):
                        se = frappe.get_doc(
                            "Stock Entry", self.stock_entry_reference)
                        if se.docstatus == 1:
                            se.docstatus = 2
                            se.save(ignore_permissions=True)
                except Exception:
                    frappe.db.rollback()
                    frappe.throw("Can't cancel/change Stock Entry..!")
                if se:
                    try:
                        frappe.db.sql(
                            f"UPDATE `tabWork Order` SET status='Not Started' WHERE name='{se.work_order}'")
                        frappe.db.sql(
                            f"UPDATE `tabWork Order Operation` SET status='Pending' WHERE parent='{se.work_order}' AND parentfield='operations' AND parenttype='Work Order' ")
                        frappe.db.sql(
                            f"UPDATE `tabJob Card` SET status='Work In Progress',docstatus=0 WHERE work_order='{se.work_order}'")
                    except Exception:
                        frappe.db.rollback()
                        frappe.throw(
                            "Can't cancel/change Work Order,Job card .. !")
            else:
                frappe.throw("Stock Entry reference not found.")
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(
                title=f"{self.doctype }- on cancel failed", message=frappe.get_traceback())
            self.reload()


def validate_cavity(self):
    if self.no_of_cavity_in_mspec:
        if not float(self.no_of_cavity_in_mspec) >= float(self.no_of_running_cavities):
            return {"message": f"The <b>No.of.Cavitiy - {self.no_of_running_cavities}</b> can't be greater than - <b>{self.no_of_cavity_in_mspec}</b>..! "}
        else:
            return {"status": "success"}
    else:
        return {"message": f"The <b>No.of.Cavities</b> from <b>Job Card</b> not fetched.<br>Please check the Job Card..!"}


def rollback_entries(self, msg):
    try:
        # Log the cause of the rollback
        frappe.log_error(title=f"MPE Rollback Triggered: {self.name}", message=f"Reason: {msg}")

        self.reload()
        
        # 1. Rollback Main Stock Entry
        stock_name = frappe.db.get_value("Stock Entry", {"blanking_dc_no": self.name}, "name")
        if stock_name:
            delete_stock_entry_safely(stock_name)

        # 2. Reset Job Card
        frappe.db.set_value("Job Card", self.job_card, {"docstatus": 0, "status": "Work In Progress"})
        
        # 3. Reset Work Order
        work_order = frappe.db.get_value("Job Card", self.job_card, "work_order")
        if work_order:
            frappe.db.set_value("Work Order", work_order, {"status": "In Process", "produced_qty": 0})

        # 4. Rollback Inspection Entries and their Stock Entries (DISABLED as per requirement)
        # exe_insp = frappe.db.get_all("Inspection Entry", 
        #     filters={
        #         "lot_no": self.scan_lot_number, 
        #         "docstatus": 1,
        #         "inspection_type": ["in", ["Line Inspection", "Patrol Inspection", "Lot Inspection"]]
        #     },
        #     fields=["name", "stock_entry_reference"]
        # )
        
        # if exe_insp:
        #     for ins in exe_insp:
        #         # Delete the Stock Entry linked to Inspection
        #         if ins.stock_entry_reference:
        #             delete_stock_entry_safely(ins.stock_entry_reference)
                
        #         # Revert Inspection Entry to Draft (Using SQL to avoid validation loops if any)
        #         frappe.db.set_value("Inspection Entry", ins.name, "docstatus", 0)

        # 5. Reset MPE
        self.db_set("docstatus", 0)
        self.db_set("stock_entry_reference", None)
        
        # 6. Delete the Batch
        del__resp, batch__no = delete_batches([self.scan_lot_number])
        
        frappe.db.commit()
        self.reload()
        
        if not del__resp:
            frappe.msgprint(batch__no)
            
    except Exception:
        frappe.db.rollback()
        self.reload()
        frappe.log_error(title="rollback_entries", message=frappe.get_traceback())
        frappe.msgprint("Something went wrong..Not able to rollback..!")
    frappe.throw(msg)


def manual_rollback_entries(self, msg):
    try:
        stock__id = frappe.db.get_value("Stock Entry", {"blanking_dc_no": self.name}, [
                                        "name", "work_order"], as_dict=1)
        if stock__id:
            # Use the new safe deletion utility for the main stock entry
            delete_stock_entry_safely(stock__id.name)
            if stock__id.work_order:
                frappe.db.set_value(
                    "Work Order", stock__id.work_order, "produced_qty", 0)
        
        # Revert the MPE docstatus to 0
        frappe.db.sql(""" UPDATE `tabStock Entry` SET docstatus = 0 WHERE blanking_dc_no=%(dc_no)s""", {
                      "dc_no": self.name})
        
        exe_insp = frappe.db.sql(
            f" SELECT stock_entry_reference,name FROM `tabInspection Entry` WHERE (inspection_type = 'Line Inspection' OR inspection_type = 'Patrol Inspection' OR inspection_type = 'Lot Inspection') AND docstatus = 1 AND lot_no='{self.scan_lot_number}' ORDER BY inspection_type DESC LIMIT 1 ", as_dict=1)
        if exe_insp:
            for ins in exe_insp:
                try:
                    if ins.stock_entry_reference:
                        # Use the new safe deletion utility for inspection-related stock entries
                        delete_stock_entry_safely(ins.stock_entry_reference)
                    
                    # Revert Inspection Entry to Draft
                    exe_ins = frappe.get_doc("Inspection Entry", ins.name)
                    exe_ins.db_set("docstatus", 0)
                    frappe.db.commit()
                except Exception:
                    frappe.db.rollback()
                    frappe.log_error(title="manual_rollback_entries - Inspection Entry",
                                     message=frappe.get_traceback())
                    frappe.msgprint(f"Something went wrong while rolling back Inspection Entry {ins.name}..!")
        frappe.msgprint(msg)
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title="manual_rollback_entries",
                         message=frappe.get_traceback())
        frappe.msgprint("Something went wrong..Not able to rollback..!")


def validate_comsumption_details(self):
    try:
        import json
        consumed_qty = 0.0
        weight = flt(self.weight_without_shell, 3)
        inital_validate = True
        
        # Create a mapping of bin codes to their actual remaining weights from balance_bins child table
        balance_bin_weights = {}
        if hasattr(self, 'balance_bins') and self.balance_bins:
            for balance_bin in self.balance_bins:
                balance_bin_weights[balance_bin.bin_code] = flt(balance_bin.net_weight, 3)
        
        # Handle balance bins separately - they need special treatment
        for is__bb in self.updated_batch_details:
            if is__bb.get('is_balance_bin'):
                # Store original values for audit trail
                is__bb['consumed__qty_while_balance_bin'] = is__bb.get('consumed__qty')
                is__bb['balance__qty_while_balance_bin'] = is__bb.get('balance__qty')
                
                # Calculate proportional consumption for this production run ONLY
                is__bb_compound_qty = flt(flt(is__bb.get('consumed__qty') / self.compound_available_qty, 3) * flt(weight, 3), 3)
                is__bb['consumed__qty'] = is__bb_compound_qty
                consumed_qty = flt(consumed_qty + is__bb_compound_qty, 3)
                
                # ✅ FIX: For balance bins, use actual measured remaining weight
                bin_code = is__bb.get('bin')
                if bin_code in balance_bin_weights:
                    # Use the physically measured remaining weight
                    is__bb["balance__qty"] = balance_bin_weights[bin_code]
                    frappe.log_error(
                        title="Balance Bin Corrected", 
                        message=f"Bin {bin_code}: Used actual weight {balance_bin_weights[bin_code]} instead of calculated {flt((flt(is__bb['qty'], 3) - is__bb_compound_qty), 3)}"
                    )
                else:
                    # Fallback to calculated method if balance bin data not found
                    frappe.log_error(
                        title="Balance Bin Missing Data", 
                        message=f"Bin {bin_code}: No balance_bins data found, using calculated method"
                    )
                    is__bb["balance__qty"] = flt((flt(is__bb["qty"], 3) - is__bb_compound_qty), 3)
        
        # Handle fresh bins with corrected inventory logic
        if consumed_qty < weight:
            for k in self.updated_batch_details:
                if not k.get('is_balance_bin'):
                    # Proportional share logic
                    compound__qty_share = flt((flt(k["qty"], 3) / self.compound_available_qty) * flt(weight, 3), 3)
                    
                    if inital_validate and weight <= compound__qty_share:
                        consumed_qty = weight
                        k["consumed__qty"] = weight
                        k["balance__qty"] = flt((flt(k["qty"], 3) - weight), 3) # Fix: Subtract from actual qty
                        k["is__consumed"] = 1
                        break
                    else:
                        inital_validate = False
                        remaining_to_consume = flt(weight - consumed_qty, 3)
                        
                        if remaining_to_consume >= compound__qty_share:
                            # Consume the whole share
                            consumed_qty = flt(consumed_qty + compound__qty_share, 3)
                            k["consumed__qty"] = compound__qty_share
                            k["balance__qty"] = flt((flt(k["qty"], 3) - compound__qty_share), 3) # Fix: Subtract share from actual
                            k["is__consumed"] = 1
                        else:
                            # Consume only what's needed
                            k["consumed__qty"] = remaining_to_consume
                            consumed_qty = weight
                            k["balance__qty"] = flt((flt(k["qty"], 3) - remaining_to_consume), 3) # Fix: Subtract from actual
                            k["is__consumed"] = 1
                            break
        
        # Validation: Shortage Block
        if flt(weight, 3) > flt(self.compound_available_qty, 3):
            frappe.throw(
                f"<b>Insufficient compound stock scanned!</b><br>"
                f"Net Compound Required: {weight} Kg<br>"
                f"Available in Scanned Bins: {self.compound_available_qty} Kg<br><br>"
                f"Please scan more bins or check the weights."
            )
        
        # ...existing validation code...
        vcwspps = validate_consumption_with_spp_settings(self)
        if vcwspps.get('status') == "success":
            self.updated_batch_details = json.dumps(self.updated_batch_details)
            return {"status": 'success'}
        else:
            return vcwspps
    except Exception:
        frappe.log_error(title="validate_comsumption_details", message=frappe.get_traceback())
        return {"status": "failed", "message": "Something went wrong, not able to calculate <b>Consumption Qty</b>..!"}


def validate_consumption_with_spp_settings(self):
    spp_settings = frappe.get_single("SPP Settings")
    if not spp_settings.mat_percentage:
        return {"status": "failed", "message": "Minimum '%' of Compound Consumption not mapped in <p>SPP Settings</p>. "}
    prod_one_perc = flt(self.weight_without_shell/100, 3)
    # As per arun instruction when round three precision it will give zero so use 0.001
    if not prod_one_perc:
        prod_one_perc = 0.001
    # frappe.log_error(title="--prod_one_perc",message=prod_one_perc)
    comp_perce_in_prod = flt(
        flt(self.compound_available_qty, 3) / prod_one_perc, 3)
    # frappe.log_error(title="--comp_perce_in_prod",message=comp_perce_in_prod)
    if comp_perce_in_prod >= float(spp_settings.mat_percentage):
        return {"status": "success"}
    else:
        # return {"status":"failed","message":f"The <b>Compound Consumption - {comp_perce_in_prod}%</b> is less than the <b>{spp_settings.mat_percentage}%</b> of <b>Produced Qty</b>..!"}
        return {"status": "failed", "message": f"The scanned <b>Bin Wt</b> less than the <b>Produced Qty</b>, Check if you have missed scanning any bins."}


def validate_mat_qty(self):
    try:
        # Total material available (Compound available according to bins + Shells)
        total_available_qty = (
            flt(flt(self.compound_available_qty, 3) + flt(self.shell_qty_kgs, 3), 3))
        
        # Total material produced/consumed (Finished + Rejection + Purge + Leakage)
        total_required_qty = flt(self.weight + self.line_rejection_qty + flt(self.purged_compound) + flt(self.compound_leakage), 3)
        
        spp_settings = frappe.get_single("SPP Settings")
        if not spp_settings.maximum__allowed_qty and spp_settings.maximum__allowed_qty != 0:
            return {"status": "failed", "message": "The '%' of excess Qty allowed for the <b>Production Entry</b> not mapped in <b>SPP Settings</b>..!"}
        
        if not total_available_qty == total_required_qty:
            if total_required_qty > total_available_qty:
                if spp_settings.maximum__allowed_qty:
                    one_percen = flt(total_available_qty / 100, 3)
                    actual_percen = flt(total_required_qty / one_percen, 3)
                    allowd_percen = flt(100.0 + spp_settings.maximum__allowed_qty, 3)
                    if actual_percen > allowd_percen:
                        total_with_extra_qty = flt(spp_settings.maximum__allowed_qty * one_percen, 3)
                        return {"status": "failed", "message": f"The <b>Total Required Qty (Prod+Rej+Purge) - {total_required_qty} kgs</b> should be less than or equal to total <b>Available Qty -> {str(flt(self.compound_available_qty,3)) + '+ ' + str(total_with_extra_qty) } {' + ' + str(flt(self.shell_qty_kgs,3)) +' = ' +str(flt(total_available_qty + total_with_extra_qty,3)) if self.shell_qty_kgs else ' = ' +str(flt(total_available_qty + total_with_extra_qty,3))} Kgs</b>"}
                elif spp_settings.maximum__allowed_qty == 0:
                    return {"status": "failed", "message": f"The <b>Total Required Qty (Prod+Rej+Purge) - {total_required_qty} kgs</b> should be less than or equal to total <b>Available Qty -> {flt(self.compound_available_qty,3)} {'+ ' + str(flt(self.shell_qty_kgs,3))+ ' = ' +str(total_available_qty) if self.shell_qty_kgs else ''} Kgs</b>"}
        return {"status": 'success'}
    except Exception:
        frappe.log_error(title="error in validate mat qty",
                         message=frappe.get_traceback())
        return {"status": "failed", "message": "Something went wrong, not able to validate <b>Produced Qty</b>..!"}


def validate_actual_warehouse_stock(self):
    """
    CONDITION 2: Validate that each batch has sufficient stock in the warehouse
    
    This function:
    1. Reads calculated consumption details from validate_comsumption_details()
    2. Queries actual warehouse stock for each batch
    3. Compares required qty vs available qty
    4. Returns error if insufficient stock found
    
    NOTE: This is a READ-ONLY validation function
    - Does NOT create any documents
    - Does NOT modify any data
    - Does NOT trigger any automated flows
    - Only STOPS submission if stock is insufficient
    """
    try:
        import json
        
        # Step 1: Parse batch details (already calculated by validate_comsumption_details)
        if isinstance(self.updated_batch_details, str):
            batch_details = json.loads(self.updated_batch_details)
        else:
            batch_details = self.updated_batch_details
        
        # Step 2: Get source warehouse from Work Order
        work_order = frappe.db.get_value("Job Card", self.job_card, "work_order")
        if not work_order:
            return {"status": "failed", "message": "Work Order not found for Job Card"}
        
        source_warehouse = frappe.db.get_value("Work Order", work_order, "source_warehouse")
        if not source_warehouse:
            return {"status": "failed", "message": f"Source warehouse not found in Work Order {work_order}"}
        
        # Step 3: Consolidate consumption by batch (handle multiple bins with same batch)
        batch_consumption = {}
        for batch in batch_details:
            # Only check batches that will be consumed
            if not batch.get('is__consumed'):
                continue
            
            # Skip balance bins (already validated during scanning)
            if batch.get('is_balance_bin'):
                continue
            
            batch_no = batch.get('batch_no__')
            consumed_qty = flt(batch.get('consumed__qty'), 3)
            
            # Skip if no batch or no consumption
            if not batch_no or consumed_qty <= 0:
                continue
            
            # Consolidate consumption for same batch from multiple bins
            if batch_no in batch_consumption:
                batch_consumption[batch_no]['consumed_qty'] = flt(
                    batch_consumption[batch_no]['consumed_qty'] + consumed_qty, 3
                )
            else:
                batch_consumption[batch_no] = {
                    'batch_no': batch_no,
                    'compound': batch.get('compound'),
                    'consumed_qty': consumed_qty,
                    'spp_batch_number': batch.get('spp_batch_number')
                }
        
        # Step 4: Check warehouse stock for each batch
        shortages = []
        for batch_no, batch_info in batch_consumption.items():
            # Use erpnext native get_batch_qty to get stock info (READ-ONLY)
            available_qty = get_batch_qty(
                batch_no=batch_no,
                warehouse=source_warehouse,
                item_code=batch_info['compound']
            )
            available_qty = flt(available_qty, 3)
            required_qty = flt(batch_info['consumed_qty'], 3)
            
            # Check if stock is insufficient
            if available_qty < required_qty:
                shortages.append({
                    'batch_no': batch_no,
                    'spp_batch_number': batch_info.get('spp_batch_number', 'N/A'),
                    'required': required_qty,
                    'available': available_qty,
                    'shortage': flt(required_qty - available_qty, 3)
                })
        
        # Step 5: Return result
        if shortages:
            # Format error message as HTML table
            error_message = "<b>Insufficient Stock in Warehouse</b><br><br>"
            error_message += "<table border='1' style='border-collapse: collapse; width: 100%; font-size: 13px;'>"
            error_message += "<thead><tr style='background-color: #f8f9fa;'>"
            error_message += "<th style='padding: 8px; text-align: left; border: 1px solid #dee2e6;'>Batch No</th>"
            error_message += "<th style='padding: 8px; text-align: left; border: 1px solid #dee2e6;'>SPP Batch No</th>"
            error_message += "<th style='padding: 8px; text-align: right; border: 1px solid #dee2e6;'>Required (Kg)</th>"
            error_message += "<th style='padding: 8px; text-align: right; border: 1px solid #dee2e6;'>Available (Kg)</th>"
            error_message += "<th style='padding: 8px; text-align: right; border: 1px solid #dee2e6;'>Shortage (Kg)</th>"
            error_message += "</tr></thead><tbody>"
            
            for shortage in shortages:
                error_message += "<tr>"
                error_message += f"<td style='padding: 8px; border: 1px solid #dee2e6;'>{shortage['batch_no']}</td>"
                error_message += f"<td style='padding: 8px; border: 1px solid #dee2e6;'>{shortage['spp_batch_number']}</td>"
                error_message += f"<td style='padding: 8px; text-align: right; border: 1px solid #dee2e6;'>{shortage['required']:.3f}</td>"
                error_message += f"<td style='padding: 8px; text-align: right; border: 1px solid #dee2e6;'>{shortage['available']:.3f}</td>"
                error_message += f"<td style='padding: 8px; text-align: right; border: 1px solid #dee2e6; color: #dc3545; font-weight: bold;'>{shortage['shortage']:.3f}</td>"
                error_message += "</tr>"
            
            error_message += "</tbody></table>"
            error_message += f"<br><b>Source Warehouse:</b> {source_warehouse}"
            error_message += "<br><br><i>Please ensure sufficient stock is available before submitting.</i>"
            
            return {"status": "failed", "message": error_message}
        
        # All batches have sufficient stock
        return {"status": "success"}
        
    except Exception as e:
        frappe.log_error(
            title="validate Error",
            message=f"Error : {str(e)}\n{frappe.get_traceback()}"
        )
        return {
            "status": "failed",
            "message": "Error validating warehouse stock. Please contact system administrator."
        }


def validate_shell(self):
    selected_shell_batch = None
    total_shell_qty_in_kgs = 0
    total_shell_qty_in_nos = 0
    shell_item = None
    spp_settings = frappe.get_single("SPP Settings")
    if not spp_settings.unit_2_warehouse:
        frappe.throw(
            f'<b>Unit - 2 Warehouse</b> is not mapped in <b>SPP Settings</b>..!')
    bom = frappe.db.get_value("Job Card", self.job_card, "bom_no")
    shell_details = frappe.db.sql(f""" SELECT BI.item_code FROM `tabBOM Item` BI 
			       						INNER JOIN `tabBOM` B ON B.name = BI.parent
			       						INNER JOIN `tabItem` I ON I.name = BI.item_code
			       						WHERE I.item_group = 'Shell' AND B.name = '{bom}' """, as_dict=1)
    if shell_details:
        check_uom = frappe.db.get_all("UOM Conversion Detail", filters={
                                      "parent": shell_details[0].item_code, "uom": "Kg"}, fields=['conversion_factor'])
        if check_uom:
            shell_item = shell_details[0].item_code
            total_shell_qty_in_nos = self.number_of_lifts * self.no_of_running_cavities
            
            # Use shell weight from Mould Specification if available
            shell_weight_gms = 0.0
            mould_spec = frappe.db.get_value("Mould Specification", 
                {"mould_ref": self.mould_reference, "compound_code": self.compound, "mould_status": "ACTIVE"}, 
                "shell_weight")
            
            if mould_spec:
                shell_weight_gms = flt(mould_spec, 3)
            else:
                # Fallback to UOM conversion
                shell_weight_gms = flt(1000 / check_uom[0].conversion_factor, 3)
            
            total_shell_qty_in_kgs = flt((shell_weight_gms / 1000) * total_shell_qty_in_nos, 3)
            query = f""" SELECT B.batch_id,IBSB.qty batch_qty FROM `tabBatch` B 
							INNER JOIN `tabItem Batch Stock Balance` IBSB ON 
								IBSB.batch_no = B.batch_id AND IBSB.item_code = B.item
							WHERE B.item = '{shell_details[0].item_code}' AND IBSB.warehouse = '{spp_settings.unit_2_warehouse}'
								AND B.disabled = 0 AND B.expiry_date >= CURDATE() """
            stock_info = frappe.db.sql(query, as_dict=1)
            if stock_info:
                for k in stock_info:
                    if k.batch_qty >= total_shell_qty_in_nos:
                        selected_shell_batch = k.batch_id
                        break
                if not selected_shell_batch:
                    return {'status': 'failed', 'message': f'There is no enough <b>Stock</b> is found for the shell item - <b>{shell_details[0].item_code}</b>'}
            else:
                return {'status': 'failed', 'message': f'<b>Stock</b> is not found for the shell item - <b>{shell_details[0].item_code}</b>'}
        else:
            return {'status': 'failed', 'message': f'<b>UOM</b> conversion factor in <b>Kgs</b> not found for the item - <b>{shell_details[0].item_code}</b>'}
        return {'status': 'success', 'is_shell_item_found': True, 'warehouse': spp_settings.unit_2_warehouse, 'batch_id': selected_shell_batch, 'total_shell_qty_in_kgs': total_shell_qty_in_kgs, 'total_shell_qty_in_nos': total_shell_qty_in_nos, 'shell_item': shell_item}
    return {'status': 'success', 'is_shell_item_found': False}


def make_stock_entry(self):
    try:
        production__item = frappe.db.get_value("Work Order", frappe.db.get_value(
            "Job Card", self.job_card, "work_order"), "production_item")
        batch__rep, batch__no = generate_batch_no(
            batch_id="T"+self.scan_lot_number, item=production__item, qty=flt(flt((self.weight + self.line_rejection_qty), 3), 3))
        if batch__rep:
            jc = frappe.get_doc("Job Card", self.job_card)
            for time_log in jc.time_logs:
                time_log.completed_qty = flt(
                    flt((self.weight + self.line_rejection_qty), 3), 3)
                time_log.time_in_mins = 1
                time_log.employee = self.employee
            jc.total_completed_qty = flt(
                flt((self.weight + self.line_rejection_qty), 3), 3)
            jc.for_quantity = flt(
                flt((self.weight + self.line_rejection_qty), 3), 3)
            jc.number_of_lifts = self.number_of_lifts
            jc.no_of_running_cavities = self.no_of_running_cavities
            jc.cure_time = self.curing_time
            if self.special_instructions:
                jc.remarks = self.special_instructions
            jc.save(ignore_permissions=True)
            
            spp_settings = frappe.get_single("SPP Settings")
            if not spp_settings.from_location:
                frappe.throw(
                    "Asset Movement <b>From location</b> not mapped in SPP settings")
            if not spp_settings.to_location:
                frappe.throw(
                    "Asset Movement <b>To location</b> not mapped in SPP settings")
            
            work_order_id = frappe.db.get_value(
                "Job Card", self.job_card, "work_order")
            work_order = frappe.get_doc("Work Order", work_order_id)
            if work_order.operations:
                for operation in work_order.operations:
                    frappe.db.set_value("Work Order Operation", operation.name, "completed_qty", flt(
                        flt((self.weight + self.line_rejection_qty), 3), 3))
                    frappe.db.commit()
            
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.purpose = "Manufacture"
            stock_entry.work_order = work_order_id
            stock_entry.company = work_order.company
            stock_entry.from_bom = 1
            stock_entry.naming_series = "MAT-STE-.YYYY.-"
            
            """ For identifying procees name to change the naming series the field is used """
            naming_status, naming_series = get_stock_entry_naming_series(
                spp_settings, "Moulding Entry")
            if naming_status:
                stock_entry.naming_series = naming_series
            """ End """
            
            stock_entry.bom_no = work_order.bom_no
            stock_entry.set_posting_time = 0
            stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
            stock_entry.stock_entry_type = "Manufacture"
            stock_entry.fg_completed_qty = flt(
                flt((self.weight + self.line_rejection_qty), 3), 3)
            if work_order.bom_no:
                stock_entry.inspection_required = frappe.db.get_value(
                    "BOM", work_order.bom_no, "inspection_required"
                )
            stock_entry.from_warehouse = work_order.source_warehouse
            stock_entry.to_warehouse = work_order.fg_warehouse
            
            bcode_resp = generate_barcode(self.scan_lot_number)
            resp__s = append_source_details(stock_entry, self, work_order)
            
            if resp__s:
                stock_entry.append("items", {
                    "item_code": work_order.production_item,
                    "s_warehouse": None,
                    "t_warehouse": work_order.fg_warehouse,
                    "stock_uom": "Kg",
                    "uom": "Kg",
                    "conversion_factor_uom": 1,
                    "is_finished_item": 1,
                    "transfer_qty": flt(flt(self.weight, 3), 3),
                    "qty": flt(flt(self.weight, 3), 3),
                    "use_serial_batch_fields": 1,
                    "spp_batch_number": self.scan_lot_number,
                    "mix_barcode": bcode_resp.get("barcode_text"),
                    "barcode_attach": bcode_resp.get("barcode"),
                    "barcode_text": bcode_resp.get("barcode_text"),
                    "source_ref_document": self.doctype,
                    "source_ref_id": self.name,
                    "batch_no": batch__no,
                    "docstatus": 0
                })
                stock_entry.blanking_dc_no = self.name
                stock_entry.insert(ignore_permissions=True)
                
                """ Update posting date and time """
                frappe.db.sql(
                    f" UPDATE `tabStock Entry` SET posting_date = '{self.moulding_date}' WHERE name = '{stock_entry.name}' ")
                """ End """
                
                """ Update stock entry reference """
                frappe.db.set_value(self.doctype, self.name,
                                    "stock_entry_reference", stock_entry.name)
                # frappe.db.commit() (Removed for atomicity)
                """ End """
                
                ref_res, batch__no = generate_batch_no(
                    batch_id=batch__no, reference_doctype="Stock Entry", reference_name=stock_entry.name)
                
                if ref_res:
                    # 🆕 NEW: Submit Stock Entry immediately
                    print(f"\n🚀 Submitting Stock Entry immediately: {stock_entry.name}")
                    stock_entry_doc = frappe.get_doc("Stock Entry", stock_entry.name)
                    
                    # Handle Serial and Batch Bundles
                    for item in stock_entry_doc.items:
                        if item.serial_and_batch_bundle:
                            existing_bundle = frappe.db.exists(
                                "Serial and Batch Bundle",
                                item.serial_and_batch_bundle
                            )
                            if existing_bundle:
                                item.serial_no = None
                                item.batch_no = None
                        item.use_serial_batch_fields = 1
                    
                    # Submit the stock entry
                    stock_entry_doc.docstatus = 1
                    stock_entry_doc.save(ignore_permissions=True)
                    print(f"✅ Stock Entry {stock_entry.name} submitted successfully")
                    
                    # 🛡️ NEW FALLBACK: Submit Line & Patrol inspection stock entries immediately
                    submit_inspection_stock_entries_from_moulding(self, stock_entry_doc)
                    
                    # Update bins after successful submission
                    update_bins(self, resp__s, spp_settings)
                    
                    # 🆕 NEW: Complete Job Card immediately
                    print(f"\n🏁 Completing Job Card: {self.job_card}")
                    frappe.db.set_value("Job Card", self.job_card, "docstatus", 1)
                    frappe.db.set_value("Job Card", self.job_card, "status", 'Completed')
                    
                    # 🆕 NEW: Complete Work Order immediately
                    print(f"🏁 Completing Work Order: {work_order_id}")
                    frappe.db.set_value("Work Order", work_order_id, "status", "Completed")
                    
                    # frappe.db.commit() (Removed for atomicity)
                    print("✅ Moulding Production Entry submission complete - Stock Entry SUBMITTED")
                    
                    return {"status": "success"}
                else:
                    return {"status": "failed", "message": batch__no}
            else:
                return {"status": "failed", "message": f'<b>Batch Details</b> with <b>Compound</b> consumption qty not found..! '}
        else:
            return {"status": "failed", "message": batch__no}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(message=frappe.get_traceback(),
                         title="Moulding SE Error")
        return {"status": "failed", "message": "Stock Entry Creation Failed"}




def submit_inspection_stock_entries_from_moulding(self, moulding_stock_entry):
    """
    Submit Line & Patrol inspection stock entries immediately after Moulding Production
    """
    try:
        print(f"\n🛡️ Fallback: Submitting Line & Patrol inspection stock entries")
        print(f"   Lot: {self.scan_lot_number}")
        
        target_batch = None
        for item in moulding_stock_entry.items:
            if item.t_warehouse and item.is_finished_item:
                target_batch = item.batch_no
                break
        
        if not target_batch:
            print(f"   ⚠️ No batch found in Moulding Stock Entry")
            return
        
        print(f"   📦 Target Batch: {target_batch}")
        
        exe_insp = frappe.db.sql(
            f"""SELECT name, stock_entry_reference, inspection_type 
            FROM `tabInspection Entry` 
            WHERE (inspection_type = 'Line Inspection' 
                   OR inspection_type = 'Patrol Inspection') 
            AND docstatus = 1 
            AND lot_no = '{self.scan_lot_number}'""",
            as_dict=1
        )
        
        if not exe_insp:
            print(f"   ℹ️ No Line/Patrol inspections found yet")
            return
        
        print(f"\n   📋 Found {len(exe_insp)} inspection entries:")
        for ins in exe_insp:
            print(f"      - {ins.inspection_type}: {ins.name} (Stock Entry: {ins.stock_entry_reference or 'None'})")
        
        submitted_count = 0
        for ins in exe_insp:
            if ins.stock_entry_reference:
                print(f"\n   🔄 Processing {ins.inspection_type} - {ins.name}")
                
                ins_stock_entry = frappe.get_doc("Stock Entry", ins.stock_entry_reference)
                
                frappe.db.sql(f"""
                    UPDATE `tabStock Entry Detail` 
                    SET batch_no = '{target_batch}' 
                    WHERE source_ref_document = 'Inspection Entry' 
                    AND source_ref_id = '{ins.name}'
                """)
                print(f"      ✅ Updated batch in Stock Entry Detail")
                
                frappe.db.sql(f"""
                    UPDATE `tabInspection Entry` 
                    SET batch_no = '{target_batch}', 
                        spp_batch_number = '{self.scan_lot_number}' 
                    WHERE name = '{ins.name}'
                """)
                print(f"      ✅ Updated batch in Inspection Entry")
                
                if ins_stock_entry.docstatus == 0:
                    for item in ins_stock_entry.items:
                        item.use_serial_batch_fields = 1
                        if not item.batch_no:
                            item.batch_no = target_batch
                    
                    ins_stock_entry.docstatus = 1
                    ins_stock_entry.save(ignore_permissions=True)
                    
                    if ins_stock_entry.posting_date:
                        frappe.db.sql(f"""
                            UPDATE `tabStock Entry` 
                            SET posting_date = '{ins_stock_entry.posting_date}' 
                            WHERE name = '{ins_stock_entry.name}'
                        """)
                    
                    submitted_count += 1
                    print(f"      ✅ Stock Entry {ins.stock_entry_reference} SUBMITTED")
                else:
                    print(f"      ℹ️ Stock Entry {ins.stock_entry_reference} already submitted")
            else:
                print(f"\n   ℹ️ {ins.inspection_type} - {ins.name} has no rejections")
                
                frappe.db.sql(f"""
                    UPDATE `tabInspection Entry` 
                    SET batch_no = '{target_batch}', 
                        spp_batch_number = '{self.scan_lot_number}' 
                    WHERE name = '{ins.name}'
                """)
                print(f"      ✅ Updated batch reference")
        
        frappe.db.commit()
        
        print(f"\n   ✅ Fallback Complete: Submitted {submitted_count} Line/Patrol inspection stock entries")
        print(f"   📊 Summary: Line & Patrol stock entries now have batch {target_batch}")
        
    except Exception as e:
        frappe.log_error(
            title=f"submit_inspection_stock_entries_from_moulding - Error - {self.name}",
            message=f"Lot: {self.scan_lot_number}\nError: {str(e)}\n{frappe.get_traceback()}"
        )
        print(f"   ⚠️ Error in fallback mechanism: {str(e)}")

def update_bins(self, resp__s, spp_settings):
    for c__bin in resp__s:
        if c__bin.get('is__consumed') and c__bin.get('is_balance_bin'):
            frappe.db.sql(
                f""" UPDATE `tabBlank Bin Issue Item` set is_completed=1 where name = '{c__bin.get('blank_bin_issue_item_name')}' """)
            frappe.db.sql(""" UPDATE `tabItem Bin Mapping` set qty=(%(qty)s),job_card = %(job_card)s where name=%(name)s """, {
                          "qty": c__bin.get('balance__qty'), 'job_card': c__bin.get('job_card'), "name": c__bin.get('item_bin_mapping_name')})
        elif c__bin.get('is__consumed') and not c__bin.get('is_balance_bin'):
            frappe.db.sql(""" UPDATE `tabItem Bin Mapping` set is_retired=1 , job_card = %(job_card)s where name =%(name)s """, {
                          'job_card': c__bin.get('job_card'), "name": c__bin.get('item_bin_mapping_name')})
            frappe.db.sql(
                f""" UPDATE `tabBlank Bin Issue Item` set is_completed=1 where name = '{c__bin.get('blank_bin_issue_item_name')}' """)
            last_mov = frappe.db.sql(
                f" SELECT AMI.target_location FROM `tabAsset Movement` AM INNER JOIN `tabAsset Movement Item` AMI ON AM.name = AMI.parent WHERE AMI.asset = '{c__bin.get('bin')}' ORDER BY AMI.creation DESC LIMIT 1 ", as_dict=1)
            if last_mov:
                if not last_mov[0].target_location == spp_settings.from_location:
                    make_asset_movement(spp_settings, c__bin)
            else:
                make_asset_movement(spp_settings, c__bin)


def append_source_details(stock_entry, self, work_order):
    import json
    final_batch_details = []
    batch_details = json.loads(self.updated_batch_details)
    for b__ in batch_details:
        if b__.get('is__consumed'):
            match_found = False
            for exe_b in final_batch_details:
                if exe_b.get('batch_no__') == b__.get('batch_no__') and exe_b.get('spp_batch_number') == b__.get('spp_batch_number'):
                    match_found = True
                    exe_b['consumed__qty'] = flt(
                        (exe_b['consumed__qty'] + b__['consumed__qty']), 3)
            if not match_found:
                final_batch_details.append(b__)
    # Calculate total quantity to subtract from normal consumption lines if there's a purge
    total_purge_qty = flt(self.purged_compound) + flt(self.compound_leakage)
    remaining_purge_to_deduct = total_purge_qty

    for f__b in final_batch_details:
        # Calculate how much of this batch item is "normal" consumption vs "purge"
        full_batch_qty = flt(f__b.get('consumed__qty'), 3)
        normal_consumption_qty = full_batch_qty
        
        if remaining_purge_to_deduct > 0:
            if remaining_purge_to_deduct >= full_batch_qty:
                # This entire line's quantity is covered by purge scrap
                normal_consumption_qty = 0
                remaining_purge_to_deduct = flt(remaining_purge_to_deduct - full_batch_qty, 3)
            else:
                # Part of this line is normal, part is purge
                normal_consumption_qty = flt(full_batch_qty - remaining_purge_to_deduct, 3)
                remaining_purge_to_deduct = 0
        
        # Only add a normal consumption line if there's quantity left after purge deduction
        if normal_consumption_qty > 0:
            stock_entry.append("items", {
                "item_code": self.compound,
                "s_warehouse": work_order.source_warehouse,
                "t_warehouse": None,
                "stock_uom": "Kg",
                "uom": "Kg",
                "conversion_factor_uom": 1,
                "is_finished_item": 0,
                "use_serial_batch_fields": 1,
                "transfer_qty": flt(normal_consumption_qty, 3),
                "qty": flt(normal_consumption_qty, 3),
                "spp_batch_number": f__b.get('spp_batch_number'),
                "batch_no": f__b.get('batch_no__'),
            })
    
    # Add purged compound + leakage as scrap transfer (for Injection Moulding)
    total_purge_qty = flt(self.purged_compound) + flt(self.compound_leakage)
    if total_purge_qty > 0:
        spp_settings = frappe.get_single("SPP Settings")
        scrap_warehouse = spp_settings.get("purge_scrap_warehouse")
        
        if not scrap_warehouse:
            frappe.throw("Purge Scrap Warehouse not configured in <b>SPP Settings</b>")
        
        # Validate that we have consumed batches
        if not final_batch_details or len(final_batch_details) == 0:
            frappe.throw("No consumed batch details found for purged compound")
        
        # Use the EXACT same batch as the first consumed compound item
        first_batch_info = final_batch_details[0]
        purge_batch_no = first_batch_info.get('batch_no__')
        purge_spp_batch = first_batch_info.get('spp_batch_number')
        
        # Validate batch number exists
        if not purge_batch_no:
            frappe.throw(f"Batch number not found in consumed batch details for purged compound")
        
        stock_entry.append("items", {
            "item_code": self.compound,  # Same compound item
            "s_warehouse": work_order.source_warehouse,
            # Consumed as scrap (not transferred). NOTE: is_scrap_item must stay 0 —
            # erpnext >= 15.116 (validate_warehouse) treats Manufacture rows with
            # is_scrap_item=1 as OUTPUTS: it blanks s_warehouse and demands a
            # t_warehouse ("Target warehouse is mandatory for row N"), which both
            # fails this insert and would invert the movement (purge arriving in a
            # warehouse instead of leaving the source). Purge IS consumption —
            # keep it a plain consume row (same net stock effect as before).
            "t_warehouse": None,
            "stock_uom": "Kg",
            "uom": "Kg",
            "conversion_factor_uom": 1,
            "is_finished_item": 0,
            "transfer_qty": flt(total_purge_qty, 3),
            "qty": flt(total_purge_qty, 3),
            "use_serial_batch_fields": 1,  # Use batch fields for consumption items
            "batch_no": purge_batch_no,  # EXPLICITLY set to same batch as consumed compound
            "spp_batch_number": purge_spp_batch,
            "docstatus": 0
        })
    
    if self.shell_qty_nos:
        stock_entry.append("items", {
            "item_code": self.shell_item,
            "s_warehouse": self.s_source_warehouse,
            "t_warehouse": None,
            "stock_uom": "Nos",
            "uom": "Nos",
            "conversion_factor_uom": 1,
            "is_finished_item": 0,
            "transfer_qty": self.shell_qty_nos,
            "use_serial_batch_fields": 1,
            "qty": self.shell_qty_nos,
            "batch_no": self.s_batch,
            # For avaoiding the child table only submitted issue which means the parent docstatus = 0 but child docstatus = 1
            "docstatus": 0
        })
    return batch_details


def make_asset_movement(spp_settings, x):
    asset__mov = frappe.new_doc("Asset Movement")
    asset__mov.company = "SPP"
    asset__mov.transaction_date = now()
    asset__mov.purpose = "Transfer"
    asset__mov.append("assets", {
        "asset": x.get('bin'),
        "source_location": spp_settings.to_location,
        "target_location": spp_settings.from_location,
    })
    asset__mov.insert(ignore_permissions=True)
    ass__doc = frappe.get_doc("Asset Movement", asset__mov.name)
    ass__doc.docstatus = 1
    ass__doc.save(ignore_permissions=True)


def get_spp_batch_date(compound):
    serial_no = 1
    serial_nos = frappe.db.get_all("SPP Batch Serial", filters={
                                   "posted_date": getdate()}, fields=['serial_no'], order_by="serial_no DESC")
    if serial_nos:
        serial_no = serial_nos[0].serial_no+1
    month_key = getmonth(str(str(getdate()).split('-')[1]))
    l = len(str(getdate()).split('-')[0])
    compound_key = (str(getdate()).split(
        '-')[0])[l - 2:]+month_key+str(str(getdate()).split('-')[2])+"X"+str(serial_no)
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
    new_h = h + (2*margin)
    new_image = Image.new('RGB', (w, new_h), (255, 255, 255))
    # put barcode on new image
    new_image.paste(barcode_image, (0, margin))
    # object to draw text
    draw = ImageDraw.Draw(new_image)
    new_image.save(str(frappe.local.site) +
                   '/public/files/{filename}.png'.format(filename=barcode_text), 'PNG')
    barcode = "/files/" + barcode_text + ".png"
    return {"barcode": barcode, "barcode_text": barcode_text}


@frappe.whitelist()
def validate_operator(operator, supervisor=None):
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
            check_emp = frappe.db.sql(f"""SELECT name,employee_name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s AND designation IN ({designation}) """, {
                                      "barcode": operator}, as_dict=1)
            if check_emp:
                return {"status": "Success", "message": check_emp[0]}
            else:
                return {"status": "Failed", "message": "Employee not found."}
        else:
            return {"status": "Failed", "message": "Designation not mapped in SPP Settings."}
    else:
        check_emp = frappe.db.sql("""SELECT employee_name,name FROM `tabEmployee` WHERE status='Active' AND barcode_text=%(barcode)s""", {
                                  "barcode": operator}, as_dict=1)
        if check_emp:
            return {"status": "Success", "message": check_emp[0]}
    return {"status": "Failed", "message": "Employee not found."}


@frappe.whitelist()
def validate_lot_number(batch_no):
	try:
		job_card = frappe.db.get_value(
			"Job Card", {"batch_code": batch_no, "operation": "Moulding"}, 'status')
		if not job_card:
			return {"status": "Failed", "message": "The scanned lot barcode is <b>invalid</b>..!."}
		if job_card == "Completed":
			return {"status": "Failed", "message": "The <b>Moulding Operation</b> for the scanned lot was completed..!"}

		check_line_inspe_entry = frappe.db.get_value("Inspection Entry", {
													 "lot_no": batch_no, "docstatus": 1, "inspection_type": "Line Inspection"})
		check_patrol_inspe_entry = frappe.db.get_value("Inspection Entry", {
													   "lot_no": batch_no, "docstatus": 1, "inspection_type": "Patrol Inspection"})

		missing_inspections = []
		if not check_line_inspe_entry:
			missing_inspections.append("Line Inspection")
		if not check_patrol_inspe_entry:
			missing_inspections.append("Patrol Inspection")

		if missing_inspections:
			return {"status": "Failed", "message": f"The following inspections are missing: {', '.join(missing_inspections)}"}

		check_lot_issue = frappe.db.sql(""" SELECT BI.bin,BI.name as blank_bin_issue_item_name,B.name as blanking_bin_issue_name,
							B.job_card,JB.name as job_card,B.scan_bin,JB.mould_reference,JB.no_of_running_cavities
							FROM `tabBlank Bin Issue Item` BI 
							INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
							INNER JOIN `tabBlank Bin Issue` B ON B.name = BI.parent
							WHERE BI.is_completed = 0 AND JB.batch_code=%(lot_no)s 
							AND B.docstatus = 1 ORDER BY B.creation ASC """, {"lot_no": batch_no}, as_dict=1)
		if not check_lot_issue:
			return {"status": "Failed", "message": "There is no entry for Blank Bin Issue for the scanned lot number."}
		else:
			if not check_lot_issue[0].mould_reference:
				return {"status": "Failed", "message": f"The <b>Mould Referenece</b> not found in <b>Job Card - {check_lot_issue[0].job_card}</b>"}
			else:
				mould_ref = frappe.db.get_value(
					"Asset", check_lot_issue[0].mould_reference, "item_code")
				if mould_ref:
					if check_lot_issue[0].no_of_running_cavities:
						check_lot_issue[0].mould_reference = mould_ref
					else:
						return {"status": "Failed", "message": f"The <b>No.Of.Cavity</b> not found in the <b>Job Card - {check_lot_issue[0].job_card}</b>"}
				else:
					return {"status": "Failed", "message": f"The <b>Mould Referenece</b> not found in <b>Asset - {check_lot_issue[0].mould_reference}</b>"}
			all_blank__bins = []
			for bin__ in check_lot_issue:
				check_bin_release = frappe.db.sql(
					f" SELECT name item_bin_mapping_name,compound,spp_batch_number,qty FROM `tabItem Bin Mapping` WHERE blanking__bin = '{bin__.bin}' AND is_retired = 0 ", as_dict=1)
				if not check_bin_release:
					return {"status": "Failed", "message": f"The bin <b>{bin__.bin}</b> is already released manually, Please check <b>Item Bin Mapping</b>..!"}
				else:
					bin__.update(check_bin_release[0])
					if not bin__.compound:
						return {"status": "Failed", "message": f"There is no <b>Compound</b> found in bin <b>{bin__.bin}</b>."}
				batch_no = frappe.db.sql(
					f""" SELECT batch_no,docstatus,parenttype FROM `tabDelivery Note Item` WHERE spp_batch_no = '{bin__.spp_batch_number}'  """, as_dict=1)
				if not batch_no:
					spp_settings = frappe.get_single("SPP Settings")
					if not spp_settings.unit_2_warehouse:
						return {"status": "Failed", "message": f"The default <b>Unit - 1 Warehouse</b> not found in <b>SPP Settings</b>..!"}
					if not spp_settings.default_sheeting_warehouse:
						return {"status": "Failed", "message": f"The default <b>Sheeting Warehouse</b> not found in <b>SPP Settings</b>..!"}
					batch_no = frappe.db.sql(f""" SELECT SED.batch_no,SED.parenttype,SED.docstatus FROM `tabStock Entry` SE 
													INNER JOIN `tabStock Entry Detail` SED ON SED.parent=SE.name WHERE SE.stock_entry_type="Material Transfer" 
													AND SED.spp_batch_number = '{bin__.spp_batch_number}' AND SED.s_warehouse = '{spp_settings.default_sheeting_warehouse}' AND SED.t_warehouse = '{spp_settings.unit_2_warehouse}'  """, as_dict=1)
					if not batch_no:
						batch_no = frappe.db.sql(f""" SELECT SED.batch_no,SED.parenttype,SED.docstatus FROM `tabStock Entry` SE 
													INNER JOIN `tabStock Entry Detail` SED ON SED.parent=SE.name WHERE SE.stock_entry_type="Repack" 
													AND SED.spp_batch_number = '{bin__.spp_batch_number}' AND SED.t_warehouse = '{spp_settings.default_sheeting_warehouse}'  """, as_dict=1)
				if batch_no:
					if batch_no[0].docstatus == 1:
						bin__.batch_no__ = batch_no[0].batch_no
					else:
						return {"status": "Failed", "message": f"The <b>{batch_no[0].parenttype}</b> is not <b>submitted or cancelled</b>..!"}
				else:
					""" For get f name from bom """
					f__name = frappe.db.sql(""" SELECT BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabJob Card` J ON J.bom_no = B.name WHERE J.name=%(name)s AND B.is_active=1""", {
											"name": bin__.job_card}, as_dict=1)
					if f__name:
						return {"status": "Failed", "message": f"The Batch No. not found for the item - <b>{f__name[0].item_code}</b>..!"}
					else:
						return {"status": "Failed", "message": f"The Batch No. not found for the source item..!"}
				all_blank__bins.append(bin__)
				""" End """
			f__name = frappe.db.sql(""" SELECT B.item FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name INNER JOIN `tabJob Card` J ON J.bom_no = B.name WHERE J.name=%(name)s AND B.is_active=1""", {
									"name": bin__.job_card}, as_dict=1)
			if f__name:
				bom__ = frappe.db.sql(""" SELECT B.name,BI.item_code FROM `tabBOM Item` BI INNER JOIN `tabBOM` B ON BI.parent = B.name WHERE B.item=%(bom_item)s AND B.is_Active=1 """, {
									  "bom_item": f__name[0].item}, as_dict=1)
				boms__item = []
				for bm in bom__:
					boms__item.append(bm.item_code)
				for c__bin in all_blank__bins:
					c__bin.item_to_produce = f__name[0].item
					if not c__bin.compound in boms__item:
						return {"status": "Failed", "message": f"There is no active BOM found for the bin <b>Compound - {check_lot_issue[0].compound}</b>"}
			else:
				return {"status": "Failed", "message": f"BOM is not found for <b>Item to Produce</b>"}
			return {"status": "Success", "message": all_blank__bins}
	except Exception:
		frappe.log_error(
			title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.moulding_production_entry.validate_lot_number", message=frappe.get_traceback())


@frappe.whitelist()
def validate_bin(batch_no, job_card):
    # check_retired = frappe.db.sql(""" SELECT IB.name FROM `tabItem Bin Mapping` IB
    # 							  INNER JOIN `tabBlanking Bin` BB ON IB.blanking_bin=BB.name
    # 							  WHERE BB.barcode_text=%(barcode)s AND IB.is_retired=0""",{"barcode":batch_no},as_dict=1)
    check_retired = frappe.db.sql(""" SELECT IB.name FROM `tabItem Bin Mapping` IB
								  INNER JOIN `tabAsset` A ON IB.blanking__bin=A.name
								  WHERE A.barcode_text=%(barcode)s AND IB.is_retired=0""", {"barcode": batch_no}, as_dict=1)
    if not check_retired:
        return {"status": "Failed", "message": "The Scanned bin already released."}

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
					 """, {"barcode": batch_no}, as_dict=1)
    if not check_lot_issue:
        return {"status": "Failed", "message": "The Scanned bin not issued for the Job Card "+job_card+"."}
    else:
        return {"status": "Success", "bin_weight": check_lot_issue[0].bin_weight, "blanking_bin": check_lot_issue[0].blanking_bin, "asset_name": check_lot_issue[0].asset_name}


@frappe.whitelist()
def validate_bin_weight(weight, bin, bin_Weight, prod_weight):
    item_bin = frappe.db.get_all("Item Bin Mapping", filters={
                                 "blanking__bin": bin, "is_retired": 0}, fields=['qty'])
    if item_bin:
        if flt(weight) <= flt(bin_Weight):
            return {"status": "Failed", "message": f"The <b>Gross Weight</b> of balance bin  can't be less than the <b>Bin Weight - {bin_Weight}</b>..!"}
        if (flt(weight) - flt(bin_Weight)) > (flt(item_bin[0].qty) - flt(prod_weight)):
            return {"status": "Failed", "message": "The quantity in the bin <b>"+bin+"</b> is <b>"+str('%.3f' % (flt(item_bin[0].qty) - flt(prod_weight)))+"</b>"}
    else:
        return {"status": "Failed", "message": f"The bin is already <b>Released</b>..!"}
    return {"status": "Success"}


@frappe.whitelist()
def validate_tolerance(self):
    spp_settings = frappe.get_single("SPP Settings")
    total_bins_weight = frappe.db.sql(""" SELECT sum(IB.qty) as total_qty FROM `tabItem Bin Mapping` IB
						INNER JOIN `tabBlank Bin Issue Item` BI ON IB.blanking__bin = BI.bin
						INNER JOIN `tabJob Card` JB ON JB.name= BI.job_card
						WHERE IB.is_retired = 0 AND BI.is_completed=0 AND BI.docstatus = 1 AND JB.name=%(job_card)s""", {"job_card": self.job_card}, as_dict=1)
    if spp_settings.production_tolerance != 0 and total_bins_weight and total_bins_weight[0].total_qty:
        from_wt = total_bins_weight[0].total_qty-(
            (total_bins_weight[0].total_qty * spp_settings.production_tolerance)/100)
        to_wt = total_bins_weight[0].total_qty + (
            (total_bins_weight[0].total_qty * spp_settings.production_tolerance)/100)
        if not self.weight >= from_wt and self.weight < to_wt:
            return {"status": True, "message": "Mat bin weight should be between <b>"+str('%.3f' % (from_wt))+"</b> to <b>"+'%.3f' % (to_wt)+"</b>"}
    return {"status": True}