// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sub Lot Creation', {
	refresh: function (frm) {
		frm.events.view_stock_entry(frm)
		frm.events.change_label(frm)
	},
	timeline_refresh: frm => {
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry: (frm) => {
		if (frm.doc.stock_entry_reference) {
			frm.add_custom_button(__("View Stock Entry"), function () {
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			});
		}
		else {
			frm.remove_custom_button('View Stock Entry');
		}
		if (!frm.doc.available_qty && !frm.doc.__islocal) {
			frm.set_df_property("available_qty", "hidden", 1)
		}
		else {
			frm.set_df_property("available_qty", "hidden", 0)
		}
		if (!frm.doc.qty && !frm.doc.__islocal) {
			frm.set_df_property("qty", "hidden", 1)
		}
		else {
			frm.set_df_property("qty", "hidden", 0)
		}
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	change_label:frm =>{
		setTimeout(() =>{
			if(frm.doc.uom && frm.doc.uom == "Kg"){
				$(frm.get_field('available_qty').wrapper).find('label').text("Available Qty (Kgs)")
			}
			else if(frm.doc.uom && frm.doc.uom == "Nos"){
				$(frm.get_field('available_qty').wrapper).find('label').text("Available Qty (Nos)")
			}
		},500)
	},
	qty:frm =>{
		if(!frm.doc.available_qty || frm.doc.available_qty == undefined){
			frappe.validated = false
			frm.set_value("qty","")
			frappe.msgprint(`The available stock Qty not found`)
		}
		if((frm.doc.qty && frm.doc.available_qty) && (frm.doc.qty > frm.doc.available_qty) && frm.doc.uom == "Kg"){
			frappe.validated = false
			frm.set_value("qty","")
			frappe.msgprint(`The Qty can't be greater than available qty - ${frm.doc.available_qty}`)
		}
		if((frm.doc.qty && frm.doc.available_qty_kgs) && (frm.doc.qty > frm.doc.available_qty_kgs) && frm.doc.uom == "Nos"){
			frappe.validated = false
			frm.set_value("qty","")
			frappe.msgprint(`The Qty can't be greater than available qty - ${frm.doc.available_qty_kgs}`)
		}
	},
	"scan_lot_no": (frm) => {
		if (frm.doc.scan_lot_no && frm.doc.scan_lot_no != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.sub_lot_creation.sub_lot_creation.validate_lot',
				args: {
					lot_no: frm.doc.scan_lot_no,
					name:frm.doc.name
				},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_lot_no", "");
						frm.set_df_property("available_qty", "hidden", 1)
						frm.set_df_property("qty", "hidden", 1)
					}
					else if (r && r.status == "success") {
						if(r.message.containing_lrt_sublot){
							frm.set_value("lrt_found", r.message.containing_lrt_sublot)
							frm.set_value("lrt_details",r.message.lrt_datas)	
						}
						else{
							frm.set_value("lrt_found", 0)
							frm.set_value("lrt_details", JSON.stringify({}))
						}
						if(r.message.deflashing_receipt_parent){
							frm.set_value("deflashing_receipt_parent", r.message.deflashing_receipt_parent)	
						}
						if(r.message.lot_resource_tagging_parent){
							frm.set_value("lot_resource_tagging_parent", r.message.lot_resource_tagging_parent)	
						}
						if(r.message.despatch_u1_parent){
							frm.set_value("despatch_u1_parent", r.message.despatch_u1_parent)	
						}
						frm.set_value("scan_lot_no", frm.doc.scan_lot_no.toUpperCase())
						frm.set_value("available_qty", r.message.qty)
						frm.set_value("reference_doctype", r.message.source_ref_document)
						frm.set_value("warehouse", r.message.t_warehouse)
						frm.set_value("item_code", r.message.item_code)
						frm.set_value("spp_batch_no", r.message.spp_batch_number)
						frm.set_value("uom", r.message.stock_uom)
						frm.set_value("batch_no", r.message.batch_no)
						frm.set_value("first_parent_lot_no", r.message.first_parent_lot_no)
						frm.set_value("material_receipt_parent", r.message.material_receipt_parent)
						frm.set_value("available_qty_kgs", r.message.available_qty_in_kgs)
						frm.set_df_property("qty", "hidden", 0)
						frm.set_df_property("available_qty", "hidden", 0)
						frm.events.change_label(frm)
					}
					else {
						frm.set_df_property("available_qty", "hidden", 1)
						frm.set_df_property("qty", "hidden", 1)
						frappe.msgprint("Something went wrong..!");
					}
				}
			});
		}
	},
});
