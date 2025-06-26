"""
Custom Role Permissions Management
This module handles the restoration of custom role permissions for core ERPNext doctypes
after migrations that reset permissions.
"""

import frappe
from frappe import _


def restore_batch_permissions():
    """
    Restore custom role permissions for Batch doctype after migrations
    """
    try:
        # Define your custom role permissions for Batch doctype
        # Based on your current Custom DocPerm entries
        custom_batch_permissions = [
            {
                "role": "Item Manager",
                "doctype": "Batch",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "submit": 0,
                "cancel": 0,
                "amend": 0,
                "report": 1,
                "export": 1,
                "import": 0,
                "set_user_permissions": 0,
                "share": 1,
                "print": 1,
                "email": 1,
                "if_owner": 0
            },
            {
                "role": "Purchase User",
                "doctype": "Batch",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 0,
                "submit": 0,
                "cancel": 0,
                "amend": 0,
                "report": 0,
                "export": 1,
                "import": 0,
                "set_user_permissions": 0,
                "share": 0,
                "print": 0,
                "email": 0,
                "if_owner": 0
            },
            {
                "role": "All",
                "doctype": "Batch",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 0,  # No delete permission for safety
                "submit": 0,
                "cancel": 0,
                "amend": 0,
                "report": 1,
                "export": 1,
                "import": 1,  # This field exists as "import"
                "share": 1,
                "print": 1,
                "email": 1,
                "if_owner": 0
            }
            # Add more custom roles if needed - you have these available:
            # Batch Operator, Blanker, Compound Inspector, Delivery Manager, Despatcher
            # Uncomment and configure as needed:
            # ,{
            #     "role": "Batch Operator",
            #     "doctype": "Batch", 
            #     "read": 1,
            #     "write": 1,
            #     "create": 1,
            #     "delete": 0,
            #     "submit": 0,
            #     "cancel": 0,
            #     "amend": 0,
            #     "report": 1,
            #     "export": 1,
            #     "import": 0,
            #     "set_user_permissions": 0,
            #     "share": 1,
            #     "print": 1,
            #     "email": 0,
            #     "if_owner": 0
            # }
        ]
        
        for perm in custom_batch_permissions:
            # Check if permission already exists
            existing = frappe.db.exists("Custom DocPerm", {
                "parent": perm["doctype"],
                "role": perm["role"]
            })
            
            if not existing:
                # Create new custom permission
                doc = frappe.new_doc("Custom DocPerm")
                
                # Set required fields for Custom DocPerm
                doc.parent = perm["doctype"]
                doc.role = perm["role"]
                doc.read = perm.get("read", 0)
                doc.write = perm.get("write", 0)
                doc.create = perm.get("create", 0)
                doc.delete = perm.get("delete", 0)
                doc.submit = perm.get("submit", 0)
                doc.cancel = perm.get("cancel", 0)
                doc.amend = perm.get("amend", 0)
                doc.report = perm.get("report", 0)
                doc.export = perm.get("export", 0)
                setattr(doc, "import", perm.get("import", 0))  # Use setattr for reserved keyword
                doc.share = perm.get("share", 0)
                doc.print = perm.get("print", 0)
                doc.email = perm.get("email", 0)
                doc.if_owner = perm.get("if_owner", 0)
                doc.permlevel = perm.get("permlevel", 0)
                
                doc.insert(ignore_permissions=True)
                frappe.logger().info(f"Created custom permission for role {perm['role']} on {perm['doctype']}")
            else:
                # Update existing permission
                doc = frappe.get_doc("Custom DocPerm", existing)
                
                # Update fields
                doc.read = perm.get("read", 0)
                doc.write = perm.get("write", 0)
                doc.create = perm.get("create", 0)
                doc.delete = perm.get("delete", 0)
                doc.submit = perm.get("submit", 0)
                doc.cancel = perm.get("cancel", 0)
                doc.amend = perm.get("amend", 0)
                doc.report = perm.get("report", 0)
                doc.export = perm.get("export", 0)
                setattr(doc, "import", perm.get("import", 0))  # Use setattr for reserved keyword
                doc.share = perm.get("share", 0)
                doc.print = perm.get("print", 0)
                doc.email = perm.get("email", 0)
                doc.if_owner = perm.get("if_owner", 0)
                doc.permlevel = perm.get("permlevel", 0)
                
                doc.save(ignore_permissions=True)
                frappe.logger().info(f"Updated custom permission for role {perm['role']} on {perm['doctype']}")
        
        # Clear cache to apply changes
        frappe.clear_cache(doctype="Batch")
        frappe.db.commit()
        
    except Exception as e:
        frappe.logger().error(f"Error restoring batch permissions: {str(e)}")
        raise


