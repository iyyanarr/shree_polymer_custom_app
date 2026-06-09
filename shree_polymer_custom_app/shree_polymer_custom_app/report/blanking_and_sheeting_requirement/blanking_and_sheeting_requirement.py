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
		ORDER BY compound_ref, date, shift, press_no
	"""


def get_raw_rows(filters):
	return frappe.db.sql(_build_query(filters), as_dict=1)


def get_grouped_data(filters):
	raw = get_raw_rows(filters)
	ratio = _summary_ratio()
	out = []
	current_compound = None
	subtotal = 0.0

	def emit_subtotal(label):
		out.append({
			"date": None,
			"shift": None,
			"id": None,
			"press_no": None,
			"product_ref": None,
			"mould_no": None,
			"compound_ref": f"Total — {label}",
			"blank_type": None,
			"avg_blank_wt_kgs": None,
			"avg_lift_wt_kgs": None,
			"target_lifts": None,
			"blanking_req_kgs": flt(subtotal, 3),
			"sheeting_req_kgs": flt(subtotal * ratio, 3),
		})

	for row in raw:
		compound = row.get("compound_ref")
		if current_compound is None:
			current_compound = compound
		if compound != current_compound:
			emit_subtotal(current_compound)
			current_compound = compound
			subtotal = 0.0
		row["sheeting_req_kgs"] = flt(flt(row.get("blanking_req_kgs") or 0) * ratio, 3)
		out.append(row)
		subtotal += flt(row.get("blanking_req_kgs") or 0)

	if current_compound is not None:
		emit_subtotal(current_compound)

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

	groups = []
	current = None
	for row in raw:
		compound = row.get("compound_ref")
		if current is None or current["compound_ref"] != compound:
			current = {"compound_ref": compound, "rows": [], "subtotal": 0.0}
			groups.append(current)
		current["rows"].append(row)
		current["subtotal"] += flt(row.get("blanking_req_kgs") or 0)

	for g in groups:
		g["sheeting_subtotal"] = flt(g["subtotal"] * ratio, 3)

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
