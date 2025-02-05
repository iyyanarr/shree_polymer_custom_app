// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('SPP Settings', {
	refresh: function(frm) {
		if(!frm.naming_series_options || (frm.naming_series_options && frm.naming_series_options.length==0)){
			frm.events.get_naming_series(frm)
		}
		else{
			frm.events.set_naming_series(frm)
		}
		frm.set_query("deflashing_vendor",()=>{
			return {
				filters:{
					"disabled":0,
					"is_group":1
				}
			}
		})
		frm.set_query('warehouse', 'mixing_operations', () => {
			return {
				"filters": {
					"customer":  ["is", "set"]
				}
			};
		});
		frm.trigger('set_subcontractor_filter')
	},
	set_subcontractor_filter(frm){
		frappe.call({
			method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_settings.spp_settings.get_filter_subcontractor',
			args: {},
			freeze: true,
			callback: function (r) {
				if(r.status=="failed"){
					frappe.msgprint(r.message)
				}
				else{
					frm.set_query("subcontractor","subcontractor_tat_mapping",()=>{
						return {
							"filters": [
								["Warehouse", "name", "in", JSON.parse(r.message)]
							]
						};
					})
				}
			}
		});
	},
	set_naming_series:(frm) =>{
		cur_frm.fields_dict['spp_naming_series'].grid.update_docfield_property("spp_naming_series","options",frm.naming_series_options);
		frm.refresh_field('spp_naming_series');
	},
	get_naming_series:frm =>{
		frappe.call({
			method:"shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_settings.spp_settings.get_naming_series_options",
			args:{},
			async:true,
			type: "GET",
			freeze:true,
			callback:res =>{
				if(res && res.status == "success"){
					frm.naming_series_options = res.message
					frm.events.set_naming_series(frm)
				}
				else {
					frappe.msgeprint("Something Went Wrong..! Can't get naming series for <b>Stock Entry</b>")
				}
			}
		})
	}
});
