// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deflashing Despatch Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.docstatus == 1 && frm.doc.stock_entry_reference){
			frm.add_custom_button(__("View Stock Transfer"), function(){
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
			frm.remove_custom_button('View Stock Transfer');
		}
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	refresh: (frm) => {
		frm.events.view_stock_entry(frm)
		frm.set_df_property("qty", "hidden", 1)
		if (frm.doc.docstatus == 1) {
			frm.set_df_property("scan_section", "hidden", 1)
		}
		if(frm.doc.scan_deflashing_vendor){
			frm.set_df_property("scan_deflashing_vendor", "hidden", 1)
		}
		if(frm.doc.docstatus == 0){
			frm.trigger('add')
		}
	},
	"scan_lot_number": (frm) => {
		if (frm.doc.scan_lot_number && frm.doc.scan_lot_number != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_lot_barcode',
				args: {
					bar_code: frm.doc.scan_lot_number
				},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_lot_number", "");
						frm.set_value("batch_no", "")
						frm.set_value("spp_batch_no", "")
						frm.set_value("job_card", "")
						frm.set_value("item", "")
						frm.set_value("qty", "")
						frm.set_value("lot_number", "")
						frm.set_value("valuation_rate", "")
						frm.set_value("amount", "")
						frm.set_value("source_warehouse_id","")
						frm.set_df_property("qty", "hidden", 1)
					}
					else if (r && r.status == "success") {
						if (frm.doc.items && frm.doc.items.length>0) {
							let flag = false
							frm.doc.items.map(res =>{
								if (res.lot_number == frm.doc.scan_lot_number){
									flag = true
									frappe.validated = false
									frappe.msgprint(`Scanned lot <b>${frm.doc.scan_lot_number}</b> already added.`);
									frm.set_value("scan_lot_number", "");
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
						frm.set_value("job_card", r.job_card)
						frm.set_value("item", r.item)
						frm.set_value("qty", r.qty)
						frm.set_value("lot_number", frm.doc.scan_lot_number.toUpperCase())
						frm.set_value("source_warehouse_id", r.from_warehouse)
						frm.set_value("valuation_rate", r.valuation_rate)
						frm.set_value("amount", r.amount)
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
	"scan_deflashing_vendor": (frm) => {
		if (frm.doc.scan_deflashing_vendor && frm.doc.scan_deflashing_vendor != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_warehouse',
				args: {
					bar_code: frm.doc.scan_deflashing_vendor
				},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_deflashing_vendor", "");
						frm.set_value("warehouse","")
						frm.set_value("warehouse_id", "")
					}
					else if (r && r.status == "success") {
						frm.set_value("warehouse", r.warehouse_name)
						frm.set_value("warehouse_id", r.name)
						if(frm.doc.scan_deflashing_vendor){
							frm.set_value("scan_deflashing_vendor",frm.doc.scan_deflashing_vendor.toUpperCase())
							frm.set_df_property("scan_deflashing_vendor", "hidden", 1)
						}
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
	enable_disable_btn:frm =>{
		if (frm.doc.scan_lot_number  && frm.doc.scan_deflashing_vendor) {
			$(frm.get_field('add').wrapper).find('.add-row').removeAttr("disabled")
		}
		else{
			$(frm.get_field('add').wrapper).find('.add-row').attr("disabled","disabled")
		}
	},
	"add": function (frm) {
		let wrapper = $(frm.get_field('add').wrapper).empty();
		$(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);
		$(frm.get_field('add').wrapper).find('.add-row').on('click', function () {
			if (!frm.doc.scan_lot_number || frm.doc.scan_lot_number == undefined) {
				frappe.msgprint("Lot no is missing.");
				return
			}
			if (!frm.doc.scan_deflashing_vendor || frm.doc.scan_deflashing_vendor == undefined) {
				frappe.msgprint("Deflashing Vendor code is missing.");
				return
			}
			else {
				var row = frappe.model.add_child(frm.doc, "Deflashing Despatch Entry Item", "items");
				row.lot_number = frm.doc.lot_number;
				row.batch_no = frm.doc.batch_no;
				row.spp_batch_no = frm.doc.spp_batch_no;
				row.warehouse_code = frm.doc.scan_deflashing_vendor;
				row.job_card = frm.doc.job_card;
				row.item = frm.doc.item;
				row.qty = frm.doc.qty;
				row.warehouse = frm.doc.warehouse;
				row.warehouse_id = frm.doc.warehouse_id;
				row.source_warehouse_id = frm.doc.source_warehouse_id;
				row.valuation_rate = frm.doc.valuation_rate;
				row.amount = frm.doc.amount;
				frm.set_df_property("qty", "hidden", 1)
				frm.refresh_field('items');
				frm.set_value("scan_lot_number", "");
				frm.set_value("batch_no", "")
				frm.set_value("spp_batch_no", "")
				frm.set_value("job_card", "")
				frm.set_value("item", "")
				frm.set_value("qty", "")
				frm.set_value("lot_number", "")
				frm.set_value("source_warehouse_id", "")
				frm.set_value("valuation_rate", "")
				frm.set_value("amount", "")
				// frm.set_value("scan_deflashing_vendor", "");
				// frm.set_value("warehouse", "")
				// frm.set_value("warehouse_id", "")
				}
			});
		}
});
