# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ItemBinMapping(Document):
	pass

@frappe.whitelist()
def get_bin_category():
	try:
		spp_settings = frappe.get_single("SPP Settings")
		if spp_settings.bin_category:
			return {"status":"Success","category":spp_settings.bin_category}
		return {"status":"Failed"}
	except Exception:
		frappe.log_error(title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.item_bin_mapping.item_bin_mapping.get_bin_category",message=frappe.get_traceback())