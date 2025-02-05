# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SPPSettings(Document):
	pass

@frappe.whitelist()
def get_naming_series_options():
	try:
		naming_series = frappe.get_meta("Stock Entry").get_field("naming_series").options.split('\n')
		frappe.local.response.message = sorted(naming_series)
		frappe.local.response.status = 'success'
	except Exception:
		frappe.local.response.status = 'failed'
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_settings.spp_settings.get_naming_series_options",message=frappe.get_traceback())


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