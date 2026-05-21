import frappe
import json

def get_se_examples():
    doctypes = [
        "Material Transfer",
        "Cut Bit Transfer",
        "Blank Bin Inward Entry",
        "Deflashing Despatch Entry",
        "Despatched Material Return Entry",
        "Despatch To U1 Entry",
        "Receive Deflashing Entry",
        "Sub Lot Creation",
        "Weight Mismatch Tracker"
    ]
    
    results = {}
    
    # 1. Inspection Entries
    for insp_type in ["Line Inspection", "Patrol Inspection", "Lot Inspection", "Incoming Inspection"]:
        try:
            docs = frappe.get_all("Inspection Entry", filters={"docstatus": 1, "inspection_type": insp_type}, fields=["name"], limit=20, order_by="creation desc")
            found = False
            for d in docs:
                d_name = d.name if hasattr(d, 'name') else d.get('name')
                se = None
                try:
                    doc = frappe.get_doc("Inspection Entry", d_name)
                    if getattr(doc, "stock_entry_reference", None):
                        se = [{"name": doc.stock_entry_reference}]
                except:
                    pass
                if se:
                    se_name = se[0].name if hasattr(se[0], 'name') else se[0].get('name')
                    se_doc = frappe.get_doc("Stock Entry", se_name)
                    item = se_doc.items[0] if se_doc.items else None
                    results[f"Inspection - {insp_type}"] = {
                        "docname": d_name,
                        "stock_entry": se_doc.name,
                        "type": se_doc.stock_entry_type,
                        "item": item.item_code if item else None,
                        "qty": item.qty if item else None,
                        "uom": item.uom if item else None,
                        "s_warehouse": item.s_warehouse if item else None,
                        "t_warehouse": item.t_warehouse if item else None,
                    }
                    found = True
                    break
            if not found:
                results[f"Inspection - {insp_type}"] = "Not found"
        except Exception as e:
            results[f"Inspection - {insp_type}"] = str(e)

    # 2. Other Doctypes
    for dt in doctypes:
        try:
            se = None
            docs = frappe.get_all(dt, filters={"docstatus": 1}, fields=["name"], limit=20, order_by="creation desc")
            for d in docs:
                d_name = d.name if hasattr(d, 'name') else d.get('name')
                doc = frappe.get_doc(dt, d_name)
                ref = getattr(doc, "stock_entry_reference", None) or getattr(doc, "stock_entry_ref", None) or getattr(doc, "stock_reconciliation_ref", None)
                if ref and (ref.startswith("STE") or ref.startswith("MAT")):
                    se = [{"name": ref}]
                    break
                
                if dt == "Receive Deflashing Entry" and getattr(doc, "received_stock_entry_ref", None):
                    for item in doc.received_stock_entry_ref:
                        if getattr(item, "stock_entry", None):
                            se = [{"name": item.stock_entry}]
                            break
                    if se:
                        break
                        
            if se:
                se_name = se[0].name if hasattr(se[0], 'name') else se[0].get('name')
                se_doc = frappe.get_doc("Stock Entry", se_name)
                item = se_doc.items[0] if se_doc.items else None
                results[dt] = {
                    "docname": getattr(se_doc, "custom_reference_docname", None) or getattr(se_doc, "reference_docname", None) or d_name,
                    "stock_entry": se_doc.name,
                    "type": se_doc.stock_entry_type,
                    "item": item.item_code if item else None,
                    "qty": item.qty if item else None,
                    "uom": item.uom if item else None,
                    "s_warehouse": item.s_warehouse if item else None,
                    "t_warehouse": item.t_warehouse if item else None,
                }
            else:
                results[dt] = "No stock entry found"
        except Exception as e:
            results[dt] = str(e)
            
    if results.get("Weight Mismatch Tracker") == "No stock entry found":
        try:
            docs = frappe.get_all("Weight Mismatch Tracker", filters={"docstatus": 1}, fields=["name"], limit=20, order_by="creation desc")
            for d in docs:
                d_name = d.name if hasattr(d, 'name') else d.get('name')
                wmt = frappe.get_doc("Weight Mismatch Tracker", d_name)
                if wmt.stock_reconciliation_ref:
                    results["Weight Mismatch Tracker"] = {
                        "docname": d_name,
                        "stock_reconciliation": wmt.stock_reconciliation_ref
                    }
                    break
        except:
            pass
            
    with open('/tmp/se_examples.json', 'w') as f:
        f.write(json.dumps(results, indent=2))
    
    print("Done")
