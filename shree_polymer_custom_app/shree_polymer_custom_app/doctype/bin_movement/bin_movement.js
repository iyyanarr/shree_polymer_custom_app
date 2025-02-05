// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bin Movement', {
	refresh: (frm) => {
		frm.set_df_property("qty", "hidden", 1)
		if (frm.doc.docstatus == 1) {
			frm.set_df_property("scan_section", "hidden", 1)
		}
		if(frm.doc.docstatus == 0){
			frm.trigger('add')
		}
	},
	enable_disable_btn:frm =>{
		if (frm.doc.scan_bin) {
			$(frm.get_field('add').wrapper).find('.add-row').removeAttr("disabled")
		}
		else{
			$(frm.get_field('add').wrapper).find('.add-row').attr("disabled","disabled")
		}
	},
	"scan_bin": (frm) => {
		if (frm.doc.scan_bin && frm.doc.scan_bin != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.bin_movement.bin_movement.validate_bin',
				args: {
					bin_code: frm.doc.scan_bin
				},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_bin", "");
						frm.set_df_property("qty", "hidden", 1)
					}
					else if (r && r.status == "success") {
						frm.set_value("asset_movement",1)
						frm.set_value("bin_released",1)
						if (frm.doc.movement_items && frm.doc.movement_items.length>0) {
							let flag = false
							frm.doc.movement_items.map(res =>{
								if (res.bin_barcode == frm.doc.scan_bin){
									flag = true
									frappe.msgprint(`Scanned Bin <b>${frm.doc.scan_bin}</b> already added.`);
									frm.set_value("scan_bin", "");
									return
								}
							})
							if(flag){
								return
							}
						}
						if(r.message.asset_movement.status == "failed" && r.message.item_bin_mapping.status == "failed"){
							frm.set_value("scan_bin", "");
							frm.set_value("asset_movement",0)
							frm.set_value("bin_released",0)
							frappe.msgprint(`The Bin is already released and also moved..!`)
							return	
						}
						else if(r.message.asset_movement.status == "failed"){
							frm.set_value("asset_movement",0)
							frappe.show_alert({
								message:__(`${r.message.asset_movement.message}`),
								indicator:'Red'
							}, 5);
							frm.events.set_form_values(frm,r)
						}
						else if(r.message.item_bin_mapping.status == "failed"){
							frm.set_value("bin_released",0)
							frappe.show_alert({
								message:__(`${r.message.item_bin_mapping.message}`),
								indicator:'Red'
							}, 5);
							frm.events.set_form_values(frm,r)
						}
						else{
							frm.events.set_form_values(frm,r)
						}
					}
					else {
						frm.set_df_property("qty", "hidden", 1)
						frappe.msgprint("Something went wrong..!");
					}
				}
			});
		}
		else{
			frm.events.enable_disable_btn(frm)
		}
	},
	set_form_values(frm,r){
		frm.set_value("compound", r.message.item_bin_mapping.compound)
		frm.set_value("bin_id", r.message.item_bin_mapping.bin_id ? r.message.item_bin_mapping.bin_id : r.message.asset_movement.bin_id)
		frm.set_value("current_location",r.message.asset_movement.current_location)
		frm.set_value("bin_name",r.message.item_bin_mapping.bin_name ? r.message.item_bin_mapping.bin_name : r.message.asset_movement.bin_name)
		frm.set_value("qty",r.message.item_bin_mapping.qty)
		frm.set_value("spp_batch_number",r.message.item_bin_mapping.spp_batch_number)
		frm.set_value("job_card",r.message.item_bin_mapping.job_card)
		frm.set_value("ibm_id",r.message.item_bin_mapping.ibm_id)
		frm.set_df_property("qty", "hidden", 0)
		frm.events.enable_disable_btn(frm)
	},
	"add": function (frm) {
		let wrapper = $(frm.get_field('add').wrapper).empty();
		$(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);
		$(frm.get_field('add').wrapper).find('.add-row').on('click', function () {
			if (!frm.doc.scan_bin || frm.doc.scan_bin == undefined) {
				frappe.msgprint("Please scan bin before add.");
				return
			}
			else {
				var row = frappe.model.add_child(frm.doc, "Bin Movement Item", "movement_items");
				row.bin_barcode = frm.doc.scan_bin;
				row.compound = frm.doc.compound;
				row.bin_id = frm.doc.bin_id;
				row.current_location = frm.doc.current_location;
				row.bin_name = frm.doc.bin_name;
				row.spp_batch_number = frm.doc.spp_batch_number;
				row.qty = frm.doc.qty;
				row.job_card = frm.doc.job_card;
				row.asset_movement = frm.doc.asset_movement;
				row.bin_released = frm.doc.bin_released;
				row.ibm_id = frm.doc.ibm_id;
				frm.set_df_property("qty", "hidden", 1)
				frm.refresh_field('movement_items');
				frm.set_value("scan_bin", "");
				frm.set_value("compound", "")
				frm.set_value("bin_id", "")
				frm.set_value("current_location", "")
				frm.set_value("bin_name", "")
				frm.set_value("qty", "")
				frm.set_value("spp_batch_number", "")
				frm.set_value("job_card", "")
				frm.set_value("asset_movement","")
				frm.set_value("bin_released","")
				frm.set_value("ibm_id","")
				}
			});
		}
});
