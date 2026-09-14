# Copyright (c) 2026, Shree Polymer and contributors
# For license information, please see license.txt
"""Resolve the ONE Item Bin Mapping a bin operation must act on.

Four places in this app draw down a bin's mapping. Two do it correctly, keyed on
the specific mapping row the scan resolved:

    blank_bin_inward_entry.asset_movement   UPDATE ... WHERE name = ibm_id
    moulding_production_entry (on_submit)   UPDATE ... WHERE name = item_bin_mapping_name

Two did not. They searched by COMPOUND ALONE, took row [0] with no ORDER BY, and
so retired or decremented an arbitrary live mapping belonging to some other bin:

    cut_bit_transfer                        filters={"compound": x.item_code, "is_retired": 0}
    blank_bin_rejection_entry               filters={"compound": self.item,   "is_retired": 0}

Both already know their bin - Cut Bit Transfer scans it into `scan_clip__bin`,
Blank Bin Rejection holds it in `bin_code` - so the bin was available and simply
unused.

Blast radius on production, 05-12 Sep 2026: 162 successful legacy cut-bit
transfers, against compounds that live in many bins at once - C_6122 in 45,
C_70103 in 19, C_69221 in 16, and 25 compounds in more than one bin. A C_6122
cut-bit had roughly a 1-in-45 chance of touching the bin it was actually about.

This is the WRITE-side twin of the hazard custom_app #13 named on the read side
("the moulding check reads whichever one MariaDB returns first"). A guard was
added there; here the same non-determinism is corrupting the data.
"""

import frappe


def resolve_bin_asset(scanned):
    """Asset name for a scanned bin, whether the scan is the name or the barcode."""
    if not scanned:
        return None
    scanned = str(scanned).strip()
    if frappe.db.exists("Asset", scanned):
        return scanned
    return frappe.db.get_value("Asset", {"barcode_text": scanned}, "name")


def resolve_live_bin_mapping(scanned_bin, compound=None, spp_batch_number=None):
    """The live Item Bin Mapping this operation must act on, or None.

    Narrowed hardest-first, using whatever the caller actually has:

        bin + compound + batch   most precise
        compound + batch         when no bin is available
        (compound alone)         REFUSED - that is the bug this replaces

    Ordered by creation so the answer is deterministic rather than whatever
    MariaDB happens to return first.

    A bin is NOT always available. Bridge-created Cut Bit Transfers leave
    scan_clip__bin empty - verified on production, CBT-25185 and CBT-25186
    (12 Sep 2026, transfer_from="Blanking", scan_clip__bin=None) - so requiring
    one would silently stop the draw-down those entries are supposed to do.
    Their item rows do carry spp_batch_no, which narrows to the bins holding one
    sheeting batch (3 for 26I08X23-1) instead of every bin holding the compound
    (46 for C_6122).

    Returns None when nothing narrower than the compound is available. The
    caller must then do NOTHING: drawing down an arbitrary bin is worse than
    skipping, because the bin hit belongs to a different lot entirely.
    """
    filters = {"is_retired": 0}
    asset = resolve_bin_asset(scanned_bin)
    if asset:
        filters["blanking__bin"] = asset
    if compound:
        filters["compound"] = compound
    if spp_batch_number:
        filters["spp_batch_number"] = spp_batch_number

    # Compound alone is exactly the defect being removed - never fall back to it.
    if "blanking__bin" not in filters and "spp_batch_number" not in filters:
        return None

    rows = frappe.db.get_all(
        "Item Bin Mapping", filters=filters, fields=["name", "qty"],
        order_by="creation desc", limit_page_length=1,
    )
    if rows:
        return rows[0]
    # A bin was named but holds nothing matching: do not widen the search.
    return None


def draw_down_bin_mapping(mapping, qty):
    """Retire the mapping when the draw empties it, else reduce it.

    Mirrors what cut_bit_transfer and blank_bin_rejection_entry already did, with
    the row now correctly identified. A draw LARGER than the mapping holds is
    left alone and recorded - it means the two disagree about the bin, and
    silently zeroing it would hide that.
    """
    if not mapping:
        return
    held, drawn = frappe.utils.flt(mapping.get("qty")), frappe.utils.flt(qty)
    if held == drawn:
        frappe.db.set_value("Item Bin Mapping", mapping["name"], "is_retired", 1)
    elif held > drawn:
        frappe.db.set_value("Item Bin Mapping", mapping["name"], "qty", held - drawn)
    else:
        frappe.log_error(
            title="Bin draw larger than the mapping holds",
            message=("Item Bin Mapping {0} holds {1} but the entry drew {2}. Left "
                     "untouched - the bin record and the entry disagree."
                     .format(mapping["name"], held, drawn)),
        )
