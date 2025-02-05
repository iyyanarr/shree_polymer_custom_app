# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(filters), get_datas(filters)
	return columns, data

def get_columns(filters):
	c__ = []
	c__.append(_('Lot No')+':Data:140')
	c__.append(_('Item')+':Link/Item:80')
	c__.append(_('Compound BOM No')+':Link/BOM:160')
	c__.append(_('Press No')+':Link/Workstation:175')
	c__.append(_('Moulding Operator')+':Link/Employee:150')
	if filters.get('report_type') == "Deflashing Rejection Report" or filters.get('report_type') == "Final Rejection Report":
		c__.append(_('Deflashing Operator')+':Link/Warehouse:200')
	c__.append(_('Mould Ref')+':Data:120')
	if filters.get('report_type') == "Final Rejection Report":
		c__.append(_('Trimming ID Operator')+':Link/Employee:130')
		c__.append(_('Trimming OD Operator')+':Link/Employee:130')
	c__.append(_('Production Qty Nos')+':Int:160')
	c__.append(_('Compound Consumed Qty Kgs')+':Float:220')
	if filters.get('show_rejection_qty'):
		# c__.append(_('Line Inspected Qty Nos')+':Float:180')
		c__.append(_('Line Rejection Nos')+':Float:160')
	c__.append(_('Line Rejection')+':Percent:120')
	if filters.get('show_rejection_qty'):
		# c__.append(_('Patrol Inspected Qty Nos')+':Float:180')
		c__.append(_('Patrol Rejection Nos')+':Float:160')
	c__.append(_('Patrol Rejection')+':Percent:130')
	if filters.get('show_rejection_qty'):
		# c__.append(_('Lot Inspected Qty Nos')+':Float:180')
		c__.append(_('Lot Rejection Nos')+':Float:160')
	c__.append(_('Lot Rejection')+':Percent:120')
	if filters.get('report_type') == "Deflashing Rejection Report" or filters.get('report_type') == "Final Rejection Report":
		if filters.get('show_rejection_qty'):
			# c__.append(_('Incoming Inspected Qty Nos')+':Float:180')
			c__.append(_('Incoming Rejection Nos')+':Float:180')
		c__.append(_('Incoming Rejection')+':Percent:160')
	if filters.get('report_type') == "Final Rejection Report":
		if filters.get('show_rejection_qty'):
			# c__.append(_('Final Inspected Qty Nos')+':Float:180')
			c__.append(_('Final Rejection Nos')+':Float:180')
		c__.append(_('Final Rejection')+':Percent:120')
	c__.append(_('Total Rejection')+':Percent:120')
	return c__

