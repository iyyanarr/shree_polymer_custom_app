# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class BinMovement(Document):
	def validate(self):
		if not self.movement_items:
			frappe.throw('Please add some items before save..!')
	
	def on_submit(self):
		make_bin_release_movement(self)

def make_bin_release_movement(self):
	try:
		spp_settings = frappe.get_single("SPP Settings")
		for bin__ in self.movement_items:
			if bin__.asset_movement:
				make_asset_movement(spp_settings,bin__)
			if  bin__.bin_released:
				frappe.db.set_value("Item Bin Mapping",bin__.ibm_id,"is_retired",1)
				frappe.db.sql(""" UPDATE `tabBlank Bin Issue Item` set is_completed = 1 where bin=%(bin)s and is_completed=0 """,{"bin":bin__.bin_id})
				frappe.db.commit()
	except Exception:
		frappe.log_error(title="make_bin_release_movement failed",message=frappe.get_traceback())
		frappe.get_doc(self.doctype,self.docname).db_set("docstatus", 0)
		frappe.db.commit()
		self.reload()

def make_asset_movement(spp_settings,x):
	asset__mov = frappe.new_doc("Asset Movement")
	asset__mov.company = "SPP"
	asset__mov.transaction_date = now()
	asset__mov.purpose = "Transfer"
	asset__mov.append("assets",{
		"asset":x.bin_id,
		"source_location":spp_settings.to_location,
		"target_location":spp_settings.from_location,
	})
	asset__mov.insert(ignore_permissions=True)
	ass__doc = frappe.get_doc("Asset Movement",asset__mov.name)
	ass__doc.docstatus = 1
	ass__doc.save(ignore_permissions=True)

@frappe.whitelist()
def validate_bin(bin_code):
	try:
		resp__dict = {"item_bin_mapping":{},"asset_movement":{}}
		asset = frappe.db.get_value("Asset",{"barcode_text":bin_code})
		if asset:
			spp_settings = frappe.get_single("SPP Settings")
			if validate_asset_location(spp_settings):
				include_asset_mv(resp__dict,spp_settings,asset)
				compound_resp = frappe.db.sql(f""" SELECT IBM.name ibm_id,IBM.compound,A.name bin_id,A.asset_name bin_name,IBM.is_retired,IBM.spp_batch_number,IBM.qty,IBM.job_card 
												   FROM `tabItem Bin Mapping` IBM INNER JOIN `tabAsset` A ON IBM.blanking__bin = A.name WHERE A.barcode_text = '{bin_code}' AND IBM.is_retired = 0 """,as_dict = 1)
				if compound_resp:
					resp__dict['item_bin_mapping']['status'] = 'success'
					resp__dict['item_bin_mapping'].update(compound_resp[0])
				else:
					resp__dict['item_bin_mapping']['status'] = 'failed'
					resp__dict['item_bin_mapping']['message'] = f"The Bin is already released."	
				frappe.response.status = 'success'
				frappe.response.message = resp__dict
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Invalid <b>Bin</b> barcode..!"
	except Exception:
		frappe.log_error(message=frappe.get_traceback(),title="shree_polymer_custom_app.shree_polymer_custom_app.doctype.bin_movement.bin_movement.validate_bin")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong."

def validate_asset_location(spp_settings):
	if not spp_settings.from_location:
		frappe.response.status == "failed"
		frappe.response.message == "Asset Movement <b>From location</b> not mapped in SPP settings"
		return False
	if not spp_settings.to_location:
		frappe.response.status == "failed"
		frappe.response.message == "Asset Movement <b>From location</b> not mapped in SPP settings"
		return False
	return True
		
def include_asset_mv(resp__dict,spp_settings,asset):
	last_mov = frappe.db.sql(f" SELECT AMI.target_location FROM `tabAsset Movement` AM INNER JOIN `tabAsset Movement Item` AMI ON AM.name = AMI.parent WHERE AMI.asset = '{asset}' ORDER BY AMI.creation DESC LIMIT 1 ",as_dict = 1)
	if last_mov:
		if not last_mov[0].target_location == spp_settings.from_location:
			asset__details = frappe.db.get_value("Asset",asset,["asset_name as bin_name","name as bin_id"],as_dict = 1)
			resp__dict['asset_movement']['status'] = 'success'
			resp__dict['asset_movement']['current_location'] = spp_settings.from_location
			resp__dict['asset_movement'].update(asset__details)
		else:
			resp__dict['asset_movement']['status'] = 'failed'
			resp__dict['asset_movement']['message'] = f'The Bin is Already moved to the location <b>{spp_settings.to_location}</b>'
			resp__dict['asset_movement']['current_location'] = spp_settings.to_location
	else:
		resp__dict['asset_movement']['status'] = 'success'
		resp__dict['asset_movement']['message'] = 'Need to move asset'
		resp__dict['asset_movement']['current_location'] = spp_settings.from_location	