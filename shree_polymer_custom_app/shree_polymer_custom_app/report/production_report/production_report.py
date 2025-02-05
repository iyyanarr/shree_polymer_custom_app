# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = get_columns(), get_datas(filters)
	return columns, data

def get_columns():
	col__ = []
	col__.append(_("Date") + ":Date:100")
	col__.append(_("Shift") + ":Data:120")
	col__.append(_("Press") + ":Link/Workstation:180")
	col__.append(_("PCard") + ":Data:100")
	# col__.append(_("Operator") + ":Link/Employee:120")
	col__.append(_("Operator Name") + ":Data:150")
	# col__.append(_("Line Inspector") + ":Link/Employee:120")
	col__.append(_("Line Inspector Name") + ":Data:150")
	col__.append(_("SPP Ref") + ":Link/Item:80")
	col__.append(_("Compound Code") + ":Data:130")
	col__.append(_("Mould Ref") + ":Link/Item:130")
	col__.append(_("Batch Code") + ":Data:100")
	col__.append(_("NOC") + ":Int:60")
	col__.append(_("NOL") + ":Int:60")
	col__.append(_("Line Inspection")+":Percent:120")
	col__.append(_("Lot Inspection")+":Percent:120")
	col__.append(_("Total Produced Qty Kgs") + ":Float:170")
	col__.append(_("Total Produced QTY Nos")+":Int:180")
	col__.append(_("Theoretical Produced QTY")+":Float:190")
	return col__

def get_datas(filters):
	condition = ""
	if filters.get('from_date'):
		condition += f" AND DATE(WP.date) >= '{filters.get('from_date')}' "
	if filters.get('to_date'):
		condition += f" AND DATE(WP.date) <= '{filters.get('to_date')}' "
	if filters.get('shift'):
		condition += f" AND JC.shift_type = '{filters.get('shift')}' "
	if filters.get('press'):
		condition += f" AND JC.workstation = '{filters.get('press')}' "
	if filters.get('spp_batch_no'):
		condition += f" AND JC.batch_code LIKE '%{filters.get('spp_batch_no')}%' "
	query = f""" 
				SELECT date, shift, press,pcard,operator,operator_name,
					line_inspector,line_inspector_name,
					spp_ref,compound_code, batch_code,
					noc, nol,line_inspection, line_rejected_qty , line_inspected_qty,
					lot_inspection,  lot_rejected_qty , lot_inspected_qty,
					total_produced_qty_kgs,	total_produced_qty_nos,
					total_produced_qty theoretical_produced_qty,mould_ref 
					FROM (
						SELECT DISTINCT A.item_code mould_ref,
							DATE(MPE.moulding_date) date,JC.shift_type shift,JC.workstation press,JC.batch_code pcard,
							MPE.employee operator,MPE.employee_name operator_name,
							IE.inspector_code line_inspector,IE.inspector_name line_inspector_name,
							JC.production_item spp_ref,
							MPE.compound compound_code,SED.spp_batch_number batch_code,
							JC.no_of_running_cavities noc,JC.number_of_lifts nol,
								IE.total_rejected_qty_in_percentage
							line_inspection, IE.total_rejected_qty_kg line_rejected_qty ,IE.total_inspected_qty line_inspected_qty,
								LO.total_rejected_qty_in_percentage
							lot_inspection, LO.total_rejected_qty_kg lot_rejected_qty ,LO.total_inspected_qty lot_inspected_qty,
								ROUND(SED.qty,3) 
							total_produced_qty_kgs,		
								CASE 
									WHEN 
										MS.avg_blank_wtproduct_gms != 0
									THEN 
										ROUND(((SED.qty)/(MS.avg_blank_wtproduct_gms/1000)),0)
									ELSE 0 
								END 
							total_produced_qty_nos,
								MPE.number_of_lifts * MPE.no_of_running_cavities 
							total_produced_qty
						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
							INNER JOIN `tabAsset` A ON A.name = JC.mould_reference
							INNER JOIN `tabWork Plan Item` WPI ON WPI.job_card = JC.name AND WPI.docstatus = 1
							INNER JOIN `tabWork Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
							INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number AND IE.inspection_type = "Line Inspection"
							INNER JOIN `tabInspection Entry` LO ON LO.lot_no = MPE.scan_lot_number AND LO.inspection_type = "Lot Inspection"
							INNER JOIN `tabAsset` ASS ON ASS.name = JC.mould_reference
							INNER JOIN `tabMould Specification` MS ON MS.mould_ref = ASS.item_code
												AND MS.spp_ref = MPE.item_to_produce AND MS.mould_status = 'ACTIVE'
						WHERE 
							MPE.docstatus = 1 
							AND JC.docstatus = 1 
							AND SED.docstatus = 1 
							AND IE.docstatus = 1 
							AND LO.docstatus = 1 
							AND SED.item_code = JC.production_item 
							AND MPE.scan_lot_number = IE.lot_no
							AND JC.name = MPE.job_card
							{condition} 
						
						UNION ALL
						
						SELECT DISTINCT A.item_code mould_ref,
							DATE(MPE.moulding_date) date,JC.shift_type shift,JC.workstation press,JC.batch_code pcard,
							MPE.employee operator,MPE.employee_name operator_name,
							IE.inspector_code line_inspector,IE.inspector_name line_inspector_name,
							JC.production_item spp_ref,
							MPE.compound compound_code,SED.spp_batch_number batch_code,
							JC.no_of_running_cavities noc,JC.number_of_lifts nol,
								IE.total_rejected_qty_in_percentage
							line_inspection, IE.total_rejected_qty_kg line_rejected_qty ,IE.total_inspected_qty line_inspected_qty,
								LO.total_rejected_qty_in_percentage
							lot_inspection, LO.total_rejected_qty_kg lot_rejected_qty ,LO.total_inspected_qty lot_inspected_qty,
								ROUND(SED.qty,3) 
							total_produced_qty_kgs,		
								CASE 
									WHEN 
										MS.avg_blank_wtproduct_gms != 0
									THEN 
										ROUND(((SED.qty)/(MS.avg_blank_wtproduct_gms/1000)),0)
									ELSE 0 
								END 
							total_produced_qty_nos,
								MPE.number_of_lifts * MPE.no_of_running_cavities 
							total_produced_qty
						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
							INNER JOIN `tabAsset` A ON A.name = JC.mould_reference
							INNER JOIN `tabAdd On Work Plan Item` WPI ON WPI.job_card = JC.name AND WPI.docstatus = 1
							INNER JOIN `tabAdd On Work Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
							INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number AND IE.inspection_type = "Line Inspection"
							INNER JOIN `tabInspection Entry` LO ON LO.lot_no = MPE.scan_lot_number AND LO.inspection_type = "Lot Inspection"
							INNER JOIN `tabAsset` ASS ON ASS.name = JC.mould_reference
							INNER JOIN `tabMould Specification` MS ON MS.mould_ref = ASS.item_code
												AND MS.spp_ref = MPE.item_to_produce AND MS.mould_status = 'ACTIVE'
						WHERE 
							MPE.docstatus = 1 
							AND JC.docstatus = 1 
							AND SED.docstatus = 1 
							AND IE.docstatus = 1 
							AND LO.docstatus = 1 
							AND SED.item_code = JC.production_item 
							AND MPE.scan_lot_number = IE.lot_no
							AND JC.name = MPE.job_card
							{condition}  
				) DEMO ORDER BY date DESC """	
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
		total_produced_qty_kgs = flt(sum(k.total_produced_qty_kgs if k.total_produced_qty_kgs else 0.0 for k in resp__),3)
		total_produced_qty_nos = round((sum(k.total_produced_qty_nos if k.total_produced_qty_nos else 0 for k in resp__)))
		theoretical_produced_qty = round((sum(k.theoretical_produced_qty if k.theoretical_produced_qty else 0 for k in resp__)))
		resp__.append({"batch_code":"<b>Total</b>","total_produced_qty_kgs":total_produced_qty_kgs,"total_produced_qty_nos":total_produced_qty_nos,"theoretical_produced_qty":theoretical_produced_qty,"noc":total_noc,"nol":total_nol,"line_inspection":__total_line_rejection,"lot_inspection":__total_lot_rejection})

