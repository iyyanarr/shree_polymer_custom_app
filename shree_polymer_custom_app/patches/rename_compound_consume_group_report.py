import frappe


def execute():
	old_name = "Compound Consume Group Report"
	new_name = "Blanking And Sheeting Requirement"

	if not frappe.db.exists("Report", old_name):
		return

	if frappe.db.exists("Report", new_name) and frappe.db.exists("Report", old_name):
		frappe.delete_doc("Report", old_name, force=True, ignore_permissions=True)
		return

	frappe.rename_doc("Report", old_name, new_name, force=True, merge=False)
