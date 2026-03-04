import frappe
import json

def check_stock_source():
    frappe.connect()
    # Patterns from user screenshot
    item_code = "C_6122"
    barcode_pattern = "26C03X001"
    
    # Check Bin for item_code
    bins = frappe.db.sql(f"""
        SELECT warehouse, actual_qty, reserved_qty 
        FROM tabBin 
        WHERE item_code = '{item_code}' AND actual_qty > 0
    """, as_dict=1)
    
    print(f"Bins for {item_code}:")
    for b in bins:
        print(f"  Wh: {b.warehouse}, Qty: {b.actual_qty}")
    
    # Check for specific barcode in Stock Ledger or Batch
    # Batches often contain the barcode/spp_batch_no
    batches = frappe.db.get_all("Batch", 
                               filters={"name": ["like", f"%{barcode_pattern}%"]},
                               fields=["name", "item_code", "expiry_date"])
    print(f"\nBatches matching '{barcode_pattern}':")
    for b in batches:
        print(f"  Batch: {b.name}, Item: {b.item_code}")
        
    # Check Stock Ledger for recent entries of C_6122
    sle = frappe.db.sql(f"""
        SELECT posting_date, warehouse, batch_no, actual_qty, voucher_no
        FROM `tabStock Ledger Entry`
        WHERE item_code = '{item_code}'
        ORDER BY creation DESC
        LIMIT 10
    """, as_dict=1)
    
    print(f"\nRecent SLEs for {item_code}:")
    for s in sle:
        print(f"  Date: {s.posting_date}, Wh: {s.warehouse}, Batch: {s.batch_no}, Qty: {s.actual_qty}, Doc: {s.voucher_no}")

if __name__ == "__main__":
    check_stock_source()
