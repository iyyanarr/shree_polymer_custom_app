import frappe
import json

def debug_full_snapshot():
    frappe.connect()
    item_code = "C_6122"
    warehouse = "Compound Inspection - SPP INDIA"
    
    # Run the equivalent query from sync_api.py for this item/warehouse
    query = f"""
		SELECT 
			data.item_code,
			data.warehouse,
			SUM(data.actual_qty) as actual_qty,
			data.batch_no,
			MAX(data.barcode) as barcode
		FROM (
			-- 1. Legacy SLE Batches
			SELECT 
				bin.item_code,
				bin.warehouse,
				sle.actual_qty as actual_qty,
				batch.name as batch_no,
				batch.barcode_text as barcode
			FROM `tabBin` bin
			INNER JOIN `tabItem` item ON bin.item_code = item.name
			INNER JOIN `tabWarehouse` ware ON bin.warehouse = ware.name
			INNER JOIN `tabStock Ledger Entry` sle ON sle.item_code = bin.item_code AND sle.warehouse = bin.warehouse
			LEFT JOIN `tabBatch` batch ON sle.batch_no = batch.name AND item.has_batch_no = 1
			WHERE 
				item.name = '{item_code}'
				AND bin.warehouse = '{warehouse}'
				AND item.has_batch_no = 1
				AND sle.batch_no IS NOT NULL AND sle.batch_no != ''
				AND sle.is_cancelled = 0

			UNION ALL

			-- 2. Modern v15 SABB Batches
			SELECT 
				bin.item_code,
				bin.warehouse,
				sbe.qty as actual_qty,
				sbe.batch_no as batch_no,
				sed.mix_barcode as barcode
			FROM `tabBin` bin
			INNER JOIN `tabItem` item ON bin.item_code = item.name
			INNER JOIN `tabWarehouse` ware ON bin.warehouse = ware.name
			INNER JOIN `tabStock Ledger Entry` sle ON sle.item_code = bin.item_code AND sle.warehouse = bin.warehouse
			INNER JOIN `tabSerial and Batch Bundle` sabb ON sle.serial_and_batch_bundle = sabb.name
			INNER JOIN `tabSerial and Batch Entry` sbe ON sbe.parent = sabb.name
			LEFT JOIN `tabStock Entry Detail` sed ON sabb.voucher_no = sed.parent AND sabb.voucher_detail_no = sed.name
			WHERE 
				item.name = '{item_code}'
				AND bin.warehouse = '{warehouse}'
				AND item.has_batch_no = 1
				AND (sle.batch_no IS NULL OR sle.batch_no = '')
				AND sle.is_cancelled = 0
		) data
		GROUP BY 
			data.item_code, data.warehouse, data.batch_no
    """
    
    results = frappe.db.sql(query, as_dict=True)
    print(f"Results for {item_code} in {warehouse}:")
    print(json.dumps(results, indent=2))
    
    # Also check the total Bin quantity
    bin_qty = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
    print(f"\nBin Total Actual Qty: {bin_qty}")

if __name__ == "__main__":
    debug_full_snapshot()
