// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Bin Mapping', {
	refresh: function(frm) {
		frm.events.get_filter_bin_category(frm)
	},
	get_filter_bin_category:frm =>{
		  frappe.call({
	                method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.item_bin_mapping.item_bin_mapping.get_bin_category",
	                args: {
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(r.message.status=="Success")
	                	{
						  frm.set_query("blanking__bin", function() {
						  	  return {
						            "filters": {
						                "asset_category": r.message.category
						            }
						        };
						  });
	                	}
				 	}
			 });
		}
});
