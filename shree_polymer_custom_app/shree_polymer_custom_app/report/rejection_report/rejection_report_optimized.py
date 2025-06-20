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
		c__.append(_('Line Rejection Nos')+':Float:160')
	c__.append(_('Line Rejection')+':Percent:120')
	if filters.get('show_rejection_qty'):
		c__.append(_('Patrol Rejection Nos')+':Float:160')
	c__.append(_('Patrol Rejection')+':Percent:130')
	if filters.get('show_rejection_qty'):
		c__.append(_('Lot Rejection Nos')+':Float:160')
	c__.append(_('Lot Rejection')+':Percent:120')
	if filters.get('report_type') == "Deflashing Rejection Report" or filters.get('report_type') == "Final Rejection Report":
		if filters.get('show_rejection_qty'):
			c__.append(_('Incoming Rejection Nos')+':Float:180')
		c__.append(_('Incoming Rejection')+':Percent:160')
	if filters.get('report_type') == "Final Rejection Report":
		if filters.get('show_rejection_qty'):
			c__.append(_('Final Rejection Nos')+':Float:180')
		c__.append(_('Final Rejection')+':Percent:120')
	c__.append(_('Total Rejection')+':Percent:120')
	return c__

def get_datas(filters):
	"""
	Optimized version of get_datas with better performance and error handling
	"""
	# Add mandatory date filter if not provided to limit scope
	if not filters.get('date'):
		filters['date'] = frappe.utils.today()
	
	if filters.get('report_type') == "Line Rejection Report":
		return get_line_rejection_data(filters)
	elif filters.get('report_type') == "Deflashing Rejection Report":
		return get_deflashing_rejection_data(filters)
	elif filters.get('report_type') == "Final Rejection Report":
		return get_final_rejection_data(filters)
	else:
		frappe.throw(_("Please select a valid report type"))

