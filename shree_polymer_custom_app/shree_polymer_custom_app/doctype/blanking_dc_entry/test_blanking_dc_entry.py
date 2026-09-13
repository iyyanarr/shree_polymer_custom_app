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


class TestBlankingDCRecordsOccupiedBin(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		free_bin(BIN)

	def test_free_bin_is_accepted(self):
		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.docstatus, 0)

	def test_accepts_a_bin_that_never_came_back_and_records_it(self):
		"""Asset still at the TO location: its last cycle was never released.

		That is the NORMAL state at shift change here. The moulding entry for the
		previous lot is routinely not posted until after the next shift has already
		taken the bin, so the Asset location lags reality by a shift. The bin in the
		operator's hands is empty; only the record says otherwise.

		Refusing it (shipped #13, 9 Sep) did not protect anything, because Ops has
		already committed the stock by the time the Legacy leg runs -- the refusal
		is permanent divergence, not a block. It stranded 19 bins across 8 DCs on
		12 Sep 2026, and spiked to 19 failures in 36 DCs on 10 Sep.
		"""
		free_bin(BIN, location=TO_LOC)
		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)          # must not raise
		self.assertEqual(doc.items[0].bin_code, BIN)

	def test_accepts_a_bin_that_still_holds_compound_and_records_it(self):
		"""A bin carrying a live mapping is accepted, and the fact is recorded.

		Two live mappings on one bin is a LEGITIMATE state here -- 4 of the 7
		doubled bins on production are mirrored identically in Console. The hazard
		#13 named was that "the moulding check reads whichever one MariaDB returns
		first", which is a non-deterministic read in the MPE lookup. Forbidding a
		real state to work around a missing ORDER BY somewhere else is the wrong
		trade, and it is the trade that jammed the line.
		"""
		frappe.get_doc({
			"doctype": "Item Bin Mapping", "compound": COMPOUND, "qty": 4.0, "is_retired": 0,
			"blanking__bin": BIN, "spp_batch_number": "26OLD-1",
		}).insert(ignore_permissions=True)

		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)          # must not raise
		self.assertEqual(doc.items[0].bin_code, BIN)

	def test_an_occupied_bin_is_written_to_the_error_log(self):
		"""Dropping the block must not drop the signal -- we still need to measure
		how often a bin is taken before its last lot was posted."""
		frappe.get_doc({
			"doctype": "Item Bin Mapping", "compound": COMPOUND, "qty": 4.0, "is_retired": 0,
			"blanking__bin": BIN, "spp_batch_number": "26OLD-1",
		}).insert(ignore_permissions=True)
		before = frappe.db.count("Error Log")

		make_dc(BIN).insert(ignore_permissions=True)

		self.assertGreater(frappe.db.count("Error Log"), before,
			"a bin that was not free must still be recorded")

	def test_accepts_an_empty_bin_even_with_an_open_blank_bin_issue(self):
		"""An empty bin is free, whatever its paperwork says.

		The open-Blank-Bin-Issue refusal shipped in #13 could only ever fire on
		an EMPTY bin: the "still holds compound" check above throws first
		whenever the bin actually has material. So it never protected the case
		it named ("another lot owns it") — it just stranded bins whose issue was
		never closed. Only a Bin Movement or an MPE sets is_completed, so
		releasing a bin by retiring its Item Bin Mapping leaves the issue open
		for good: 164 bins were stuck that way on prod.

		Worse, Ops commits the stock before the Legacy leg runs, so a
		Legacy-only refusal is permanent divergence rather than a safe block —
		10 Blanking DC entries diverged in the two days after #13 shipped
		(e.g. BDC-2026-01064: Ops MES-LOG-2026-21252 Success, Legacy Failed on
		bin BLB -00208, and every retry failed identically).
		"""
		open_blank_bin_issue(BIN, lot="26TEST01")     # paperwork open, bin empty

		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)           # must not raise

		self.assertEqual(doc.items[0].bin_code, BIN)

	def test_material_plus_open_paperwork_is_still_accepted(self):
		"""Neither material nor paperwork blocks the DC any more.

		The protection moves to a pre-flight that runs BEFORE Ops commits, so the
		operator is told at the blanking station and nothing diverges. Until that
		ships, recording beats refusing: a refusal here cannot stop the Ops write
		that already happened.
		"""
		frappe.get_doc({
			"doctype": "Item Bin Mapping", "blanking__bin": BIN,
			"compound": COMPOUND, "spp_batch_number": "26OLD-1",
			"qty": 5.0, "is_retired": 0,
		}).insert(ignore_permissions=True)
		open_blank_bin_issue(BIN, lot="26TEST01")

		doc = make_dc(BIN)
		doc.insert(ignore_permissions=True)          # must not raise
		self.assertEqual(doc.items[0].bin_code, BIN)

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
