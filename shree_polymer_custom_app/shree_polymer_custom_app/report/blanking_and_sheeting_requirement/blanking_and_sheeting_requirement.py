# Copyright (c) 2026, Tridotstech and contributors
# For license information, please see license.txt

import json
import os

import frappe
from frappe import _
from frappe.utils import flt, nowdate


def execute(filters=None):
	columns, data = get_columns(), get_grouped_data(filters or {})
	return columns, data


def get_columns():
	return [
		_("Date") + ":Date:110",
		_("Shift") + ":Data:130",
		_("ID") + ":Link/Work Planning:130",
		_("Press No") + ":Link/Workstation:162",
		_("Product Ref") + ":Link/Item:100",
		_("Mould No") + ":Link/Item:100",
		_("Compound Ref") + ":Link/Item:160",
		_("Blank Type") + ":Data",
		_("Avg Blank Wt Kgs") + ":Float:150",
		_("Avg Lift Wt Kgs") + ":Float:120",
		_("Target Lifts") + ":Float : 95",
		_("Blanking Req Kgs") + ":Float : 150",
		_("Sheeting Req Kgs") + ":Float : 180",
	]


# Presses are stored as free text ("P1 : TUNGYU - 100 Ton"), so a plain sort gives
# P1, P10, P11, P2 ... Order on the digits after the P instead, and park any
# non-numeric station (e.g. "Dot Marker") after the numbered presses.
PRESS_ORDER_SQL = """
		CASE WHEN press_no REGEXP '^P[0-9]+' THEN 0 ELSE 1 END,
		CAST(REGEXP_SUBSTR(press_no, '[0-9]+') AS UNSIGNED),
		press_no
"""