def get_datas(filters):
	query = None
	condition = ""
	if filters.get('report_type') == "Line Rejection Report":
		if filters.get('date'):
			condition += f""" AND DATE(WP.date) = '{filters.get('date')}' """
		if filters.get('t_item'):
			condition += f""" AND MPE.item_to_produce = '{filters.get('t_item')}' """
		if filters.get('compound_bom_no'):
			condition += f""" AND SE.bom_no = '{filters.get('compound_bom_no')}' """
		if filters.get('press_no'):
			condition += f""" AND BBIS.press = '{filters.get('press_no')}' """
		if filters.get('moulding_operator'):
			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
		if filters.get('mould_ref'):
			condition += f""" AND BBIS.mould = '{filters.get('mould_ref')}' """
		query = f""" SELECT date_,
						lot_no,item,compound_bom_no,press_no,moulding_operator,mould_ref,
							ROUND((qty/avg_blank_wtproduct_kgs),0) 
						production_qty_nos,
						compound_consumed_qty_kgs,
							line_rejected_qty_nos
						line_rejection_nos,
							line_rejection_percent
						line_rejection,
							patrol_rejected_qty_nos
						patrol_rejection_nos,
							patrol_rejection_percent
						patrol_rejection,
							lot_rejected_qty_nos
						lot_rejection_nos,
							lot_rejection_percent
						lot_rejection,
							((patrol_rejected_qty_nos + line_rejected_qty_nos + lot_rejected_qty_nos) 
								/ (patrol_inspected_qty + line_inspected_qty + lot_inspected_qty)) * 100
						total_rejection,
						 patrol_inspected_qty patrol_inspected_qty_nos,line_inspected_qty line_inspected_qty_nos,lot_inspected_qty lot_inspected_qty_nos
					FROM 
						( SELECT WP.date date_,
							MPE.scan_lot_number lot_no,MPE.item_to_produce item,SE.bom_no compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
							BBIS.press press_no,MPE.employee moulding_operator,
							BBIS.mould mould_ref,
								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
									ELSE 0 END 
							avg_blank_wtproduct_kgs,
								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
								  WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name LIMIT 1)
							compound_consumed_qty_kgs,
								CASE 
									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
										THEN LINE.total_rejected_qty 
									ELSE 0.0 
							END line_rejected_qty_nos,
								CASE 
									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END line_rejection_percent,
								CASE 
									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
										THEN LINE.inspected_qty_nos 
									ELSE 0.0 
							END line_inspected_qty,

								CASE 
									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
										THEN PINE.total_rejected_qty 
									ELSE 0.0 
							END patrol_rejected_qty_nos,
								CASE 
									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN PINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END patrol_rejection_percent,
								CASE 
									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
										THEN PINE.inspected_qty_nos 
									ELSE 0.0 
							END patrol_inspected_qty,

								CASE 
									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
										THEN LOINE.total_rejected_qty 
									ELSE 0.0 
							END lot_rejected_qty_nos,
								CASE 
									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LOINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END lot_rejection_percent,
								CASE 
									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
										THEN LOINE.inspected_qty_nos 
									ELSE 0.0 
							END lot_inspected_qty
						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabWork Plan Item` WPI ON WPI.job_card = MPE.job_card AND WPI.docstatus = 1
							INNER JOIN `tabWork Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
							INNER JOIN `tabBlank Bin Issue` BBIS ON 
								BBIS.name = ( SELECT SBBIS.name FROM `tabBlank Bin Issue` SBBIS
												WHERE SBBIS.scan_production_lot = MPE.scan_lot_number 
													AND SBBIS.docstatus = 1 LIMIT 1 )
							INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference
							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.docstatus = 1
							INNER JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
							INNER JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
							INNER JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
								AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
						WHERE SED.t_warehouse IS NOT NULL
							   AND MPE.docstatus = 1 
							   AND SE.docstatus = 1 
							   AND BBIS.docstatus = 1 
							   {condition}
					UNION ALL
						
						SELECT WP.date date_,
							MPE.scan_lot_number lot_no,MPE.item_to_produce item,SE.bom_no compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
							BBIS.press press_no,MPE.employee moulding_operator,
							BBIS.mould mould_ref,
								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
									ELSE 0 END 
							avg_blank_wtproduct_kgs,
								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
								  WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name LIMIT 1)
							compound_consumed_qty_kgs,
								CASE 
									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
										THEN LINE.total_rejected_qty 
									ELSE 0.0 
							END line_rejected_qty_nos,
								CASE 
									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END line_rejection_percent,
								CASE 
									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
										THEN LINE.inspected_qty_nos 
									ELSE 0.0 
							END line_inspected_qty,

								CASE 
									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
										THEN PINE.total_rejected_qty 
									ELSE 0.0 
							END patrol_rejected_qty_nos,
								CASE 
									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN PINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END patrol_rejection_percent,
								CASE 
									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
										THEN PINE.inspected_qty_nos 
									ELSE 0.0 
							END patrol_inspected_qty,

								CASE 
									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
										THEN LOINE.total_rejected_qty 
									ELSE 0.0 
							END lot_rejected_qty_nos,
								CASE 
									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LOINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END lot_rejection_percent,
								CASE 
									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
										THEN LOINE.inspected_qty_nos 
									ELSE 0.0 
							END lot_inspected_qty
						FROM 
							`tabMoulding Production Entry` MPE 
							INNER JOIN `tabAdd On Work Plan Item` WPI ON WPI.job_card = MPE.job_card AND WPI.docstatus = 1
							INNER JOIN `tabAdd On Work Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
							INNER JOIN `tabBlank Bin Issue` BBIS ON 
								BBIS.name = ( SELECT SBBIS.name FROM `tabBlank Bin Issue` SBBIS
												WHERE SBBIS.scan_production_lot = MPE.scan_lot_number 
													AND SBBIS.docstatus = 1 LIMIT 1 )
							INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference
							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.docstatus = 1
							INNER JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
							INNER JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
							INNER JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
								AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
						WHERE SED.t_warehouse IS NOT NULL
							   AND MPE.docstatus = 1 
							   AND SE.docstatus = 1 
							   AND BBIS.docstatus = 1 
							   {condition} ) 
					DEMO ORDER BY date_ DESC """	
		result__ = frappe.db.sql(query , as_dict = 1) 
		if result__:
			total_production_qty_nos = 0.0
			total_compound_consumed_qty_kgs = 0.0
			total_patrol_inspected_qty_nos = 0.0
			total_patrol_rejected_qty_nos = 0.0
			total_line_inspected_qty_nos = 0.0
			total_line_rejected_qty_nos = 0.0
			total_lot_inspected_qty_nos = 0.0
			total_lot_rejected_qty_nos = 0.0
			for x in result__:
				if x.production_qty_nos:
					total_production_qty_nos += x.production_qty_nos
				if x.compound_consumed_qty_kgs:
					total_compound_consumed_qty_kgs += x.compound_consumed_qty_kgs
				if x.patrol_inspected_qty_nos:
					total_patrol_inspected_qty_nos += x.patrol_inspected_qty_nos
				if x.patrol_rejection_nos:
					total_patrol_rejected_qty_nos += x.patrol_rejection_nos
				if x.line_inspected_qty_nos:
					total_line_inspected_qty_nos += x.line_inspected_qty_nos
				if x.line_rejection_nos:
					total_line_rejected_qty_nos += x.line_rejection_nos
				if x.lot_inspected_qty_nos:
					total_lot_inspected_qty_nos += x.lot_inspected_qty_nos
				if x.lot_rejection_nos:
					total_lot_rejected_qty_nos += x.lot_rejection_nos
			result__.append({"mould_ref":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
							"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
							# "line_rejection_nos":((total_line_rejected_qty_nos / total_line_inspected_qty_nos )) if total_line_inspected_qty_nos else 0.0,
							"line_rejection":((total_line_rejected_qty_nos / total_line_inspected_qty_nos ) * 100) if total_line_inspected_qty_nos else 0.0,
							# "patrol_rejection_nos":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos )) if total_patrol_inspected_qty_nos else 0.0,
							"patrol_rejection":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos ) * 100) if total_patrol_inspected_qty_nos else 0.0,
							# "lot_rejection_nos":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos )) if total_lot_inspected_qty_nos else 0.0,
							"lot_rejection":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos ) * 100) if total_lot_inspected_qty_nos else 0.0,
							"total_rejection":(((total_line_rejected_qty_nos + total_patrol_rejected_qty_nos + total_lot_rejected_qty_nos) /
												(total_line_inspected_qty_nos + total_patrol_inspected_qty_nos + total_lot_inspected_qty_nos)) * 100) if (total_line_inspected_qty_nos + total_patrol_inspected_qty_nos + total_lot_inspected_qty_nos) else 0.0})
		return result__
	elif filters.get('report_type') == "Deflashing Rejection Report":
		if filters.get('date'):
			condition += f""" AND DATE(INE.posting_date) = '{filters.get('date')}' """
		if filters.get('p_item'):
			condition += f""" AND B.item = '{filters.get('p_item')}' """
		if filters.get('compound_bom_no'):
			condition += f""" AND CB.name = '{filters.get('compound_bom_no')}' """
		if filters.get('press_no'):
			condition += f""" AND BBIS.press = '{filters.get('press_no')}' """
		if filters.get('moulding_operator'):
			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
		if filters.get('mould_ref'):
			condition += f""" AND BBIS.mould = '{filters.get('mould_ref')}' """
		if filters.get('deflashing_operator'):
			condition += f""" AND DFR.from_warehouse_id = '{filters.get('deflashing_operator')}' """
		query = f""" SELECT 
						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
						ROUND(qty,0) production_qty_nos,
						compound_consumed_qty_kgs,
							line_rejected_qty_nos
						line_rejection_nos,
							line_rejection_percent
						line_rejection,
							patrol_rejected_qty_nos
						patrol_rejection_nos,
							patrol_rejection_percent
						patrol_rejection,
							lot_rejected_qty_nos
						lot_rejection_nos,
							lot_rejection_percent
						lot_rejection,
							incoming_rejected_qty_nos
						incoming_rejection_nos,
							incoming_rejection_percent
						incoming_rejection,

						 patrol_inspected_qty patrol_inspected_qty_nos,line_inspected_qty line_inspected_qty_nos,
						 lot_inspected_qty lot_inspected_qty_nos,incoming_inspected_qty_nos

					FROM 
						( SELECT 
							DFR.scan_lot_number lot_no,B.item,CB.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
							BBIS.press press_no,MPE.employee moulding_operator,DFR.from_warehouse_id deflashing_operator,
							BBIS.mould mould_ref,
								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
								  WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
							compound_consumed_qty_kgs,

							CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
									ELSE 0 END 
							avg_blank_wtproduct_kgs,
							
								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
										INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
									WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
							moulding_prod_qty,
							
								CASE 
									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
										THEN LINE.total_rejected_qty 
									ELSE 0.0 
							END line_rejected_qty_nos,
								CASE 
									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END line_rejection_percent,
								CASE 
									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
										THEN LINE.inspected_qty_nos 
									ELSE 0.0 
							END line_inspected_qty,

								CASE 
									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
										THEN PINE.total_rejected_qty 
									ELSE 0.0 
							END patrol_rejected_qty_nos,
								CASE 
									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN PINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END patrol_rejection_percent,
								CASE 
									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
										THEN PINE.inspected_qty_nos 
									ELSE 0.0 
							END patrol_inspected_qty,

								CASE 
									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
										THEN LOINE.total_rejected_qty 
									ELSE 0.0 
							END lot_rejected_qty_nos,
								CASE 
									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LOINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END lot_rejection_percent,
								CASE 
									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
										THEN LOINE.inspected_qty_nos 
									ELSE 0.0 
							END lot_inspected_qty,

								CASE 
									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
										THEN INE.total_rejected_qty 
									ELSE 0.0 
							END incoming_rejected_qty_nos,
								CASE 
									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
										THEN INE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END incoming_rejection_percent,
								CASE 
									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
										THEN INE.total_inspected_qty_nos 
									ELSE 0.0 
							END incoming_inspected_qty_nos
						FROM 
							`tabDeflashing Receipt Entry` DFR 
							INNER JOIN `tabBOM Item` BI ON BI.item_code = DFR.item AND DFR.docstatus = 1
							INNER JOIN `tabBOM` B ON BI.parent = B.name AND B.is_active=1 AND B.is_default=1
							INNER JOIN `tabBOM` CB ON CB.Item = DFR.item AND CB.is_active=1 AND CB.is_default=1
							INNER JOIN `tabBOM Item` CBI ON CBI.parent = CB.name 
							INNER JOIN `tabStock Entry` SE ON SE.name = DFR.stock_entry_reference AND SE.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.is_finished_item = 1
							INNER JOIN `tabBlank Bin Issue` BBIS ON 
								BBIS.name = ( SELECT SBBIS.name FROM `tabBlank Bin Issue` SBBIS
												WHERE SBBIS.scan_production_lot = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1)
													AND SBBIS.docstatus = 1 LIMIT 1 ) AND BBIS.docstatus = 1
							LEFT JOIN `tabMoulding Production Entry` MPE ON 
									MPE.scan_lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1) AND MPE.docstatus = 1
							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
								AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference 
								AND MSE.docstatus = 1
							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
							INNER JOIN `tabInspection Entry` INE ON INE.lot_no = DFR.scan_lot_number 
								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
						WHERE SED.t_warehouse IS NOT NULL {condition} ) 
					DEMO """
		result__ = frappe.db.sql(query , as_dict = 1) 
		# frappe.log_error(title='------',message=result__)
		if result__:
			total_production_qty_nos = 0.0
			total_compound_consumed_qty_kgs = 0.0
			total_patrol_inspected_qty_nos = 0.0
			total_patrol_rejected_qty_nos = 0.0
			total_line_inspected_qty_nos = 0.0
			total_line_rejected_qty_nos = 0.0
			total_lot_inspected_qty_nos = 0.0
			total_lot_rejected_qty_nos = 0.0
			total_incoming_rejected_qty_nos = 0.0
			total_incoming_inspected_qty_nos = 0.0
			for x in result__:
				try:
					if x.production_qty_nos:
						total_production_qty_nos += x.production_qty_nos
					if x.compound_consumed_qty_kgs:
						total_compound_consumed_qty_kgs += x.compound_consumed_qty_kgs
					if x.patrol_inspected_qty_nos:
						total_patrol_inspected_qty_nos += x.patrol_inspected_qty_nos
					if x.patrol_rejection_nos:
						total_patrol_rejected_qty_nos += x.patrol_rejection_nos
					if x.line_inspected_qty_nos:
						total_line_inspected_qty_nos += x.line_inspected_qty_nos
					if x.line_rejection_nos:
						total_line_rejected_qty_nos += x.line_rejection_nos
					if x.lot_inspected_qty_nos:
						total_lot_inspected_qty_nos += x.lot_inspected_qty_nos
					if x.lot_rejection_nos:
						total_lot_rejected_qty_nos += x.lot_rejection_nos
					if x.incoming_inspected_qty_nos:
						total_incoming_inspected_qty_nos += x.incoming_inspected_qty_nos
					if x.incoming_rejection_nos:
						total_incoming_rejected_qty_nos += x.incoming_rejection_nos
				
					x['total_rejection'] = (
							( ( x.patrol_rejection_nos if x.patrol_rejection_nos else 0.0) 
								+ ( x.line_rejection_nos if x.line_rejection_nos else 0.0)
									+ ( x.lot_rejection_nos if x.lot_rejection_nos else 0.0)
										+ x.incoming_rejection_nos if x.incoming_rejection_nos else 0.0
							) /

							( ( x.patrol_inspected_qty_nos if x.patrol_inspected_qty_nos else 0.0)
								+ ( x.line_inspected_qty_nos if  x.line_inspected_qty_nos else 0.0)
									+ ( x.lot_inspected_qty_nos if x.lot_inspected_qty_nos else 0.0)
										+ x.incoming_inspected_qty_nos if x.incoming_inspected_qty_nos else 0.0
							)
						) * 100
				except ZeroDivisionError:
					x['total_rejection'] = 0
			result__.append({"mould_ref":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
									"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
									# "line_rejection_nos":((total_line_rejected_qty_nos / total_line_inspected_qty_nos )) if total_line_inspected_qty_nos else 0.0,
									"line_rejection":((total_line_rejected_qty_nos / total_line_inspected_qty_nos ) * 100) if total_line_inspected_qty_nos else 0.0,
									# "patrol_rejection_nos":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos )) if total_patrol_inspected_qty_nos else 0.0,
									"patrol_rejection":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos ) * 100) if total_patrol_inspected_qty_nos else 0.0,
									# "lot_rejection_nos":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos )) if total_lot_inspected_qty_nos else 0.0,
									"lot_rejection":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos ) * 100) if total_lot_inspected_qty_nos else 0.0,
									# "incoming_rejection_nos":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos )) if total_incoming_inspected_qty_nos else 0.0,
									"incoming_rejection":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos ) * 100) if total_incoming_inspected_qty_nos else 0.0,
									"total_rejection":(((total_patrol_rejected_qty_nos + total_line_rejected_qty_nos + total_lot_rejected_qty_nos + total_incoming_rejected_qty_nos) /
														(total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos)) * 100) if (total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos) else 0.0})
		return result__	
	elif filters.get('report_type') == "Final Rejection Report":
		if filters.get('date'):
			condition += f""" AND DATE(VSINE.posting_date) = '{filters.get('date')}' """
		if filters.get('f_item'):
			condition += f""" AND VSINE.product_ref_no = '{filters.get('f_item')}' """
		if filters.get('compound_bom_no'):
			condition += f""" AND B.name = '{filters.get('compound_bom_no')}' """
		if filters.get('press_no'):
			condition += f""" AND BBIS.press = '{filters.get('press_no')}' """
		if filters.get('moulding_operator'):
			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
		if filters.get('mould_ref'):
			condition += f""" AND BBIS.mould = '{filters.get('mould_ref')}' """
		if filters.get('deflashing_operator'):
			condition += f""" AND VSINE.source_warehouse = '{filters.get('deflashing_operator')}' """
		if filters.get('trimming_id__operator'):
			condition += f""" AND LRT.operator_id = '{filters.get('trimming_id__operator')}' AND operation_type = 'Trimming ID' """
		if filters.get('trimming_od_operator'):
			condition += f""" AND LRT.operator_id = '{filters.get('trimming_od_operator')}' AND operation_type = 'Trimming OD' """
		query = f""" SELECT 
						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
						trimming_id_operator,trimming_od_operator,ROUND(qty,0) production_qty_nos,
						compound_consumed_qty_kgs,
							line_rejected_qty_nos
						line_rejection_nos,
							line_rejection_percent
						line_rejection,
							patrol_rejected_qty_nos
						patrol_rejection_nos,
							patrol_rejection_percent
						patrol_rejection,
							lot_rejected_qty_nos
						lot_rejection_nos,
							lot_rejection_percent
						lot_rejection,
							incoming_rejected_qty_nos
						incoming_rejection_nos,
							incoming_rejection_percent
						incoming_rejection,
							final_rejected_qty_nos
						final_rejection_nos,
							final_rejection_percent
						final_rejection,

						line_inspected_qty line_inspected_qty_nos,
						patrol_inspected_qty patrol_inspected_qty_nos,
						lot_inspected_qty lot_inspected_qty_nos,
						incoming_inspected_qty_nos,final_inspected_qty_nos
							
					FROM 
						( SELECT 
							VSINE.lot_no lot_no,VSINE.product_ref_no item,B.name compound_bom_no,SUM(CAST(SED.qty as DECIMAL(10,3))) qty,
							LRT.operator_id trimming_id_operator,OLRT.operator_id trimming_od_operator,
							BBIS.press press_no,MPE.employee moulding_operator,
							(CASE 
							    WHEN (VSINE.source_warehouse IS NOT NULL AND VSINE.source_warehouse != '') 
									THEN VSINE.source_warehouse
										ELSE 
											(SELECT DRE.warehouse 
												FROM `tabDeflashing Receipt Entry` DRE 
													WHERE 
														(CASE 
															WHEN DRE.scan_lot_number = VSINE.lot_no 
																THEN DRE.scan_lot_number=VSINE.lot_no
														ELSE 
															DRE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
													END) AND DRE.docstatus = 1 LIMIT 1)
							END) deflashing_operator,
								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
										ELSE 0 END 
							avg_blank_wtproduct_kgs,
								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
											INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
										WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
							moulding_prod_qty,
							BBIS.mould mould_ref,
								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
										INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
									WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
							compound_consumed_qty_kgs,	

								CASE 
									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
										THEN LINE.total_rejected_qty 
									ELSE 0.0 
							END line_rejected_qty_nos,
								CASE 
									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END line_rejection_percent,
								CASE 
									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
										THEN LINE.inspected_qty_nos 
									ELSE 0.0 
							END line_inspected_qty,

								CASE 
									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
										THEN PINE.total_rejected_qty 
									ELSE 0.0 
							END patrol_rejected_qty_nos,
								CASE 
									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN PINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END patrol_rejection_percent,
								CASE 
									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
										THEN PINE.inspected_qty_nos 
									ELSE 0.0 
							END patrol_inspected_qty,

								CASE 
									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
										THEN LOINE.total_rejected_qty 
									ELSE 0.0 
							END lot_rejected_qty_nos,
								CASE 
									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN LOINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END lot_rejection_percent,
								CASE 
									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
										THEN LOINE.inspected_qty_nos 
									ELSE 0.0 
							END lot_inspected_qty,

								CASE 
									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
										THEN INE.total_rejected_qty 
									ELSE 0.0 
							END incoming_rejected_qty_nos,
								CASE 
									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
										THEN INE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END incoming_rejection_percent,
								CASE 
									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
										THEN INE.total_inspected_qty_nos 
									ELSE 0.0 
							END incoming_inspected_qty_nos,

								CASE 
									WHEN VSINE.total_rejected_qty  != 0 AND VSINE.total_rejected_qty IS NOT NULL
										THEN SUM(VSINE.total_rejected_qty)
									ELSE 0.0 
							END final_rejected_qty_nos,
								CASE 
									WHEN VSINE.total_rejected_qty_in_percentage  != 0 AND VSINE.total_rejected_qty_in_percentage IS NOT NULL
										THEN VSINE.total_rejected_qty_in_percentage 
									ELSE 0.0 
							END final_rejection_percent,
								CASE 
									WHEN VSINE.total_inspected_qty_nos  != 0 AND VSINE.total_inspected_qty_nos IS NOT NULL
										THEN SUM(VSINE.total_inspected_qty_nos)
									ELSE 0.0 
							END final_inspected_qty_nos,
									
								IFNULL((SELECT DFSED.qty FROM `tabStock Entry Detail` DFSED 
									INNER JOIN `tabStock Entry` DFSE ON DFSE.name = DFSED.parent
									INNER JOIN `tabDeflashing Receipt Entry` DFRE ON DFRE.stock_entry_reference = DFSE.name
								WHERE 
									DFRE.scan_lot_number= INE.lot_no AND DFSED.t_warehouse IS NOT NULL LIMIT 1),0) deflashing_receipt_qty
						FROM 
							`tabInspection Entry` VSINE 
							INNER JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
							INNER JOIN `tabBlank Bin Issue` BBIS ON 
								BBIS.name = ( SELECT SBBIS.name FROM `tabBlank Bin Issue` SBBIS
												WHERE SBBIS.scan_production_lot = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
													AND SBBIS.docstatus = 1 LIMIT 1 ) AND BBIS.docstatus = 1
							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.docstatus = 1 
								AND MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
								AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
							LEFT JOIN `tabBOM` B ON B.item = MPE.item_to_produce AND B.is_active=1 AND B.is_default=1
							INNER JOIN `tabBOM Item` BI ON BI.parent = B.name 
							INNER JOIN `tabItem` MMI ON MMI.name = BI.item_code
							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
							LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
							LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no AND LRT.operation_type = 'ID Trimming' AND LRT.docstatus = 1
							LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no AND OLRT.operation_type = 'OD Trimming' AND OLRT.docstatus = 1
						WHERE 
							SED.t_warehouse IS NOT NULL AND 
							(VSINE.inspection_type = "Final Visual Inspection" OR VSINE.inspection_type = "Visual Inspection") 
							AND VSINE.docstatus = 1 
							AND MMI.item_group = 'Compound' {condition} 
							GROUP BY VSINE.lot_no ) 
					DEMO """	
		result__ = frappe.db.sql(query , as_dict = 1)
		if result__:
			total_production_qty_nos = 0.0
			total_compound_consumed_qty_kgs = 0.0

			total_patrol_inspected_qty_nos = 0.0
			total_patrol_rejected_qty_nos = 0.0
			total_line_inspected_qty_nos = 0.0
			total_line_rejected_qty_nos = 0.0
			total_lot_inspected_qty_nos = 0.0
			total_lot_rejected_qty_nos = 0.0
			total_incoming_inspected_qty_nos = 0.0
			total_incoming_rejected_qty_nos = 0.0
			total_final_inspected_qty_nos = 0.0
			total_final_rejected_qty_nos = 0.0
			over_all_total_rejections_nos = 0.0
			over_all_total_inspected_nos = 0.0
			for rej in result__:
				# on 18/10/23 for multiple final visual inspection
				if rej.final_rejection_nos:	
					final_rejection = (rej.final_rejection_nos / rej.final_inspected_qty_nos) * 100
					rej.final_rejection = final_rejection
				# end
				total_rejections_nos = 0.0
				total_inspected_nos = 0.0
				try:
					if rej.production_qty_nos:
						total_production_qty_nos += rej.production_qty_nos
					if rej.compound_consumed_qty_kgs:
						total_compound_consumed_qty_kgs += rej.compound_consumed_qty_kgs

					if rej.patrol_inspected_qty_nos:
						total_patrol_inspected_qty_nos += rej.patrol_inspected_qty_nos
						total_inspected_nos += rej.patrol_inspected_qty_nos
					if rej.patrol_rejection_nos:
						total_patrol_rejected_qty_nos += rej.patrol_rejection_nos 
						total_rejections_nos += rej.patrol_rejection_nos 

					if rej.line_inspected_qty_nos:
						total_line_inspected_qty_nos += rej.line_inspected_qty_nos
						total_inspected_nos += rej.line_inspected_qty_nos 
					if rej.line_rejection_nos:
						total_line_rejected_qty_nos += rej.line_rejection_nos 
						total_rejections_nos += rej.line_rejection_nos 
						
					if rej.lot_inspected_qty_nos:
						total_lot_inspected_qty_nos += rej.lot_inspected_qty_nos
						total_inspected_nos += rej.lot_inspected_qty_nos 
					if rej.lot_rejection_nos:
						total_lot_rejected_qty_nos += rej.lot_rejection_nos 
						total_rejections_nos += rej.lot_rejection_nos 

					if rej.incoming_inspected_qty_nos:
						total_incoming_inspected_qty_nos += rej.incoming_inspected_qty_nos
						total_inspected_nos += rej.incoming_inspected_qty_nos 
					if rej.incoming_rejection_nos:
						total_incoming_rejected_qty_nos += rej.incoming_rejection_nos
						total_rejections_nos += rej.incoming_rejection_nos 

					if rej.final_inspected_qty_nos:
						total_final_inspected_qty_nos += rej.final_inspected_qty_nos
						total_inspected_nos += rej.final_inspected_qty_nos
					if rej.final_rejection_nos:
						total_final_rejected_qty_nos += rej.final_rejection_nos
						total_rejections_nos += rej.final_rejection_nos 

					rej['total_rejection'] = (total_rejections_nos / total_inspected_nos) * 100

					over_all_total_inspected_nos += total_inspected_nos
					over_all_total_rejections_nos += total_rejections_nos
				except ZeroDivisionError:
					rej['total_rejection'] = 0
			result__.append({"mould_ref":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
									"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
									"line_rejection_nos":((total_line_rejected_qty_nos / total_line_inspected_qty_nos )) if total_line_inspected_qty_nos else 0.0,
									"line_rejection":((total_line_rejected_qty_nos / total_line_inspected_qty_nos ) * 100) if total_line_inspected_qty_nos else 0.0,
									"patrol_rejection_nos":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos )) if total_patrol_inspected_qty_nos else 0.0,
									"patrol_rejection":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos ) * 100) if total_patrol_inspected_qty_nos else 0.0,
									"lot_rejection_nos":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos )) if total_lot_inspected_qty_nos else 0.0,
									"lot_rejection":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos ) * 100) if total_lot_inspected_qty_nos else 0.0,
									"incoming_rejection_nos":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos )) if total_incoming_inspected_qty_nos else 0.0,
									"incoming_rejection":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos ) * 100) if total_incoming_inspected_qty_nos else 0.0,
									"final_rejection_nos":((total_final_rejected_qty_nos / total_final_inspected_qty_nos )) if total_final_inspected_qty_nos else 0.0,
									"final_rejection":((total_final_rejected_qty_nos / total_final_inspected_qty_nos ) * 100) if total_final_inspected_qty_nos else 0.0,
									"total_rejection": (over_all_total_rejections_nos / over_all_total_inspected_nos )* 100})
		return result__	
	
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





