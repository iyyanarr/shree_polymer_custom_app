// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blanking DC Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
		frm.trigger('hide_scan_section')
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.stock_entry_reference){
			// frm.add_custom_button(__("View Stock Entry"), function(){
			// 	frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);				
			//   });
			  frm.add_custom_button(__("View Delivery Note"), function(){
				frappe.set_route("Form", "Delivery Note", frm.doc.stock_entry_reference);
			  });
		}
		else{
			frm.remove_custom_button('View Stock Entry');
		}
		if(frm.doc.docstatus == 1){
			frm.set_df_property("item_produced","hidden",1)
		}
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	from_blank_bin_inward(frm){
		frm.trigger('hide_scan_section')
	},
	item_produced(frm){
		frm.trigger('hide_scan_section')
	},
	hide_scan_section(frm){
		if(frm.doc.item_produced && !frm.doc.from_blank_bin_inward){
			frm.set_df_property("blanking_entry_section","hidden",0)
		}
		else{
			if(frm.doc.from_blank_bin_inward){
				if(frm.doc.item_produced){
					frm.set_value('item_produced','')
				}
				frm.set_df_property("blanking_entry_section","hidden",0)
				frm.set_df_property("item_produced","hidden",1)
				frm.set_df_property("blanking_entry_section","hidden",0)
				frm.set_df_property("scan_clip","hidden",1)
			}
			else{
				frm.set_df_property("blanking_entry_section","hidden",1)
				frm.set_df_property("item_produced","hidden",0)
				frm.set_df_property("scan_clip","hidden",0)
			}
		}
		// frm.get_field('items').grid.grid_buttons.addClass('hidden')
		if(frm.doc.docstatus == 1 || frm.doc.docstatus == 2){
			frm.set_df_property("blanking_entry_section","hidden",1)
		}
	},
	refresh: function(frm) {
		frm.trigger('hide_scan_section')
		frm.events.view_stock_entry(frm)
		if(frm.doc.docstatus == 1){
			frm.set_df_property("blanking_entry_section","hidden",1)
		}
		 frm.set_query("employee", function() {
	        return {
	        	"query":"shree_polymer_custom_app.shree_polymer_custom_app.api.get_process_based_employess",
	            "filters": {
	                "process":"Blanking"
	            }
	        };
	    });
		  frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blanking_dc_entry.blanking_dc_entry.get_blanking_item_group',
	                args: {
	                },
	                freeze: true,
	                callback: function(r) {
						let filter_flag = false
	                	if(r.message.status=="Success"){
							filter_flag = true
							frm.set_query("item_produced", function() {
								return {
										"filters": {
											"item_group": r.message.item_group
										}
									};
							});
							}
					    else if(r.message.status == "Failed"){
							frappe.msgprint(`Mat item group not mapped in <b>SPP Settings..!</b>`)
							} 
					if (!filter_flag){
						frm.set_query("item_produced", function() {
							return {
									"filters": {
										"name": ["in",[]]
									}
								};
						});
					}    
				 }
			 });
		if(frm.doc.docstatus == 0){
		frm.trigger('add_html')
		}
	},
	"scan_clip":function(frm){
		var scan_clip = frm.doc.scan_clip;
		if(scan_clip!="" && scan_clip!=undefined ){
			if(frm.doc.item_produced){
				frappe.call({
						method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blanking_dc_entry.blanking_dc_entry.validate_clip_barcode',
						args: {
							batch_no: scan_clip,
							item_produced:frm.doc.item_produced,
						},
						freeze: true,
						callback: function(r) {
							if(r.message.status == "Failed"){
								frappe.msgprint(r.message.message);
								frm.set_value("scan_clip","");
								frm.set_value("item_produced","");
							}
							else{
								frm.set_value("scanned_item",r.message.message.item_code);
								frm.set_value("available_quantity",r.message.message.qty);
								frm.set_value("sheeting_clip",r.message.message.sheeting_clip);
								frm.set_value("spp_batch_number",r.message.message.spp_batch_number);
								frm.set_value("batch_no",r.message.message.batch_no);
								frm.set_value("mix_barcode",r.message.message.mix_barcode);
								frm.set_value("t_item_to_produce",r.message.message.item_to_produce);
							}
						}
					});
				}
			else{
				frappe.msgprint(`Please choose <b>Item to produce</b> before scan bin and clip..!`)
			}
			}
		if(frm.doc.scan_clip==""){
			$(frm.get_field('add_html').wrapper).find('.add-row').attr("disabled","disabled")

		}
	},
	"manual_clip_code":function(frm){
		var scan_clip = frm.doc.manual_clip_code;
		if(frm.doc.item_produced!="" && frm.doc.item_produced!=undefined){
		if(scan_clip!="" && scan_clip!=undefined ){
			 frappe.call({
	                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blanking_dc_entry.blanking_dc_entry.validate_clip_barcode',
	                args: {
	                    batch_no: scan_clip,
	                    item_produced:frm.doc.item_produced,
	                },
	                freeze: true,
	                callback: function(r) {
	                	console.log(r)
	                	if(r.message.status == "Failed"){
							frappe.msgprint(r.message.message);
							frm.set_value("manual_clip_code","");
	                	}
	                	else{
	                		frm.set_value("scanned_item",r.message.message.item_code);
	                		frm.set_value("sheeting_clip",r.message.message.sheeting_clip);
	                		frm.set_value("available_quantity",r.message.message.qty);
	                		frm.set_value("spp_batch_number",r.message.message.spp_batch_number);
	                		frm.set_value("batch_no",r.message.message.batch_no);
	                	}
	                }
			});
			}
		}
	},
	"scan_bin":function(frm){
		var scan_clip = frm.doc.scan_bin;
			if(scan_clip!="" && scan_clip!=undefined ){
				if(frm.doc.item_produced || frm.doc.from_blank_bin_inward){
					frappe.call({
							// method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blanking_dc_entry.blanking_dc_entry.validate_bin_barcode',
							method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blanking_dc_entry.blanking_dc_entry.validate_asset_barcode',
							args: {
								batch_no: scan_clip,
								from_blank_bin_inward:frm.doc.from_blank_bin_inward ? 'yes':'no'
							},
							freeze: true,
							callback: function(r) {
								if(r.message.status == "Failed"){
									frappe.msgprint(r.message.message);
									frm.set_value("scan_bin","");
								}
								else{
									var check_already = 0;
									if(frm.doc.items!=undefined){
										for(var k=0;k<frm.doc.items.length;k++){
											if(frm.doc.items[k].bin_code==r.message.message.name){
												check_already = 1;
											}
										}
									}
									if(check_already==0){
										if(frm.doc.from_blank_bin_inward){
											frm.set_value("asset_name",r.message.message.asset_name);
											frm.set_value("bin_code",r.message.message.name);
											frm.set_value("bin_weight",r.message.message.bin_weight);
											frm.set_value("gross_weight_kgs",r.message.message.bin_weight + r.message.message.qty);
											frm.set_value("net_weight_kgs",r.message.message.qty);
											frm.set_value("scanned_item",r.message.message.item);
											frm.set_value("available_quantity",r.message.message.available_qty);
											frm.set_value("spp_batch_number",r.message.message.spp_batch_number);
											frm.set_value("batch_no",r.message.message.batch_no);
											frm.set_value("item_to_produce",r.message.message.mat);
											frm.set_value("t_item_to_produce",r.message.message.mat);
											$(frm.get_field('add_html').wrapper).find('.add-row').removeAttr("disabled")
										}
										else{
											frm.set_value("asset_name",r.message.message.asset_name);
											frm.set_value("bin_code",r.message.message.name);
											frm.set_value("bin_weight",r.message.message.bin_weight);
											// if(frm.doc.scan_clip && frm.doc.item_produced){
											// 	$(frm.get_field('add_html').wrapper).find('.add-row').removeAttr("disabled")
											// }
											if(frm.doc.scan_clip){
												$(frm.get_field('add_html').wrapper).find('.add-row').removeAttr("disabled")
											}
										}
									}
									else{
										frm.set_value("scan_bin","");
										frappe.msgprint("Scanned Bin already added.");
									}
								}
							}
					});
				}
				else{
					frappe.msgprint(`Please choose <b>Item to produce</b> before scan bin and clip..!`)
				}
		}
		if(frm.doc.scan_bin==""){
			$(frm.get_field('add_html').wrapper).find('.add-row').attr("disabled","disabled")

		}
	},
	net_weight_kgs(frm){
		if(frm.doc.net_weight_kgs){
			if(frm.doc.available_quantity){
				if(frm.doc.net_weight_kgs > frm.doc.available_quantity){
					frappe.msgprint(`The <b>Net weight - ${frm.doc.net_weight_kgs} kgs</b> can't be greater than the <b>Available Weight - ${frm.doc.available_quantity} kgs</b>`)
					frm.set_value("gross_weight_kgs",0)
					frm.set_value("net_weight_kgs",0)
					return
				}
			}
			else{
				frappe.msgprint(`The available <b>Qty</b> is not found..!`)
				frm.set_value("gross_weight_kgs",0)
				frm.set_value("net_weight_kgs",0)
				return
			}
		}
	},
	"gross_weight_kgs":function(frm){
		if(frm.doc.gross_weight_kgs && frm.doc.gross_weight_kgs <= frm.doc.bin_weight){
			frappe.msgprint("The <b>Gross weight</b> can't be less than or equal to the <b>Bin Weight</b>")
			frm.set_value("gross_weight_kgs",0)
			frm.set_value("net_weight_kgs",0)
			return 
		}
		else{
			if(frm.doc.gross_weight_kgs){
				var net_wt= frm.doc.gross_weight_kgs - frm.doc.bin_weight
				frm.set_value("net_weight_kgs",net_wt);
			}
		}
	},
	"add_html":(frm)=>{
		let wrapper = $(frm.get_field('add_html').wrapper).empty();
		let table_html = $(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);
		$(frm.get_field('add_html').wrapper).find('.add-row').on('click', function () {
			var valid_form = 1;
			if(frm.doc.from_blank_bin_inward){
				if(!frm.doc.item_to_produce || frm.doc.item_to_produce==undefined){
					frappe.msgprint("Item Produced is missing.");
					valid_form = 0;
					return false;
				}
				if(frm.doc.spp_batch_number=="" || frm.doc.spp_batch_number==undefined){
					frappe.msgprint("SPP Batch Number is missing.");
					valid_form = 0;
					return false;
				}
				if(frm.doc.bin_code=="" || frm.doc.bin_code==undefined){
					frappe.msgprint("Please scan the bin.");
					valid_form = 0;
					return false;
				}
				if(frm.doc.net_weight_kgs == "" || frm.doc.net_weight_kgs == undefined || !frm.doc.net_weight_kgs){
					frappe.msgprint("Net Weight is missing.");
					valid_form = 0;
					return false;
				}
				if(frm.doc.batch_no == "" || frm.doc.batch_no == undefined || !frm.doc.batch_no){
					frappe.msgprint("Batch No is missing.");
					valid_form = 0;
					return false;
				}
			}
			else{
				if(!frm.doc.item_produced || frm.doc.item_produced==undefined){
					frappe.msgprint("Please choose Item Produced");
					valid_form = 0;
					return false;
				}
				if(frm.doc.spp_batch_number=="" || frm.doc.spp_batch_number==undefined){
					frappe.msgprint("Please scan the clip.");
					valid_form = 0;
					return false;
				}
				if(frm.doc.bin_code=="" || frm.doc.bin_code==undefined){
					frappe.msgprint("Please scan the bin.");
					valid_form = 0;
					return false;
				}
				if(frm.doc.gross_weight_kgs=="" || frm.doc.gross_weight_kgs==undefined){
					frappe.msgprint("Please enter the Gross Weight.");
					valid_form = 0;
					return false;
				}
			}
			if(valid_form==1){
				var row = frappe.model.add_child(frm.doc, "Blanking DC Item", "items");
	    		// row.item_produced = frm.doc.item_produced;
				row.t_item_to_produce = frm.doc.t_item_to_produce;
	    		row.scanned_item = frm.doc.scanned_item;
	    		row.spp_batch_number = frm.doc.spp_batch_number;
	    		row.batch_no = frm.doc.batch_no;
	    		row.bin_code = frm.doc.bin_code;
				row.asset_name = frm.doc.asset_name;
	    		row.bin_weight = frm.doc.bin_weight;
	    		row.gross_weight = frm.doc.gross_weight_kgs;
	    		row.net_weight = frm.doc.net_weight_kgs;
	    		row.sheeting_clip = frm.doc.sheeting_clip;
	    		row.available_quantity = frm.doc.available_quantity;
				row.mix_barcode = frm.doc.mix_barcode;
	    		frm.refresh_field('items');
	    		// frm.set_value("item_produced","");
				frm.set_value("t_item_to_produce","");
				frm.set_value("item_to_produce","");
	    		frm.set_value("scanned_item","");
				frm.set_value("mix_barcode","");
	    		frm.set_value("spp_batch_number","");
	    		frm.set_value("bin_code","");
				frm.set_value("asset_name","");
	    		frm.set_value("bin_weight","");
	    		frm.set_value("gross_weight_kgs","");
	    		frm.set_value("net_weight_kgs","");
	    		frm.set_value("available_quantity","");
	    		frm.set_value("batch_no","");
	    		frm.set_value("sheeting_clip","");
	    		frm.set_value("scan_bin","");
	    		frm.set_value("scan_clip","");
	    		$(frm.get_field('add_html').wrapper).find('.add-row').attr("disabled","disabled")

			}
		});
	},
	"add":function(frm){
		var valid_form = 1;
		// if(!frm.doc.item_produced || frm.doc.item_produced==undefined){
		// 	frappe.msgprint("Please choose Item Produced");
		// 	valid_form = 0;
		// 	return false;
		// }
		if(frm.doc.spp_batch_number=="" || frm.doc.spp_batch_number==undefined){
			frappe.msgprint("Please scan the clip.");
			valid_form = 0;
			return false;
		}
		if(frm.doc.bin_code=="" || frm.doc.bin_code==undefined){
			frappe.msgprint("Please scan the bin.");
			valid_form = 0;
			return false;
		}
		if(frm.doc.gross_weight_kgs=="" || frm.doc.gross_weight_kgs==undefined){
			frappe.msgprint("Please enter the Gross Weight.");
			valid_form = 0;
			return false;
		}
		if(valid_form==1){
			var row = frappe.model.add_child(frm.doc, "Blanking DC Item", "items");
    		// row.item_produced = frm.doc.item_produced;
			row.t_item_to_produce = frm.doc.t_item_to_produce;
    		row.scanned_item = frm.doc.scanned_item;
    		row.spp_batch_number = frm.doc.spp_batch_number;
    		row.batch_no = frm.doc.batch_no;
    		row.bin_code = frm.doc.bin_code;
			row.asset_name = frm.doc.asset_name;
    		row.bin_weight = frm.doc.bin_weight;
    		row.gross_weight = frm.doc.gross_weight_kgs;
    		row.net_weight = frm.doc.net_weight_kgs;
    		row.sheeting_clip = frm.doc.sheeting_clip;
    		row.available_quantity = frm.doc.available_quantity;
			row.mix_barcode = frm.doc.mix_barcode;
    		frm.refresh_field('items');
    		// frm.set_value("item_produced","");
			frm.set_value("t_item_to_produce","");
    		frm.set_value("scanned_item","");
			frm.set_value("mix_barcode","");
    		frm.set_value("spp_batch_number","");
    		frm.set_value("bin_code","");
			frm.set_value("asset_name","");
    		frm.set_value("bin_weight","");
    		frm.set_value("gross_weight_kgs","");
    		frm.set_value("net_weight_kgs","");
    		frm.set_value("available_quantity","");
    		frm.set_value("batch_no","");
    		frm.set_value("sheeting_clip","");
    		frm.set_value("scan_bin","");
    		frm.set_value("scan_clip","");

		}
	}
});
