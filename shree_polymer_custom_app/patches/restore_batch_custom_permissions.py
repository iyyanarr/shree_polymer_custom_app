"""
Patch to restore custom role permissions for Batch doctype
This patch runs after ERPNext migration to restore custom permissions
"""

import frappe
from shree_polymer_custom_app.custom_role_permissions import restore_all_custom_permissions


def execute():
    """
    Execute the patch to restore custom permissions
    """
    try:
        frappe.logger().info("Starting patch to restore custom role permissions...")
        restore_all_custom_permissions()
        frappe.logger().info("Patch completed successfully - custom role permissions restored")
    except Exception as e:
        frappe.logger().error(f"Patch failed: {str(e)}")
        # Don't raise the exception to prevent migration failure
        # Just log the error and continue
        pass