# Back up on 18/10/23 final visual inspection query

# query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						trimming_id_operator,trimming_od_operator,ROUND(qty,0) production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_nos
# 						line_rejection_nos,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_nos
# 						patrol_rejection_nos,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_nos
# 						lot_rejection_nos,
# 							lot_rejection_percent
# 						lot_rejection,
# 							incoming_rejected_qty_nos
# 						incoming_rejection_nos,
# 							incoming_rejection_percent
# 						incoming_rejection,
# 							final_rejected_qty_nos
# 						final_rejection_nos,
# 							final_rejection_percent
# 						final_rejection,

# 						line_inspected_qty line_inspected_qty_nos,
# 						patrol_inspected_qty patrol_inspected_qty_nos,
# 						lot_inspected_qty lot_inspected_qty_nos,
# 						incoming_inspected_qty_nos,final_inspected_qty_nos
							
# 					FROM 
# 						( SELECT 
# 							VSINE.lot_no lot_no,VSINE.product_ref_no item,B.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							LRT.operator_id trimming_id_operator,OLRT.operator_id trimming_od_operator,
# 							BBIS.press press_no,MPE.employee moulding_operator,
# 							(CASE 
# 							    WHEN (VSINE.source_warehouse IS NOT NULL AND VSINE.source_warehouse != '') 
# 									THEN VSINE.source_warehouse
# 										ELSE 
# 											(SELECT DRE.warehouse 
# 												FROM `tabDeflashing Receipt Entry` DRE 
# 													WHERE 
# 														(CASE 
# 															WHEN DRE.scan_lot_number = VSINE.lot_no 
# 																THEN DRE.scan_lot_number=VSINE.lot_no
# 														ELSE 
# 															DRE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 													END) AND DRE.docstatus = 1 LIMIT 1)
# 							END) deflashing_operator,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 										ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 											INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 										WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
# 							BBIS.mould mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 										INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 									WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,	

# 								CASE 
# 									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
# 										THEN LINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END line_rejected_qty_nos,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
# 										THEN LINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END line_inspected_qty,

# 								CASE 
# 									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
# 										THEN PINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_nos,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
# 										THEN PINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
# 										THEN LOINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END lot_rejected_qty_nos,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
# 										THEN LOINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END lot_inspected_qty,

# 								CASE 
# 									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
# 										THEN INE.total_rejected_qty 
# 									ELSE 0.0 
# 							END incoming_rejected_qty_nos,
# 								CASE 
# 									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN INE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END incoming_rejection_percent,
# 								CASE 
# 									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
# 										THEN INE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END incoming_inspected_qty_nos,

# 								CASE 
# 									WHEN VSINE.total_rejected_qty  != 0 AND VSINE.total_rejected_qty IS NOT NULL
# 										THEN VSINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END final_rejected_qty_nos,
# 								CASE 
# 									WHEN VSINE.total_rejected_qty_in_percentage  != 0 AND VSINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN VSINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END final_rejection_percent,
# 								CASE 
# 									WHEN VSINE.total_inspected_qty_nos  != 0 AND VSINE.total_inspected_qty_nos IS NOT NULL
# 										THEN VSINE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END final_inspected_qty_nos,
									
# 								IFNULL((SELECT DFSED.qty FROM `tabStock Entry Detail` DFSED 
# 									INNER JOIN `tabStock Entry` DFSE ON DFSE.name = DFSED.parent
# 									INNER JOIN `tabDeflashing Receipt Entry` DFRE ON DFRE.stock_entry_reference = DFSE.name
# 								WHERE 
# 									DFRE.scan_lot_number= INE.lot_no AND DFSED.t_warehouse IS NOT NULL LIMIT 1),0) deflashing_receipt_qty
# 						FROM 
# 							`tabInspection Entry` VSINE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabBlank Bin Issue` BBIS ON 
# 								BBIS.name = ( SELECT SBBIS.name FROM `tabBlank Bin Issue` SBBIS
# 												WHERE SBBIS.scan_production_lot = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 													AND SBBIS.docstatus = 1 LIMIT 1 ) AND BBIS.docstatus = 1
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.docstatus = 1 
# 								AND MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
# 								AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
# 							LEFT JOIN `tabBOM` B ON B.item = MPE.item_to_produce AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM Item` BI ON BI.parent = B.name 
# 							INNER JOIN `tabItem` MMI ON MMI.name = BI.item_code
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no AND LRT.operation_type = 'ID Trimming' AND LRT.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no AND OLRT.operation_type = 'OD Trimming' AND OLRT.docstatus = 1
# 						WHERE 
# 							SED.t_warehouse IS NOT NULL AND 
# 							(VSINE.inspection_type = "Final Visual Inspection" OR VSINE.inspection_type = "Visual Inspection") 
# 							AND VSINE.docstatus = 1 
# 							AND MMI.item_group = 'Compound' {condition} ) 
# 					DEMO """	
# end






# def get_datas(filters):
# 	query = None
# 	condition = ""
# 	if filters.get('report_type') == "Line Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(LINE.modified) = '{filters.get('date')}' """
# 		if filters.get('t_item'):
# 			condition += f""" AND WPI.item = '{filters.get('t_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND SE.bom_no = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,mould_ref,
# 							(qty/avg_blank_wtproduct_kgs) 
# 						production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_nos
# 						line_rejection_nos,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_nos
# 						patrol_rejection_nos,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_nos
# 						lot_rejection_nos,
# 							lot_rejection_percent
# 						lot_rejection,
# 							((patrol_rejected_qty_nos + line_rejected_qty_nos + lot_rejected_qty_nos) 
# 								/ (patrol_inspected_qty + line_inspected_qty + lot_inspected_qty)) * 100
# 						total_rejection,
# 						 patrol_inspected_qty patrol_inspected_qty_nos,line_inspected_qty line_inspected_qty_nos,lot_inspected_qty lot_inspected_qty_nos
# 					FROM 
# 						( SELECT 
# 							MPE.scan_lot_number lot_no,WPI.item,SE.bom_no compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							WPI.work_station press_no,MPE.employee moulding_operator,
# 							(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 									ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 								  WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name LIMIT 1)
# 							compound_consumed_qty_kgs,
# 								CASE 
# 									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
# 										THEN LINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END line_rejected_qty_nos,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
# 										THEN LINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END line_inspected_qty,

# 								CASE 
# 									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
# 										THEN PINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_nos,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
# 										THEN PINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
# 										THEN LOINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END lot_rejected_qty_nos,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
# 										THEN LOINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END lot_inspected_qty
# 						FROM 
# 							`tabMoulding Production Entry` MPE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference AND MPE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.docstatus = 1
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = MPE.scan_lot_number AND WPI.docstatus = 1
# 							INNER JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							INNER JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 						WHERE SED.t_warehouse IS NOT NULL AND SE.docstatus = 1 AND WPI.docstatus = 1 {condition} ) 
# 					DEMO """	
# 		result__ = frappe.db.sql(query , as_dict = 1) 
# 		if result__:
# 			total_production_qty_nos = 0.0
# 			total_compound_consumed_qty_kgs = 0.0
# 			total_patrol_inspected_qty_nos = 0.0
# 			total_patrol_rejected_qty_nos = 0.0
# 			total_line_inspected_qty_nos = 0.0
# 			total_line_rejected_qty_nos = 0.0
# 			total_lot_inspected_qty_nos = 0.0
# 			total_lot_rejected_qty_nos = 0.0
# 			for x in result__:
# 				if x.production_qty_nos:
# 					total_production_qty_nos += x.production_qty_nos
# 				if x.compound_consumed_qty_kgs:
# 					total_compound_consumed_qty_kgs += x.compound_consumed_qty_kgs
# 				if x.patrol_inspected_qty_nos:
# 					total_patrol_inspected_qty_nos += x.patrol_inspected_qty_nos
# 				if x.patrol_rejection_nos:
# 					total_patrol_rejected_qty_nos += x.patrol_rejection_nos
# 				if x.line_inspected_qty_nos:
# 					total_line_inspected_qty_nos += x.line_inspected_qty_nos
# 				if x.line_rejection_nos:
# 					total_line_rejected_qty_nos += x.line_rejection_nos
# 				if x.lot_inspected_qty_nos:
# 					total_lot_inspected_qty_nos += x.lot_inspected_qty_nos
# 				if x.lot_rejection_nos:
# 					total_lot_rejected_qty_nos += x.lot_rejection_nos
# 			result__.append({"mould_ref":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
# 							"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
# 							# "line_rejection_nos":((total_line_rejected_qty_nos / total_line_inspected_qty_nos )) if total_line_inspected_qty_nos else 0.0,
# 							"line_rejection":((total_line_rejected_qty_nos / total_line_inspected_qty_nos ) * 100) if total_line_inspected_qty_nos else 0.0,
# 							# "patrol_rejection_nos":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos )) if total_patrol_inspected_qty_nos else 0.0,
# 							"patrol_rejection":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos ) * 100) if total_patrol_inspected_qty_nos else 0.0,
# 							# "lot_rejection_nos":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos )) if total_lot_inspected_qty_nos else 0.0,
# 							"lot_rejection":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos ) * 100) if total_lot_inspected_qty_nos else 0.0,
# 							"total_rejection":(((total_line_rejected_qty_nos + total_patrol_rejected_qty_nos + total_lot_rejected_qty_nos) /
# 												(total_line_inspected_qty_nos + total_patrol_inspected_qty_nos + total_lot_inspected_qty_nos)) * 100) if (total_line_inspected_qty_nos + total_patrol_inspected_qty_nos + total_lot_inspected_qty_nos) else 0.0})
# 		return result__
# 	elif filters.get('report_type') == "Deflashing Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(INE.modified) = '{filters.get('date')}' """
# 		if filters.get('p_item'):
# 			condition += f""" AND B.item = '{filters.get('p_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND CB.name = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		if filters.get('deflashing_operator'):
# 			condition += f""" AND DFR.from_warehouse_id = '{filters.get('deflashing_operator')}' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						qty production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_nos
# 						line_rejection_nos,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_nos
# 						patrol_rejection_nos,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_nos
# 						lot_rejection_nos,
# 							lot_rejection_percent
# 						lot_rejection,
# 							incoming_rejected_qty_nos
# 						incoming_rejection_nos,
# 							incoming_rejection_percent
# 						incoming_rejection,

