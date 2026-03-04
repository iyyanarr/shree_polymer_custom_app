import frappe
from frappe.utils import today

def run():
    items_data = [
        {"item_code": "B_EH0039", "qty": 18.25, "batch_no": "26C04X01"},
        {"item_code": "FB_EH0039", "qty": 0.35, "batch_no": "26C04X02"},
        {"item_code": "B_7025", "qty": 20.54, "batch_no": "26C04X03"},
        {"item_code": "FB_7025", "qty": 0.45, "batch_no": "26C04X04"},
        {"item_code": "FB_7040", "qty": 5.15, "batch_no": "26C04X05"},
    ]

    print(f"📦 Creating Material Receipt with {len(items_data)} items...")
    
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.company = "SPP INDIA" if frappe.db.exists("Company", "SPP INDIA") else "SPP"
    se.posting_date = today()
    se.set_posting_time = 1

    target_warehouse = "U3-Store - SPP INDIA"
    if not frappe.db.exists("Warehouse", target_warehouse):
        whs = frappe.get_all("Warehouse", filters={"is_group": 0}, limit=1)
        if whs:
            target_warehouse = whs[0].name
        else:
            print("❌ No warehouse found")
            return

    for item in items_data:
        item_code = item["item_code"]
        test_barcode = item["batch_no"]
        qty = item["qty"]

        print(f"🔄 Checking Item: {item_code}")
        if not frappe.db.exists("Item", item_code):
            print(f"⚠️ Item {item_code} missing. Creating dummy batch for testing anyway if item exists in legacy?")
            # We assume items exist as it's a legacy site copy.
            continue

        print(f"🔄 Creating/Updating Batch: {test_barcode}")
        if frappe.db.exists("Batch", test_barcode):
            frappe.delete_doc("Batch", test_barcode, ignore_permissions=True)
            frappe.db.commit()

        batch = frappe.new_doc("Batch")
        batch.batch_id = test_barcode
        batch.item = item_code
        batch.insert(ignore_permissions=True)
        frappe.db.commit()

        se.append("items", {
            "item_code": item_code,
            "qty": qty,
            "t_warehouse": target_warehouse,
            "uom": "Kg",
            "stock_uom": "Kg",
            "conversion_factor": 1,
            "batch_no": test_barcode,
            "spp_batch_number": test_barcode,
            "mix_barcode": test_barcode
        })

    if not se.items:
        print("❌ No valid items found to add to Stock Entry")
        return

    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()
    print(f"✅ Material Receipt Submitted: {se.name} with {len(se.items)} items")
