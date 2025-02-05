// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lot Resource Tagging', {
	refresh:frm =>{
		frm.rendom__id = Math.floor(Math.random() * 1000);
		frm.events.view_stock_entry(frm)
		frm.events.bind_operation(frm,true,[])
		frm.events.available_qty(frm)
		frm.events.hide_show_operator(frm)
	},
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
		frm.events.available_qty(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.stock_entry_ref){
			frm.add_custom_button(__("View Stock Entry"), function(){
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_ref);
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
	operation_type(frm){
		if(frm.doc.operation_type && frm.doc.operation_type != undefined){
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.check_return_workstation',
					args: {
						operation_type:frm.doc.operation_type,
					},
					freeze: true,
					callback: function (r) {
						if(r && r.message && r.message.status == "success"){
							frm.set_value("workstation",r.message.message)
							refresh_field('workstation')
						}
						else if(r && r.message){
							frappe.msgprint(r.message.message)
							frm.set_value("scan_lot_no","")
							refresh_field('scan_lot_no')
						}
						else{
							frappe.msgprint("Something went wrong while fetching workstation details..!")
							frm.set_value("scan_lot_no","")
							refresh_field('scan_lot_no')
						}
					}
				});	
		}
	},
	"qtynos":(frm) =>{
		if(frm.doc.qtynos && frm.doc.qtynos > frm.doc.available_qty){
			frappe.validated = false
			frappe.throw(`The Qty - <b>${frm.doc.qtynos}</b> should be less than the available qty - <b>${frm.doc.available_qty}</b>`)
		}
	},
	available_qty(frm){
		setTimeout(()=>{
			if(frm.doc.qtynos && frm.doc.available_qty != frm.doc.qtynos){
				frm.set_value('qtynos',frm.doc.available_qty)
			}
			else if(!frm.doc.qtynos){
				frm.set_value('qtynos',frm.doc.available_qty)
			}
		},200)
		frm.set_df_property('qtynos','read_only',1)
		frm.set_df_property('available_qty','hidden',1)
	},
	"scan_lot_no": (frm) => {
		if (frm.doc.scan_lot_no && frm.doc.scan_lot_no != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_lot_number',
				args: {
					barcode: frm.doc.scan_lot_no,
					operation_type:frm.doc.operation_type
				},
				freeze: true,
				callback: function (r) {
					if (r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_lot_no", "");
					}
					else if(r.status == "success"){
						let op_flag = true
						if(r.message.bom_operations.length == 0){
							op_flag = false
							frappe.msgprint('<b>Operations</b> not found in BOM..!')
							frm.set_value("scan_lot_no", "");
							return 
						}
						else{
							frm.events.bind_operation(frm,false,r.message.bom_operations)
							frm.events.hide_show_operator(frm)
							// frm.events.bind_operation_by_emp(frm,r.message.bom_operations)
						}
						if(op_flag){
							if (r.message.name){
								frm.set_value("job_card", r.message.name);
							}
							frm.set_value("product_ref", r.message.production_item);
							frm.set_value("batch_no", r.message.batch_no);
							frm.set_value("bom_no", r.message.bom_no);
							frm.set_value("warehouse", r.message.from_warehouse);
							frm.set_value("available_qty", r.message.qty_from_item_batch);
							frm.set_value("spp_batch_no", r.message.spp_batch_number);
							frm.set_value("scan_lot_no", frm.doc.scan_lot_no.toUpperCase());
						}
					}
					else{
						frappe.msgprint("Something went wrong.");
						frm.set_value("scan_lot_no", "");
					}
				}
			});	
		}
		else{
			frm.trigger('delete_opearation_details')
			$(frm.get_field('operation_type_html').wrapper).empty();
		}
	},
	delete_opearation_details(frm,type_=''){
		if(!type_){
			frm.set_value('operation_type',"")
		}
		frm.set_value('scan_operator',"")
		frm.set_value('operator_id',"")
		frm.set_value('operator_name',"")
	},
	"scan_operator": function(frm) {
		if(frm.doc.scan_operator && frm.doc.scan_operator != undefined){
			if (frm.doc.scan_lot_no){
				if(frm.doc.operation_type){
					frappe.call({
						method:'shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_inspector_barcode',
						args:{
							"b__code":frm.doc.scan_operator,
							"operation_type":frm.doc.operation_type
						},
						freeze:true,
						callback:(r) =>{
							if(r && r.status=="failed"){
								frappe.msgprint(r.message);
								frm.set_value("scan_operator", "");
								frm.set_value('operator_id',"")
								frm.set_value('operator_name',"")
							}
							else if(r && r.status=="success"){
								frm.set_value("operator_name",r.message.employee_name);
								frm.set_value("operator_id",r.message.name);
							}
							else{
								frappe.msgprint("Somthing went wrong.");
								frm.set_value("scan_operator", "");
								frm.set_value('operator_id',"")
								frm.set_value('operator_name',"")
							}
						}
					})
				}
				else{
					frappe.msgprint("Please select <b>Operation</b> before scan operator..!")
					frm.set_value("scan_operator", "");
				}
			}
			else{
				frappe.msgprint("Please scan <b>Lot</b> before scan operator..!")
				frm.set_value("scan_operator", "");
			}
		}
	},
	hide_show_operator(frm){
		if(frm.doc.operation_type){
			frm.set_df_property('scan_operator','hidden',0)
		}
		else{
			frm.set_df_property('scan_operator','hidden',1)
		}
	},
	bind_operation(frm,fetch_boms,operations){
		$(frm.get_field('operation_type_html').wrapper).empty();
		if(frm.doc.scan_lot_no && fetch_boms){
			if(frm.doc.docstatus != 1 && frm.doc.docstatus != 2 && !frm.is_new()){
				let operations__ = []
				if(frm.doc.operations){
					operations__ = frm.doc.operations.split(',')
					frm.events.bind_select_html(frm,operations__)
					$(`#bom_operation_${frm.rendom__id}`).val(cur_frm.doc.operation_type);
				}
				else{
					frappe.msgprint('<b>Operations</b> not found in BOM..!')
				}
			}
			else{
				if(!frm.is_new()){
					frm.events.bind_select_html(frm,[])
					$(`#bom_operation_${frm.rendom__id}`).val(cur_frm.doc.operation_type);
					$(`#bom_operation_${frm.rendom__id}`).attr("readonly", "readonly"); 
				}
			}
		}
		else{
			if(operations && operations.length > 0){
				let opts = []
				operations.map(op__ =>{
					opts.push(op__.operation)
				})
				frm.events.bind_select_html(frm,opts)
				frm.set_value("operations",opts.join(','))
				// cur_frm.set_value('operation_type',opts[0])
				refresh_field("operation_type")
			}
			else{
				if(frm.doc.scan_lot_no){
					frappe.msgprint('<b>Operations</b> not found in BOM..!')
					frm.set_value("scan_lot_no", "");
				}
			}
		}
	},
	bind_operation_by_emp: (frm,operations) => {
			let opts = []
			operations.map(op__ =>{
				opts.push(op__.operation)
			})
			frm.set_value("operations",opts.join(','))
			refresh_field("operation_type")
	},
	save_operation: (frm) => {
		frm.events.delete_opearation_details(frm,true)
		let value = $(`#bom_operation_${frm.rendom__id} option:selected`).text();
		frm.doc.__unsaved = 1
		cur_frm.set_value('operation_type',value)
		refresh_field("operation_type")
		frm.events.hide_show_operator(frm)
	},
	bind_select_html(frm,options){
		let options_html = ''
		if(frm.doc.docstatus==0){
			options_html = `<option value=""></option>`
		}
		if (options && options.length > 0){
			options.map(res =>{
				options_html += `<option value="${res}">${res}</option>`
			})
		}
		else{
			options_html += `<option value="${cur_frm.doc.operation_type}">${cur_frm.doc.operation_type}</option>`
		}
		let wrapper = $(frm.get_field('operation_type_html').wrapper).empty();
				let html = $(`
				<div class="clearfix">
				<label class="control-label" style="padding-right: 0px;">Operation Type</label>
			</div>
			<div class="control-input-wrapper">
				<div class="control-input flex align-center" style="position:relative;margin-bottom: 15px;">
					<select type="text" id='bom_operation_${frm.rendom__id}' autocomplete="off" class="input-with-feedback form-control ellipsis" maxlength="140" data-fieldtype="Select" data-fieldname="operation_type__html" placeholder="" data-doctype="Lot Resource Tagging">
						${options_html}
					</select>
					<div class="select-icon " style="padding-left: inherit;
						padding-right: inherit;
						position: absolute;
						pointer-events: none;
						top: 7px;
						right: 12px;">
								<svg class="icon  icon-sm" style="">
									<use class="" href="#icon-select"></use>
								</svg>
					</div>
			</div>`)
			wrapper.html(html)
			html.find(`#bom_operation_${frm.rendom__id}`).on('change',()=>{
				frm.events.save_operation(frm)
			})
	},
});







	// "scan_operator": function(frm) {
	// 	if(frm.doc.scan_operator && frm.doc.scan_operator != undefined){
	// 		if (frm.doc.scan_lot_no){
	// 			if(frm.doc.operations){
	// 				frappe.call({
	// 					method:'shree_polymer_custom_app.shree_polymer_custom_app.doctype.lot_resource_tagging.lot_resource_tagging.validate_inspector_barcode',
	// 					args:{
	// 						"b__code":frm.doc.scan_operator,
	// 						"operations":frm.doc.operations
	// 					},
	// 					freeze:true,
	// 					callback:(r) =>{
	// 						if(r && r.status=="failed"){
	// 							frappe.msgprint(r.message);
	// 							frm.set_value("scan_operator", "");
	// 						}
	// 						else if(r && r.status=="success"){
	// 							frm.set_value("operator_name",r.message.employee_name);
	// 							frm.set_value("operator_id",r.message.name);
	// 							frm.events.bind_operation(frm,false,r.message.operation)
	// 						}
	// 						else{
	// 							frappe.msgprint("Somthing went wrong.");
	// 							frm.set_value("scan_operator", "");
	// 						}
	// 					}
	// 				})
	// 			}
	// 			else{
	// 				frappe.msgprint("The <b>Operations</b> not found..!")
	// 				frm.set_value("scan_operator", "");
	// 			}
	// 		}
	// 		else{
	// 			frappe.msgprint("Please scan <b>Lot</b> before scan operator..!")
	// 			frm.set_value("scan_operator", "");
	// 		}
	// 	}
	// },
	// bind_operation(frm,fetch_boms,operations){
	// 	$(frm.get_field('operation_type_html').wrapper).empty();
	// 	if(frm.doc.scan_lot_no && fetch_boms){
	// 		if(frm.doc.docstatus != 1 && frm.doc.docstatus != 2 && !frm.is_new()){
	// 			let operations__ = []
	// 			if(frm.doc.employee_operations){
	// 				operations__ = frm.doc.employee_operations.split(',')
	// 				frm.events.bind_select_html(frm,operations__)
	// 				$(`#bom_operation_${frm.rendom__id}`).val(cur_frm.doc.operation_type);
	// 			}
	// 			else{
	// 				frappe.msgprint('<b>Operations</b> not found in BOM..!')
	// 			}
	// 		}
	// 		else{
	// 			if(!frm.is_new()){
	// 				frm.events.bind_select_html(frm,[])
	// 				$(`#bom_operation_${frm.rendom__id}`).val(cur_frm.doc.operation_type);
	// 				$(`#bom_operation_${frm.rendom__id}`).attr("readonly", "readonly"); 
	// 			}
	// 		}
	// 	}
	// 	else{
	// 		if(operations && operations.length > 0){
	// 			frm.events.bind_select_html(frm,operations)
	// 			frm.set_value("employee_operations",operations.join(','))
	// 			cur_frm.set_value('operation_type',operations[0])
	// 			refresh_field("operation_type")
	// 		}
	// 		else{
	// 			if(frm.doc.scan_lot_no){
	// 				frappe.msgprint('<b>Operations</b> not found in BOM..!')
	// 				frm.set_value("scan_lot_no", "");
	// 			}
	// 		}
	// 	}
	// },