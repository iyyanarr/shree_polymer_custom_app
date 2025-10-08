import frappe
from frappe.utils import flt

# ====== TEST MODE CONFIGURATION ======
# Set to True to test with limited records first
# Set to False to run full backfill on all records
TEST_MODE = False
TEST_LIMIT = 10  # Number of records to process in test mode
# ====================================

def execute():
	"""
	Backfill all calculated fields for existing Deflashing Receipt Entry records.
	
	This patch calculates the following fields for records created before the feature was implemented:
	- product_wt_from_uom: Weight per piece from UOM conversion
	- qty_in_nos: Received quantity in numbers
	- blank_wt: Blank weight from Mould Specification (including shell weight)
	- qty_despatched_nos: Despatched quantity in numbers
	- qty_received_nos: Same as qty_in_nos
	- difference_nos: Difference between received and despatched
	- scrap_expected_per_piece_gms: Expected scrap per piece
	- total_scrap_expected_kg: Total expected scrap
	- actual_scrap_kg: Actual scrap from scrap_weight
	- scrap_difference_kg: Difference between actual and expected scrap
	"""
	print("\n" + "=" * 80)
	if TEST_MODE:
		print(f"⚠️  RUNNING IN TEST MODE - Processing only {TEST_LIMIT} records")
	print("Starting Deflashing Receipt Entry Fields Backfill")
	print("=" * 80 + "\n")
	
	# Initialize counters
	total_processed = 0
	successfully_calculated = 0
	failed_no_bom = 0
	failed_no_uom = 0
	failed_no_mould_entry = 0
	failed_no_mould_spec = 0
	failed_other_errors = 0
	
	try:
		# Get all Deflashing Receipt Entry records that need backfill
		query = """
			SELECT 
				name,
				lot_number,
				scan_lot_number,
				item,
				product_weight,
				qty,
				scrap_weight
			FROM `tabDeflashing Receipt Entry`
			WHERE docstatus = 1
			  AND (
			      qty_in_nos IS NULL OR qty_in_nos = 0 
			      OR product_wt_from_uom IS NULL OR product_wt_from_uom = 0
			      OR blank_wt IS NULL OR blank_wt = 0
			  )
			  AND product_weight > 0
			ORDER BY creation DESC
		"""
		
		# Add LIMIT in test mode
		if TEST_MODE:
			query += f" LIMIT {TEST_LIMIT}"
		
		print(f"🔍 Fetching records to process...")
		records_to_update = frappe.db.sql(query, as_dict=1)
		
		total_records = len(records_to_update)
		
		if TEST_MODE:
			print(f"🧪 TEST MODE: Found {total_records} records to process (limited to {TEST_LIMIT})\n")
		else:
			print(f"Found {total_records} records to process\n")
		
		# Process each record
		for idx, record in enumerate(records_to_update, 1):
			total_processed += 1
			
			print(f"\n{'='*80}")
			print(f"Processing Record {idx}/{total_records}")
			print(f"{'='*80}")
			print(f"  📄 Entry: {record.name}")
			print(f"  🏷️  Lot Number: {record.lot_number}")
			print(f"  📦 Item: {record.item}")
			print(f"  ⚖️  Product Weight: {record.product_weight} kg")
			print(f"  📊 Qty (Despatched): {record.qty} kg")
			print(f"  🗑️  Scrap Weight: {record.scrap_weight or 0} kg")
			
			try:
				# STEP 1: Find BOM to get produced item
				print(f"\n  Step 1: Looking for BOM...")
				bom = frappe.db.sql("""
					SELECT B.item, B.name
					FROM `tabBOM Item` BI 
					INNER JOIN `tabBOM` B ON BI.parent = B.name 
					WHERE BI.item_code = %(item_code)s 
					AND B.is_active = 1 
					AND B.is_default = 1
				""", {"item_code": record.item}, as_dict=1)
				
				if not bom or not bom[0].item:
					failed_no_bom += 1
					print(f"  ❌ FAILED: BOM not found for item {record.item}")
					continue
				
				produced_item = bom[0].item
				print(f"  ✅ Found BOM: {bom[0].name}")
				print(f"     - Produced Item: {produced_item}")
				
				# STEP 2: Get UOM conversion factor
				print(f"\n  Step 2: Looking for UOM Conversion...")
				conversion_detail = frappe.db.get_value(
					"UOM Conversion Detail",
					{"parent": produced_item, "uom": "Kg"},
					"conversion_factor"
				)
				
				if not conversion_detail:
					failed_no_uom += 1
					print(f"  ❌ FAILED: UOM conversion factor not found for {produced_item}")
					continue
				
				print(f"  ✅ Found UOM Conversion Factor: {conversion_detail}")
				
				# STEP 3: Calculate product_wt_from_uom (weight per piece in grams)
				print(f"\n  Step 3: Calculating product weight from UOM...")
				# Formula: product_wt_from_uom = round(1000 / conversion_factor, 3)
				product_wt_from_uom = round(1000 / conversion_detail, 3)
				print(f"     - Formula: 1000 / {conversion_detail} = {product_wt_from_uom}g per piece")
				
				# STEP 4: Calculate qty_in_nos (received quantity)
				print(f"\n  Step 4: Calculating qty in nos (received)...")
				# Formula: qty_in_nos = round((product_weight / product_wt_from_uom) × 1000)
				if product_wt_from_uom > 0:
					qty_in_nos = round((record.product_weight / product_wt_from_uom) * 1000)
					print(f"     - Formula: ({record.product_weight} / {product_wt_from_uom}) × 1000 = {qty_in_nos} pieces")
				else:
					qty_in_nos = 0
					print(f"  ⚠️  Warning: product_wt_from_uom is 0, setting qty_in_nos to 0")
				
				# STEP 5: Fetch Blank Weight from Mould Specification
				print(f"\n  Step 5: Looking for Mould Specification...")
				lot_to_search = record.scan_lot_number or record.lot_number
				
				moulding_entry = frappe.db.get_value(
					"Moulding Production Entry", 
					{"scan_lot_number": lot_to_search}, 
					["mould_reference", "item_to_produce"], 
					as_dict=1
				)
				
				if not moulding_entry or not moulding_entry.mould_reference:
					failed_no_mould_entry += 1
					print(f"  ❌ FAILED: Moulding Production Entry not found for lot {lot_to_search}")
					continue
				
				print(f"  ✅ Found Moulding Entry")
				print(f"     - Mould Reference: {moulding_entry.mould_reference}")
				print(f"     - Item to Produce: {moulding_entry.item_to_produce}")
				
				# Fetch avg_blank_wtproduct_gms AND shell_weight from Mould Specification
				mould_spec = frappe.db.get_value(
					"Mould Specification", 
					{
						"mould_ref": moulding_entry.mould_reference, 
						"spp_ref": moulding_entry.item_to_produce, 
						"mould_status": "ACTIVE"
					}, 
					["avg_blank_wtproduct_gms", "shell_weight"],
					as_dict=True
				)
				
				if not mould_spec or not mould_spec.avg_blank_wtproduct_gms:
					failed_no_mould_spec += 1
					print(f"  ❌ FAILED: Mould Specification not found")
					print(f"     - Mould Ref: {moulding_entry.mould_reference}")
					print(f"     - SPP Ref: {moulding_entry.item_to_produce}")
					continue
				
				print(f"  ✅ Found Mould Specification")
				print(f"     - Avg Blank Weight: {mould_spec.avg_blank_wtproduct_gms}g")
				print(f"     - Shell Weight: {mould_spec.shell_weight or 0}g")
				
				# STEP 6: Calculate total blank weight (including shell weight)
				print(f"\n  Step 6: Calculating total blank weight...")
				try:
					blank_wt = float(str(mould_spec.avg_blank_wtproduct_gms).strip())
					if mould_spec.shell_weight:
						shell_wt = float(mould_spec.shell_weight)
						blank_wt = blank_wt + shell_wt
						print(f"     - Total: {blank_wt}g (avg: {mould_spec.avg_blank_wtproduct_gms}g + shell: {shell_wt}g)")
					else:
						print(f"     - Total: {blank_wt}g (no shell weight)")
				except (ValueError, TypeError) as e:
					failed_other_errors += 1
					print(f"  ❌ FAILED: Invalid blank weight value - {str(e)}")
					continue
				
				# STEP 7: Calculate qty_despatched_nos
				print(f"\n  Step 7: Calculating qty despatched nos...")
				# Formula: qty_despatched_nos = round((qty / blank_wt) × 1000)
				if blank_wt > 0 and record.qty:
					qty_despatched_nos = round((record.qty / blank_wt) * 1000)
					print(f"     - Formula: ({record.qty} / {blank_wt}) × 1000 = {qty_despatched_nos} pieces")
				else:
					qty_despatched_nos = 0
					print(f"  ⚠️  Warning: blank_wt or qty is 0, setting qty_despatched_nos to 0")
				
				# STEP 8: Calculate quantity differences
				print(f"\n  Step 8: Calculating quantity differences...")
				qty_received_nos = qty_in_nos
				difference_nos = qty_received_nos - qty_despatched_nos
				print(f"     - Received: {qty_received_nos} pieces")
				print(f"     - Despatched: {qty_despatched_nos} pieces")
				print(f"     - Difference: {difference_nos} pieces")
				
				# STEP 9: Calculate scrap tracking fields
				print(f"\n  Step 9: Calculating scrap tracking...")
				
				# Scrap Expected per Piece = Blank Weight - Product Weight from UOM
				scrap_expected_per_piece_gms = round(blank_wt - product_wt_from_uom, 3)
				print(f"     - Scrap per piece: {scrap_expected_per_piece_gms}g = {blank_wt}g - {product_wt_from_uom}g")
				
				# Total Scrap Expected = (scrap_per_piece × qty_despatched) / 1000
				if scrap_expected_per_piece_gms and qty_despatched_nos:
					total_scrap_expected_kg = round((scrap_expected_per_piece_gms * qty_despatched_nos) / 1000, 3)
					print(f"     - Total expected: {total_scrap_expected_kg}kg = ({scrap_expected_per_piece_gms}g × {qty_despatched_nos}) / 1000")
				else:
					total_scrap_expected_kg = 0
					print(f"     - Total expected: 0kg (no scrap data)")
				
				# Actual Scrap
				actual_scrap_kg = record.scrap_weight or 0
				print(f"     - Actual scrap: {actual_scrap_kg}kg")
				
				# Scrap Difference = Actual - Expected
				scrap_difference_kg = round(actual_scrap_kg - total_scrap_expected_kg, 3)
				print(f"     - Scrap difference: {scrap_difference_kg}kg")
				
				# STEP 10: Update the record in database
				print(f"\n  Step 10: Updating database...")
				frappe.db.sql("""
					UPDATE `tabDeflashing Receipt Entry`
					SET 
						product_wt_from_uom = %(product_wt_from_uom)s,
						qty_in_nos = %(qty_in_nos)s,
						blank_wt = %(blank_wt)s,
						qty_despatched_nos = %(qty_despatched_nos)s,
						qty_received_nos = %(qty_received_nos)s,
						difference_nos = %(difference_nos)s,
						scrap_expected_per_piece_gms = %(scrap_expected_per_piece_gms)s,
						total_scrap_expected_kg = %(total_scrap_expected_kg)s,
						actual_scrap_kg = %(actual_scrap_kg)s,
						scrap_difference_kg = %(scrap_difference_kg)s
					WHERE name = %(name)s
				""", {
					"name": record.name,
					"product_wt_from_uom": product_wt_from_uom,
					"qty_in_nos": qty_in_nos,
					"blank_wt": blank_wt,
					"qty_despatched_nos": qty_despatched_nos,
					"qty_received_nos": qty_received_nos,
					"difference_nos": difference_nos,
					"scrap_expected_per_piece_gms": scrap_expected_per_piece_gms,
					"total_scrap_expected_kg": total_scrap_expected_kg,
					"actual_scrap_kg": actual_scrap_kg,
					"scrap_difference_kg": scrap_difference_kg
				})
				
				successfully_calculated += 1
				print(f"  ✅ SUCCESS: Record updated with all calculated fields")
				
			except Exception as e:
				failed_other_errors += 1
				print(f"  ❌ FAILED: Unexpected error - {str(e)}")
				frappe.log_error(
					message=frappe.get_traceback(),
					title=f"Backfill Error - Receipt {record.name}"
				)
		
		# Final commit
		frappe.db.commit()
		print(f"\n✅ Database committed successfully")
		
		# Print summary
		print("\n" + "=" * 80)
		print("BACKFILL SUMMARY")
		print("=" * 80)
		print(f"Total Records Processed: {total_processed}")
		print(f"✅ Successfully Calculated: {successfully_calculated} ({round(successfully_calculated/total_processed*100, 2) if total_processed else 0}%)")
		print(f"❌ Failed - No BOM Found: {failed_no_bom}")
		print(f"❌ Failed - No UOM Conversion: {failed_no_uom}")
		print(f"❌ Failed - No Moulding Entry: {failed_no_mould_entry}")
		print(f"❌ Failed - No Mould Spec: {failed_no_mould_spec}")
		print(f"❌ Failed - Other Errors: {failed_other_errors}")
		print("=" * 80 + "\n")
		
	except Exception as e:
		print(f"\n❌ CRITICAL ERROR: {str(e)}")
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Deflashing Receipt Entry Backfill - Critical Error"
		)
		raise
