# Copyright (c) 2026, Shree Polymer and contributors
# See license.txt
"""The "no Blank Bin Issue" message must name the real cause.

validate_lot_number's join requires ALL of: a submitted Blank Bin Issue, an
item with is_completed = 0, and a job_card that resolves to the lot. Any one
failing produced the same sentence — "There is no entry for Blank Bin Issue
for the scanned lot number" — so an operator went hunting for a document that
was usually sitting right there, submitted, against the right bin.

Live (11 Sep 2026): lot 26I11X01 got that sentence while PE-80280 sat
submitted against bin BLB -00241, its item already flipped to is_completed = 1
by an unrelated bin release two hours earlier. Bin BLB -00241 had in fact been
filled, issued and retired twice that day under two different batches.

Run with:
    bench --site spp15.local run-tests --module \
      shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.test_blank_bin_issue_message
"""

import unittest
from unittest.mock import patch

from shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry import (
    moulding_production_entry as mpe,
)


def _row(issue, bin_code, is_completed, docstatus=1, job_card="PO-JOB1"):
    from frappe import _dict
    return _dict(issue=issue, bin=bin_code, is_completed=is_completed,
                 docstatus=docstatus, job_card=job_card)


class TestExplainMissingBlankBinIssue(unittest.TestCase):
    @patch.object(mpe, "frappe")
    def test_no_issue_at_all_keeps_the_original_sentence(self, mock_frappe):
        mock_frappe.db.sql.return_value = []
        msg = mpe.explain_missing_blank_bin_issue("26I11X01")
        self.assertEqual(
            msg, "There is no entry for Blank Bin Issue for the scanned lot number.")

    @patch.object(mpe, "frappe")
    def test_all_bins_consumed_says_so_and_names_them(self, mock_frappe):
        """The live case: the issue exists, every item is already completed."""
        mock_frappe.db.sql.return_value = [_row("PE-80280", "BLB -00241", 1)]
        msg = mpe.explain_missing_blank_bin_issue("26I11X01")
        self.assertIn("already marked consumed", msg)
        self.assertIn("BLB -00241", msg)
        self.assertIn("PE-80280", msg)
        self.assertNotIn("There is no entry", msg)

    @patch.object(mpe, "frappe")
    def test_unsubmitted_issue_is_reported_as_unsubmitted(self, mock_frappe):
        mock_frappe.db.sql.return_value = [_row("PE-80999", "BLB -00010", 0, docstatus=0)]
        msg = mpe.explain_missing_blank_bin_issue("26I11X09")
        self.assertIn("has not been submitted", msg)
        self.assertIn("PE-80999", msg)

    @patch.object(mpe, "frappe")
    def test_issue_with_no_job_card_is_reported_as_unlinked(self, mock_frappe):
        """The job_card race: submitted, open, but job_card never resolved."""
        mock_frappe.db.sql.return_value = [_row("PE-79939", "BLB -00233", 0, job_card=None)]
        msg = mpe.explain_missing_blank_bin_issue("26I07Y08")
        self.assertIn("not linked to a Job Card", msg)
        self.assertIn("PE-79939", msg)

    @patch.object(mpe, "frappe")
    def test_a_diagnostic_failure_never_replaces_the_answer(self, mock_frappe):
        mock_frappe.db.sql.side_effect = RuntimeError("db gone")
        msg = mpe.explain_missing_blank_bin_issue("26I11X01")
        self.assertEqual(
            msg, "There is no entry for Blank Bin Issue for the scanned lot number.")
        self.assertTrue(mock_frappe.log_error.called)
