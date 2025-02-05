// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Despatched Material Return Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	refresh: function(frm) {
		frm.events.set_warehouse_filter(frm)
		frm.events.view_stock_entry(frm)
		frm.events.set_read_only_warehouse(frm)
		if (frm.doc.docstatus == 1) {
			frm.set_df_property("scan_section", "hidden", 1)
		}
		if(frm.doc.docstatus == 0){
			frm.trigger('add')
		}
		frm.set_df_property("qty", "hidden", 1)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.docstatus == 1 && frm.doc.stock_entry_reference){
			frm.add_custom_button(__("View Material Transfer"), function(){
				let dc_ids = frm.doc.stock_entry_reference.split(',')
				if(dc_ids.length > 1){
					frappe.route_options = {
						"name": ["in",dc_ids]
					};
					frappe.set_route("List", "Stock Entry");
				}
				else{
					frappe.set_route("Form", "Stock Entry", dc_ids[0]);
				}
			  });
		}
		else{
			frm.remove_custom_button('View Material Transfer');
		}
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	// target_warehouse(frm){
	// 	frm.events.set_read_only_warehouse(frm)
	// },
	set_read_only_warehouse(frm){
		frm.set_df_property("target_warehouse", "read_only", 1)
		// if(frm.doc.target_warehouse && frm.doc.items && frm.doc.items.length > 0){
		// 	frm.set_df_property("target_warehouse", "read_only", 1)
		// }
		// else{
		// 	frm.set_df_property("target_warehouse", "read_only", 0)
		// }
		frm.events.enable_disable_btn(frm)
	},
	set_warehouse_filter(frm){
		frm.set_query("target_warehouse",() =>{
			return {
				filters:{
					"is_group":["!=",1],
					"disabled":["!=",1]
				}
			}
		})
	},
	enable_disable_btn:frm =>{
		if (frm.doc.scan_lotmixbarcode  && frm.doc.target_warehouse) {
			$(frm.get_field('add').wrapper).find('.add-row').removeAttr("disabled")
		}
		else{
			$(frm.get_field('add').wrapper).find('.add-row').attr("disabled","disabled")
		}
	},
	"scan_lotmixbarcode": (frm) => {
		if (frm.doc.scan_lotmixbarcode && frm.doc.scan_lotmixbarcode != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatched_material_return_entry.despatched_material_return_entry.validate_lot_mix_barcode',
				args: {
					bar_code: frm.doc.scan_lotmixbarcode
				},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_lotmixbarcode", "");
						frm.set_value("batch_no", "")
						frm.set_value("spp_batch_no", "")
						frm.set_value("item", "")
						frm.set_value("qty", "")
						frm.set_value("uom", "")
						frm.set_value("source_warehouse_id","")
						frm.set_value("target_warehouse","")
						frm.set_df_property("qty", "hidden", 1)
					}
					else if (r && r.status == "success") {
						if (frm.doc.items && frm.doc.items.length>0) {
							let flag = false
							frm.doc.items.map(res =>{
								if (res.lot_number == frm.doc.scan_lotmixbarcode){
									flag = true
									frappe.validated = false
									frappe.msgprint(`Scanned lot <b>${frm.doc.scan_lotmixbarcode}</b> is already added.`);
									frm.set_value("scan_lotmixbarcode", "");
									return
								}
							})
							if(flag){
								return
							}
						}
						frm.set_df_property("qty", "hidden", 0)
						frm.set_value("batch_no", r.batch_no)
						frm.set_value("spp_batch_no", r.spp_batch_number)
						frm.set_value("item", r.item)
						frm.set_value("qty", r.qty)
						frm.set_value("source_warehouse_id", r.from_warehouse)
						frm.set_value("target_warehouse", r.to_warehouse)
						frm.set_value("uom", r.uom)
						frm.events.enable_disable_btn(frm)
					}
					else {
						frappe.msgprint("Something went wrong.");
					}
				}
			});
		}
		else{
			frm.events.enable_disable_btn(frm)
		}
	},
	"add": function (frm) {
		let wrapper = $(frm.get_field('add').wrapper).empty();
		$(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);
		$(frm.get_field('add').wrapper).find('.add-row').on('click', function () {
			if (!frm.doc.scan_lotmixbarcode || frm.doc.scan_lotmixbarcode == undefined) {
				frappe.msgprint("Lot no is missing.");
				return
			}
			if (!frm.doc.target_warehouse || frm.doc.target_warehouse == undefined) {
				frappe.msgprint("Please Choose target warehouse before add.");
				return
			}
			else {
				var row = frappe.model.add_child(frm.doc, "Despatched Material Return Entry Item", "items");
				row.lot_number = frm.doc.scan_lotmixbarcode;
				row.batch_no = frm.doc.batch_no;
				row.spp_batch_no = frm.doc.spp_batch_no;
				row.source_warehouse_id = frm.doc.source_warehouse_id;	
				row.target_warehouse_id = frm.doc.target_warehouse;	
				row.item = frm.doc.item;
				row.qty = frm.doc.qty;
				row.target_warehouse_id = frm.doc.target_warehouse;
				row.uom = frm.doc.uom;
				frm.refresh_field('items');
				frm.set_df_property("qty", "hidden", 1)
				frm.set_value("scan_lotmixbarcode", "");
				frm.set_value("batch_no", "")
				frm.set_value("spp_batch_no", "")
				frm.set_value("item", "")
				frm.set_value("qty", "")
				frm.set_value("source_warehouse_id", "")
				frm.set_value("target_warehouse", "")
				frm.set_value("uom", "")
				// frm.events.set_read_only_warehouse(frm)
				}
			});
		}
});
