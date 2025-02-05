// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt
let cut_bit_items = [];
let used_bar_codes = [];
frappe.ui.form.on('Material Transfer', {
	"material_transfer_type":function(frm){
		if(frm.doc.material_transfer_type=="Transfer Batches to Mixing Center" || frm.doc.material_transfer_type=="Final Batch Mixing" || frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
			frm.set_value("source_warehouse","U3-Store - SPP INDIA");
		}
		else{
			frm.set_value("source_warehouse","");
		}
		 var process_type = frm.doc.material_transfer_type;
	    if(frm.doc.material_transfer_type == "Final Batch Mixing"){
	    	process_type = "Transfer Batches to Mixing Center";
	    }
	     if(frm.doc.material_transfer_type != "Transfer Compound to Sheeting Warehouse"){
			frm.set_query("target_warehouse", function() {
	            return {
	                "query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_minxing_t_warehouses",
	                "filters": {
	                     "type":process_type
	                }
	            };
	        });
			frm.set_value("target_warehouse","");
		}
		else{
			frm.set_value("target_warehouse","Sheeting Warehouse - SPP INDIA");
		}
		 frm.set_query("employee", function() {
	        return {
	        	"query":"shree_polymer_custom_app.shree_polymer_custom_app.api.get_process_based_employess",
	            "filters": {
	                "process":frm.doc.material_transfer_type
	            }
	        };
	    });
		 
	},

	"source_warehouse":function(frm){
		cur_frm.clear_table("batches");
	    frm.refresh_field('batches');
		frm.set_value("scan_spp_batch_number","")
		frm.set_value("scan_location","")
	},
	"target_warehouse":function(frm){
		cur_frm.clear_table("batches");
	    frm.refresh_field('batches');
		frm.set_value("scan_spp_batch_number","")
		frm.set_value("scan_location","")
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
	"scan_clip":function(frm){

		var scan_clip = frm.doc.scan_clip;

		if(scan_clip!="" && scan_clip!=undefined){
			frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_scanned_clip',
	                args: {
	                    scan_clip: scan_clip,
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(r.message){
	                		if(r.message.length>0){
								 var is_exist = 0;
								 if(frm.doc.sheeting_clip){
								 	for(var c=0;c<frm.doc.sheeting_clip.length;c++){
								 		if(r.message[0].name == frm.doc.sheeting_clip[c].sheeting_clip){
								 			is_exist = 1;

								 		}
								 	}
								 }
								 if(is_exist==0){
								 	var row = frappe.model.add_child(frm.doc, "Sheeting Clip Mapping", "sheeting_clip");
			                		row.sheeting_clip = r.message[0].name;
			                		frm.refresh_field('sheeting_clip');
			                		frm.set_value("scan_clip","")
								 }
	                		}
	                		else{
								frm.set_value("scan_clip","")
								frappe.msgprint("The scanned clip not found.")

	                		}
	                	}
	                	else{
								frm.set_value("scan_clip","")
								frappe.msgprint("The scanned clip not found.")

	                		}
					}
				});
		}
	},
	"scan_spp_batch_number":function(frm){
		if(frm.doc.batches){
			used_bar_codes = [];
			for(var k=0;k<frm.doc.batches.length;k++){
					used_bar_codes.push(frm.doc.batches[k].scan_barcode)
				}
		}
		if(frm.doc.scan_spp_batch_number!="undefined" && frm.doc.scan_spp_batch_number!="" && used_bar_codes.indexOf(frm.doc.scan_spp_batch_number)==-1){
			if(frm.doc.target_warehouse!="" && frm.doc.target_warehouse!=undefined){
		     var s_type = "Material Transfer"
		   if(frm.doc.material_transfer_type=="Transfer Batches to Mixing Center" ||
		     	frm.doc.material_transfer_type=="Final Batch Mixing"){
		     	s_type = "Manufacture"
		     }
		     if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
		     	s_type = "Manufacture"
		     }
			 frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.validate_spp_batch_no',
	                args: {
	                    batch_no: frm.doc.scan_spp_batch_number,
	                    warehouse:frm.doc.source_warehouse,
	                    t_warehouse:frm.doc.target_warehouse,
	                    s_type:s_type,
	                    t_type:frm.doc.material_transfer_type,
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(!r.message.status){
	                		frappe.msgprint(r.message.message);
	                		frm.set_value("scan_spp_batch_number","")
	                	}
	                	else{
	                		var st_details = r.message.stock;
	                		var check_cut_items = 1
	                		var cut_bit_msg = ""

	                		if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
	                			if(r.message.is_cut_bit_item==1){
	                				if(frm.doc.batches.length==0){
	                					check_cut_items = 0;
	                					cut_bit_msg = "Please choose compound first to transfer to Sheeting Warehouse"
	                				}
	                				else{
	                					check_cut_items =0;
	                					for (var i = 0; i < frm.doc.batches.length; i++) {
	                						if(frm.doc.batches[i].item_code == st_details[0].item_code)
	                						{
	                							check_cut_items =1;
	                						}
	                					}
	                					if (check_cut_items == 0){
	                						cut_bit_msg = "Compund and Cutbit item are differed.Please choose proper Cut bit item."
	                					}
	                				}
	                			}
	                		}
	                		if (check_cut_items==1){
		                		
		                		var row = frappe.model.add_child(frm.doc, "Mixing Center Items", "batches");
		                		var scanned_code = frm.doc.scan_spp_batch_number;
		                		row.item_code = st_details[0].item_code;
		                		row.item_name = st_details[0].item_code;
		                		if(r.message.is_cut_bit_item==0){
		                			row.spp_batch_no = st_details[0].spp_batch_number;
		                		}
		                		row.batch_no = st_details[0].batch_no;
		                		if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
		                			// row.qty = st_details[0].transfer_qty;
		                			row.qty = 0;
		                			row.qc_template = st_details[0].quality_inspection_template
		                			frm.set_value("cutbit_qty",r.message.cut_percentage_val);
		                			frm.refresh_field('cutbit_qty');
		                		}
		                		else{
		                			row.qty = st_details[0].transfer_qty;
		                		}
		                		if( st_details[0].qi_name!=undefined &&  st_details[0].qi_name!="" &&  st_details[0].qi_name!=null){
		                			row.quality_inspection = st_details[0].qi_name;
		                		}
		                		row.is_cut_bit_item = r.message.is_cut_bit_item 
		                		row.qty_uom = st_details[0].stock_uom;
		                		row.scan_barcode = frm.doc.scan_spp_batch_number;
		                		used_bar_codes.push(scanned_code);
		                		frm.refresh_field('batches');
		                		if(r.message.cut_bit_items){
		                			if(r.message.cut_bit_items.length>0){
		                				for(var ct = 0 ;ct<r.message.cut_bit_items.length;ct++){
		                					var ct_row = frappe.model.add_child(frm.doc, "Mixing Center Items", "batches");
					                		var scanned_code = frm.doc.scan_spp_batch_number;
					                		ct_row.item_code = st_details[0].item_code;
					                		ct_row.item_name = st_details[0].item_code;
					                		ct_row.qty = r.message.cut_bit_items[ct].qty;
					                		ct_row.is_cut_bit_item = 1 
					                		ct_row.qty_uom = st_details[0].stock_uom;
					                		ct_row.scan_barcode = frm.doc.scan_spp_batch_number;
					                		frm.refresh_field('batches');
		                				}
		                			}
		                		}
		                		frm.set_value("scan_spp_batch_number","")
		                		
		                	}
		                	else{
		                		frm.set_value("scan_spp_batch_number","")
		                		frappe.msgprint(cut_bit_msg);
		                	}
	      
	                	}

	                }
	            });
				}
				else{
					frappe.msgprint("Please select Target Warehouse")
				}
			}
			else{
				frm.set_value("scan_spp_batch_number","")
			}
	},
	use_cut_bit:function(frm){
		if(frm.doc.use_cut_bit==1){
			frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_cutbit_items',
	                args: {
	                    items:JSON.stringify(frm.doc.batches)
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(r.message.length>0){
	                		var options = []
	                		for (var i = 0; i < r.message.length; i++) {
	                			options.push(r.message[i].spp_batch_number);
	                			cut_bit_items.push(r.message[i]);
	                		}
	                		frappe.meta.get_docfield('Cut Bit Item', 'spp_batch_number', frm.doc.name).options = options;
							frm.refresh_field('cut_bit_items');
							// frappe.meta.get_docfield("DoctypeName", "fields", cur_frm.doc.name).options = [""].concat(options);
							// frappe.model.set_value(cdt, cdn,"fields", options);
							// cur_frm.refresh_field("fields");
	                	}
	                	else{
	                		frappe.msgprint("There are items available in Cut Bit Warehouse")
	                	}
						
					}
				});
		}
	},
	enter_manually:function(frm){
	if(frm.doc.batches){
		used_bar_codes = [];
		for(var k=0;k<frm.doc.batches.length;k++){
				used_bar_codes.push(frm.doc.batches[k].scan_barcode)
			}
	}
		if(frm.doc.enter_manually==1){
			setTimeout(function(){
	 $('input[data-fieldname="manual_scan_spp_batch_number"]').change(function(){
		 
	  if(frm.doc.manual_scan_spp_batch_number!="undefined" && frm.doc.manual_scan_spp_batch_number!="" && used_bar_codes.indexOf(frm.doc.manual_scan_spp_batch_number)==-1){
			if(frm.doc.target_warehouse!="" && frm.doc.target_warehouse!=undefined){
		     var s_type = "Material Transfer"
		     if(frm.doc.material_transfer_type=="Transfer Batches to Mixing Center" ||
		     	frm.doc.material_transfer_type=="Final Batch Mixing"){
		     	s_type = "Manufacture"
		     }
		     if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
		     	s_type = "Manufacture"
		     }
			 frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.validate_spp_batch_no',
	                args: {
	                    batch_no: frm.doc.manual_scan_spp_batch_number,
	                    warehouse:frm.doc.source_warehouse,
	                    t_warehouse:frm.doc.target_warehouse,
	                    s_type:s_type,
	                    t_type:frm.doc.material_transfer_type,
	                },
	                freeze: true,
	                callback: function(r) {
	                	if(!r.message.status){
	                		frappe.msgprint(r.message.message);
	                		frm.set_value("manual_scan_spp_batch_number","")
	                	}
	                	else{
	                		var st_details = r.message.stock;
	                		var check_cut_items = 1
	                		var cut_error_msg = "Please choose compound first to transfer to Sheeting Warehouse";
	                		if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
	                			if(r.message.is_cut_bit_item==1){
	                				if(frm.doc.batches.length==0){
	                					check_cut_items = 0;
	                				}
	                				else{
	                					check_cut_items =0;
	                					for (var i = 0; i < frm.doc.batches.length; i++) {
	                						if(frm.doc.batches[i].item_code == st_details[0].item_code)
	                						{
	                							check_cut_items =1;
	                						}
	                					}
	                					if(check_cut_items==0){
	                						cut_error_msg = "Fresh batch item and Cut Bit Item not matched.";
	                					}
	                				}
	                			}
	                		}
	                		if (check_cut_items==1){
		                		
		                		var row = frappe.model.add_child(frm.doc, "Mixing Center Items", "batches");
		                		var scanned_code = frm.doc.manual_scan_spp_batch_number;
		                		row.item_code = st_details[0].item_code;
		                		row.item_name = st_details[0].item_code;
		                		if(r.message.is_cut_bit_item==0){
		                			row.spp_batch_no = st_details[0].spp_batch_number;
		                		}
		                		row.batch_no = st_details[0].batch_no;
		                		if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse" && r.message.is_cut_bit_item==0){
		                			// row.qty = st_details[0].transfer_qty;
		                			row.qty = 0;
		                			row.qc_template = st_details[0].quality_inspection_template;
		                			frm.set_value("cutbit_qty",r.message.cut_percentage_val);
		                			frm.refresh_field('cutbit_qty');
		                		}
		                		else{
		                			row.qty = st_details[0].transfer_qty;
		                		}
		                		if( st_details[0].qi_name!=undefined &&  st_details[0].qi_name!="" &&  st_details[0].qi_name!=null){
		                			row.quality_inspection = st_details[0].qi_name;
		                		}
		                		row.is_cut_bit_item = r.message.is_cut_bit_item 
		                		row.qty_uom = st_details[0].stock_uom;
		                		row.scan_barcode = scanned_code;
		                		used_bar_codes.push(scanned_code);
		                		frm.refresh_field('batches');
		                		if(r.message.cut_bit_items){
		                			if(r.message.cut_bit_items.length>0){
		                				for(var ct = 0 ;ct<r.message.cut_bit_items.length;ct++){
		                					var ct_row = frappe.model.add_child(frm.doc, "Mixing Center Items", "batches");
					                		var scanned_code = frm.doc.scan_spp_batch_number;
					                		ct_row.item_code = st_details[0].item_code;
					                		ct_row.item_name = st_details[0].item_code;
					                		ct_row.qty = r.message.cut_bit_items[ct].qty;
					                		ct_row.is_cut_bit_item = 1 
					                		ct_row.qty_uom = st_details[0].stock_uom;
					                		ct_row.scan_barcode = frm.doc.scan_spp_batch_number;
					                		frm.refresh_field('batches');
		                				}
		                			}
		                		}
		                		frm.set_value("manual_scan_spp_batch_number","")
		                	}
		                	else{
		                		frm.set_value("manual_scan_spp_batch_number","")
		                		frappe.msgprint(cut_error_msg);
		                	}
	      
	                	}

	                }
	            });
				}
				else{
					frappe.msgprint("Please select Target Warehouse")
				}
			}
			else{
				frm.set_value("scan_spp_batch_number","")
			}
	 })
	},1000);
		}
	},
	refresh: function(frm) {
		frm.set_query("item", function() {
	        return {
	        	"query":"shree_polymer_custom_app.shree_polymer_custom_app.doctype.spp_production_entry.spp_production_entry.get_compounds",
	            "filters": {
	                
	            }
	        };
	    });
        if(frm.doc.batches){
			for (var i = 0; i < frm.doc.batches.length; i++) {
				used_bar_codes.push(frm.doc.batches.scan_barcode);
			}
		}
		 var process_type = frm.doc.material_transfer_type;
	    if(frm.doc.material_transfer_type == "Final Batch Mixing"){
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
			if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse") {
			var allow_qi = 0;
			for (var i = 0; i < frm.doc.batches.length; i++) {
				 if(frm.doc.batches[i].qc_template && !frm.doc.batches[i].quality_inspection){
				 	allow_qi = 1;
				 	break;
				 }
			}
			
			if(allow_qi==1){
				frm.add_custom_button(__("Quality Inspection(s)"), () => {
						 new quality_inspections({
	                            frm: frm,
	                        });
				}, __("Create"));
				frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if(frm.doc.dc_no){
			frm.add_custom_button(__("View DC"), () => {
				frappe.set_route("Form", "SPP Delivery Challan", frm.doc.dc_no);

			});
		}
		if(frm.doc.stock_entry_ref){
			frm.add_custom_button(__("View Stock Entry"), () => {
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_ref);

			});
		}
		 if(frm.doc.batches){
	    	var t_qty = 0;
	    	for (var i = 0; i < frm.doc.batches.length; i++) {
	    		t_qty+=frm.doc.batches[i].qty;
	    	}
			frm.set_value("qty",t_qty);
	    }
	    //  if(frm.doc.material_transfer_type == "Final Batch Mixing"){
	    // 	process_type = "Transfer Batches to Mixing Center";
	    // }
	    if (has_common(frappe.user_roles, ['Batch Operator']) && frappe.session.user!="Administrator") {
	   	 set_field_options("material_transfer_type", ["Transfer Batches to Mixing Center","Final Batch Mixing"])
	    }
	    if (has_common(frappe.user_roles, ['Mill Operator']) && frappe.session.user!="Administrator") {
	   	 set_field_options("material_transfer_type", ["Transfer Compound to Sheeting Warehouse"])
	    }
	    if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
	    	for(var i=0;i<frm.doc.batches;i++){
				if(frm.doc.batches[i].is_cut_bit_item==0)
				frappe.call({
			        method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_cut_bit_rate',
			        args: {
			            item_code :frm.doc.batches[i].item_code,
			            qty :frm.doc.batches[i].qty
			        },
			        freeze: true,
			        callback: function(r) {
			        	frm.set_value("cutbit_qty",r.message);
				        frm.refresh_field('cutbit_qty');

			        }
			    });
			}
	}
	},
	 
	
});
frappe.ui.form.on("Material Transfer Item", "qty", function(frm, cdt, cdn) {
	if(frm.doc.material_transfer_type=="Transfer Compound to Sheeting Warehouse"){
		var item = locals[cdt][cdn];
		frappe.call({
	        method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.material_transfer.material_transfer.get_cut_bit_rate',
	        args: {
	            item_code :item.item_code,
	            qty :item.qty
	        },
	        freeze: true,
	        callback: function(r) {
	        	frm.set_value("cutbit_qty",r.message);
		        frm.refresh_field('cutbit_qty');

	        }
	    });
	}


});

