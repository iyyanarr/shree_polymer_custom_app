# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from shree_polymer_custom_app.shree_polymer_custom_app.api import get_stock_entry_naming_series

class CutBitTransfer(Document):

    def on_submit(self):
        create_stock_entry(self)
        self.reload()

@frappe.whitelist()
def validate_clip_barcode(batch_no, t_type, warehouse):
    frappe.log_error(message=f"START: validate_clip_barcode called with batch_no={batch_no}, t_type={t_type}, warehouse={warehouse}", 
                   title="CutBit Debug: Function Start")
    
    spp_settings = frappe.get_single("SPP Settings")
    frappe.log_error(message=f"Retrieved SPP settings", title="CutBit Debug: Settings")
    
    # Default values
    ct_type = "Clip"
    s_warehouse = spp_settings.default_sheeting_warehouse
    frappe.log_error(message=f"Initial warehouse set to {s_warehouse}", title="CutBit Debug: Warehouse")
    
    # Step 1: Check clip mapping
    frappe.log_error(message=f"Checking clip mapping for barcode {batch_no}", title="CutBit Debug: Clip Check")
    clip_mapping = frappe.db.sql(""" SELECT compound, spp_batch_number, qty FROM `tabItem Clip Mapping` CM 
                                 INNER JOIN `tabSheeting Clip` SC ON SC.name = CM.sheeting_clip 
                                 WHERE SC.barcode_text = %(mix_barcode)s AND CM.is_retired=0""", 
                                {"mix_barcode": batch_no}, as_dict=1)
    frappe.log_error(message=f"Clip mapping query result: {clip_mapping}", title="CutBit Debug: Clip Result")
    
    if clip_mapping:
        old_batch_no = batch_no
        batch_no = clip_mapping[0].compound + "_" + clip_mapping[0].spp_batch_number.split('-')[0]
        frappe.log_error(message=f"Clip found - reformatted batch_no from {old_batch_no} to {batch_no}", 
                       title="CutBit Debug: Clip Found")
    
    # Step 2: Check bin mapping if no clip found
    if not clip_mapping:
        frappe.log_error(message=f"No clip mapping found, checking bin mapping", title="CutBit Debug: Bin Check")
        clip_mapping = frappe.db.sql(""" SELECT compound, spp_batch_number, qty FROM `tabItem Bin Mapping` IBM 
                                     INNER JOIN `tabAsset` A ON A.name = IBM.blanking__bin 
                                     WHERE A.barcode_text = %(mix_barcode)s AND IBM.is_retired=0 """, 
                                    {"mix_barcode": batch_no}, as_dict=1)
        frappe.log_error(message=f"Bin mapping query result: {clip_mapping}", title="CutBit Debug: Bin Result")
        
        if clip_mapping:
            old_batch_no = batch_no
            batch_no = clip_mapping[0].compound + "_" + clip_mapping[0].spp_batch_number.split('-')[0]
            ct_type = "Bin"
            old_warehouse = s_warehouse
            s_warehouse = spp_settings.unit_2_warehouse
            frappe.log_error(message=f"Bin found - reformatted batch_no from {old_batch_no} to {batch_no}", 
                           title="CutBit Debug: Bin Found")
            frappe.log_error(message=f"Changed type to {ct_type} and warehouse from {old_warehouse} to {s_warehouse}", 
                           title="CutBit Debug: Warehouse Change")
    
    # Step 3: Check stock details
    frappe.log_error(message=f"Checking stock details with batch_no={batch_no}, warehouse={s_warehouse}", 
                   title="CutBit Debug: Stock Check")
    stock_details = frappe.db.sql(""" SELECT S.name, SD.item_code, SD.item_name, SD.transfer_qty, SD.spp_batch_number, 
                      SD.batch_no, SD.stock_uom 
                      FROM `tabStock Entry Detail` SD
                      INNER JOIN `tabStock Entry` S ON SD.parent = S.name
                      WHERE (SD.mix_barcode = %(mix_barcode)s OR SD.barcode_text = %(mix_barcode)s) 
                      AND SD.t_warehouse = %(t_warehouse)s 
                      AND S.docstatus = 1  
                      ORDER BY S.creation DESC limit 1 """,
                     {'mix_barcode': batch_no, 't_warehouse': s_warehouse}, as_dict=1)
    frappe.log_error(message=f"Stock details query result: {stock_details}", title="CutBit Debug: Stock Result")
    
    # Step 4: Process stock details if found
    if stock_details:
        items = stock_details[0].item_code
        frappe.log_error(message=f"Stock details found for item_code={items}", title="CutBit Debug: Item Found")
        
        # First stock balance query
        frappe.log_error(message=f"Running first stock balance query for warehouse {s_warehouse}", 
                       title="CutBit Debug: Balance Query 1")
        s_query = f"SELECT I.item_code, I.item_name, I.description, I.batch_no, SD.spp_batch_number, SD.mix_barcode, \
                    I.stock_uom as uom, I.qty FROM `tabItem Batch Stock Balance` I \
                    INNER JOIN `tabBatch` B ON I.batch_no = B.name \
                    INNER JOIN `tabStock Entry Detail` SD ON SD.batch_no = B.name \
                    WHERE I.item_code ='{items}' AND (SD.mix_barcode = '{batch_no}' OR SD.barcode_text = '{batch_no}') \
                    AND I.qty > 0 AND I.warehouse ='{s_warehouse}' AND B.expiry_date >= curdate()"
        
        frappe.log_error(message=f"First query: {s_query}", title="CutBit Debug: Query Text 1")
        st_details = frappe.db.sql(s_query, as_dict=1)
        frappe.log_error(message=f"First stock balance query result: {st_details}", 
                       title="CutBit Debug: Balance Result 1")
        
        # Second stock balance query if first returns no results
        if not st_details:
            frappe.log_error(message=f"No stock found in first query, trying with unit_2_warehouse", 
                           title="CutBit Debug: Balance Query 2")
            s_query = f"SELECT I.item_code, I.item_name, I.description, I.batch_no, SD.spp_batch_number, SD.mix_barcode, \
                        I.stock_uom as uom, I.qty FROM `tabItem Batch Stock Balance` I \
                        INNER JOIN `tabBatch` B ON I.batch_no = B.name \
                        INNER JOIN `tabStock Entry Detail` SD ON SD.batch_no = B.name \
                        WHERE I.item_code ='{items}' AND (SD.mix_barcode = '{batch_no}' OR SD.barcode_text = '{batch_no}') \
                        AND I.qty > 0 AND I.warehouse ='{spp_settings.unit_2_warehouse}' AND B.expiry_date >= curdate()"
            
            frappe.log_error(message=f"Second query: {s_query}", title="CutBit Debug: Query Text 2")
            st_details = frappe.db.sql(s_query, as_dict=1)
            frappe.log_error(message=f"Second stock balance query result: {st_details}", 
                           title="CutBit Debug: Balance Result 2")
        
        # Override quantity if we have clip mapping
        if st_details and clip_mapping:
            old_qty = st_details[0].qty
            st_details[0].qty = clip_mapping[0].qty
            frappe.log_error(message=f"Overriding qty from {old_qty} to {clip_mapping[0].qty}", 
                           title="CutBit Debug: Qty Override")
        
        frappe.log_error(message=f"Returning success with stock={st_details} and source_warehouse={s_warehouse}", 
                       title="CutBit Debug: Success Return")
        return {"status": "Success", "stock": st_details, "source_warehouse": s_warehouse}
    
    # Step 5: Return failure if no stock found
    frappe.log_error(message=f"No stock found, returning failure message for {ct_type} {batch_no} in {s_warehouse}", 
                   title="CutBit Debug: Failed Return")
    return {"status": "Failed", "message": "Scanned " + ct_type + " <b>" + batch_no + "</b> not exist in the <b>" + s_warehouse + "</b>"}


