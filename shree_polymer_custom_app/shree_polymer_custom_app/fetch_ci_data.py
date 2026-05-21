import frappe, json, datetime

def json_serial(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return str(obj)
    if isinstance(obj, datetime.timedelta):
        return str(obj)
    return str(obj)

# Stock Entry header
se = frappe.db.get_value("Stock Entry", "CE-2026-01886",
    ["name","docstatus","posting_date","posting_time","stock_entry_type","work_order","company"],
    as_dict=True)
print("=== STOCK ENTRY CE-2026-01886 ===")
print(json.dumps(se, indent=2, default=json_serial))

# SE Items
se_items = frappe.db.get_all("Stock Entry Detail",
    filters={"parent": "CE-2026-01886"},
    fields=["name","item_code","qty","batch_no","mix_barcode","spp_batch_number",
            "s_warehouse","t_warehouse","is_finished_item","source_ref_document","source_ref_id"],
    order_by="idx asc")
print("\n=== SE ITEMS ===")
print(json.dumps(se_items, indent=2, default=json_serial))

# DCR
dcr = frappe.db.get_value("Delivery Challan Receipt", "MTDCR-2026-04-08-00002",
    ["name","docstatus","dc_receipt_date","mixing_time"], as_dict=True)
print("\n=== DCR MTDCR-2026-04-08-00002 ===")
print(json.dumps(dcr, indent=2, default=json_serial))

# QI linked to SE
qis = frappe.db.get_all("Quality Inspection",
    filters={"reference_name": "CE-2026-01886"},
    fields=["name","docstatus","status","item_code","batch_no","inspected_by"])
print("\n=== QUALITY INSPECTIONS for CE-2026-01886 ===")
print(json.dumps(qis, indent=2, default=json_serial))

# Bridge logs for COMPOUND_INSPECTION — most recent 5
logs = frappe.db.get_all("Legacy Bridge Log",
    filters={"process_type": "COMPOUND_INSPECTION"},
    fields=["name","reference_id","status","result_message","creation","traceback"],
    order_by="creation desc", limit=5)
print("\n=== RECENT CI BRIDGE LOGS ===")
print(json.dumps(logs, indent=2, default=json_serial))
