# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

def execute(filters=None):
	columns, data = get_columns(),get_datas(filters)
	return columns, data

def get_columns():
	col__ = []
	col__.append(_("Date")+":Date:100")
	col__.append(_("Compound Ref")+":Link/Item:120")
	col__.append(_("Batch No")+":Data:120")
	# col__.append(_("Cavity No")+":Int:90")
	col__.append(_("Hardness Min")+":Float:120")
	col__.append(_("Hardness Max")+":Float:120")
	col__.append(_("Hardness Observed")+":Float:150")
	col__.append(_("SG Min")+":Float:110")
	col__.append(_("SG Max")+":Float:110")
	col__.append(_("SG Observed")+":Float:120")
	col__.append(_("TS2 Min")+":Float:110")
	col__.append(_("TS2 Max")+":Float:110")
	col__.append(_("TS2 Observed")+":Float:120")
	col__.append(_("TC90 Min")+":Float:110")
	col__.append(_("TC90 Max")+":Float:110")
	col__.append(_("TC90 Observed")+":Float:130")
	col__.append(_("Result")+":Data:70")
	col__.append(_("Maturation Approved By")+":Link/Employee:180")
	col__.append(_("Quality Approved By")+":Link/Employee:160")
	col__.append(_("Maturation Approver Remarks")+":Data:250")
	col__.append(_("Quality Approver Remarks")+":Data:250")
	return col__

def get_datas(filters):
	condition = ""
	if filters.get('compound_ref'):
		condition += f" AND CINSP.compound_ref = '{filters.get('compound_ref')}' "

	if filters.get('from_date'):
		condition += f" AND DATE(CINSP.posting_date) >= '{getdate(filters.get('from_date'))}' "	
	if filters.get('to_date'):
		condition += f" AND DATE(CINSP.posting_date) <= '{getdate(filters.get('to_date'))}' "
	if filters.get('batch_no'):
		condition += f" AND CINSP.batch_no LIKE '%{filters.get('batch_no')}%' "
	
	query = f""" SELECT 
					DATE(CINSP.posting_date) date,CINSP.compound_ref,CINSP.batch_no,CINSP.cavity_no,
					CINSP.min_hardness hardness_min,CINSP.max_hardness hardness_max,
						CASE
							WHEN CINSP.no_enough_hardness
								THEN CINSP.q_hardness_observed
							ELSE
								CINSP.hardness_observed
					END hardness_observed,
					CINSP.sg_min,CINSP.sg_max,
						CASE
							WHEN CINSP.no_enough_sg
								THEN CINSP.q_sg_observed
							ELSE
								CINSP.sg_observed
					END sg_observed,
					CINSP.ts2_min,CINSP.ts2_max,
						CASE
							WHEN CINSP.no_enough_ts2
								THEN CINSP.q_ts2_observed
							ELSE
								CINSP.ts2_observed
					END ts2_observed,
					CINSP.tc_90_min tc90_min,CINSP.tc_90_max tc90_max,
						CASE
							WHEN CINSP.no_enough_tc90
								THEN CINSP.q_tc_90_observed
							ELSE
								CINSP.tc_90_observed
					END tc90_observed,
					CASE
						WHEN (CINSP.no_enough_aging OR CINSP.no_enough_hardness OR CINSP.no_enough_sg 
							OR CINSP.no_enough_ts2 OR CINSP.no_enough_tc90)
							THEN "FAIL" 
						ELSE
							'PASS' 
					END result,
					CASE
						WHEN CINSP.no_enough_aging 
							THEN CINSP.approver_id
						ELSE
							'  -' 
					END maturation_approved_by,
					CASE
						WHEN (CINSP.no_enough_hardness OR CINSP.no_enough_sg 
							OR CINSP.no_enough_ts2 OR CINSP.no_enough_tc90)
							THEN CINSP.quality_approver_id
						ELSE
							'  -' 
					END quality_approved_by, 
					CASE
						WHEN (CINSP.m_remarks IS NULL 
							OR CINSP.m_remarks = '')
							THEN ' -'
						ELSE
							CINSP.m_remarks
					END maturation_approver_remarks,
					CASE
						WHEN (CINSP.q_remarks IS NULL 
							OR CINSP.q_remarks = '')
							THEN ' -'
						ELSE
							CINSP.q_remarks
					END quality_approver_remarks
				FROM `tabCompound Inspection` CINSP 
				WHERE CINSP.docstatus = 1 {condition} """
	resp_ = frappe.db.sql(query,as_dict = 1)
	if resp_:
		resp_.append({"batch_no":"<b>Average</b>",
			"hardness_min":(sum(float(x.hardness_min) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"hardness_max":(sum(float(x.hardness_max) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"hardness_observed":(sum(float(x.hardness_observed) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"sg_min":(sum(float(x.sg_min) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"sg_max":(sum(float(x.sg_max) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"sg_observed":(sum(float(x.sg_observed) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"ts2_min":(sum(float(x.ts2_min) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"ts2_max":(sum(float(x.ts2_max) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"ts2_observed":(sum(float(x.ts2_observed) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"tc90_min":(sum(float(x.tc90_min) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"tc90_max":(sum(float(x.tc90_max) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0,
			"tc90_observed":(sum(float(x.tc90_observed) if x.hardness_min else 0.0 for x in resp_) / len(resp_)) if resp_ else 0
				})
	return resp_

@frappe.whitelist()
def get_filter_compound_ref(doctype, compound_ref, searchfield, start, page_len, filters):
	search_condition = ""
	if compound_ref:
		search_condition = "AND I.name LIKE '%"+compound_ref+"%'"
	query = f""" SELECT I.name FROM `tabItem` I
	 		 WHERE I.item_group = 'Compound' {search_condition} """
	compounds = frappe.db.sql(query)
	return compounds
