# Copyright (c) 2023, Tridotstech and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import flt

class TestMouldSpecification(unittest.TestCase):
	def test_validate_with_null_values(self):
		# Create a dummy Mould Specification with some None/Null values
		doc = frappe.get_doc({
			"doctype": "Mould Specification",
			"mould_ref": "MLD-TEST-1",
			"compound_code": "COMP-TEST-1",
			"spp_ref": "SPP-TEST-1",
			"mould_status": "DEV",
			"noof_cavities": 12,
			"no_of_piece": None, # Null value
			"blank_specifications": [
				{
					"blank_type": "STRIP",
					"wtpiece_min_gms": 79.5,
					"wtpiece_max_gms": None, # Null value that caused the error
					"no_of_piece": 1
				}
			]
		})
		
		# This should not throw TypeError
		try:
			doc.validate()
		except TypeError as e:
			self.fail(f"validate() raised TypeError unexpectedly: {e}")
		except Exception as e:
			self.fail(f"validate() raised {type(e).__name__} unexpectedly: {e}")

		# Verify calculations handled None as 0
		self.assertEqual(doc.no_of_cavity_per_blank, 12) # 12 / 0 -> 12 (as per logic)
		self.assertEqual(doc.blank_specifications[0].wtlift_max_gms, 0.0) # 0 * 0
		self.assertEqual(doc.blank_specifications[0].wtpiece_avg_gms, round(79.5 / 2, 3)) # (79.5 + 0) / 2
