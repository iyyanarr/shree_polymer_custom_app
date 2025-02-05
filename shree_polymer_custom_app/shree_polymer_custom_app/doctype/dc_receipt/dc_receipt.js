// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt
var scanned_batches = [];
frappe.ui.form.on('DC Receipt', {
	timeline_refresh:frm =>{
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
	"refresh":function(frm){
		frm.events.view_stock_entry(frm)
		if(frm.doc.batches){
			for (var i = 0; i < frm.doc.batches.length; i++) {
				scanned_batches.push(frm.doc.batches[i].scan_barcode);
			}
		}
		frm.set_query("dc_no", function() {
            return {
                "filters": [
                ["SPP Delivery Challan", "status", "!=", "Completed"]
           	 ]
            };
        });
	},

	"continue_without_dc":function(frm){
		if(frm.doc.continue_without_dc){
			frm.set_value("source_warehouse","U3-Store - SPP INDIA");
			frm.set_value("target_warehouse","U3-Store - SPP INDIA");
			frm.set_value("operation","Final Batch Mixing");
		}
		else{
			frm.set_value("source_warehouse","");
			frm.set_value("target_warehouse","");
			frm.set_value("operation","");
		
		}
	},
	"scan_mixbarcode":function(frm){
		if(frm.doc.continue_without_dc==0){
		if(frm.doc.scan_mixbarcode!="undefined" && frm.doc.scan_mixbarcode!=""){
			if(frm.doc.dc_no && frm.doc.scan_mixbarcode){
				console.log(scanned_batches)
				if(scanned_batches.indexOf(frm.doc.scan_mixbarcode)==-1){
				 frappe.call({
		                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.dc_receipt.dc_receipt.validate_dc_barocde',
		                args: {
		                    batch_no: frm.doc.scan_mixbarcode,
		                    dc_no:frm.doc.dc_no
		                },
		                freeze: true,
		                callback: function(r) {
		                	if(r.message.status=="Success"){
		                		var st_details = r.message.stock;
		                		var row = frappe.model.add_child(frm.doc, "Mixing Center Items", "batches");
		                		row.item_code = st_details[0].item_code;
		                		row.item_name = st_details[0].item_code;
		                		row.spp_batch_no = st_details[0].spp_batch_no;
		                		row.batch_no = st_details[0].batch_no;
		                		row.qty = st_details[0].qty;
		                		row.qty_uom = st_details[0].qty_uom;
		                		row.scan_barcode = st_details[0].scan_barcode;
		                		frm.refresh_field('batches');
		                		frm.set_value("scan_mixbarcode","")
		                		scanned_batches.push(st_details[0].scan_barcode)
		                	}
		                	else{
								frappe.msgprint(r.message.message);
		                	}
		                }
		            });
				}
				else{
					frm.refresh_field('batches');
		            frm.set_value("scan_mixbarcode","")
				}

		}
		else{
			frappe.msgprint("Please select DC No");
			}
		}
	 }
	 
	 else{
	 	if(frm.doc.scan_mixbarcode!="undefined" && frm.doc.scan_mixbarcode!=""){
	 		if(scanned_batches.indexOf(frm.doc.scan_mixbarcode)==-1){
			 	 frappe.call({
		                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.dc_receipt.dc_receipt.validate_mix_barocde',
		                args: {
		                    batch_no: frm.doc.scan_mixbarcode,
		                    warehouse:frm.doc.source_warehouse
		                },
		                freeze: true,
		                callback: function(r) {
		                	if(r.message.status=="Success"){
		                		var st_details = r.message.stock;
		                		var row = frappe.model.add_child(frm.doc, "Mixing Center Items", "batches");
		                		row.item_code = st_details[0].item_code;
		                		row.item_name = st_details[0].item_code;
		                		row.spp_batch_no = st_details[0].spp_batch_no;
		                		row.batch_no = st_details[0].batch_no;
		                		row.qty = st_details[0].qty;
		                		row.qty_uom = st_details[0].qty_uom;
		                		row.scan_barcode = st_details[0].scan_barcode;
		                		frm.refresh_field('batches');
		                		frm.set_value("scan_mixbarcode","")
		                		scanned_batches.push(st_details[0].scan_barcode)
		                	}
		                	else{
								frappe.msgprint(r.message.message);
		                	}

		                }
				});
	 	}
	 }
	}

	}
});
