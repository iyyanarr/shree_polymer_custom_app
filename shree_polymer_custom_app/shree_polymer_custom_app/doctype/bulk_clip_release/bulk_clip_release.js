// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Clip Release', {
	"clip": function (frm) {
		if(frm.doc.clip) {
			if(frm.doc.clip_release_item && frm.doc.clip_release_item.length > 0){
				let release_flag = false;
				frm.doc.clip_release_item.map(res =>{
					if(res.clip_barcode == frm.doc.clip){
						release_flag = true;
						return
					}
				})
				if(release_flag){
					frappe.msgprint(`Scanned clip <b>${frm.doc.clip}</b> already added..!`);
					frm.set_value("clip", "");
					return
				}
			}
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.bulk_clip_release.bulk_clip_release.validate_clip',
				args: {
					clip: frm.doc.clip
				},
				freeze:true,
				callback: function (res) {
					if (res.status == 'failed') {
						frappe.msgprint(res.message);
						frm.set_value("clip", "");
					}
					else if (res.status == 'success') {
						frm.add_child("clip_release_item", {
							item_clip_mapping_id: res.message.name,
							clip_name: res.message.sheeting_clip,
							compound: res.message.compound,
							clip_barcode: frm.doc.clip,
							spp_batch_number: res.message.spp_batch_number
						});
						frm.refresh_field("clip_release_item");
						frm.set_value("clip", "");
						frm.get_field("clip_release_item").grid.cannot_add_rows = true;
					}
					else {
						frappe.msgprint("Something went wrong while fetching data..!");
					}
				}
			})
		}
	}
});