# 						 patrol_inspected_qty patrol_inspected_qty_nos,line_inspected_qty line_inspected_qty_nos,
# 						 lot_inspected_qty lot_inspected_qty_nos,incoming_inspected_qty_nos

# 					FROM 
# 						( SELECT 
# 							DFR.scan_lot_number lot_no,B.item,CB.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							WPI.work_station press_no,MPE.employee moulding_operator,DFR.from_warehouse_id deflashing_operator,
# 								(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 								  WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,

# 							CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 									ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
							
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 										INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 									WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
							
# 								CASE 
# 									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
# 										THEN LINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END line_rejected_qty_nos,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
# 										THEN LINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END line_inspected_qty,

# 								CASE 
# 									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
# 										THEN PINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_nos,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
# 										THEN PINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
# 										THEN LOINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END lot_rejected_qty_nos,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
# 										THEN LOINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END lot_inspected_qty,

# 								CASE 
# 									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
# 										THEN INE.total_rejected_qty 
# 									ELSE 0.0 
# 							END incoming_rejected_qty_nos,
# 								CASE 
# 									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN INE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END incoming_rejection_percent,
# 								CASE 
# 									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
# 										THEN INE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END incoming_inspected_qty_nos
# 						FROM 
# 							`tabDeflashing Receipt Entry` DFR 
# 							INNER JOIN `tabBOM Item` BI ON BI.item_code = DFR.item AND DFR.docstatus = 1
# 							INNER JOIN `tabBOM` B ON BI.parent = B.name AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM` CB ON CB.Item = DFR.item AND CB.is_active=1 AND CB.is_default=1
# 							INNER JOIN `tabBOM Item` CBI ON CBI.parent = CB.name 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = DFR.stock_entry_reference AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.is_finished_item = 1
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1) AND WPI.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.scan_lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1) AND MPE.docstatus = 1
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							INNER JOIN `tabInspection Entry` INE ON INE.lot_no = DFR.scan_lot_number 
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 						WHERE SED.t_warehouse IS NOT NULL {condition} ) 
# 					DEMO """
# 		result__ = frappe.db.sql(query , as_dict = 1) 
# 		if result__:
# 			total_production_qty_nos = 0.0
# 			total_compound_consumed_qty_kgs = 0.0
# 			total_patrol_inspected_qty_nos = 0.0
# 			total_patrol_rejected_qty_nos = 0.0
# 			total_line_inspected_qty_nos = 0.0
# 			total_line_rejected_qty_nos = 0.0
# 			total_lot_inspected_qty_nos = 0.0
# 			total_lot_rejected_qty_nos = 0.0
# 			total_incoming_rejected_qty_nos = 0.0
# 			total_incoming_inspected_qty_nos = 0.0
# 			for x in result__:
# 				try:
# 					if x.production_qty_nos:
# 						total_production_qty_nos += x.production_qty_nos
# 					if x.compound_consumed_qty_kgs:
# 						total_compound_consumed_qty_kgs += x.compound_consumed_qty_kgs
# 					if x.patrol_inspected_qty_nos:
# 						total_patrol_inspected_qty_nos += x.patrol_inspected_qty_nos
# 					if x.patrol_rejection_nos:
# 						total_patrol_rejected_qty_nos += x.patrol_rejection_nos
# 					if x.line_inspected_qty_nos:
# 						total_line_inspected_qty_nos += x.line_inspected_qty_nos
# 					if x.line_rejection_nos:
# 						total_line_rejected_qty_nos += x.line_rejection_nos
# 					if x.lot_inspected_qty_nos:
# 						total_lot_inspected_qty_nos += x.lot_inspected_qty_nos
# 					if x.lot_rejection_nos:
# 						total_lot_rejected_qty_nos += x.lot_rejection_nos
# 					if x.incoming_inspected_qty_nos:
# 						total_incoming_inspected_qty_nos += x.incoming_inspected_qty_nos
# 					if x.incoming_rejection_nos:
# 						total_incoming_rejected_qty_nos += x.incoming_rejection_nos
				
# 					x['total_rejection'] = (
# 							( ( x.patrol_rejection_nos if x.patrol_rejection_nos else 0.0) 
# 								+ ( x.line_rejection_nos if x.line_rejection_nos else 0.0)
# 									+ ( x.lot_rejection_nos if x.lot_rejection_nos else 0.0)
# 										+ x.incoming_rejection_nos if x.incoming_rejection_nos else 0.0
# 							) /

# 							( ( x.patrol_inspected_qty_nos if x.patrol_inspected_qty_nos else 0.0)
# 								+ ( x.line_inspected_qty_nos if  x.line_inspected_qty_nos else 0.0)
# 									+ ( x.lot_inspected_qty_nos if x.lot_inspected_qty_nos else 0.0)
# 										+ x.incoming_inspected_qty_nos if x.incoming_inspected_qty_nos else 0.0
# 							)
# 						) * 100
					
# 				except ZeroDivisionError:
# 					x['total_rejection'] = 0
# 			result__.append({"mould_ref":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
# 									"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
# 									# "line_rejection_nos":((total_line_rejected_qty_nos / total_line_inspected_qty_nos )) if total_line_inspected_qty_nos else 0.0,
# 									"line_rejection":((total_line_rejected_qty_nos / total_line_inspected_qty_nos ) * 100) if total_line_inspected_qty_nos else 0.0,
# 									# "patrol_rejection_nos":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos )) if total_patrol_inspected_qty_nos else 0.0,
# 									"patrol_rejection":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos ) * 100) if total_patrol_inspected_qty_nos else 0.0,
# 									# "lot_rejection_nos":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos )) if total_lot_inspected_qty_nos else 0.0,
# 									"lot_rejection":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos ) * 100) if total_lot_inspected_qty_nos else 0.0,
# 									# "incoming_rejection_nos":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos )) if total_incoming_inspected_qty_nos else 0.0,
# 									"incoming_rejection":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos ) * 100) if total_incoming_inspected_qty_nos else 0.0,
# 									"total_rejection":(((total_patrol_rejected_qty_nos + total_line_rejected_qty_nos + total_lot_rejected_qty_nos + total_incoming_rejected_qty_nos) /
# 														(total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos)) * 100) if (total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos) else 0.0})
# 		return result__	
# 	elif filters.get('report_type') == "Final Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(VSINE.modified) = '{filters.get('date')}' """
# 		if filters.get('f_item'):
# 			condition += f""" AND VSINE.product_ref_no = '{filters.get('f_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND B.name = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		if filters.get('deflashing_operator'):
# 			condition += f""" AND VSINE.source_warehouse = '{filters.get('deflashing_operator')}' """
# 		if filters.get('trimming_id__operator'):
# 			condition += f""" AND LRT.operator_id = '{filters.get('trimming_id__operator')}' AND operation_type = 'Trimming ID' """
# 		if filters.get('trimming_od_operator'):
# 			condition += f""" AND LRT.operator_id = '{filters.get('trimming_od_operator')}' AND operation_type = 'Trimming OD' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						trimming_id_operator,trimming_od_operator,qty production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_nos
# 						line_rejection_nos,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_nos
# 						patrol_rejection_nos,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_nos
# 						lot_rejection_nos,
# 							lot_rejection_percent
# 						lot_rejection,
# 							incoming_rejected_qty_nos
# 						incoming_rejection_nos,
# 							incoming_rejection_percent
# 						incoming_rejection,
# 							final_rejected_qty_nos
# 						final_rejection_nos,
# 							final_rejection_percent
# 						final_rejection,

# 						line_inspected_qty line_inspected_qty_nos,
# 						patrol_inspected_qty patrol_inspected_qty_nos,
# 						lot_inspected_qty lot_inspected_qty_nos,
# 						incoming_inspected_qty_nos,final_inspected_qty_nos
							
# 					FROM 
# 						( SELECT 
# 							VSINE.lot_no lot_no,VSINE.product_ref_no item,B.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							LRT.operator_id trimming_id_operator,OLRT.operator_id trimming_od_operator,
# 							WPI.work_station press_no,MPE.employee moulding_operator,
# 							(CASE 
# 							    WHEN (VSINE.source_warehouse IS NOT NULL AND VSINE.source_warehouse != '') 
# 									THEN VSINE.source_warehouse
# 										ELSE 
# 											(SELECT DRE.warehouse 
# 												FROM `tabDeflashing Receipt Entry` DRE 
# 													WHERE 
# 														(CASE 
# 															WHEN DRE.scan_lot_number = VSINE.lot_no 
# 																THEN DRE.scan_lot_number=VSINE.lot_no
# 														ELSE 
# 															DRE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 													END) AND DRE.docstatus = 1 LIMIT 1)
# 							END) deflashing_operator,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 										ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 											INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 										WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
# 								(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 										INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 									WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,	

# 								CASE 
# 									WHEN LINE.total_rejected_qty  != 0 AND LINE.total_rejected_qty IS NOT NULL
# 										THEN LINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END line_rejected_qty_nos,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.inspected_qty_nos  != 0 AND LINE.inspected_qty_nos IS NOT NULL
# 										THEN LINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END line_inspected_qty,

# 								CASE 
# 									WHEN PINE.total_rejected_qty  != 0 AND PINE.total_rejected_qty IS NOT NULL
# 										THEN PINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_nos,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.inspected_qty_nos  != 0 AND PINE.inspected_qty_nos IS NOT NULL
# 										THEN PINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty  != 0 AND LOINE.total_rejected_qty IS NOT NULL
# 										THEN LOINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END lot_rejected_qty_nos,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.inspected_qty_nos  != 0 AND LOINE.inspected_qty_nos IS NOT NULL
# 										THEN LOINE.inspected_qty_nos 
# 									ELSE 0.0 
# 							END lot_inspected_qty,

# 								CASE 
# 									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
# 										THEN INE.total_rejected_qty 
# 									ELSE 0.0 
# 							END incoming_rejected_qty_nos,
# 								CASE 
# 									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN INE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END incoming_rejection_percent,
# 								CASE 
# 									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
# 										THEN INE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END incoming_inspected_qty_nos,

# 								CASE 
# 									WHEN VSINE.total_rejected_qty  != 0 AND VSINE.total_rejected_qty IS NOT NULL
# 										THEN VSINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END final_rejected_qty_nos,
# 								CASE 
# 									WHEN VSINE.total_rejected_qty_in_percentage  != 0 AND VSINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN VSINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END final_rejection_percent,
# 								CASE 
# 									WHEN VSINE.total_inspected_qty_nos  != 0 AND VSINE.total_inspected_qty_nos IS NOT NULL
# 										THEN VSINE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END final_inspected_qty_nos,
									
# 								IFNULL((SELECT DFSED.qty FROM `tabStock Entry Detail` DFSED 
# 									INNER JOIN `tabStock Entry` DFSE ON DFSE.name = DFSED.parent
# 									INNER JOIN `tabDeflashing Receipt Entry` DFRE ON DFRE.stock_entry_reference = DFSE.name
# 								WHERE 
# 									DFRE.scan_lot_number= INE.lot_no AND DFSED.t_warehouse IS NOT NULL LIMIT 1),0) deflashing_receipt_qty
# 						FROM 
# 							`tabInspection Entry` VSINE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND WPI.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.docstatus = 1 AND MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 							LEFT JOIN `tabBOM` B ON B.item = MPE.item_to_produce AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM Item` BI ON BI.parent = B.name 
# 							INNER JOIN `tabItem` MMI ON MMI.name = BI.item_code
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no AND LRT.operation_type = 'ID Trimming' AND LRT.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no AND OLRT.operation_type = 'OD Trimming' AND OLRT.docstatus = 1
# 						WHERE 
# 							SED.t_warehouse IS NOT NULL AND 
# 							(VSINE.inspection_type = "Final Visual Inspection" OR VSINE.inspection_type = "Visual Inspection") AND VSINE.docstatus = 1 
# 							AND MMI.item_group = 'Compound' {condition} ) 
# 					DEMO """	
# 		result__ = frappe.db.sql(query , as_dict = 1) 
# 		if result__:
# 			total_production_qty_nos = 0.0
# 			total_compound_consumed_qty_kgs = 0.0

