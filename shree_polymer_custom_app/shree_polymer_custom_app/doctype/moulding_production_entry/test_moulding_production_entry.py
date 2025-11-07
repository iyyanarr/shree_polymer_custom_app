# Copyright (c) 2023, Tridotstech and Contributors
# See license.txt

# import frappe
import unittest

class TestMouldingProductionEntry(unittest.TestCase):
	"""
	Test cases for Moulding Production Entry - NEW FLOW (Single-Stage Submission)
	
	MIGRATION NOTES:
	================
	OLD FLOW (Two-Stage):
	1. Moulding Production Entry on_submit() → Creates DRAFT Stock Entry
	2. Wait for Line Inspection + Lot Inspection to complete
	3. Lot Inspection triggers submit_moulding_entry()
	4. manual_on_submit() submits Stock Entry + updates inspections
	
	NEW FLOW (Single-Stage):
	1. Moulding Production Entry on_submit() → Creates AND SUBMITS Stock Entry immediately
	2. Job Card and Work Order completed immediately
	3. Batch number (T12345) exists in database immediately
	4. Inspections query existing batch number independently
	5. No cross-doctype triggering
	
	CHANGES REQUIRED:
	=================
	File 1: moulding_production_entry.py
	--------------------------------------
	A. In make_stock_entry() function (Line 556):
	   - After stock_entry.insert(), add immediate submission
	   - Move Job Card and Work Order completion here
	   - Remove dependency on manual_on_submit()
	
	B. In manual_on_submit() function (Line 143):
	   - Mark as DEPRECATED
	   - Add warning log if called
	   - Eventually remove entirely
	
	File 2: inspection_entry.py
	----------------------------
	A. In on_submit() method:
	   - Remove call to self.submit_moulding_entry()
	   - Add logic to get batch from existing Moulding Production Stock Entry
	   - Update inspection stock entries with batch independently
	
	B. submit_moulding_entry() function:
	   - Mark as DEPRECATED
	   - Eventually remove entirely
	
	BENEFITS:
	=========
	1. Stock recorded immediately when production happens ✅
	2. No hidden cross-doctype triggers ✅
	3. Inspections work independently ✅
	4. Simpler workflow - easier to debug ✅
	5. Accurate inventory reporting (correct dates) ✅
	
	BATCH NUMBER AVAILABILITY:
	==========================
	After Moulding Production Entry is submitted:
	
	Query to get batch number:
	--------------------------
	mould_prod = frappe.get_doc("Moulding Production Entry", 
	    {"scan_lot_number": lot_number})
	
	if mould_prod.stock_entry_reference:
	    stock_entry = frappe.get_doc("Stock Entry", mould_prod.stock_entry_reference)
	    
	    # Get batch from finished goods item
	    for item in stock_entry.items:
	        if item.t_warehouse and item.is_finished_item:
	            target_batch = item.batch_no  # e.g., "T12345"
	            break
	
	OR using direct SQL:
	-------------------
	target_batch = frappe.db.sql('''
	    SELECT sed.batch_no 
	    FROM `tabStock Entry Detail` sed
	    INNER JOIN `tabStock Entry` se ON se.name = sed.parent
	    INNER JOIN `tabMoulding Production Entry` mpe ON mpe.stock_entry_reference = se.name
	    WHERE mpe.scan_lot_number = %s
	    AND sed.is_finished_item = 1
	    AND sed.t_warehouse IS NOT NULL
	    LIMIT 1
	''', (lot_number,), as_dict=1)
	
	if target_batch:
	    batch_no = target_batch[0].batch_no
	
	INSPECTION ENTRY UPDATES:
	=========================
	When Inspection Entry submits:
	
	1. Get batch from Moulding Production (already exists)
	2. Create rejection Stock Entry with existing batch
	3. Submit rejection Stock Entry immediately
	4. No need to trigger Moulding Production updates
	
	Example:
	-------
	def on_submit(self):
	    # Get existing batch
	    batch_no = self.get_batch_from_moulding_production()
	    
	    # Create rejection stock entry if needed
	    if self.rejected_qty > 0 and batch_no:
	        rejection_ste = self.create_rejection_stock_entry(batch_no)
	        rejection_ste.submit()  # Submit immediately
	    
	    # Update self with batch info
	    self.batch_no = batch_no
	    self.spp_batch_number = self.lot_no
	    
	    # ❌ REMOVED: self.submit_moulding_entry()
	
	def get_batch_from_moulding_production(self):
	    mould_prod = frappe.db.get_value(
	        "Moulding Production Entry",
	        {"scan_lot_number": self.lot_no},
	        ["stock_entry_reference"],
	        as_dict=1
	    )
	    
	    if not mould_prod or not mould_prod.stock_entry_reference:
	        frappe.throw("Moulding Production Entry not found or Stock Entry not created")
	    
	    # Get batch from stock entry
	    batch_info = frappe.db.get_value(
	        "Stock Entry Detail",
	        {
	            "parent": mould_prod.stock_entry_reference,
	            "is_finished_item": 1,
	            "t_warehouse": ["is", "set"]
	        },
	        "batch_no"
	    )
	    
	    return batch_info
	
	TESTING CHECKLIST:
	==================
	[ ] 1. Create Moulding Production Entry
	[ ] 2. Verify Stock Entry is submitted immediately (docstatus = 1)
	[ ] 3. Verify Batch number exists (T{lot_number})
	[ ] 4. Verify Job Card status = "Completed"
	[ ] 5. Verify Work Order status = "Completed"
	[ ] 6. Verify Item Bin Mapping updated
	[ ] 7. Create Line Inspection with rejections
	[ ] 8. Verify Line Inspection can get batch number
	[ ] 9. Verify Line Inspection rejection Stock Entry created with correct batch
	[ ] 10. Verify Line Inspection submission does NOT trigger Moulding Production
	[ ] 11. Create Lot Inspection with rejections
	[ ] 12. Verify Lot Inspection can get batch number
	[ ] 13. Verify Lot Inspection rejection Stock Entry created with correct batch
	[ ] 14. Verify Lot Inspection submission does NOT trigger Moulding Production
	[ ] 15. Verify total inventory: Production - Line Rejection - Lot Rejection = Final Stock
	[ ] 16. Verify no DRAFT Stock Entries exist in system
	
	ROLLBACK PLAN:
	==============
	If issues found after deployment:
	
	1. Revert code changes in moulding_production_entry.py
	2. Revert code changes in inspection_entry.py
	3. Run SQL to find any stuck draft stock entries:
	   
	   SELECT name, blanking_dc_no, docstatus 
	   FROM `tabStock Entry` 
	   WHERE blanking_dc_no LIKE 'MLDPE%' 
	   AND docstatus = 0
	
	4. Manually submit or cancel stuck entries
	5. Redeploy old code
	
	DATABASE CLEANUP AFTER MIGRATION:
	==================================
	After confirming new flow works:
	
	1. Check for orphaned draft stock entries:
	   
	   SELECT se.name, se.blanking_dc_no, se.creation, se.docstatus
	   FROM `tabStock Entry` se
	   LEFT JOIN `tabMoulding Production Entry` mpe ON mpe.stock_entry_reference = se.name
	   WHERE se.blanking_dc_no LIKE 'MLDPE%'
	   AND se.docstatus = 0
	   AND mpe.name IS NULL
	
	2. Archive or delete test entries created during migration
	
	3. Verify all recent Moulding Production entries have submitted stock entries:
	   
	   SELECT mpe.name, mpe.scan_lot_number, mpe.stock_entry_reference, 
	          se.docstatus as stock_entry_status
	   FROM `tabMoulding Production Entry` mpe
	   LEFT JOIN `tabStock Entry` se ON se.name = mpe.stock_entry_reference
	   WHERE mpe.creation >= '2025-01-01'
	   AND (se.docstatus != 1 OR se.name IS NULL)
	
	PERFORMANCE CONSIDERATIONS:
	===========================
	1. Submitting Stock Entry immediately adds ~2-3 seconds to submission time
	2. No performance impact on Inspection Entry (same query complexity)
	3. Reduced database load (no waiting for triggers, immediate cleanup)
	4. Better for concurrent users (no race conditions between inspections)
	"""
	pass

	def test_stock_entry_submitted_immediately(self):
		"""
		Test that Stock Entry is submitted immediately when Moulding Production Entry is submitted.
		No longer waits for inspections.
		"""
		# TODO: Implement test after migration
		pass

	def test_batch_number_available_after_submission(self):
		"""
		Test that batch number (T{lot_number}) is available in database
		immediately after Moulding Production Entry submission.
		"""
		# TODO: Implement test after migration
		pass

	def test_inspection_can_get_batch_independently(self):
		"""
		Test that Inspection Entry can query and get the batch number
		from Moulding Production Entry without triggering any updates.
		"""
		# TODO: Implement test after migration
		pass

	def test_no_cross_doctype_triggers(self):
		"""
		Test that submitting Inspection Entry does NOT trigger
		any updates to Moulding Production Entry or its Stock Entry.
		"""
		# TODO: Implement test after migration
		pass

	def test_job_card_completed_immediately(self):
		"""
		Test that Job Card status changes to "Completed" immediately
		when Moulding Production Entry is submitted.
		"""
		# TODO: Implement test after migration
		pass

	def test_work_order_completed_immediately(self):
		"""
		Test that Work Order status changes to "Completed" immediately
		when Moulding Production Entry is submitted.
		"""
		# TODO: Implement test after migration
		pass
