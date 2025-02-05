# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_datas(filters)
	return columns, data

def get_columns():
	col__ = []
	col__.append(_("Moulding Date") + ":Date:100")
	col__.append(_("Job Card No") + ":Date:150")
	col__.append(_("Item Ref") + ":Link/Item:180")
	col__.append(_("No Of Lifts") + ":Int:100")
	col__.append(_("No Of Cavities") + ":Int:120")
	col__.append(_("Shift Number") + ":Int:120")
	col__.append(_("Shift Supervisor") + ":Link/Employee:80")
	col__.append(_("Press Operator") + ":Link/Employee:130")
	col__.append(_("Blank Sizing Operator") + ":Link/Employee:100")
	col__.append(_("Blank Cutting Operator") + ":Link/Employee:100")
	col__.append(_("Lot No") + ":Date:150")
	col__.append(_("Product Item") + ":Link/Item:150")
	col__.append(_("Target Lifts") + ":Int:60")
	col__.append(_("Incentive Per Lift") + ":Currency:60")
	col__.append(_("Moulding Incentive") + ":Currency:60")
	col__.append(_("Blanking Sizing Incentive")+":Currency:120")
	col__.append(_("Blank Cutting Incentive")+":Currency:120")
	return col__

def get_datas(filters):
	query = f""" SELECT
							MPE.job_card,DATE(MPE.modified),MPE.item_to_produce,MPE.number_of_lifts
						MPE.no_of_running_cavities,
							WP.shift_number,WP.supervisor_id
						MPE.employee,'','',MPE.scan_lot_number """