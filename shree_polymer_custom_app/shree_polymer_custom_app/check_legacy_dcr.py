import frappe
import json

def check_dcr():
    frappe.connect()
    dcr_name = "MTDCR-2026-03-03-00002"
    if not frappe.db.exists("Delivery Challan Receipt", dcr_name):
        print(f"DCR {dcr_name} not found")
        return

    dcr = frappe.get_doc("Delivery Challan Receipt", dcr_name)
    print(f"DCR: {dcr.name}")
    print(f"Status: {dcr.status}")
    print(f"Inward Material Type: {dcr.inward_material_type}")
    print(f"Stock Entry Reference: {dcr.stock_entry_reference}")
    
    print("\nDC Items:")
    for item in dcr.dc_items:
        it_group = frappe.db.get_value("Item", item.item_to_manufacture, "item_group")
        print(f"  Item to Manufactue: {item.item_to_manufacture} (Group: {it_group})")
        print(f"  DC No: {item.dc_no}")
        print(f"  Operation: {item.operation}")
        print(f"  Qty: {item.qty}")
        print("-" * 20)

if __name__ == "__main__":
    check_dcr()