def _build_query(filters):
	condition = ""
	acondition = ""

	if filters.get("press_no"):
		condition += f" AND WPI.work_station = '{filters.get('press_no')}' "
		acondition += f" AND AWPI.work_station = '{filters.get('press_no')}' "
	if filters.get("product_ref"):
		condition += f" AND WPI.item = '{filters.get('product_ref')}' "
		acondition += f" AND AWPI.item = '{filters.get('product_ref')}' "
	if filters.get("mould_number"):
		condition += f" AND WPI.mould = '{filters.get('mould_number')}' "
		acondition += f" AND AWPI.mould = '{filters.get('mould_number')}' "
	if filters.get("compound_ref"):
		condition += f" AND BOMI.item_code = '{filters.get('compound_ref')}' "
		acondition += f" AND ABOMI.item_code = '{filters.get('compound_ref')}' "
	if filters.get("date"):
		condition += f" AND DATE(WP.date) = '{filters.get('date')}' "
		acondition += f" AND DATE(AWP.date) = '{filters.get('date')}' "
	if filters.get("shift"):
		condition += f" AND WP.shift_type = '{filters.get('shift')}' "
		acondition += f" AND AWP.shift_type = '{filters.get('shift')}' "

	compound_query = "(MS.wtlift_avg_gms/1000) * WPIT.target_qty"
	a_compound_query = "(AMS.wtlift_avg_gms/1000) * AWPIT.target_qty"
	spp_settings = frappe.get_single("SPP Settings")
	extra_pct = spp_settings.extra__of_compound_required
	if extra_pct:
		compound_query = (
			f"((MS.wtlift_avg_gms/1000) * WPIT.target_qty)"
			f" + ((((MS.wtlift_avg_gms/1000) * WPIT.target_qty)/100) * {extra_pct})"
		)
		a_compound_query = (
			f"((AMS.wtlift_avg_gms/1000) * AWPIT.target_qty)"
			f" + ((((AMS.wtlift_avg_gms/1000) * AWPIT.target_qty)/100) * {extra_pct})"
		)

	return f"""
		SELECT * FROM (
			SELECT DISTINCT DATE(WP.date) date, WP.shift_type shift,
				WP.name id,
				WPI.work_station press_no,
				WPI.item product_ref,
				WPI.mould mould_no,
				BOMI.item_code AS compound_ref,
				MS.blank_type blank_type,
				CASE
					WHEN MS.wtpiece_avg_gms = 0 THEN 0
					ELSE MS.avg_blank_wtproduct_gms/1000
				END AS avg_blank_wt_kgs,
				CASE
					WHEN MS.wtlift_avg_gms = 0 THEN 0
					ELSE MS.wtlift_avg_gms/1000
				END AS avg_lift_wt_kgs,
				WPIT.target_qty target_lifts,
				CASE
					WHEN MS.wtlift_avg_gms = 0 THEN 0
					ELSE {compound_query}
				END AS blanking_req_kgs
			FROM `tabWork Planning` WP
				INNER JOIN `tabWork Plan Item` WPI ON WPI.parent = WP.name
				INNER JOIN `tabBOM Item` BOMI ON BOMI.parent = WPI.bom
				INNER JOIN `tabItem` I ON I.name = BOMI.item_code AND I.item_group = 'Compound'
				INNER JOIN `tabMould Specification` MS ON MS.mould_ref = WPI.mould
					AND MS.spp_ref = WPI.item AND MS.mould_status = 'ACTIVE'
				INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = WPI.item
					AND WPIT.shift_type = WP.shift_time
			WHERE WP.docstatus = 1 {condition}

			UNION ALL

			SELECT DISTINCT DATE(AWP.date) date, AWP.shift_type shift,
				AWP.name id,
				AWPI.work_station press_no,
				AWPI.item product_ref,
				AWPI.mould mould_no,
				ABOMI.item_code AS compound_ref,
				AMS.blank_type blank_type,
				CASE
					WHEN AMS.wtpiece_avg_gms = 0 THEN 0
					ELSE AMS.avg_blank_wtproduct_gms/1000
				END AS avg_blank_wt_kgs,
				CASE
					WHEN AMS.wtlift_avg_gms = 0 THEN 0
					ELSE AMS.wtlift_avg_gms/1000
				END AS avg_lift_wt_kgs,
				AWPIT.target_qty target_lifts,
				CASE
					WHEN AMS.wtlift_avg_gms = 0 THEN 0
					ELSE {a_compound_query}
				END AS blanking_req_kgs
			FROM `tabAdd On Work Planning` AWP
				INNER JOIN `tabAdd On Work Plan Item` AWPI ON AWPI.parent = AWP.name
				INNER JOIN `tabBOM Item` ABOMI ON ABOMI.parent = AWPI.bom
				INNER JOIN `tabItem` AI ON AI.name = ABOMI.item_code AND AI.item_group = 'Compound'
				INNER JOIN `tabMould Specification` AMS ON AMS.mould_ref = AWPI.mould
					AND AMS.spp_ref = AWPI.item AND AMS.mould_status = 'ACTIVE'
				INNER JOIN `tabWork Plan Item Target` AWPIT ON AWPIT.item = AWPI.item
					AND AWPIT.shift_type = AWP.shift_time
			WHERE AWP.docstatus = 1 {acondition}
		) combined
		ORDER BY {PRESS_ORDER_SQL}, compound_ref, date, shift
	"""


def get_raw_rows(filters):
	return frappe.db.sql(_build_query(filters), as_dict=1)


def _group_by_press(raw, ratio):
	"""Split the rows into press blocks, in the natural press order the query
	already applied, and annotate every row with its sheeting requirement."""
	groups = []
	current = None

	for row in raw:
		row["sheeting_req_kgs"] = flt(flt(row.get("blanking_req_kgs") or 0) * ratio, 3)
		press = row.get("press_no")
		if current is None or current["press_no"] != press:
			current = {"press_no": press, "rows": [], "subtotal": 0.0}
			groups.append(current)
		current["rows"].append(row)
		current["subtotal"] += flt(row.get("blanking_req_kgs") or 0)

	# Subtotals stay at full precision so the grand total is the sum of the raw
	# values, not of pre-rounded ones; callers round for display.
	for g in groups:
		g["sheeting_subtotal"] = g["subtotal"] * ratio

	return groups


def _compound_summary(raw, ratio):
	"""Per-compound totals across every press. The table itself runs press by
	press for the shop floor, so this keeps the mixing room's compound
	quantities available in one place."""
	totals = {}
	for row in raw:
		compound = row.get("compound_ref")
		totals[compound] = totals.get(compound, 0.0) + flt(row.get("blanking_req_kgs") or 0)

	return [
		{
			"compound_ref": compound,
			"blanking_req_kgs": flt(total, 3),
			"sheeting_req_kgs": flt(total * ratio, 3),
		}
		for compound, total in sorted(totals.items())
	]


