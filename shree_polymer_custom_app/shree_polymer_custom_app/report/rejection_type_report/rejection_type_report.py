# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

exe_fields = ["rejection_perc","rej_qty","insp_qty","insp_id","spp_ref","lot_no","date"]
def execute(filters=None):
	columns = get_columns() 
	data = get_datas(filters,columns)
	return columns, data

def get_columns():
	col__ = [
		{	
		"label": _("Date"),
		"fieldname": "date",
		"fieldtype": "Data",
		"width": 130,
		},
		{	
		"label": _("Card #"),
		"fieldname": "lot_no",
		"fieldtype": "Data",
		"width": 130,
		},
		{	
		"label": _("SPP Ref"),
		"fieldname": "spp_ref",
		"fieldtype": "Link",
		"width": 80,
		"options":"Item"
		},
		{	
		"label": _("Insp ID"),
		"fieldname": "insp_id",
		"fieldtype": "Data",
		"width": 180,
		},
		{	
		"label": _("Insp Q"),
		"fieldname": "insp_qty",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("Rej Q"),
		"fieldname": "rej_qty",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("Rej %"),
		"fieldname": "rejection_perc",
		"fieldtype": "Percent",
		"width": 70,
		},
		{	
		"label": _("F"),
		"fieldname": "flow",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("BU"),
		"fieldname": "bubble",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("CM"),
		"fieldname": "cutmark",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("DF"),
		"fieldname": "loose_flash",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("RIB"),
		"fieldname": "rib",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("DL"),
		"fieldname": "tool_mark",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("BO"),
		"fieldname": "bonding_failure",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("UF"),
		"fieldname": "under_fill",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("DT"),
		"fieldname": "thread_dirt_fp",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("UC"),
		"fieldname": "under_cure",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("SD"),
		"fieldname": "surface_defect",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("OC"),
		"fieldname": "over_cure",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("OT"),
		"fieldname": "over_trim",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("MD"),
		"fieldname": "mould_damage",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("WD"),
		"fieldname": "wood_particle",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("WV"),
		"fieldname": "washer_visible",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("TK U/S"),
		"fieldname": "thickness_undrsze",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("BL"),
		"fieldname": "blaster",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("DP"),
		"fieldname": "dispersn_problem",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("T US"),
		"fieldname": "thickness_undrsze_tus",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("TK OS"),
		"fieldname": "thickness_oversize",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("ID US"),
		"fieldname": "id_undrsze",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("ID OS"),
		"fieldname": "id_oversize",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("OD US"),
		"fieldname": "io_undrsze",
		"fieldtype": "Int",
		"width": 70,
		},
		{	
		"label": _("OD OS"),
		"fieldname": "od_oversize",
		"fieldtype": "Int",
		"width": 70,
		},
	]
	return col__

