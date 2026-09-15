# Copyright (c) 2026, Shree Polymer and contributors
# For license information, please see license.txt
"""Two defects that together strand stock on a failed Moulding Production Entry.

ONE — the bin-release guard reads a different source than ERPNext validates.

moulding_production_entry.py decides whether to send a bin home by looking at
the newest Asset Movement Item:

    if last_mov:
        if not last_mov[0].target_location == spp_settings.from_location:
            make_asset_movement(...)

make_asset_movement then hardcodes the direction source=to_location (U2),
target=from_location (U3). ERPNext validates that move against the ASSET's own
`location` field -- not against the movement history. When the two disagree the
move is attempted and refused:

    Asset BLB -00087 does not belong to the location U2 - Ambattur

They do disagree. On 2026-09-11 a bulk reconciliation (system1@padmasteel.in,
transaction_date 10:50:49) submitted Asset Movements taking these bins U3 -> U2
without the asset's own location following. So the history says U2 while
Asset.location still says U3: the guard sees "not home, bring it back" and
ERPNext sees "this asset is not at U2". Verified on production for BLB -00087,
-00209, -00221 and -00091.

Read the field ERPNext enforces. This is the same rule bridge #74 applied to
the Bin Movement leg (_asset_move_needed); the MPE leg kept the old one.

TWO — the rollback cannot undo a submitted Stock Entry.

delete_stock_entry_safely calls frappe.delete_doc(..., force=1). force does NOT
bypass Frappe's submitted-document check, so for an already-submitted entry it
raises

    Stock Entry MPE-2026-08010: Submitted Record cannot be deleted.
    You must cancel it first

the except swallows it into Error Log, and the compensating action silently
does nothing. The MPE stays at docstatus=0 with its stock consumed. Seven such
orphans accumulated between 12 and 15 Sep 2026 (MPE-2026-08010, -08013, -08018,
-08023, -08028, -08033, -08036).

Cancelling is what actually reverses the ledger, and it has to happen BEFORE
the link-breaking UPDATEs -- those null out batch_no and serial_and_batch_bundle,
which is exactly what a cancel needs in order to reverse the stock.
"""

import unittest
from unittest.mock import MagicMock, patch, call


class TestBinReleaseAssetMoveGuard(unittest.TestCase):
    """The guard must key on Asset.location, the field ERPNext enforces."""

    def setUp(self):
        self.frappe = patch(
            "shree_polymer_custom_app.shree_polymer_custom_app.doctype"
            ".moulding_production_entry.moulding_production_entry.frappe").start()
        self.addCleanup(patch.stopall)

    def _settings(self, home="U3 - Ambattur", away="U2 - Ambattur"):
        s = MagicMock()
        s.from_location = home
        s.to_location = away
        return s

    def _needs_move(self, asset_location, home="U3 - Ambattur"):
        from shree_polymer_custom_app.shree_polymer_custom_app.doctype \
            .moulding_production_entry.moulding_production_entry import _bin_move_needed
        self.frappe.db.get_value.return_value = asset_location
        return _bin_move_needed(self._settings(home=home), "BLB -00087")

    def test_bin_already_home_is_not_moved(self):
        # The live case: history said U2, Asset.location says U3.
        self.assertFalse(self._needs_move("U3 - Ambattur"))

    def test_bin_at_u2_is_moved_home(self):
        self.assertTrue(self._needs_move("U2 - Ambattur"))

    def test_bin_somewhere_else_still_attempts_the_move(self):
        # Fail open: unchanged behaviour for a third location.
        self.assertTrue(self._needs_move("U4 - Aranvoyal"))

    def test_unknown_location_fails_open(self):
        self.assertTrue(self._needs_move(None))

    def test_missing_home_setting_fails_open(self):
        self.assertTrue(self._needs_move("U3 - Ambattur", home=None))

    def test_movement_history_is_not_consulted(self):
        # Asset.location is home, so no move -- regardless of any history.
        self.assertFalse(self._needs_move("U3 - Ambattur"))
        self.frappe.db.sql.assert_not_called()


class TestRollbackCancelsBeforeDeleting(unittest.TestCase):
    """A submitted Stock Entry must be cancelled, or nothing is rolled back."""

    def setUp(self):
        self.frappe = patch(
            "shree_polymer_custom_app.shree_polymer_custom_app.api.frappe").start()
        self.addCleanup(patch.stopall)
        self.frappe.db.exists.return_value = True
        self.frappe.get_all.return_value = []
        self.doc = MagicMock()
        self.frappe.get_doc.return_value = self.doc
        self.calls = []
        self.doc.cancel.side_effect = lambda: self.calls.append("cancel")
        self.frappe.db.sql.side_effect = lambda *a, **k: self.calls.append("sql")
        self.frappe.delete_doc.side_effect = lambda *a, **k: self.calls.append("delete")

    def _run(self, docstatus):
        from shree_polymer_custom_app.shree_polymer_custom_app.api import (
            delete_stock_entry_safely)
        self.doc.docstatus = docstatus
        delete_stock_entry_safely("MPE-2026-08010")

    def test_submitted_entry_is_cancelled(self):
        self._run(docstatus=1)
        self.assertIn("cancel", self.calls)

    def test_cancel_happens_before_the_link_breaking_updates(self):
        # The UPDATEs null batch_no / serial_and_batch_bundle; cancel needs them
        # intact to reverse the ledger.
        self._run(docstatus=1)
        self.assertLess(self.calls.index("cancel"), self.calls.index("sql"))

    def test_cancel_happens_before_the_delete(self):
        self._run(docstatus=1)
        self.assertLess(self.calls.index("cancel"), self.calls.index("delete"))

    def test_draft_entry_is_not_cancelled(self):
        self._run(docstatus=0)
        self.assertNotIn("cancel", self.calls)
        self.assertIn("delete", self.calls)

    def test_already_cancelled_entry_is_not_cancelled_again(self):
        self._run(docstatus=2)
        self.assertNotIn("cancel", self.calls)

    def test_a_failed_cancel_is_reported_not_swallowed_silently(self):
        self.doc.cancel.side_effect = Exception("linked docs exist")
        self._run(docstatus=1)
        self.assertTrue(self.frappe.log_error.called,
                        "a rollback that could not reverse the stock must be logged")


if __name__ == "__main__":
    unittest.main()
