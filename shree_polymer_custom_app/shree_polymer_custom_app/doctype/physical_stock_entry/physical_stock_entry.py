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

    # Direct batch lookup for specific item groups
    if item_group in ['Raw Material', 'Batch', 'Final Batch']:
        print(f"Processing {item_group} flow with direct batch lookup")
        stock_balance = frappe.db.get_value(
            'Item Batch Stock Balance',
            {'batch_no': batch_or_mixed_barcode, 'warehouse': warehouse},
            ['item_code', 'item_name', 'description', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
            as_dict=True
        )
        print(f"{item_group} Stock Balance: {stock_balance}")

        if not stock_balance:
            print(f"No stock balance found for {item_group}")
            return {"message": f"No Item Batch Stock Balance data found for {item_group} and given batch."}

        return stock_balance
    
    # For all other item types, get batch number from stock entry first
    else:
        print(f"Processing {item_group}: Looking up related stock entry for barcode: {batch_or_mixed_barcode}")
        stock_entry = frappe.db.get_value(
            'Stock Entry Detail',
            {'mix_barcode': batch_or_mixed_barcode},
            ['batch_no'],
            as_dict=True
        )
        
        if stock_entry and stock_entry.get('batch_no'):
            search_batch = stock_entry.get('batch_no')
            print(f"Found batch number {search_batch} from stock entry")
            
            # Fetch Item Batch Stock Balance using obtained batch_no
            stock_balance = frappe.db.get_value(
                'Item Batch Stock Balance',
                {'batch_no': search_batch, 'warehouse': warehouse},
                ['item_code', 'item_name', 'description', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
                as_dict=True
            )
            print(f"Final Stock Balance: {stock_balance}")

            if not stock_balance:
                print(f"No stock balance found for the batch {search_batch}")
                return {"message": f"No Item Batch Stock Balance data found for the retrieved batch number {search_batch}."}

            return stock_balance
        else:
            print(f"No stock entry found for mix_barcode: {batch_or_mixed_barcode}")
            return {"message": f"No stock entry found for barcode {batch_or_mixed_barcode}"}

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