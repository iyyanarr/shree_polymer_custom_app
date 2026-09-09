# Copyright (c) 2026, Shree Polymer and Contributors
# See license.txt

"""A Blanking DC must refuse a bin that is not free, and must not hide failure.

Production evidence (spp15, 14 Aug -> 9 Sep 2026): 96 orphan Blanking DC drafts,
33 bins carrying two active Item Bin Mappings, and moulding entries failing on
compounds that were never in their bin. The chain each time:

  a bin goes out on a DC (Asset moved U3 -> U2) -> its moulding never completes
  -> Bin Movement never moves it back -> the floor refills and rescans it into a
  NEW DC -> ERPNext rejects the Asset Movement ("does not belong to location")
  -> on_submit swallows that, make___rollback half-cleans and COMMITS -> legacy is
  left with a draft DC and stray mappings the bridge then reports as "missing".

So: refuse the bin up front, in validate, naming what is holding it; and if
on_submit does fail, raise -- never swallow -- and never commit mid-failure.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from shree_polymer_custom_app.shree_polymer_custom_app.doctype.blanking_dc_entry import (
	blanking_dc_entry as bdc,
)

BIN = "BLB -00045"          # a real bin asset on the local legacy clone
COMPOUND = "C_6122"
FROM_LOC = "U3 - Ambattur"
TO_LOC = "U2 - Ambattur"


def free_bin(bin_name, location=FROM_LOC):
	"""Make a real bin look free inside the test transaction (rolled back after)."""
	frappe.db.set_value("Asset", bin_name, "location", location, update_modified=False)
	frappe.db.sql("UPDATE `tabItem Bin Mapping` SET is_retired=1 WHERE blanking__bin=%s", bin_name)
	frappe.db.sql("UPDATE `tabBlank Bin Issue Item` SET is_completed=1 WHERE bin=%s", bin_name)


def make_dc(bin_name, batch="26TEST-1", gross=6.96):
	return frappe.get_doc({
		"doctype": "Blanking DC Entry",
		"employee": "HR-CON-EMP-00086",
		"posting_date": today(),
		"items": [{
			"bin_code": bin_name, "bin_weight": 1.4, "gross_weight": gross,
			"scanned_item": COMPOUND, "spp_batch_number": batch, "t_item_to_produce": "T5059",
		}],
	})


def open_blank_bin_issue(bin_name, lot):
	"""A submitted Blank Bin Issue still holding the bin (is_completed=0)."""
	doc = frappe.get_doc({
		"doctype": "Blank Bin Issue",
		"scan_production_lot": lot, "scan_bin": bin_name, "bin": bin_name,
		"items": [{"bin": bin_name, "is_completed": 0, "compound": COMPOUND}],
	})
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	doc.db_set("docstatus", 1, update_modified=False)
	for it in doc.items:
		frappe.db.set_value("Blank Bin Issue Item", it.name, "docstatus", 1, update_modified=False)
	return doc


class TestBlankingDCRefusesOccupiedBin(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		free_bin(BIN)

	def test_free_bin_is_accepted(self):
		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.docstatus, 0)

	def test_refuses_a_bin_that_never_came_back(self):
		"""Asset still at the TO location: its last cycle was never released."""
		free_bin(BIN, location=TO_LOC)
		with self.assertRaises(frappe.ValidationError) as cm:
			make_dc(BIN).insert(ignore_permissions=True)
		msg = str(cm.exception)
		self.assertIn(BIN, msg)
		self.assertIn(TO_LOC, msg)

	def test_refuses_a_bin_that_still_holds_compound(self):
		frappe.get_doc({
			"doctype": "Item Bin Mapping", "compound": COMPOUND, "qty": 4.0, "is_retired": 0,
			"blanking__bin": BIN, "spp_batch_number": "26OLD-1",
		}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError) as cm:
			make_dc(BIN).insert(ignore_permissions=True)
		msg = str(cm.exception)
		self.assertIn(BIN, msg)
		self.assertIn("26OLD-1", msg, "must name the batch still in the bin")

	def test_refuses_a_bin_still_issued_to_a_lot_and_names_the_lot(self):
		open_blank_bin_issue(BIN, lot="26TEST01")
		with self.assertRaises(frappe.ValidationError) as cm:
			make_dc(BIN).insert(ignore_permissions=True)
		msg = str(cm.exception)
		self.assertIn(BIN, msg)
		self.assertIn("26TEST01", msg, "the supervisor must be told WHICH lot holds the bin")

	def test_blank_bin_inward_path_is_exempt(self):
		"""Inward bins legitimately carry a mapping; that path never created one."""
		open_blank_bin_issue(BIN, lot="26TEST02")
		doc = make_dc(BIN)
		doc.from_blank_bin_inward = 1
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.docstatus, 0)


class TestBlankingDCDoesNotHideFailure(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		free_bin(BIN)

	def test_on_submit_reraises_and_does_not_commit(self):
		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)
		with patch.object(bdc, "create___asset_movement", side_effect=RuntimeError("asset movement rejected")), \
		     patch.object(frappe.db, "commit") as commit:
			with self.assertRaises(RuntimeError):
				doc.submit()
		self.assertFalse(commit.called, "a failed submit must not commit a half-cleaned state")

	def test_rollback_removes_the_mapping_even_when_qty_drifted(self):
		"""The old delete matched on exact qty; a row whose qty had moved survived as a ghost."""
		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Item Bin Mapping", "compound": COMPOUND, "qty": 10.0, "is_retired": 0,
			"blanking__bin": BIN, "spp_batch_number": "26TEST-1",
		}).insert(ignore_permissions=True)
		with patch.object(frappe.db, "commit"):
			bdc.make___rollback(doc)
		self.assertFalse(
			frappe.db.exists("Item Bin Mapping", {"blanking__bin": BIN, "spp_batch_number": "26TEST-1", "is_retired": 0}),
			"rollback must remove this DC's mapping by bin+batch, not by exact qty",
		)