frappe.ui.form.on("Cut Bit Item", "spp_batch_number", function(frm, cdt, cdn) {
	var check_already = 0
	var item = locals[cdt][cdn];
	for (var i = 0; i < frm.doc.cut_bit_items.length; i++) {
		if(frm.doc.cut_bit_items[i].spp_batch_number == item.spp_batch_number && item.name != frm.doc.cut_bit_items[i].name){
			frappe.msgprint("<b>"+item.spp_batch_number+"</b> is already added.");
			check_already = 1;
			cur_frm.get_field("cut_bit_items").grid.grid_rows[item.idx-1].remove();
			frm.refresh_field('cut_bit_items');	
		}
	}
	if(check_already==0){
		var obj = cut_bit_items.filter(o=>o.spp_batch_number==item.spp_batch_number);
		console.log(obj)
		if(obj){
			item.qty = obj[0].transfer_qty;
			item.uom = obj[0].stock_uom;
			item.batch_no = obj[0].batch_no;
			item.item_code = obj[0].item_code;
			item.item_name = obj[0].item_name;
		}
		frm.refresh_field('cut_bit_items');	
	}

});
var quality_inspections = Class.extend({
    init: function(opts) {
        this.frm = opts.frm;
        this.make();
    },
    make: function() {
    	let data = [];
		const fields = [
			{
				label: "Items",
				fieldtype: "Table",
				fieldname: "items",
				cannot_add_rows: true,
				in_place_edit: true,
				data: data,
				get_data: () => {
					return data;
				},
				fields: [
					{
						fieldtype: "Data",
						fieldname: "docname",
						hidden: true
					},
					{
						fieldtype: "Read Only",
						fieldname: "item_code",
						label: __("Item Code"),
						in_list_view: true
					},
					{
						fieldtype: "Read Only",
						fieldname: "item_name",
						label: __("Item Name"),
						in_list_view: true
					},
					{
						fieldtype: "Float",
						fieldname: "qty",
						label: __("Accepted Quantity"),
						in_list_view: true,
						read_only: true
					},
					
				]
			}
		];
		var dt = this.frm.doc.doctype;
		var dname = this.frm.doc.name;
		const dialog = new frappe.ui.Dialog({
			title: __("Select Items for Quality Inspection"),
			fields: fields,
			primary_action: function () {
				const data = dialog.get_values();
				frappe.call({
					method: "erpnext.controllers.stock_controller.make_quality_inspections",
					args: {
						doctype: dt,
						docname: dname,
						items: data.items
					},
					freeze: true,
					callback: function (r) {
						if (r.message.length > 0) {
							if (r.message.length === 1) {
								frappe.set_route("Form", "Quality Inspection", r.message[0]);
							} else {
								frappe.route_options = {
									"reference_type": this.frm.doc.doctype,
									"reference_name": this.frm.doc.name
								};
								frappe.set_route("List", "Quality Inspection");
							}
						}
						dialog.hide();
					}
				});
			},
			primary_action_label: __("Create")
		});
		this.frm.doc.batches.forEach(item => {
			if (!item.quality_inspection && item.qc_template) {
				let dialog_items = dialog.fields_dict.items;
				dialog_items.df.data.push({
					"docname": item.name,
					"item_code": item.item_code,
					"item_name": item.item_name,
					"qty": item.qty,
					"description": item.description,
					"quality_document": item.qc_template,
					
				});
				dialog_items.grid.refresh();
			}
		});
			dialog.show();
    }
})

