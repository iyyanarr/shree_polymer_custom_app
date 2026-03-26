import frappe

@frappe.whitelist()
def should_sync_work_order(doc, consumer, update_log=None):
    """
    Sync criteria for {2526spp -> Master}: 
    Item Group == 'Batch' AND Item Code starts with B_ or FB_
    """
    # Cast to doc if it's a dict
    if isinstance(doc, dict):
        doc = frappe._dict(doc)
        
    # Check Item Group
    if doc.item_group != "Batch":
        return False
        
    # Check Item Code pattern
    item_code = doc.production_item or doc.item_code
    if item_code and (item_code.startswith("B_") or item_code.startswith("FB_")):
        return True
        
    return False

@frappe.whitelist()
def should_sync_stock_entry_2526(doc, consumer, update_log=None):
    """
    Sync criteria for {2526spp -> Master}: 
    Purpose in [Material Transfer, Material Transfer for Manufacturing, Manufacturing]
    """
    if isinstance(doc, dict):
        doc = frappe._dict(doc)
        
    allowed_purposes = [
        "Material Transfer", 
        "Material Transfer for Manufacturing", 
        "Manufacturing"
    ]
    return doc.purpose in allowed_purposes

@frappe.whitelist()
def should_sync_stock_entry_master(doc, consumer, update_log=None):
    """
    Sync criteria for {Master -> 2526spp}: 
    Purpose == 'Repack Entry' AND (Item Group == 'Batch' AND Item Code starts with B_ or FB_)
    """
    if isinstance(doc, dict):
        doc = frappe._dict(doc)
        
    if doc.purpose != "Repack Entry":
        return False
        
    # Check if any item in the Stock Entry matches the Batch/B_/FB_ criteria
    for item in doc.items:
        # Fetch Item Group from Item master
        item_group = frappe.db.get_value("Item", item.item_code, "item_group")
        if item_group == "Batch" and (item.item_code.startswith("B_") or item.item_code.startswith("FB_")):
            return True
            
    return False