def get_line_rejection_data(filters):
	"""
	Optimized Line Rejection Report query
	"""
	# Build WHERE conditions
	conditions = ["MPE.docstatus = 1", "SE.docstatus = 1", "BBIS.docstatus = 1"]
	
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
	
	# Simplified query structure - breaking down the complex joins
	query = f"""
		SELECT 
			WP.date as date_,
			MPE.scan_lot_number as lot_no,
			MPE.item_to_produce as item,
			SE.bom_no as compound_bom_no,
			BBIS.press as press_no,
			MPE.employee as moulding_operator,
			BBIS.mould as mould_ref,
			ROUND((CAST(SED.qty as DECIMAL(10,3)) / 
				CASE WHEN MSP.avg_blank_wtproduct_gms != 0 
					THEN MSP.avg_blank_wtproduct_gms/1000 
					ELSE 1 END), 0) as production_qty_nos,
			(SELECT CAST(MSED.qty as DECIMAL(10,3)) 
			 FROM `tabStock Entry Detail` MSED
			 INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
			 WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name 
			 LIMIT 1) as compound_consumed_qty_kgs,
			COALESCE(LINE.total_rejected_qty, 0.0) as line_rejected_qty_nos,
			COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) as line_rejection_percent,
			COALESCE(LINE.inspected_qty_nos, 0.0) as line_inspected_qty,
			COALESCE(PINE.total_rejected_qty, 0.0) as patrol_rejected_qty_nos,
			COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) as patrol_rejection_percent,
			COALESCE(PINE.inspected_qty_nos, 0.0) as patrol_inspected_qty,
			COALESCE(LOINE.total_rejected_qty, 0.0) as lot_rejected_qty_nos,
			COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) as lot_rejection_percent,
			COALESCE(LOINE.inspected_qty_nos, 0.0) as lot_inspected_qty
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
		WHERE 
			SED.t_warehouse IS NOT NULL AND {where_clause}
		
		UNION ALL
		
		SELECT 
			WP.date as date_,
			MPE.scan_lot_number as lot_no,
			MPE.item_to_produce as item,
			SE.bom_no as compound_bom_no,
			BBIS.press as press_no,
			MPE.employee as moulding_operator,
			BBIS.mould as mould_ref,
			ROUND((CAST(SED.qty as DECIMAL(10,3)) / 
				CASE WHEN MSP.avg_blank_wtproduct_gms != 0 
					THEN MSP.avg_blank_wtproduct_gms/1000 
					ELSE 1 END), 0) as production_qty_nos,
			(SELECT CAST(MSED.qty as DECIMAL(10,3)) 
			 FROM `tabStock Entry Detail` MSED
			 INNER JOIN `tabItem` MI ON MI.name = MSED.item_code 
			 WHERE MI.item_group = 'Compound' AND MSED.parent = SE.name 
			 LIMIT 1) as compound_consumed_qty_kgs,
			COALESCE(LINE.total_rejected_qty, 0.0) as line_rejected_qty_nos,
			COALESCE(LINE.total_rejected_qty_in_percentage, 0.0) as line_rejection_percent,
			COALESCE(LINE.inspected_qty_nos, 0.0) as line_inspected_qty,
			COALESCE(PINE.total_rejected_qty, 0.0) as patrol_rejected_qty_nos,
			COALESCE(PINE.total_rejected_qty_in_percentage, 0.0) as patrol_rejection_percent,
			COALESCE(PINE.inspected_qty_nos, 0.0) as patrol_inspected_qty,
			COALESCE(LOINE.total_rejected_qty, 0.0) as lot_rejected_qty_nos,
			COALESCE(LOINE.total_rejected_qty_in_percentage, 0.0) as lot_rejection_percent,
			COALESCE(LOINE.inspected_qty_nos, 0.0) as lot_inspected_qty
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
		WHERE 
			SED.t_warehouse IS NOT NULL AND {where_clause}
		ORDER BY date_ DESC
		LIMIT 1000
	"""
	
	try:
		result__ = frappe.db.sql(query, as_dict=1, timeout=30) 
		
		if result__:
			# Calculate totals
			total_production_qty_nos = 0.0
			total_compound_consumed_qty_kgs = 0.0
			total_patrol_inspected_qty_nos = 0.0
			total_patrol_rejected_qty_nos = 0.0
			total_line_inspected_qty_nos = 0.0
			total_line_rejected_qty_nos = 0.0
			total_lot_inspected_qty_nos = 0.0
			total_lot_rejected_qty_nos = 0.0
			
			for x in result__:
				# Add total rejection calculation
				total_inspected = (x.get('patrol_inspected_qty', 0) + 
								  x.get('line_inspected_qty', 0) + 
								  x.get('lot_inspected_qty', 0))
				total_rejected = (x.get('patrol_rejected_qty_nos', 0) + 
								 x.get('line_rejected_qty_nos', 0) + 
								 x.get('lot_rejected_qty_nos', 0))
				
				x['total_rejection'] = (total_rejected / total_inspected * 100) if total_inspected > 0 else 0.0
				
				# Update running totals
				if x.get('production_qty_nos'):
					total_production_qty_nos += x['production_qty_nos']
				if x.get('compound_consumed_qty_kgs'):
					total_compound_consumed_qty_kgs += x['compound_consumed_qty_kgs']
				if x.get('patrol_inspected_qty'):
					total_patrol_inspected_qty_nos += x['patrol_inspected_qty']
				if x.get('patrol_rejected_qty_nos'):
					total_patrol_rejected_qty_nos += x['patrol_rejected_qty_nos']
				if x.get('line_inspected_qty'):
					total_line_inspected_qty_nos += x['line_inspected_qty']
				if x.get('line_rejected_qty_nos'):
					total_line_rejected_qty_nos += x['line_rejected_qty_nos']
				if x.get('lot_inspected_qty'):
					total_lot_inspected_qty_nos += x['lot_inspected_qty']
				if x.get('lot_rejected_qty_nos'):
					total_lot_rejected_qty_nos += x['lot_rejected_qty_nos']
			
			# Add totals row
			result__.append({
				"mould_ref": "<b>Total</b>",
				"production_qty_nos": total_production_qty_nos,
				"compound_consumed_qty_kgs": total_compound_consumed_qty_kgs,
				"line_rejection": (total_line_rejected_qty_nos / total_line_inspected_qty_nos * 100) if total_line_inspected_qty_nos else 0.0,
				"patrol_rejection": (total_patrol_rejected_qty_nos / total_patrol_inspected_qty_nos * 100) if total_patrol_inspected_qty_nos else 0.0,
				"lot_rejection": (total_lot_rejected_qty_nos / total_lot_inspected_qty_nos * 100) if total_lot_inspected_qty_nos else 0.0,
				"total_rejection": ((total_line_rejected_qty_nos + total_patrol_rejected_qty_nos + total_lot_rejected_qty_nos) /
								   (total_line_inspected_qty_nos + total_patrol_inspected_qty_nos + total_lot_inspected_qty_nos) * 100) if (total_line_inspected_qty_nos + total_patrol_inspected_qty_nos + total_lot_inspected_qty_nos) else 0.0
			})
		
		return result__
		
	except Exception as e:
		frappe.log_error(f"Line Rejection Report Error: {str(e)}", "Rejection Report")
		frappe.throw(_("Report generation failed. Please contact administrator. Error: {0}").format(str(e)))

def get_deflashing_rejection_data(filters):
	"""
	Simplified Deflashing Rejection Report - placeholder for now
	"""
	frappe.msgprint(_("Deflashing Rejection Report is being optimized. Please use Line Rejection Report for now."))
	return []

def get_final_rejection_data(filters):
	"""
	Simplified Final Rejection Report - placeholder for now
	"""
	frappe.msgprint(_("Final Rejection Report is being optimized. Please use Line Rejection Report for now."))
	return []

# Keep the original utility functions
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
