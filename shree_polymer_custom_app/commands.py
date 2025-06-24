"""
Custom commands for managing role permissions
"""

import click
import frappe
from frappe.commands import pass_context, get_site
from shree_polymer_custom_app.custom_role_permissions import (
    restore_all_custom_permissions,
    export_custom_permissions_to_fixtures
)


@click.command('restore-custom-permissions')
@click.option('--site', help='Site name')
@pass_context
def restore_custom_permissions(context, site=None):
    """
    Restore custom role permissions for core doctypes
    Usage: bench --site [site-name] restore-custom-permissions
    """
    if not site:
        site = get_site(context)
    
    with frappe.init_site(site):
        frappe.connect()
        try:
            restore_all_custom_permissions()
            click.echo("✅ Custom permissions restored successfully!")
        except Exception as e:
            click.echo(f"❌ Error restoring permissions: {str(e)}")
            raise
        finally:
            frappe.destroy()


@click.command('export-custom-permissions')
@click.option('--site', help='Site name')
@pass_context
def export_custom_permissions(context, site=None):
    """
    Export current custom permissions to fixtures
    Usage: bench --site [site-name] export-custom-permissions
    """
    if not site:
        site = get_site(context)
    
    with frappe.init_site(site):
        frappe.connect()
        try:
            permissions = export_custom_permissions_to_fixtures()
            click.echo(f"✅ Exported {len(permissions) if permissions else 0} custom permissions to fixtures!")
        except Exception as e:
            click.echo(f"❌ Error exporting permissions: {str(e)}")
            raise
        finally:
            frappe.destroy()


commands = [
    restore_custom_permissions,
    export_custom_permissions,
]