def get_datas(filters,columns):
	condition = ""
	Inspection_type = filters.get('inspection_type')
	default_select_query = ""
	select_query = ""
	union_select = ""
	if filters.get('spp_batch_no'):
		condition += f" AND JC.batch_code LIKE '%{filters.get('spp_batch_no')}%' "
	if filters.get('from_date'):
		condition += f" AND DATE(WP.date) >= '{filters.get('from_date')}' "
	if filters.get('to_date'):
		condition += f" AND DATE(WP.date) <= '{filters.get('to_date')}' "
	if Inspection_type == "Line Inspection" or Inspection_type == "Lot Inspection":
		if Inspection_type == "Line Inspection":
			default_select_query = f""" 	
											IE.total_rejected_qty 
										total_ins_rejected_qty ,
											IE.inspected_qty_nos 
										total_ins_inspected_qty,
											IE.inspector_name
										inspector_name,
											IE.product_ref_no
										ins_item,
									"""
		elif Inspection_type == "Lot Inspection":
			default_select_query = f""" 
											LO.total_rejected_qty
										total_ins_rejected_qty ,
											LO.inspected_qty_nos
										total_ins_inspected_qty,
										 	LO.inspector_name
										inspector_name,
										 	LO.product_ref_no
										ins_item, 
									"""
	else:
		default_select_query = f""" 
									( SELECT SUM(INS.total_rejected_qty)
										FROM `tabInspection Entry` INS
												WHERE INS.docstatus = 1 AND INS.inspection_type = "{Inspection_type}"
													AND INS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_ins_rejected_qty,
									( SELECT SUM(INS.total_inspected_qty_nos)
										FROM `tabInspection Entry` INS
												WHERE INS.docstatus = 1 AND INS.inspection_type = "{Inspection_type}"
													AND INS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								total_ins_inspected_qty, 
									( SELECT GROUP_CONCAT(DISTINCT INS.inspector_name)
										FROM `tabInspection Entry` INS
												WHERE INS.docstatus = 1 AND INS.inspection_type = "{Inspection_type}"
													AND INS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								inspector_name,
									( SELECT GROUP_CONCAT(DISTINCT INS.product_ref_no)
										FROM `tabInspection Entry` INS
												WHERE INS.docstatus = 1 AND INS.inspection_type = "{Inspection_type}"
													AND INS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%'))
								ins_item,"""
	for rej in columns:
		if rej.get('fieldname') not in exe_fields:
			label_1 = rej.get('fieldname').split("_")
			label_2 = (" ").join(label_1)
			select_query += f""" ( SELECT IFNULL(SUM(INSI.rejected_qty),0)
											FROM `tabInspection Entry` INS
												INNER JOIN `tabInspection Entry Item` INSI ON INSI.parent = INS.name
													WHERE INS.docstatus = 1 AND INS.inspection_type =  "{Inspection_type}"
														AND INS.lot_no LIKE CONCAT('%',MPE.scan_lot_number,'%')
														AND INSI.type_of_defect LIKE "{label_2}%")
								{rej.get('fieldname')}, """
			union_select += f"{rej.get('fieldname')},"
	select_query = select_query[:-2]
	union_select = union_select[:-1]
	query = f""" 
				SELECT date,batch_code lot_no,
						(CASE 
							WHEN 
								total_ins_rejected_qty != 0
							THEN ((total_ins_rejected_qty / total_ins_inspected_qty) * 100)
						ELSE
							0
						END)
					rejection_perc,
					total_ins_inspected_qty insp_qty,
					total_ins_rejected_qty rej_qty,
					inspector_name insp_id,
					ins_item spp_ref,
					{union_select}
					FROM (
							SELECT DISTINCT 
								DATE(MPE.moulding_date) date,JC.batch_code,
							{default_select_query}
							{select_query}
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
							{default_select_query}
							{select_query}
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
	calculate_total_rejection(resp__,columns)
	return resp__
 
def calculate_total_rejection(resp__,columns):
	if resp__ :
		overall_res = {"batch_code":"<b>Total</b>"}
		total_inspected_qty = 0
		total_rejected_qty = 0
		total_ins_inspected_qty = 0
		total_ins_rejected_qty = 0
		for rej in columns:
			if rej.get('fieldname') not in exe_fields:
				overall_res[rej.get('fieldname')] = 0
		for k in resp__:
			for key in k:
				if key in overall_res:
					overall_res[key] = overall_res.get(key) + k.get(key)
			total_inspected_qty += k.insp_qty if k.insp_qty else 0.0 
			total_rejected_qty += k.rej_qty if k.rej_qty else 0
			total_ins_inspected_qty += k.insp_qty if k.insp_qty else 0.0 
			total_ins_rejected_qty += k.rej_qty if k.rej_qty else 0.0 
		if total_ins_rejected_qty:
			__total_ins_rejection =  (total_ins_rejected_qty / total_ins_inspected_qty) * 100
		else:
			__total_ins_rejection = 0
		overall_res['insp_qty'] = total_inspected_qty
		overall_res['rej_qty'] = total_rejected_qty
		overall_res['rejection_perc'] = __total_ins_rejection
		resp__.append(overall_res)


