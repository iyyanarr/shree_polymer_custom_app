# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BlankBinIssue(Document):
	""" Some times the master table values not saved in child doc, so here update is running """
	def validate(self):
		child_dict = {"job_card":self.job_card,"production_item":self.production_item,"qty_to_manufacture":self.qty_to_manufacture,"press":self.press,
						"mould":self.mould,"bin_weight":self.bin_weight,"compound":self.compound,"spp_batch_number":self.spp_batch_number,
						"qty":self.qty,"asset_name":self.asset_name,"bin":self.bin}
		if self.items:
			for it in self.items:
				child_dict['is_completed'] = 1 if it.is_completed else 0
		self.items = []
		self.append("items",child_dict)
		if not self.scan_production_lot:
			frappe.throw("Please scan job card <b>Lot number</b> before save..!")
		if not self.scan_bin:
			frappe.throw("Please scan <b>Bin</b> before save..!")

	def on_submit(self):
		if not self.items:
			frappe.throw("Please add some items before submit.")
	
@frappe.whitelist()
def validate_blank_issue_barcode(barcode,scan_type,docname,production_item = None):
	try:
		if scan_type == "scan_production_lot":
			job_card = frappe.db.get_value("Job Card",{"batch_code":barcode,"operation":"Moulding"},["name","production_item","for_quantity","workstation","mould_reference","status"],as_dict=1)
			if job_card:
				if job_card.status != "Work In Progress":
					frappe.response.status = 'failed'
					frappe.response.message = f"Scanned job card <b>"+barcode+f"</b> operations are {job_card.status}..!"
				else:
					""" For checking exe bin issue """
					# blank_bin_issue = frappe.db.sql("""SELECT I.name FROM `tabBlank Bin Issue Item` I  
					# 				  INNER JOIN `tabBlank Bin Issue` B ON B.name=I.parent
					# 				  WHERE I.is_completed=0 AND I.job_card=%(job_card)s AND B.name<>%(docname)s""",{"job_card":job_card.get('name'),"docname":docname},as_dict=1)
					# if blank_bin_issue:
					# 	frappe.response.status = 'failed'
					# 	frappe.response.message = "Scanned job card <b>"+barcode+"</b> is already issued."
					# else:
					# 	job_card['mould_reference'] = frappe.db.get_value("Asset",{"name":job_card.get('mould_reference')},"item_code")
					# 	frappe.response.status = 'success'
					# 	frappe.response.message = job_card

					job_card['mould_reference'] = frappe.db.get_value("Asset",{"name":job_card.get('mould_reference')},"item_code")
					frappe.response.status = 'success'
					frappe.response.message = job_card
					""" End """
			else:
				frappe.response.status = 'failed'
				frappe.response.message = "Scanned job card <b>"+barcode+"</b> not exist."
			
		elif scan_type == "scan_bin":
			# bl_bin = frappe.db.sql(""" SELECT IBM.compound,IBM.spp_batch_number,IBM.qty,BB.name,BB.bin_weight,IBM.is_retired FROM `tabBlanking Bin` BB INNER JOIN `tabItem Bin Mapping` IBM ON BB.name=IBM.blanking_bin 
			# 						WHERE barcode_text=%(barcode_text)s ORDER BY IBM.creation desc""",{"barcode_text":barcode},as_dict=1)
			bl_bin = frappe.db.sql(""" SELECT IBM.compound,IBM.spp_batch_number,IBM.qty,A.name,A.bin_weight,IBM.is_retired,A.asset_name 
			  						FROM `tabAsset` A 
			  							INNER JOIN `tabItem Bin Mapping` IBM ON A.name=IBM.blanking__bin 
									WHERE A.barcode_text=%(barcode_text)s ORDER BY IBM.creation desc""",{"barcode_text":barcode},as_dict=1)
			if bl_bin:
				if bl_bin[0].is_retired == 1:
					frappe.response.status = 'failed'
					frappe.response.message = "No item found in Scanned Bin."
				if not bl_bin[0].bin_weight:
					frappe.response.status = 'failed'
					frappe.response.message = "Bin weight not set in Asset..!"
				spp_settings = frappe.get_single("SPP Settings")
				if not spp_settings.to_location:
					frappe.response.status = 'failed'
					frappe.response.message = "Asset Default To Location not found in SPP Settings."
				location = frappe.db.sql("""SELECT name FROM `tabAsset` WHERE barcode_text=%(barcode_text)s  AND location=%(location)s""",{"location":spp_settings.to_location,"barcode_text":barcode},as_dict=1)
				if not location:
					frappe.response.status = 'failed'
					frappe.response.message = "Scanned Bin <b>"+barcode+"</b> not exist in the location <b>"+spp_settings.to_location+"</b>."
				else:
					if bl_bin[0].asset_name != production_item:
						frappe.response.status = 'failed'
						frappe.response.message = f"Bin item {bl_bin[0].asset_name} doesn’t match job card item {production_item}."
						return
					c_resp = validate_compound(production_item,bl_bin[0])
					if c_resp:
						frappe.response.status = 'success'
						frappe.response.message= bl_bin[0]
			else:
				frappe.response.status = 'failed'
				frappe.response.message = "Scanned Bin <b>"+barcode+"</b> not exist."
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_issue.blank_bin_issue.validate_blank_issue_barcode")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."

def validate_compound(production_item,bl_bin):
	try:
		query = f""" SELECT BI.item_code FROM `tabBOM` B 
					INNER JOIN 	`tabBOM Item` BI ON BI.parent = B.name
					INNER JOIN `tabItem` I ON I.name = BI.item_code 
					WHERE I.item_group = 'Compound' AND B.is_active = 1 AND B.item = '{production_item}' """
		resp_ = frappe.db.sql(query, as_dict = 1)
		if resp_:
			for c_ in resp_:
				if c_.item_code == bl_bin.compound:
					return True
			else:
				frappe.response.status = "failed"
				frappe.response.message = f"The <b>Bin compound-{bl_bin.compound}</b> is not matched with any of <b>BOM</b> compound..!</b>"
				return False
		else:
			frappe.response.status = "failed"
			frappe.response.message = f"<b>BOM</b> compound details not found..!"
			return False
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_issue.blank_bin_issue.validate_compound")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."







# def on_cancel(self):
	# 	if self.items:
	# 		for item in self.items:
	# 			if item.is_completed:
	# 				frappe.db.set_value(item.doctype,item.name,"is_completed",0)	
	# 		frappe.db.commit()