# 			total_patrol_inspected_qty_nos = 0.0
# 			total_patrol_rejected_qty_nos = 0.0
# 			total_line_inspected_qty_nos = 0.0
# 			total_line_rejected_qty_nos = 0.0
# 			total_lot_inspected_qty_nos = 0.0
# 			total_lot_rejected_qty_nos = 0.0
# 			total_incoming_inspected_qty_nos = 0.0
# 			total_incoming_rejected_qty_nos = 0.0
# 			total_final_inspected_qty_nos = 0.0
# 			total_final_rejected_qty_nos = 0.0
# 			over_all_total_rejections_nos = 0.0
# 			over_all_total_inspected_nos = 0.0
# 			for rej in result__:
# 				total_rejections_nos = 0.0
# 				total_inspected_nos = 0.0
# 				try:
# 					if rej.production_qty_nos:
# 						total_production_qty_nos += rej.production_qty_nos
# 					if rej.compound_consumed_qty_kgs:
# 						total_compound_consumed_qty_kgs += rej.compound_consumed_qty_kgs

# 					if rej.patrol_inspected_qty_nos:
# 						total_patrol_inspected_qty_nos += rej.patrol_inspected_qty_nos
# 						total_inspected_nos += rej.patrol_inspected_qty_nos
# 					if rej.patrol_rejection_nos:
# 						total_patrol_rejected_qty_nos += rej.patrol_rejection_nos 
# 						total_rejections_nos += rej.patrol_rejection_nos 

# 					if rej.line_inspected_qty_nos:
# 						total_line_inspected_qty_nos += rej.line_inspected_qty_nos
# 						total_inspected_nos += rej.line_inspected_qty_nos 
# 					if rej.line_rejection_nos:
# 						total_line_rejected_qty_nos += rej.line_rejection_nos 
# 						total_rejections_nos += rej.line_rejection_nos 
						
# 					if rej.lot_inspected_qty_nos:
# 						total_lot_inspected_qty_nos += rej.lot_inspected_qty_nos
# 						total_inspected_nos += rej.lot_inspected_qty_nos 
# 					if rej.lot_rejection_nos:
# 						total_lot_rejected_qty_nos += rej.lot_rejection_nos 
# 						total_rejections_nos += rej.lot_rejection_nos 

# 					if rej.incoming_inspected_qty_nos:
# 						total_incoming_inspected_qty_nos += rej.incoming_inspected_qty_nos
# 						total_inspected_nos += rej.incoming_inspected_qty_nos 
# 					if rej.incoming_rejection_nos:
# 						total_incoming_rejected_qty_nos += rej.incoming_rejection_nos
# 						total_rejections_nos += rej.incoming_rejection_nos 

# 					if rej.final_inspected_qty_nos:
# 						total_final_inspected_qty_nos += rej.final_inspected_qty_nos
# 						total_inspected_nos += rej.final_inspected_qty_nos
# 					if rej.final_rejection_nos:
# 						total_final_rejected_qty_nos += rej.final_rejection_nos
# 						total_rejections_nos += rej.final_rejection_nos 

# 					rej['total_rejection'] = (total_rejections_nos / total_inspected_nos) * 100

# 					over_all_total_inspected_nos += total_inspected_nos
# 					over_all_total_rejections_nos += total_rejections_nos
# 				except ZeroDivisionError:
# 					rej['total_rejection'] = 0
# 			result__.append({"mould_ref":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
# 									"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
# 									"line_rejection_nos":((total_line_rejected_qty_nos / total_line_inspected_qty_nos )) if total_line_inspected_qty_nos else 0.0,
# 									"line_rejection":((total_line_rejected_qty_nos / total_line_inspected_qty_nos ) * 100) if total_line_inspected_qty_nos else 0.0,
# 									"patrol_rejection_nos":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos )) if total_patrol_inspected_qty_nos else 0.0,
# 									"patrol_rejection":((total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos ) * 100) if total_patrol_inspected_qty_nos else 0.0,
# 									"lot_rejection_nos":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos )) if total_lot_inspected_qty_nos else 0.0,
# 									"lot_rejection":((total_lot_rejected_qty_nos / total_lot_inspected_qty_nos ) * 100) if total_lot_inspected_qty_nos else 0.0,
# 									"incoming_rejection_nos":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos )) if total_incoming_inspected_qty_nos else 0.0,
# 									"incoming_rejection":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos ) * 100) if total_incoming_inspected_qty_nos else 0.0,
# 									"final_rejection_nos":((total_final_rejected_qty_nos / total_final_inspected_qty_nos )) if total_final_inspected_qty_nos else 0.0,
# 									"final_rejection":((total_final_rejected_qty_nos / total_final_inspected_qty_nos ) * 100) if total_final_inspected_qty_nos else 0.0,
# 									"total_rejection": (over_all_total_rejections_nos / over_all_total_inspected_nos )* 100})
# 		return result__	


















# rej['total_rejection'] = ((
					# 		( (rej.patrol_rejection_nos if rej.patrol_rejection_nos else 0.0) 
					# 			+ (rej.line_rejection_nos if rej.line_rejection_nos else 0.0) 
					# 				+ (rej.lot_rejection_nos if rej.lot_rejection_nos else 0.0) 
					# 					+ (rej.incoming_rejection_nos if rej.incoming_rejection_nos else 0.0)
					# 					+ (rej.final_rejection_nos if rej.final_rejection_nos else 0.0)
					# 		) /

					# 		( (rej.patrol_inspected_qty if rej.patrol_inspected_qty else 0.0) 
					# 			+ (rej.line_inspected_qty if rej.line_inspected_qty else 0.0) 
					# 				+ (rej.lot_inspected_qty if rej.lot_inspected_qty else 0.0) 
					# 					+ (rej.incoming_inspected_qty_nos if rej.incoming_inspected_qty_nos else 0.0)
					# 					+(rej.final_inspected_qty_nos if rej.final_inspected_qty_nos else 0.0)
					# 		) 
					# 	) * 100)

# Back up 20/07/2023

# import frappe
# from frappe import _

# def execute(filters=None):
# 	columns, data = get_columns(filters), get_datas(filters)
# 	return columns, data

# def get_columns(filters):
# 	c__ = []
# 	c__.append(_('Lot No')+':Data:90')
# 	c__.append(_('Item')+':Link/Item:80')
# 	c__.append(_('Compound BOM No')+':Link/BOM:130')
# 	c__.append(_('Press No')+':Link/Workstation:175')
# 	c__.append(_('Moulding Operator')+':Link/Employee:130')
# 	if filters.get('report_type') == "Deflashing Rejection Report" or filters.get('report_type') == "Final Rejection Report":
# 		c__.append(_('Deflashing Operator')+':Link/Warehouse:130')
# 	c__.append(_('Mould Ref')+':Data:120')
# 	if filters.get('report_type') == "Final Rejection Report":
# 		c__.append(_('Trimming ID Operator')+':Link/Employee:130')
# 		c__.append(_('Trimming OD Operator')+':Link/Employee:130')
# 	c__.append(_('Production Qty Nos')+':Float:140')
# 	c__.append(_('Compound Consumed Qty Kgs')+':Float:150')
# 	c__.append(_('Line Rejection')+':Float:120')
# 	c__.append(_('Patrol Rejection')+':Float:120')
# 	c__.append(_('Lot Rejection')+':Float:120')
# 	if filters.get('report_type') == "Deflashing Rejection Report" or filters.get('report_type') == "Final Rejection Report":
# 		c__.append(_('Incoming Rejection')+':Float:120')
# 	if filters.get('report_type') == "Final Rejection Report":
# 		c__.append(_('Final Rejection')+':Float:120')
# 	c__.append(_('Total Rejection')+':Float:120')
# 	return c__

# def get_datas(filters):
# 	query = None
# 	condition = ""
# 	if filters.get('report_type') == "Line Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(LINE.modified) = '{filters.get('date')}' """
# 		if filters.get('t_item'):
# 			condition += f""" AND WPI.item = '{filters.get('t_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND SE.bom_no = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,mould_ref,
# 							(qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty)) 
# 						production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							(line_rejection_qty/((qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty))/100)) 
# 						line_rejection,
# 							(patrol_rejection_qty/((qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty))/100)) 
# 						patrol_rejection,
# 							(lot_rejection_qty/((qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty))/100)) 
# 						lot_rejection,
# 							((line_rejection_qty/((qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty))/100))
# 							+ (patrol_rejection_qty/((qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty))/100))
# 							+ (lot_rejection_qty/((qty/avg_blank_wtproduct_kgs - (line_rejection_qty + patrol_rejection_qty + lot_rejection_qty))/100))) 
# 						total_rejection 
# 					FROM 
# 						( SELECT 
# 							MPE.scan_lot_number lot_no,WPI.item,SE.bom_no compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							WPI.work_station press_no,MPE.employee moulding_operator,
# 							(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 									ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 								  WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name LIMIT 1)
# 							compound_consumed_qty_kgs,
# 								(CASE WHEN LINE.total_rejected_qty !=0 AND LINE.total_rejected_qty IS NOT NULL THEN LINE.total_rejected_qty ELSE 0 END) 
# 							line_rejection_qty,
# 								(CASE WHEN PINE.total_rejected_qty !=0 AND PINE.total_rejected_qty IS NOT NULL THEN PINE.total_rejected_qty ELSE 0 END) 
# 							patrol_rejection_qty,
# 								(CASE WHEN LOINE.total_rejected_qty !=0 AND LOINE.total_rejected_qty IS NOT NULL THEN LOINE.total_rejected_qty ELSE 0 END) 
# 							lot_rejection_qty
# 						FROM 
# 							`tabMoulding Production Entry` MPE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference 
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = MPE.scan_lot_number 
# 							INNER JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							INNER JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 						WHERE SED.t_warehouse IS NOT NULL AND SE.docstatus = 1 AND WPI.docstatus = 1 {condition} ) 
# 					DEMO """	
# 	elif filters.get('report_type') == "Deflashing Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(INE.modified) = '{filters.get('date')}' """
# 		if filters.get('p_item'):
# 			condition += f""" AND B.item = '{filters.get('p_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND CB.name = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		if filters.get('deflashing_operator'):
# 			condition += f""" AND DFR.from_warehouse_id = '{filters.get('deflashing_operator')}' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						(qty - incoming_rejection) production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							(line_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100)) 
# 						line_rejection,
# 							(patrol_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100)) 
# 						patrol_rejection,
# 							(lot_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100)) 
# 						lot_rejection,
# 							(incoming_rejection/((qty - incoming_rejection)/100)) 
# 						incoming_rejection,
# 							((line_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100))
# 							+ (patrol_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100))
# 							+ (lot_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100))) 
# 							+(incoming_rejection/((qty - incoming_rejection)/100)) 
# 						total_rejection
# 					FROM 
# 						( SELECT 
# 							DFR.scan_lot_number lot_no,B.item,CB.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							WPI.work_station press_no,MPE.employee moulding_operator,DFR.from_warehouse_id deflashing_operator,
# 								(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 								  WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,

# 							CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 									ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
							
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 										INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 									WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
							
