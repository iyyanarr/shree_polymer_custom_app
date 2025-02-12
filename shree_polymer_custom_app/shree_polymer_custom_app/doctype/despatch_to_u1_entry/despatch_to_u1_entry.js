// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Despatch To U1 Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.docstatus == 1 && frm.doc.stock_entry_reference){
			frm.add_custom_button(__("View Stock Entry"), function(){
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			  });
		}
		else{
			frm.remove_custom_button('Stock Entry');
		}
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	refresh: function(frm) {
		frm.events.view_stock_entry(frm)
		frm.set_df_property("weight_kgs","hidden",1)
		frm.set_df_property("qty_nos","hidden",1)
		if (frm.doc.docstatus == 1) {
			frm.set_df_property("scan_lot", "hidden", 1)
		}
		if(frm.doc.docstatus == 0){
			frm.trigger('add_html')
		}
	},
	"scan_lot_number": (frm) => {
		if (frm.doc.scan_lot_number && frm.doc.scan_lot_number != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.despatch_to_u1_entry.despatch_to_u1_entry.validate_lot_number',
				args: {
					lot_no: frm.doc.scan_lot_number,
					docname: frm.doc.name
				},
				freeze: true,
				callback: function (r) {
					if (r.status == "failed" || r.status == "Failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_lot_number", "");
					}
					else if (r.status == "success" || r.status == "Success") {
						if (frm.doc.vendor && frm.doc.vendor != r.message.warehouse){
							frappe.validated = false
							frappe.throw(`The scanned Vendor - <b>${r.message.warehouse}</b> and existsing vendor - <b>${frm.doc.vendor}</b> can't be different.`)
							return 
						}
						if (frm.doc.items && frm.doc.items.length>0) {
							let flag = false
							frm.doc.items.map(res =>{
								if (res.lot_no == frm.doc.scan_lot_number){
									frm.set_value("scan_lot_number", "");
									flag = true
									frappe.validated = false
									frappe.msgprint(`Scanned Lot <b>${frm.doc.scan_lot_number}</b> already added.`);
									return
								}
							})
							if(flag){
								return
							}
						}
						frm.set_df_property("weight_kgs","hidden",0)
						frm.set_df_property("qty_nos","hidden",0)
						frm.set_value("lot_no",frm.doc.scan_lot_number.toUpperCase())	
						frm.set_value("date",r.message.creation)	
						frm.set_value("product_ref",r.message.item)	
						frm.set_value("qty_nos",r.message.qty_nos)	
						frm.set_value("vendor",r.message.warehouse)	
						frm.set_value("weight_kgs",r.message.product_weight)
						frm.set_value("spp_batch_no",r.message.spp_batch_no)	
						frm.set_value("batch_no",r.message.batch_no)	
						frm.set_value("qty_uom",r.message.qty_uom)	
						frm.set_value("valuation_rate", r.message.valuation_rate)
						frm.set_value("amount", r.message.amount)
						$(frm.get_field('add_html').wrapper).find('button.btn.btn-xs.btn-default.add-row').removeAttr("disabled")
					}
					else {
						frappe.msgprint("Something went wrong.");
					}
				}
			});
		}
		if(frm.doc.scan_lot_number == '' || frm.doc.scan_lot_number == undefined){
			$(frm.get_field('add_html').wrapper).find('.add-row').attr("disabled","disabled")
		}
	},
	"add_html": (frm) => {
		let wrapper = $(frm.get_field('add_html').wrapper).empty();
		$(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);
		$(frm.get_field('add_html').wrapper).find('.add-row').on('click', function () {

		if (!frm.doc.lot_no) {
			frappe.msgprint("Please Scan Lot before add.");
			return false;
		}
		else {
			var row = frappe.model.add_child(frm.doc, "Despatch To U1 Entry Item", "items");
			row.lot_no = frm.doc.lot_no
			row.date = frm.doc.date
			row.product_ref = frm.doc.product_ref
			row.qty_nos = frm.doc.qty_nos
			row.vendor = frm.doc.vendor
			row.weight_kgs = frm.doc.weight_kgs
			row.spp_batch_no = frm.doc.spp_batch_no
			row.batch_no = frm.doc.batch_no
			row.qty_uom = frm.doc.qty_uom
			row.valuation_rate = frm.doc.valuation_rate;
			row.amount = frm.doc.amount;
			frm.refresh_field('items');
			if(frm.doc.items && frm.doc.items.length > 0){
				let total_lots = 0
				let total_weight_no = 0
				let total_weight_kg = 0
				frm.doc.items.map(function (res){
					total_lots += 1
					total_weight_no += res.qty_nos ? res.qty_nos + total_weight_no : total_weight_no
					total_weight_kg += res.weight_kgs ? res.weight_kgs + total_weight_kg : total_weight_kg
				})
				frm.set_value("total_lots",total_lots)
				frm.set_value("total_qty_kgs",total_weight_kg)	
				frm.set_value("total_qty_nos",total_weight_no)
				refresh_field("total_lots")
				refresh_field("total_qty_kgs")
				refresh_field("total_qty_nos")
			}
			frm.set_value("lot_no","")	
			frm.set_value("date","")	
			frm.set_value("product_ref","")
			frm.set_value("spp_batch_no","")		
			frm.set_value("qty_nos",0)	
			frm.set_value("batch_no","")
			frm.set_value("qty_uom","")
			// frm.set_value("vendor","")	
			frm.set_value("weight_kgs",0)
			frm.set_df_property("weight_kgs","hidden",1)
			frm.set_df_property("qty_nos","hidden",1)	
			frm.set_value("scan_lot_number","")	
			frm.set_value("valuation_rate", 0)
			frm.set_value("amount", 0)	
			$(frm.get_field('add_html').wrapper).find('.add-row').attr("disabled","disabled")
		}
	})
	},
});
