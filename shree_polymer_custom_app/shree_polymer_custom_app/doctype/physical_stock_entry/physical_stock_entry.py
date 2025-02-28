# Copyright (c) 2025, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PhysicalStockEntry(Document):
	pass



WAREHOUSE_MAPPING = {
    'Raw Material': 'Incoming Store - SPP INDIA',
    'Compund & Batch & Master Batch': 'U3-Store - SPP INDIA',
    'Matt & Product & Finished Good': 'U2-Store - SPP INDIA',
    'Cut Bit':'Cutbit Warehouse - SPP INDIA'
}

@frappe.whitelist()
def get_item_details(batch_number):
    batch = frappe.get_doc('Batch', batch_number)
    item_code = batch.item
    item_name = frappe.db.get_value('Item', item_code, 'item_name')
    item_group = frappe.db.get_value('Item', item_code, 'item_group')
    warehouse = get_warehouse_for_item_group(item_group)
    current_stock = frappe.db.get_value('Bin', {'item_code': item_code, 'warehouse': warehouse}, 'actual_qty')

    return {
        'item_code': item_code,
        'item_name': item_name,
        'item_group': item_group,
        'warehouse': warehouse,
        'current_stock': current_stock
    }

def get_warehouse_for_item_group(item_group):
    if "Raw Material" in item_group:
        return 'Incoming Store - SPP INDIA'
    elif "Compound" in item_group or "Batch" in item_group or "Master Batch" in item_group:
        return 'U3-Store - SPP INDIA'
    elif "Matt" in item_group or "Product" in item_group or "Finished Good" in item_group:
        return 'U2-Store - SPP INDIA'
    else:
        return None