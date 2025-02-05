# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = get_columns(filters), get_datas(filters)
	return columns, data

def get_columns(filters):
	col__ = []
	# col__.append(_("Date") + ":Date:100")
	if filters.get('group_by'):
		if filters.get('group_by') == "Mat Product":
			col__.append(_("SPP Ref") + ":Link/Item:80")
		elif filters.get('group_by') == "Compound":
			col__.append(_("Compound Code") + ":Link/Item:130")
		elif filters.get('group_by') == "Shift":
			col__.append(_("Shift") + ":Link/Shift Type:130")
		elif filters.get('group_by') == "Mould":
			col__.append(_("Mould") + ":Data:180")
		elif filters.get('group_by') == "Press":
			col__.append(_("Press") + ":Link/Workstation:180")
		elif filters.get('group_by') == "Operator":
			col__.append(_("Operator") + ":Link/Employee:120")
	col__.append(_("Line Rejection") + ":Percent:120")
	col__.append(_("Lot Rejection") + ":Percent:120")
	col__.append(_("NOC") + ":Int:60")
	col__.append(_("NOL") + ":Int:60")
	col__.append(_("Total Produced weight") + ":Float:170")
	col__.append(_("Total Produced Qty Nos") + ":Int:180")
	col__.append(_("Theoretical Produced Qty Nos") + ":Int:180")
	col__.append(_("Variance Nos") + ":Int:180")
	return col__

def get_datas(filters):
	condition = ""
	group_by = ""
	select_query = ""
	if filters.get('group_by'):
		if filters.get('group_by') == "Mat Product":
			group_by = f" GROUP BY JC.production_item"
			select_query = f" ,JC.production_item spp_ref"
		elif filters.get('group_by') == "Compound":
			group_by = f" GROUP BY MPE.compound"
			select_query = f" ,MPE.compound compound_code"
		elif filters.get('group_by') == "Shift":
			group_by = f" GROUP BY JC.shift_type"
			select_query = f" ,JC.shift_type shift"
		elif filters.get('group_by') == "Mould":
			group_by = f" GROUP BY asset.asset_name"
			select_query = f" ,asset.asset_name mould"
		elif filters.get('group_by') == "Press":
			group_by = f" GROUP BY JC.workstation"
			select_query = f" ,JC.workstation press"
		elif filters.get('group_by') == "Operator":
			group_by = f" GROUP BY MPE.employee"
			select_query = f" ,MPE.employee operator"
	if filters.get('from_date'):
		condition += f" AND DATE(MPE.moulding_date) >= '{filters.get('from_date')}' "
	if filters.get('to_date'):
		condition += f" AND DATE(MPE.moulding_date) <= '{filters.get('to_date')}' "
	if filters.get('operator'):
		condition += f" AND MPE.employee = '{filters.get('operator')}' "
	if filters.get('shift'):
		condition += f" AND JC.shift_type = '{filters.get('shift')}' "
	if filters.get('press'):
		condition += f" AND JC.workstation = '{filters.get('press')}' "
	if filters.get('mould'):
		condition += f" AND asset.asset_name = '{filters.get('mould')}' "
	if filters.get('product_ref'):
		condition += f" AND JC.production_item = '{filters.get('product_ref')}' "
	if filters.get('compound_ref'):
		condition += f" AND MPE.compound = '{filters.get('compound_ref')}' "

	query = f"""SELECT
					DATE(MPE.moulding_date) date,
						ROUND(((SUM(LIE.total_rejected_qty_kg) / SUM(LIE.total_inspected_qty)) * 100),3)
					AS line_rejection,
						SUM(LIE.total_rejected_qty_kg)
					AS line_rejected_qty,
						SUM(LIE.total_inspected_qty)
					AS line_inspected_qty,
						ROUND(((SUM(LOIE.total_rejected_qty_kg) / SUM(LOIE.total_inspected_qty)) * 100),3)
					AS lot_rejection,
						SUM(LOIE.total_rejected_qty_kg) 
					AS lot_rejected_qty,
						SUM(LOIE.total_inspected_qty) 
					AS lot_inspected_qty,
						SUM(JC.no_of_running_cavities) 
					noc,
						SUM(JC.number_of_lifts) 
					nol,
						SUM(SED.qty) 
					total_produced_weight,
						SUM(SED.qty)/(MS.avg_blank_wtproduct_gms/1000)
					total_produced_qty_nos,
						ROUND(SUM(WPIT.target_qty) * MS.noof_cavities)
					theoretical_produced_qty_nos,
						ROUND((SUM(WPIT.target_qty) * MS.noof_cavities) - (SUM(MPE.number_of_lifts) * SUM(MPE.no_of_running_cavities)))
					variance_nos {select_query}
				FROM 
					`tabMoulding Production Entry` MPE 
					INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card
					INNER JOIN `tabInspection Entry` LIE ON LIE.lot_no = MPE.scan_lot_number 
						AND LIE.inspection_type = "Line Inspection"
					INNER JOIN `tabInspection Entry` LOIE ON LOIE.lot_no = MPE.scan_lot_number 
						AND LOIE.inspection_type = "Lot Inspection"
					INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
													AND SED.item_code = JC.production_item
					INNER JOIN `tabAsset` asset ON asset.name = JC.mould_reference
					INNER JOIN `tabMould Specification` MS ON MS.mould_ref = asset.item_code
								AND MS.spp_ref = MPE.item_to_produce AND MS.mould_status = 'ACTIVE'
					INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = JC.production_item 
							AND WPIT.shift_type = JC.shift_time
				WHERE 
					MPE.docstatus = 1 
					AND JC.docstatus = 1
					AND asset.docstatus = 1
					AND LIE.docstatus = 1
					AND LOIE.docstatus = 1
					AND SED.docstatus = 1
					{condition}
				{group_by} """
	# frappe.log_error(title='summary report query',message=query)
	resp__ = frappe.db.sql(query,as_dict = 1)
	calculate_total_rejection(resp__)
	return resp__

