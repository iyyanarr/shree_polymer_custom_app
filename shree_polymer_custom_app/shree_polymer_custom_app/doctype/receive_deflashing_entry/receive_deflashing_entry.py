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
    """
    Creates stock entries for the received deflashing items
    Args:
        doc_name (str): Name of the Receive Deflashing Entry document
        items (list): List of items to create stock entries for
    Returns:
        dict: Information about processed items and created stock entries
    """
    print("DEBUG: Starting create_stock_entries function")
    print(f"DEBUG: Received doc_name: {doc_name}")
    print(f"DEBUG: Received items type: {type(items)}")

    if not doc_name or not items:
        print("DEBUG: Missing required parameters")
        frappe.throw(_("Missing required parameters"))

    # Convert items from JSON string if needed
    if isinstance(items, str):
        try:
            print(f"DEBUG: Converting items from JSON string: {items[:100]}...")
            items = json.loads(items)
            print(f"DEBUG: Converted items count: {len(items)}")
        except Exception as e:
            print(f"DEBUG: Error parsing JSON: {str(e)}")
            frappe.throw(_("Invalid items data: {0}").format(str(e)))

    # Get the parent document and filter items
    try:
        print(f"DEBUG: Getting parent doc: {doc_name}")
        parent_doc = frappe.get_doc("Receive Deflashing Entry", doc_name)
        print(f"DEBUG: Parent doc retrieved, items count: {len(parent_doc.items)}")

        # Filter items that need stock entries
        items_to_process = []
        for item_data in items:
            matching_items = [row for row in parent_doc.items 
                            if row.lot_no == item_data.get("lot_no") ]
                            # and (not row.stock_entry or row.stock_entry == "") 
                            # and (not row.stock_entry_status or row.stock_entry_status == "")]
            
            if matching_items:
                print(f"DEBUG: Found matching item without stock entry for lot_no: {item_data.get('lot_no')}")
                items_to_process.append(item_data)

        print(f"DEBUG: Found {len(items_to_process)} items eligible for stock entry creation")
        items = items_to_process

    except frappe.DoesNotExistError:
        print(f"DEBUG: Parent doc not found: {doc_name}")
        frappe.throw(_("Receive Deflashing Entry {0} not found").format(doc_name))
    except Exception as e:
        print(f"DEBUG: Error getting parent doc: {str(e)}")
        frappe.throw(_("Error retrieving document: {0}").format(str(e)))

    # Get target warehouse from the document
    target_warehouse = parent_doc.receiving_warehouse
    print(f"DEBUG: Target warehouse: {target_warehouse}")
    if not target_warehouse:
        print("DEBUG: Target warehouse is missing")
        frappe.throw(_("Receiving Warehouse is not specified in the document"))

    processed_items = []
    stock_entries = []
    stock_entry_refs = []

    # Process each filtered item
    print(f"DEBUG: Starting to process {len(items)} items")
    for item_idx, item_data in enumerate(items):
        try:
            print(f"DEBUG: Processing item {item_idx}, lot_no: {item_data.get('lot_no')}")
            
            # Find the corresponding child item
            child_items = [row for row in parent_doc.items if row.lot_no == item_data.get("lot_no")]
            print(f"DEBUG: Found {len(child_items)} matching child items")
            
            if not child_items:
                print(f"DEBUG: No child items found for lot {item_data.get('lot_no')}")
                continue

            child_item = child_items[0]
            print(f"DEBUG: Child item details - vendor: {child_item.vendor}, product_ref: {child_item.product_ref}")

            source_warehouse = 'U1-Transit Store - SPP INDIA'
            print(f"DEBUG: Source warehouse (vendor): {source_warehouse}")
            
            if not source_warehouse:
                print(f"DEBUG: Source warehouse missing for lot {item_data.get('lot_no')}")
                frappe.throw(_("Source Warehouse (Vendor) is not specified for lot {0}").format(item_data.get("lot_no")))

            # Create stock entry
            print("DEBUG: Creating stock entry")
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Transfer"
            stock_entry.company = frappe.defaults.get_user_default("Company")
            stock_entry.posting_date = frappe.utils.today()
            stock_entry.posting_time = frappe.utils.nowtime()
            stock_entry.reference_doctype = "Receive Deflashing Entry"
            stock_entry.reference_docname = doc_name
            stock_entry.spp_batch_number = item_data.get("lot_no")

            # Get source document info if available
            if item_data.get("stock_entry_reference"):
                print(f"DEBUG: Getting source doc: {item_data.get('stock_entry_reference')}")
                source_doc = frappe.get_doc("Stock Entry", item_data.get("stock_entry_reference"))
                stock_entry.deflash_dispatch_reference = source_doc.name
                print(f"DEBUG: Set deflash_dispatch_reference: {source_doc.name}")

            print(f"DEBUG: Item data - product_ref: {item_data.get('product_ref')}, received_weight: {item_data.get('received_weight')}")

            # Get item details and conversion factor
            item_doc = frappe.get_doc("Item", item_data.get("product_ref"))

            # Find the kg to nos conversion factor from the UOMs table
            if item_data.get("status") == "Received":
                # For Received items, use the original qty_nos without conversion
                qty_in_nos = float(item_data.get("qty_nos") or 0)
                print(f"DEBUG: Using original qty_nos for Received item: {qty_in_nos}")
            else:
                # For other items, perform the weight conversion
                conversion_factor = 1  # Default value
                for uom_row in item_doc.uoms:
                    if uom_row.uom == "Kg":
                        conversion_factor = uom_row.conversion_factor
                        print(f"DEBUG: Found conversion factor for {item_data.get('product_ref')}: {conversion_factor}")
                        break

                # Calculate quantity in nos from weight
                weight_in_kg = float(item_data.get("received_weight") or 0)
                qty_in_nos = weight_in_kg * conversion_factor
                print(f"DEBUG: Converting {weight_in_kg} kg to nos using factor {conversion_factor} = {qty_in_nos} nos")

            # Add item to stock entry
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

            # Save and submit the stock entry
            print("DEBUG: Inserting stock entry")
            stock_entry.insert()
            print(f"DEBUG: Stock entry inserted with name: {stock_entry.name}")
            print("DEBUG: Submitting stock entry")
            stock_entry.submit()
            print("DEBUG: Stock entry submitted")

            # Update the child table item
            print("DEBUG: Updating child table item")
            child_item.stock_entry = stock_entry.name
            child_item.received_product_qty_nos = qty_in_nos
            child_item.stock_entry_status = "Created"
            child_item.stock_entry_reference_return = stock_entry.name

            # Add to processed lists
            processed_items.append(item_data.get("lot_no"))
            stock_entries.append(stock_entry.name)
            stock_entry_refs.append(stock_entry.name)
            
            print(f"DEBUG: Successfully processed item {item_idx}")
            frappe.db.commit()

        except Exception as e:
            print(f"DEBUG: Error processing item {item_idx}: {str(e)}")
            frappe.log_error(
                message=f"Error creating stock entry for lot {item_data.get('lot_no')}: {str(e)}",
                title="Stock Entry Creation Error"
            )

    # Update parent document
    if processed_items:
        print(f"DEBUG: Updating parent document with {len(stock_entry_refs)} stock entry references")
        
        # Calculate totals
        total_lots = len(processed_items)
        total_qty_kgs = 0
        total_qty_nos = 0
        
        for item in parent_doc.items:
            if item.stock_entry:
                total_qty_kgs += float(item.received_weight or 0)
                total_qty_nos += float(item.qty_nos or 0)

        print(f"DEBUG: Calculated totals - Lots: {total_lots}, Kgs: {total_qty_kgs}, Nos: {total_qty_nos}")

        # Update parent document fields
        parent_doc.total_lots = total_lots
        parent_doc.total_qty_kgs = total_qty_kgs
        parent_doc.total_qty_nos = total_qty_nos

        # Add stock entries to reference table
        for stock_entry_name in stock_entry_refs:
            exists = False
            if parent_doc.received_stock_entry_ref:
                exists = any(row.stock_entry == stock_entry_name
                           for row in parent_doc.received_stock_entry_ref)
            
            if not exists:
                parent_doc.append('received_stock_entry_ref', {
                    'stock_entry': stock_entry_name
                })
                print(f"DEBUG: Added stock entry {stock_entry_name} to received_stock_entry_ref table")

        # Update document status
        all_items_processed = True
        for item in parent_doc.items:
            if not item.stock_entry_reference_return:
                all_items_processed = False
                break

        parent_doc.status = "Closed" if all_items_processed else "Pending"
        print(f"DEBUG: Setting document status to: {parent_doc.status}")
        
        print("DEBUG: Saving parent document with updated totals")
        parent_doc.save()
        parent_doc.submit()
    else:
        print("DEBUG: No items were processed")

    print(f"DEBUG: Returning results - processed items: {len(processed_items)}, stock entries: {len(stock_entries)}")
    return {
        "processed_items": processed_items,
        "stock_entries": stock_entries
    }

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
