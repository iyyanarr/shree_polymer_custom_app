# Copyright (c) 2025, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PhysicalStockEntry(Document):
	pass

# Warehouse mapping dictionary
WAREHOUSE_MAPPING = {
    'Raw Material': 'Incoming Store - SPP INDIA',
    'Compound': 'U3-Store - SPP INDIA',
    'Batch': 'U3-Store - SPP INDIA',
    'Final Batch': 'U3-Store - SPP INDIA',
    'Master Batch': 'U3-Store - SPP INDIA',
    'Matt': 'U2-Store - SPP INDIA',
    'Products': 'U2-Store - SPP INDIA',
    'Finished Product': 'U2-Store - SPP INDIA',
    'Cut Bit': 'Cutbit Warehouse - SPP INDIA'
}

@frappe.whitelist()
def get_filtered_stock_by_parameters(mixed_barcode, item_group):
    print('**************************',mixed_barcode, item_group)
    """
    Fetch stock details grouped by item using mixed_barcode and item_group filters,
    while mapping the warehouse based on item_group in Python.
    """
    if not mixed_barcode or not item_group:
        return {"error": "Mixed Barcode and Item Group are required"}

    warehouse = get_warehouse_for_item_group(item_group)
    if not warehouse:
        return {"error": "Warehouse mapping not found for the given item group"}
    print('**************************',warehouse,mixed_barcode, item_group)
    sql_query = """
        SELECT 
            sed.item_code,
            i.item_name,
            sed.spp_batch_number,
            sed.mix_barcode,
            sed.batch_no,
            SUM(sed.qty) AS current_stock,
            sed.t_warehouse
        FROM 
            `tabStock Entry` se
        JOIN 
            `tabStock Entry Detail` sed ON se.name = sed.parent
        JOIN 
            `tabItem` i ON sed.item_code = i.item_code
        WHERE 
            se.stock_entry_type = 'Manufacture' AND
            sed.mix_barcode = %s AND
            i.item_group = %s AND
            sed.t_warehouse = %s AND
            sed.spp_batch_number IS NOT NULL AND sed.spp_batch_number != '' AND
            sed.t_warehouse IS NOT NULL AND sed.t_warehouse != '' AND
            sed.batch_no IS NOT NULL AND sed.batch_no != ''
        GROUP BY 
            sed.item_code, sed.spp_batch_number, sed.mix_barcode, sed.batch_no,  sed.t_warehouse
        ORDER BY 
            sed.item_code, sed.spp_batch_number;
    """

    try:
        result = frappe.db.sql(sql_query, (mixed_barcode,warehouse,item_group,), as_dict=True)
        if not result:
            return {"message": "No data found for the given filters."}
        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_filtered_stock_by_parameters Error")
        return {"error": str(e)}

def get_warehouse_for_item_group(item_group):
    """
    Map item groups to their corresponding warehouse.
    """
    for key, value in WAREHOUSE_MAPPING.items():
        if key in item_group:
            return value
    return None

# Example usage
# filtered_data = get_filtered_stock_by_parameters("MB12345", "Products")
# frappe.msgprint(str(filtered_data))