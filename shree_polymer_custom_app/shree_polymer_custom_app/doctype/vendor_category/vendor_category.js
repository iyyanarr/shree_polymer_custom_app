// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vendor Category', {
	refresh: function(frm) {
		frm.trigger('set_warehouse_filter')
	},
	set_warehouse_filter(frm){
		frappe.call({
			method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.vendor_category.vendor_category.get_filter_subcontractor',
			args: {},
			freeze: true,
			callback: function (r) {
				if(r.status=="failed"){
					frappe.msgprint(r.message)
				}
				else{
					frm.set_query("vendor","vendors",()=>{
						return {
							"filters":{
								"name":["in",JSON.parse(r.message)]
							}
						};
					})
				}
			}
		});
	},
});