# 								(CASE WHEN LINE.total_rejected_qty !=0 AND LINE.total_rejected_qty IS NOT NULL THEN LINE.total_rejected_qty ELSE 0 END) 
# 							line_rejection,
# 									(CASE WHEN PINE.total_rejected_qty !=0 AND PINE.total_rejected_qty IS NOT NULL THEN PINE.total_rejected_qty ELSE 0 END) 
# 							patrol_rejection,
# 									(CASE WHEN LOINE.total_rejected_qty !=0 AND LOINE.total_rejected_qty IS NOT NULL THEN LOINE.total_rejected_qty ELSE 0 END) 
# 							lot_rejection,
# 								(CASE WHEN INE.total_rejected_qty !=0 AND INE.total_rejected_qty IS NOT NULL THEN INE.total_rejected_qty ELSE 0 END) 
# 							incoming_rejection
# 						FROM 
# 							`tabDeflashing Receipt Entry` DFR 
# 							INNER JOIN `tabBOM Item` BI ON BI.item_code = DFR.item 
# 							INNER JOIN `tabBOM` B ON BI.parent = B.name AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM` CB ON CB.Item = DFR.item AND CB.is_active=1 AND CB.is_default=1
# 							INNER JOIN `tabBOM Item` CBI ON CBI.parent = CB.name 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = DFR.stock_entry_reference AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1) AND WPI.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.scan_lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1)
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							INNER JOIN `tabInspection Entry` INE ON INE.lot_no = DFR.scan_lot_number 
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 						WHERE SED.t_warehouse IS NOT NULL {condition} ) 
# 					DEMO """	
# 	elif filters.get('report_type') == "Final Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(VSINE.modified) = '{filters.get('date')}' """
# 		if filters.get('f_item'):
# 			condition += f""" AND VSINE.product_ref_no = '{filters.get('f_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND B.name = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		if filters.get('deflashing_operator'):
# 			condition += f""" AND VSINE.source_warehouse = '{filters.get('deflashing_operator')}' """
# 		if filters.get('trimming_id__operator'):
# 			condition += f""" AND LRT.operator_id = '{filters.get('trimming_id__operator')}' AND operation_type = 'Trimming ID' """
# 		if filters.get('trimming_od_operator'):
# 			condition += f""" AND LRT.operator_id = '{filters.get('trimming_od_operator')}' AND operation_type = 'Trimming OD' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						trimming_id_operator,trimming_od_operator,(qty - final_rejection) production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							(line_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100)) 
# 						line_rejection,
# 							(patrol_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100)) 
# 						patrol_rejection,
# 							(lot_rejection/((moulding_prod_qty/avg_blank_wtproduct_kgs - (line_rejection + patrol_rejection + lot_rejection))/100)) 
# 						lot_rejection,
# 							(incoming_rejection/(deflashing_receipt_qty)/100)
# 						incoming_rejection,
# 							(final_rejection/((qty - final_rejection)/100))
# 						final_rejection,
# 							(
# 							 CAST(line_rejection/CAST(((CAST((moulding_prod_qty/avg_blank_wtproduct_kgs) as DECIMAL(10,3)) - (line_rejection + patrol_rejection + lot_rejection))/100) as DECIMAL(10,3)) as DECIMAL(10,3))
# 							+CAST(patrol_rejection/CAST(((CAST((moulding_prod_qty/avg_blank_wtproduct_kgs) as DECIMAL(10,3)) - (line_rejection + patrol_rejection + lot_rejection))/100) as DECIMAL(10,3)) as DECIMAL(10,3))
# 							+CAST(lot_rejection/CAST(((CAST((moulding_prod_qty/avg_blank_wtproduct_kgs) as DECIMAL(10,3)) - (line_rejection + patrol_rejection + lot_rejection))/100) as DECIMAL(10,3)) as DECIMAL(10,3)) 
# 							+CAST((incoming_rejection/(deflashing_receipt_qty/100)) as DECIMAL(10,3)) 
# 							+CAST((final_rejection/((qty - final_rejection)/100)) as DECIMAL(10,3))
# 							)
# 						total_rejection 
# 					FROM 
# 						( SELECT 
# 							VSINE.lot_no lot_no,VSINE.product_ref_no item,B.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							LRT.operator_id trimming_id_operator,OLRT.operator_id trimming_od_operator,
# 							WPI.work_station press_no,MPE.employee moulding_operator,
# 							(CASE 
# 							    WHEN (VSINE.source_warehouse IS NOT NULL AND VSINE.source_warehouse != '') 
# 									THEN VSINE.source_warehouse
# 										ELSE 
# 											(SELECT DRE.warehouse 
# 												FROM `tabDeflashing Receipt Entry` DRE 
# 													WHERE 
# 														(CASE 
# 															WHEN DRE.scan_lot_number = VSINE.lot_no 
# 																THEN DRE.scan_lot_number=VSINE.lot_no
# 														ELSE 
# 															DRE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 													END) AND DRE.docstatus = 1 LIMIT 1)
# 							END) deflashing_operator,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 										ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 											INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 										WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
# 								(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 										INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 									WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,							
# 								(CASE WHEN LINE.total_rejected_qty !=0 AND LINE.total_rejected_qty IS NOT NULL THEN LINE.total_rejected_qty ELSE 0 END) 
# 							line_rejection,
# 									(CASE WHEN PINE.total_rejected_qty !=0 AND PINE.total_rejected_qty IS NOT NULL THEN PINE.total_rejected_qty ELSE 0 END) 
# 							patrol_rejection,
# 									(CASE WHEN LOINE.total_rejected_qty !=0 AND LOINE.total_rejected_qty IS NOT NULL THEN LOINE.total_rejected_qty ELSE 0 END) 
# 							lot_rejection,
# 								(CASE WHEN INE.total_rejected_qty !=0 AND INE.total_rejected_qty IS NOT NULL THEN INE.total_rejected_qty ELSE 0 END) 
# 							incoming_rejection,
# 								(CASE WHEN VSINE.total_rejected_qty !=0 AND VSINE.total_rejected_qty IS NOT NULL THEN VSINE.total_rejected_qty ELSE 0 END) 
# 							final_rejection,
# 								IFNULL((SELECT DFSED.qty FROM `tabStock Entry Detail` DFSED 
# 									INNER JOIN `tabStock Entry` DFSE ON DFSE.name = DFSED.parent
# 									INNER JOIN `tabDeflashing Receipt Entry` DFRE ON DFRE.stock_entry_reference = DFSE.name
# 								WHERE 
# 									DFRE.scan_lot_number= INE.lot_no AND DFSED.t_warehouse IS NOT NULL LIMIT 1),0) deflashing_receipt_qty
# 						FROM 
# 							`tabInspection Entry` VSINE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND WPI.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 							LEFT JOIN `tabBOM` B ON B.item = MPE.item_to_produce AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM Item` BI ON BI.parent = B.name 
# 							INNER JOIN `tabItem` MMI ON MMI.name = BI.item_code
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no AND LRT.operation_type = 'ID Trimming'
# 							LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no AND OLRT.operation_type = 'OD Trimming'
# 						WHERE 
# 							SED.t_warehouse IS NOT NULL AND 
# 							VSINE.inspection_type = "Final Visual Inspection" AND VSINE.docstatus = 1 
# 							AND MMI.item_group = 'Compound' {condition} ) 
# 					DEMO """	
# 	# frappe.log_error(title=f"-- {filters.get('report_type')} query ---",message = query)
# 	result__ = frappe.db.sql(query , as_dict = 1) 
# 	return result__
	
# @frappe.whitelist()
# def get_moulds(doctype, mould, searchfield, start, page_len, filters):
# 	search_condition = ""
# 	if mould:
# 		search_condition = " AND I.name LIKE '%"+mould+"%'"
# 	mould_group = frappe.db.get_single_value("SPP Settings","mould_item_group")
# 	query = f""" SELECT I.name FROM `tabItem` I
# 				WHERE I.item_group = '{mould_group}' {search_condition}
# 			"""
# 	mould = frappe.db.sql(query)
# 	return mould

# @frappe.whitelist()
# def get_press_info(doctype, press, searchfield, start, page_len, filters):
# 	search_condition = ""
# 	if press:
# 		search_condition = " AND WSP.work_station LIKE '%"+press+"%'"
# 	query = f""" SELECT WPS.work_station FROM `tabWork Plan Station` WPS
# 					WHERE WPS.parent = 'SPP Settings' {search_condition}
# 			"""
# 	press = frappe.db.sql(query)
# 	return press

# @frappe.whitelist()
# def get_moulding_operator_info(doctype, operator, searchfield, start, page_len, filters):
# 	condition = ''
# 	for k in filters.get('designation').split(','):
# 		condition += f"'{k}',"
# 	condition = condition[:-1]
# 	filters['designation'] = condition
# 	search_condition = ""
# 	if operator:
# 		search_condition = " AND EMP.name LIKE '%"+operator+"%'"
# 	query = f""" SELECT EMP.name,EMP.employee_name FROM `tabEmployee` EMP WHERE EMP.designation IN (SELECT SPPDM.designation FROM `tabSPP Designation Mapping` SPPDM
# 					WHERE SPPDM.parent = 'SPP Settings' AND SPPDM.spp_process IN ({filters.get('designation')}) ) {search_condition}
# 			"""
# 	operator = frappe.db.sql(query)
# 	return operator


#backup on 21/7/23


# def get_datas(filters):
# 	query = None
# 	condition = ""
# 	if filters.get('report_type') == "Line Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(LINE.modified) = '{filters.get('date')}' """
# 		if filters.get('t_item'):
# 			condition += f""" AND WPI.item = '{filters.get('t_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND SE.bom_no = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,mould_ref,
# 							(qty/avg_blank_wtproduct_kgs) 
# 						production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_kg
# 						line_rejection_kgs,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_kg
# 						patrol_rejection_kgs,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_kg
# 						lot_rejection_kgs,
# 							lot_rejection_percent
# 						lot_rejection,
# 							((patrol_rejected_qty_kg + line_rejected_qty_kg + lot_rejected_qty_kg) 
# 								/ (patrol_inspected_qty + line_inspected_qty + lot_inspected_qty)) * 100
# 						total_rejection,
# 						 patrol_inspected_qty,line_inspected_qty,lot_inspected_qty
# 					FROM 
# 						( SELECT 
# 							MPE.scan_lot_number lot_no,WPI.item,SE.bom_no compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							WPI.work_station press_no,MPE.employee moulding_operator,
# 							(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 									ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 								  WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name LIMIT 1)
# 							compound_consumed_qty_kgs,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_kg  != 0 AND LINE.total_rejected_qty_kg IS NOT NULL
# 										THEN LINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END line_rejected_qty_kg,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.total_inspected_qty  != 0 AND LINE.total_inspected_qty IS NOT NULL
# 										THEN LINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END line_inspected_qty,

# 								CASE 
# 									WHEN PINE.total_rejected_qty_kg  != 0 AND PINE.total_rejected_qty_kg IS NOT NULL
# 										THEN PINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_kg,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.total_inspected_qty  != 0 AND PINE.total_inspected_qty IS NOT NULL
# 										THEN PINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty_kg  != 0 AND LOINE.total_rejected_qty_kg IS NOT NULL
# 										THEN LOINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END lot_rejected_qty_kg,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.total_inspected_qty  != 0 AND LOINE.total_inspected_qty IS NOT NULL
# 										THEN LOINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END lot_inspected_qty
# 						FROM 
# 							`tabMoulding Production Entry` MPE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference AND MPE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.docstatus = 1
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = MPE.scan_lot_number AND WPI.docstatus = 1
# 							INNER JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							INNER JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 						WHERE SED.t_warehouse IS NOT NULL AND SE.docstatus = 1 AND WPI.docstatus = 1 {condition} ) 
# 					DEMO """	
# 		result__ = frappe.db.sql(query , as_dict = 1) 
# 		if result__:
# 			total_production_qty_nos = 0.0
# 			total_compound_consumed_qty_kgs = 0.0
# 			total_patrol_inspected_qty_kgs = 0.0
# 			total_patrol_rejected_qty_kgs = 0.0
# 			total_line_inspected_qty_kgs = 0.0
# 			total_line_rejected_qty_kgs = 0.0
# 			total_lot_inspected_qty_kgs = 0.0
# 			total_lot_rejected_qty_kgs = 0.0
# 			for x in result__:
# 				if x.production_qty_nos:
# 					total_production_qty_nos += x.production_qty_nos
# 				if x.compound_consumed_qty_kgs:
# 					total_compound_consumed_qty_kgs += x.compound_consumed_qty_kgs
# 				if x.patrol_inspected_qty:
# 					total_patrol_inspected_qty_kgs += x.patrol_inspected_qty
# 				if x.patrol_rejection_kgs:
# 					total_patrol_rejected_qty_kgs += x.patrol_rejection_kgs
# 				if x.line_inspected_qty:
# 					total_line_inspected_qty_kgs += x.line_inspected_qty
# 				if x.line_rejection_kgs:
# 					total_line_rejected_qty_kgs += x.line_rejection_kgs
# 				if x.lot_inspected_qty:
# 					total_lot_inspected_qty_kgs += x.lot_inspected_qty
# 				if x.lot_rejection_kgs:
# 					total_lot_rejected_qty_kgs += x.lot_rejection_kgs
# 			result__.append({"lot_no":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
# 							"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
# 							"line_rejection_kgs":((total_line_rejected_qty_kgs / total_line_inspected_qty_kgs )) if total_line_inspected_qty_kgs else 0.0,
# 							"line_rejection":((total_line_rejected_qty_kgs / total_line_inspected_qty_kgs ) * 100) if total_line_inspected_qty_kgs else 0.0,
# 							"patrol_rejection_kgs":((total_patrol_rejected_qty_kgs / total_patrol_inspected_qty_kgs )) if total_patrol_inspected_qty_kgs else 0.0,
# 							"patrol_rejection":((total_patrol_rejected_qty_kgs / total_patrol_inspected_qty_kgs ) * 100) if total_patrol_inspected_qty_kgs else 0.0,
# 							"lot_rejection_kgs":((total_lot_rejected_qty_kgs / total_lot_inspected_qty_kgs )) if total_lot_inspected_qty_kgs else 0.0,
# 							"lot_rejection":((total_lot_rejected_qty_kgs / total_lot_inspected_qty_kgs ) * 100) if total_lot_inspected_qty_kgs else 0.0,
# 							"total_rejection":(((total_line_rejected_qty_kgs + total_patrol_rejected_qty_kgs + total_lot_rejected_qty_kgs) /
# 												(total_line_inspected_qty_kgs + total_patrol_inspected_qty_kgs + total_lot_inspected_qty_kgs)) * 100) if (total_line_inspected_qty_kgs + total_patrol_inspected_qty_kgs + total_lot_inspected_qty_kgs) else 0.0})
# 		return result__
# 	elif filters.get('report_type') == "Deflashing Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(INE.modified) = '{filters.get('date')}' """
# 		if filters.get('p_item'):
# 			condition += f""" AND B.item = '{filters.get('p_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND CB.name = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		if filters.get('deflashing_operator'):
# 			condition += f""" AND DFR.from_warehouse_id = '{filters.get('deflashing_operator')}' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						qty production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_kg
# 						line_rejection_kgs,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_kg
# 						patrol_rejection_kgs,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_kg
# 						lot_rejection_kgs,
# 							lot_rejection_percent
# 						lot_rejection,
# 							incoming_rejected_qty_nos
# 						incoming_rejection_nos,
# 							incoming_rejection_percent
# 						incoming_rejection,

# 						line_one_no_qty_equal_kgs,line_inspected_qty,
# 						patrol_one_no_qty_equal_kgs,patrol_inspected_qty,
# 						lot_one_no_qty_equal_kgs,lot_inspected_qty,
# 						incoming_inspected_qty_nos

# 					FROM 
# 						( SELECT 
# 							DFR.scan_lot_number lot_no,B.item,CB.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							WPI.work_station press_no,MPE.employee moulding_operator,DFR.from_warehouse_id deflashing_operator,
# 								(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 								 	INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 								  WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,

# 							CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 									ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
							
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 										INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 									WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
							
