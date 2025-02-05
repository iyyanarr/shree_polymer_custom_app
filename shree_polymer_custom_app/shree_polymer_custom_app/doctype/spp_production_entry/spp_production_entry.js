// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('SPP Production Entry', {
	

	refresh: function(frm) {
		frm.set_query("item", function() {
	        return {
	        	"query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_production_entry.spp_production_entry.get_compounds",
	            "filters": {
	                
	            }
	        };
	    });
	    frm.set_query("employee", function() {
	        return {
	        	"query":"shree_polymer_custom_app.shree_polymer_custom_app.api.get_process_based_employess",
	            "filters": {
	                "process":frm.doc.type
	            }
	        };
	    });
	    if(frm.doc.required_items){
	    	var t_qty = 0;
	    	for (var i = 0; i < frm.doc.required_items.length; i++) {
	    		t_qty+=frm.doc.required_items[i].qty;
	    	}
			frm.set_value("qty",t_qty);
	    }
	    var process_type = frm.doc.type;
	    if(frm.doc.type == "Final Batch Mixing"){
	    	process_type = "Transfer Batches to Mixing Center";
	    }
	    frm.set_query("target_warehouse", function() {
            return {
                "query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_minxing_t_warehouses",
                "filters": {
                     "type":process_type
                }
            };
        });
         frm.set_query("source_warehouse", function() {
            return {
                "query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_minxing_s_warehouses",
                "filters": {
                     "type":frm.doc.type
                }
            };
        });
         if(frm.doc.type=="Blanking"){
         	frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_production_entry.spp_production_entry.get_settings',
	                
	                freeze: true,
	                callback: function(r) {
	                	frm.set_value("target_warehouse",r.message.default_blanking_warehouse);
	                	frm.set_value("source_warehouse",r.message.default_sheeting_warehouse);
	                }
	            });
         }
	},
	"scan_location":function(frm){
		var scanned_loc = frm.doc.scan_location;

		if(scanned_loc!="" && scanned_loc!=undefined){
			frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_scanned_warehouse',
	                args: {
	                    scanned_loc: scanned_loc,
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(r.message){
	                		if(r.message.length>0){
								frm.set_value("target_warehouse",r.message[0].name);
								frm.set_value("scan_location","");
	                		}
	                		else{
								frm.set_value("scan_location","")
								frappe.msgprint("The scanned warehouse not found.")

	                		}
	                	}
	                	else{
								frm.set_value("scan_location","")
								frappe.msgprint("The scanned warehouse not found.")

	                		}
					}
				});
		}
	},
	
	"fbm_barcode":function(frm){
		if(frm.doc.fbm_barcode!="undefined" && frm.doc.fbm_barcode!=""){
			if(frm.doc.target_warehouse!="" && frm.doc.target_warehouse!=undefined){
			 frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_production_entry.spp_production_entry.validate_item_spp_barcode',
	                args: {
	                    batch_no: frm.doc.fbm_barcode,
	                    warehouse:frm.doc.source_warehouse,
	                    item:frm.doc.item,
	                    bom_no:frm.doc.bom_no,
	                    p_type:frm.doc.type,
	                },
	                freeze: true,
	                callback: function(r) {
	                	var scanned_code = frm.doc.fbm_barcode;
	                	if(r.message.status=="Failed"){
	                		frappe.msgprint(r.message.message);
	                		frm.set_value("fbm_barcode","")
	                	}
	                	else{
	                		if (r.message.stock.length>0){
	                		var st_details = r.message.stock;
	                		var row = frappe.model.add_child(frm.doc, "Mixing Item", "required_items");
	                		row.item_code = st_details[0].item_code;
	                		row.item_name = st_details[0].item_name;
	                		row.spp_batch_number = st_details[0].spp_batch_number;
	                		row.batch_no = st_details[0].batch_no;
	                		row.qty = st_details[0].qty;
	                		row.uom = st_details[0].uom;
	                		row.transfer_qty = st_details[0].qty;
	                		row.stock_uom = st_details[0].uom;
	                		row.source_warehouse = frm.doc.source_warehouse;
	                		row.scan_barcode = scanned_code;
	                		if(frm.doc.type == "Final Batch Mixing"){
	                		row.operation = "Final Batch Mixing";
	                		}
	                		if(frm.doc.type == "Blanking"){
	                		row.operation = "Blanking";
	                		}
	                		if(st_details[0].bom_item!=undefined && st_details[0].bom_item!=""){
	                			row.item_to_manufacture = st_details[0].bom_item;
	                		}
	                		frm.refresh_field('required_items');
	                		frm.set_value("fbm_barcode","");
	                		var t_qty = 0;
					    	for (var i = 0; i < frm.doc.required_items.length; i++) {
					    		t_qty+=frm.doc.required_items[i].qty;
					    	}
							frm.set_value("qty",t_qty);
							if(r.message.cutbit_items!=undefined){
								if(r.message.cutbit_items.length>0){
									var cutbit_items = r.message.cutbit_items;
									for (var i = 0; i < cutbit_items.length; i++) {
										var row = frappe.model.add_child(frm.doc, "Mixing Item", "required_items");
				                		row.item_code = cutbit_items[i].item_code;
				                		row.item_name = cutbit_items[i].item_name;
				                		row.spp_batch_number = cutbit_items[i].spp_batch_number;
				                		row.batch_no = cutbit_items[i].batch_no;
				                		row.qty = cutbit_items[i].transfer_qty;
				                		row.uom = cutbit_items[i].stock_uom;
				                		row.transfer_qty = cutbit_items[i].transfer_qty;
				                		row.stock_uom = cutbit_items[i].stock_uom;
				                		row.source_warehouse = frm.doc.source_warehouse;
				                		row.scan_barcode = scanned_code;
				                		row.is_cut_bit_item = 1
				                		if(frm.doc.type == "Final Batch Mixing"){
				                		row.operation = "Final Batch Mixing";
				                		}
				                		if(frm.doc.type == "Blanking"){
				                		row.operation = "Blanking";
				                		}
				                		frm.refresh_field('required_items');
									}
			                		
								}
							}

	                	}
	                	else{
							frappe.msgprint("Stock not available.");
	                		frm.refresh_field('required_items');

	                	}
	                }

	                }
	            });
				}
				else{
					frappe.msgprint("Please select Target Warehouse")
				}
			}
	},
	enter_manually:function(frm){
		if(frm.doc.enter_manually==1){
			setTimeout(function(){
	 $('input[data-fieldname="manual_scan_spp_batch_number"]').change(function(){
		if(frm.doc.manual_scan_spp_batch_number!="undefined" && frm.doc.manual_scan_spp_batch_number!=""){
			if(frm.doc.target_warehouse!="" && frm.doc.target_warehouse!=undefined){
			 frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_production_entry.spp_production_entry.validate_item_spp_barcode',
	                args: {
	                    batch_no: frm.doc.manual_scan_spp_batch_number,
	                    warehouse:frm.doc.source_warehouse,
	                    item:frm.doc.item,
	                    bom_no:frm.doc.bom_no,
	                    p_type:frm.doc.type,
	                },
	                freeze: true,
	                callback: function(r) {
	                	var scanned_code = frm.doc.manual_scan_spp_batch_number;
	                	if(r.message.status=="Failed"){
	                		frappe.msgprint(r.message.message);
	                		frm.set_value("manual_scan_spp_batch_number","")
	                	}
	                	else{
	                		if (r.message.stock.length>0){
	                		var st_details = r.message.stock;
	                		var row = frappe.model.add_child(frm.doc, "Mixing Item", "required_items");
	                		row.item_code = st_details[0].item_code;
	                		row.item_name = st_details[0].item_name;
	                		row.spp_batch_number = st_details[0].spp_batch_number;
	                		row.batch_no = st_details[0].batch_no;
	                		row.qty = st_details[0].qty;
	                		row.uom = st_details[0].uom;
	                		row.transfer_qty = st_details[0].qty;
	                		row.stock_uom = st_details[0].uom;
	                		row.source_warehouse = frm.doc.source_warehouse;
	                		row.scan_barcode = scanned_code;
	                		if(frm.doc.type == "Final Batch Mixing"){
	                		row.operation = "Final Batch Mixing";
	                		}
	                		if(frm.doc.type == "Blanking"){
	                		row.operation = "Blanking";
	                		}
	                		if(st_details[0].bom_item!=undefined && st_details[0].bom_item!=""){
	                			row.item_to_manufacture = st_details[0].bom_item;
	                		}
	                		frm.refresh_field('required_items');
	                		frm.set_value("manual_scan_spp_batch_number","");
	                		var t_qty = 0;
					    	for (var i = 0; i < frm.doc.required_items.length; i++) {
					    		t_qty+=frm.doc.required_items[i].qty;
					    	}
							frm.set_value("qty",t_qty);
							if(r.message.cutbit_items!=undefined){
								if(r.message.cutbit_items.length>0){
									var cutbit_items = r.message.cutbit_items;
									for (var i = 0; i < cutbit_items.length; i++) {
										var row = frappe.model.add_child(frm.doc, "Mixing Item", "required_items");
				                		row.item_code = cutbit_items[i].item_code;
				                		row.item_name = cutbit_items[i].item_name;
				                		row.spp_batch_number = cutbit_items[i].spp_batch_number;
				                		row.batch_no = cutbit_items[i].batch_no;
				                		row.qty = cutbit_items[i].transfer_qty;
				                		row.uom = cutbit_items[i].stock_uom;
				                		row.transfer_qty = cutbit_items[i].transfer_qty;
				                		row.stock_uom = cutbit_items[i].stock_uom;
				                		row.source_warehouse = frm.doc.source_warehouse;
				                		row.scan_barcode = scanned_code;
				                		row.is_cut_bit_item = 1
				                		if(frm.doc.type == "Final Batch Mixing"){
				                		row.operation = "Final Batch Mixing";
				                		}
				                		if(frm.doc.type == "Blanking"){
				                		row.operation = "Blanking";
				                		}
				                		frm.refresh_field('required_items');
									}
			                		
								}
							}

	                	}
	                	else{
							frappe.msgprint("Stock not available.");
	                		frm.refresh_field('required_items');

	                	}
	                }

	                }
	            });
				}
				else{
					frappe.msgprint("Please select Target Warehouse")
				}
			}
	 })
	},1000);
		}
	},
	"type":function(frm){
		if(frm.doc.type == "Final Batch Mixing" || frm.doc.type == "Mixing Internal"){
			frm.set_value("source_warehouse","U3-Store - SPP INDIA");
			frm.set_value("target_warehouse","U3-Store - SPP INDIA");

		}
		else{
			frm.set_value("source_warehouse","");
			frm.set_value("target_warehouse","");
		}
		cur_frm.clear_table("required_items")
		cur_frm.refresh_field("required_items")
		frm.set_value("item","");
		var process_type = frm.doc.type;
	    if(frm.doc.type == "Final Batch Mixing"){
	    	process_type = "Transfer Batches to Mixing Center";
	    }
	    frm.set_query("target_warehouse", function() {
            return {
                "query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_minxing_t_warehouses",
                "filters": {
                     "type":process_type
                }
            };
        });
         frm.set_query("source_warehouse", function() {
            return {
                "query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_minxing_s_warehouses",
                "filters": {
                     "type":frm.doc.type
                }
            };
        });
         if(frm.doc.type=="Blanking"){
         	frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_production_entry.spp_production_entry.get_settings',
	                
	                freeze: true,
	                callback: function(r) {
	                	frm.set_value("target_warehouse",r.message.default_blanking_warehouse);
	                	frm.set_value("source_warehouse",r.message.default_sheeting_warehouse);
	                }
	            });
         }
	},
	bom_no: function(frm) {
		
	},
	
	target_warehouse: function(frm) {
		cur_frm.clear_table("required_items");
		cur_frm.refresh_field("required_items");
		frm.set_value("item","");
	},
	source_warehouse: function(frm) {
		cur_frm.clear_table("required_items")
		cur_frm.refresh_field("required_items")
		frm.set_value("item","");
	},

	item: function(frm) {
	
},
});
