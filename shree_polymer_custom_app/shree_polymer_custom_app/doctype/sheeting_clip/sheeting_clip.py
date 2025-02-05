# Copyright (c) 2022, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from shree_polymer_custom_app.shree_polymer_custom_app.api import remove_spl_characters

class SheetingClip(Document):
	def on_update(self):
		if not self.barcode:
			generate_barcode(self)

def generate_barcode(self):
	import code128
	import io
	from PIL import Image, ImageDraw, ImageFont
	barcode_param = barcode_text = self.name
	# barcode_param,barcode_text = None,None
	# while True:
	# 	barcode_param = barcode_text = str(randomStringDigits(8))
	# 	if frappe.db.get_all(self.doctype,filters={"barcode_text":barcode_text}):
	# 		continue
	# 	if frappe.db.get_all("Warehouse",filters={"barcode_text":barcode_text}):
	# 		continue
	# 	else:
	# 		break
	barcode_image = code128.image(barcode_param, height=120)
	w, h = barcode_image.size
	margin = 5
	new_h = h +(2*margin) 
	new_image = Image.new( 'RGB', (w, new_h), (255, 255, 255))
	# put barcode on new image
	new_image.paste(barcode_image, (0, margin))
	# object to draw text
	draw = ImageDraw.Draw(new_image)
	file_url_name = remove_spl_characters(barcode_param)
	new_image.save(str(frappe.local.site)+'/public/files/{filename}.png'.format(filename=file_url_name), 'PNG')
	self.barcode = "/files/" + file_url_name + ".png"
	self.barcode_text = barcode_text
	self.save()
	
def randomStringDigits(stringLength=6):
	import random
	import string
	lettersAndDigits = string.ascii_uppercase + string.digits
	return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))
