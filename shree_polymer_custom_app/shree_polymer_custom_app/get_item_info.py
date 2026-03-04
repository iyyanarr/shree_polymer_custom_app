import frappe
import json

def get_item_info():
    frappe.connect()
    item_code = "C_6122"
    item = frappe.get_all("Item", 
                         filters={"name": item_code},
                         fields=["name", "item_name", "item_group", "has_batch_no"])
    print(json.dumps(item, indent=2))

if __name__ == "__main__":
    get_item_info()