def get_grouped_data(filters):
	raw = get_raw_rows(filters)
	ratio = _summary_ratio()
	out = []

	for g in _group_by_press(raw, ratio):
		out.extend(g["rows"])
		out.append({
			"press_no": f"Total — {g['press_no']}",
			"blanking_req_kgs": flt(g["subtotal"], 3),
			"sheeting_req_kgs": flt(g["sheeting_subtotal"], 3),
		})

	for c in _compound_summary(raw, ratio):
		out.append({
			"compound_ref": f"Compound Total — {c['compound_ref']}",
			"blanking_req_kgs": c["blanking_req_kgs"],
			"sheeting_req_kgs": c["sheeting_req_kgs"],
		})

	return out


SHEETING_PCT_OVER_BLANKING = 30  # business rule: sheeting requirement is 30% above the blanking requirement


def _summary_ratio():
	# Sheeting requirement = Blanking requirement × 1.30 (i.e., 30% extra on top of the press/blanking
	# value to cover mixing + sheet-trim losses). Fixed business rule — does NOT derive from
	# SPP Settings.extra__of_compound_required (which only governs the blanking buffer).
	return 1.0 + (SHEETING_PCT_OVER_BLANKING / 100.0)


@frappe.whitelist()
def get_print_html(filters=None):
	if isinstance(filters, str):
		filters = json.loads(filters)
	filters = filters or {}

	raw = get_raw_rows(filters)
	ratio = _summary_ratio()

	groups = _group_by_press(raw, ratio)
	compound_summary = _compound_summary(raw, ratio)

	grand_total = sum(g["subtotal"] for g in groups)
	sheeting_grand_total = flt(grand_total * ratio, 3)

	report_doc = frappe.get_cached_doc("Report", "Blanking And Sheeting Requirement")
	letter_head_name = report_doc.letter_head or "Purchase Order"
	letter_head_content = (
		frappe.db.get_value("Letter Head", letter_head_name, "content") or ""
	)

	template_path = os.path.join(
		os.path.dirname(__file__), "blanking_and_sheeting_requirement.html"
	)
	with open(template_path) as fh:
		template = fh.read()

	return frappe.render_template(
		template,
		{
			"letter_head": letter_head_content,
			"filters": filters,
			"groups": groups,
			"compound_summary": compound_summary,
			"grand_total": flt(grand_total, 3),
			"sheeting_grand_total": sheeting_grand_total,
			"printed_on": nowdate(),
		},
	)


@frappe.whitelist()
def get_filter_pressno(doctype, press_no, searchfield, start, page_len, filters):
	return frappe.db.sql(""" SELECT work_station FROM `tabWork Plan Station` """)


@frappe.whitelist()
def get_filter_product_ref(doctype, product_ref, searchfield, start, page_len, filters):
	search_condition = ""
	if product_ref:
		search_condition = " AND I.name like '%" + product_ref + "%'"
	itemgroup = frappe.db.get_single_value("SPP Settings", "item_group")
	return frappe.db.sql(
		f""" SELECT I.name FROM `tabItem` I
			WHERE I.item_group = '{itemgroup}' {search_condition} """
	)


@frappe.whitelist()
def get_filter_mould_number(doctype, mould_number, searchfield, start, page_len, filters):
	search_condition = ""
	if mould_number:
		search_condition = " AND I.name LIKE '%" + mould_number + "%'"
	mould_group = frappe.db.get_single_value("SPP Settings", "mould_item_group")
	return frappe.db.sql(
		f""" SELECT I.name FROM `tabItem` I
			WHERE I.item_group = '{mould_group}' {search_condition} """
	)


@frappe.whitelist()
def get_filter_compound_ref(doctype, compound_ref, searchfield, start, page_len, filters):
	search_condition = ""
	if compound_ref:
		search_condition = "AND I.name LIKE '%" + compound_ref + "%'"
	return frappe.db.sql(
		f""" SELECT I.name FROM `tabItem` I
			WHERE I.item_group = 'Compound' {search_condition} """
	)
