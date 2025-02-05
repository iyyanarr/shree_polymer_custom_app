// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blank Bin Rejection Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	refresh:(frm) =>{
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.stock_entry_reference){
			frm.add_custom_button(__("View Stock Entry"), function(){
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			  });
		}
		else{
			frm.remove_custom_button('View Stock Entry');
		}
	},
	"scan_inspector": function(frm) {
		if(frm.doc.scan_inspector && frm.doc.scan_inspector != undefined){
			frappe.call({
				method:'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_rejection_entry.blank_bin_rejection_entry.validate_inspector_barcode',
				args:{
					"b__code":frm.doc.scan_inspector
				},
				freeze:true,
				callback:(r) =>{
					if(r && r.status=="failed"){
						frappe.msgprint(r.message);
						frm.set_value("scan_inspector", "");
					}
					else if(r && r.status=="success"){
						frm.set_value("inspector_name",r.message.employee_name);
						frm.set_value("inspector_code",r.message.name);
					}
					else{
						frappe.msgprint("Somthing went wrong.");
						frm.set_value("scan_inspector", "");
					}
				}
			})
		}
	},
	"scan_bin": (frm) => {
		if (frm.doc.scan_bin && frm.doc.scan_bin != undefined) {
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_rejection_entry.blank_bin_rejection_entry.validate_bin_barcode',
					args: {
						bar_code: frm.doc.scan_bin,
					},
					freeze: true,
					callback: function (r) {
						if (r.status == "failed") {
							frappe.msgprint(r.message);
							frm.set_value("scan_bin", "");
						}
						else if(r.status == "success"){
							frm.set_value("available_qty", r.message.qty);
							frm.set_value("item", r.message.item);
							frm.set_value("compound_code", r.message.compound_code);
							frm.set_value("bin_code", r.message.name);
							frm.set_value("bin_name", r.message.asset_name);
							frm.set_value("bin_weight", r.message.bin_weight);	
							frm.set_value("batch_code", r.message.batch_no);	
						}
					}
				});	
		}
	},
	"gross_weight": (frm) => {
		if(frm.doc.gross_weight && frm.doc.gross_weight>0){
			if((frm.doc.gross_weight - frm.doc.bin_weight) > frm.doc.available_qty){
				frappe.validated = false
				frm.set_value("gross_weight", "");	
				frappe.msgprint(`The Net Weight can't be greater than - <b>${frm.doc.available_qty}</b>`)
			}
			if((frm.doc.bin_weight) >= frm.doc.gross_weight){
				frappe.validated = false
				frm.set_value("gross_weight", "");	
				frappe.msgprint(`The Net Weight can't be lesser than the bin weight - <b>${frm.doc.bin_weight}</b>`)
			}
			else{
				frm.set_value("quantity", (frm.doc.gross_weight-frm.doc.bin_weight));
			}
		}
		else{
			frm.set_value("quantity", "");
		}	
	}
});
