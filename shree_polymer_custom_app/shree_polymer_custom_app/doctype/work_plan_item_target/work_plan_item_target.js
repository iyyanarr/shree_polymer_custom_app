// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Plan Item Target', {
	refresh: function(frm) {
		frm.events.set_shift_type(frm)
	},
	set_shift_type(frm){
		frappe.call({
			method:"shree_polymer_custom_app.shree_polymer_custom_app.doctype.work_plan_item_target.work_plan_item_target.get_shift_timings",
			args:{},
			freeze:true,
			callback:(res)=>{
				if(res){
					if(res.status == "success"){
						set_field_options("shift_type",res.data)
					}
					else{
						frappe.msgprint(res.message)
					}
				}
				else{
					frappe.msgprint("Api response failed..!")
				}
			}
		})

	}
});