def restore_employee_permissions():
    """
    Restore custom role permissions for Employee doctype after migrations
    """
    try:
        # Define your custom role permissions for Employee doctype
        custom_employee_permissions = [
            {
                "role": "Blanker",
                "doctype": "Employee",
                "read": 1,
                "write": 0,
                "create": 0,
                "delete": 0,
                "submit": 0,
                "cancel": 0,
                "amend": 0,
                "report": 1,
                "export": 1,
                "import": 0,
                "set_user_permissions": 0,
                "share": 0,
                "print": 1,
                "email": 0,
                "if_owner": 0
            }
            # Add more roles for Employee if needed
        ]
        
        for perm in custom_employee_permissions:
            # Check if permission already exists
            existing = frappe.db.exists("Custom DocPerm", {
                "parent": perm["doctype"],
                "role": perm["role"]
            })
            
            if not existing:
                # Create new custom permission
                doc = frappe.new_doc("Custom DocPerm")
                
                # Set required fields for Custom DocPerm
                doc.parent = perm["doctype"]
                doc.role = perm["role"]
                doc.read = perm.get("read", 0)
                doc.write = perm.get("write", 0)
                doc.create = perm.get("create", 0)
                doc.delete = perm.get("delete", 0)
                doc.submit = perm.get("submit", 0)
                doc.cancel = perm.get("cancel", 0)
                doc.amend = perm.get("amend", 0)
                doc.report = perm.get("report", 0)
                doc.export = perm.get("export", 0)
                setattr(doc, "import", perm.get("import", 0))  # Use setattr for reserved keyword
                doc.share = perm.get("share", 0)
                doc.print = perm.get("print", 0)
                doc.email = perm.get("email", 0)
                doc.if_owner = perm.get("if_owner", 0)
                doc.permlevel = perm.get("permlevel", 0)
                
                doc.insert(ignore_permissions=True)
                frappe.logger().info(f"Created custom permission for role {perm['role']} on {perm['doctype']}")
            else:
                # Update existing permission
                doc = frappe.get_doc("Custom DocPerm", existing)
                
                # Update fields
                doc.read = perm.get("read", 0)
                doc.write = perm.get("write", 0)
                doc.create = perm.get("create", 0)
                doc.delete = perm.get("delete", 0)
                doc.submit = perm.get("submit", 0)
                doc.cancel = perm.get("cancel", 0)
                doc.amend = perm.get("amend", 0)
                doc.report = perm.get("report", 0)
                doc.export = perm.get("export", 0)
                setattr(doc, "import", perm.get("import", 0))  # Use setattr for reserved keyword
                doc.share = perm.get("share", 0)
                doc.print = perm.get("print", 0)
                doc.email = perm.get("email", 0)
                doc.if_owner = perm.get("if_owner", 0)
                doc.permlevel = perm.get("permlevel", 0)
                
                doc.save(ignore_permissions=True)
                frappe.logger().info(f"Updated custom permission for role {perm['role']} on {perm['doctype']}")
        
        # Clear cache to apply changes
        frappe.clear_cache(doctype="Employee")
        frappe.db.commit()
        
    except Exception as e:
        frappe.logger().error(f"Error restoring employee permissions: {str(e)}")
        raise


def restore_all_custom_permissions():
    """
    Restore all custom permissions after migration
    """
    try:
        # Restore Batch permissions
        restore_batch_permissions()
        
        # Restore Employee permissions
        restore_employee_permissions()
        
        # Add other doctype permission restoration here if needed
        # restore_other_doctype_permissions()
        
        frappe.logger().info("Successfully restored all custom permissions")
        
    except Exception as e:
        frappe.logger().error(f"Error in restore_all_custom_permissions: {str(e)}")
        raise


def export_custom_permissions_to_fixtures():
    """
    Export current custom permissions to fixtures for backup
    This function can be run manually to backup current permissions
    """
    try:
        # Get all custom permissions for core doctypes
        custom_perms = frappe.get_all("Custom DocPerm", 
            filters={"parent": ["in", ["Batch", "Employee"]]},  # Add other doctypes as needed
            fields=["name", "parent", "role", "read", "write", "create", "delete", 
                   "submit", "cancel", "amend", "report", "export", "import", 
                   "set_user_permissions", "share", "print", "email", "if_owner"]
        )
        
        if custom_perms:
            # Save to fixtures file
            import json
            fixtures_path = frappe.get_app_path("shree_polymer_custom_app", "shree_polymer_custom_app", "fixtures", "custom_docperm.json")
            
            with open(fixtures_path, 'w') as f:
                json.dump(custom_perms, f, indent=4, default=str)
            
            frappe.logger().info(f"Exported {len(custom_perms)} custom permissions to fixtures")
            return custom_perms
        
    except Exception as e:
        frappe.logger().error(f"Error exporting custom permissions: {str(e)}")
        raise