# 								CASE 
# 									WHEN LINE.total_rejected_qty_kg  != 0 AND LINE.total_rejected_qty_kg IS NOT NULL
# 										THEN LINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END line_rejected_qty_kg,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.total_inspected_qty  != 0 AND LINE.total_inspected_qty IS NOT NULL
# 										THEN LINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END line_inspected_qty,
# 							LINE.one_no_qty_equal_kgs line_one_no_qty_equal_kgs,

# 								CASE 
# 									WHEN PINE.total_rejected_qty_kg  != 0 AND PINE.total_rejected_qty_kg IS NOT NULL
# 										THEN PINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_kg,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.total_inspected_qty  != 0 AND PINE.total_inspected_qty IS NOT NULL
# 										THEN PINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,
# 							PINE.one_no_qty_equal_kgs patrol_one_no_qty_equal_kgs,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty_kg  != 0 AND LOINE.total_rejected_qty_kg IS NOT NULL
# 										THEN LOINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END lot_rejected_qty_kg,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.total_inspected_qty  != 0 AND LOINE.total_inspected_qty IS NOT NULL
# 										THEN LOINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END lot_inspected_qty,
# 							LOINE.one_no_qty_equal_kgs lot_one_no_qty_equal_kgs,

# 								CASE 
# 									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
# 										THEN INE.total_rejected_qty 
# 									ELSE 0.0 
# 							END incoming_rejected_qty_nos,
# 								CASE 
# 									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN INE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END incoming_rejection_percent,
# 								CASE 
# 									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
# 										THEN INE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END incoming_inspected_qty_nos
# 						FROM 
# 							`tabDeflashing Receipt Entry` DFR 
# 							INNER JOIN `tabBOM Item` BI ON BI.item_code = DFR.item AND DFR.docstatus = 1
# 							INNER JOIN `tabBOM` B ON BI.parent = B.name AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM` CB ON CB.Item = DFR.item AND CB.is_active=1 AND CB.is_default=1
# 							INNER JOIN `tabBOM Item` CBI ON CBI.parent = CB.name 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = DFR.stock_entry_reference AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.is_finished_item = 1
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1) AND WPI.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.scan_lot_number = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1) AND MPE.docstatus = 1
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							INNER JOIN `tabInspection Entry` INE ON INE.lot_no = DFR.scan_lot_number 
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 						WHERE SED.t_warehouse IS NOT NULL {condition} ) 
# 					DEMO """
# 		result__ = frappe.db.sql(query , as_dict = 1) 
# 		if result__:
# 			total_production_qty_nos = 0.0
# 			total_compound_consumed_qty_kgs = 0.0
# 			total_patrol_inspected_qty_kgs = 0.0
# 			total_patrol_rejected_qty_kgs = 0.0
# 			total_line_inspected_qty_kgs = 0.0
# 			total_line_rejected_qty_kgs = 0.0
# 			total_lot_inspected_qty_kgs = 0.0
# 			total_lot_rejected_qty_kgs = 0.0
# 			total_incoming_inspected_qty_nos = 0.0
# 			total_incoming_rejected_qty_nos = 0.0

# 			total_patrol_inspected_qty_nos = 0.0
# 			total_patrol_rejected_qty_nos = 0.0
# 			total_line_inspected_qty_nos = 0.0
# 			total_line_rejected_qty_nos = 0.0
# 			total_lot_inspected_qty_nos = 0.0
# 			total_lot_rejected_qty_nos = 0.0

# 			for rej in result__:
# 				try:
# 					if rej.patrol_inspected_qty and rej.patrol_one_no_qty_equal_kgs:
# 						total_patrol_inspected_qty_nos += rej.patrol_inspected_qty  / rej.patrol_one_no_qty_equal_kgs
# 					if rej.patrol_rejection_kgs and rej.patrol_one_no_qty_equal_kgs:
# 						total_patrol_rejected_qty_nos += rej.patrol_rejection_kgs / rej.patrol_one_no_qty_equal_kgs
# 					if rej.line_inspected_qty and rej.line_one_no_qty_equal_kgs:
# 						total_line_inspected_qty_nos += rej.line_inspected_qty / rej.line_one_no_qty_equal_kgs
# 					if rej.line_rejection_kgs and rej.line_one_no_qty_equal_kgs:
# 						total_line_rejected_qty_nos += rej.line_rejection_kgs / rej.line_one_no_qty_equal_kgs
# 					if rej.lot_inspected_qty and rej.lot_one_no_qty_equal_kgs:
# 						total_lot_inspected_qty_nos += rej.lot_inspected_qty / rej.lot_one_no_qty_equal_kgs
# 					if rej.lot_rejection_kgs and rej.lot_one_no_qty_equal_kgs:
# 						total_lot_rejected_qty_nos += rej.lot_rejection_kgs / rej.lot_one_no_qty_equal_kgs
				
# 					rej['total_rejection'] = (
# 							( ( (rej.patrol_rejection_kgs / rej.patrol_one_no_qty_equal_kgs) if rej.patrol_rejection_kgs and rej.patrol_one_no_qty_equal_kgs else 0.0) 
# 								+ ( (rej.line_rejection_kgs / rej.line_one_no_qty_equal_kgs) if rej.line_rejection_kgs and rej.line_one_no_qty_equal_kgs else 0.0)
# 									+ ( (rej.lot_rejection_kgs / rej.lot_one_no_qty_equal_kgs) if rej.lot_rejection_kgs and rej.lot_one_no_qty_equal_kgs else 0.0)
# 										+ float(rej.incoming_rejection_nos) if rej.incoming_rejection_nos else 0.0
# 							) /

# 							( ( (rej.patrol_inspected_qty  / rej.patrol_one_no_qty_equal_kgs) if rej.patrol_inspected_qty and rej.patrol_one_no_qty_equal_kgs else 0.0)
# 								+ ( (rej.line_inspected_qty / rej.line_one_no_qty_equal_kgs) if rej.line_inspected_qty and rej.line_one_no_qty_equal_kgs else 0.0)
# 									+ ( (rej.lot_inspected_qty / rej.lot_one_no_qty_equal_kgs) if rej.lot_inspected_qty and rej.lot_one_no_qty_equal_kgs else 0.0)
# 										+ float(rej.incoming_inspected_qty_nos) if rej.incoming_inspected_qty_nos else 0.0
							
# 							)
# 						) * 100
# 					if rej.production_qty_nos:
# 						total_production_qty_nos += rej.production_qty_nos
# 					if rej.compound_consumed_qty_kgs:
# 						total_compound_consumed_qty_kgs += rej.compound_consumed_qty_kgs
# 					if rej.patrol_inspected_qty:
# 						total_patrol_inspected_qty_kgs += rej.patrol_inspected_qty
# 					if rej.patrol_rejection_kgs:
# 						total_patrol_rejected_qty_kgs += rej.patrol_rejection_kgs
# 					if rej.line_inspected_qty:
# 						total_line_inspected_qty_kgs += rej.line_inspected_qty
# 					if rej.line_rejection_kgs:
# 						total_line_rejected_qty_kgs += rej.line_rejection_kgs
# 					if rej.lot_inspected_qty:
# 						total_lot_inspected_qty_kgs += rej.lot_inspected_qty
# 					if rej.lot_rejection_kgs:
# 						total_lot_rejected_qty_kgs += rej.lot_rejection_kgs
# 					if rej.incoming_inspected_qty_nos:
# 						total_incoming_inspected_qty_nos += float(rej.incoming_inspected_qty_nos)
# 					if rej.incoming_rejection_nos:
# 						total_incoming_rejected_qty_nos += float(rej.incoming_rejection_nos)
# 				except ZeroDivisionError:
# 					rej['total_rejection'] = 0
# 			result__.append({"lot_no":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
# 									"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
# 									"line_rejection_kgs":((total_line_rejected_qty_kgs / total_line_inspected_qty_kgs )) if total_line_inspected_qty_kgs else 0.0,
# 									"line_rejection":((total_line_rejected_qty_kgs / total_line_inspected_qty_kgs ) * 100) if total_line_inspected_qty_kgs else 0.0,
# 									"patrol_rejection_kgs":((total_patrol_rejected_qty_kgs / total_patrol_inspected_qty_kgs )) if total_patrol_inspected_qty_kgs else 0.0,
# 									"patrol_rejection":((total_patrol_rejected_qty_kgs / total_patrol_inspected_qty_kgs ) * 100) if total_patrol_inspected_qty_kgs else 0.0,
# 									"lot_rejection_kgs":((total_lot_rejected_qty_kgs / total_lot_inspected_qty_kgs )) if total_lot_inspected_qty_kgs else 0.0,
# 									"lot_rejection":((total_lot_rejected_qty_kgs / total_lot_inspected_qty_kgs ) * 100) if total_lot_inspected_qty_kgs else 0.0,
# 									"incoming_rejection_nos":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos )) if total_incoming_inspected_qty_nos else 0.0,
# 									"incoming_rejection":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos ) * 100) if total_incoming_inspected_qty_nos else 0.0,
# 									"total_rejection":(((total_patrol_rejected_qty_nos + total_line_rejected_qty_nos + total_lot_rejected_qty_nos + total_incoming_rejected_qty_nos) /
# 														(total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos)) * 100) if (total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos) else 0.0})
# 		return result__	
# 	elif filters.get('report_type') == "Final Rejection Report":
# 		if filters.get('date'):
# 			condition += f""" AND DATE(VSINE.modified) = '{filters.get('date')}' """
# 		if filters.get('f_item'):
# 			condition += f""" AND VSINE.product_ref_no = '{filters.get('f_item')}' """
# 		if filters.get('compound_bom_no'):
# 			condition += f""" AND B.name = '{filters.get('compound_bom_no')}' """
# 		if filters.get('press_no'):
# 			condition += f""" AND WPI.work_station = '{filters.get('press_no')}' """
# 		if filters.get('moulding_operator'):
# 			condition += f""" AND MPE.employee = '{filters.get('moulding_operator')}' """
# 		if filters.get('mould_ref'):
# 			condition += f""" AND WPI.mould = '{filters.get('mould_ref')}' """
# 		if filters.get('deflashing_operator'):
# 			condition += f""" AND VSINE.source_warehouse = '{filters.get('deflashing_operator')}' """
# 		if filters.get('trimming_id__operator'):
# 			condition += f""" AND LRT.operator_id = '{filters.get('trimming_id__operator')}' AND operation_type = 'Trimming ID' """
# 		if filters.get('trimming_od_operator'):
# 			condition += f""" AND LRT.operator_id = '{filters.get('trimming_od_operator')}' AND operation_type = 'Trimming OD' """
# 		query = f""" SELECT 
# 						lot_no,item,compound_bom_no,press_no,moulding_operator,deflashing_operator,mould_ref,
# 						trimming_id_operator,trimming_od_operator,qty production_qty_nos,
# 						compound_consumed_qty_kgs,
# 							line_rejected_qty_kg
# 						line_rejection_kgs,
# 							line_rejection_percent
# 						line_rejection,
# 							patrol_rejected_qty_kg
# 						patrol_rejection_kgs,
# 							patrol_rejection_percent
# 						patrol_rejection,
# 							lot_rejected_qty_kg
# 						lot_rejection_kgs,
# 							lot_rejection_percent
# 						lot_rejection,
# 							incoming_rejected_qty_nos
# 						incoming_rejection_nos,
# 							incoming_rejection_percent
# 						incoming_rejection,
# 							final_rejected_qty_nos
# 						final_rejection_nos,
# 							final_rejection_percent
# 						final_rejection,

# 						line_one_no_qty_equal_kgs,line_inspected_qty,
# 						patrol_one_no_qty_equal_kgs,patrol_inspected_qty,
# 						lot_one_no_qty_equal_kgs,lot_inspected_qty,
# 						incoming_inspected_qty_nos,final_inspected_qty_nos
							
# 					FROM 
# 						( SELECT 
# 							VSINE.lot_no lot_no,VSINE.product_ref_no item,B.name compound_bom_no,CAST(SED.qty as DECIMAL(10,3)) qty,
# 							LRT.operator_id trimming_id_operator,OLRT.operator_id trimming_od_operator,
# 							WPI.work_station press_no,MPE.employee moulding_operator,
# 							(CASE 
# 							    WHEN (VSINE.source_warehouse IS NOT NULL AND VSINE.source_warehouse != '') 
# 									THEN VSINE.source_warehouse
# 										ELSE 
# 											(SELECT DRE.warehouse 
# 												FROM `tabDeflashing Receipt Entry` DRE 
# 													WHERE 
# 														(CASE 
# 															WHEN DRE.scan_lot_number = VSINE.lot_no 
# 																THEN DRE.scan_lot_number=VSINE.lot_no
# 														ELSE 
# 															DRE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 													END) AND DRE.docstatus = 1 LIMIT 1)
# 							END) deflashing_operator,
# 								CASE WHEN MSP.avg_blank_wtproduct_gms != 0 THEN MSP.avg_blank_wtproduct_gms/1000 
# 										ELSE 0 END 
# 							avg_blank_wtproduct_kgs,
# 								( SELECT MLSED.qty moulding_prod_qty FROM `tabStock Entry Detail` MLSED 
# 											INNER JOIN 	`tabStock Entry` MLSE ON MLSE.name = MLSED.parent
# 										WHERE MLSE.name =  MSE.name AND MLSED.t_warehouse IS NOT NULL LIMIT 1 )
# 							moulding_prod_qty,
# 								(SELECT A.asset_name FROM `tabAsset` A WHERE A.item_code = WPI.mould LIMIT 1)
# 							mould_ref,
# 								( SELECT CAST(MSED.qty as DECIMAL(10,3)) c_qty FROM `tabStock Entry Detail` MSED
# 										INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
# 									WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name LIMIT 1)
# 							compound_consumed_qty_kgs,	

