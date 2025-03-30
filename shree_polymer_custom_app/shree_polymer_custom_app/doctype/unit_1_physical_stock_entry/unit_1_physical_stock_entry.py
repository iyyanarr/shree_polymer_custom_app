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

    # For all item types, prioritize U1-Store when checking inventory
    stock_balance = fetch_stock_from_warehouses(batch_or_mixed_barcode, warehouses)

    if not stock_balance:
        print("No stock balance found for the batch in any warehouse")
        return {"message": f"No stock found for {batch_or_mixed_barcode} in any configured warehouse."}

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
