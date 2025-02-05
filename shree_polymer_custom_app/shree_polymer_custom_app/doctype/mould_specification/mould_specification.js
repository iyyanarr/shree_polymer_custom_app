// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mould Specification', {
	refresh: function(frm) {
		frm.events.set_filters(frm)
	},
	set_filters(frm){
		frappe.call({
			method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.mould_specification.mould_specification.get_work_mould_filters',
			args: {
			},
			freeze: true,
			callback: function (r) {
				if (r && r.status == "success") {
					frm.set_query("spp_ref", function () {
						return {
							"filters": {
								"item_group": r.message.item_group
							}
						};
					});
					frm.set_query("mould_ref", function () {
						return {
							"filters": {
								"item_group": r.message.mould_item_group
							}
						};
					});
					frm.set_query("compound_code", function () {
						return {
							"filters": {
								"item_group": "Compound"
							}
						};
					});

				}
			}
		});
	}
});
