# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = get_columns(), get_datas(filters)
	return columns, data

def get_columns():
	col__ = [
		{	
		"label": _("Production Lot No"),
		"fieldname": "lot_no",
		"fieldtype": "Data",
		"width": 150,
		},
		{	
		"label": _("ID Trimmer"),
		"fieldname": "id_trimmer",
		"fieldtype": "Data",
		"width": 250,
		},
		{	
		"label": _("OD Trimmer"),
		"fieldname": "od_trimmer",
		"fieldtype": "Data",
		"width": 250,
		},
		{	
		"label": _("Trimmed Qty(Nos)"),
		"fieldname": "trim_qty",
		"fieldtype": "Int",
		"width": 160,
		},
		{	
		"label": _("Trimming Rejection"),
		"fieldname": "trim_rejection_perc",
		"fieldtype": "Percent",
		"width": 160,
		},
		{	
		"label": _("FG Qty(Nos)"),
		"fieldname": "fg_qty_nos",
		"fieldtype": "Int",
		"width": 110,
		},
		{	
		"label": _("FG Rejection"),
		"fieldname": "fg_rejection",
		"fieldtype": "Percent",
		"width": 110,
		},
	]
	return col__

def get_datas(filters):
	condition = ""
	if filters.get('from_date'):
		condition += f" AND DATE(WP.date) >= '{filters.get('from_date')}' "
	if filters.get('to_date'):
		condition += f" AND DATE(WP.date) <= '{filters.get('to_date')}' "
	if filters.get('spp_batch_no'):
		condition += f" AND JC.batch_code LIKE '%{filters.get('spp_batch_no')}%' "
	query = f""" 
				SELECT date,batch_code lot_no,
						(CASE 
							WHEN 
								total_finalins_rejected_qty != 0
							THEN ((total_finalins_rejected_qty / total_finalins_inspected_qty) * 100)
						ELSE
							0
						END)
					fg_rejection,
					total_finalins_inspected_qty,total_finalins_rejected_qty,
						total_fg_qty 
					fg_qty_nos,
					total_lrt_qty trim_qty,
					od_trimmers od_trimmer,
					id_trimmers id_trimmer,
						(CASE 
							WHEN 
								total_trimming_rej_nos != 0
							THEN ((total_trimming_rej_nos / total_finalins_inspected_qty) * 100)
						ELSE
							0
						END)
					trim_rejection_perc,
					total_trimming_rej_nos 
					FROM (
						SELECT DISTINCT 
							DATE(MPE.moulding_date) date,JC.batch_code,
								( SELECT SUM(FIVINS.total_rejected_qty)
									FROM `tabInspection Entry` FIVINS
											WHERE FIVINS.docstatus = 1 AND FIVINS.inspection_type = "Final Visual Inspection"
												AND FIVINS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							total_finalins_rejected_qty,
								( SELECT SUM(FIVINS.total_inspected_qty_nos)
									FROM `tabInspection Entry` FIVINS
											WHERE FIVINS.docstatus = 1 AND FIVINS.inspection_type = "Final Visual Inspection"
												AND FIVINS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							total_finalins_inspected_qty,
								( SELECT IFNULL((SUM(
											CASE 
												WHEN 
													(FG.vs_pdir_qty_after_rejection IS NULL
															OR FG.vs_pdir_qty_after_rejection = 0)
												THEN 
													LRT.qty_after_rejection_nos
												ELSE 
													FG.vs_pdir_qty_after_rejection
											END	
												)),0)
										FROM `tabInspection Entry` FG
											LEFT JOIN `tabLot Resource Tagging` LRT ON 
												LRT.name = ( SELECT 
																name FROM `tabLot Resource Tagging` 
															WHERE scan_lot_no = FG.lot_no LIMIT 1 )
												AND LRT.docstatus = 1
												WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
													AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							total_fg_qty,
								( SELECT IFNULL((SUM(
												CASE 
													WHEN 
														(LRT.qtynos IS NULL
																OR LRT.qtynos = 0)
													THEN 
														0
													ELSE 
														LRT.qtynos
												END	
													)),0)
										FROM `tabInspection Entry` FG
											INNER JOIN `tabLot Resource Tagging` LRT ON 
												LRT.scan_lot_no = FG.lot_no AND LRT.docstatus = 1 
													AND ( LRT.stock_entry_ref IS NOT NULL AND LRT.stock_entry_ref != "")
 												WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
													AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							total_lrt_qty,
								( SELECT GROUP_CONCAT(LRT.operator_name)
										FROM `tabInspection Entry` FG
											INNER JOIN `tabLot Resource Tagging` LRT ON 
												LRT.scan_lot_no = FG.lot_no AND LRT.docstatus = 1 
													AND LRT.operation_type = "OD Trimming"
 												WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
													AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							od_trimmers,
								( SELECT GROUP_CONCAT(LRT.operator_name)
										FROM `tabInspection Entry` FG
											INNER JOIN `tabLot Resource Tagging` LRT ON 
												LRT.scan_lot_no = FG.lot_no AND LRT.docstatus = 1 
													AND LRT.operation_type = "ID Trimming"
 												WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
													AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							id_trimmers,
								( SELECT SUM(FINSI.rejected_qty)
										FROM `tabInspection Entry` FIVINS
											INNER JOIN `tabInspection Entry Item` FINSI ON FINSI.parent = FIVINS.name
												WHERE FIVINS.docstatus = 1 AND FIVINS.inspection_type = "Final Visual Inspection"
													AND FIVINS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%')
													AND FINSI.type_of_defect LIKE "%trim%")
							total_trimming_rej_nos

						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
							INNER JOIN `tabWork Plan Item` WPI ON WPI.job_card = JC.name AND WPI.docstatus = 1
							INNER JOIN `tabWork Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
							INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number AND IE.inspection_type = "Line Inspection"
							INNER JOIN `tabInspection Entry` LO ON LO.lot_no = MPE.scan_lot_number AND LO.inspection_type = "Lot Inspection"
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
						
							SELECT DISTINCT 
								DATE(MPE.moulding_date) date,JC.batch_code,
									( SELECT SUM(FIVINS.total_rejected_qty)
										FROM `tabInspection Entry` FIVINS
												WHERE FIVINS.docstatus = 1 AND FIVINS.inspection_type = "Final Visual Inspection"
													AND FIVINS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_finalins_rejected_qty,
									( SELECT SUM(FIVINS.total_inspected_qty_nos)
										FROM `tabInspection Entry` FIVINS
												WHERE FIVINS.docstatus = 1 AND FIVINS.inspection_type = "Final Visual Inspection"
													AND FIVINS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_finalins_inspected_qty,
									( SELECT IFNULL((SUM(
												CASE 
													WHEN 
														(FG.vs_pdir_qty_after_rejection IS NULL
																OR FG.vs_pdir_qty_after_rejection = 0)
													THEN 
														LRT.qty_after_rejection_nos
													ELSE 
														FG.vs_pdir_qty_after_rejection
												END	
													)),0)
											FROM `tabInspection Entry` FG
												LEFT JOIN `tabLot Resource Tagging` LRT ON 
													LRT.name = ( SELECT 
																	name FROM `tabLot Resource Tagging` 
																WHERE scan_lot_no = FG.lot_no LIMIT 1 )
													AND LRT.docstatus = 1
													WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
														AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_fg_qty,
									( SELECT IFNULL((SUM(
													CASE 
														WHEN 
															(LRT.qtynos IS NULL
																	OR LRT.qtynos = 0)
														THEN 
															0
														ELSE 
															LRT.qtynos
													END	
														)),0)
											FROM `tabInspection Entry` FG
												INNER JOIN `tabLot Resource Tagging` LRT ON 
													LRT.scan_lot_no = FG.lot_no AND LRT.docstatus = 1 
														AND ( LRT.stock_entry_ref IS NOT NULL AND LRT.stock_entry_ref != "")
													WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
														AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_lrt_qty,
									( SELECT GROUP_CONCAT(LRT.operator_name)
										FROM `tabInspection Entry` FG
											INNER JOIN `tabLot Resource Tagging` LRT ON 
												LRT.scan_lot_no = FG.lot_no AND LRT.docstatus = 1 
													AND LRT.operation_type = "OD Trimming"
 												WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
														AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								od_trimmers,
									( SELECT GROUP_CONCAT(LRT.operator_name)
											FROM `tabInspection Entry` FG
												INNER JOIN `tabLot Resource Tagging` LRT ON 
													LRT.scan_lot_no = FG.lot_no AND LRT.docstatus = 1 
														AND LRT.operation_type = "ID Trimming"
													WHERE FG.docstatus = 1 AND FG.inspection_type = "Final Visual Inspection"
														AND FG.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								id_trimmers,
									( SELECT SUM(FINSI.rejected_qty)
										FROM `tabInspection Entry` FIVINS
											INNER JOIN `tabInspection Entry Item` FINSI ON FINSI.parent = FIVINS.name
												WHERE FIVINS.docstatus = 1 AND FIVINS.inspection_type = "Final Visual Inspection"
													AND FIVINS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%')
													AND FINSI.type_of_defect LIKE "%trim%")
								total_trimming_rej_nos
						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
							INNER JOIN `tabAdd On Work Plan Item` WPI ON WPI.job_card = JC.name AND WPI.docstatus = 1
							INNER JOIN `tabAdd On Work Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.source_ref_id = MPE.name
							INNER JOIN `tabInspection Entry` IE ON IE.lot_no = MPE.scan_lot_number AND IE.inspection_type = "Line Inspection"
							INNER JOIN `tabInspection Entry` LO ON LO.lot_no = MPE.scan_lot_number AND LO.inspection_type = "Lot Inspection"
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
	# frappe.log_error(title="query---",message=query)
	resp__ = frappe.db.sql(query,as_dict = 1)
	# frappe.log_error(title="---",message=resp__)
	calculate_total_rejection(resp__)
	return resp__
 
def calculate_total_rejection(resp__):
	if resp__ :
		fg_qty_nos = 0
		total_finalins_inspected_qty = 0
		total_finalins_rejection_qty = 0
		total_trim = 0
		total_trim_inspected_qty = 0
		total_trim_rejection_qty = 0
		for k in resp__:
			fg_qty_nos += k.fg_qty_nos if k.fg_qty_nos else 0.0 
			total_finalins_inspected_qty += k.total_finalins_inspected_qty if k.total_finalins_inspected_qty else 0.0 
			total_finalins_rejection_qty += k.total_finalins_rejected_qty if k.total_finalins_rejected_qty else 0.0 
			total_trim += k.trim_qty if k.trim_qty else 0
			total_trim_inspected_qty += k.total_finalins_inspected_qty if k.total_finalins_inspected_qty else 0.0 
			total_trim_rejection_qty += k.total_trimming_rej_nos if k.total_trimming_rej_nos else 0.0 
		if total_finalins_rejection_qty:
			__total_finalins_rejection =  (total_finalins_rejection_qty / total_finalins_inspected_qty) * 100
		else:
			__total_finalins_rejection = 0
		if total_trim_rejection_qty:
			__total_total_trimming_rej =  (total_trim_rejection_qty / total_trim_inspected_qty) * 100
		else:
			__total_total_trimming_rej = 0
		resp__.append({"batch_code":"<b>Total</b>",
		 				"trim_qty":total_trim,
						"fg_qty_nos":fg_qty_nos,
						"fg_rejection":__total_finalins_rejection,
						"trim_rejection_perc":__total_total_trimming_rej
						})