def calculate_total_rejection(resp__):
	if resp__:
		total_line_inspected_qty = sum(k.line_inspected_qty if k.line_inspected_qty else 0.0 for k in resp__)
		total_line_rejection_qty = sum(k.line_rejected_qty if k.line_rejected_qty else 0.0 for k in resp__)
		__total_line_rejection =  (total_line_rejection_qty / total_line_inspected_qty) * 100
		total_lot_inspected_qty = sum(k.lot_inspected_qty if k.lot_inspected_qty else 0.0 for k in resp__)
		total_lot_rejection_qty = sum(k.lot_rejected_qty if k.lot_rejected_qty else 0.0 for k in resp__)
		__total_lot_rejection = (total_lot_rejection_qty / total_lot_inspected_qty) * 100
		total_nol = sum(k.nol if k.nol else 0 for k in resp__)
		total_noc = sum(k.noc if k.noc else 0 for k in resp__)
		total_produced_qty_kgs = flt(sum(k.total_produced_weight if k.total_produced_weight else 0.0 for k in resp__),3)
		total_produced_qty_nos = sum(k.total_produced_qty_nos if k.total_produced_qty_nos else 0 for k in resp__)
		theoretical_produced_qty_nos = sum(k.theoretical_produced_qty_nos if k.theoretical_produced_qty_nos else 0 for k in resp__)
		variance_nos = sum(k.variance_nos if k.variance_nos else 0 for k in resp__)
		resp__.append({"batch_code":"<b>Total</b>","total_produced_weight":total_produced_qty_kgs,"total_produced_qty_nos":total_produced_qty_nos,"noc":total_noc,"nol":total_nol,
		 				"line_rejection":__total_line_rejection,"lot_rejection":__total_lot_rejection,
						"theoretical_produced_qty_nos":theoretical_produced_qty_nos,"variance_nos":variance_nos})

@frappe.whitelist()
def get_moulds(doctype, mould, searchfield, start, page_len, filters):
	search_condition = ""
	if mould:
		search_condition = " AND I.name LIKE '%"+mould+"%'"
	mould_group = frappe.db.get_single_value("SPP Settings","mould_item_group")
	query = f""" SELECT I.name FROM `tabItem` I
				WHERE I.item_group = '{mould_group}' {search_condition}
			"""
	mould = frappe.db.sql(query)
	return mould

