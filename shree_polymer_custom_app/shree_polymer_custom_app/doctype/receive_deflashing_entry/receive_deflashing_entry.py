# Copyright (c) 2025, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import json

class ReceiveDeflashingEntry(Document):
    pass

@frappe.whitelist()
def get_despatch_info(dd_number):
    try:
        despatch_entry = frappe.get_doc("Despatch To U1 Entry", dd_number)
        return despatch_entry
    except frappe.DoesNotExistError:
        frappe.throw(_("Despatch Entry not found for DD Number: {0}").format(dd_number))
    except Exception as e:
        frappe.log_error(message=str(e))
        frappe.throw(_("An error occurred while fetching the Despatch Entry"))

@frappe.whitelist()
def create_stock_entries(doc_name, items):
    spp_settings = frappe.get_single("SPP Settings")
    """Creates stock entries for received deflashing items"""
    if not doc_name or not items:
        frappe.throw(_("Missing required parameters"))

    # Parse JSON items if needed
    items = json.loads(items) if isinstance(items, str) else items
    
    # Get parent doc and validate
    try:
        parent_doc = frappe.get_doc("Receive Deflashing Entry", doc_name)
        target_warehouse = parent_doc.receiving_warehouse
        if not target_warehouse:
            frappe.throw(_("Receiving Warehouse is not specified"))
    except frappe.DoesNotExistError:
        frappe.throw(_("Receive Deflashing Entry {0} not found").format(doc_name))

    # Pre-process items and build lookup maps
    item_map = {item.lot_no: item for item in parent_doc.items}
    items_to_process = [item for item in items if item.get("lot_no") in item_map]
    
    if not items_to_process:
        return {"processed_items": [], "stock_entries": []}

    # Cache common values
    company = frappe.defaults.get_user_default("Company")
    source_warehouse = spp_settings.p_target_warehouse
    processed_data = {
        "items": [],
        "stock_entries": [],
        "refs": [],
        "total_kgs": 0,
        "total_nos": 0
    }

    # Process items in batches
    for item_data in items_to_process:
        try:
            child_item = item_map.get(item_data.get("lot_no"))
            if not child_item:
                continue

            # Get item details and calculate quantities
            item_doc = frappe.get_doc("Item", item_data.get("product_ref"))
            qty_in_nos = _calculate_quantity(item_data, item_doc)

            # Create and submit stock entry
            stock_entry = _create_stock_entry(
                item_data=item_data,
                qty_in_nos=qty_in_nos,
                company=company,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
                doc_name=doc_name,
                item_doc=item_doc
            )

            # Update child item and tracking data
            _update_child_item(child_item, stock_entry.name, qty_in_nos)
            _track_processed_item(processed_data, item_data, child_item, stock_entry.name)

        except Exception as e:
            frappe.log_error(
                message=f"Error processing lot {item_data.get('lot_no')}: {str(e)}",
                title="Stock Entry Creation Error"
            )

    # Update parent document if items were processed
    if processed_data["items"]:
        _update_parent_document(parent_doc, processed_data)

    return {
        "processed_items": processed_data["items"],
        "stock_entries": processed_data["stock_entries"]
    }

def _calculate_quantity(item_data, item_doc):
    """Calculate quantity based on item status"""
    if item_data.get("status") == "Received":
        return float(item_data.get("received_product_qty_nos") or 0)
    
    conversion_factor = 1
    for uom_row in item_doc.uoms:
        if uom_row.uom == "Kg":
            conversion_factor = uom_row.conversion_factor
            break
    
    weight_in_kg = float(item_data.get("received_weight") or 0)
    return weight_in_kg * conversion_factor

def _create_stock_entry(item_data, qty_in_nos, company, source_warehouse, 
                       target_warehouse, doc_name, item_doc):
    """Create and submit stock entry"""
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.update({
        "stock_entry_type": "Material Transfer",
        "company": company,
        "posting_date": frappe.utils.today(),
        "posting_time": frappe.utils.nowtime(),
        "reference_doctype": "Receive Deflashing Entry",
        "reference_docname": doc_name,
        "spp_batch_number": item_data.get("lot_no")
    })

    if item_data.get("stock_entry_reference"):
        stock_entry.deflash_dispatch_reference = frappe.get_value(
            "Stock Entry", item_data.get("stock_entry_reference"), "name"
        )

    stock_entry.append("items", {
        "item_code": item_data.get("product_ref"),
        "qty": qty_in_nos,
        "stock_uom": "Nos",
        "uom": "Nos",
        "conversion_factor": 1,
        "s_warehouse": source_warehouse,
        "t_warehouse": target_warehouse,
        "use_serial_batch_fields": 1,
        "batch_no": item_data.get("batch_no"),
        "spp_batch_number": item_data.get("lot_no"),
        "basic_rate": item_doc.standard_rate or 0
    })

    stock_entry.insert()
    stock_entry.submit()
    return stock_entry

def _update_child_item(child_item, stock_entry_name, qty_in_nos):
    """Update child table item"""
    child_item.stock_entry = stock_entry_name
    child_item.received_product_qty_nos = qty_in_nos
    child_item.stock_entry_status = "Created"
    child_item.stock_entry_reference_return = stock_entry_name

def _track_processed_item(processed_data, item_data, child_item, stock_entry_name):
    """Track processed item data"""
    processed_data["items"].append(item_data.get("lot_no"))
    processed_data["stock_entries"].append(stock_entry_name)
    processed_data["refs"].append(stock_entry_name)
    processed_data["total_kgs"] += float(child_item.received_weight or 0)
    processed_data["total_nos"] += float(child_item.qty_nos or 0)

def _update_parent_document(parent_doc, processed_data):
    """Update parent document with processed data"""
    parent_doc.update({
        "total_lots": len(processed_data["items"]),
        "total_qty_kgs": processed_data["total_kgs"],
        "total_qty_nos": processed_data["total_nos"]
    })

    # Add stock entry references
    for stock_entry_name in processed_data["refs"]:
        if not any(row.stock_entry == stock_entry_name 
                  for row in (parent_doc.received_stock_entry_ref or [])):
            parent_doc.append('received_stock_entry_ref', {
                'stock_entry': stock_entry_name
            })

    # Check if all items have stock entries and total received lots match
    all_processed = (all(item.stock_entry_status == "Created" for item in parent_doc.items) and
                     len(parent_doc.items) == parent_doc.total_received_lots)
    
    parent_doc.status = "Closed" if all_processed else "Pending"
    parent_doc.save()
    if all_processed:
        parent_doc.submit()

@frappe.whitelist()
def check_existing_entries(dd_number, current_doc=None):
    """Check if there are existing Receive Deflashing Entry docs for the given DD number."""
    filters = {
        'dd_number': dd_number,
        'docstatus': ['<', 2]  # Not cancelled
    }
    
    if current_doc:
        filters['name'] = ['!=', current_doc]
    
    existing = frappe.get_all('Receive Deflashing Entry',
                             filters=filters,
                             fields=['name'],
                             limit=1)
    
    return {
        'exists': bool(existing),
        'doc_name': existing[0].name if existing else None
    }