# 								CASE 
# 									WHEN LINE.total_rejected_qty_kg  != 0 AND LINE.total_rejected_qty_kg IS NOT NULL
# 										THEN LINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END line_rejected_qty_kg,
# 								CASE 
# 									WHEN LINE.total_rejected_qty_in_percentage  != 0 AND LINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END line_rejection_percent,
# 								CASE 
# 									WHEN LINE.total_inspected_qty  != 0 AND LINE.total_inspected_qty IS NOT NULL
# 										THEN LINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END line_inspected_qty,
# 							LINE.one_no_qty_equal_kgs line_one_no_qty_equal_kgs,

# 								CASE 
# 									WHEN PINE.total_rejected_qty_kg  != 0 AND PINE.total_rejected_qty_kg IS NOT NULL
# 										THEN PINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END patrol_rejected_qty_kg,
# 								CASE 
# 									WHEN PINE.total_rejected_qty_in_percentage  != 0 AND PINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN PINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END patrol_rejection_percent,
# 								CASE 
# 									WHEN PINE.total_inspected_qty  != 0 AND PINE.total_inspected_qty IS NOT NULL
# 										THEN PINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END patrol_inspected_qty,
# 							PINE.one_no_qty_equal_kgs patrol_one_no_qty_equal_kgs,

# 								CASE 
# 									WHEN LOINE.total_rejected_qty_kg  != 0 AND LOINE.total_rejected_qty_kg IS NOT NULL
# 										THEN LOINE.total_rejected_qty_kg 
# 									ELSE 0.0 
# 							END lot_rejected_qty_kg,
# 								CASE 
# 									WHEN LOINE.total_rejected_qty_in_percentage  != 0 AND LOINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN LOINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END lot_rejection_percent,
# 								CASE 
# 									WHEN LOINE.total_inspected_qty  != 0 AND LOINE.total_inspected_qty IS NOT NULL
# 										THEN LOINE.total_inspected_qty 
# 									ELSE 0.0 
# 							END lot_inspected_qty,
# 							LOINE.one_no_qty_equal_kgs lot_one_no_qty_equal_kgs,

# 								CASE 
# 									WHEN INE.total_rejected_qty  != 0 AND INE.total_rejected_qty IS NOT NULL
# 										THEN INE.total_rejected_qty 
# 									ELSE 0.0 
# 							END incoming_rejected_qty_nos,
# 								CASE 
# 									WHEN INE.total_rejected_qty_in_percentage  != 0 AND INE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN INE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END incoming_rejection_percent,
# 								CASE 
# 									WHEN INE.total_inspected_qty_nos  != 0 AND INE.total_inspected_qty_nos IS NOT NULL
# 										THEN INE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END incoming_inspected_qty_nos,

# 								CASE 
# 									WHEN VSINE.total_rejected_qty  != 0 AND VSINE.total_rejected_qty IS NOT NULL
# 										THEN VSINE.total_rejected_qty 
# 									ELSE 0.0 
# 							END final_rejected_qty_nos,
# 								CASE 
# 									WHEN VSINE.total_rejected_qty_in_percentage  != 0 AND VSINE.total_rejected_qty_in_percentage IS NOT NULL
# 										THEN VSINE.total_rejected_qty_in_percentage 
# 									ELSE 0.0 
# 							END final_rejection_percent,
# 								CASE 
# 									WHEN VSINE.total_inspected_qty_nos  != 0 AND VSINE.total_inspected_qty_nos IS NOT NULL
# 										THEN VSINE.total_inspected_qty_nos 
# 									ELSE 0.0 
# 							END final_inspected_qty_nos,
									
# 								IFNULL((SELECT DFSED.qty FROM `tabStock Entry Detail` DFSED 
# 									INNER JOIN `tabStock Entry` DFSE ON DFSE.name = DFSED.parent
# 									INNER JOIN `tabDeflashing Receipt Entry` DFRE ON DFRE.stock_entry_reference = DFSE.name
# 								WHERE 
# 									DFRE.scan_lot_number= INE.lot_no AND DFSED.t_warehouse IS NOT NULL LIMIT 1),0) deflashing_receipt_qty
# 						FROM 
# 							`tabInspection Entry` VSINE 
# 							INNER JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
# 							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabWork Plan Item` WPI ON WPI.lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND WPI.docstatus = 1
# 							LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = WPI.mould
# 							LEFT JOIN `tabMoulding Production Entry` MPE ON MPE.docstatus = 1 AND MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
# 							LEFT JOIN `tabBOM` B ON B.item = MPE.item_to_produce AND B.is_active=1 AND B.is_default=1
# 							INNER JOIN `tabBOM Item` BI ON BI.parent = B.name 
# 							INNER JOIN `tabItem` MMI ON MMI.name = BI.item_code
# 							LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
# 								AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
# 								AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
# 								AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
# 							LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
# 								AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no AND LRT.operation_type = 'ID Trimming' AND LRT.docstatus = 1
# 							LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no AND OLRT.operation_type = 'OD Trimming' AND OLRT.docstatus = 1
# 						WHERE 
# 							SED.t_warehouse IS NOT NULL AND 
# 							(VSINE.inspection_type = "Final Visual Inspection" OR VSINE.inspection_type = "Visual Inspection") AND VSINE.docstatus = 1 
# 							AND MMI.item_group = 'Compound' {condition} ) 
# 					DEMO """	
# 		result__ = frappe.db.sql(query , as_dict = 1) 
# 		if result__:
# 			total_production_qty_nos = 0.0
# 			total_compound_consumed_qty_kgs = 0.0
# 			total_patrol_inspected_qty_kgs = 0.0
# 			total_patrol_rejected_qty_kgs = 0.0
# 			total_line_inspected_qty_kgs = 0.0
# 			total_line_rejected_qty_kgs = 0.0
# 			total_lot_inspected_qty_kgs = 0.0
# 			total_lot_rejected_qty_kgs = 0.0
# 			total_incoming_inspected_qty_nos = 0.0
# 			total_incoming_rejected_qty_nos = 0.0
# 			total_final_inspected_qty_nos = 0.0
# 			total_final_rejected_qty_nos = 0.0

# 			total_patrol_inspected_qty_nos = 0.0
# 			total_patrol_rejected_qty_nos = 0.0
# 			total_line_inspected_qty_nos = 0.0
# 			total_line_rejected_qty_nos = 0.0
# 			total_lot_inspected_qty_nos = 0.0
# 			total_lot_rejected_qty_nos = 0.0

# 			for rej in result__:
# 				frappe.log_error(title="---1",message=rej)
# 				try:
# 					if rej.patrol_inspected_qty and rej.patrol_one_no_qty_equal_kgs:
# 						total_patrol_inspected_qty_nos += rej.patrol_inspected_qty  / rej.patrol_one_no_qty_equal_kgs
# 					if rej.patrol_rejection_kgs and rej.patrol_one_no_qty_equal_kgs:
# 						total_patrol_rejected_qty_nos += rej.patrol_rejection_kgs / rej.patrol_one_no_qty_equal_kgs
# 					if rej.line_inspected_qty and rej.line_one_no_qty_equal_kgs:
# 						total_line_inspected_qty_nos += rej.line_inspected_qty / rej.line_one_no_qty_equal_kgs
# 					if rej.line_rejection_kgs and rej.line_one_no_qty_equal_kgs:
# 						total_line_rejected_qty_nos += rej.line_rejection_kgs / rej.line_one_no_qty_equal_kgs
# 					if rej.lot_inspected_qty and rej.lot_one_no_qty_equal_kgs:
# 						total_lot_inspected_qty_nos += rej.lot_inspected_qty / rej.lot_one_no_qty_equal_kgs
# 					if rej.lot_rejection_kgs and rej.lot_one_no_qty_equal_kgs:
# 						total_lot_rejected_qty_nos += rej.lot_rejection_kgs / rej.lot_one_no_qty_equal_kgs
				
# 					rej['total_rejection'] = (
# 							( ( (rej.patrol_rejection_kgs / rej.patrol_one_no_qty_equal_kgs) if rej.patrol_rejection_kgs and rej.patrol_one_no_qty_equal_kgs else 0.0) 
# 								+ ( (rej.line_rejection_kgs / rej.line_one_no_qty_equal_kgs) if rej.line_rejection_kgs and rej.line_one_no_qty_equal_kgs else 0.0)
# 									+ ( (rej.lot_rejection_kgs / rej.lot_one_no_qty_equal_kgs) if rej.lot_rejection_kgs and rej.lot_one_no_qty_equal_kgs else 0.0)
# 										+ float(rej.incoming_rejection_nos) if rej.incoming_rejection_nos else 0.0
# 										+ float(rej.final_rejection_nos) if rej.final_rejection_nos else 0.0
# 							) /

# 							( ( (rej.patrol_inspected_qty  / rej.patrol_one_no_qty_equal_kgs) if rej.patrol_inspected_qty and rej.patrol_one_no_qty_equal_kgs else 0.0)
# 								+ ( (rej.line_inspected_qty / rej.line_one_no_qty_equal_kgs) if rej.line_inspected_qty and rej.line_one_no_qty_equal_kgs else 0.0)
# 									+ ( (rej.lot_inspected_qty / rej.lot_one_no_qty_equal_kgs) if rej.lot_inspected_qty and rej.lot_one_no_qty_equal_kgs else 0.0)
# 										+ float(rej.incoming_inspected_qty_nos) if rej.incoming_inspected_qty_nos else 0.0
# 										+ float(rej.final_inspected_qty_nos) if rej.final_inspected_qty_nos else 0.0
							
# 							)
# 						) * 100
# 					if rej.production_qty_nos:
# 						total_production_qty_nos += rej.production_qty_nos
# 					if rej.compound_consumed_qty_kgs:
# 						total_compound_consumed_qty_kgs += rej.compound_consumed_qty_kgs
# 					if rej.patrol_inspected_qty:
# 						total_patrol_inspected_qty_kgs += rej.patrol_inspected_qty
# 					if rej.patrol_rejection_kgs:
# 						total_patrol_rejected_qty_kgs += rej.patrol_rejection_kgs
# 					if rej.line_inspected_qty:
# 						total_line_inspected_qty_kgs += rej.line_inspected_qty
# 					if rej.line_rejection_kgs:
# 						total_line_rejected_qty_kgs += rej.line_rejection_kgs
# 					if rej.lot_inspected_qty:
# 						total_lot_inspected_qty_kgs += rej.lot_inspected_qty
# 					if rej.lot_rejection_kgs:
# 						total_lot_rejected_qty_kgs += rej.lot_rejection_kgs
# 					if rej.incoming_inspected_qty_nos:
# 						total_incoming_inspected_qty_nos += float(rej.incoming_inspected_qty_nos)
# 					if rej.incoming_rejection_nos:
# 						total_incoming_rejected_qty_nos += float(rej.incoming_rejection_nos)
# 					if rej.final_inspected_qty_nos:
# 						total_final_inspected_qty_nos += float(rej.final_inspected_qty_nos)
# 					if rej.final_rejection_nos:
# 						total_final_rejected_qty_nos += float(rej.final_rejection_nos)
# 				except ZeroDivisionError:
# 					rej['total_rejection'] = 0
# 			result__.append({"lot_no":"<b>Total</b>","production_qty_nos":total_production_qty_nos,
# 									"compound_consumed_qty_kgs":total_compound_consumed_qty_kgs,
# 									"line_rejection_kgs":((total_line_rejected_qty_kgs / total_line_inspected_qty_kgs )) if total_line_inspected_qty_kgs else 0.0,
# 									"line_rejection":((total_line_rejected_qty_kgs / total_line_inspected_qty_kgs ) * 100) if total_line_inspected_qty_kgs else 0.0,
# 									"patrol_rejection_kgs":((total_patrol_rejected_qty_kgs / total_patrol_inspected_qty_kgs )) if total_patrol_inspected_qty_kgs else 0.0,
# 									"patrol_rejection":((total_patrol_rejected_qty_kgs / total_patrol_inspected_qty_kgs ) * 100) if total_patrol_inspected_qty_kgs else 0.0,
# 									"lot_rejection_kgs":((total_lot_rejected_qty_kgs / total_lot_inspected_qty_kgs )) if total_lot_inspected_qty_kgs else 0.0,
# 									"lot_rejection":((total_lot_rejected_qty_kgs / total_lot_inspected_qty_kgs ) * 100) if total_lot_inspected_qty_kgs else 0.0,
# 									"incoming_rejection_nos":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos )) if total_incoming_inspected_qty_nos else 0.0,
# 									"incoming_rejection":((total_incoming_rejected_qty_nos / total_incoming_inspected_qty_nos ) * 100) if total_incoming_inspected_qty_nos else 0.0,
# 									"final_rejection_nos":((total_final_rejected_qty_nos / total_final_inspected_qty_nos )) if total_final_inspected_qty_nos else 0.0,
# 									"final_rejection":((total_final_rejected_qty_nos / total_final_inspected_qty_nos ) * 100) if total_final_inspected_qty_nos else 0.0,
# 									"total_rejection":(((total_patrol_rejected_qty_nos + total_line_rejected_qty_nos + total_lot_rejected_qty_nos + total_incoming_rejected_qty_nos + total_final_rejected_qty_nos) /
# 														(total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos + total_final_inspected_qty_nos)) * 100) if (total_patrol_inspected_qty_nos + total_line_inspected_qty_nos + total_lot_inspected_qty_nos + total_incoming_inspected_qty_nos + total_final_inspected_qty_nos) else 0.0})
# 		return result__	