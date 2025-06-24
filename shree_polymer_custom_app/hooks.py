from . import __version__ as app_version

app_name = "shree_polymer_custom_app"
app_title = "Shree Polymer Custom App"
app_publisher = "Tridotstech"
app_description = "Shree Polymer Custom App"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@tridotstech.com"
app_license = "MIT"

# Includes in <head>
# ------------------
 
# include js, css files in header of desk.html
# app_include_css = "/assets/shree_polymer_custom_app/css/shree_polymer_custom_app.css"
# app_include_js = "/assets/shree_polymer_custom_app/js/shree_polymer_custom_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/shree_polymer_custom_app/css/shree_polymer_custom_app.css"
# web_include_js = "/assets/shree_polymer_custom_app/js/shree_polymer_custom_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "shree_polymer_custom_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Stock Entry" : "public/js/st_entry.js",
              "Delivery Note" : "public/js/st_entry.js"}
# app_include_js = ["/assets/spplive/js/st_entry.js"]

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "shree_polymer_custom_app.install.before_install"
after_install = "shree_polymer_custom_app.custom_role_permissions.restore_all_custom_permissions"
after_migrate = "shree_polymer_custom_app.custom_role_permissions.restore_all_custom_permissions"

# Uninstallation
# ------------

# before_uninstall = "shree_polymer_custom_app.uninstall.before_uninstall"
# after_uninstall = "shree_polymer_custom_app.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "shree_polymer_custom_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
 
# permission_query_conditions = {
# 	"Batch ERP Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_berp",
#     "Stock Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_se",
#     "Material Transfer": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_mt",
# 	"Delivery Challan Receipt": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_dcr",
# 	"Delivery Note": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_dn",
#     "Work Order": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_wo",
#     "Job Card": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_jc",
#     "Cut Bit Transfer": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_cbt",
#     "Bulk Clip Release": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_bcr",
#     "Blanking DC Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_bdce",
#     "Bin Movement": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_mv",
#     "Asset Movement": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_amv",
#     "Work Planning": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_wrkp",
#     "Add On Work Planning": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_awrkp",
#     "Blank Bin Issue": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_bbissue",
#     "Moulding Production Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_moupe",
#     "Sub Lot Creation": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_sublc",
#     "Deflashing Despatch Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_dede",
#     "Deflashing Receipt Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_drepe",
#     "Despatch To U1 Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_deu1e",
#     "Lot Resource Tagging": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_loet",
#     "Blank Bin Rejection Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_bbnre",
#     "Inspection Entry": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_inspe",
# 	"Billing": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_bilg",
#     "Packing": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_pack",
#     "Quality Inspection": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_qcins",
#     "Compound Inspection": "shree_polymer_custom_app.shree_polymer_custom_app.permission_query.get_filter_cmins",
# 	}

# Document Events
# ---------------
# Hook on document methods and events
fixtures = [
	{
		"doctype": "Stock Entry",
		"filters": [
			["name", "in", [
        	"Stock Entry-sheeting_clip"
			]]
		]
	},
	{
		"doctype": "Quality Inspection",
		"filters": [
			["name", "in", [
        	"Quality Inspection-spp_batch_number",
        	"Quality Inspection-quality_document"
			]]
		]
	},
	{
		"doctype": "Warehouse",
		"filters": [
			["name", "in", [
        	"Warehouse-barcode_section",
        	"Warehouse-barcode",
        	"Warehouse-barcode_text",
        	"Warehouse-customer",
			]]
		]
	},
	{
		"doctype": "Job Card",
		"filters": [
			["name", "in", [
        	"Job Card-moulding","Job Card-press_no","Job Card-operator_code","Job Card-operator_code","Job Card-column_break_72",
			"Job Card-comments","Job Card-batch_code","Job Card-barcode_image_url","Job Card-barcode_text","Job Card-moulding_lot_number",
            "Job Card-total_qty_after_inspection","Job Card-shift_type","Job Card-shift_time"
			]]
		]
	},
	{
		"doctype": "Stock Entry Detail",
		"filters": [
			["name", "in", [
        	"Stock Entry Detail-deflash_receipt_reference",
            "Stock Entry Detail-inspection_ref",
            "Stock Entry Detail-source_ref_document",
            "Stock Entry Detail-source_ref_id",
            "Stock Entry Detail-reference"
			]]
		]
	},
	{
		"doctype": "Delivery Note",
		"filters": [
			["name", "in", [
        	"Delivery Note-operation",
        	"Delivery Note-received_status",
            "Delivery Note-special_instructions",
            "Delivery Note-special_instruction",
            "Delivery Note-reference_document",
            "Delivery Note-reference_name"
			]]
		]
	},
	{
		"doctype": "Delivery Note Item",
		"filters": [
			["name", "in", [
        	"Delivery Note Item-scan_barcode",
        	"Delivery Note Item-spp_batch_no",
        	"Delivery Note Item-is_received",
        	"Delivery Note Item-dc_receipt_no",
        	"Delivery Note Item-dc_receipt_date",
			"Delivery Note Item-dc_return_receipt_no",
			"Delivery Note Item-dc_return_date",
			"Delivery Note Item-is_return"
			]]
		]
	},
    {
		"doctype": "Asset",
		"filters": [
			["name", "in", [
        	"Asset-barcode_text","Asset-barcode","Asset-bin_weight"]]
		]
	},
    {
		"doctype": "Batch ERP Entry",
		"filters": [
			["name", "in", [
        	"Batch ERP Entry-stock_entry_reference"]]
		]
	},
    {
		"doctype": "BOM",
		"filters": [
			["name", "in", [
        	"BOM-raw_materials"]]
		]
	},
     {
		"doctype": "Sales Invoice",
		"filters": [
			["name", "in", [
        	"Sales Invoice-asn_number","Sales Invoice-vehicle_number"]]
		]
	},
     {
		"doctype": "Shift Type",
		"filters": [
			["name", "in", [
        	"Shift Type-total_time","Shift Type-job_card_naming_series"]]
		]
	},
     {
		"doctype": "Item",
		"filters": [
			["name", "in", [
        	"Item-fresh_time"]]
		]
	}
]

