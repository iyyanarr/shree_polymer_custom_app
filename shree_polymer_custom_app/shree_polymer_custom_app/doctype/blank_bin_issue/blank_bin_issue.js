// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blank Bin Issue', {
	refresh: function(frm) {
		// frm.set_df_property("qty_to_manufacture", "hidden", 1)
		// frm.set_df_property("bin_weight", "hidden", 1)
		// frm.set_df_property("qty", "hidden", 1)
		// if(frm.doc.docstatus == 1){
		// 	frm.set_df_property("scan_section", "hidden", 1)
		// }
		if(frm.doc.docstatus == 0){
		frm.trigger('add_html')
		}
	},
	"scan_production_lot": (frm) => {
		if (frm.doc.scan_production_lot && frm.doc.scan_production_lot != undefined) {
			frm.events.validate_add(frm,"scan_production_lot")
		}
	},
	"scan_bin": (frm) => {
		if (frm.doc.scan_bin && frm.doc.scan_bin != undefined) {
			frm.events.validate_add(frm,"scan_bin")
		}
	},
	"add_values":(frm)=>{
		if (!frm.doc.job_card || frm.doc.job_card == undefined) {
			frappe.msgprint("Please scan the job card.");
			return
		}
		if (!frm.doc.bin || frm.doc.bin == undefined) {
			frappe.msgprint("Please scan the bin.");
			return
		}
		if (frm.doc.job_card && frm.doc.bin) {
			var row = frappe.model.add_child(frm.doc, "Blank Bin Issue Item", "items");
			row.job_card = frm.doc.job_card
			row.production_item = frm.doc.production_item
			row.qty_to_manufacture = frm.doc.qty_to_manufacture
			row.press = frm.doc.press
			row.mould = frm.doc.mould
			row.bin_weight = frm.doc.bin_weight
			row.compound = frm.doc.compound
			row.spp_batch_number = frm.doc.spp_batch_number
			row.qty = frm.doc.qty
			row.asset_name = frm.doc.asset_name
			row.bin = frm.doc.bin;
			frm.refresh_field('items');
		}
		frappe.dom.unfreeze()
	},
	"append_values":(frm) =>{
		if(frm.doc.scan_bin && frm.doc.scan_production_lot){
			frappe.dom.freeze()
			setTimeout(()=>{
				frm.events.add_values(frm)
			},1000)
		}
	},
	"add_html":(frm)=>{
		let wrapper = $(frm.get_field('add_html').wrapper).empty();
		let table_html = $(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);
		$(frm.get_field('add_html').wrapper).find('.add-row').on('click', function () {
			if(!frm.doc.job_card || frm.doc.job_card == undefined){
			frappe.msgprint("Please scan the job card.");
			return
			}
			if(!frm.doc.bin || frm.doc.bin == undefined){
				frappe.msgprint("Please scan the bin.");
				return
			}
			if(frm.doc.job_card && frm.doc.bin){
				var row = frappe.model.add_child(frm.doc, "Blank Bin Issue Item", "items");
				// Job card
				row.job_card = frm.doc.job_card
				row.production_item = frm.doc.production_item
				row.qty_to_manufacture = frm.doc.qty_to_manufacture
				row.press = frm.doc.press
				row.mould = frm.doc.mould
				row.bin_weight = frm.doc.bin_weight
				row.compound = frm.doc.compound
				row.spp_batch_number = frm.doc.spp_batch_number
				row.qty = frm.doc.qty
				row.asset_name = frm.doc.asset_name
				// end
	    		row.bin = frm.doc.bin;
				frm.refresh_field('items');
				// Job card
				frm.set_value("job_card","");
				frm.set_value("production_item", "");
				frm.set_value("qty_to_manufacture", "");
				frm.set_value("asset_name", "");
				frm.set_value("press", "");
				frm.set_value("mould", "");
				// end
				frm.set_value("compound","");
				frm.set_value("spp_batch_number","");
				frm.set_value("qty","");
	    		frm.set_value("bin","");
				frm.set_value("bin_weight", "");
				frm.set_value("scan_production_lot","");
	    		frm.set_value("scan_bin","");
	    		$(frm.get_field('add_html').wrapper).find('.add-row').attr("disabled","disabled")
			}
		});
	},
	// "add":(frm) =>{

	// 	if(!frm.doc.job_card || frm.doc.job_card == undefined){
	// 		frappe.msgprint("Please scan the job card.");
	// 		return
	// 	}
	// 	if(!frm.doc.bin || frm.doc.bin == undefined){
	// 		frappe.msgprint("Please scan the bin.");
	// 		return
	// 	}
	// 	if(frm.doc.job_card && frm.doc.bin){
	// 		var row = frappe.model.add_child(frm.doc, "Blank Bin Issue Item", "items");
	// 		row.job_card = frm.doc.job_card;
    // 		row.bin = frm.doc.bin;
	// 		frm.refresh_field('items');
	// 		frm.set_value("job_card","");
    // 		frm.set_value("bin","");
	// 		frm.set_value("bin_weight", "");
	// 		frm.set_value("scan_production_lot","");
    // 		frm.set_value("scan_bin","");
			

	// 	}
	// },
	validate_add:(frm,type_of_scan) =>{
		if(type_of_scan == "scan_production_lot"){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_issue.blank_bin_issue.validate_blank_issue_barcode',
				args: {
					barcode: frm.doc.scan_production_lot,
					scan_type:"scan_production_lot",
					docname:frm.doc.name 
				},
				freeze: true,
				callback: function (r) {
					if (r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_production_lot", "");
					}
					else if(r.status == "success"){
						if (frm.doc.items && frm.doc.items.length>0 && frm.doc.bin) {
							let flag = false
							frm.doc.items.map(res =>{
								if (res.job_card == r.message && res.bin==frm.doc.bin){
									frm.set_value("scan_production_lot", "");
									flag = true
									frappe.validated = false
									frappe.msgprint(`Scanned job card <b>${frm.doc.scan_production_lot}</b> already added.`);
									return
								}
							})
							if(flag){
								return
							}
						}
						frm.set_value("scan_production_lot", frm.doc.scan_production_lot.toUpperCase());
						frm.set_value("job_card", r.message.name);
						frm.set_value("production_item", r.message.production_item);
						frm.set_value("qty_to_manufacture", r.message.for_quantity);
						frm.set_value("press", r.message.workstation);
						frm.set_value("mould", r.message.mould_reference);
						frm.set_df_property("qty_to_manufacture", "hidden", 0)
						frm.events.append_values(frm)
						frm.set_value("scan_bin", "");
					}
					else{
						frappe.msgprint("Something went wrong.");
					}
				}
			});	
		}
		else{
			if(frm.doc.scan_production_lot){
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.blank_bin_issue.blank_bin_issue.validate_blank_issue_barcode',
					args: {
						barcode: frm.doc.scan_bin,
						scan_type:"scan_bin",
						docname:frm.doc.name,
						production_item:frm.doc.production_item
					},
					freeze: true,
					callback: function (r) {
						if (r.status == "failed") {
							frappe.msgprint(r.message);
							frm.set_value("scan_bin", "");
						}
						else if(r.status == "success"){
							if (frm.doc.items && frm.doc.items.length>0 && frm.doc.job_card) {
								let flag = false
								frm.doc.items.map(res =>{
									// if (res.bin == r.message)
									if (res.job_card ==frm.doc.job_card && res.bin==r.message)
									{
										flag = true
										frm.set_value("scan_bin", "");
										frappe.validated = false
										frappe.msgprint(`Scanned bin <b>${frm.doc.scan_bin}</b> already added.`);
										return
									}
								})
								if(flag){
									return
								}
							}
							frm.set_value("scan_bin", frm.doc.scan_bin.toUpperCase());
							frm.set_value("bin", r.message.name);
							frm.set_value("bin_weight", r.message.bin_weight);
							frm.set_value("compound", r.message.compound);
							frm.set_value("spp_batch_number", r.message.spp_batch_number);
							frm.set_value("qty", r.message.qty);
							frm.set_value("asset_name", r.message.asset_name);
							frm.set_df_property("bin_weight", "hidden", 0)
							frm.set_df_property("qty", "hidden", 0)
							if(frm.doc.job_card){
								$(frm.get_field('add_html').wrapper).find('.add-row').removeAttr("disabled")
							}
							frm.events.append_values(frm)
						}
						else{
							frappe.msgprint("Something went wrong.");
						}
					}
				});	
			}
			else{
				frm.set_value("scan_bin", "");
				frappe.msgprint("Please scan <b>Job Card</b> before scan <b>Bin</b>..!")
			}

		}
	}
});
