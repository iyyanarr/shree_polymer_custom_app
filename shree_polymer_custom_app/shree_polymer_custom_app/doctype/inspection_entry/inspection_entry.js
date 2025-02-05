// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inspection Entry', {
	total_inspected_qty_nos(frm){
		if(frm.doc.total_inspected_qty_nos){
			if(frm.doc.uom == "Nos"){
				if(parseFloat(frm.doc.total_inspected_qty_nos) > parseFloat(frm.doc.available_qty_nos)){
					frm.set_value("total_inspected_qty_nos","")
					frappe.msgprint(`Total <b>Inspected Qty</b> can't be greater than <b>Available Qty</b>`)
				}
			}
		}
	},
	total_inspected_qty_kgs(frm){
		if(frm.doc.total_inspected_qty_kgs){
			if(frm.doc.uom == "Kgs"){
				if(parseFloat(frm.doc.total_inspected_qty_kgs) > parseFloat(frm.doc.available_qty_kgs)){
					frm.set_value("total_inspected_qty_kgs","")
					frappe.msgprint(`Total <b>Inspected Qty</b> can't be greater than <b>Available Qty</b>`)
				}
				else{
					let qty_nos = Math.round(parseFloat(frm.doc.total_inspected_qty_kgs) * parseFloat(frm.doc.one_kg_equal_nos))
					frm.set_value("total_inspected_qty_nos",qty_nos)
				}	
			}
		}
	},
	bind_rejections(frm){
		frm.addtional_rejections = [{"type_of_defect":"TOOL MARK"},
									{"type_of_defect":"BONDING FALUIRE"},
									{"type_of_defect":"THREAD"},
									{"type_of_defect":"OVER TRIM"},
									{"type_of_defect":"MOULD DAMAGE"},
									{"type_of_defect":"WOOD PARTICLE"},
									{"type_of_defect":"WASHER VISIBLE"},
									{"type_of_defect":"DISPERS PROBLEM"},
									{"type_of_defect":"THK UNDERSIZ"},
									{"type_of_defect":"THK OVERSIZE"},
									{"type_of_defect":"ID UNDERSIZ"},
									{"type_of_defect":"ID OVERSIZE"},
									{"type_of_defect":"OD UNDERSIZ"},
									{"type_of_defect":"OD OVERSIZE"},
									{"type_of_defect":"IMPRESSION MARK"},
									{"type_of_defect":"WELD LINE"},
									{"type_of_defect":"BEND"},
									{"type_of_defect":"PIN HOLE"},
									{"type_of_defect":"BACKRIND"},
									{"type_of_defect":"BONDING BUBBLE"},
									{"type_of_defect":"PARTING LINE CUTMARK"},
									{"type_of_defect":"MOULD RUST "},
									{"type_of_defect":"STAIN ISSUE "},
									{"type_of_defect":"STRETCH TEST "}]
	},
	'onload_post_render': function(frm) {
			let html = `<datalist id="suggestion_list">`
			frm.addtional_rejections.map(res =>{
				html += ` <option value="${res.type_of_defect}">${res.type_of_defect}</option>`
			})
			html += `</datalist>`
			frm.fields_dict.items.grid.wrapper.on('mouseenter click', 'input[data-fieldname="type_of_defect"]', function(e) {
				$(`input[data-fieldname="type_of_defect"]`).attr("list","suggestion_list")
				$(`input[data-fieldname="type_of_defect"]`).html(html)
			})
	},
	update_inspection_types(frm){
		if(frm.doc.docstatus == 0 && frm.doc.items){
			let balance_empty_fields = 42 - frm.doc.items.length
			let bal_empty_field = [...Array(balance_empty_fields).keys()]
			bal_empty_field.map(resp =>{
				frm.add_child("items", {type_of_defect:""})
			})
			refresh_field('items')
			frm.doc.items.map((res,idx) => {
				idx = idx + 1 
				if (idx > 37){
					var grid_row = cur_frm.fields_dict['items'].grid.grid_rows_by_docname[res.name],
					field = frappe.utils.filter_dict(grid_row.docfields, { fieldname: "type_of_defect" })[0];
					field.fieldtype = "Data"
					field.read_only = 0
				}
			})
			refresh_field('items')
		}
		frm.get_field("items").grid.cannot_add_rows = true;
	},
	timeline_refresh: frm => {
		frm.events.view_stock_entry(frm)
		// frm.events.hide_show_specification_section(frm)
	},
	view_stock_entry: (frm) => {
		frm.removes_rejections = []
		if (frm.doc.stock_entry_reference) {
			frm.add_custom_button(__("View Stock Entry"), function () {
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			});
		}
		else {
			frm.remove_custom_button('View Stock Entry');
		}
		if (frm.doc.vs_pdir_stock_entry_ref) {
			frm.add_custom_button(__("View F/G Stock Entry"), function () {
				frappe.set_route("Form", "Stock Entry", frm.doc.vs_pdir_stock_entry_ref);
			});
		}
		else {
			frm.remove_custom_button('View F/G Stock Entry');
		}
		frm.events.view_wo_jc(frm)
		// frm.events.hide_show_specification_section(frm)
		if (!frm.doc.posting_date) {
			frm.set_value('posting_date', frappe.datetime.now_date())
			refresh_field('posting_date')
		}
		frm.events.bind_rejections(frm)
	},
	hide_show_specification_section(frm) {
		if (frm.doc.inspection_type == "Final Visual Inspection" || frm.doc.inspection_type == "PDIR") {
			frappe.set_df_property("specification_section", "hidden", 0)
			frappe.set_df_property("specification_section", "reqd", 1)
		}
		else {
			frappe.set_df_property("specification_section", "reqd", 0)
			frappe.set_df_property("specification_section", "hidden", 1)
		}
	},
	view_wo_jc(frm) {
		if (frm.doc.lot_no) {
			// if (!has_common(frappe.user_roles, ['Line Inspector','Lot Inspector','Incoming Inspector','Packer']) || frappe.session.user == "Administrator") {
				frappe.db.get_value('Job Card', { batch_code: frm.doc.lot_no }, ['name', 'work_order'])
					.then(r => {
						if (r.message.name) {
							frm.add_custom_button("View Job Card", () => {
								frappe.set_route("Form", "Job Card", r.message.name)
							})
						}
						if (r.message.work_order) {
							frm.add_custom_button("View Work Order", () => {
								frappe.set_route("Form", "Work Order", r.message.work_order)
							})
						}
					})
			// }
		}
	},
	check_role_assign_opts(frm){
		let ins_opts = []
		if (has_common(frappe.user_roles, ['Line Inspector']) && frappe.session.user!="Administrator") {
			ins_opts.push('Line Inspection')
	    }
		if (has_common(frappe.user_roles, ['Lot Inspector']) && frappe.session.user!="Administrator") {
			ins_opts.push('Lot Inspection')
	    }
		if (has_common(frappe.user_roles, ['Incoming Inspector']) && frappe.session.user!="Administrator") {
			ins_opts.push("Incoming Inspection")
	    }
		if (has_common(frappe.user_roles, ['Packer','U1 Supervisor']) && frappe.session.user!="Administrator") {
			ins_opts.push("Final Visual Inspection")
	    }
		if(ins_opts && ins_opts.length > 0){
			set_field_options("inspection_type", ins_opts)
		}
	},
	validate(frm){
		if(frm.removes_rejections){
			let found = false
			let removes_rejections = []
			let alert_removes_rejections = []
			frm.defect__arry_list = [ "FLOW-(FL)", 
								 "BUBBLE-(BU) / BLISTER-(BL)", 
								 "CUTMARK-(CU)",
								 "DEFLASH-(DF)", 
								 "RIB", 
								 "FOREIGN PARTICLE-(FP)",
								 "UNDER FILL-( UF )",
								 "DIPRESSION-(DP)", 
								 "UNDER CURE-(UC)", 
								 "SURFACE DEFECT-(SD)",
								 "OVER CURE-(OC) /FAST CURE",
								 "BURST / TEAR", 
								 "BLACK MARK",
								]
			frm.removes_rejections.map(res =>{
				if(frm.defect__arry_list.includes(res)){
					removes_rejections.push({"type_of_defect": res})
					alert_removes_rejections.push(res)
					found = true
				}
			})
			if(found){
				for (let i = 0; i < removes_rejections.length; i++) {
					frm.add_child("items", removes_rejections[i])
				}
				refresh_field('items')
				frappe.validated = false
				frappe.msgprint(`Default <b>Rejection Types - ${alert_removes_rejections.join(',')}</b> can't be delete.`)
			}
			frm.removes_rejections = []
		}
	},
	refresh: (frm) => {
		frm.events.check_role_assign_opts(frm)
		frm.events.view_stock_entry(frm)
		if (frm.doc.docstatus == 1) {
			// frm.set_df_property("scan_production_lot", "hidden", 1)
			frm.set_df_property("type_of_defect", "hidden", 1)
			frm.set_df_property("rejected_qty", "hidden", 1)
			frm.set_df_property("add", "hidden", 1)
		}

		if (frm.doc.inspection_type && (frm.doc.inspection_type == "Lot Inspection" || frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection")) {
			frm.set_df_property("inspected_qty_nos", "read_only", 0)
			frm.set_df_property("inspected_qty_nos", "hidden", 0)
		}
		else {
			frm.set_df_property("inspected_qty_nos", "read_only", 1)
			frm.set_df_property("inspected_qty_nos", "hidden", 1)
		}

	},
	"inspection_type": frm => {
		if (frm.doc.inspection_type && (frm.doc.inspection_type == "Lot Inspection" || frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection")) {
			frm.set_df_property("inspected_qty_nos", "read_only", 0)
			frm.set_df_property("inspected_qty_nos", "hidden", 0)
		}
		else {
			frm.set_df_property("inspected_qty_nos", "read_only", 1)
			frm.set_df_property("inspected_qty_nos", "hidden", 1)
		}
		frm.set_value("scan_inspector", "")
		frm.set_value("inspector_name", "")
		frm.set_value("inspector_code", "")
		frm.set_value("scan_production_lot", "")
		frm.set_value("product_ref_no", "")
		frm.set_value("lot_no", "")
		frm.set_value("operator_name", "")
		frm.set_value("batch_no", "")
		frm.set_value("spp_batch_number", "")
		frm.set_value("machine_no", "")
		frm.set_value("total_inspected_qty", "")
		frm.set_value("inspected_qty_nos", "")
		frm.set_value("total_inspected_qty_nos", "")
		frm.doc.items = []
		refresh_field('items')
		frm.set_value("total_rejected_qty", "")
		frm.set_value("total_rejected_qty_in_percentage", "")
		frm.set_value("total_rejected_qty_kg", "")

		frm.set_value("id_minimum", "")
		frm.set_value("id_maximum", "")
		frm.set_value("od_minimum", "")
		frm.set_value("od_maximum", "")
		frm.set_value("hardness", "")
		frm.set_value("thickness", "")

		frm.set_value("source_warehouse", '')
		frm.set_value("vs_pdir_qty", '')
	},
	"inspected_qty_nos": frm => {
		if (frm.doc.inspected_qty_nos && frm.doc.inspected_qty_nos != undefined && frm.doc.one_no_qty_equal_kgs && frm.doc.one_no_qty_equal_kgs != undefined) {
			let total_ins_kg = frm.doc.inspected_qty_nos * frm.doc.one_no_qty_equal_kgs
			frm.set_value("total_inspected_qty", total_ins_kg)
			refresh_field("total_inspected_qty")
		}
	},
	"scan_inspector": function (frm) {
		if (frm.doc.scan_inspector && frm.doc.scan_inspector != undefined) {
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.validate_inspector_barcode',
				args: {
					"b__code": frm.doc.scan_inspector,
					inspection_type: frm.doc.inspection_type
				},
				freeze: true,
				callback: (r) => {
					if (r && r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_inspector", "");
						frm.set_value("inspector_name", "")
						frm.set_value("inspector_code", "")
					}
					else if (r && r.status == "success") {
						frm.set_value("inspector_name", r.message.employee_name);
						frm.set_value("inspector_code", r.message.name);
						// frm.set_value("scan_inspector", "");
						frm.events.generate_defect_entry(frm, "Inspector No")
					}
					else {
						frappe.msgprint("Somthing went wrong.");
						frm.set_value("scan_inspector", "");
					}
				}
			})
		}
	},
	"scan_production_lot": (frm) => {
		if (frm.doc.scan_production_lot && frm.doc.scan_production_lot != undefined) {
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.inspection_entry.inspection_entry.validate_lot_number',
				args: {
					batch_no: frm.doc.scan_production_lot,
					docname: frm.doc.name,
					inspection_type: frm.doc.inspection_type
				},
				freeze: true,
				callback: function (r) {
					if (r && r.message && r.message.status == "Failed") {
						frappe.msgprint(r.message.message);
						frm.set_value("scan_production_lot", "");
						frm.set_value("product_ref_no", "")
						frm.set_value("lot_no", "")
						frm.set_value("operator_name", "")
						frm.set_value("batch_no", "")
						frm.set_value("spp_batch_number", "")
						frm.set_value("machine_no", "")
						frm.set_value("total_inspected_qty", "")
						frm.set_value("inspected_qty_nos", "")
						frm.set_value("total_inspected_qty_nos", "")
						frm.doc.items = []
						refresh_field('items')
						frm.set_value("total_rejected_qty", "")
						frm.set_value("total_rejected_qty_in_percentage", "")
						frm.set_value("total_rejected_qty_kg", "")
						frm.set_value("moulding_production_completed", 0)
						frm.set_value("source_warehouse", '')
						frm.set_value("vs_pdir_qty", '')
					}
					else if (r && r.message && r.message.status == "Success") {
						if (frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection") {
							frm.set_value("product_ref_no", r.message.message.production_item)
							frm.set_value("lot_no", r.message.message.batch_code)
							frm.set_value("operator_name", r.message.message.employee)
							frm.set_value("batch_no", r.message.message.batch_no)
							frm.set_value("spp_batch_number", r.message.message.spp_batch_no)
							frm.set_value("machine_no", r.message.message.workstation)
							frm.one_no_qty_equal_kgs = r.message.message.one_no_qty_equal_kgs
							frm.set_value("one_no_qty_equal_kgs", r.message.message.one_no_qty_equal_kgs)
							frm.set_value("moulding_production_completed", r.message.message.moulding_production_entry)
							frm.trigger("inspected_qty_nos")
							frm.events.generate_defect_entry(frm, "Lot No")
						}
						else if (frm.doc.inspection_type == "Lot Inspection") {
							frm.set_value("product_ref_no", r.message.message.production_item)
							frm.set_value("lot_no", r.message.message.batch_code)
							frm.set_value("operator_name", r.message.message.employee)
							frm.set_value("batch_no", r.message.message.batch_no)
							frm.set_value("spp_batch_number", r.message.message.spp_batch_no)
							frm.set_value("machine_no", r.message.message.workstation)
							// frm.set_value("total_inspected_qty", r.message.message.qty_from_item_batch)
							frm.one_no_qty_equal_kgs = r.message.message.one_no_qty_equal_kgs
							frm.set_value("one_no_qty_equal_kgs", r.message.message.one_no_qty_equal_kgs)
							frm.trigger("inspected_qty_nos")
							frm.events.generate_defect_entry(frm, "Lot No")
						}
						else if (frm.doc.inspection_type == "Incoming Inspection" || frm.doc.inspection_type == "Final Inspection" || frm.doc.inspection_type == "Final Visual Inspection" || frm.doc.inspection_type == "PDIR") {
							frm.set_value("product_ref_no", r.message.message.production_item)
							frm.set_value("lot_no", r.message.message.batch_code)
							frm.set_value("operator_name", r.message.message.employee)
							frm.set_value("batch_no", r.message.message.batch_no)
							frm.set_value("spp_batch_number", r.message.message.spp_batch_number)
							frm.set_value("machine_no", r.message.message.workstation)
							frm.events.generate_defect_entry(frm, "Lot No")
							if (r.message.message.warehouse) {
								frm.set_value("source_warehouse", r.message.message.warehouse)
							}
							if (r.message.message.qty_from_item_batch) {
								frm.set_value("vs_pdir_qty", r.message.message.qty_from_item_batch
								)
							}
							if (r.message.message.available_qty_kgs) {
								frm.set_value("available_qty_kgs", r.message.message.available_qty_kgs
								)
							}
							if (r.message.message.available_qty_nos) {
								frm.set_value("available_qty_nos", r.message.message.available_qty_nos
								)
							}
							if (r.message.message._1kg_eq_nos) {
								frm.set_value("one_kg_equal_nos", r.message.message._1kg_eq_nos
								)
								}
						}
					}
					else {
						frappe.msgprint("Something went wrong.");
					}
				}
			});
		}
	},
	generate_defect_entry: (frm, resp_type) => {
		if (resp_type == "Inspector No") {
			if (!frm.doc.inspector_code || frm.doc.inspector_code == undefined) {
				frappe.validated = false
				frappe.msgprint("Could not find <b>Inspector ID</b>.");
				return
			}
		}
		else if (resp_type == "Lot No") {
			if ((frm.doc.inspection_type == "Lot Inspection" || frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection") && (!frm.one_no_qty_equal_kgs || frm.one_no_qty_equal_kgs == undefined)) {
				frappe.validated = false
				frappe.msgprint("Avg Blank Wt/Product not found in <b>Mould Specification</b>.");
				return
			}
			if (!frm.doc.product_ref_no || frm.doc.product_ref_no == undefined) {
				frappe.validated = false
				frappe.msgprint("Product reference is missing.");
				return
			}
			if (!frm.doc.machine_no || frm.doc.machine_no == undefined) {
				frappe.validated = false
				frappe.msgprint("Machine no is missing.");
				return
			}
			if (!frm.doc.lot_no || frm.doc.lot_no == undefined) {
				frappe.validated = false
				frappe.msgprint("Could not find the lot number.");
				return
			}
			if ((!frm.doc.batch_no || frm.doc.batch_no == undefined) && frm.doc.inspection_type != "Line Inspection" && frm.doc.inspection_type != "Patrol Inspection" && frm.doc.inspection_type != "Lot Inspection") {
				frappe.validated = false
				frappe.msgprint("Batch no is missing.");
				return
			}
		}
		if (frm.doc.inspector_code && frm.doc.lot_no) {
			frm.doc.items = []
			refresh_field('items')
			frm.set_value("total_rejected_qty", "")
			frm.set_value("total_rejected_qty_in_percentage", "")
			frm.set_value("total_rejected_qty_kg", "")
			frm.defect__arry = [{"type_of_defect": "FLOW-(FL)"}, 
								{"type_of_defect": "BUBBLE-(BU) / BLISTER-(BL)"}, 
								{"type_of_defect": "CUTMARK-(CU)"},
								{"type_of_defect": "DEFLASH-(DF)"}, 
								{"type_of_defect": "RIB"}, 
								{"type_of_defect": "FOREIGN PARTICLE-(FP)"},
								{"type_of_defect": "UNDER FILL-( UF )"},
								{"type_of_defect": "DIPRESSION-(DP)"}, 
								{"type_of_defect": "UNDER CURE-(UC)"}, 
								{"type_of_defect": "SURFACE DEFECT-(SD)"},
								{"type_of_defect": "OVER CURE-(OC) /FAST CURE"},
								{"type_of_defect": "BURST / TEAR"}, 
								{"type_of_defect": "BLACK MARK"},
							]
			for (let i = 0; i < frm.defect__arry.length; i++) {
				frm.add_child("items", frm.defect__arry[i])
			}
			refresh_field('items')
			// frm.trigger('update_inspection_types')
		}
	}
});

