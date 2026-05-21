import frappe
import json

def analyze_warehouses():
    try:
        # 1. Get all warehouses starting with DF
        df_warehouses = frappe.get_all("Warehouse", 
            filters={"name": ["like", "DF%"]}, 
            fields=["name", "warehouse_name", "parent_warehouse"])
        
        # 2. Get recent Deflashing entries to see which warehouses are actually used
        recent_despatch = frappe.get_all("Deflashing Despatch Entry", 
            fields=["name", "source_warehouse_id", "warehouse_id", "scan_deflashing_vendor"],
            limit=20, order_by="creation desc")
            
        recent_receipt = frappe.get_all("Deflashing Receipt Entry", 
            fields=["name", "from_warehouse_id", "warehouse_id", "scan_deflashing_vendor"],
            limit=20, order_by="creation desc")
            
        # 3. Analyze patterns
        patterns = {}
        for w in df_warehouses:
            name = w.name
            if ":" in name:
                prefix = name.split(":")[0].strip()
                patterns[prefix] = name
        
        result = json.dumps({
            "df_warehouses": df_warehouses,
            "patterns_found": patterns,
            "recent_despatch": recent_despatch,
            "recent_receipt": recent_receipt
        }, default=str, indent=2)
        print(result)
        return result
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"
