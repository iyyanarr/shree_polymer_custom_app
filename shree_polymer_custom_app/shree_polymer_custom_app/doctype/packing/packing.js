// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Packing', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
		frm.trigger('hide_show_item')
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
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
	},
	refresh: function(frm) {
		frm.events.view_stock_entry(frm)
		frm.trigger('bin_datas')
		frm.trigger('hide_show_item')
		// frm.trigger('filter_custom_item_group')
		if(frm.doc.docstatus == 1){
			frm.set_df_property("scan_section","hidden",1)
		}
		if(!frm.doc.qty_kgs){
			frm.set_df_property("qty_kgs","hidden",1)
		}
		if(!frm.doc.qty_nos){
			frm.set_df_property("qty_nos","hidden",1)
		}
		if(frm.doc.packing_type){
			frm.set_df_property("packing_type","hidden",0)
		}
		if(frm.doc.item){
			frm.set_df_property("item","read_only",1)
		}
	},
	bin_datas(frm){
		if(frm.doc.customer_items){
			let item_uom = JSON.parse(frm.doc.customer_items)
			let items = []
			if(item_uom){
				item_uom.map(rs=>{
					items.push(rs.item_code)
				})
			}
			frm.bom__items = items
			frm.bom__items_uom = item_uom
		}
	},
	scan_lot_no(frm){
		frm.trigger('hide_show_item')
	},
	product_ref(frm){
		frm.trigger('hide_show_item')
	},
	hide_show_item(frm){
		if(!frm.doc.scan_lot_no && !frm.doc.items ){
			frm.set_df_property("item","hidden",1)
			frm.set_value("item","")
			refresh_field("item")
		}
		else{
			frm.set_df_property("item","hidden",0)
			frm.set_df_property("packing_type","hidden",0)
		}
		if(!frm.doc.available_qty){
			frm.set_df_property("available_qty","hidden",1)
		}
		else{
			frm.set_df_property("available_qty","hidden",0)
		}
		frm.set_df_property("qty_kgs","read_only",1)
	},
	filter_custom_item_group (frm){
		if(!frm.packing__group){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.get_customer_item_group',
				args: {},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
					}
					else if (r && r.status == "success") {
						frm.packing__group = r.message
						frm.trigger('apply_filter')
					}
					else {
						frappe.msgprint("Something went wrong api not responding..!");
					}
				}
			});
		}
		else{
			frm.trigger('apply_filter')
		}
	},
	apply_filter(frm){
		if(frm.bom__items){
			frm.set_query("item",() =>{
				return {
					"filters":{
						// "item_group" : frm.packing__group,
						"name" : ["in",frm.bom__items]
					}
				}
			})
		}
		if(frm.packing__types){
			frm.set_df_property("packing_type","read_only",0)
			frm.set_df_property('packing_type', 'options', frm.packing__types);
			frm.refresh_field('packing_type');
		}
	},
	"scan_lot_no": (frm) => {
		if (frm.doc.scan_lot_no && frm.doc.scan_lot_no != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.packing.packing.validate_lot_barcode',
				args: {
					batch_no: frm.doc.scan_lot_no,
					item:frm.doc.item
				},
				freeze: true,
				callback: function (r) {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_lot_no", "");
						frm.set_value("available_qty", "");
						frm.set_value("product_ref", "");
						frm.set_value("spp_batch_no", "");
						frm.set_value("batch_no", "")
						frm.set_value("qty_nos", 0)	
						frm.set_df_property("qty_nos", "hidden", 1)
						frm.set_value("qty_kgs", 0)	
						frm.set_df_property("qty_kgs", "hidden", 1)
					}
					else if (r && r.status == "success") {
						console.log(r.message)
						frm.set_value("available_qty",parseInt(r.message.qty_from_item_batch))
						refresh_field("available_qty")
						frm.total_nos = 0
						frm.total_kgs = 0
						frm.total_balance_nos = 0
						frm.total_balance_kgs = 0
						if (frm.doc.items && frm.doc.items.length>0) {
							frm.doc.items.map(res =>{
								if (res.lot_no == frm.doc.scan_lot_no){
									frm.total_nos += res.qty_nos
									frm.total_kgs += res.qty__kgs
								}
							})
							if (frm.doc.balance_lot_items && frm.doc.balance_lot_items.length>0) {
								frm.doc.balance_lot_items.map(res =>{
									if (res.lot_no == frm.doc.scan_lot_no){
										frm.total_balance_nos += res.qty_nos
										frm.total_balance_kgs += res.qty__kgs
									}
								})
							}
							frm.total_nos += frm.total_balance_nos
							frm.total_kgs += frm.total_balance_kgs
							if (parseInt(r.message.qty_from_item_batch) <= frm.total_nos){
								frappe.msgprint(`The all stock qty for the lot - <b>${frm.doc.scan_lot_no}</b> is consumed in this entry.`)
								frm.set_value("scan_lot_no", "");
								frm.set_value("product_ref", "");
								frm.set_value("spp_batch_no", "");
								frm.set_value("batch_no", "")
								frm.set_value("qty_nos", 0)
								frm.set_value("available_qty", "")	
								frm.set_df_property("qty_nos", "hidden", 1)
								frm.set_value("qty_kgs", 0)
								frm.set_df_property("qty_kgs", "hidden", 1)
								return
							}
							else{
								frm.set_value("available_qty",parseInt((r.message.qty_from_item_batch - frm.total_nos)))
								refresh_field("available_qty")
							}
						}
						frm.set_df_property("qty_nos", "hidden", 0)
						frm.set_df_property("qty_kgs", "hidden", 0)
						frm.set_value("product_ref", r.message.item_code)
						frm.set_value("spp_batch_no", r.message.spp_batch_number)
						frm.set_value("batch_no", r.message.batch_no)
						frm.set_value("warehouse", r.message.from_warehouse)
						// frm.set_value("qty_nos", r.message.qty)
						let items = []
						if(r.message.items){
							r.message.items.map(rs=>{
								items.push(rs.item_code)
							})
						}
						frm.bom__items = items
						frm.bom__items_uom = r.message.items
						frm.packing__types = r.message.packing_types
						frm.set_value("customer_items", JSON.stringify(r.message.items))
						frm.trigger('apply_filter')
						frm.trigger('item')
						frm.set_df_property("item","hidden",0)
					}
					else {
						frappe.msgprint("Something went wrong..!");
					}
				}
			});
		}
	},
	item(frm){
		if(frm.doc.item){
			let _lkg_eq_nos = 0.0
			frm.bom__items_uom.map(res =>{
				if(res.item_code == frm.doc.item){
					_lkg_eq_nos = res._1kg_eq_nos
				}
			})
			if (_lkg_eq_nos){
				// let available_qty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
				// let qty_nos = parseInt(available_qty_kgs * _lkg_eq_nos)
				let available_qty_kgs = frm.doc.available_qty /_lkg_eq_nos
				let qty_nos = Math.round(available_qty_kgs * _lkg_eq_nos)
				if(!qty_nos){
					frappe.msgprint(`The Available qty <b>${available_qty_kgs} kgs</b> not enough to convert into <b>No's</b>..!`)
				}
				else{
					frm.set_value("qty_kgs", available_qty_kgs)
					frm.set_value("qty_nos", qty_nos)
				}
			}
			else{
				frappe.msgprint(`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`)
				frm.set_value("qty_nos", "")
				frm.set_value("qty_kgs", "")
			}
		}
	},
	scan_balance_lot(frm){
		if(frm.doc.scan_balance_lot){
			if(frm.doc.items && frm.doc.items.length > 0){
				let match_found = false
				let matched_name = ""
				frm.doc.items.map(resp =>{
					if(resp.lot_no == frm.doc.scan_balance_lot){
						match_found = true
						matched_name = resp.name
					}
				})
				if(match_found){
					frm.set_value("balance_lot_child_id",matched_name)
					refresh_field('balance_lot_child_id')
				}
				else{
					frm.set_value("scan_balance_lot","")
					frappe.msgprint(`The scanned lot <b>${frm.doc.scan_balance_lot}</b> is not exists in the scanned lot items list..!`)
				}
			}
			else{
				frm.set_value("scan_balance_lot","")
				frappe.msgprint(`There is no <b>Lot Items</b> added.
				<br>Please scan and add some items before scan<b>Balance Lot</b>..!`)
			}
		}
	},
	balance_qty_kgs(frm){
		if(frm.doc.balance_qty_kgs){
			if(frm.doc.item){
				let _lkg_eq_nos = 0.0
				frm.bom__items_uom.map(res =>{
					if(res.item_code == frm.doc.item){
						_lkg_eq_nos = res._1kg_eq_nos
					}
				})
				if (_lkg_eq_nos){
					let exe_rec = locals["Packing Item"][frm.doc.balance_lot_child_id]
					let available_balance_qty_kgs = exe_rec.qty__kgs
					if(parseFloat(frm.doc.balance_qty_kgs) >= available_balance_qty_kgs){
						frappe.msgprint(`The entered qty <b>${frm.doc.balance_qty_kgs} kg's</b> can't be equal to (OR) greater than the available stock <b>${available_balance_qty_kgs.toFixed(3)} kg's</b>`)
						frm.set_value("balance_qty_kgs", "")
						frm.set_value("balance_qty_nos", "")
					}
					else{
						let ava_qty = available_balance_qty_kgs - frm.doc.balance_qty_kgs
						let qty_nos = Math.round(ava_qty * _lkg_eq_nos)
						if(!qty_nos || !ava_qty){
							if(!qty_nos){
								frm.set_value("balance_qty_kgs", "")
								frappe.msgprint("Please enter less <b>Balance Qty in kg's</b>.<br>The Lot qty (no's) can't be zero..!")
							}
							else{
								frm.set_value("balance_qty_kgs", "")
								frappe.msgprint("Please enter less <b>Balance Qty kg's</b>.<br>The Lot qty (kg's) can't be zero..!")
							}
						}
						else{
							frm.set_value("exe_lot_bal_qty_nos", qty_nos) 
							frm.set_value("exe_lot_bal_qty_kgs", ava_qty) 
							let balance_qty_nos = Math.round(frm.doc.balance_qty_kgs * _lkg_eq_nos)
							frm.set_value("balance_qty_nos", balance_qty_nos)
						}
					}
				}
				else{
					frappe.msgprint(`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`)
					frm.set_value("balance_qty_nos", "")
					frm.set_value("balance_qty_kgs", "")
				}
			}
			else{
				frappe.msgprint("Please select <b>Item to Produce</b> before enter qty..!")
				frm.set_value("balance_qty_kgs", "")
			}
		}
	},
	balance_qty_nos(frm){
		if(frm.doc.balance_qty_kgs && !frm.doc.balance_qty_nos){
			frm.set_value("balance_qty_kgs", "")
			frappe.msgprint("Please enter more <b>Balance Qty (kg's)</b>.<br>The <b>Balance qty (no's)</b> in Lot can't be zero..!")
		}
		else{
			if(frm.doc.balance_qty_nos){
				if(frm.doc.item){
					let _lkg_eq_nos = 0.0
					let _lno_eq_kgs = 0.0
					frm.bom__items_uom.map(res =>{
						if(res.item_code == frm.doc.item){
							_lkg_eq_nos = res._1kg_eq_nos
						}
					})
					if (_lkg_eq_nos){
						let exe_rec = locals["Packing Item"][frm.doc.balance_lot_child_id]
						let available_balance_qty_nos = exe_rec.qty_nos
						if(parseFloat(frm.doc.balance_qty_nos) >= available_balance_qty_nos){
							frappe.msgprint(`The entered qty <b>${frm.doc.balance_qty_nos} no's</b> can't be equal to (OR) greater than the available stock <b>${available_balance_qty_nos.toFixed(3)} no's</b>`)
							frm.set_value("balance_qty_kgs", "")
							frm.set_value("balance_qty_nos", "")
						}
						else{
							_lno_eq_kgs = 1 / _lkg_eq_nos
							let ava_qty = available_balance_qty_nos - frm.doc.balance_qty_nos
							let qty_kgs = parseFloat((ava_qty * _lno_eq_kgs).toFixed(3))
							if(!qty_kgs || !ava_qty){
								if(!qty_kgs){
									frm.set_value("balance_qty_nos", "")
									frappe.msgprint("Please enter less <b>Balance Qty in No's</b>.<br>The Lot qty (kg's) can't be zero..!")
								}
								else{
									frm.set_value("balance_qty_nos", "")
									frappe.msgprint("Please enter less <b>Balance Qty in No's</b>.<br>The Lot qty (kg's) can't be zero..!")
								}
							}
							else{
								frm.set_value("exe_lot_bal_qty_kgs", qty_kgs) 
								frm.set_value("exe_lot_bal_qty_nos", ava_qty) 
								let balance_qty_kgs = parseFloat((frm.doc.balance_qty_nos * _lno_eq_kgs).toFixed(3))
								frm.set_value("balance_qty_kgs", balance_qty_kgs)
							}
						}
					}
					else{
						frappe.msgprint(`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`)
						frm.set_value("balance_qty_nos", "")
						frm.set_value("balance_qty_kgs", "")
					}
				}
				else{
					frappe.msgprint("Please select <b>Item to Produce</b> before enter qty..!")
					frm.set_value("balance_qty_nos", "")
				}
			}
		}
	},
	"add": (frm) => {
		if (!frm.doc.scan_lot_no) {
			frappe.msgprint("Please Scan Lot before add.");
			return false;
		}
		if (!frm.doc.packing_type) {
			frappe.msgprint("Please Select Packing Type before add.");
			return false;
		}
		if (!frm.doc.item) {
			frappe.msgprint("Please Select Item before add.");
			return false;
		}
		if (!frm.doc.qty_nos) {
			frappe.msgprint("Please enter quantity in <b>Nos</b> before add.");
			return false;
		}
		if (!frm.doc.qty_kgs) {
			frappe.msgprint("Please enter quantity <b>Kgs</b> before add.");
			return false;
		}
		if(!frm.doc.available_qty){
			frappe.msgprint("Could not find the available stock.");
			return false;
		}
		else {
			if(frm.doc.available_qty <  frm.doc.qty_nos){
				frappe.msgprint(`The entered qty <b>${frm.doc.qty_nos}</b> is greater than the available stock <b>${frm.doc.available_qty}</b>`)
				frm.set_value("qty_nos", "")
				frm.set_value("qty_kgs", "")
			}
			else{
				frm.all_total_nos = frm.doc.qty_nos
				frm.all_total_kgs = frm.doc.qty_kgs
				if (frm.doc.items && frm.doc.items.length>0) {
					frm.doc.items.map(res =>{
						frm.all_total_nos += res.qty_nos
						frm.all_total_kgs +=  res.qty__kgs
					})
				}
				frm.set_value("total_qty_nos",parseInt(frm.all_total_nos))
				frm.set_value("total_qty_kgs",parseFloat(frm.all_total_kgs.toFixed(3)))
				refresh_field("total_qty_nos")
				refresh_field("total_qty_kgs")
				var row = frappe.model.add_child(frm.doc, "Packing Item", "items");
				row.lot_no = frm.doc.scan_lot_no
				row.product_ref = frm.doc.product_ref
				row.qty_nos = frm.doc.qty_nos
				row.qty__kgs = frm.doc.qty_kgs
				row.batch_no = frm.doc.batch_no
				row.spp_batch_no = frm.doc.spp_batch_no
				row.item = frm.doc.item
				row.packing_type = frm.doc.packing_type
				frm.refresh_field('items');
				frm.set_value("scan_lot_no", "");
				frm.set_value("product_ref", "");
				frm.set_value("spp_batch_no", "");
				frm.set_value("batch_no", "")
				frm.set_value("available_qty", "")
				// frm.set_value("packing_type", "")
				frm.set_value("qty_nos", 0)	
				frm.set_value("qty_kgs", 0)	
				// frm.set_value("item", "")
				frm.set_df_property("qty_nos", "hidden", 1)
				frm.set_df_property("qty_kgs", "hidden", 1)
				frm.trigger('hide_show_item')
				frm.set_df_property("packing_type","read_only",1)
				frm.set_df_property("item","read_only",1)
				// frm.set_df_property('packing_type', 'options', []);
				frm.refresh_field('packing_type');
			}
		}
	},
	"add_balance_lot": (frm) => {
		if (!frm.doc.scan_balance_lot) {
			frappe.msgprint("Please Scan Balance Lot before add.");
			return false;
		}
		if (!frm.doc.balance_qty_nos && frm.doc.uom == "Nos") {
			frappe.msgprint("Please enter balance qty before add..!");
			return false;
		}
		if (!frm.doc.balance_lot_child_id) {
			frappe.msgprint("Balance lot Child ID is missing.");
			return false;
		}
		if(!frm.doc.balance_qty_kgs && frm.doc.uom == "Kgs"){
			frappe.msgprint("Please enter balance qty before add..!");
			return false;
		}
		if(!frm.doc.exe_lot_bal_qty_kgs){
			frappe.msgprint("The <b<Balance Qty Kg's</b> in existing lot is missing...!");
			return false;
		}
		if(!frm.doc.exe_lot_bal_qty_nos){
			frappe.msgprint("The <b<Balance Qty No's</b> in existing lot is missing...!");
			return false;
		}
		else {
			let exe_rec = locals["Packing Item"][frm.doc.balance_lot_child_id]
			var row = frappe.model.add_child(frm.doc, "Packing Balance Lot", "balance_lot_items");
			row.lot_no = frm.doc.scan_balance_lot
			row.qty_nos = frm.doc.balance_qty_nos
			row.qty__kgs = frm.doc.balance_qty_kgs
			row.product_ref = exe_rec.product_ref
			row.batch_no = exe_rec.batch_no
			row.spp_batch_no = exe_rec.spp_batch_no
			row.item = exe_rec.item
			row.packing_type = exe_rec.packing_type
			frm.refresh_field('balance_lot_items');

			frm.all_total_nos = frm.doc.total_qty_nos ? frm.doc.total_qty_nos - frm.doc.balance_qty_nos : frm.doc.balance_qty_nos;
			frm.all_total_kgs = frm.doc.total_qty_kgs ? frm.doc.total_qty_kgs - frm.doc.balance_qty_kgs : frm.doc.balance_qty_kgs;
			frm.set_value("total_qty_nos",parseInt(frm.all_total_nos))
			frm.set_value("total_qty_kgs",parseFloat(frm.all_total_kgs.toFixed(3)))
			refresh_field("total_qty_nos")
			refresh_field("total_qty_kgs")
			
			frm.set_value('scan_balance_lot',"")
			frm.set_value('balance_lot_child_id',"")
			frm.set_value('balance_qty_kgs',"")
			frm.set_value('balance_qty_nos',"")
			exe_rec.qty_nos = frm.doc.exe_lot_bal_qty_nos
			exe_rec.qty__kgs = frm.doc.exe_lot_bal_qty_kgs
			frm.refresh_field('items');
			frm.set_value('exe_lot_bal_qty_nos',"")
			frm.set_value('exe_lot_bal_qty_kgs',"")
		}
	},
});









