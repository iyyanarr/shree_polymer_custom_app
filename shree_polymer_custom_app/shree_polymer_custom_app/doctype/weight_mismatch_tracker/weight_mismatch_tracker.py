# Import required Frappe modules
import frappe
from frappe.model.document import Document

class WeightMismatchTracker(Document):
    def before_insert(self):
        # Check for duplicate Ref Lot Number
        if self.ref_lot_number:
            duplicate_entry = frappe.db.exists("Weight Mismatch Tracker", {"ref_lot_number": self.ref_lot_number})
            if duplicate_entry:
                frappe.throw(f"A Weight Mismatch Tracker entry already exists for Ref Lot Number {self.ref_lot_number}. Duplicates are not allowed.")

        # Fetch Moulding Production Entry based on ref_lot_number
        if self.ref_lot_number:
            moulding_production_entry = frappe.db.get_value(
                "Moulding Production Entry",
                {"scan_lot_number": self.ref_lot_number},
                ["name", "employee","no_of_running_cavities","number_of_lifts"],  # Fetch both name and employee fields
                as_dict=True
            )
            print("**********", moulding_production_entry)

            # If found, set ref_production_entry and entry_person fields
            if moulding_production_entry:
                self.ref_production_entry = moulding_production_entry.get("name")
                self.entry_person = moulding_production_entry.get("employee")
                self.no_of_running_cavities = moulding_production_entry.get("no_of_running_cavities")
                self.number_of_lifts =  moulding_production_entry.get("number_of_lifts")
            else:
                # If no entry is found, throw an error
                frappe.throw(
                    f"No Moulding Production Entry found for Scan Lot Number {self.ref_lot_number}. Please check."
                )

@frappe.whitelist()
def create_stock_reconciliation(document_name, posting_date):
    """
    Create a Stock Reconciliation entry from the fields in the Weight Mismatch Tracker document.
    """

    # Validate required inputs
    if not document_name or not posting_date:
        frappe.throw("Document Name and Posting Date are required to create Stock Reconciliation Entry.")

    # Get the Weight Mismatch Tracker document
    mismatch_doc = frappe.get_doc("Weight Mismatch Tracker", document_name)

    # Validate required fields in the Weight Mismatch Tracker
    if not mismatch_doc.item_code:
        frappe.throw("Item Code is required to create Stock Reconciliation.")
    if not mismatch_doc.warehouse:
        frappe.throw("Warehouse is required to create Stock Reconciliation.")

    # Prepare quantities
    current_qty = mismatch_doc.system_weight if mismatch_doc.system_weight is not None else 0
    approved_qty = mismatch_doc.approved_weight if mismatch_doc.approved_weight is not None else 0

    # Prepare the Stock Reconciliation data
    items = [{
        "item_code": mismatch_doc.item_code,
        "warehouse": mismatch_doc.warehouse,
        "current_qty": current_qty,
        "use_serial_batch_fields": 1,  # Include batch details if needed
        "batch_no": mismatch_doc.batch_number if mismatch_doc.batch_number else None,
        "qty": approved_qty,
    }]

    # Create and insert the Stock Reconciliation entry
    sr_doc = frappe.get_doc({
        "doctype": "Stock Reconciliation",
        "title": f"Reconcile for {mismatch_doc.name}",
        "posting_date": posting_date,
        "purpose": "Stock Reconciliation",
        "company": frappe.defaults.get_user_default("company"),
        "items": items
    })
    sr_doc.insert()
    # Optionally submit the Stock Reconciliation (uncomment if auto-submission is needed)
    sr_doc.submit()

    # Update the Weight Mismatch Tracker with reconciliation reference and status
    mismatch_doc.stock_reconcile_ref = sr_doc.name
    mismatch_doc.status = "Resolved"
    mismatch_doc.save()
    mismatch_doc.submit()

    # Log the operation
    frappe.logger().info(f"Stock Reconciliation {sr_doc.name} created and updated in {document_name}")

    # Return the name of the Stock Reconciliation document
    return sr_doc.name
@frappe.whitelist()
def create_stock_transfer(document_name, item_code, transfer_amount, from_warehouse, batch_no, posting_date,reason_code):
    """
    Create a stock transfer for the Weight Mismatch Tracker based on the Reason Code.
    """

    # Fetch the Weight Mismatch Tracker document
    mismatch_doc = frappe.get_doc("Weight Mismatch Tracker", document_name)


    # Determine the target warehouse based on the Reason Code
    
    if reason_code == "Spillage":
        to_warehouse = "U2-Scrap - SPP INDIA"  # Target warehouse for Spillage
    elif reason_code == "Inspection Entry Wrong":
        to_warehouse = "U2 Rejection - SPP INDIA"  # Target warehouse for Inspection Entry Wrong
    else:
        frappe.throw(f"Unhandled Reason Code: {reason_code}")


    # Create the Stock Entry
    stock_entry = frappe.get_doc({
        "doctype": "Stock Entry",
        "posting_date": posting_date,
        "stock_entry_type": "Material Transfer",
        "items": [
            {
                "item_code": item_code,
                "qty": transfer_amount,
                "use_serial_batch_fields": 1,
                "batch_no": batch_no,
                "s_warehouse": from_warehouse,
                "t_warehouse": to_warehouse,
            }
        ]
    })

    stock_entry.insert()
    stock_entry.submit()

    # Update mismatch document with the Stock Entry reference and status
    mismatch_doc.stock_spillage_ref = stock_entry.name  # Assuming this field exists
    mismatch_doc.status = "Resolved"
    mismatch_doc.save()
    mismatch_doc.submit()

    return stock_entry.name