@frappe.whitelist()
def get_moulding_operator_info(doctype, operator, searchfield, start, page_len, filters):
	condition = ''
	for k in filters.get('designation').split(','):
		condition += f"'{k}',"
	condition = condition[:-1]
	filters['designation'] = condition
	search_condition = ""
	if operator:
		search_condition = " AND EMP.name LIKE '%"+operator+"%'"
	query = f""" SELECT EMP.name,EMP.employee_name FROM `tabEmployee` EMP WHERE EMP.designation IN (SELECT SPPDM.designation FROM `tabSPP Designation Mapping` SPPDM
					WHERE SPPDM.parent = 'SPP Settings' AND SPPDM.spp_process IN ({filters.get('designation')}) ) {search_condition}
			"""
	operator = frappe.db.sql(query)
	return operator

@frappe.whitelist()
def get_press_info(doctype, press, searchfield, start, page_len, filters):
	search_condition = ""
	if press:
		search_condition = " AND WSP.work_station LIKE '%"+press+"%'"
	query = f""" SELECT WPS.work_station FROM `tabWork Plan Station` WPS
					WHERE WPS.parent = 'SPP Settings' {search_condition}
			"""
	press = frappe.db.sql(query)
	return press

@frappe.whitelist()
def get_filter_compound_ref(doctype, compound_ref, searchfield, start, page_len, filters):
	search_condition = ""
	if compound_ref:
		search_condition = "AND I.name LIKE '%"+compound_ref+"%'"
	query = f""" SELECT I.name FROM `tabItem` I
	 		 WHERE I.item_group = 'Compound' {search_condition} """
	compounds = frappe.db.sql(query)
	return compounds

@frappe.whitelist()
def get_filter_product_ref(doctype, product_ref, searchfield, start, page_len, filters):
	search_condition = ""
	if product_ref:
		search_condition = " AND I.name like '%"+product_ref+"%'"
	itemgroup = frappe.db.get_single_value("SPP Settings","item_group")
	query = f""" SELECT I.name FROM `tabItem` I 
				WHERE  I.item_group = '{itemgroup}' {search_condition} """
	product_ref = frappe.db.sql(query)
	return product_ref



# def get_datas(filters):
# 	condition = ""
# 	# group_by = """ GROUP BY
# 	# 				MPE.moulding_date """
# 	group_by = """ GROUP BY
# 					JC.production_item """
# 	select_query = ""
# 	if filters.get('group_by'):
# 		if filters.get('group_by') == "Mat Product":
# 			# group_by += f" ,JC.production_item"
# 			select_query += f" ,JC.production_item spp_ref"
# 		elif filters.get('group_by') == "Compound":
# 			group_by += f" ,MPE.compound"
# 			select_query += f" ,MPE.compound compound_code"
# 		elif filters.get('group_by') == "Shift":
# 			group_by += f" ,JC.shift_type"
# 			select_query += f" ,JC.shift_type shift"
# 		elif filters.get('group_by') == "Mould":
# 			group_by += f" ,asset.asset_name"
# 			select_query += f" ,asset.asset_name mould"
# 		elif filters.get('group_by') == "Press":
# 			group_by += f" ,JC.workstation"
# 			select_query += f" ,JC.workstation press"
# 		elif filters.get('group_by') == "Operator":
# 			group_by += f" ,MPE.employee"
# 			select_query += f" ,MPE.employee operator"
# 	if filters.get('from_date'):
# 		condition += f" AND DATE(MPE.moulding_date) >= '{filters.get('from_date')}' "
# 	if filters.get('to_date'):
# 		condition += f" AND DATE(MPE.moulding_date) <= '{filters.get('to_date')}' "
# 	if filters.get('operator'):
# 		condition += f" AND MPE.employee = '{filters.get('operator')}' "
# 	if filters.get('shift'):
# 		condition += f" AND JC.shift_type = '{filters.get('shift')}' "
# 	if filters.get('press'):
# 		condition += f" AND JC.workstation = '{filters.get('press')}' "
# 	if filters.get('mould'):
# 		condition += f" AND asset.asset_name = '{filters.get('mould')}' "
# 	if filters.get('product_ref'):
# 		condition += f" AND JC.production_item = '{filters.get('product_ref')}' "
# 	if filters.get('compound_ref'):
# 		condition += f" AND MPE.compound = '{filters.get('compound_ref')}' "

