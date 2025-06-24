"""
Helper script to identify current custom roles and permissions for Batch doctype
Run this to see what permissions currently exist before configuring the restoration system
"""

import frappe


def get_current_batch_permissions():
    """
    Get all current permissions for Batch doctype including custom ones
    """
    print("=== Current Batch Doctype Permissions ===\n")
    
    # Get standard permissions
    print("1. Standard DocPerm entries:")
    standard_perms = frappe.get_all("DocPerm", 
        filters={"parent": "Batch"},
        fields=["role", "read", "write", "create", "delete", "submit", "cancel", "report", "export", "share", "print"]
    )
    
    for perm in standard_perms:
        print(f"   Role: {perm['role']}")
        print(f"   Permissions: {', '.join([k for k, v in perm.items() if v == 1 and k != 'role'])}")
        print()
    
    # Get custom permissions
    print("2. Custom DocPerm entries:")
    custom_perms = frappe.get_all("Custom DocPerm", 
        filters={"parent": "Batch"},
        fields=["role", "read", "write", "create", "delete", "submit", "cancel", "report", "export", "share", "print"]
    )
    
    if custom_perms:
        for perm in custom_perms:
            print(f"   Role: {perm['role']}")
            print(f"   Permissions: {', '.join([k for k, v in perm.items() if v == 1 and k != 'role'])}")
            print()
    else:
        print("   No custom permissions found")
    
    # Get all roles in system
    print("3. All available roles:")
    all_roles = frappe.get_all("Role", fields=["name", "disabled"])
    for role in all_roles:
        status = "disabled" if role.get("disabled") else "active"
        print(f"   - {role['name']} ({status})")


def get_user_roles(user_email=None):
    """
    Get roles for a specific user
    """
    if not user_email:
        user_email = frappe.session.user
    
    print(f"\n=== Roles for user: {user_email} ===")
    
    user_roles = frappe.get_all("Has Role", 
        filters={"parent": user_email},
        fields=["role"]
    )
    
    for role in user_roles:
        print(f"   - {role['role']}")


if __name__ == "__main__":
    # This script should be run in Frappe console
    # bench --site [your-site] console
    # exec(open('path/to/this/script.py').read())
    
    try:
        get_current_batch_permissions()
        get_user_roles()
        
        print("\n=== Next Steps ===")
        print("1. Identify which role needs custom permissions for Batch doctype")
        print("2. Update custom_role_permissions.py with the correct role name")
        print("3. Set the desired permissions in the custom_batch_permissions list")
        print("4. Test the restoration function")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you're running this in Frappe console with site context")
