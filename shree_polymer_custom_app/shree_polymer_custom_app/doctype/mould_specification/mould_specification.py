# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MouldSpecification(Document):
	def before_naming(self):
		self.naming_id = self.mould_ref + '-' + self.spp_ref
	def validate(self):
		self.no_of_cavity_per_blank = round(float(self.noof_cavities) / float(self.no_of_piece),3) if self.no_of_piece else self.noof_cavities 
		if self.mould_status == "ACTIVE":
			exe = frappe.db.get_value(self.doctype,{"name":["!=",self.name],"mould_ref":self.mould_ref,"compound_code":self.compound_code,"spp_ref":self.spp_ref,"mould_status":"ACTIVE"})
			if exe:
				frappe.throw(f"The <b>Specification</b> already in <b>Active</b> for the Mould <b>{self.mould_ref}</b> & Compound <b>{self.compound_code}</b> & Mat <b>{self.spp_ref}</b>.")
		if self.blank_specifications:
			wtpiece_avg_gms = 0.0
			wtlift_avg_gms = 0.0
			for bl_spec in self.blank_specifications:
				bl_spec.wtlift_min_gms = round(bl_spec.wtpiece_min_gms * float(self.no_of_piece),3)
				bl_spec.wtlift_max_gms = round(bl_spec.wtpiece_max_gms * float(self.no_of_piece),3)
				bl_spec.wtpiece_avg_gms = round(((bl_spec.wtpiece_min_gms + bl_spec.wtpiece_max_gms)/2),3) if bl_spec.wtpiece_min_gms + bl_spec.wtpiece_max_gms else 0
				bl_spec.wtlift_avg_gms = round(((bl_spec.wtlift_min_gms + bl_spec.wtlift_max_gms)/2),3) if bl_spec.wtlift_min_gms + bl_spec.wtlift_max_gms else 0
				wtpiece_avg_gms += bl_spec.wtpiece_avg_gms
				wtlift_avg_gms += bl_spec.wtlift_avg_gms
			self.wtpiece_avg_gms = round(wtpiece_avg_gms / len(self.blank_specifications),3)
			self.wtlift_avg_gms = round(wtlift_avg_gms / len(self.blank_specifications),3)
			self.avg_blank_wtproduct_gms = round(self.wtpiece_avg_gms / self.no_of_cavity_per_blank,3) if self.no_of_cavity_per_blank else wtlift_avg_gms
		if self.shell_weight:
			self.avg_blank_wtproduct_gms = float(self.avg_blank_wtproduct_gms) + self.shell_weight

@frappe.whitelist()
def get_work_mould_filters():
	try:
		frappe.response.message = frappe.get_single("SPP Settings")
		frappe.response.status = 'success'
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.mould_specification.mould_specification.get_work_mould_filters")
		frappe.response.status = 'failed'