# 	query = f"""SELECT
# 					DATE(MPE.moulding_date) date,
# 						ROUND(((SUM(LIE.total_rejected_qty_kg) / SUM(LIE.total_inspected_qty)) * 100),3)
# 					AS line_rejection,
# 						SUM(LIE.total_rejected_qty_kg)
# 					AS line_rejected_qty,
# 						SUM(LIE.total_inspected_qty)
# 					AS line_inspected_qty,
# 						ROUND(((SUM(LOIE.total_rejected_qty_kg) / SUM(LOIE.total_inspected_qty)) * 100),3)
# 					AS lot_rejection,
# 						SUM(LOIE.total_rejected_qty_kg) 
# 					AS lot_rejected_qty,
# 						SUM(LOIE.total_inspected_qty) 
# 					AS lot_inspected_qty,
# 						SUM(JC.no_of_running_cavities) 
# 					noc,
# 						SUM(JC.number_of_lifts) 
# 					nol,
# 						SUM(SED.qty) 
# 					total_produced_weight,
# 						SUM(SED.qty)/(MS.avg_blank_wtproduct_gms/1000)
# 					total_produced_qty_nos,
# 						SUM(CAST(WPIT.target_qty AS INTEGER)) * CAST(MS.noof_cavities AS INTEGER)
# 					theoretical_produced_qty_nos,
# 						(SUM(CAST(WPIT.target_qty AS INTEGER)) * CAST(MS.noof_cavities AS INTEGER)) - (SUM(CAST(MPE.number_of_lifts AS INTEGER)) * SUM(CAST(MPE.no_of_running_cavities AS INTEGER)))
# 					variance_nos {select_query}
# 				FROM 
# 					`tabMoulding Production Entry` MPE 
# 					INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card
# 					INNER JOIN `tabInspection Entry` LIE ON LIE.lot_no = MPE.scan_lot_number 
# 						AND LIE.inspection_type = "Line Inspection"
# 					INNER JOIN `tabInspection Entry` LOIE ON LOIE.lot_no = MPE.scan_lot_number 
# 						AND LOIE.inspection_type = "Lot Inspection"
# 					INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
# 													AND SED.item_code = JC.production_item
# 					INNER JOIN `tabAsset` asset ON asset.name = JC.mould_reference
# 					INNER JOIN `tabMould Specification` MS ON MS.mould_ref = asset.item_code
# 								AND MS.spp_ref = MPE.item_to_produce AND MS.mould_status = 'ACTIVE'
# 					INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = JC.production_item 
# 							AND WPIT.shift_type = JC.shift_time
# 				WHERE 
# 					MPE.docstatus = 1 
# 					AND JC.docstatus = 1
# 					AND asset.docstatus = 1
# 					AND LIE.docstatus = 1
# 					AND LOIE.docstatus = 1
# 					AND SED.docstatus = 1
# 					{condition}
# 				{group_by} """
# 	frappe.log_error(title='------',message=query)
# 	resp__ = frappe.db.sql(query,as_dict = 1)
# 	calculate_total_rejection(resp__)
# 	return resp__




