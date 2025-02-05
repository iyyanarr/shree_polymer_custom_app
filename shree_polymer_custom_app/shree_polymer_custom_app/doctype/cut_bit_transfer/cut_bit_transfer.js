// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt
let used_bar_codes = [];
frappe.ui.form.on('Cut Bit Transfer', {
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
	refresh: function(frm) {
		frm.events.view_stock_entry(frm)
		if(frm.doc.transfer_from == "Warming"){
			frm.set_value("source_warehouse","Sheeting Warehouse - SPP INDIA");
		}
		if(frm.doc.transfer_from == "Blanking"){
			frm.set_value("source_warehouse","Blanking Warehouse - SPP INDIA");
		}
		if (has_common(frappe.user_roles, ['Mill Operator']) && frappe.session.user!="Administrator") {
	   		 set_field_options("transfer_from", ["Warming"])
	    }
	    if (has_common(frappe.user_roles, ['Blanker']) && frappe.session.user!="Administrator") {
	   		 set_field_options("transfer_from", ["Blanking"])
	    }
		frm.events.set_link_query(frm)
	},
	set_link_query(frm){
		frm.set_query("employee", function() {
	        return {
	        	"query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.cut_bit_transfer.cut_bit_transfer.get_process_based_employess",
	            "filters": {
	                "process":"Cut Bit Transfer"
	            }
	        };
	    });
	},
	transfer_from: function(frm) {
		
		if(frm.doc.transfer_from == "Warming"){
			frm.set_value("source_warehouse","Sheeting Warehouse - SPP INDIA");
		}
		if(frm.doc.transfer_from == "Blanking"){
			frm.set_value("source_warehouse","Blanking Warehouse - SPP INDIA");
		}
	},
	"scan_clip__bin":function(frm){
		if(frm.doc.items){
			used_bar_codes = [];
			for(var k=0;k<frm.doc.items.length;k++){
					used_bar_codes.push(frm.doc.items[k].scan_barcode)
				}
		}
		var scan_clip = frm.doc.scan_clip__bin;

		if(scan_clip!="" && scan_clip!=undefined){
			if(!scan_clip.toLowerCase().startsWith("cb_")){

			
			frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.cut_bit_transfer.cut_bit_transfer.validate_clip_barcode',
	                args: {
	                    batch_no: scan_clip,
	                    t_type:frm.doc.transfer_from,
	                    warehouse:frm.doc.source_warehouse
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(r.message.status=="Failed"){
	                		frappe.msgprint(r.message.message);
	                		frm.set_value("scan_clip__bin","")
	                	}
	                	else{

	                		var st_details = r.message.stock;
	                		var is_exist = 0;
	                		if(frm.doc.items){
		                		for(var i=0;i<frm.doc.items.length;i++){
		                			if(st_details[0].item_code == frm.doc.items[i].item_code &&
		                			st_details[0].spp_batch_number == frm.doc.items[i].spp_batch_no &&
		                			st_details[0].batch_no == frm.doc.items[i].batch_no &&
		                			st_details[0].mix_barcode == frm.doc.items[i].scan_barcode ){
		                				is_exist = 1;
		                			}
		                		}
		                	}
	                		if(is_exist==0){
			                	var row = frappe.model.add_child(frm.doc, "Mixing Center Items", "items");
		                		var scanned_code = frm.doc.scan_spp_batch_number;
		                		row.item_code = st_details[0].item_code;
		                		row.item_name = st_details[0].item_code;
		                		row.spp_batch_no = st_details[0].spp_batch_number;
		                		row.batch_no = st_details[0].batch_no;
		                		row.qty = 0;
		                		row.qty_uom = st_details[0].uom;
		                		row.ct_source_warehouse = r.message.source_warehouse;
		                		row.scan_barcode = st_details[0].mix_barcode;
		                		used_bar_codes.push(scanned_code);
		                		frm.refresh_field('items');
		                		frm.set_value("scan_clip__bin","");
		                	}
		                	else{
	                			frappe.msgprint("Item is already added.");
	                			frm.set_value("scan_clip__bin","");
		                	}
                		}
	                }
	            })
			}
			else{
				var ct_item = scan_clip.toLowerCase().split("cb_")[1];
				var ct_valid = 0;
				if(frm.doc.items){
				for(var i=0;i<frm.doc.items.length;i++){
					if(frm.doc.items[i].item_code.toLowerCase() == ct_item){
						ct_valid = 1;
	                	frm.set_value("cut_bit_item",frm.doc.items[i].item_code);
	                	frm.set_value("scan_clip__bin","");

					}
					}
				}
				if(ct_valid==0){
					frappe.msgprint("Cut Bit Item and Fresh Batch Item not matched.");
					frm.set_value("cut_bit_item","");
	                frm.set_value("scan_clip__bin","");
				}
			}
		}
	},
	"manual_scan_spp_batch_number":function(frm){
		if(frm.doc.items){
			used_bar_codes = [];
			for(var k=0;k<frm.doc.items.length;k++){
					used_bar_codes.push(frm.doc.items[k].scan_barcode)
				}
		}
		var scan_clip = frm.doc.manual_scan_spp_batch_number;

		if(scan_clip!="" && scan_clip!=undefined){
			if(!scan_clip.toLowerCase().startsWith("cb_")){

			
			frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.cut_bit_transfer.cut_bit_transfer.validate_clip_barcode',
	                args: {
	                    batch_no: scan_clip,
	                    t_type:frm.doc.transfer_from,
	                    warehouse:frm.doc.source_warehouse
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(r.message.status=="Failed"){
	                		frappe.msgprint(r.message.message);
	                		frm.set_value("scan_clip__bin","")
	                	}
	                	else{

	                		var st_details = r.message.stock;
	                		var is_exist = 0;
	                		if(frm.doc.items){
		                		for(var i=0;i<frm.doc.items.length;i++){
		                			if(st_details[0].item_code == frm.doc.items[i].item_code &&
		                			st_details[0].spp_batch_number == frm.doc.items[i].spp_batch_no &&
		                			st_details[0].batch_no == frm.doc.items[i].batch_no &&
		                			st_details[0].mix_barcode == frm.doc.items[i].scan_barcode &&
		                			st_details[0].qty == frm.doc.items[i].qty){
		                				is_exist = 1;
		                			}
		                		}
		                	}
	                		if(is_exist==0){
			                	var row = frappe.model.add_child(frm.doc, "Mixing Center Items", "items");
		                		var scanned_code = frm.doc.scan_spp_batch_number;
		                		row.item_code = st_details[0].item_code;
		                		row.item_name = st_details[0].item_code;
		                		row.spp_batch_no = st_details[0].spp_batch_number;
		                		row.batch_no = st_details[0].batch_no;
		                		row.qty = 0;
		                		row.qty_uom = st_details[0].uom;
		                		row.scan_barcode = st_details[0].mix_barcode;
		                		row.ct_source_warehouse = r.message.source_warehouse;
		                		used_bar_codes.push(scanned_code);
		                		frm.refresh_field('items');
		                		frm.set_value("manual_scan_spp_batch_number","");
		                	}
		                	else{
	                			frappe.msgprint("Item is already added.");
	                			frm.set_value("manual_scan_spp_batch_number","");
		                	}
                		}
	                }
	            })
			}
			else{
				var ct_item = scan_clip.toLowerCase().split("cb_")[1];
				var ct_valid = 0;
				for(var i=0;i<frm.doc.items.length;i++){
					if(frm.doc.items[i].item_code.toLowerCase() == ct_item){
						ct_valid = 1;
	                	frm.set_value("cut_bit_item",frm.doc.items[i].item_code);
	                	frm.set_value("manual_scan_spp_batch_number","");

					}
				}
				if(ct_valid==0){
					frappe.msgprint("Cut Bit Item and Fresh Batch Item not matched.");
					frm.set_value("cut_bit_item","");
	                frm.set_value("manual_scan_spp_batch_number","");
				}
			}
		}
	}
});
