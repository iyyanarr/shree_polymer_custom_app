// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blank Bin Inward Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	refresh:(frm) =>{
		if(frm.doc.docstatus == 1){
			frm.set_df_property("bin_scan_section", "hidden", 1)
		}
		frm.set_df_property("bin_weight_kgs", "hidden", 1)
		frm.set_df_property("gross_weight_kgs", "hidden", 1)
		frm.set_df_property("net_weight_kgs", "hidden", 1)
		if(frm.doc.docstatus == 0){
			$('button[data-fieldname="add"]').attr("disabled","disabled");
		}
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.stock_entry_reference){
			frm.add_custom_button(__("View Stock Entry"), function(){
				frappe.route_options = {
					"name": ["in",frm.doc.stock_entry_reference.split(',')]
				};
				frappe.set_route("List", "Stock Entry");
			  });
		}
		else{
			frm.remove_custom_button('View Stock Entry');
		}
	},
	move_to_cut_bit_warehouse(frm){
		frm.set_value("available_qty", "");
		frm.set_value("bin_code","");
		frm.set_value("bin_name","");
		frm.set_value("bin_weight_kgs","");
		frm.set_value("item", "");
		frm.set_value("compound_code", "");
		frm.set_value("gross_weight_kgs","");
		frm.set_value("net_weight_kgs","");
		frm.set_value("blank_bin","");
		frm.set_value("scan_cut_bit_batch","");
		frm.set_value("spp_batch_number","");
		frm.set_value("batch_no","");
		frm.set_value("ibm_id","");
		frm.set_df_property("bin_weight_kgs", "hidden", 1)
		frm.set_df_property("gross_weight_kgs", "hidden", 1)
		frm.set_df_property("net_weight_kgs", "hidden", 1)
		$('button[data-fieldname="add"]').attr("disabled","disabled");
	},
	"gross_weight_kgs": (frm) => {
		if(frm.doc.gross_weight_kgs && (frm.doc.gross_weight_kgs>0)){
			if((frm.doc.gross_weight_kgs - frm.doc.bin_weight_kgs) > frm.doc.available_qty){
				frappe.validated = false
				frm.set_value("gross_weight_kgs", "");	
				frappe.msgprint(`The Net Weight can't be greater than - <b>${frm.doc.available_qty}</b>`)
			}
			if(frm.doc.gross_weight_kgs && (frm.doc.gross_weight_kgs>0)){
				if((frm.doc.bin_weight_kgs) >= frm.doc.gross_weight_kgs){
					frappe.validated = false
					frm.set_value("gross_weight_kgs", "");	
					frappe.msgprint(`The Net Weight can't be lesser than the bin weight - <b>${frm.doc.bin_weight_kgs}</b>`)
				}
				else{
					frm.set_value("net_weight_kgs", (frm.doc.gross_weight_kgs-frm.doc.bin_weight_kgs));
				}
			}
		}
		else{
			frm.set_value("net_weight_kgs", "");
		}	
	},
	"blank_bin": (frm) => {
		if (frm.doc.blank_bin && frm.doc.blank_bin != undefined) {
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.validate_bin_barcode',
					args: {
						bar_code: frm.doc.blank_bin,
					},
					freeze: true,
					callback: function (r) {
						if (r.status == "failed") {
							frappe.msgprint(r.message);
							frm.set_value("blank_bin", "");
						}
						else if(r.status == "success"){
							
							if (frm.doc.items && frm.doc.items.length>0) {
								frm.doc.items.map(res =>{
									if (res.bin_code == r.message.name){
										frappe.msgprint(`Scanned Bin <b>${frm.doc.blank_bin}</b> is already added.`);
										return
									}
								})
								frm.set_value("blank_bin", "");
								return
							}
							frm.set_df_property("bin_weight_kgs", "hidden", 0)
							frm.set_df_property("gross_weight_kgs", "hidden", 0)
							frm.set_df_property("net_weight_kgs", "hidden", 0)
							frm.set_value("available_qty", r.message.qty);
							frm.set_value("bin_code", r.message.name);
							frm.set_value("bin_name", r.message.asset_name);
							frm.set_value("bin_weight_kgs", r.message.bin_weight);
							frm.set_value("item", r.message.item);
							frm.set_value("compound_code", r.message.compound_code);
							frm.set_value("spp_batch_number", r.message.spp_batch_number);
							frm.set_value("batch_no", r.message.batch_no);
							frm.set_value("ibm_id", r.message.item_bin_mapping_id);
							$('button[data-fieldname="add"]').removeAttr("disabled");
							if(frm.doc.move_to_cut_bit_warehouse){
								$('button[data-fieldname="add"]').attr("disabled","disabled");
							}
						}
						else{
							frappe.msgprint("Something went wrong.");
						}
					}
				});	
		}
	},
	scan_cut_bit_batch(frm){
		if(frm.doc.scan_cut_bit_batch){
			if(frm.doc.blank_bin){
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_inward_entry.blank_bin_inward_entry.validate_cutbit_batch_barcode',
					args: {
						bar_code: frm.doc.scan_cut_bit_batch,
						compound:frm.doc.compound_code
					},
					freeze: true,
					callback: function (r) {
						if(r){
							if(r.status == "success"){
								frm.set_value("cut_bit_batch",r.message)
								$('button[data-fieldname="add"]').removeAttr("disabled");
							}
							else{
								frm.set_value("scan_cut_bit_batch","")
								frappe.msgprint(r.message)	
							}
						}
						else{
							frm.set_value("scan_cut_bit_batch","")
							frappe.msgprint("Not able to fetch batch details.Try again..!")
						}
					}
				})
			}
			else{
				frm.set_value("scan_cut_bit_batch","")
				frappe.msgprint("Please scan <b>Bin</b> before scan <b>Cut Bit Batch</b>..!")
			}
		}
	},
	"add":function(frm){
		if(!frm.doc.blank_bin || frm.doc.blank_bin == undefined){
			frappe.msgprint("Please scan the Bin.");
		}
		if(frm.doc.move_to_cut_bit_warehouse){
			if(!frm.doc.scan_cut_bit_batch  || frm.doc.scan_cut_bit_batch  == undefined){
				frappe.msgprint("Please scan the Cut Bit Batch.");
			}
		}
		if(!frm.doc.gross_weight_kgs || frm.doc.gross_weight_kgs == undefined){
			frappe.msgprint("Please enter the Gross Weight.");
		}
		else{
			var row = frappe.model.add_child(frm.doc, "Blank Bin Inward Item", "items");
			row.bin_code = frm.doc.bin_code;
			row.bin_name = frm.doc.bin_name;
    		row.bin_weight_kgs = frm.doc.bin_weight_kgs;
			row.item = frm.doc.item;
    		row.compound_code = frm.doc.compound_code;
			row.bin_gross_weight = frm.doc.gross_weight_kgs;
			row.bin_net_weight = frm.doc.net_weight_kgs;
			row.spp_batch_number = frm.doc.spp_batch_number;
			row.batch_no = frm.doc.batch_no;
			row.ibm_id = frm.doc.ibm_id;
			row.available_qty = frm.doc.available_qty;
			if(frm.doc.move_to_cut_bit_warehouse){
				row.cut_bit_batch = frm.doc.cut_bit_batch;
				frm.set_value("scan_cut_bit_batch","");
				frm.set_value("cut_bit_batch","");
			}
			frm.refresh_field('items');
			frm.set_value("available_qty", "");
			frm.set_value("bin_code","");
			frm.set_value("bin_name","");
    		frm.set_value("bin_weight_kgs","");
			frm.set_value("item", "");
			frm.set_value("compound_code", "");
			frm.set_value("gross_weight_kgs","");
    		frm.set_value("net_weight_kgs","");
			frm.set_value("blank_bin","");
			frm.set_value("spp_batch_number","");
			frm.set_value("batch_no","");
			frm.set_value("ibm_id","");
			frm.set_df_property("bin_weight_kgs", "hidden", 1)
			frm.set_df_property("gross_weight_kgs", "hidden", 1)
			frm.set_df_property("net_weight_kgs", "hidden", 1)
			$('button[data-fieldname="add"]').attr("disabled","disabled");
		}
	}
});