// balance_qty_kgs(frm){
// 	if(frm.doc.balance_qty_kgs){
// 		if(frm.doc.item){
// 			let _lkg_eq_nos = 0.0
// 			frm.bom__items_uom.map(res =>{
// 				if(res.item_code == frm.doc.item){
// 					_lkg_eq_nos = res._1kg_eq_nos
// 				}
// 			})
// 			if (_lkg_eq_nos){
// 				// let available_balance_qty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
// 				let available_balance_qty_kgs = frm.doc.available_qty /_lkg_eq_nos
// 				let available_bqty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
// 				if(parseFloat(frm.doc.balance_qty_kgs) >= available_bqty_kgs){
// 					frappe.msgprint(`The entered qty <b>${frm.doc.balance_qty_kgs} kg's</b> can't be equal to (OR) greater than the available stock <b>${available_balance_qty_kgs.toFixed(3)} kg's</b>`)
// 					frm.set_value("balance_qty_kgs", "")
// 					frm.set_value("balance_qty_nos", "")
// 				}
// 				else{
// 					let ava_qty = available_balance_qty_kgs - frm.doc.balance_qty_kgs
// 					// let qty_nos = parseInt(ava_qty * _lkg_eq_nos)
// 					let qty_nos = Math.round(ava_qty * _lkg_eq_nos)
// 					if(!qty_nos || !ava_qty){
// 						if(!qty_nos){
// 							frm.set_value("balance_qty_kgs", "")
// 							frappe.msgprint("Please enter less <b>Balance Qty in kg's</b>.<br>The Lot qty (no's) can't be zero..!")
// 						}
// 						else{
// 							frm.set_value("balance_qty_kgs", "")
// 							frappe.msgprint("Please enter less <b>Balance Qty kg's</b>.<br>The Lot qty (kg's) can't be zero..!")
// 						}
// 					}
// 					else{
// 						frm.set_value("qty_nos", qty_nos) 
// 						frm.set_value("qty_kgs", ava_qty) 
// 						// let balance_qty_nos = parseInt(frm.doc.balance_qty_kgs * _lkg_eq_nos)
// 						let balance_qty_nos = Math.round(frm.doc.balance_qty_kgs * _lkg_eq_nos)
// 						frm.set_value("balance_qty_nos", balance_qty_nos)
// 					}
// 				}
// 			}
// 			else{
// 				frappe.msgprint(`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`)
// 				frm.set_value("balance_qty_nos", "")
// 				frm.set_value("balance_qty_kgs", "")
// 			}
// 		}
// 		else{
// 			frappe.msgprint("Please select <b>Item to Produce</b> before enter qty..!")
// 			frm.set_value("balance_qty_kgs", "")
// 		}
// 	}
// },
// balance_qty_nos(frm){
// 	if(frm.doc.balance_qty_kgs && !frm.doc.balance_qty_nos){
// 		frm.set_value("balance_qty_kgs", "")
// 		frappe.msgprint("Please enter more <b>Balance Qty (kg's)</b>.<br>The <b>Balance qty (no's)</b> in Lot can't be zero..!")
// 	}
// },



// qty_kgs(frm){
	// 	if(frm.doc.qty_kgs){
	// 		if(frm.doc.item){
	// 			let _lkg_eq_nos = 0.0
	// 			frm.bom__items_uom.map(res =>{
	// 				if(res.item_code == frm.doc.item){
	// 					_lkg_eq_nos = res._1kg_eq_nos
	// 				}
	// 			})
	// 			if (_lkg_eq_nos){
	// 				let available_qty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
	// 				if(parseFloat(frm.doc.qty_kgs) > available_qty_kgs){
	// 					frappe.msgprint(`The entered qty <b>${frm.doc.qty_kgs} kg's</b> is greater than the available stock <b>${available_qty_kgs} kg's</b>`)
	// 					frm.set_value("qty_kgs", "")
	// 					frm.set_value("qty_nos", "")
	// 				}
	// 				else{
	// 					let qty_nos = parseInt(frm.doc.qty_kgs * _lkg_eq_nos)
	// 					frm.set_value("qty_nos", qty_nos)
	// 				}
	// 			}
	// 			else{
	// 				frappe.msgprint(`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`)
	// 				frm.set_value("qty_nos", "")
	// 				frm.set_value("qty_kgs", "")
	// 			}
	// 		}
	// 		else{
	// 			frappe.msgprint("Please select <b>Item to Produce</b> before enter qty..!")
	// 			frm.set_value("qty_kgs", "")
	// 		}
	// 	}
	// },
	// qty_nos(frm){
	// 	if(frm.doc.available_qty && frm.doc.qty_nos){
	// 		if(frm.doc.available_qty <  frm.doc.qty_nos){
	// 			frappe.msgprint(`The entered qty <b>${frm.doc.qty_nos} no's</b> is greater than the available stock <b>${frm.doc.available_qty} no's</b>`)
	// 			frm.set_value("qty_nos", "")
	// 			frm.set_value("qty_kgs", "")
	// 		}
	// 	}
	// },



	// balance_qty_kgs(frm){
	// 	if(frm.doc.balance_qty_kgs){
	// 		if(frm.doc.item){
	// 			let _lkg_eq_nos = 0.0
	// 			frm.bom__items_uom.map(res =>{
	// 				if(res.item_code == frm.doc.item){
	// 					_lkg_eq_nos = res._1kg_eq_nos
	// 				}
	// 			})
	// 			if (_lkg_eq_nos){
	// 				let available_balance_qty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
	// 				if(parseFloat(frm.doc.balance_qty_kgs) >= available_balance_qty_kgs){
	// 					frappe.msgprint(`The entered qty <b>${frm.doc.balance_qty_kgs} kg's</b> can't be equal to (OR) greater than the available stock <b>${available_balance_qty_kgs} kg's</b>`)
	// 					frm.set_value("balance_qty_kgs", "")
	// 					frm.set_value("balance_qty_nos", "")
	// 				}
	// 				else{
	// 					// let res_ = frm.events.calculate_no_to_kgs(frm)
	// 					// if(res_ && res_.status == "success"){
	// 						let ava_qty = available_balance_qty_kgs - frm.doc.balance_qty_kgs
	// 						// let qty_nos = parseInt(ava_qty * _lkg_eq_nos)
	// 						let qty_nos = ava_qty * _lkg_eq_nos
	// 						if(!qty_nos || !ava_qty){
	// 							if(!qty_nos){
	// 								frm.set_value("balance_qty_kgs", "")
	// 								frappe.msgprint("Please enter less <b>Balance Qty in kg's</b>.<br>The Lot qty (no's) can't be zero..!")
	// 							}
	// 							else{
	// 								frm.set_value("balance_qty_kgs", "")
	// 								frappe.msgprint("Please enter less <b>Balance Qty kg's</b>.<br>The Lot qty (kg's) can't be zero..!")
	// 							}
	// 						}
	// 						else{
	// 							frm.set_value("qty_nos", qty_nos) 
	// 							frm.set_value("qty_kgs", ava_qty) 
	// 							// let balance_qty_nos = parseInt(frm.doc.balance_qty_kgs * _lkg_eq_nos)
	// 							let balance_qty_nos = frm.doc.balance_qty_kgs * _lkg_eq_nos
	// 							frm.set_value("balance_qty_nos", balance_qty_nos)
	// 						}
	// 					// }
	// 					// else{
	// 					// 	frappe.msgprint(res_.message)
	// 					// }
	// 				}
	// 			}
	// 			else{
	// 				frappe.msgprint(`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`)
	// 				frm.set_value("balance_qty_nos", "")
	// 				frm.set_value("balance_qty_kgs", "")
	// 			}
	// 		}
	// 		else{
	// 			frappe.msgprint("Please select <b>Item to Produce</b> before enter qty..!")
	// 			frm.set_value("balance_qty_kgs", "")
	// 		}
	// 	}
	// },
	// balance_qty_nos(frm){
	// 	if(frm.doc.balance_qty_kgs && !frm.doc.balance_qty_nos){
	// 		frm.set_value("balance_qty_kgs", "")
	// 		frappe.msgprint("Please enter more <b>Balance Qty (kg's)</b>.<br>The <b>Balance qty (no's)</b> in Lot can't be zero..!")
	// 	}
	// },
	// calculate_no_to_kgs(frm){
	// 	if(frm.doc.item){
	// 		let _lkg_eq_nos = 0.0
	// 		frm.bom__items_uom.map(res =>{
	// 			if(res.item_code == frm.doc.item){
	// 				_lkg_eq_nos = res._1kg_eq_nos
	// 			}
	// 		})
	// 		if (_lkg_eq_nos){
	// 			let available_qty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
	// 			let qty_nos = parseInt(available_qty_kgs * _lkg_eq_nos)
	// 			if(!qty_nos){
	// 				return {"status":"failed","message":`The Available qty <b>${available_qty_kgs} kgs</b> not enough to convert into <b>No's</b>..!`}
	// 			}
	// 			else{
	// 				return {"status":"success","message":available_qty_kgs}
	// 			}
	// 		}
	// 		else{
	// 			return {"status":"failed","message":`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`}
	// 		}
	// 	}
	// },


	// calculate_no_to_kgs(frm){
	// 	if(frm.doc.item){
	// 		let _lkg_eq_nos = 0.0
	// 		frm.bom__items_uom.map(res =>{
	// 			if(res.item_code == frm.doc.item){
	// 				_lkg_eq_nos = res._1kg_eq_nos
	// 			}
	// 		})
	// 		if (_lkg_eq_nos){
	// 			let available_qty_kgs =  parseFloat((frm.doc.available_qty /_lkg_eq_nos).toFixed(3))
	// 			let qty_nos = parseInt(available_qty_kgs * _lkg_eq_nos)
	// 			if(!qty_nos){
	// 				return {"status":"failed","message":`The Available qty <b>${available_qty_kgs} kgs</b> not enough to convert into <b>No's</b>..!`}
	// 			}
	// 			else{
	// 				return {"status":"success","message":available_qty_kgs}
	// 			}
	// 		}
	// 		else{
	// 			return {"status":"failed","message":`The <b>UOM</b> conversion factor for the item - <b>${frm.doc.item}</b> is not found..!`}
	// 		}
	// 	}
	// },