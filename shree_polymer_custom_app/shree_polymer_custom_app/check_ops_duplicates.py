import frappe
import json

def get_duplicates_on_ops():
    frappe.connect()
    item_code = "C_6122"
    
    # Check Bin for the item
    bins = frappe.get_all("Bin", 
                         filters={"item_code": item_code, "actual_qty": [">", 0]},
                         fields=["warehouse", "actual_qty", "reserved_qty", "batch_no"])
    
    print(f"Bins found for {item_code} on this site:")
    print(json.dumps(bins, indent=2))
    
    # Search for the specific barcode from the user's screenshot: C_26C03X001
    barcode = "C_26C03X001"
    
    # Check Batch table
    batches = frappe.get_all("Batch", 
                            filters={"name": ["like", f"%{barcode}%"]},
                            fields=["name", "item_code", "expiry_date"])
    print(f"\nBatches matching '{barcode}':")
    print(json.dumps(batches, indent=2))
    
    # Check Stock Entry Details (where barcodes are often stored as mix_barcode)
    seds = frappe.db.sql(f"""
        SELECT parent, name, item_code, batch_no, mix_barcode, spp_batch_number, t_warehouse, qty
        FROM `tabStock Entry Detail`
        WHERE (mix_barcode LIKE '%{barcode}%' OR spp_batch_number LIKE '%{barcode}%')
          AND docstatus = 1
        ORDER BY creation DESC
        LIMIT 5
    """, as_dict=1)
    print(f"\nRecent Stock Entry Details matching '{barcode}':")
    print(json.dumps(seds, indent=2))

if __name__ == "__main__":
    get_duplicates_on_ops()