frappe.ui.form.on('Inspection Entry Item', {
	before_items_remove(frm,cdt,cdn){
		let row = locals[cdt][cdn]
		frm.removes_rejections.push(row.type_of_defect)
	},
	items_add(frm,cdt,cdn){
		let row = locals[cdt][cdn]
		var grid_row = cur_frm.fields_dict['items'].grid.grid_rows_by_docname[row.name],
		field = frappe.utils.filter_dict(grid_row.docfields, { fieldname: "type_of_defect" })[0];
		field.fieldtype = "Data"
		field.read_only = 0
	},
	"type_of_defect": (frm, cdt, cdn) => {
		let row = locals[cdt][cdn]
		if(!row.type_of_defect){
			row.rejected_qty = 0
			refresh_field('items')
			frappe.msgprint("The <b>Rejection Qty</b> can't be present with <b>Type of Defect</b>..!")
		}
	},
	"rejected_qty": (frm, cdt, cdn) => {
		let row = locals[cdt][cdn]
		if(row.type_of_defect){
			if (row.rejected_qty && row.rejected_qty != undefined) {
				if (!frm.doc.inspected_qty_nos && (frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection" || frm.doc.inspection_type == "Lot Inspection")) {
					row.rejected_qty = ''
					frappe.validated = false
					frappe.msgprint("Please enter total inspected Qty before reject...!")
					return
				}
				if (!frm.doc.total_inspected_qty_nos && (frm.doc.inspection_type == "Incoming Inspection" || frm.doc.inspection_type == "Final Inspection" || frm.doc.inspection_type == "Final Visual Inspection" || frm.doc.inspection_type == "PDIR")) {
					row.rejected_qty = ''
					frappe.validated = false
					frappe.msgprint("Please enter total inspected Qty before reject...!")
					return
				}
				if (frm.doc.inspection_type == "Lot Inspection" || frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection") {
					let total_ins_kg = frm.doc.inspected_qty_nos * frm.doc.one_no_qty_equal_kgs
					frm.doc.total_inspected_qty = total_ins_kg
					if (!frm.doc.total_inspected_qty || frm.doc.total_inspected_qty == undefined) {
						frappe.validated = false
						frappe.msgprint("Total inspected Qty is not found.");
						return
					}
				}
				if (frm.doc.inspection_type == "Incoming Inspection" || frm.doc.inspection_type == "Final Inspection" || frm.doc.inspection_type == "Final Visual Inspection" || frm.doc.inspection_type == "PDIR") {
					if (!frm.doc.total_inspected_qty_nos || frm.doc.total_inspected_qty_nos == undefined) {
						frappe.validated = false
						frappe.msgprint("Total inspected Qty is not found.");
						return
					}
				}

				if (frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection") {
					if (!frm.doc.one_no_qty_equal_kgs || frm.doc.one_no_qty_equal_kgs == undefined) {
						frappe.validated = false
						frappe.msgprint("Avg Blank Wt/Product not found in <b>Mould Specification</b>.");
						return
					}
					else {
						let cur_rejected_qty = frm.doc.one_no_qty_equal_kgs * row.rejected_qty
						var before_r_qty_kgs = 0;
						for (var i = 0; i < frm.doc.items.length; i++) {
							if (frm.doc.items[i].rejected_qty_kg && row.name != frm.doc.items[i].name) {
								before_r_qty_kgs += frm.doc.items[i].rejected_qty_kg
							}
						}
						// if ((frm.doc.total_inspected_qty ? frm.doc.total_inspected_qty : 0) >= (parseFloat(cur_rejected_qty.toFixed(3)) + (before_r_qty_kgs ? before_r_qty_kgs : 0))) {
						// 	row.rejected_qty_kg = parseFloat(cur_rejected_qty.toFixed(3));
						if ((frm.doc.total_inspected_qty ? frm.doc.total_inspected_qty : 0) >= (cur_rejected_qty + (before_r_qty_kgs ? before_r_qty_kgs : 0))) {
							row.rejected_qty_kg = cur_rejected_qty;
							frm.refresh_field('items');
							if (frm.doc.items) {
								var r_qty = 0;
								var r_qty_kgs = 0;
								for (var i = 0; i < frm.doc.items.length; i++) {
									if (frm.doc.items[i].rejected_qty) {
										r_qty += frm.doc.items[i].rejected_qty
									}
									if (frm.doc.items[i].rejected_qty_kg) {
										r_qty_kgs += frm.doc.items[i].rejected_qty_kg
									}
								}
								frm.set_value("total_rejected_qty", r_qty)
								frm.set_value("total_rejected_qty_kg", r_qty_kgs)
								if (r_qty_kgs) {
									var r_qty_per = (r_qty_kgs / frm.doc.total_inspected_qty) * 100
									// frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
									let fixed_percent = parseFloat(r_qty_per.toFixed(3))
									frm.set_value("total_rejected_qty_in_percentage",fixed_percent ? fixed_percent :0.001)
								}
								else {
									frm.set_value("total_rejected_qty_in_percentage", 0)
								}
							}
						}
						else {
							row.rejected_qty = ""
							frappe.msgprint(`Total <b>Rejected Quantity</b> should be less than the <b>Total Inspected Quantity</b>.`);
						}
					}

				}
				else if (frm.doc.inspection_type == "Lot Inspection") {
					if (!frm.doc.one_no_qty_equal_kgs || frm.doc.one_no_qty_equal_kgs == undefined) {
						frappe.validated = false
						frappe.msgprint("Avg Blank Wt/Product not found in <b>Mould Specification</b>.");
						return
					}
					else {
						let cur_rejected_qty = frm.doc.one_no_qty_equal_kgs * row.rejected_qty
						var before_r_qty_kgs = 0;
						for (var i = 0; i < frm.doc.items.length; i++) {
							if (frm.doc.items[i].rejected_qty_kg && row.name != frm.doc.items[i].name) {
								before_r_qty_kgs += frm.doc.items[i].rejected_qty_kg
							}
						}
						// if ((frm.doc.total_inspected_qty ? frm.doc.total_inspected_qty : 0) >= (parseFloat(cur_rejected_qty.toFixed(3)) + (before_r_qty_kgs ? before_r_qty_kgs : 0))) {
						// 	row.rejected_qty_kg = parseFloat(cur_rejected_qty.toFixed(3));
						if ((frm.doc.total_inspected_qty ? frm.doc.total_inspected_qty : 0) >= (cur_rejected_qty + (before_r_qty_kgs ? before_r_qty_kgs : 0))) {
							row.rejected_qty_kg = cur_rejected_qty;
							frm.refresh_field('items');
							if (frm.doc.items) {
								var r_qty = 0;
								var r_qty_kgs = 0;
								for (var i = 0; i < frm.doc.items.length; i++) {
									if (frm.doc.items[i].rejected_qty) {
										r_qty += frm.doc.items[i].rejected_qty
									}
									if (frm.doc.items[i].rejected_qty_kg) {
										r_qty_kgs += frm.doc.items[i].rejected_qty_kg
									}
								}
								frm.set_value("total_rejected_qty", r_qty)
								frm.set_value("total_rejected_qty_kg", r_qty_kgs)
								if (r_qty_kgs) {
									var r_qty_per = (r_qty_kgs / frm.doc.total_inspected_qty) * 100
									// frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
									let fixed_percent = parseFloat(r_qty_per.toFixed(3))
									frm.set_value("total_rejected_qty_in_percentage",fixed_percent ? fixed_percent :0.001)
								}
								else {
									frm.set_value("total_rejected_qty_in_percentage", 0)
								}
							}
						}
						else {
							row.rejected_qty = ""
							frappe.msgprint(`Total <b>Rejected Quantity</b> should be less than the <b>Total Inspected Quantity</b>.`);
						}
					}
				}
				else if (frm.doc.inspection_type == "Incoming Inspection" || frm.doc.inspection_type == "Final Inspection" || frm.doc.inspection_type == "Final Visual Inspection" || frm.doc.inspection_type == "PDIR") {
					var before_r_qty = 0;
					for (var i = 0; i < frm.doc.items.length; i++) {
						if (frm.doc.items[i].rejected_qty) {
							before_r_qty += frm.doc.items[i].rejected_qty
						}
					}
					if ((frm.doc.total_inspected_qty_nos ? frm.doc.total_inspected_qty_nos : 0) >= (before_r_qty ? before_r_qty : 0)) {
						if (frm.doc.items) {
							var r_qty = 0;
							for (var i = 0; i < frm.doc.items.length; i++) {
								if (frm.doc.items[i].rejected_qty) {
									r_qty += frm.doc.items[i].rejected_qty
								}
							}
							frm.set_value("total_rejected_qty", r_qty)
							if (r_qty) {
								var r_qty_per = (r_qty / frm.doc.total_inspected_qty_nos) * 100
								// frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
								let fixed_percent = parseFloat(r_qty_per.toFixed(3))
								frm.set_value("total_rejected_qty_in_percentage",fixed_percent ? fixed_percent :0.001)
							}
							else {
								frm.set_value("total_rejected_qty_in_percentage", 0)
							}
						}
					}
					else {
						row.rejected_qty = ""
						frappe.msgprint("Total <b>Rejected Quantity</b> should be less than the <b>Total Inspected Quantity</b>.");
					}
				}
			}
			else {
				if (frm.doc.inspection_type == "Line Inspection" || frm.doc.inspection_type == "Patrol Inspection") {
					row.rejected_qty_kg = 0;
					frm.refresh_field('items');
					if (frm.doc.items) {
						var r_qty = 0;
						var r_qty_kgs = 0;
						for (var i = 0; i < frm.doc.items.length; i++) {
							if (frm.doc.items[i].rejected_qty) {
								r_qty += frm.doc.items[i].rejected_qty
							}
							if (frm.doc.items[i].rejected_qty_kg) {
								r_qty_kgs += frm.doc.items[i].rejected_qty_kg
							}
						}
						frm.set_value("total_rejected_qty", r_qty)
						frm.set_value("total_rejected_qty_kg", r_qty_kgs)
						if (r_qty_kgs) {
							var r_qty_per = (r_qty_kgs / frm.doc.total_inspected_qty) * 100
							// frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
							let fixed_percent = parseFloat(r_qty_per.toFixed(3))
							frm.set_value("total_rejected_qty_in_percentage",fixed_percent ? fixed_percent :0.001)
						}
						else {
							frm.set_value("total_rejected_qty_in_percentage", 0)
						}
					}
				}
				else if (frm.doc.inspection_type == "Lot Inspection") {
					row.rejected_qty_kg = 0;
					frm.refresh_field('items');
					if (frm.doc.items) {
						var r_qty = 0;
						var r_qty_kgs = 0;
						for (var i = 0; i < frm.doc.items.length; i++) {
							if (frm.doc.items[i].rejected_qty) {
								r_qty += frm.doc.items[i].rejected_qty
							}
							if (frm.doc.items[i].rejected_qty_kg) {
								r_qty_kgs += frm.doc.items[i].rejected_qty_kg
							}
						}
						frm.set_value("total_rejected_qty", r_qty)
						frm.set_value("total_rejected_qty_kg", r_qty_kgs)
						if (r_qty_kgs) {
							var r_qty_per = (r_qty_kgs / frm.doc.total_inspected_qty) * 100
							// frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
							let fixed_percent = parseFloat(r_qty_per.toFixed(3))
							frm.set_value("total_rejected_qty_in_percentage",fixed_percent ? fixed_percent :0.001)
						}
						else {
							frm.set_value("total_rejected_qty_in_percentage", 0)
						}
					}
				}
				else if (frm.doc.inspection_type == "Incoming Inspection" || frm.doc.inspection_type == "Final Inspection" || frm.doc.inspection_type == "Final Visual Inspection" || frm.doc.inspection_type == "PDIR") {
					row.rejected_qty = 0;
					frm.refresh_field('items');
					if (frm.doc.items) {
						var r_qty = 0;
						for (var i = 0; i < frm.doc.items.length; i++) {
							if (frm.doc.items[i].rejected_qty) {
								r_qty += frm.doc.items[i].rejected_qty
							}
						}
						frm.set_value("total_rejected_qty", r_qty)
						if (r_qty) {
							var r_qty_per = (r_qty / frm.doc.total_inspected_qty_nos) * 100
							// frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
							let fixed_percent = parseFloat(r_qty_per.toFixed(3))
							frm.set_value("total_rejected_qty_in_percentage",fixed_percent ? fixed_percent :0.001)
						}
						else {
							frm.set_value("total_rejected_qty_in_percentage", 0)
						}
					}
				}
			}
		}
		else{
			row.rejected_qty = 0
			refresh_field('items')
			frappe.msgprint('Please enter <b>Rejection Type</b> before entering <b>Rejection Qty</b>..!')
		}
	}
});

















// backup
// "add": function (frm) {
	// 	if (!frm.doc.product_ref_no || frm.doc.product_ref_no == undefined) {
	// 		frappe.msgprint("Product reference no is missing.");
	// 		return
	// 	}
	// 	if (!frm.doc.type_of_defect || frm.doc.type_of_defect == undefined) {
	// 		frappe.msgprint("Please select type of defect.");
	// 		return
	// 	}
	// 	if (!frm.doc.rejected_qty || frm.doc.rejected_qty == undefined) {
	// 		frappe.msgprint("Please enter the rejected qty.");
	// 		return
	// 	}
	// 	if (!frm.doc.machine_no || frm.doc.machine_no == undefined) {
	// 		frappe.msgprint("Please enter the machine number.");
	// 		return
	// 	}
	// 	if (!frm.doc.lot_no || frm.doc.lot_no == undefined) {
	// 		frappe.msgprint("Please enter the lot number.");
	// 		return
	// 	}
	// 	if (!frm.doc.inspector_code || frm.doc.inspector_code == undefined) {
	// 		frappe.msgprint("Please Scan the Inspector.");
	// 		return
	// 	}
	// 	if((frm.doc.inspection_type == "Lot Inspection" || frm.doc.inspection_type == "Line Inspection") && (!frm.one_no_qty_equal_kgs || frm.one_no_qty_equal_kgs == undefined)){
	// 		frappe.msgprint("UOM coversion factor value not found.");
	// 		return
	// 	}
	// 	else {
	// 		if(frm.doc.inspection_type == "Lot Inspection" || frm.doc.inspection_type == "Line Inspection"){
	// 			let cur_rejected_qty = frm.one_no_qty_equal_kgs *  frm.doc.rejected_qty
	// 			if ((frm.doc.total_inspected_qty ? frm.doc.total_inspected_qty : 0) > (cur_rejected_qty + (frm.doc.total_rejected_qty_kg ? frm.doc.total_rejected_qty_kg : 0))) {
	// 				var row = frappe.model.add_child(frm.doc, "Inspection Entry Item", "items");
	// 				row.product_ref_no = frm.doc.product_ref_no;
	// 				row.lot_no = frm.doc.lot_no;
	// 				row.type_of_defect = frm.doc.type_of_defect;
	// 				row.rejected_qty = frm.doc.rejected_qty;
	// 				row.rejected_qty_kg = cur_rejected_qty;
	// 				row.operator_name = frm.doc.operator_name;
	// 				row.machine_no = frm.doc.machine_no;
	// 				row.inspector_name = frm.doc.inspector_name
	// 				row.inspector_code = frm.doc.inspector_code
	// 				row.batch_no = frm.doc.batch_no
	// 				frm.refresh_field('items');
	// 				frm.set_value("type_of_defect", "FLOW-(FL)");
	// 				frm.set_value("rejected_qty", 0);
	// 				if (frm.doc.items) {
	// 					var r_qty = 0;
	// 					var r_qty_kgs = 0;
	// 					for (var i = 0; i < frm.doc.items.length; i++) {
	// 						r_qty += frm.doc.items[i].rejected_qty
	// 						r_qty_kgs += frm.doc.items[i].rejected_qty_kg
	// 					}
	// 					frm.set_value("total_rejected_qty", r_qty)
	// 					frm.set_value("total_rejected_qty_kg", r_qty_kgs)
	// 					var r_qty_per = (r_qty_kgs / frm.doc.total_inspected_qty) * 100
	// 					frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
	// 				}
	// 			}
	// 			else {
	// 				frappe.msgprint("Total <b>Rejected Quantity</b> should be less than the <b>Total Inspected Quantity</b>.");
	// 				}
	// 		}
	// 		else if(frm.doc.inspection_type == "Incoming Inspection" || frm.doc.inspection_type == "Patrol Inspection" || frm.doc.inspection_type == "Final Inspection"){
	// 			if ((frm.doc.total_inspected_qty_nos ? frm.doc.total_inspected_qty_nos : 0) > ((frm.doc.rejected_qty ? frm.doc.rejected_qty : 0) + (frm.doc.total_rejected_qty ? frm.doc.total_rejected_qty : 0))) {
	// 				var row = frappe.model.add_child(frm.doc, "Inspection Entry Item", "items");
	// 				row.product_ref_no = frm.doc.product_ref_no;
	// 				row.lot_no = frm.doc.lot_no;
	// 				row.type_of_defect = frm.doc.type_of_defect;
	// 				row.rejected_qty = frm.doc.rejected_qty;
	// 				row.operator_name = frm.doc.operator_name;
	// 				row.machine_no = frm.doc.machine_no;
	// 				row.inspector_name = frm.doc.inspector_name
	// 				row.inspector_code = frm.doc.inspector_code
	// 				row.batch_no = frm.doc.batch_no
	// 				frm.refresh_field('items');
	// 				frm.set_value("type_of_defect", "FLOW-(FL)");
	// 				frm.set_value("rejected_qty", 0);
	// 				if (frm.doc.items) {
	// 					var r_qty = 0;
	// 					for (var i = 0; i < frm.doc.items.length; i++) {
	// 						r_qty += frm.doc.items[i].rejected_qty
	// 					}
	// 					frm.set_value("total_rejected_qty", r_qty)
	// 					var r_qty_per = (r_qty / frm.doc.total_inspected_qty_nos) * 100
	// 					frm.set_value("total_rejected_qty_in_percentage", r_qty_per)
	// 				}
	// 			}
	// 			else {
	// 				frappe.msgprint("Total <b>Rejected Quantity</b> should be less than the <b>Total Inspected Quantity</b>.");
	// 				}
	// 		}
	// 	}
	// }


	// update_opts(frm,option) {
	// 	let options = ["FLOW-(FL)", "BUBBLE-(BU) / BLISTER-(BL)", "CUTMARK-(CU)",
	// 		"DEFLASH-(DF)", "RIB", "FOREIGN PARTICLE-(FP)", "UNDER FILL-( UF )",
	// 		"DIPRESSION-(DP)", "UNDER CURE-(UC)", "SURFACE DEFECT-(SD)", "OVER CURE-(OC) /FAST CURE"
	// 		, "BURST / TEAR", "BLACK MARK"]
	// 	let df_options = [...options]
	// 	frm.doc.items.map(res => {
	// 		if(!res.type_of_defect.includes(Object.keys(options))){
	// 			df_options.push(res.type_of_defect)
	// 		}
	// 	})
	// 	frm.doc.items.map(res => {
	// 		var grid_row = cur_frm.fields_dict['items'].grid.grid_rows_by_docname[res.name],
	// 		field = frappe.utils.filter_dict(grid_row.docfields, { fieldname: "type_of_defect" })[0];
	// 		field.options = df_options
	// 	})
	// 	refresh_field('items')
	// },