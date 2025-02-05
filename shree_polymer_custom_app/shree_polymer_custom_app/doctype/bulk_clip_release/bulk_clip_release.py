# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BulkClipRelease(Document):
	def validate(self):
		if not self.clip_release_item:
			frappe.throw("Please scan some clips before save..!")

	def on_submit(self):
		clips__ = ""
		for each__clip in self.clip_release_item:
			clips__ += f"'{each__clip.item_clip_mapping_id}',"
		clips__ = clips__[:-1]
		frappe.db.sql(f""" UPDATE `tabItem Clip Mapping` SET is_retired = 1 WHERE name IN ({clips__}) """)
		frappe.db.commit()

@frappe.whitelist()
def validate_clip(clip):
	try:
		exe_clip = frappe.db.get_value("Sheeting Clip",{'barcode_text':clip})
		if exe_clip:
			clip_info = frappe.db.sql(""" SELECT ICM.name,ICM.is_retired,ICM.compound,ICM.sheeting_clip,ICM.spp_batch_number,ICM.qty FROM
										  `tabItem Clip Mapping` ICM INNER JOIN `tabSheeting Clip` SC ON ICM.sheeting_clip = SC.name
										   WHERE SC.barcode_text = '{clip}' AND ICM.is_retired = 0 ORDER BY ICM.creation DESC """.format(clip=clip),as_dict = 1)
			if clip_info:
				frappe.response.status = 'success'
				frappe.response.message = clip_info[0]								
			else:
				frappe.response.status = 'failed'
				frappe.response.message = f"Scanned clip <b>{clip}</b> is already released..!"			
		else:
			frappe.response.status = 'failed'
			frappe.response.message = "Invalid <b>Clip</b> barcode..!"	
	except Exception:
		frappe.log_error(message = frappe.get_traceback(),title = "shree_polymer_custom_app.shree_polymer_custom_app.doctype.bulk_clip_release.bulk_clip_release.validate_clip")
		frappe.response.status = 'failed'
		frappe.response.message = "Something went wrong,not able to fetch info..!" 