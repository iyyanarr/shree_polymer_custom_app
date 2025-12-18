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
			total_wt_piece_sum = 0.0  # Sum of all Wt/Piece
			
			for bl_spec in self.blank_specifications:
				bl_spec.wtlift_min_gms = round(bl_spec.wtpiece_min_gms * float(self.no_of_piece),3)
				bl_spec.wtlift_max_gms = round(bl_spec.wtpiece_max_gms * float(self.no_of_piece),3)
				bl_spec.wtpiece_avg_gms = round(((bl_spec.wtpiece_min_gms + bl_spec.wtpiece_max_gms)/2),3) if bl_spec.wtpiece_min_gms + bl_spec.wtpiece_max_gms else 0
				bl_spec.wtlift_avg_gms = round(((bl_spec.wtlift_min_gms + bl_spec.wtlift_max_gms)/2),3) if bl_spec.wtlift_min_gms + bl_spec.wtlift_max_gms else 0
				wtpiece_avg_gms += bl_spec.wtpiece_avg_gms
				wtlift_avg_gms += bl_spec.wtlift_avg_gms
				# Add to total sum for new calculation
				total_wt_piece_sum += bl_spec.wtpiece_avg_gms
				
			self.wtpiece_avg_gms = round(wtpiece_avg_gms / len(self.blank_specifications),3)
			self.wtlift_avg_gms = round(wtlift_avg_gms / len(self.blank_specifications),3)
			
			# Fix: Calculate as Sum of 'Wt/Piece' x No. Of Piece / No. of Cavities
			if self.noof_cavities and float(self.noof_cavities) > 0:
				# Formula: {[(Sum of ‘Avg Wt. of each blank * No of Piece) - Pot Residue} / No. of Cavities
				
				# Calculate weighted sum from child table values
				weighted_wt_piece_sum = 0.0
				for bl_spec in self.blank_specifications:
					qty = bl_spec.no_of_piece if bl_spec.no_of_piece else 0
					weighted_wt_piece_sum += (bl_spec.wtpiece_avg_gms * qty)

				pot_residue = self.pot_residue if self.pot_residue else 0.0
				numerator = weighted_wt_piece_sum - float(pot_residue)
				
				# Ensure result is not negative, though business logic should prevent this
				numerator = max(0.0, numerator)
				self.avg_blank_wtproduct_gms = round(numerator / float(self.noof_cavities), 3)
			else:
				self.avg_blank_wtproduct_gms = round(self.wtpiece_avg_gms / self.no_of_cavity_per_blank,3) if self.no_of_cavity_per_blank else wtlift_avg_gms
		# Note: Shell weight is stored separately and handled in rejection calculations
		# The avg_blank_wtproduct_gms should contain only the compound/material weight

@frappe.whitelist()
def get_work_mould_filters():
	try:
		frappe.response.message = frappe.get_single("SPP Settings")
		frappe.response.status = 'success'
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.mould_specification.mould_specification.get_work_mould_filters")
		frappe.response.status = 'failed'

@frappe.whitelist()
def fix_mould_specification_calculations():
	"""
	Data migration function to fix existing mould specification calculations
	Remove shell weight from avg_blank_wtproduct_gms and recalculate properly
	"""
	try:
		# Get all mould specifications
		mould_specs = frappe.get_all("Mould Specification", 
			fields=["name", "shell_weight", "avg_blank_wtproduct_gms"], 
			filters={"docstatus": ["!=", 2]})
		
		updated_count = 0
		
		for spec in mould_specs:
			if spec.shell_weight and spec.avg_blank_wtproduct_gms:
				# Recalculate by triggering the validate method
				doc = frappe.get_doc("Mould Specification", spec.name)
				
				# Store old value for comparison
				old_value = doc.avg_blank_wtproduct_gms
				
				# Trigger validation to recalculate
				doc.validate()
				
				# Save the document
				doc.save()
				
				new_value = doc.avg_blank_wtproduct_gms
				
				print(f"Updated {spec.name}: {old_value} -> {new_value}")
				updated_count += 1
		
		frappe.db.commit()
		
		message = f"Successfully updated {updated_count} mould specifications"
		print(message)
		return {"status": "success", "message": message}
		
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Fix Mould Specification Calculations Error"
		)
		error_msg = f"Error updating mould specifications: {str(e)}"
		print(error_msg)
		return {"status": "error", "message": error_msg}

@frappe.whitelist()
def check_mould_spec_calculation(mould_spec_name):
	"""Check the calculation for a specific mould specification"""
	try:
		doc = frappe.get_doc("Mould Specification", mould_spec_name)
		
		result = {
			"mould_ref": doc.mould_ref,
			"spp_ref": doc.spp_ref,
			"noof_cavities": doc.noof_cavities,
			"no_of_piece": doc.no_of_piece,
			"shell_weight": doc.shell_weight,
			"current_avg_blank_wtproduct_gms": doc.avg_blank_wtproduct_gms
		}
		
		if doc.blank_specifications:
			# Calculate weighted sum from child table values
			total_wt_piece = sum([float(spec.wtpiece_avg_gms or 0) for spec in doc.blank_specifications])
			weighted_wt_piece_sum = 0.0
			for spec in doc.blank_specifications:
				qty = spec.no_of_piece if spec.no_of_piece else 0
				weighted_wt_piece_sum += (float(spec.wtpiece_avg_gms or 0) * flt(qty))

			pot_residue = doc.pot_residue if doc.pot_residue else 0.0
			numerator = weighted_wt_piece_sum - float(pot_residue)
			numerator = max(0.0, numerator)
			expected_avg = numerator / float(doc.noof_cavities)
			
			result["pot_residue"] = pot_residue
			result["weighted_wt_piece_sum"] = weighted_wt_piece_sum
			material_weight_per_piece_kg = expected_avg / 1000
			
			result.update({
				"total_wt_piece_sum": total_wt_piece,
				"expected_avg_blank_wtproduct_gms": expected_avg,
				"material_weight_per_piece_kg": material_weight_per_piece_kg,
				"blank_specifications": [
					{
						"idx": spec.idx,
						"blank_type": spec.blank_type,
						"wtpiece_avg_gms": spec.wtpiece_avg_gms,
						"no_of_piece": spec.no_of_piece
					} for spec in doc.blank_specifications
				]
			})
		
		return result
		
	except Exception as e:
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Check Mould Spec Calculation Error"
		)
		return {"error": str(e)}