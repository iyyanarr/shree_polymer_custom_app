// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deflashing Receipt Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.stock_entry_reference && !frm.doc.scrap_stock_entry_ref){
			frm.add_custom_button(__("View Stock Entry"), function(){
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			  });
		}
		else if(frm.doc.stock_entry_reference && frm.doc.scrap_stock_entry_ref){
			frm.add_custom_button(__("View Manufacturing Entry"), function(){
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			  },__("View Stock Entry"));
			  frm.add_custom_button(__("View Scrap Entry"), function(){
				frappe.set_route("Form", "Stock Entry", frm.doc.scrap_stock_entry_ref);
			  },__("View Stock Entry"));
		}
		else{
			frm.remove_custom_button('View Stock Entry');
		}
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	refresh: function(frm) {
		frm.events.view_stock_entry(frm)
		if(!frm.doc.scrap_weight && frm.doc.docstatus == 1){
			frm.set_df_property("scrap_weight", "hidden", 1)
		}
		
		if(!frm.doc.qty && frm.doc.docstatus == 1){
			frm.set_df_property("qty", "hidden", 1)
		}
		
		if(!frm.doc.product_weight && frm.doc.docstatus == 1){
			frm.set_df_property("product_weight", "hidden", 1)
		}
	},
	"scan_lot_number": (frm) => {
		if ((frm.doc.scan_lot_number && frm.doc.scan_lot_number != undefined) && (frm.doc.scan_deflashing_vendor && frm.doc.scan_deflashing_vendor != undefined)){
			frm.trigger("validate_fetch_info")
		}
	},
	"scan_deflashing_vendor": (frm) => {
		if ((frm.doc.scan_deflashing_vendor && frm.doc.scan_deflashing_vendor != undefined) && (frm.doc.scan_lot_number && frm.doc.scan_lot_number != undefined)){
			frm.trigger("validate_fetch_info")
		}
	},
	"validate_fetch_info":(frm) =>{
		frappe.call({
			method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.validate_lot_barcode',
			args: {
				bar_code: frm.doc.scan_lot_number,
				// warehouse
					w__barcode:frm.doc.scan_deflashing_vendor
				// end
			},
			freeze: true,
			callback: function (r) {
				if (r && r.status == "failed") {
					frappe.msgprint(r.message);
					if (r.error_type){
						frm.set_value("scan_deflashing_vendor", "");
						frm.set_value("from_warehouse_id", "")
						frm.set_value("warehouse", "")
					}
					else{
						frm.set_value("scan_lot_number", "");
						frm.set_value("batch_no", "")
						frm.set_value("spp_batch_no", "")
						// frm.set_value("job_card", "")
						frm.set_value("item", "")
						frm.set_value("qty", "")
						frm.set_value("lot_number", "")
						frm.set_value("product_weight", "")
						frm.set_value("scrap_weight", "")
						frm.set_df_property("qty", "hidden", 1)
					}
				}
				else if (r && r.status == "success") {
					if (frm.doc.items && frm.doc.items.length>0) {
						let flag = false
						frm.doc.items.map(res =>{
							if (res.lot_number == frm.doc.scan_lot_number){
								frm.set_value("scan_lot_number", "");
								flag = true
								frappe.validated = false
								frappe.msgprint(`Scanned lot <b>${frm.doc.scan_lot_number}</b> already added.`);
								return
							}
						})
						if(flag){
							return
						}
					}
					frm.set_value("scan_deflashing_vendor", frm.doc.scan_deflashing_vendor.toUpperCase())
					frm.set_value("scan_lot_number", frm.doc.scan_lot_number.toUpperCase())
					frm.set_df_property("qty", "hidden", 0)
					frm.set_value("batch_no", r.batch_no)
					frm.set_value("spp_batch_no", r.spp_batch_number)
					// frm.set_value("job_card", r.job_card?r.job_card:'')
					frm.set_value("item", r.item)
					frm.set_value("qty", r.qty)
					frm.set_value("lot_number", frm.doc.scan_lot_number)
					frm.set_value("from_warehouse_id", r.from_warehouse)
					frm.set_df_property("scrap_weight", "hidden", 0)
					frm.set_df_property("product_weight", "hidden", 0)
					frm.set_value("warehouse", r.warehouse_name)
				}
				else {
					frappe.msgprint("Something went wrong.");
				}
			}
		});
	}
});


// Back up


