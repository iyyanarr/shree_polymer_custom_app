# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_datas(filters)
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
	
	# Add default date filter to prevent unlimited queries
	if not filters.get('date'):
		filters['date'] = frappe.utils.today()  # Default to today only
		frappe.msgprint(_("No date filter provided. Showing data for today only. Date: {0}").format(filters['date']))
	
	if filters.get('report_type') == "Line Rejection Report":
		# Build conditions for Line Rejection Report
		conditions = ["MPE.docstatus = 1", "SE.docstatus = 1", "BBIS.docstatus = 1", "SED.t_warehouse IS NOT NULL"]
		
		if filters.get('date'):
			conditions.append(f"DATE(WP.date) = '{filters.get('date')}'")
		if filters.get('t_item'):
			conditions.append(f"MPE.item_to_produce = '{filters.get('t_item')}'")
		if filters.get('compound_bom_no'):
			conditions.append(f"SE.bom_no = '{filters.get('compound_bom_no')}'")
		if filters.get('press_no'):
			conditions.append(f"BBIS.press = '{filters.get('press_no')}'")
		if filters.get('moulding_operator'):
			conditions.append(f"MPE.employee = '{filters.get('moulding_operator')}'")
		if filters.get('mould_ref'):
			conditions.append(f"BBIS.mould = '{filters.get('mould_ref')}'")
		
		where_clause = " AND ".join(conditions)
		
		# Simplified query structure - direct SELECT without complex subqueries
		query = f"""
		SELECT 
			WP.date as date_,
			MPE.scan_lot_number as lot_no,
			MPE.item_to_produce as item,
			SE.bom_no as compound_bom_no,
			BBIS.press as press_no,
			MPE.employee as moulding_operator,
			BBIS.mould as mould_ref,
			ROUND(CAST(SED.qty as DECIMAL(10,3)) / 
				CASE WHEN MSP.avg_blank_wtproduct_gms != 0 
					THEN MSP.avg_blank_wtproduct_gms/1000 
					ELSE 1 END, 0) as production_qty_nos,
			(SELECT CAST(MSED.qty as DECIMAL(10,3)) 
			 FROM `tabStock Entry Detail` MSED
			 INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
			 WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name 
			 LIMIT 1) as compound_consumed_qty_kgs,
			COALESCE(LINE.total_rejected_qty, 0.0) as line_rejection_nos,
			COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) as line_rejection,
			COALESCE(PINE.total_rejected_qty, 0.0) as patrol_rejection_nos,
			COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) as patrol_rejection,
			COALESCE(LOINE.total_rejected_qty, 0.0) as lot_rejection_nos,
			COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) as lot_rejection,
			((COALESCE(PINE.total_rejected_qty, 0.0) + COALESCE(LINE.total_rejected_qty, 0.0) + COALESCE(LOINE.total_rejected_qty, 0.0)) / 
			 (COALESCE(PINE.inspected_qty_nos, 0.0) + COALESCE(LINE.inspected_qty_nos, 0.0) + COALESCE(LOINE.inspected_qty_nos, 0.0))) * 100 as total_rejection,
			COALESCE(PINE.inspected_qty_nos, 0.0) as patrol_inspected_qty_nos,
			COALESCE(LINE.inspected_qty_nos, 0.0) as line_inspected_qty_nos,
			COALESCE(LOINE.inspected_qty_nos, 0.0) as lot_inspected_qty_nos
		FROM 
			`tabMoulding Production Entry` MPE 
			INNER JOIN `tabWork Plan Item` WPI ON WPI.job_card = MPE.job_card AND WPI.docstatus = 1
			INNER JOIN `tabWork Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
			INNER JOIN `tabBlank Bin Issue` BBIS ON 
				BBIS.scan_production_lot = MPE.scan_lot_number AND BBIS.docstatus = 1
			INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference
			INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.docstatus = 1
			LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
				AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
			LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
				AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
				AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
				AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
		WHERE {where_clause}
		
		UNION ALL
		
		SELECT 
			WP.date as date_,
			MPE.scan_lot_number as lot_no,
			MPE.item_to_produce as item,
			SE.bom_no as compound_bom_no,
			BBIS.press as press_no,
			MPE.employee as moulding_operator,
			BBIS.mould as mould_ref,
			ROUND(CAST(SED.qty as DECIMAL(10,3)) / 
				CASE WHEN MSP.avg_blank_wtproduct_gms != 0 
					THEN MSP.avg_blank_wtproduct_gms/1000 
					ELSE 1 END, 0) as production_qty_nos,
			(SELECT CAST(MSED.qty as DECIMAL(10,3)) 
			 FROM `tabStock Entry Detail` MSED
			 INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
			 WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name 
			 LIMIT 1) as compound_consumed_qty_kgs,
			COALESCE(LINE.total_rejected_qty, 0.0) as line_rejection_nos,
			COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) as line_rejection,
			COALESCE(PINE.total_rejected_qty, 0.0) as patrol_rejection_nos,
			COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) as patrol_rejection,
			COALESCE(LOINE.total_rejected_qty, 0.0) as lot_rejection_nos,
			COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) as lot_rejection,
			((COALESCE(PINE.total_rejected_qty, 0.0) + COALESCE(LINE.total_rejected_qty, 0.0) + COALESCE(LOINE.total_rejected_qty, 0.0)) / 
			 (COALESCE(PINE.inspected_qty_nos, 0.0) + COALESCE(LINE.inspected_qty_nos, 0.0) + COALESCE(LOINE.inspected_qty_nos, 0.0))) * 100 as total_rejection,
			COALESCE(PINE.inspected_qty_nos, 0.0) as patrol_inspected_qty_nos,
			COALESCE(LINE.inspected_qty_nos, 0.0) as line_inspected_qty_nos,
			COALESCE(LOINE.inspected_qty_nos, 0.0) as lot_inspected_qty_nos
		FROM 
			`tabMoulding Production Entry` MPE 
			INNER JOIN `tabAdd On Work Plan Item` WPI ON WPI.job_card = MPE.job_card AND WPI.docstatus = 1
			INNER JOIN `tabAdd On Work Planning` WP ON WPI.parent = WP.name AND WP.docstatus = 1
			INNER JOIN `tabBlank Bin Issue` BBIS ON 
				BBIS.scan_production_lot = MPE.scan_lot_number AND BBIS.docstatus = 1
			INNER JOIN `tabStock Entry` SE ON SE.name = MPE.stock_entry_reference
			INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.docstatus = 1
			LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
				AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
			LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = MPE.scan_lot_number 
				AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = MPE.scan_lot_number 
				AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = MPE.scan_lot_number 
				AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
		WHERE {where_clause}
		ORDER BY date_ DESC 
		LIMIT 100 """
		try:	
			result__ = frappe.db.sql(query, as_dict=1)
		except Exception as e:
			frappe.log_error(f"Line Rejection Report Query Error: {str(e)}", "Rejection Report")
			frappe.throw(_("Query failed: {0}").format(str(e)))
		
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
							DFR.scan_lot_number AS lot_no,
							B.item,
							CB.name AS compound_bom_no,
							BBIS.press AS press_no,
							MPE.employee AS moulding_operator,
							DFR.from_warehouse_id AS deflashing_operator,
							BBIS.mould AS mould_ref,
							ROUND(CAST(SED.qty as DECIMAL(10,3)), 0) AS production_qty_nos,
							( SELECT CAST(MSED.qty as DECIMAL(10,3)) 
							  FROM `tabStock Entry Detail` MSED
							  INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
							  WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name 
							  LIMIT 1) AS compound_consumed_qty_kgs,
							COALESCE(LINE.total_rejected_qty, 0.0) AS line_rejected_qty_nos,
							COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) AS line_rejection_percent,
							COALESCE(LINE.inspected_qty_nos, 0.0) AS line_inspected_qty,
							COALESCE(PINE.total_rejected_qty, 0.0) AS patrol_rejected_qty_nos,
							COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) AS patrol_rejection_percent,
							COALESCE(PINE.inspected_qty_nos, 0.0) AS patrol_inspected_qty,
							COALESCE(LOINE.total_rejected_qty, 0.0) AS lot_rejected_qty_nos,
							COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) AS lot_rejection_percent,
							COALESCE(LOINE.inspected_qty_nos, 0.0) AS lot_inspected_qty,
							COALESCE(INE.total_rejected_qty, 0.0) AS incoming_rejected_qty_nos,
							COALESCE(INE.total_rejected_qty_in_percentage, 0.0) AS incoming_rejection_percent,
							COALESCE(INE.total_inspected_qty_nos, 0.0) AS incoming_inspected_qty_nos,
							COALESCE(LINE.inspected_qty_nos, 0.0) AS line_inspected_qty_nos,
							COALESCE(PINE.inspected_qty_nos, 0.0) AS patrol_inspected_qty_nos,
							COALESCE(LOINE.inspected_qty_nos, 0.0) AS lot_inspected_qty_nos
						FROM 
							`tabDeflashing Receipt Entry` DFR 
							INNER JOIN `tabBOM Item` BI ON BI.item_code = DFR.item AND DFR.docstatus = 1
							INNER JOIN `tabBOM` B ON BI.parent = B.name AND B.is_active=1 AND B.is_default=1
							INNER JOIN `tabBOM` CB ON CB.Item = DFR.item AND CB.is_active=1 AND CB.is_default=1
							INNER JOIN `tabBOM Item` CBI ON CBI.parent = CB.name 
							INNER JOIN `tabStock Entry` SE ON SE.name = DFR.stock_entry_reference AND SE.docstatus = 1
							INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.is_finished_item = 1
							INNER JOIN `tabBlank Bin Issue` BBIS ON 
								BBIS.scan_production_lot = SUBSTRING_INDEX(DFR.scan_lot_number, '-', 1)
								AND BBIS.docstatus = 1
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
						WHERE SED.t_warehouse IS NOT NULL {condition} 
						ORDER BY INE.posting_date DESC LIMIT 1000 """
		result__ = frappe.db.sql(query, as_dict=1) 
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
				# Calculate total rejection for each record
				total_inspected = (x.get('patrol_inspected_qty_nos', 0) + 
								  x.get('line_inspected_qty_nos', 0) + 
								  x.get('lot_inspected_qty_nos', 0) + 
								  x.get('incoming_inspected_qty_nos', 0))
				total_rejected = (x.get('patrol_rejected_qty_nos', 0) + 
								 x.get('line_rejected_qty_nos', 0) + 
								 x.get('lot_rejected_qty_nos', 0) + 
								 x.get('incoming_rejected_qty_nos', 0))
				
				x['total_rejection'] = (total_rejected / total_inspected * 100) if total_inspected > 0 else 0.0
				
				# Add to column names expected by UI
				x['line_rejection_nos'] = x.get('line_rejected_qty_nos', 0)
				x['line_rejection'] = x.get('line_rejection_percent', 0)
				x['patrol_rejection_nos'] = x.get('patrol_rejected_qty_nos', 0)
				x['patrol_rejection'] = x.get('patrol_rejection_percent', 0)
				x['lot_rejection_nos'] = x.get('lot_rejected_qty_nos', 0)
				x['lot_rejection'] = x.get('lot_rejection_percent', 0)
				x['incoming_rejection_nos'] = x.get('incoming_rejected_qty_nos', 0)
				x['incoming_rejection'] = x.get('incoming_rejection_percent', 0)
				
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
				except ZeroDivisionError:
					pass
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
		# Build conditions for Final Rejection Report
		condition = ""
		if filters.get('date'):
			condition += f""" AND DATE(VSINE.posting_date) = '{filters.get('date')}' """
		if filters.get('f_item'):
			condition += f""" AND VSINE.product_ref_no = '{filters.get('f_item')}' """
		if filters.get('deflashing_operator'):
			condition += f""" AND VSINE.source_warehouse = '{filters.get('deflashing_operator')}' """
		
		# Final Rejection Report query - UNION of both historical and recent data 
		# Historical data from tabInspection Entry (before May 2025) and recent data from tabSPP Inspection Entry (after May 2025)
		query = f""" 
		(SELECT DISTINCT
			VSINE.lot_no,
			VSINE.product_ref_no AS item,
			COALESCE(B.name, '') AS compound_bom_no,
			COALESCE(BBIS.press, '') AS press_no,
			COALESCE(MPE.employee, '') AS moulding_operator,
			COALESCE(VSINE.source_warehouse, '') AS deflashing_operator,
			COALESCE(BBIS.mould, '') AS mould_ref,
			COALESCE(LRT.operator_id, '') AS trimming_id_operator,
			COALESCE(OLRT.operator_id, '') AS trimming_od_operator,
			COALESCE(ROUND(CAST(SED.qty as DECIMAL(10,3)) / 
				CASE WHEN MSP.avg_blank_wtproduct_gms != 0 
					THEN MSP.avg_blank_wtproduct_gms/1000 
					ELSE 1 END, 0), 0) AS production_qty_nos,
			COALESCE((SELECT CAST(MSED.qty as DECIMAL(10,3)) 
				FROM `tabStock Entry Detail` MSED
				INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
				WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name 
				LIMIT 1), 0.0) AS compound_consumed_qty_kgs,
			COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) AS line_rejection_percent,
			COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) AS patrol_rejection_percent,
			COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) AS lot_rejection_percent,
			COALESCE(INE.total_rejected_qty_in_percentage, 0.0) AS incoming_rejection_percent,
			COALESCE(VSINE.total_rejected_qty_in_percentage, 0.0) AS final_rejection_percent,
			COALESCE(LINE.total_rejected_qty, 0.0) AS line_rejected_qty_nos,
			COALESCE(PINE.total_rejected_qty, 0.0) AS patrol_rejected_qty_nos,
			COALESCE(LOINE.total_rejected_qty, 0.0) AS lot_rejected_qty_nos,
			COALESCE(INE.total_rejected_qty, 0.0) AS incoming_rejected_qty_nos,
			COALESCE(VSINE.total_rejected_qty, 0.0) AS final_rejected_qty_nos,
			COALESCE(LINE.inspected_qty_nos, 0.0) AS line_inspected_qty_nos,
			COALESCE(PINE.inspected_qty_nos, 0.0) AS patrol_inspected_qty_nos,
			COALESCE(LOINE.inspected_qty_nos, 0.0) AS lot_inspected_qty_nos,
			COALESCE(INE.total_inspected_qty_nos, 0.0) AS incoming_inspected_qty_nos,
			COALESCE(VSINE.total_inspected_qty_nos, 0.0) AS final_inspected_qty_nos
		FROM `tabInspection Entry` VSINE 
			LEFT JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
			LEFT JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.t_warehouse IS NOT NULL
			LEFT JOIN `tabBlank Bin Issue` BBIS ON 
				BBIS.scan_production_lot = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND BBIS.docstatus = 1
			LEFT JOIN `tabMoulding Production Entry` MPE ON 
				MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND MPE.docstatus = 1
			LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
				AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
			LEFT JOIN `tabBOM` B ON B.item = VSINE.product_ref_no AND B.is_active=1 AND B.is_default=1
			LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
			LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
				AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
				AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
				AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
				AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
			LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no 
				AND LRT.operation_type = 'ID Trimming' AND LRT.docstatus = 1
			LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no 
				AND OLRT.operation_type = 'OD Trimming' AND OLRT.docstatus = 1
		WHERE VSINE.docstatus = 1 
			AND VSINE.inspection_type = 'Final Visual Inspection' 
			AND DATE(VSINE.posting_date) < '2025-05-02' {condition})
		
		UNION ALL
		
		(SELECT DISTINCT
			VSINE.lot_no,
			VSINE.product_ref_no AS item,
			COALESCE(B.name, '') AS compound_bom_no,
			COALESCE(BBIS.press, '') AS press_no,
			COALESCE(MPE.employee, '') AS moulding_operator,
			COALESCE(VSINE.source_warehouse, '') AS deflashing_operator,
			COALESCE(BBIS.mould, '') AS mould_ref,
			COALESCE(LRT.operator_id, '') AS trimming_id_operator,
			COALESCE(OLRT.operator_id, '') AS trimming_od_operator,
			COALESCE(ROUND(CAST(SED.qty as DECIMAL(10,3)) / 
				CASE WHEN MSP.avg_blank_wtproduct_gms != 0 
					THEN MSP.avg_blank_wtproduct_gms/1000 
					ELSE 1 END, 0), 0) AS production_qty_nos,
			COALESCE((SELECT CAST(MSED.qty as DECIMAL(10,3)) 
				FROM `tabStock Entry Detail` MSED
				INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
				WHERE MI.item_group = 'Compound' AND MSED.parent = MSE.name 
				LIMIT 1), 0.0) AS compound_consumed_qty_kgs,
			COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) AS line_rejection_percent,
			COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) AS patrol_rejection_percent,
			COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) AS lot_rejection_percent,
			COALESCE(INE.total_rejected_qty_in_percentage, 0.0) AS incoming_rejection_percent,
			COALESCE(VSINE.total_rejected_qty_in_percentage, 0.0) AS final_rejection_percent,
			COALESCE(LINE.total_rejected_qty, 0.0) AS line_rejected_qty_nos,
			COALESCE(PINE.total_rejected_qty, 0.0) AS patrol_rejected_qty_nos,
			COALESCE(LOINE.total_rejected_qty, 0.0) AS lot_rejected_qty_nos,
			COALESCE(INE.total_rejected_qty, 0.0) AS incoming_rejected_qty_nos,
			COALESCE(VSINE.total_rejected_qty, 0.0) AS final_rejected_qty_nos,
			COALESCE(LINE.inspected_qty_nos, 0.0) AS line_inspected_qty_nos,
			COALESCE(PINE.inspected_qty_nos, 0.0) AS patrol_inspected_qty_nos,
			COALESCE(LOINE.inspected_qty_nos, 0.0) AS lot_inspected_qty_nos,
			COALESCE(INE.total_inspected_qty_nos, 0.0) AS incoming_inspected_qty_nos,
			COALESCE(VSINE.total_inspected_qty_nos, 0.0) AS final_inspected_qty_nos
		FROM `tabSPP Inspection Entry` VSINE 
			LEFT JOIN `tabStock Entry` SE ON SE.name = VSINE.vs_pdir_stock_entry_ref AND SE.docstatus = 1
			LEFT JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name AND SED.t_warehouse IS NOT NULL
			LEFT JOIN `tabBlank Bin Issue` BBIS ON 
				BBIS.scan_production_lot = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND BBIS.docstatus = 1
			LEFT JOIN `tabMoulding Production Entry` MPE ON 
				MPE.scan_lot_number = SUBSTRING_INDEX(VSINE.lot_no, '-', 1) AND MPE.docstatus = 1
			LEFT JOIN `tabMould Specification` MSP ON MSP.mould_ref = BBIS.mould
				AND MSP.spp_ref = MPE.item_to_produce AND MSP.mould_status = 'ACTIVE'
			LEFT JOIN `tabBOM` B ON B.item = VSINE.product_ref_no AND B.is_active=1 AND B.is_default=1
			LEFT JOIN `tabStock Entry` MSE ON MSE.name = MPE.stock_entry_reference AND MSE.docstatus = 1
			LEFT JOIN `tabInspection Entry` LINE ON LINE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
				AND LINE.inspection_type = "Line Inspection" AND LINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` PINE ON PINE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
				AND PINE.inspection_type = "Patrol Inspection" AND PINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` LOINE ON LOINE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1)
				AND LOINE.inspection_type = "Lot Inspection" AND LOINE.docstatus = 1
			LEFT JOIN `tabInspection Entry` INE ON (INE.lot_no = VSINE.lot_no OR INE.lot_no = SUBSTRING_INDEX(VSINE.lot_no, '-', 1))
				AND INE.inspection_type = "Incoming Inspection" AND INE.docstatus = 1
			LEFT JOIN `tabLot Resource Tagging` LRT ON LRT.scan_lot_no = VSINE.lot_no 
				AND LRT.operation_type = 'ID Trimming' AND LRT.docstatus = 1
			LEFT JOIN `tabLot Resource Tagging` OLRT ON OLRT.scan_lot_no = VSINE.lot_no 
				AND OLRT.operation_type = 'OD Trimming' AND OLRT.docstatus = 1
		WHERE VSINE.docstatus = 1 
			AND VSINE.inspection_type = 'Final Visual Inspection' 
			AND DATE(VSINE.posting_date) >= '2025-05-02' {condition})
		
		ORDER BY lot_no DESC 
		LIMIT 500 """
		result__ = frappe.db.sql(query, as_dict=1)
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
				if rej.get('final_rejected_qty_nos') and rej.get('final_inspected_qty_nos'):	
					final_rejection = (rej['final_rejected_qty_nos'] / rej['final_inspected_qty_nos']) * 100
					rej['final_rejection'] = final_rejection
				
				# Calculate total rejection for each record
				total_inspected = (rej.get('patrol_inspected_qty_nos', 0) + 
								  rej.get('line_inspected_qty_nos', 0) + 
								  rej.get('lot_inspected_qty_nos', 0) + 
								  rej.get('incoming_inspected_qty_nos', 0) + 
								  rej.get('final_inspected_qty_nos', 0))
				total_rejected = (rej.get('patrol_rejected_qty_nos', 0) + 
								 rej.get('line_rejected_qty_nos', 0) + 
								 rej.get('lot_rejected_qty_nos', 0) + 
								 rej.get('incoming_rejected_qty_nos', 0) + 
								 rej.get('final_rejected_qty_nos', 0))
				
				rej['total_rejection'] = (total_rejected / total_inspected * 100) if total_inspected > 0 else 0.0
				
				# Add to column names expected by UI
				rej['line_rejection_nos'] = rej.get('line_rejected_qty_nos', 0)
				rej['line_rejection'] = rej.get('line_rejection_percent', 0)
				rej['patrol_rejection_nos'] = rej.get('patrol_rejected_qty_nos', 0)
				rej['patrol_rejection'] = rej.get('patrol_rejection_percent', 0)
				rej['lot_rejection_nos'] = rej.get('lot_rejected_qty_nos', 0)
				rej['lot_rejection'] = rej.get('lot_rejection_percent', 0)
				rej['incoming_rejection_nos'] = rej.get('incoming_rejected_qty_nos', 0)
				rej['incoming_rejection'] = rej.get('incoming_rejection_percent', 0)
				rej['final_rejection_nos'] = rej.get('final_rejected_qty_nos', 0)
				
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
									"total_rejection": ((over_all_total_rejections_nos / over_all_total_inspected_nos) * 100) if over_all_total_inspected_nos else 0.0})
		return result__	
	
	# Default fallback if no report type matches
	return []

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
