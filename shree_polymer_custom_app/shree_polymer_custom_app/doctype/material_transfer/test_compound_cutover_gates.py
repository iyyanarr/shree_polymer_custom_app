# Copyright (c) 2026, Shree Polymer and contributors
# See license.txt
"""Under the cutover, sheeting accepts ONLY receipted compound.

Legacy stops carrying the mixing chain, so three gates on this screen assume a
world that no longer exists:

  check_compound_inspection  there is no Compound Inspection to find — the
                             compound arrives already approved, and the receipt
                             IS the evidence it passed
  validate_qi                no Quality Inspection is created on Legacy either
  validate_spp_batch_no      must accept ONLY Material Receipt, so the stock the
                             old chain left behind (deliberately frozen) cannot
                             be drawn on

All three stand down together, per site, behind spp_compound_cutover. With the
flag off nothing changes — production keeps the old behaviour while staging runs
the new one.

Run with:
    bench --site spp15.local run-tests --module \
      shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.test_compound_cutover_gates
"""

import unittest
from unittest.mock import MagicMock, patch

from shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer import (
    material_transfer as mt,
)


class TestCutoverFlag(unittest.TestCase):
    @patch.object(mt, "frappe")
    def test_off_by_default(self, mock_frappe):
        mock_frappe.conf.get.return_value = None
        self.assertFalse(mt.compound_cutover_enabled())

    @patch.object(mt, "frappe")
    def test_on_when_the_site_sets_it(self, mock_frappe):
        mock_frappe.conf.get.return_value = 1
        self.assertTrue(mt.compound_cutover_enabled())


class TestCheckCompoundInspection(unittest.TestCase):
    @patch.object(mt, "compound_cutover_enabled", return_value=True)
    @patch.object(mt, "frappe")
    def test_stands_down_under_cutover_without_querying(self, mock_frappe, _flag):
        self.assertFalse(mt.check_compound_inspection("C_26I08X9", "U3-Store - SPP INDIA", "Manufacture"))
        mock_frappe.db.sql.assert_not_called()

    @patch.object(mt, "compound_cutover_enabled", return_value=False)
    @patch.object(mt, "frappe")
    def test_still_runs_with_the_flag_off(self, mock_frappe, _flag):
        mock_frappe.db.sql.return_value = []
        mt.check_compound_inspection("C_26I08X9", "U3-Store - SPP INDIA", "Manufacture")
        mock_frappe.db.sql.assert_called_once()


class TestValidateQi(unittest.TestCase):
    def _doc(self):
        doc = MagicMock()
        row = MagicMock(); row.qc_template = "QI-TEMPLATE"; row.quality_inspection = None
        row.idx = 1; row.item_code = "C_6024"
        doc.batches = [row]
        return doc

    @patch.object(mt, "compound_cutover_enabled", return_value=True)
    @patch.object(mt, "frappe")
    def test_passes_under_cutover(self, mock_frappe, _flag):
        res = mt.validate_qi(self._doc())
        self.assertTrue(res["status"])
        mock_frappe.db.get_value.assert_not_called()

    @patch.object(mt, "compound_cutover_enabled", return_value=False)
    @patch.object(mt, "frappe")
    def test_still_demands_a_qi_with_the_flag_off(self, mock_frappe, _flag):
        mock_frappe.db.get_value.return_value = 0
        res = mt.validate_qi(self._doc())
        self.assertFalse(res["status"])
        self.assertIn("Quality Inspection is required", res["message"])


class TestValidateSppBatchNoAcceptsOnlyReceipts(unittest.TestCase):
    """The clause that blocks the frozen old-chain stock."""

    def _run(self, cutover):
        captured = []
        with patch.object(mt, "compound_cutover_enabled", return_value=cutover), \
             patch.object(mt, "frappe") as mock_frappe:
            mock_frappe.get_single.return_value = MagicMock(default_cut_bit_warehouse="CB - SPP")
            def sql(q, *a, **k):
                captured.append(q)
                return []
            mock_frappe.db.sql.side_effect = sql
            mock_frappe.db.get_value.return_value = None
            try:
                mt.validate_spp_batch_no("C_26I08X9", "U3-Store - SPP INDIA",
                                         "Sheeting Warehouse - SPP INDIA",
                                         "Manufacture", "Transfer Compound to Sheeting Warehouse")
            except Exception:
                pass
        return " ".join(captured)

    def test_under_cutover_only_material_receipt_is_accepted(self):
        sql = self._run(True)
        self.assertIn("S.stock_entry_type = 'Material Receipt'", sql)
        self.assertNotIn("%(type)s", sql)

    def test_with_the_flag_off_the_original_clause_is_unchanged(self):
        sql = self._run(False)
        self.assertIn("%(type)s", sql)
        self.assertIn("Material Receipt", sql)
