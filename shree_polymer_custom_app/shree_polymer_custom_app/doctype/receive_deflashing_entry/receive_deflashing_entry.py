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
    
    print(f"DEBUG: Items to process: {len(items)}")
    for idx, item in enumerate(items[:3]):  # Print first 3 items for debugging
        print(f"DEBUG: Item {idx}: {item}")
    
    # Get the parent document
    try:
        print(f"DEBUG: Getting parent doc: {doc_name}")
        parent_doc = frappe.get_doc("Receive Deflashing Entry", doc_name)
        print(f"DEBUG: Parent doc retrieved, items count: {len(parent_doc.items)}")
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
    
    # Process each item
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
            
            # Check if stock entry already created by looking at stock_entry_reference_return
            if hasattr(child_item, 'stock_entry_reference_return') and child_item.stock_entry_reference_return:
                print(f"DEBUG: Stock entry already exists: {child_item.stock_entry_reference_return}")
                continue
                
            print(f"DEBUG: Child item details - vendor: {child_item.vendor}, product_ref: {child_item.product_ref}")
            
            source_warehouse = 'U1-Transit Store - SPP INDIA'  # Use vendor as source warehouse
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
            
            # Add item to stock entry
            stock_entry.append("items", {
                "item_code": item_data.get("product_ref"),
                "qty": float(item_data.get("received_weight")),  # Convert to float
                "s_warehouse": source_warehouse,
                "t_warehouse": target_warehouse,
                "use_serial_batch_fields": 1,
                "batch_no": item_data.get("batch_no"),
                "spp_batch_number": item_data.get("lot_no"),
                "is_deflashed": 1,
                "status": item_data.get("status")
            })
            
            # Save and submit the stock entry
            print("DEBUG: Inserting stock entry")
            stock_entry.insert()
            print(f"DEBUG: Stock entry inserted with name: {stock_entry.name}")
            
            print("DEBUG: Submitting stock entry")
            stock_entry.submit()
            print("DEBUG: Stock entry submitted")
            
            # Update the child table item with only existing fields
            print("DEBUG: Updating child table item")
            if hasattr(child_item, 'stock_entry_status'):
                child_item.stock_entry_status = "Created"
            
            child_item.stock_entry_reference_return = stock_entry.name
            
            # Add to processed list
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
    
    print(f"DEBUG: Processing complete. Processed items: {len(processed_items)}")
    
    # Update parent document
    if processed_items:
        print(f"DEBUG: Updating parent document with {len(stock_entry_refs)} stock entry references")
        # Update received_stock_entry_ref field with comma-separated list of stock entries
        if stock_entry_refs:
            if parent_doc.received_stock_entry_ref:
                # Append new entries to existing ones
                existing_refs = parent_doc.received_stock_entry_ref.split(',')
                print(f"DEBUG: Existing refs: {len(existing_refs)}")
                all_refs = existing_refs + stock_entry_refs
                parent_doc.received_stock_entry_ref = ','.join(list(set(all_refs)))  # Remove duplicates
            else:
                parent_doc.received_stock_entry_ref = ','.join(stock_entry_refs)
        
        # Check status based on whether all items have stock entries
        all_items_processed = True
        for item in parent_doc.items:
            if not item.stock_entry_reference_return:
                all_items_processed = False
                break
        
        if all_items_processed:
            print("DEBUG: All items processed, setting status to Closed")
            parent_doc.status = "Closed"
        else:
            print("DEBUG: Some items still pending, setting status to Pending")
            parent_doc.status = "Pending"
        
        print("DEBUG: Saving parent document")
        parent_doc.save()
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
    
    # Exclude current document if editing
    if current_doc:
        filters['name'] = ['!=', current_doc]
    
    existing = frappe.get_all('Receive Deflashing Entry', 
                             filters=filters,
                             fields=['name'],
                             limit=1)
    
    if existing:
        return {
            'exists': True,
            'doc_name': existing[0].name
        }
    
    return {
        'exists': False
    }