// "product_weight":(frm) =>{
	// 	let product_weight_g = parseFloat(frm.doc.product_weight)
	// 	let qty_g = parseFloat(frm.doc.qty)
	// 	if(product_weight_g && !(product_weight_g > qty_g)){
	// 		let scrap_weight = qty_g - product_weight_g
	// 		frm.set_value("scrap_weight",scrap_weight)
	// 	}
	// 	else if(product_weight_g && (product_weight_g > qty_g)){
	// 		frappe.msgprint("The <b>Product Weight</b> can't be grater than <b>Available Stock</b>");
	// 		frm.set_value("product_weight", 0);
	// 		refresh_field("product_weight")
	// 		return
	// 	}
	// 	frm.trigger("validate_weight")
	// },
	// "scrap_weight":(frm) =>{
	// 	let scrap_weight_g = parseFloat(frm.doc.scrap_weight)
	// 	let qty_g = parseFloat(frm.doc.qty)
	// 	if(scrap_weight_g && !(scrap_weight_g > qty_g)){
	// 		let product_weight = qty_g - scrap_weight_g
	// 		frm.set_value("product_weight",product_weight)
	// 	}
	// 	else if(scrap_weight_g && (scrap_weight_g > qty_g)){
	// 		frappe.msgprint("The <b>Scrap Weight</b> can't be grater than <b>Available Stock</b>");
	// 		frm.set_value("scrap_weight", 0)
	// 		refresh_field("scrap_weight")
	// 		return
	// 	}
	// 	frm.trigger("validate_weight")
	// },
	// "validate_weight":(frm) =>{
	// 	if(frm.doc.product_weight && frm.doc.scrap_weight && frm.doc.qty){
	// 		let product_weight_g = parseFloat(frm.doc.product_weight)
	// 		let scrap_weight_g = parseFloat(frm.doc.scrap_weight)
	// 		let qty_g = parseFloat(frm.doc.qty)
	// 		if((product_weight_g+scrap_weight_g)>qty_g){
	// 			frappe.msgprint("The <b>Product Weight and Scrap Weight</b> can't be grater than <b>Available Stock</b>");
	// 			frm.set_value("product_weight", "");
	// 			frm.set_value("scrap_weight", "")
	// 			return
	// 		}
	// 	}
	// },


	// "add": function (frm) {
	// 	if (!frm.doc.scan_lot_number || frm.doc.scan_lot_number == undefined) {
	// 		frappe.msgprint("Lot no is missing.");
	// 		return
	// 	}
	// 	if (!frm.doc.scan_deflashing_vendor || frm.doc.scan_deflashing_vendor == undefined) {
	// 		frappe.msgprint("Deflashing Vendor code is missing.");
	// 		return
	// 	}
	// 	if (!frm.doc.product_weight || frm.doc.product_weight == undefined) {
	// 		frappe.msgprint("Please enter the product weight.");
	// 		return
	// 	}
	// 	if (!frm.doc.scrap_weight || frm.doc.scrap_weight == undefined) {
	// 		frappe.msgprint("Please enter the scrap weight.");
	// 		return
	// 	}
	// 	if(((parseFloat(frm.doc.product_weight)+parseFloat(frm.doc.scrap_weight)))>(parseFloat(frm.doc.qty))){
	// 		frappe.msgprint("The <b>Product Weight and Scrap Weight</b> can't be grater than <b>Available Stock</b>");
	// 		return
	// 	}
	// 	else {
	// 		var row = frappe.model.add_child(frm.doc, "Deflashing Receipt Entry Item", "items");
	// 		row.lot_number = frm.doc.lot_number;
	// 		row.batch_no = frm.doc.batch_no;
	// 		row.spp_batch_no = frm.doc.spp_batch_no;
	// 		row.job_card = frm.doc.job_card;
	// 		row.warehouse_code = frm.doc.scan_deflashing_vendor;
	// 		row.item = frm.doc.item;
	// 		row.qty = frm.doc.qty;
	// 		row.warehouse = frm.doc.warehouse;
	// 		row.warehouse_id = frm.doc.warehouse_id;
	// 		row.product_weight = frm.doc.product_weight;
	// 		row.scrap_weight = frm.doc.scrap_weight;
	// 		row.from_warehouse_id = frm.doc.from_warehouse_id;
	// 		frm.set_df_property("qty", "hidden", 1)
	// 		frm.refresh_field('items');
	// 		frm.set_value("scan_deflashing_vendor", "");
	// 		frm.set_value("scan_lot_number", "");
	// 		frm.set_value("batch_no", "")
	// 		frm.set_value("spp_batch_no", "")
	// 		frm.set_value("job_card", "")
	// 		frm.set_value("item", "")
	// 		frm.set_value("qty", "")
	// 		frm.set_value("lot_number", "")
	// 		frm.set_value("warehouse", "")
	// 		frm.set_value("warehouse_id", "")
	// 		frm.set_value("product_weight", "")
	// 		frm.set_value("scrap_weight", "")
	// 		frm.set_value("from_warehouse_id", "")
	// 		frm.set_df_property("scrap_weight", "hidden", 1)
	// 		frm.set_df_property("product_weight", "hidden", 1)	
	// 	}
	// }




	// 	frappe.call({
		// 		method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_receipt_entry.deflashing_receipt_entry.validate_warehouse',
		// 		args: {
		// 			bar_code: frm.doc.scan_deflashing_vendor
		// 		},
		// 		freeze: true,
		// 		callback: function (r) {
		// 			if (r && r.status == "failed") {
		// 				frappe.msgprint(r.message);
		// 				frm.set_value("scan_deflashing_vendor", "");
		// 				frm.set_value("warehouse", "")
		// 				frm.set_value("warehouse_id", "")
		// 			}
		// 			else if (r && r.status == "success") {
		// 				frm.set_value("warehouse", r.warehouse_name)
		// 				frm.set_value("warehouse_id", r.name)
		// 			}
		// 			else {
		// 				frappe.msgprint("Something went wrong.");
		// 			}
		// 		}
		// 	});