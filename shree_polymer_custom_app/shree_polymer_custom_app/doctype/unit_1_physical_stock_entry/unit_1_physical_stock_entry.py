import frappe
from frappe.model.document import Document

class Unit1PhysicalStockEntry(Document):
    pass

WAREHOUSE_MAPPING = {
    'Products': ['U1-Store - SPP INDIA', 'U2-Store - SPP INDIA'],
    'Finished Product': ['U1-Store - SPP INDIA', 'U2-Store - SPP INDIA'],
    'Products Sales': ['U2-Store - SPP INDIA']
}

@frappe.whitelist()
def get_filtered_stock_by_parameters(batch_or_mixed_barcode, item_group):
    print("\n=== Debug: get_filtered_stock_by_parameters ===")
    print(f"Input - Batch/Barcode: {batch_or_mixed_barcode}, Item Group: {item_group}")

    if not batch_or_mixed_barcode or not item_group:
        print("Error: Missing required parameters")
        return {"error": "Batch/Barcode and Item Group are required"}

    warehouses = get_warehouses_for_item_group(item_group)
    print(f"Mapped Warehouses: {warehouses}")
    if not warehouses:
        print("Error: No warehouse mapping found")
        return {"error": "Warehouse mapping not found for the given item group"}
    
    # Prepare the batch code based on item group
    search_batch = batch_or_mixed_barcode
    
    if "Products" in item_group and "Sales" not in item_group:
        # For Products, add 'P' prefix
        search_batch = f"P{batch_or_mixed_barcode}"
        print(f"Products group: Added P prefix. Modified search batch: {search_batch}")
    
    elif "Finished Product" in item_group:
        # For Finished Product, add 'F' prefix
        search_batch = f"F{batch_or_mixed_barcode}"
        print(f"Finished Product group: Added F prefix. Modified search batch: {search_batch}")
    
    elif "Products Sales" in item_group:
        # For Products Sales, get batch number from stock entry
        print(f"Products Sales: Looking up related stock entry for barcode: {batch_or_mixed_barcode}")
        stock_entry = frappe.db.get_value(
            'Stock Entry Detail',
            {'mix_barcode': batch_or_mixed_barcode},
            ['batch_no'],
            as_dict=True
        )
        
        if stock_entry and stock_entry.get('batch_no'):
            search_batch = stock_entry.get('batch_no')
            print(f"Found batch number {search_batch} from stock entry")
        else:
            print(f"No stock entry found for mix_barcode: {batch_or_mixed_barcode}")
            return {"message": f"No stock entry found for barcode {batch_or_mixed_barcode}"}

    # For all item types, prioritize U1-Store when checking inventory
    stock_balance = fetch_stock_from_warehouses(search_batch, warehouses)

    if not stock_balance:
        print("No stock balance found for the batch in any warehouse")
        return {"message": f"No stock found for {search_batch} in any configured warehouse."}

    return stock_balance

def get_warehouses_for_item_group(item_group):
    print(f"\nDebug: get_warehouses_for_item_group")
    print(f"Looking up warehouses for item group: {item_group}")
    for key, value in WAREHOUSE_MAPPING.items():
        if key in item_group:
            print(f"Found warehouse mappings: {value}")
            # Ensure U1-Store is always prioritized first if it's in the list
            sorted_warehouses = sorted(value, key=lambda x: 0 if 'U1-Store' in x else 1)
            print(f"Prioritized warehouse order: {sorted_warehouses}")
            return sorted_warehouses
    print("No warehouse mapping found")
    return None

def fetch_stock_from_warehouses(batch_or_mixed_barcode, warehouses):
    for warehouse in warehouses:
        print(f"Checking stock in warehouse: {warehouse}")
        stock_balance = frappe.db.get_value(
            'Item Batch Stock Balance',
            {'batch_no': batch_or_mixed_barcode, 'warehouse': warehouse},
            ['item_code', 'item_name', 'description', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
            as_dict=True
        )
        if stock_balance:
            print(f"Stock Balance found in {warehouse}: {stock_balance}")
            return stock_balance
        else:
            print(f"No stock found in {warehouse} for batch {batch_or_mixed_barcode}")
    return None
