# Copyright (c) 2025, Tridotstech and contributors
# For license information, please see license.txt

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
	Backfill qty_in_nos for all existing Deflashing Despatch Entry Item records.
	This patch calculates qty_in_nos based on mould specifications for records created
	before the feature was implemented.
	"""
	print("\n" + "=" * 80)
	if TEST_MODE:
		print(f"⚠️  RUNNING IN TEST MODE - Processing only {TEST_LIMIT} records")
	print("Starting Deflashing Despatch Entry qty_in_nos Backfill")
	print("=" * 80 + "\n")
	
	# Initialize counters
	total_processed = 0
	successfully_calculated = 0
	failed_missing_mould_entry = 0
	failed_missing_mould_spec = 0
	failed_invalid_blank_wt = 0
	failed_other_errors = 0
	
	try:
		# Get all Deflashing Despatch Entry Item records that need backfill
		# Only submitted records (docstatus = 1) where qty_in_nos is 0 or NULL
		# Join with parent to get parent-level ordering
		query = """
			SELECT DISTINCT
				ddei.name, 
				ddei.parent,
				ddei.lot_number, 
				ddei.item, 
				ddei.qty,
				dde.creation as parent_creation
			FROM `tabDeflashing Despatch Entry Item` ddei
			INNER JOIN `tabDeflashing Despatch Entry` dde
				ON dde.name = ddei.parent
			INNER JOIN `tabMoulding Production Entry` mpe 
				ON mpe.scan_lot_number = ddei.lot_number
			WHERE ddei.docstatus = 1 
			  AND (ddei.qty_in_nos = 0 OR ddei.qty_in_nos IS NULL)
			  AND ddei.qty > 0
			  AND mpe.mould_reference IS NOT NULL
			  AND mpe.mould_reference != ''
			ORDER BY dde.creation DESC, ddei.idx ASC
		"""
		
		# Add LIMIT in test mode
		if TEST_MODE:
			query += f" LIMIT {TEST_LIMIT}"
		
		print(f"🔍 Fetching records to process...")
		items_to_update = frappe.db.sql(query, as_dict=1)
		
		total_records = len(items_to_update)
		
		if TEST_MODE:
			print(f"🧪 TEST MODE: Found {total_records} records to process (limited to {TEST_LIMIT})\n")
		else:
			print(f"Found {total_records} records to process\n")
		
		# Process each item
		for idx, item in enumerate(items_to_update, 1):
			total_processed += 1
			
			print(f"\n{'='*80}")
			print(f"Processing Record {idx}/{total_records}")
			print(f"{'='*80}")
			print(f"  📦 Parent Entry: {item.parent}")
			print(f"  🏷️  Lot Number: {item.lot_number}")
			print(f"  📊 Item: {item.item}")
			print(f"  ⚖️  Qty (Kgs): {item.qty}")
			
			try:
				# Step 1: Get Moulding Production Entry for the lot
				print(f"\n  Step 1: Looking for Moulding Production Entry...")
				moulding_entry = frappe.db.get_value(
					"Moulding Production Entry",
					{"scan_lot_number": item.lot_number},
					["mould_reference", "item_to_produce"],
					as_dict=1
				)
				
				if not moulding_entry:
					failed_missing_mould_entry += 1
					print(f"  ❌ FAILED: Moulding Production Entry not found for lot {item.lot_number}")
					continue
				
				if not moulding_entry.mould_reference:
					failed_missing_mould_entry += 1
					print(f"  ❌ FAILED: Mould reference is empty for lot {item.lot_number}")
					continue
				
				print(f"  ✅ Found Moulding Entry")
				print(f"     - Mould Reference: {moulding_entry.mould_reference}")
				print(f"     - Item to Produce: {moulding_entry.item_to_produce}")
				
				# Step 2: Fetch avg_blank_wtproduct_gms AND shell_weight from Mould Specification
				print(f"\n  Step 2: Looking for Mould Specification...")
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
				
				if not mould_spec:
					failed_missing_mould_spec += 1
					print(f"  ❌ FAILED: Mould Specification not found")
					print(f"     - Mould Ref: {moulding_entry.mould_reference}")
					print(f"     - SPP Ref: {moulding_entry.item_to_produce}")
					print(f"     - Status: ACTIVE")
					continue
				
				if not mould_spec.avg_blank_wtproduct_gms:
					failed_missing_mould_spec += 1
					print(f"  ❌ FAILED: avg_blank_wtproduct_gms is empty in Mould Specification")
					continue
				
				print(f"  ✅ Found Mould Specification")
				print(f"     - Avg Blank Weight (gms): {mould_spec.avg_blank_wtproduct_gms}")
				print(f"     - Shell Weight: {mould_spec.shell_weight or 0}")
				
				# Step 3: Calculate total blank weight (avg_blank_wt + shell_weight)
				print(f"\n  Step 3: Calculating total blank weight...")
				try:
					avg_blank_wt = float(str(mould_spec.avg_blank_wtproduct_gms).strip())
					if mould_spec.shell_weight:
						shell_wt = float(mould_spec.shell_weight)
						avg_blank_wt = avg_blank_wt + shell_wt
						print(f"     - Total Blank Weight: {avg_blank_wt}g (avg: {mould_spec.avg_blank_wtproduct_gms}g + shell: {shell_wt}g)")
					else:
						print(f"     - Total Blank Weight: {avg_blank_wt}g (no shell weight)")
				except (ValueError, TypeError) as e:
					failed_invalid_blank_wt += 1
					print(f"  ❌ FAILED: Invalid blank weight value")
					print(f"     - Error: {str(e)}")
					print(f"     - avg_blank_wtproduct_gms: {mould_spec.avg_blank_wtproduct_gms}")
					print(f"     - shell_weight: {mould_spec.shell_weight}")
					continue
				
				if avg_blank_wt <= 0:
					failed_invalid_blank_wt += 1
					print(f"  ❌ FAILED: Blank weight is zero or negative ({avg_blank_wt}g)")
					continue
				
				# Step 4: Calculate qty_in_nos
				print(f"\n  Step 4: Calculating qty_in_nos...")
				# Formula: qty_in_nos = round((qty_in_kgs / avg_blank_wt_gms) * 1000)
				qty_in_nos = round((item.qty / avg_blank_wt) * 1000)
				print(f"     - Formula: ({item.qty} kg / {avg_blank_wt}g) × 1000")
				print(f"     - Result: {qty_in_nos} pieces")
				
				# Step 5: Update the record directly in database (bypass validation for submitted docs)
				print(f"\n  Step 5: Updating database...")
				frappe.db.set_value(
					"Deflashing Despatch Entry Item",
					item.name,
					"qty_in_nos",
					qty_in_nos,
					update_modified=False  # Don't update modified timestamp
				)
				
				successfully_calculated += 1
				print(f"  ✅ SUCCESS: Record updated with qty_in_nos = {qty_in_nos}")
				
			except Exception as e:
				failed_other_errors += 1
				print(f"  ❌ FAILED: Unexpected error - {str(e)}")
				frappe.log_error(
					message=frappe.get_traceback(),
					title=f"Backfill Error - Lot {item.lot_number}"
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
		print(f"❌ Failed - Missing Moulding Entry: {failed_missing_mould_entry}")
		print(f"❌ Failed - Missing Mould Spec: {failed_missing_mould_spec}")
		print(f"❌ Failed - Invalid Blank Weight: {failed_invalid_blank_wt}")
		print(f"❌ Failed - Other Errors: {failed_other_errors}")
		print("=" * 80 + "\n")
		
		# Create a summary document for record keeping
		create_summary_report(
			total_processed,
			successfully_calculated,
			failed_missing_mould_entry,
			failed_missing_mould_spec,
			failed_invalid_blank_wt,
			failed_other_errors
		)
		
	except Exception as e:
		print(f"\n❌ CRITICAL ERROR: {str(e)}")
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Deflashing Despatch Backfill - Critical Error"
		)
		raise

def create_summary_report(total, success, fail_mould_entry, fail_mould_spec, fail_blank_wt, fail_other):
	"""Create a summary report for the backfill operation"""
	try:
		summary = f"""
Deflashing Despatch Entry qty_in_nos Backfill Report
Date: {frappe.utils.now()}

SUMMARY:
========
Total Records Processed: {total}
Successfully Calculated: {success} ({round(success/total*100, 2) if total else 0}%)

FAILURES BREAKDOWN:
===================
Missing Moulding Production Entry: {fail_mould_entry}
Missing Mould Specification: {fail_mould_spec}
Invalid Blank Weight: {fail_blank_wt}
Other Errors: {fail_other}

TOTAL FAILURES: {fail_mould_entry + fail_mould_spec + fail_blank_wt + fail_other}
"""
		
		frappe.log_error(
			message=summary,
			title="Deflashing Despatch Backfill - Summary Report"
		)
		
	except Exception as e:
		frappe.logger().error(f"Error creating summary report: {str(e)}")
