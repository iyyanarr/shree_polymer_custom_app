# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class VendorCategory(Document):
	pass


@frappe.whitelist()
def get_filter_subcontractor():
	try:
		import json
		query = f""" SELECT name FROM `tabWarehouse` WHERE  is_group = 1 AND disabled != 1  """
		resp = frappe.db.sql(query,as_dict = 1)
		if resp:
			result = []
			for k in resp:result.append(k.name)
			frappe.response.status = "success"
			frappe.response.message = json.dumps(result)
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"There is no<b>Warehouse</b> details found..!"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = f"Something went wrong not able to filter <b>Parent Warehouse</b>..!"
		frappe.log_error(title='Error in get_filter_subcontractor',message = frappe.get_traceback())