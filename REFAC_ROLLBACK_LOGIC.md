# Documentation: Refactoring Rollback Logic

## Overview
This document summarizes the refactoring of rollback logic across various DocTypes in the `shree_polymer_custom_app`. The primary objective was to replace legacy, raw SQL-based deletion logic with more robust, ERPNext-native practices to ensure data integrity and complete cleanup of linked documents.

## Problem Statement
Various DocTypes implemented custom rollback logic using direct SQL queries like:
```sql
DELETE FROM `tabStock Entry` WHERE name = '...'
DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = '...'
```
These methods are problematic because:
1. They bypass Frappe's lifecycle hooks (e.g., `on_trash`, `after_delete`).
2. They do not clean up linked records like `Serial and Batch Bundle` documents, which were introduced in newer ERPNext versions (v14+).
3. They can lead to orphaned records and stock balance issues.

## Solution
A centralized safe deletion utility was implemented and integrated across the affected DocTypes.

### 1. Centralized Utility: `delete_stock_entry_safely`
Located in `api.py`, this function handles the deletion of `Stock Entry` documents and their dependencies:
- **Linked Bundles:** It identifies and deletes all `Serial and Batch Bundle` records associated with the Stock Entry.
- **ORM Deletion:** It uses `frappe.delete_doc` to perform the deletion, ensuring all standard ERPNext cleanup (like `Stock Ledger Entry` removal) is triggered.

### 2. Refactored DocTypes
The following files were updated to use the new centralized utility and ERPNext ORM methods (`frappe.delete_doc`, `frappe.db.set_value`):

#### **Moulding Production Entry** (`moulding_production_entry.py`)
- Refactored `rollback_entries` and `manual_rollback_entries`.
- Replaced SQL deletions for main and inspection-related Stock Entries.
- Ensured `Work Order` production quantities are correctly reverted via ORM.

#### **Blank Bin Inward Entry** (`blank_bin_inward_entry.py`)
- Refactored `rollback_entries`.
- Replaced raw SQL deletions for multiple stock entry references.

#### **Lot Resource Tagging** (`lot_resource_tagging.py`)
- Refactored `rollback_wo_se_jc`.
- Replaced custom SQL for deleting `Stock Entry`, `Job Card`, and `Work Order`.
- Transitioned to `frappe.delete_doc` for all related documents.

#### **Sub Lot Creation** (`sub_lot_creation.py`)
- Refactored `rollback_entries`.
- Integrated `delete_stock_entry_safely` for handling repack entries.

#### **Material Transfer** (`material_transfer.py`)
- Updated the exception handler in `create_sheeting_stock_entry`.
- Ensured rollbacks use the safe deletion utility if a failure occurs mid-process.

#### **Packing** (`packing.py`)
- Refactored `rollback_entries`.
- Removed a local duplicate implementation of safe deletion in favor of the centralized version.

## Key Benefits
- **Full Cleanup:** Automatically removes `Serial and Batch Bundle` records, preventing "Orphaned Bundle" errors.
- **Hook Execution:** Ensures system-level validations and triggers run correctly.
- **Maintainability:** Consolidation of deletion logic reduces code duplication and future maintenance overhead.
- **Auditability:** Proper document deletion preserves standard Frappe audit logs where applicable.

## Verification Checklist
When testing these changes:
- [ ] Verify that Stock Entries are removed from the system.
- [ ] Verify that associated Stock Ledger Entries (SLE) are removed.
- [ ] Verify that `Serial and Batch Bundle` records (if any) are deleted.
- [ ] Verify that stock levels correctly revert to their previous state.
