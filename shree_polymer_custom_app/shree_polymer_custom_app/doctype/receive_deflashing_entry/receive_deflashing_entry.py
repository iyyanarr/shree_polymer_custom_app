# Copyright (c) 2025, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class ReceiveDeflashingEntry(Document):
	pass

@frappe.whitelist()
def get_despatch_info(dd_number):
    try:
        despatch_entry = frappe.get_doc("Despatch To U1 Entry", dd_number)
        return despatch_entry
    except frappe.DoesNotExistError:
        frappe.throw(_("Despatch Entry not found for DD Number: {0}").format(dd_number))
    except Exception as e:
        frappe.log_error(message=str(e))
        frappe.throw(_("An error occurred while fetching the Despatch Entry"))