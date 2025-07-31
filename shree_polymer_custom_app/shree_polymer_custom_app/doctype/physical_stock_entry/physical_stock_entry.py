import frappe
from frappe.model.document import Document

class PhysicalStockEntry(Document):
    pass

WAREHOUSE_MAPPING = {
    'Raw Material': 'Incoming Store - SPP INDIA',
    'Compound': 'U3-Store - SPP INDIA',
    'Compound-Sheeting': 'Sheeting Warehouse - SPP INDIA',
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
    
    # For all other item types, get batch number from stockentry first
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
    
    # Hardcoded warehouse for Compound - Sheeting (handle both with and without spaces)
    if item_group == "Compound - Sheeting" or item_group == "Compound-Sheeting":
        print(f"Found hardcoded warehouse mapping for {item_group}: Sheeting Warehouse - SPP INDIA")
        return "Sheeting Warehouse - SPP INDIA"
    
    # Direct lookup first (exact match)
    if item_group in WAREHOUSE_MAPPING:
        print(f"Found exact warehouse mapping: {WAREHOUSE_MAPPING[item_group]}")
        return WAREHOUSE_MAPPING[item_group]
    
    # If no exact match, check if item_group contains any of the keys
    for key, value in WAREHOUSE_MAPPING.items():
        if key in item_group:
            print(f"Found partial warehouse mapping: {value}")
            return value
            
    print("No warehouse mapping found")
    return None



@frappe.whitelist()
def get_compound_sheeting_stock_info(scan_value, scan_type, item_group):
    """
    Handle stock information retrieval for Compound - Sheeting items
    Args:
        scan_value: The scanned barcode/clip data
        scan_type: 'bin' or 'clip'
        item_group: Should be 'Compound-Sheeting'
    """
    print(f"\n=== Debug: get_compound_sheeting_stock_info ===")
    print(f"Input - Scan Value: {scan_value}, Scan Type: {scan_type}, Item Group: {item_group}")

    if not scan_value or not scan_type or not item_group:
        print("Error: Missing required parameters")
        return {"error": "Scan value, scan type, and item group are required"}
    
    # Hardcode warehouse for Compound - Sheeting
    warehouse = "Sheeting Warehouse - SPP INDIA"
    print(f"Hardcoded Warehouse for {item_group}: {warehouse}")

    # For debugging purposes only retrieve and return the basic data
    debug_info = {
        "scan_value": scan_value,
        "scan_type": scan_type,
        "item_group": item_group,
        "warehouse": warehouse
    }

    if scan_type == 'clip':
        return get_clip_data(scan_value, debug_info, warehouse)
    elif scan_type == 'bin':
        return get_bin_data(scan_value, debug_info, warehouse)
    else:
        return {"error": "Invalid scan type. Must be 'bin' or 'clip'", "debug_info": debug_info}

def handle_clip_scanning(scan_value, warehouse):
    """
    Handle clip scanning logic:
    1. Find in sheeting_clip by barcode_text with scanned data
    2. Get the clip_id
    3. Get item_clip_mapping by sheeting_clip where is_retired is not true
    4. Take spp_batch_number from item_clip_mapping
    5. Get stock entry by spp_batch_number to get batch_no
    6. Get stock info
    """
    print(f"\n=== Debug: handle_clip_scanning ===")
    print(f"Scanning clip with value: {scan_value}")
    
    debug_info = {
        "scan_value": scan_value,
        "warehouse": warehouse,
        "steps": []
    }
    
    try:
        # Step 1: Find in sheeting_clip by barcode_text
        debug_info["steps"].append("Step 1: Finding Sheeting Clip by barcode_text")
        sheeting_clip = frappe.db.get_value(
            'Sheeting Clip',
            {'barcode_text': scan_value},
            ['name', 'clip_name'],
            as_dict=True
        )
        
        debug_info["sheeting_clip_data"] = sheeting_clip
        
        if not sheeting_clip:
            print(f"No sheeting clip found for barcode_text: {scan_value}")
            debug_info["error"] = f"No sheeting clip found for barcode: {scan_value}"
            return {"message": f"No sheeting clip found for barcode: {scan_value}", "debug_info": debug_info}
        
        clip_name = sheeting_clip.get('clip_name')
        sheeting_clip_name = sheeting_clip.get('name')
        print(f"Found sheeting clip: {sheeting_clip_name}, clip_name: {clip_name}")
        
        # Step 2 & 3: Get item_clip_mapping by sheeting_clip where is_retired is not true
        debug_info["steps"].append("Step 2: Finding Item Clip Mapping")
        item_clip_mapping = frappe.db.get_value(
            'Item Clip Mapping',
            {
                'sheeting_clip': sheeting_clip_name,
                'is_retired': ['!=', 1]  # Not retired
            },
            ['spp_batch_number', 'name', 'is_retired'],
            as_dict=True
        )
        
        debug_info["item_clip_mapping_data"] = item_clip_mapping
        
        if not item_clip_mapping:
            print(f"No active item clip mapping found for sheeting clip: {sheeting_clip_name}")
            debug_info["error"] = f"No active item clip mapping found for clip: {clip_name}"
            return {"message": f"No active item clip mapping found for clip: {clip_name}", "debug_info": debug_info}
        
        spp_batch_number = item_clip_mapping.get('spp_batch_number')
        print(f"Found spp_batch_number: {spp_batch_number}")
        
        if not spp_batch_number:
            print("No spp_batch_number found in item clip mapping")
            debug_info["error"] = "No SPP batch number found in item clip mapping"
            return {"message": "No SPP batch number found in item clip mapping", "debug_info": debug_info}
        
        # Step 4: Get stock entry by spp_batch_number to get batch_no
        debug_info["steps"].append("Step 3: Finding Stock Entry Detail by spp_batch_number")
        print(f"Searching for Stock Entry Detail with spp_batch_number: {spp_batch_number}")
        stock_entry_detail = frappe.db.get_value(
            'Stock Entry Detail',
            {'spp_batch_number': spp_batch_number},
            ['batch_no', 'name', 'item_code'],
            as_dict=True
        )
        
        debug_info["stock_entry_detail_data"] = stock_entry_detail
        
        if not stock_entry_detail or not stock_entry_detail.get('batch_no'):
            print(f"No stock entry detail found for spp_batch_number: {spp_batch_number}")
            # Let's also try to find all stock entries with this spp_batch_number for debugging
            all_entries = frappe.db.sql("""
                SELECT name, batch_no, spp_batch_number, item_code
                FROM `tabStock Entry Detail`
                WHERE spp_batch_number = %s
            """, (spp_batch_number,), as_dict=True)
            print(f"All stock entries with spp_batch_number {spp_batch_number}: {all_entries}")
            debug_info["all_stock_entries"] = all_entries
            debug_info["error"] = f"No stock entry found for SPP batch number: {spp_batch_number}"
            return {"message": f"No stock entry found for SPP batch number: {spp_batch_number}", "debug_info": debug_info}
        
        batch_no = stock_entry_detail.get('batch_no')
        print(f"Found batch_no: '{batch_no}' from stock entry detail: {stock_entry_detail.get('name')}")
        
        # Step 5: Get stock info using batch_no
        debug_info["steps"].append("Step 4: Finding Stock Balance by batch_no")
        print(f"Searching for stock balance with batch_no: '{batch_no}' and warehouse: '{warehouse}'")
        
        # First try exact match
        stock_balance = frappe.db.get_value(
            'Item Batch Stock Balance',
            {'batch_no': batch_no, 'warehouse': warehouse},
            ['item_code', 'item_name', 'description', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
            as_dict=True
        )
        
        debug_info["stock_balance_data"] = stock_balance
        
        if not stock_balance:
            print(f"No exact match found. Trying to find similar batch numbers...")
            # Try to find similar batch numbers (in case of slight variations)
            similar_batches = frappe.db.sql("""
                SELECT item_code, item_name, description, warehouse, batch_no, qty, stock_uom
                FROM `tabItem Batch Stock Balance`
                WHERE warehouse = %s 
                AND (batch_no LIKE %s OR batch_no LIKE %s)
                AND qty > 0
                ORDER BY batch_no
            """, (warehouse, f"%{batch_no}%", f"{batch_no}%"), as_dict=True)
            
            print(f"Found {len(similar_batches)} similar batches: {[b.batch_no for b in similar_batches]}")
            debug_info["similar_batches"] = similar_batches
            
            if similar_batches:
                stock_balance = similar_batches[0]  # Use the first match
                print(f"Using similar batch: {stock_balance.batch_no}")
                debug_info["used_similar_batch"] = True
        
        if not stock_balance:
            print(f"No stock balance found for batch: {batch_no}")
            debug_info["error"] = f"No stock balance found for batch: {batch_no}"
            return {"message": f"No stock balance found for batch: {batch_no}", "debug_info": debug_info}
        
        # Add additional clip information to the response
        stock_balance['clip_name'] = clip_name
        stock_balance['sheeting_clip'] = sheeting_clip_name
        stock_balance['spp_batch_number'] = spp_batch_number
        stock_balance['item_group'] = 'Compound-Sheeting'
        stock_balance['debug_info'] = debug_info
        
        print(f"Final stock balance for clip: {stock_balance}")
        return stock_balance
        
    except Exception as e:
        print(f"Error in handle_clip_scanning: {str(e)}")
        frappe.log_error(f"Error in handle_clip_scanning: {str(e)}")
        return {"error": f"Error processing clip scan: {str(e)}"}

def handle_bin_scanning(scan_value, warehouse):
    """
    Handle bin scanning logic - implement based on your bin scanning requirements
    """
    print(f"\n=== Debug: handle_bin_scanning ===")
    print(f"Scanning bin with value: {scan_value}")
    
    # TODO: Implement bin scanning logic based on your requirements
    # This is a placeholder - you'll need to implement the specific logic for bin scanning
    
    try:
        # For now, returning a placeholder response
        # You can implement the specific bin scanning logic here
        return {"message": "Bin scanning logic not yet implemented"}
        
    except Exception as e:
        print(f"Error in handle_bin_scanning: {str(e)}")
        frappe.log_error(f"Error in handle_bin_scanning: {str(e)}")
        return {"error": f"Error processing bin scan: {str(e)}"}

def get_clip_data(scan_value, debug_info, warehouse):
    """
    Retrieve only the Sheeting Clip and Item Clip Mapping data for debugging
    """
    print(f"\n=== Debug: get_clip_data ===")
    # Always use Sheeting Warehouse for Compound - Sheeting regardless of what was passed in
    warehouse = "Sheeting Warehouse - SPP INDIA"
    print(f"Scanning clip with value: {scan_value}, hardcoded warehouse: {warehouse}")
    
    try:
        # Step 1: Find in sheeting_clip by barcode_text
        sheeting_clip = frappe.db.get_value(
            'Sheeting Clip',
            {'barcode_text': scan_value},
            ['name', 'clip_name', 'barcode_text', 'creation', 'modified', 'owner', 'modified_by'],
            as_dict=True
        )
        
        debug_info["sheeting_clip_data"] = sheeting_clip
        
        if not sheeting_clip:
            print(f"No sheeting clip found for barcode_text: {scan_value}")
            debug_info["error"] = f"No sheeting clip found for barcode: {scan_value}"
            return {"message": f"No sheeting clip found for barcode: {scan_value}", "debug_info": debug_info}
        
        clip_name = sheeting_clip.get('clip_name')
        sheeting_clip_name = sheeting_clip.get('name')
        print(f"Found sheeting clip: {sheeting_clip_name}, clip_name: {clip_name}")
        
        # Step 2: Get item_clip_mapping by sheeting_clip
        item_clip_mapping = frappe.db.get_value(
            'Item Clip Mapping',
            {
                'sheeting_clip': sheeting_clip_name,
            },
            ['spp_batch_number', 'name', 'is_retired'],
            as_dict=True
        )
        
        debug_info["item_clip_mapping_data"] = item_clip_mapping
        
        if not item_clip_mapping:
            print(f"No item clip mapping found for sheeting clip: {sheeting_clip_name}")
            return {"message": f"No item clip mapping found for clip: {clip_name}", "debug_info": debug_info}
        
        # Find all item clip mappings for this clip (including retired ones)
        all_mappings = frappe.db.sql("""
            SELECT name, spp_batch_number, is_retired
            FROM `tabItem Clip Mapping`
            WHERE sheeting_clip = %s
            ORDER BY modified DESC
        """, (sheeting_clip_name,), as_dict=True)
        
        debug_info["all_item_clip_mappings"] = all_mappings
        
        # Step 3: Get stock entry by spp_batch_number to get batch_no
        spp_batch_number = item_clip_mapping.get('spp_batch_number')
        print(f"Found spp_batch_number: {spp_batch_number}")
        
        if not spp_batch_number:
            print("No spp_batch_number found in item clip mapping")
            debug_info["error"] = "No SPP batch number found in item clip mapping"
            return {"message": "No SPP batch number found in item clip mapping", "debug_info": debug_info}
        
        print(f"Searching for Stock Entry Detail with spp_batch_number: {spp_batch_number}")
        stock_entry_detail = frappe.db.get_value(
            'Stock Entry Detail',
            {'spp_batch_number': spp_batch_number},
            ['batch_no', 'name', 'item_code', 'item_name', 'stock_uom'],
            as_dict=True
        )
        
        debug_info["stock_entry_detail_data"] = stock_entry_detail
        
        if not stock_entry_detail:
            print(f"No stock entry detail found for spp_batch_number: {spp_batch_number}")
            # Find all stock entries with this spp_batch_number for debugging
            all_entries = frappe.db.sql("""
                SELECT name, batch_no, spp_batch_number, item_code, item_name
                FROM `tabStock Entry Detail`
                WHERE spp_batch_number = %s
                ORDER BY modified DESC
            """, (spp_batch_number,), as_dict=True)
            
            print(f"All stock entries with spp_batch_number {spp_batch_number}: {all_entries}")
            debug_info["all_stock_entries"] = all_entries
            
            if not all_entries:
                debug_info["error"] = f"No stock entry found for SPP batch number: {spp_batch_number}"
                return {"message": f"No stock entry found for SPP batch number: {spp_batch_number}", "debug_info": debug_info}
            
            # Use the first entry if multiple exist
            stock_entry_detail = all_entries[0]
            debug_info["using_alternative_stock_entry"] = True
        
        batch_no = stock_entry_detail.get('batch_no')
        debug_info["batch_no"] = batch_no
        print(f"Found batch_no: {batch_no} from stock entry detail")
        
        # Step 4: Get stock balance information using the batch number
        print(f"Searching for stock balance with batch_no: '{batch_no}' and warehouse: '{warehouse}'")
        
        # Try to get stock balance
        stock_balance = None
        if batch_no and warehouse:
            stock_balance = frappe.db.get_value(
                'Item Batch Stock Balance',
                {'batch_no': batch_no, 'warehouse': warehouse},
                ['item_code', 'item_name', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
                as_dict=True
            )
            
            debug_info["stock_balance_data"] = stock_balance
            
            if not stock_balance:
                print(f"No exact match found. Trying to find similar batch numbers...")
                # Try to find similar batch numbers (in case of slight variations)
                similar_batches = frappe.db.sql("""
                    SELECT item_code, item_name, warehouse, batch_no, qty, stock_uom
                    FROM `tabItem Batch Stock Balance`
                    WHERE warehouse = %s 
                    AND (batch_no LIKE %s OR batch_no LIKE %s)
                    ORDER BY batch_no
                """, (warehouse, f"%{batch_no}%", f"{batch_no}%"), as_dict=True)
                
                debug_info["similar_batches"] = similar_batches
                print(f"Found {len(similar_batches)} similar batches: {[b.batch_no for b in similar_batches]}")
                
                if similar_batches:
                    stock_balance = similar_batches[0]  # Use the first match
                    debug_info["using_similar_batch"] = True
                    print(f"Using similar batch: {stock_balance.batch_no}")
        
        # Return enhanced response with debug info
        response = {
            "clip_name": clip_name,
            "sheeting_clip": sheeting_clip_name,
            "spp_batch_number": spp_batch_number,
            "batch_no": batch_no,
            "item_code": stock_entry_detail.get('item_code'),
            "item_name": stock_entry_detail.get('item_name'),
            "stock_uom": stock_entry_detail.get('stock_uom'),
            "debug_info": debug_info
        }
        
        if stock_balance:
            # Add stock balance information to response
            response["qty"] = stock_balance.get('qty')
            response["warehouse"] = stock_balance.get('warehouse')
            print(f"Found stock balance: {stock_balance.get('qty')} {stock_balance.get('stock_uom')}")
        else:
            response["message"] = f"No stock balance found for batch: {batch_no}"
            print(f"No stock balance found for batch: {batch_no}")
            
        return response
        
    except Exception as e:
        print(f"Error in get_clip_data: {str(e)}")
        frappe.log_error(f"Error in get_clip_data: {str(e)}")
        return {"error": f"Error processing clip scan: {str(e)}", "debug_info": debug_info}

def get_bin_data(scan_value, debug_info, warehouse):
    """
    Retrieve data for a scanned bin
    1. Find the most recent Blanking DC Entry where the bin was used
    2. Get batch and stock information from that entry
    3. Return the relevant stock details
    """
    print(f"\n=== Debug: get_bin_data ===")
    print(f"Scanning bin with value: {scan_value}, warehouse: {warehouse}")
    
    try:
        # Step 1: Find the most recent Blanking DC Entry Item where this bin was used
        print(f"Searching for most recent Blanking DC Entry with bin code: {scan_value}")
        blanking_dc_items = frappe.db.sql("""
            SELECT 
                bdi.name, bdi.bin_code, bdi.asset_name, bdi.batch_no, 
                bdi.spp_batch_number, bdi.scanned_item as item_code, 
                bdi.gross_weight, bdi.net_weight, bdi.available_quantity,
                bdi.sheeting_clip, bdi.mix_barcode, 
                bdc.name as blanking_dc_entry, bdc.posting_date,
                bdc.docstatus
            FROM 
                `tabBlanking DC Item` bdi
            JOIN 
                `tabBlanking DC Entry` bdc ON bdi.parent = bdc.name
            WHERE 
                bdi.bin_code = %s
                AND bdc.docstatus = 1
            ORDER BY 
                bdc.posting_date DESC, bdc.modified DESC
            LIMIT 1
        """, (scan_value,), as_dict=True)
        
        debug_info["blanking_dc_item_data"] = blanking_dc_items[0] if blanking_dc_items else None
        
        if not blanking_dc_items:
            print(f"No Blanking DC Entry found for bin code: {scan_value}")
            debug_info["error"] = f"No Blanking DC Entry found for bin: {scan_value}"
            return {"message": f"No Blanking DC Entry found for bin: {scan_value}", "debug_info": debug_info}
        
        # Get the first (most recent) entry
        blanking_item = blanking_dc_items[0]
        print(f"Found Blanking DC Entry: {blanking_item.blanking_dc_entry}, posted on {blanking_item.posting_date}")
        
        # Step 2: Get item details from the batch
        batch_no = blanking_item.batch_no
        item_code = blanking_item.item_code
        
        if not batch_no or not item_code:
            print(f"Missing batch number or item code in Blanking DC Entry")
            debug_info["error"] = "Missing batch number or item code in Blanking DC Entry"
            return {"message": "Missing batch number or item code in Blanking DC Entry", "debug_info": debug_info}
        
        print(f"Found batch_no: {batch_no}, item_code: {item_code}")
        
        # Step 3: Get item name and other details
        item_details = frappe.db.get_value(
            'Item',
            {'item_code': item_code},
            ['item_name', 'stock_uom'],
            as_dict=True
        )
        
        debug_info["item_details"] = item_details
        
        if not item_details:
            print(f"No item found with item code: {item_code}")
            debug_info["error"] = f"No item found with item code: {item_code}"
            return {"message": f"No item found with item code: {item_code}", "debug_info": debug_info}
        
        # Step 4: Get stock balance information
        print(f"Searching for stock balance with batch_no: '{batch_no}' and warehouse: '{warehouse}'")
        stock_balance = frappe.db.get_value(
            'Item Batch Stock Balance',
            {'batch_no': batch_no, 'warehouse': warehouse},
            ['item_code', 'item_name', 'warehouse', 'batch_no', 'qty', 'stock_uom'],
            as_dict=True
        )
        
        debug_info["stock_balance_data"] = stock_balance
        
        if not stock_balance:
            print(f"No stock balance found for batch: {batch_no}")
            # Try to find similar batch numbers as a fallback
            similar_batches = frappe.db.sql("""
                SELECT item_code, item_name, warehouse, batch_no, qty, stock_uom
                FROM `tabItem Batch Stock Balance`
                WHERE warehouse = %s 
                AND (batch_no LIKE %s OR batch_no LIKE %s)
                ORDER BY batch_no
            """, (warehouse, f"%{batch_no}%", f"{batch_no}%"), as_dict=True)
            
            debug_info["similar_batches"] = similar_batches
            print(f"Found {len(similar_batches)} similar batches: {[b.batch_no for b in similar_batches]}")
            
            if similar_batches:
                stock_balance = similar_batches[0]  # Use the first match
                debug_info["using_similar_batch"] = True
                print(f"Using similar batch: {stock_balance.batch_no}")
        
        # Return enhanced response with all collected information
        response = {
            "bin_code": blanking_item.bin_code,
            "asset_name": blanking_item.asset_name,
            "batch_no": batch_no,
            "spp_batch_number": blanking_item.spp_batch_number,
            "item_code": item_code,
            "item_name": item_details.get('item_name'),
            "stock_uom": item_details.get('stock_uom'),
            "gross_weight": blanking_item.gross_weight,
            "net_weight": blanking_item.net_weight,
            "available_quantity": blanking_item.available_quantity,
            "blanking_dc_entry": blanking_item.blanking_dc_entry,
            "posting_date": blanking_item.posting_date,
            "debug_info": debug_info
        }
        
        if stock_balance:
            # Add stock balance information
            response["qty"] = stock_balance.get('qty')
            response["warehouse"] = stock_balance.get('warehouse')
            print(f"Found stock balance: {stock_balance.get('qty')} {stock_balance.get('stock_uom')}")
        else:
            response["message"] = f"No stock balance found for batch: {batch_no}"
            print(f"No stock balance found for batch: {batch_no}")
            
        return response
        
    except Exception as e:
        print(f"Error in get_bin_data: {str(e)}")
        frappe.log_error(f"Error in get_bin_data: {str(e)}")
        return {"error": f"Error processing bin scan: {str(e)}", "debug_info": debug_info}