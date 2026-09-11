# Copyright (c) 2026, Shree Polymer and contributors
# See license.txt
"""Releasing a bin must clear every live mapping on it, not just the scanned one.

validate_bin returns compound_resp[0] — the FIRST of however many live Item Bin
Mapping rows a bin carries — and the release retired that single ibm_id. A bin
holding two batches therefore kept one mapping alive through a release, and the
next Blanking DC refused it with "still holds".

Live, 11 Sep 2026: BLB -00233 carried two live mappings (26I05X23-1 = 3.847 and
26I05X22-1 = 3.09). It was released twice — BINM-2026-01019 at 13:50 and
BINM-2026-01020 at 13:53 — and both mappings were still live afterwards. Its
Blanking DC failed at 13:53:44, 28 seconds after the second release.

Two-batch bins are legitimate, not corruption: 4 of the 7 doubled bins on
production are mirrored identically in Console. The unit being released is the
BIN, not one mapping row.

Run with:
    bench --site spp15.local run-tests --module \
      shree_polymer_custom_app.shree_polymer_custom_app.doctype.bin_movement.test_bin_release_clears_every_mapping
"""

import unittest
from unittest.mock import MagicMock, patch

from shree_polymer_custom_app.shree_polymer_custom_app.doctype.bin_movement import (
    bin_movement as bm,
)


def _movement(bin_id="BLB -00233", ibm_id="ibm-first", released=1, asset_movement=0):
    row = MagicMock()
    row.bin_id = bin_id
    row.ibm_id = ibm_id
    row.bin_released = released
    row.asset_movement = asset_movement
    doc = MagicMock()
    doc.movement_items = [row]
    doc.doctype = "Bin Movement"
    doc.name = "BINM-TEST-0001"
    return doc


class TestBinReleaseClearsEveryMapping(unittest.TestCase):
    @patch.object(bm, "frappe")
    def test_release_retires_all_live_mappings_on_the_bin(self, mock_frappe):
        bm.make_bin_release_movement(_movement())
        sql = " ".join(str(c) for c in mock_frappe.db.sql.call_args_list)
        self.assertIn("tabItem Bin Mapping", sql)
        self.assertIn("blanking__bin", sql)
        self.assertIn("BLB -00233", sql)

    @patch.object(bm, "frappe")
    def test_the_scanned_row_is_still_retired_too(self, mock_frappe):
        bm.make_bin_release_movement(_movement())
        mock_frappe.db.set_value.assert_any_call(
            "Item Bin Mapping", "ibm-first", "is_retired", 1)

    @patch.object(bm, "frappe")
    def test_a_row_with_no_bin_id_still_retires_the_scanned_mapping(self, mock_frappe):
        bm.make_bin_release_movement(_movement(bin_id=None))
        mock_frappe.db.set_value.assert_any_call(
            "Item Bin Mapping", "ibm-first", "is_retired", 1)

    @patch.object(bm, "frappe")
    def test_the_blank_bin_issue_claim_is_still_closed(self, mock_frappe):
        bm.make_bin_release_movement(_movement())
        sql = " ".join(str(c) for c in mock_frappe.db.sql.call_args_list)
        self.assertIn("tabBlank Bin Issue Item", sql)
        self.assertIn("is_completed", sql)

    @patch.object(bm, "frappe")
    def test_a_row_not_marked_released_touches_nothing(self, mock_frappe):
        bm.make_bin_release_movement(_movement(released=0))
        sql = " ".join(str(c) for c in mock_frappe.db.sql.call_args_list)
        self.assertNotIn("tabItem Bin Mapping", sql)
        mock_frappe.db.set_value.assert_not_called()
