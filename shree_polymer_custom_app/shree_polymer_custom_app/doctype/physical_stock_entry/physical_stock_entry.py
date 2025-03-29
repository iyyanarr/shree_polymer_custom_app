import frappe
from frappe.model.document import Document

class PhysicalStockEntry(Document):
    pass

WAREHOUSE_MAPPING = {
    'Raw Material': 'Incoming Store - SPP INDIA',
    'Compound': 'U3-Store - SPP INDIA',
    'Compound - Sheeting': 'Sheeting Warehouse - SPP INDIA',
    'Batch': 'U3-Store - SPP INDIA',
    'Final Batch': 'U3-Store - SPP INDIA',
    'Master Batch': 'U3-Store - SPP INDIA',
    'Mat': 'U2-Store - SPP INDIA',
    'Products': 'U2-Store - SPP INDIA',
    'Finished Product': 'U2-Store - SPP INDIA',
    'Cut Bit': 'Cutbit Warehouse - SPP INDIA',
    'Products Sales': 'U2-Store - SPP INDIA'
}



@frappe.whitelist()
def get_filtered_stock_by_parameters(batch_or_mixed_barcode, item_group):
    print("\n=== Debug: get_filtered_stock_by_parameters ===")
    print(f"Input - Batch/Barcode: {batch_or_mixed_barcode}, Item Group: {item_group}")

    if not batch_or_mixed_barcode or not item_group:
        print("Error: Missing required parameters")
        return {"error": "Batch/Barcode and Item Group are required"}

    warehouse = get_warehouse_for_item_group(item_group)
    print(f"Mapped Warehouse: {warehouse}")
    
    if not warehouse:
        print("Error: No warehouse mapping found")
        return {"error": "Warehouse mapping not found for the given item group"}

    # If Raw Material (RW):
    if item_group == 'Raw Material':
        print("Processing Raw Material flow")
        stock_balance = frappe.db.get_value(
            'Item Batch Stock Balance',
            {'batch_no': batch_or_mixed_barcode, 'warehouse': warehouse},
            ['item_code', 'item_name', 'description', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
            as_dict=True
        )
        print(f"Raw Material Stock Balance: {stock_balance}")

        if not stock_balance:
            print("No stock balance found for Raw Material")
            return {"message": "No Item Batch Stock Balance data found for Raw Material and given batch."}

        return stock_balance

    # For other Item Types:
    else:
        print(f"Processing other item type: {item_group}")
        # # Step 1: Query Stock Entry Detail to get Batch Number
        # sed_result = frappe.db.sql("""
        #     SELECT sed.batch_no, sed.item_code, sed.qty
        #     FROM `tabStock Entry Detail` sed
        #     INNER JOIN `tabItem` i ON i.item_code = sed.item_code
        #     INNER JOIN `tabStock Entry` se ON se.name = sed.parent
        #     WHERE sed.mix_barcode = %s
        #         AND sed.item_group = %s
        #         AND sed.batch_no IS NOT NULL AND sed.batch_no != ''
        #         AND sed.is_finished_item = 1
        #         AND se.stock_entry_type = 'Manufacture'
        #     ORDER BY se.posting_date DESC, se.posting_time DESC
        #     LIMIT 1
        # """, (batch_or_mixed_barcode, item_group), as_dict=True)
        # print(f"Stock Entry Detail Query Result: {sed_result}")

        # if not sed_result:
        #     print("No finished item batch found")
        #     return {"message": "No Finished Item Batch found for the given barcode and item group."}

        # batch_no = sed_result[0].batch_no
        # print(f"Retrieved Batch Number: {batch_no}")

        # Step 2: Fetch Item Batch Stock Balance using obtained batch_no
        stock_balance = frappe.db.get_value(
            'Item Batch Stock Balance',
            {'batch_no':batch_or_mixed_barcode, 'warehouse': warehouse},
            ['item_code', 'item_name', 'description', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
            as_dict=True
        )
        print(f"Final Stock Balance: {stock_balance}")

        if not stock_balance:
            print("No stock balance found for the batch")
            return {"message": "No Item Batch Stock Balance data found for the retrieved batch number."}

        return stock_balance

def get_warehouse_for_item_group(item_group):
    print(f"\nDebug: get_warehouse_for_item_group")
    print(f"Looking up warehouse for item group: {item_group}")
    for key, value in WAREHOUSE_MAPPING.items():
        if key in item_group:
            print(f"Found warehouse mapping: {value}")
            return value
    print("No warehouse mapping found")
    return None



# Example Usage:
# raw_material_stock_info = get_filtered_stock_by_parameters("RW_BATCH123", "Raw Material")
# other_item_stock_info = get_filtered_stock_by_parameters("MIXED_BARCODE123", "Finished Product")
# frappe.msgprint(str(raw_material_stock_info))