# query = f"""SELECT
# 					DATE(MPE.moulding_date) date,
# 						SUM(CAST(LIE.total_rejected_qty_in_percentage as decimal(10,3))) 
# 					AS line_rejection,
# 						SUM(LIE.total_rejected_qty_kg)
# 					AS line_rejected_qty,
# 						SUM(LIE.total_inspected_qty)
# 					AS line_inspected_qty,
# 						SUM(CAST(LOIE.total_rejected_qty_in_percentage as decimal(10,3))) 
# 					AS lot_rejection,
# 						SUM(LOIE.total_rejected_qty_kg) 
# 					AS lot_rejected_qty,
# 						SUM(LOIE.total_inspected_qty) 
# 					AS lot_inspected_qty,
# 						SUM(JC.no_of_running_cavities) 
# 					noc,
# 						SUM(JC.number_of_lifts) 
# 					nol,
# 						SUM(SED.qty) 
# 					total_produced_weight,
# 						SUM(SED.qty)/(MS.avg_blank_wtproduct_gms/1000)
# 					total_produced_qty_nos,
# 						SUM(CAST(WPIT.target_qty AS INTEGER)) * CAST(MS.noof_cavities AS INTEGER)
# 					theoretical_produced_qty_nos,
# 						(CAST(WPIT.target_qty AS INTEGER) * CAST(MS.noof_cavities AS INTEGER)) - (SUM(CAST(MPE.number_of_lifts AS INTEGER)) * SUM(CAST(MPE.no_of_running_cavities AS INTEGER)))
# 					variance_nos {select_query}
# 				FROM 
# 					`tabMoulding Production Entry` MPE 
# 					INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card
# 					INNER JOIN `tabInspection Entry` LIE ON LIE.lot_no = MPE.scan_lot_number 
# 						AND LIE.inspection_type = "Line Inspection"
# 					INNER JOIN `tabInspection Entry` LOIE ON LOIE.lot_no = MPE.scan_lot_number 
# 						AND LOIE.inspection_type = "Lot Inspection"
# 					INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
# 													AND SED.item_code = JC.production_item
# 					INNER JOIN `tabAsset` asset ON asset.name = JC.mould_reference
# 					INNER JOIN `tabMould Specification` MS ON MS.mould_ref = asset.item_code
# 								AND MS.spp_ref = MPE.item_to_produce AND MS.mould_status = 'ACTIVE'
# 					INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = JC.production_item 
# 							AND WPIT.shift_type = JC.shift_time
# 				WHERE 
# 					MPE.docstatus = 1 
# 					AND JC.docstatus = 1
# 					AND asset.docstatus = 1
# 					AND LIE.docstatus = 1
# 					AND LOIE.docstatus = 1
# 					AND SED.docstatus = 1
# 					{condition}
# 				{group_by} """




# INNER JOIN `tabWork Plan Item` WPI ON WPI.job_card = JC.name
# 					INNER JOIN `tabWork Planning` WP ON WP.name = WPI.parent

