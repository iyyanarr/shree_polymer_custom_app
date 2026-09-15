# Copyright (c) 2026, Shree Polymer and contributors
"""A cut-bit transfer must draw down the bin it was scanned against.

The old code searched by COMPOUND ALONE and took row [0] with no ORDER BY:

    check_item_bin = frappe.db.get_all("Item Bin Mapping",
        filters={"compound": x.item_code, "is_retired": 0}, fields=['name','qty'])

so it retired or decremented an arbitrary live mapping belonging to some other
bin. The bin was available the whole time - Cut Bit Transfer scans it into
`scan_clip__bin`.

Production, 05-12 Sep 2026: 162 successful legacy cut-bit transfers, against
compounds spread across many bins - C_6122 in 45 live bins, C_70103 in 19,
C_69221 in 16. A C_6122 cut-bit had about a 1-in-45 chance of hitting the right
bin.
"""

import unittest
from unittest.mock import patch

from shree_polymer_custom_app.shree_polymer_custom_app.bin_mapping import (
    draw_down_bin_mapping,
    resolve_live_bin_mapping,
)


class TestResolveLiveBinMapping(unittest.TestCase):
    def setUp(self):
        self.frappe = patch(
            "shree_polymer_custom_app.shree_polymer_custom_app.bin_mapping.frappe").start()
        self.addCleanup(patch.stopall)
        self.frappe.db.exists.return_value = False
        self.frappe.db.get_value.return_value = "BLB -00045"

    def test_the_query_is_bounded_by_the_BIN(self):
        """The whole bug: without blanking__bin it can hit any bin."""
        self.frappe.db.get_all.return_value = [{"name": "ibm-1", "qty": 5.0}]
        resolve_live_bin_mapping("BLB 045", compound="C_6122")
        filters = self.frappe.db.get_all.call_args[1]["filters"]
        self.assertEqual(filters["blanking__bin"], "BLB -00045")
        self.assertEqual(filters["is_retired"], 0)

    def test_it_is_ordered_so_the_answer_is_deterministic(self):
        self.frappe.db.get_all.return_value = [{"name": "ibm-1", "qty": 5.0}]
        resolve_live_bin_mapping("BLB 045", compound="C_6122")
        self.assertIn("creation", self.frappe.db.get_all.call_args[1]["order_by"])

    def test_the_batch_narrows_it_too(self):
        self.frappe.db.get_all.return_value = [{"name": "ibm-exact", "qty": 5.0}]
        r = resolve_live_bin_mapping("BLB 045", compound="C_6122", spp_batch_number="26I08X19-1")
        self.assertEqual(r["name"], "ibm-exact")
        f = self.frappe.db.get_all.call_args[1]["filters"]
        self.assertEqual(f["spp_batch_number"], "26I08X19-1")
        self.assertEqual(f["blanking__bin"], "BLB -00045")

    def test_NO_BIN_still_works_when_the_batch_is_known(self):
        """Bridge-created cut-bit transfers leave scan_clip__bin empty - verified
        on production, CBT-25185/25186. Requiring a bin would silently stop the
        draw-down those entries exist to do."""
        self.frappe.db.get_value.return_value = None
        self.frappe.db.get_all.return_value = [{"name": "ibm-1", "qty": 2.5}]
        r = resolve_live_bin_mapping(None, compound="C_6122", spp_batch_number="26I08X23-1")
        self.assertIsNotNone(r)
        f = self.frappe.db.get_all.call_args[1]["filters"]
        self.assertNotIn("blanking__bin", f)
        self.assertEqual(f["spp_batch_number"], "26I08X23-1")

    def test_COMPOUND_ALONE_is_refused(self):
        """The whole defect: no bin and no batch must mean no write."""
        self.frappe.db.get_value.return_value = None
        self.assertIsNone(resolve_live_bin_mapping(None, compound="C_6122"))
        self.frappe.db.get_all.assert_not_called()

    def test_no_scan_and_no_batch_returns_None(self):
        self.assertIsNone(resolve_live_bin_mapping(None, compound="C_6122"))
        self.assertIsNone(resolve_live_bin_mapping("", compound="C_6122"))

    def test_a_bin_with_no_live_mapping_returns_None(self):
        self.frappe.db.get_all.return_value = []
        self.assertIsNone(resolve_live_bin_mapping("BLB 045", compound="C_6122"))


class TestDrawDown(unittest.TestCase):
    def setUp(self):
        self.frappe = patch(
            "shree_polymer_custom_app.shree_polymer_custom_app.bin_mapping.frappe").start()
        self.addCleanup(patch.stopall)
        self.frappe.utils.flt = lambda v: float(v or 0)

    def test_an_exact_draw_retires_the_mapping(self):
        draw_down_bin_mapping({"name": "ibm-1", "qty": 5.0}, 5.0)
        self.frappe.db.set_value.assert_called_once_with(
            "Item Bin Mapping", "ibm-1", "is_retired", 1)

    def test_a_partial_draw_reduces_the_qty(self):
        draw_down_bin_mapping({"name": "ibm-1", "qty": 5.0}, 2.0)
        self.frappe.db.set_value.assert_called_once_with(
            "Item Bin Mapping", "ibm-1", "qty", 3.0)

    def test_a_draw_bigger_than_the_bin_is_recorded_not_applied(self):
        """The two records disagree; zeroing it silently would hide that."""
        draw_down_bin_mapping({"name": "ibm-1", "qty": 2.0}, 5.0)
        self.frappe.db.set_value.assert_not_called()
        self.frappe.log_error.assert_called_once()

    def test_no_mapping_is_a_no_op(self):
        draw_down_bin_mapping(None, 5.0)
        self.frappe.db.set_value.assert_not_called()
