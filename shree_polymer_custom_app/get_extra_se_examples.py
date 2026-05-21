import frappe
import json

def get_examples():
    examples = {}

    # 1. Packing
    packing_se = frappe.db.get_all("Stock Entry Detail", 
                                   filters={"source_ref_document": "Packing", "docstatus": 1}, 
                                   fields=["parent as stock_entry"], limit=1)
    if packing_se:
        se_doc = frappe.get_doc("Stock Entry", packing_se[0].stock_entry)
        examples["Packing"] = {"stock_entry": se_doc.name, "purpose": se_doc.purpose, "stock_entry_type": se_doc.stock_entry_type, "items": [{"item_code": item.item_code, "qty": item.qty, "uom": item.uom, "s_warehouse": item.s_warehouse, "t_warehouse": item.t_warehouse} for item in se_doc.items]}

    # 2. Lot Resource Tagging
    lrt_se = frappe.db.get_all("Stock Entry Detail", 
                               filters={"source_ref_document": "Lot Resource Tagging", "docstatus": 1}, 
                               fields=["parent as stock_entry"], limit=1)
    if lrt_se:
        se_doc = frappe.get_doc("Stock Entry", lrt_se[0].stock_entry)
        examples["Lot Resource Tagging"] = {"stock_entry": se_doc.name, "purpose": se_doc.purpose, "stock_entry_type": se_doc.stock_entry_type, "items": [{"item_code": item.item_code, "qty": item.qty, "uom": item.uom, "s_warehouse": item.s_warehouse, "t_warehouse": item.t_warehouse} for item in se_doc.items]}

    # 3. SPP Final Visual Inspection Entry
    fvi_mt_se_name = frappe.db.get_value("Inspection Entry", {"inspection_type": "Final Visual Inspection", "docstatus": 1, "stock_entry_reference": ("!=", "")}, "stock_entry_reference")
    if fvi_mt_se_name:
        se_doc = frappe.get_doc("Stock Entry", fvi_mt_se_name)
        examples["SPP Final Visual Inspection Entry (Rejection)"] = {"stock_entry": se_doc.name, "purpose": se_doc.purpose, "stock_entry_type": se_doc.stock_entry_type, "items": [{"item_code": item.item_code, "qty": item.qty, "uom": item.uom, "s_warehouse": item.s_warehouse, "t_warehouse": item.t_warehouse} for item in se_doc.items]}
    
    fvi_mfg_se_name = frappe.db.get_value("Inspection Entry", {"inspection_type": "Final Visual Inspection", "docstatus": 1, "vs_pdir_stock_entry_ref": ("!=", "")}, "vs_pdir_stock_entry_ref")
    if fvi_mfg_se_name:
        se_doc = frappe.get_doc("Stock Entry", fvi_mfg_se_name)
        examples["SPP Final Visual Inspection Entry (FG)"] = {"stock_entry": se_doc.name, "purpose": se_doc.purpose, "stock_entry_type": se_doc.stock_entry_type, "items": [{"item_code": item.item_code, "qty": item.qty, "uom": item.uom, "s_warehouse": item.s_warehouse, "t_warehouse": item.t_warehouse} for item in se_doc.items]}

    print(json.dumps(examples, indent=2))

get_examples()