# query = f"""SELECT
# 					DATE(MPE.modified) date,
# 					JC.shift_number shift,asset.asset_name mould,
# 					JC.workstation press,JC.batch_code pcard,
# 					MPE.employee operator,JC.production_item spp_ref,
# 					BOI.item_code compound_code,SED.spp_batch_number batch_code,
# 						SUM(CAST(LIE.total_rejected_qty_kg/(SED.qty/100) as decimal(10,3))) 
# 					AS line_rejection,
# 						SUM(CAST(LOIE.total_rejected_qty_kg/(SED.qty/100) as decimal(10,3))) 
# 					AS lot_rejection,
# 						SUM(JC.no_of_running_cavities) 
# 					noc,
# 						SUM(JC.number_of_lifts) 
# 					nol,
# 						SUM(SED.qty) - (SUM(LIE.total_rejected_qty_kg) + SUM(LOIE.total_rejected_qty_kg)) 
# 					total_produced_weight,
# 						(SUM(SED.qty) - (SUM(LIE.total_rejected_qty_kg) 
# 							+ SUM(LOIE.total_rejected_qty_kg))) * 1000 / MS.avg_blank_wtproduct_gms 
# 					total_produced_qty_nos,
# 						SUM(CAST(WPIT.target_qty AS INTEGER)) * SUM(CAST(MS.noof_cavities AS INTEGER))
# 					theoretical_produced_qty_nos,
# 						(SUM(CAST(WPIT.target_qty AS INTEGER)) * SUM(CAST(MS.noof_cavities AS INTEGER))) - (SUM(CAST(MPE.number_of_lifts AS INTEGER)) * SUM(CAST(MPE.no_of_running_cavities AS INTEGER)))
# 					variance_nos
# 				FROM 
# 					`tabMoulding Production Entry` MPE 
# 					INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card
# 					INNER JOIN `tabInspection Entry` LIE ON LIE.lot_no = MPE.scan_lot_number 
# 						AND LIE.inspection_type = "Line Inspection"
# 					INNER JOIN `tabInspection Entry` LOIE ON LOIE.lot_no = MPE.scan_lot_number 
# 						AND LOIE.inspection_type = "Lot Inspection"
# 					INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference
# 					INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 					INNER JOIN `tabBOM Item` BOI ON BOI.parent = JC.bom_no
# 					INNER JOIN `tabItem` I ON I.name = BOI.item_code AND I.item_group = 'Compound'
# 					INNER JOIN `tabAsset` asset ON asset.name = JC.mould_reference
# 					INNER JOIN `tabMould Specification` MS ON MS.mould_ref = asset.item_code
# 					INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = JC.production_item
# 				WHERE 
# 					MPE.docstatus = 1 
# 					AND JC.docstatus = 1
# 					AND asset.docstatus = 1
# 					AND LIE.docstatus = 1
# 					AND LOIE.docstatus = 1
# 					AND SE.docstatus = 1
# 					AND SED.item_code = JC.production_item
# 					{condition}
# 				GROUP BY
# 					shift,press,operator,mould,compound_code,spp_ref """

	# query = f"""SELECT
	# 				DATE(MPE.modified) date,
	# 				JC.shift_number shift,
	# 				asset.name mould,
	# 				JC.workstation press,
	# 				JC.batch_code pcard,
	# 				MPE.employee operator,
	# 				JC.production_item spp_ref,
	# 				BOI.item_code compound_code,
	# 				SED.spp_batch_number batch_code,
	# 				SUM(CASE
	# 					WHEN IE.inspection_type = 'Line Inspection' THEN CAST(IE.total_rejected_qty_kg/SED.qty*100 as decimal(10,2))
	# 					ELSE 0
	# 				END) AS line_rejection,
	# 				SUM(CASE
	# 					WHEN IE.inspection_type = 'Lot Inspection' THEN CAST(IE.total_rejected_qty_kg/SED.qty*100 as decimal(10,2))
	# 					ELSE 0
	# 				END) AS lot_rejection,
	# 				SUM(CASE
	# 					WHEN IE.inspection_type = 'Lot Inspection' THEN JC.no_of_running_cavities
	# 					ELSE 0
	# 				END) noc,
	# 				SUM(CASE
	# 					WHEN IE.inspection_type = 'Lot Inspection' THEN JC.number_of_lifts
	# 					ELSE 0
	# 				END) nol,
	# 				SUM(CASE
	# 					WHEN IE.inspection_type = 'Lot Inspection' THEN SED.qty
	# 					ELSE 0
	# 				END) total_produced_weight,
	# 				SUM(CASE
	# 					WHEN IE.inspection_type = 'Lot Inspection' THEN (ROUND(SED.qty*1000/MS.wtpiece_avg_gms))
	# 					ELSE 0
	# 				END) total_produced_qty_nos
	# 			FROM 
	# 				`tabMoulding Production Entry` MPE 
	# 				INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card
	# 				INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number 
	# 				INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference
	# 				INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
	# 				INNER JOIN `tabBOM Item` BOI ON BOI.parent = JC.bom_no
	# 				INNER JOIN `tabAsset` asset ON asset.name = JC.mould_reference
	# 				INNER JOIN `tabMould Specification` MS ON MS.mould_ref = asset.item_code
	# 			WHERE 
	# 				MPE.docstatus = 1 
	# 				AND JC.docstatus = 1
	# 				AND asset.docstatus = 1
	# 				AND IE.docstatus = 1
	# 				AND SE.docstatus = 1
	# 				AND SED.item_code = JC.production_item
	# 				AND MPE.scan_lot_number = IE.lot_no
	# 				AND IE.inspection_type IN ("Line Inspection", "Lot Inspection")
	# 				{condition}
	# 			GROUP BY
	# 				shift, press, operator, mould """
	# resp__ = frappe.db.sql(query,as_dict = 1)
	# return resp__
