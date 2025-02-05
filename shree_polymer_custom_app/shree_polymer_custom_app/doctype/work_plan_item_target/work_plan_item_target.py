# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WorkPlanItemTarget(Document):
	def validate(self):
		if self.is_new() and frappe.db.get_value(self.doctype,{"item":self.item,"shift_type":self.shift_type}):
			frappe.throw(f"Target value of item <b>{self.item}</b> and the shift <b>{self.shift_type}</b> is already exists..!")

@frappe.whitelist()
def get_shift_timings():
	try:
		re = frappe.db.sql(f"SELECT DISTINCT total_time FROM `tabShift Type` ",as_dict = 1)
		if re:
			resp = [x.total_time for x in re]
			frappe.response.status = "success"
			frappe.response.data = resp
		else:
			frappe.response.status = "failed"
			frappe.response.message = "There is no <b>Shift Types</b> found..!"
	except Exception:
		frappe.response.status = "failed"
		frappe.response.message = "Something went wrong not able to fetch <b>Shift Types</b> ..!"
		frappe.log_error(title = "error in get_shift_timings", message = frappe.get_traceback())