import json
import frappe
from frappe import _


@frappe.whitelist()
def get_bom_details(item_code, bom_no=None):
    """Get BOM details for an item code with optional nested BOMs"""
    if not item_code:
        frappe.throw(_("Item Code is required"))
    
    # If BOM number is provided, use it directly
    if bom_no:
        bom_doc = frappe.get_doc("BOM", bom_no)
    else:
        # Find the default BOM for this item
        bom = frappe.get_all(
            "BOM", 
            filters={"item": item_code, "is_active": 1, "is_default": 1},
            fields=["name"],
            limit=1
        )
        
        if not bom:
            # Try to find any active BOM if default doesn't exist
            bom = frappe.get_all(
                "BOM", 
                filters={"item": item_code, "is_active": 1},
                fields=["name"],
                order_by="creation desc",
                limit=1
            )
            
        if not bom:
            return None
            
        bom_name = bom[0].name
        bom_doc = frappe.get_doc("BOM", bom_name)
    
    # Get item details
    item = frappe.get_doc("Item", item_code)
    
    # Prepare response
    result = {
        "name": bom_doc.name,
        "item_code": bom_doc.item,
        "item_name": item.item_name,
        "quantity": bom_doc.quantity,
        "uom": bom_doc.uom,
        "rate": bom_doc.raw_material_cost or 0,
        "amount": bom_doc.total_cost or 0,
        "version": getattr(bom_doc, 'version', '1'),
        "items": [],
        "operations": []
    }
    
    # Add raw materials
    for item in bom_doc.items:
        # Check if this item has its own BOM
        item_boms = frappe.get_all(
            "BOM", 
            filters={"item": item.item_code, "is_active": 1},
            fields=["name"],
            order_by="is_default desc, creation desc",
            limit=1
        )
        
        bom_no = item_boms[0].name if item_boms else None
        
        item_data = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "uom": item.uom,
            "rate": item.rate,
            "amount": item.amount,
            "bom_no": bom_no
        }
        
        result["items"].append(item_data)
    
    # Add operations if available
    if hasattr(bom_doc, 'operations') and bom_doc.operations:
        for op in bom_doc.operations:
            result["operations"].append({
                "operation": op.operation,
                "workstation": op.workstation,
                "time_in_mins": op.time_in_mins,
                "operating_cost": op.operating_cost
            })
    
    return result

@frappe.whitelist()
def get_child_bom_details(bom_no):
    """Get BOM details for a specific BOM number"""
    if not bom_no:
        frappe.throw(_("BOM number is required"))
    
    bom_doc = frappe.get_doc("BOM", bom_no)
    return get_bom_details(bom_doc.item, bom_no)
@frappe.whitelist()
def update_bom_quantities(bom_no, updated_items):
    if not frappe.has_permission("BOM", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    
    updated_items = json.loads(updated_items) if isinstance(updated_items, str) else updated_items
    
    if not updated_items:
        return {"status": "error", "message": "No items to update"}
    
    bom = frappe.get_doc("BOM", bom_no)
    
    for update in updated_items:
        for i, item in enumerate(bom.items):
            if item.item_code == update.get("item_code") and i == update.get("idx"):
                item.qty = update.get("qty")
                break
    
    bom.update_cost()
    bom.calculate_cost()
    bom.save()
    
    frappe.msgprint(_("BOM updated successfully"))
    
    return {"status": "success"}
