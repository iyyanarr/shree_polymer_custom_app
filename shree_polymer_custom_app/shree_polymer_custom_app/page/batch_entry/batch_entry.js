frappe.pages['batch-entry'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Batch ERP Entry',
		single_column: true
	});
	frappe.breadcrumbs.add("Setup");
}