doc_events = {
    "*":{
      "validate":"shree_polymer_custom_app.shree_polymer_custom_app.api.verify_enqueue_and_alert",  
	},
	"Stock Entry": {
	"on_submit": "shree_polymer_custom_app.shree_polymer_custom_app.api.update_consumed_items",
    "on_update": "shree_polymer_custom_app.shree_polymer_custom_app.api.attach_mix_barcode",
    "on_update_after_submit": "shree_polymer_custom_app.shree_polymer_custom_app.api.generate_se_mixbarcode"
	},
	"Stock Ledger Entry":{
		"on_submit": "shree_polymer_custom_app.shree_polymer_custom_app.api.on_sle_update",
		"on_cancel": "shree_polymer_custom_app.shree_polymer_custom_app.api.on_sle_update",
		"on_trash": "shree_polymer_custom_app.shree_polymer_custom_app.api.on_sle_update",
	},
	"Item":{
		"on_update": "shree_polymer_custom_app.shree_polymer_custom_app.api.on_item_update"
	},
	"Batch":{
		"on_update": "shree_polymer_custom_app.shree_polymer_custom_app.api.on_batch_update",
     "on_trash":"shree_polymer_custom_app.shree_polymer_custom_app.api.on_batch_trash",
	},
	"Warehouse":{
		"on_update": "shree_polymer_custom_app.shree_polymer_custom_app.api.update_wh_barcode"

	},
	"Employee":{
		"on_update": "shree_polymer_custom_app.shree_polymer_custom_app.api.update_emp_barcode"

	},
	"Asset":{
		"on_update":"shree_polymer_custom_app.shree_polymer_custom_app.api.update_asset_barcode",
        "on_update_after_submit":"shree_polymer_custom_app.shree_polymer_custom_app.api.update_asset_barcode"
	},
    "BOM":{
		"on_update":"shree_polymer_custom_app.shree_polymer_custom_app.api.update_raw_materials",
	},
    # "Job Card":{
	# 	"on_submit":"shree_polymer_custom_app.shree_polymer_custom_app.api.generate_lot_number"
	# },
	# "Asset Movement":{
    #      "autoname":"shree_polymer_custom_app.shree_polymer_custom_app.api.validate_and_update_am_naming",
	# },
	"Shift Type":{
        "validate":"shree_polymer_custom_app.shree_polymer_custom_app.api.update_total_work_hrs",
	}
} 

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"shree_polymer_custom_app.tasks.all"
# 	],
# 	"daily": [
# 		"shree_polymer_custom_app.tasks.daily"
# 	],
# 	"hourly": [
# 		"shree_polymer_custom_app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"shree_polymer_custom_app.tasks.weekly"
# 	]
# 	"monthly": [
# 		"shree_polymer_custom_app.tasks.monthly"
# 	]
# 	
	# "daily": [
	# 	"shree_polymer_custom_app.shree_polymer_custom_app.api.update_stock_balance",
	# ]
}

# Testing
# -------

# before_tests = "shree_polymer_custom_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "shree_polymer_custom_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "shree_polymer_custom_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"shree_polymer_custom_app.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []
