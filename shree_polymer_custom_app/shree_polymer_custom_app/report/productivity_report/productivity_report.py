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
		"label": _("Mould Ref"),
		"fieldname": "mould_ref",
		"fieldtype": "Data",
		"width": 100,
		},
		{	
		"label": _("Produced Qty(Nos) by Kgs"),
		"fieldname": "prod_qty_by_kgs",
		"fieldtype": "Int",
		"width": 200,
		},
		{	
		"label": _("Produced Qty (Nos) By Lift"),
		"fieldname": "prod_qty_by_lift",
		"fieldtype": "Int",
		"width": 200,
		},
		{	
		"label": _("Line Rejection"),
		"fieldname": "line_rejection_perc",
		"fieldtype": "Percent",
		"width": 120,
		},
		{	
		"label": _("Lot Rejection"),
		"fieldname": "lot_rejection_perc",
		"fieldtype": "Percent",
		"width": 120,
		},
		{	
		"label": _("Deflashing Received Qty(Kgs)"),
		"fieldname": "def_rec_qty_kgs",
		"fieldtype": "Float",
		"width": 210,
		},
		{	
		"label": _("Deflashing Rejection"),
		"fieldname": "def_rejection_perc",
		"fieldtype": "Percent",
		"width": 160,
		},
		{	
		"label": _("ID Trimming"),
		"fieldname": "id_trim",
		"fieldtype": "Int",
		"width": 110,
		},
		{	
		"label": _("OD Trimming"),
		"fieldname": "od_trim",
		"fieldtype": "Int",
		"width": 110,
		},
		{	
		"label": _("Post Curing"),
		"fieldname": "post_curing",
		"fieldtype": "Int",
		"width": 110,
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
	if filters.get('mould_reference'):
		condition += f" AND ASS.item_code LIKE '%{filters.get('mould_reference')}%' "
	query = f""" 
				SELECT date,batch_code lot_no,total_produced_qty_nos prod_qty_by_kgs,
					total_produced_qty prod_qty_by_lift,
					line_rejected_qty,line_inspected_qty,line_inspection line_rejection_perc,
					lot_rejected_qty,lot_inspected_qty,mould_ref,lot_inspection lot_rejection_perc,
					def_rec_qty_kgs,
						(CASE 
							WHEN 
								total_def_rejected_qty != 0
							THEN ((total_def_rejected_qty / total_def_inspected_qty) * 100)
						ELSE
							0
						END)
					def_rejection_perc,
					total_def_rejected_qty,total_def_inspected_qty,
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
					total_lrt_qty id_trim,
					total_lrt_qty od_trim,
					total_lrt_qty post_curing
					FROM (
						SELECT DISTINCT ASS.item_code mould_ref,
							DATE(MPE.moulding_date) date,JC.batch_code,
								CASE 
									WHEN 
										MS.avg_blank_wtproduct_gms != 0
									THEN 
										ROUND(((SED.qty)/(MS.avg_blank_wtproduct_gms/1000)),0)
									ELSE 0 
								END 
							total_produced_qty_nos,
								MPE.number_of_lifts * MPE.no_of_running_cavities 
							total_produced_qty,
								IE.total_rejected_qty_in_percentage
							line_inspection,
								IE.total_rejected_qty_kg 
							line_rejected_qty ,
								IE.total_inspected_qty 
							line_inspected_qty,
								LO.total_rejected_qty_in_percentage
							lot_inspection,
								LO.total_rejected_qty_kg 
							lot_rejected_qty ,
								LO.total_inspected_qty
							lot_inspected_qty,
								( SELECT SUM(DEFR.product_weight) 
									FROM `tabDeflashing Receipt Entry` DEFR
										INNER JOIN `tabInspection Entry` LINS ON LINS.lot_no = DEFR.lot_number
											AND inspection_type = "Incoming Inspection"
									 	WHERE LINS.docstatus = 1 AND DEFR.docstatus = 1
											AND DEFR.lot_number LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							def_rec_qty_kgs,
								( SELECT SUM(INCINS_R.total_rejected_qty)
									FROM `tabInspection Entry` INCINS_R
										INNER JOIN `tabDeflashing Receipt Entry` DEFR ON INCINS_R.lot_no = DEFR.lot_number
												AND inspection_type = "Incoming Inspection"
											WHERE INCINS_R.docstatus = 1 AND DEFR.docstatus = 1
												AND DEFR.lot_number LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							total_def_rejected_qty,
								( SELECT SUM(INCINS_R.total_inspected_qty_nos)
									FROM `tabInspection Entry` INCINS_R
										INNER JOIN `tabDeflashing Receipt Entry` DEFR ON INCINS_R.lot_no = DEFR.lot_number
												AND inspection_type = "Incoming Inspection"
											WHERE INCINS_R.docstatus = 1 AND DEFR.docstatus = 1
												AND DEFR.lot_number LIKE CONCAT('%',MPE.scan_lot_number,'%'))
							total_def_inspected_qty,
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
							total_lrt_qty

						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
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
						
						SELECT DISTINCT ASS.item_code mould_ref,
								DATE(MPE.moulding_date) date,JC.batch_code,
									CASE 
										WHEN 
											MS.avg_blank_wtproduct_gms != 0
										THEN 
											ROUND(((SED.qty)/(MS.avg_blank_wtproduct_gms/1000)),0)
										ELSE 0 
									END 
								total_produced_qty_nos,
									MPE.number_of_lifts * MPE.no_of_running_cavities 
								total_produced_qty,
									IE.total_rejected_qty_in_percentage
								line_inspection,
									IE.total_rejected_qty_kg 
								line_rejected_qty ,
									IE.total_inspected_qty 
								line_inspected_qty,
									LO.total_rejected_qty_in_percentage
								lot_inspection,
									LO.total_rejected_qty_kg 
								lot_rejected_qty ,
									LO.total_inspected_qty
								lot_inspected_qty,
									( SELECT SUM(DEFR.product_weight) 
									FROM `tabDeflashing Receipt Entry` DEFR
										INNER JOIN `tabInspection Entry` LINS ON LINS.lot_no = DEFR.lot_number
											AND inspection_type = "Incoming Inspection"
									 	WHERE LINS.docstatus = 1 AND DEFR.docstatus = 1
											AND DEFR.lot_number LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								def_rec_qty_kgs,
									( SELECT SUM(INCINS_R.total_rejected_qty)
										FROM `tabInspection Entry` INCINS_R
											INNER JOIN `tabDeflashing Receipt Entry` DEFR ON INCINS_R.lot_no = DEFR.lot_number
													AND inspection_type = "Incoming Inspection"
												WHERE INCINS_R.docstatus = 1 AND DEFR.docstatus = 1
													AND DEFR.lot_number LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_def_rejected_qty,
									( SELECT SUM(INCINS_R.total_inspected_qty_nos)
										FROM `tabInspection Entry` INCINS_R
											INNER JOIN `tabDeflashing Receipt Entry` DEFR ON INCINS_R.lot_no = DEFR.lot_number
													AND inspection_type = "Incoming Inspection"
												WHERE INCINS_R.docstatus = 1 AND DEFR.docstatus = 1
													AND DEFR.lot_number LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_def_inspected_qty,
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
								total_lrt_qty
						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabJob Card` JC ON JC.name = MPE.job_card AND JC.operation = "Moulding"
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
	if resp__ :
		total_line_inspected_qty = 0
		total_line_rejection_qty = 0
		fg_qty_nos = 0
		total_lot_inspected_qty = 0
		total_lot_rejection_qty = 0
		total_def_inspected_qty = 0
		total_def_rejection_qty = 0
		total_finalins_inspected_qty = 0
		total_finalins_rejection_qty = 0
		total_prod_qty_by_kgs = 0
		total_prod_qty_by_lift = 0
		total_def_rec_qty_kgs = 0
		total_id_trim = 0
		total_od_trim = 0
		total_post_curing = 0
		for k in resp__:
			total_line_inspected_qty += k.line_inspected_qty if k.line_inspected_qty else 0.0 
			total_line_rejection_qty += k.line_rejected_qty if k.line_rejected_qty else 0.0 
			fg_qty_nos += k.fg_qty_nos if k.fg_qty_nos else 0.0 
			total_lot_inspected_qty += k.lot_inspected_qty if k.lot_inspected_qty else 0.0 
			total_lot_rejection_qty += k.lot_rejected_qty if k.lot_rejected_qty else 0.0 
			total_def_inspected_qty += k.total_def_inspected_qty if k.total_def_inspected_qty else 0.0 
			total_def_rejection_qty += k.total_def_rejected_qty if k.total_def_rejected_qty else 0.0 
			total_finalins_inspected_qty += k.total_finalins_inspected_qty if k.total_finalins_inspected_qty else 0.0 
			total_finalins_rejection_qty += k.total_finalins_rejected_qty if k.total_finalins_rejected_qty else 0.0 
			total_prod_qty_by_kgs += k.prod_qty_by_kgs if k.prod_qty_by_kgs else 0 
			total_prod_qty_by_lift += k.prod_qty_by_lift if k.prod_qty_by_lift else 0 
			total_def_rec_qty_kgs += k.def_rec_qty_kgs if k.def_rec_qty_kgs else 0
			total_id_trim += k.id_trim if k.id_trim else 0
			total_od_trim += k.od_trim if k.od_trim else 0
			total_post_curing += k.post_curing if k.post_curing else 0
		if total_line_rejection_qty:
			__total_line_rejection =  (total_line_rejection_qty / total_line_inspected_qty) * 100
		else:
			__total_line_rejection = 0
		if total_lot_rejection_qty:
			__total_lot_rejection = (total_lot_rejection_qty / total_lot_inspected_qty) * 100
		else:
			__total_lot_rejection = 0
		if total_def_rejection_qty:
			__total_def_rejection =  (total_def_rejection_qty / total_def_inspected_qty) * 100
		else:
			__total_def_rejection = 0
		if total_finalins_rejection_qty:
			__total_finalins_rejection =  (total_finalins_rejection_qty / total_finalins_inspected_qty) * 100
		else:
			__total_finalins_rejection = 0
		resp__.append({"batch_code":"<b>Total</b>",
		 				"id_trim":total_id_trim,
						"od_trim":total_od_trim,
						"post_curing":total_post_curing,
						"fg_qty_nos":fg_qty_nos,
						"fg_rejection":__total_finalins_rejection,
						"def_rejection_perc":__total_def_rejection,
						"def_rec_qty_kgs":total_def_rec_qty_kgs,
						"prod_qty_by_kgs":total_prod_qty_by_kgs,
						"prod_qty_by_lift":total_prod_qty_by_lift,
						"line_rejection_perc":__total_line_rejection,
						"lot_rejection_perc":__total_lot_rejection})






# total_line_inspected_qty = sum(k.line_inspected_qty if k.line_inspected_qty else 0.0 for k in resp__)
# 			total_line_rejection_qty = sum(k.line_rejected_qty if k.line_rejected_qty else 0.0 for k in resp__)
# 			fg_qty_nos = sum(k.fg_qty_nos if k.fg_qty_nos else 0.0 for k in resp__)
# 			if total_line_rejection_qty:
# 				__total_line_rejection =  (total_line_rejection_qty / total_line_inspected_qty) * 100
# 			else:
# 				__total_line_rejection = 0
# 			total_lot_inspected_qty = sum(k.lot_inspected_qty if k.lot_inspected_qty else 0.0 for k in resp__)
# 			total_lot_rejection_qty = sum(k.lot_rejected_qty if k.lot_rejected_qty else 0.0 for k in resp__)
# 			if total_lot_rejection_qty:
# 				__total_lot_rejection = (total_lot_rejection_qty / total_lot_inspected_qty) * 100
# 			else:
# 				__total_lot_rejection = 0
# 			total_def_inspected_qty = sum(k.total_def_inspected_qty if k.total_def_inspected_qty else 0.0 for k in resp__)
# 			total_def_rejection_qty = sum(k.total_def_rejected_qty if k.total_def_rejected_qty else 0.0 for k in resp__)
# 			if total_def_rejection_qty:
# 				__total_def_rejection =  (total_def_rejection_qty / total_def_inspected_qty) * 100
# 			else:
# 				__total_def_rejection = 0
# 			total_finalins_inspected_qty = sum(k.total_finalins_inspected_qty if k.total_finalins_inspected_qty else 0.0 for k in resp__)
# 			total_finalins_rejection_qty = sum(k.total_finalins_rejected_qty if k.total_finalins_rejected_qty else 0.0 for k in resp__)
# 			if total_finalins_rejection_qty:
# 				__total_finalins_rejection =  (total_finalins_rejection_qty / total_finalins_inspected_qty) * 100
# 			else:
# 				__total_finalins_rejection = 0
# 			total_prod_qty_by_kgs = sum(k.prod_qty_by_kgs if k.prod_qty_by_kgs else 0 for k in resp__)
# 			total_prod_qty_by_lift = sum(k.prod_qty_by_lift if k.prod_qty_by_lift else 0 for k in resp__)
# 			total_def_rec_qty_kgs = sum(k.def_rec_qty_kgs if k.def_rec_qty_kgs else 0 for k in resp__)
# 		resp__.append({"batch_code":"<b>Total</b>","fg_qty_nos":fg_qty_nos,"fg_rejection":__total_finalins_rejection,"def_rejection_perc":__total_def_rejection,"def_rec_qty_kgs":total_def_rec_qty_kgs,"prod_qty_by_kgs":total_prod_qty_by_kgs,"prod_qty_by_lift":total_prod_qty_by_lift,"line_rejection_perc":__total_line_rejection,"lot_rejection_perc":__total_lot_rejection})


# ( SELECT 
# 		CASE 
# 			WHEN 
# 				(LRT.qty_after_rejection_nos IS NULL
# 						OR LRT.qty_after_rejection_nos = 0)
# 			THEN 
# 				0
# 			ELSE 
# 				LRT.qty_after_rejection_nos
# 		END	
# 	FROM `tabLot Resource Tagging` LRT
# 		WHERE LRT.name = ( SELECT 
# 								name FROM `tabLot Resource Tagging` 
# 							WHERE scan_lot_no = LRT.scan_lot_no ORDER BY modified DESC LIMIT 1 )
# 			AND LRT.docstatus = 1
# 			AND LRT.scan_lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
# lrt_first_qty,