@frappe.whitelist()
def item_filters(doctype, txt, searchfield, start, page_len, filters):
	try:
		search_condition = ""
		if txt:
			search_condition = " AND name LIKE '%"+txt+"%'"
		res_ = ()
		spp_ = frappe.get_single("SPP Settings")
		work_station_filter_val = ""
		if spp_.work_station and len(spp_.work_station) != 0:
			for wrk in spp_.work_station:
				work_station_filter_val += f'"{wrk.work_station}",'
		if work_station_filter_val:
			work_station_filter_val = work_station_filter_val[:-1]
			res_ = frappe.db.sql(f" SELECT name FROM `tabWorkstation` WHERE name IN ({work_station_filter_val}) {search_condition}")
		else:
			res_ = frappe.db.sql(f" SELECT name FROM `tabWorkstation` WHERE name IS NOT NULL {search_condition}")
		return res_
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.report.production_report.production_report.item_filters")





# if filters.get('from_date'):
# 		condition += f" AND DATE(MPE.moulding_date) >= '{filters.get('from_date')}' "
# 	if filters.get('to_date'):
# 		condition += f" AND DATE(MPE.moulding_date) <= '{filters.get('to_date')}' "



	# query = f""" SELECT DISTINCT
	# 				DATE(SE.modified) date,JC.shift_number shift,JC.workstation press,JC.batch_code pcard,
	# 				MPE.employee operator,IE.inspector_code line_inspector,
	# 				JC.production_item spp_ref,
	# 				BOI.item_code compound_code,SED.spp_batch_number batch_code,
	# 				JC.no_of_running_cavities noc,JC.number_of_lifts nol,
	# 					IE.total_rejected_qty_in_percentage
	# 				line_inspection, IE.total_rejected_qty_kg line_rejected_qty ,IE.total_inspected_qty line_inspected_qty,
	# 					LO.total_rejected_qty_in_percentage
	# 				lot_inspection, LO.total_rejected_qty_kg lot_rejected_qty ,LO.total_inspected_qty lot_inspected_qty,
	# 					SED.qty 
	# 				total_produced_qty_kgs,		
	# 					CASE 
	# 						WHEN 
	# 							MS.avg_blank_wtproduct_gms != 0
	# 						THEN 
	# 							(SED.qty)/(MS.avg_blank_wtproduct_gms/1000) 
	# 						ELSE 0 
	# 					END 
	# 				total_produced_qty_nos
	# 			FROM 
	# 				`tabMoulding Production Entry` MPE 
	# 				INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
	# 				INNER JOIN `tabBOM Item` BOI ON BOI.parent = JC.bom_no 
	# 				INNER JOIN `tabItem` MMI ON MMI.name = BOI.item_code AND MMI.item_group = 'Compound'
	# 				INNER JOIN `tabStock Entry Detail` SED ON SED.parent = MPE.stock_entry_reference
	# 				INNER JOIN `tabStock Entry` SE ON MPE.stock_entry_reference = SE.name
	# 				INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number AND IE.inspection_type = "Line Inspection"
	# 				INNER JOIN `tabInspection Entry` LO ON LO.lot_no = MPE.scan_lot_number AND LO.inspection_type = "Lot Inspection"
	# 				INNER JOIN `tabAsset` ASS ON ASS.name = JC.mould_reference
	# 				INNER JOIN `tabMould Specification` MS ON MS.mould_ref = ASS.item_code
	# 			WHERE 
	# 				MPE.docstatus = 1 
	# 				AND JC.docstatus = 1 
	# 				AND SE.docstatus = 1 
	# 				AND IE.docstatus = 1 
	# 				AND LO.docstatus = 1 
	# 				AND SED.item_code = JC.production_item 
	# 				AND MPE.scan_lot_number = IE.lot_no
	# 				AND SED.item_name = SE.item_name
	# 				AND JC.name = MPE.job_card
	# 				{condition} ORDER BY SE.modified DESC """	
	# resp__ = frappe.db.sql(query,as_dict = 1)


# 	IE.total_rejected_qty_kg/(SED.qty/100) 
	# line_inspection, 
	# 	LO.total_rejected_qty_kg/(SED.qty/100) 
	# lot_inspection,


	# query = f""" SELECT DISTINCT
	# 				DATE(SE.modified) date,JC.shift_number shift,JC.workstation press,JC.batch_code pcard,
	# 				MPE.employee operator,IE.inspector_code line_inspector,
	# 				JC.production_item spp_ref,
	# 				BOI.item_code compound_code,SED.spp_batch_number batch_code,
	# 				JC.no_of_running_cavities noc,JC.number_of_lifts nol,
	# 					IE.total_rejected_qty_in_percentage
	# 				line_inspection, IE.total_rejected_qty_kg line_rejected_qty ,IE.total_inspected_qty line_inspected_qty,
	# 					LO.total_rejected_qty_in_percentage
	# 				lot_inspection, LO.total_rejected_qty_kg lot_rejected_qty ,LO.total_inspected_qty lot_inspected_qty,
	# 				(SED.qty - 
	# 						(IE.total_rejected_qty_kg
	# 						+ LO.total_rejected_qty_kg))
	# 				total_produced_qty_kgs,		
	# 					CASE 
	# 						WHEN 
	# 							MS.avg_blank_wtproduct_gms != 0
	# 						THEN 
	# 							(SED.qty - 
	# 							(IE.total_rejected_qty_kg
	# 							+ LO.total_rejected_qty_kg))/(MS.avg_blank_wtproduct_gms/1000) 
	# 						ELSE 0 
	# 					END 
	# 				total_produced_qty_nos
	# 			FROM 
	# 				`tabMoulding Production Entry` MPE 
	# 				INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
	# 				INNER JOIN `tabBOM Item` BOI ON BOI.parent = JC.bom_no 
	# 				INNER JOIN `tabItem` MMI ON MMI.name = BOI.item_code AND MMI.item_group = 'Compound'
	# 				INNER JOIN `tabStock Entry Detail` SED ON SED.parent = MPE.stock_entry_reference
	# 				INNER JOIN `tabStock Entry` SE ON MPE.stock_entry_reference = SE.name
	# 				INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number AND IE.inspection_type = "Line Inspection"
	# 				INNER JOIN `tabInspection Entry` LO ON LO.lot_no = MPE.scan_lot_number AND LO.inspection_type = "Lot Inspection"
	# 				INNER JOIN `tabAsset` ASS ON ASS.name = JC.mould_reference
	# 				INNER JOIN `tabMould Specification` MS ON MS.mould_ref = ASS.item_code
	# 			WHERE 
	# 				MPE.docstatus = 1 
	# 				AND JC.docstatus = 1 
	# 				AND SE.docstatus = 1 
	# 				AND IE.docstatus = 1 
	# 				AND LO.docstatus = 1 
	# 				AND SED.item_code = JC.production_item 
	# 				AND MPE.scan_lot_number = IE.lot_no
	# 				AND SED.item_name = SE.item_name
	# 				AND JC.name = MPE.job_card
	# 				{condition} ORDER BY SE.modified DESC """	