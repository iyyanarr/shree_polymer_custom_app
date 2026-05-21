import frappe, json, datetime

def json_serial(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return str(obj)
    if isinstance(obj, datetime.timedelta):
        return str(obj)
    return str(obj)

def run():
    # Get the full rollback error log entry
    err = frappe.db.get_value("Error Log", "87m83rqn7v",
        ["name", "creation", "method", "error"], as_dict=True)
    print("=== FULL ROLLBACK ERROR (87m83rqn7v) ===")
    print(json.dumps(err, indent=2, default=json_serial))

    # Also check if there are any other CI-related errors in this window
    ci_errors = frappe.db.sql("""
        SELECT name, creation, method, error
        FROM `tabError Log`
        WHERE creation >= '2026-04-08 10:55:00'
          AND creation <= '2026-04-08 11:15:00'
          AND (method LIKE '%compound%' OR method LIKE '%submit_dc%' OR method LIKE '%Bridge%' OR method LIKE '%rollback%')
        ORDER BY creation ASC
    """, as_dict=True)
    print("\n=== ALL CI/BRIDGE RELATED ERRORS IN WINDOW ===")
    print(json.dumps(ci_errors, indent=2, default=json_serial))

    # Check docstatus timeline - was CE-2026-01886 already submitted before bridge tried?
    # Look at the Stock Entry submission time via Version log
    versions = frappe.db.sql("""
        SELECT name, creation, owner, data
        FROM `tabVersion`
        WHERE ref_doctype = 'Stock Entry'
          AND docname = 'CE-2026-01886'
        ORDER BY creation ASC
        LIMIT 5
    """, as_dict=True)
    print("\n=== VERSION HISTORY OF CE-2026-01886 ===")
    print(json.dumps(versions, indent=2, default=json_serial))