def create_stock_entry(mt_doc):
    try:
        frappe.log_error(message=f"Starting create_stock_entry for {mt_doc.name}", title="CutBit Debug: Create Entry Start")
        spp_settings = frappe.get_single("SPP Settings")
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.purpose = "Repack"
        stock_entry.company = "SPP"
        stock_entry.naming_series = "MAT-STE-.YYYY.-"
        """ For identifying procees name to change the naming series the field is used """
        naming_status, naming_series = get_stock_entry_naming_series(spp_settings, "Cut Bit Entry")
        if naming_status:
            stock_entry.naming_series = naming_series
            frappe.log_error(message=f"Using custom naming series: {naming_series}", title="CutBit Debug: Naming Series")
        """ End """
        stock_entry.stock_entry_type = "Repack"
        # accept 0 qty as well
        is_allowed = 0
        # stock_entry.from_warehouse = mt_doc.source_warehouse
        stock_entry.to_warehouse = spp_settings.default_cut_bit_warehouse
        frappe.log_error(message=f"Processing items for stock entry", title="CutBit Debug: Process Items")
        
        for x in mt_doc.items:
            r_batchno = x.batch_no
            ct_batch = "Cutbit_" + x.item_code
            cb_batch = frappe.db.get_all("Batch", filters={"batch_id": ct_batch})
            if cb_batch:
                r_batchno = "Cutbit_" + x.item_code
                is_allowed = 1
                frappe.log_error(message=f"Found cutbit batch for {x.item_code}", title="CutBit Debug: Batch Found")
            
            ct_source_warehouse = spp_settings.default_blanking_warehouse
            if frappe.db.get_value("Item", x.item_code, "item_group") == "Compound":
                ct_source_warehouse = spp_settings.default_sheeting_warehouse
            if frappe.db.get_value("Item", x.item_code, "item_group") == spp_settings.blanking_item_group:
                ct_source_warehouse = spp_settings.unit_2_warehouse
            
            frappe.log_error(message=f"Adding source item {x.item_code} from {ct_source_warehouse}", 
                           title="CutBit Debug: Add Source Item")
            stock_entry.append("items", {
                "item_code": x.item_code,
                "s_warehouse": ct_source_warehouse,
                "stock_uom": "Kg",
                "to_uom": "Kg",
                "uom": "Kg",
                "is_finished_item": 0,
                "transfer_qty": x.qty,
                "qty": x.qty,
                "spp_batch_number": x.spp_batch_no,
                "use_serial_batch_fields": 1,
                "batch_no": x.batch_no,
            })
        
        frappe.log_error(message=f"Adding target items", title="CutBit Debug: Add Target Items")
        for x in mt_doc.items:
            r_batchno = x.batch_no
            ct_batch = "Cutbit_" + x.item_code
            cb_batch = frappe.db.get_all("Batch", filters={"batch_id": ct_batch})
            if cb_batch:
                r_batchno = "Cutbit_" + x.item_code
                is_allowed = 1
            
            ct_source_warehouse = spp_settings.default_blanking_warehouse
            if frappe.db.get_value("Item", x.item_code, "item_group") == "Compound":
                ct_source_warehouse = spp_settings.default_sheeting_warehouse
            if frappe.db.get_value("Item", x.item_code, "item_group") == spp_settings.blanking_item_group:
                ct_source_warehouse = spp_settings.unit_2_warehouse
            
            frappe.log_error(message=f"Adding target item {x.item_code} with batch {r_batchno}", 
                           title="CutBit Debug: Add Target Item")
            stock_entry.append("items", {
                "item_code": x.item_code,
                "t_warehouse": spp_settings.default_cut_bit_warehouse,
                "stock_uom": "Kg",
                "to_uom": "Kg",
                "uom": "Kg",
                "is_finished_item": 0,
                "transfer_qty": x.qty,
                "qty": x.qty,
                "use_serial_batch_fields": 1,
                "batch_no": r_batchno,
                "source_ref_document": mt_doc.doctype,
                "source_ref_id": mt_doc.name,
                "mix_barcode": "CB_" + x.item_code
            })
            
        frappe.log_error(message="Saving stock entry", title="CutBit Debug: Save Entry")
        stock_entry.docstatus = 1
        stock_entry.save(ignore_permissions=True)
        frappe.log_error(message=f"Stock entry created: {stock_entry.name}", title="CutBit Debug: Entry Created")
        
        frappe.db.set_value(mt_doc.doctype, mt_doc.name, "stock_entry_reference", stock_entry.name)
        frappe.db.commit()
        
        frappe.log_error(message="Processing bin mappings", title="CutBit Debug: Bin Mappings")
        for x in mt_doc.items:
            if frappe.db.get_value("Item", x.item_code, "item_group") == spp_settings.blanking_item_group:
                check_item_bin = frappe.db.get_all("Item Bin Mapping", 
                                                filters={"compound": x.item_code, "is_retired": 0}, 
                                                fields=['name', 'qty'])
                if check_item_bin:
                    if check_item_bin[0].qty == x.qty:
                        frappe.db.set_value("Item Bin Mapping", check_item_bin[0].name, "is_retired", 1)
                        frappe.log_error(message=f"Retired bin mapping: {check_item_bin[0].name}", 
                                       title="CutBit Debug: Bin Retired")
                    else:
                        if check_item_bin[0].qty > x.qty:
                            new_qty = check_item_bin[0].qty - x.qty
                            frappe.db.set_value("Item Bin Mapping", check_item_bin[0].name, "qty", new_qty)
                            frappe.log_error(message=f"Updated bin mapping qty from {check_item_bin[0].qty} to {new_qty}", 
                                           title="CutBit Debug: Bin Updated")
                    frappe.db.commit()
        
        frappe.log_error(message=f"Completed create_stock_entry successfully", title="CutBit Debug: Complete Success")
        return stock_entry.name
    except Exception as e:
        frappe.log_error(message=f"Error in create_stock_entry: {str(e)}\n{frappe.get_traceback()}", 
                       title="CutBit Error: Stock Entry Failed")
        frappe.db.rollback()
        raise e

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