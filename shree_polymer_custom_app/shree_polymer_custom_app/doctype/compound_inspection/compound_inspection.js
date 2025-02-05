// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Compound Inspection', {
	refresh: function(frm) {
		frm.events.hide_show_info(frm)
		frm.events.view_qc_ins(frm)
	},
	timeline_refresh:frm =>{
		frm.events.view_qc_ins(frm)
	},
	view_qc_ins:(frm) =>{
		if(frm.doc.qc_inspection_ref){
			frm.add_custom_button(__("View Quality Inspection"), function(){
				frappe.set_route("Form", "Quality Inspection", frm.doc.qc_inspection_ref);
			  });
		}
		else{
			frm.remove_custom_button('View Quality Inspection');
		}
	},
	hide_show_info(frm){
		if(!frm.doc.posting_date){
			frm.set_value('posting_date',frappe.datetime.now_date())
			refresh_field('posting_date')
		}
		if(frm.is_new() && !frm.doc.scan_compound){
			frm.set_df_property("parameter_section","hidden",1)
		}	
		frm.events.hide_min_max_parameters(frm)
	},
	hide_min_max_parameters(frm){
		frm.set_df_property("ts2_min","hidden",1)
		frm.set_df_property("ts2_max","hidden",1)
		frm.set_df_property("sg_min","hidden",1)
		frm.set_df_property("sg_max","hidden",1)
		frm.set_df_property("min_hardness","hidden",1)
		frm.set_df_property("max_hardness","hidden",1)
		frm.set_df_property("tc_90_min","hidden",1)
		frm.set_df_property("tc_90_max","hidden",1)
	},	
	set_parameters(frm,parameters){
		parameters.map(resp =>{
			if(resp.specification == "Ts2"){
				frm.set_value("ts2_min",resp.min_value)
				frm.set_value("ts2_max",resp.max_value)
			}
			if(resp.specification == "specific gravity"){
				frm.set_value("sg_min",resp.min_value)
				frm.set_value("sg_max",resp.max_value)
			}
			if(resp.specification == "HARDNESS"){
				frm.set_value("min_hardness",resp.min_value)
				frm.set_value("max_hardness",resp.max_value)
			}
			if(resp.specification == "TC 90"){
				frm.set_value("tc_90_min",resp.min_value)
				frm.set_value("tc_90_max",resp.max_value)
			}
		})
		frm.set_df_property("parameter_section","hidden",0)
	},	
	scan_compound(frm){
		if (frm.doc.scan_compound && frm.doc.scan_compound != undefined){
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.compound_inspection.compound_inspection.validate_compound_barcode',
				args: {
					barcode: frm.doc.scan_compound,
					docname:frm.doc.name
				},
				freeze: true,
				callback: function (r) {
					if (r.status == "failed") {
						frappe.msgprint(r.message);
						frm.set_value("scan_compound", "");
					}
					else if(r.status == "success"){
						frm.set_value("compound_ref",r.message.item_code)
						frm.set_value("batch_no",r.message.spp_batch_number)
						frm.set_value("qty",r.message.qty)
						frm.set_value("stock_id",r.message.parent)
						frm.set_value("dc_receipt_id",r.message.source_ref_id)
						frm.events.set_parameters(frm,r.message.parameters)
					}
					else{
						frappe.msgprint("Something went wrong.");
						frm.set_value("scan_compound", "");
						frm.set_value("stock_id",'')
						frm.set_value("dc_receipt_id",'')
					}
				}
			});	
		}
		else{
			frm.set_value("compound_ref",'')
			frm.set_value("batch_no",'')
			frm.set_value("qty",0)
			frm.set_value("stock_id",'')
			frm.set_value("dc_receipt_id",'')
		}
	},
	scan_employee(frm) {
		if(frm.doc.scan_employee && frm.doc.scan_employee != undefined){
			frappe.call({
				method:'shree_polymer_custom_app.shree_polymer_custom_app.doctype.compound_inspection.compound_inspection.validate_inspector_barcode',
				args:{
					"b__code":frm.doc.scan_employee,
					"operation_type":"Compound Inspector"
				},
				freeze:true,
				callback:(r) =>{
					if(r && r.status=="failed"){
						frappe.msgprint(r.message);
						frm.set_value("scan_employee", "");
						frm.set_value('operator_id',"")
						frm.set_value('operator_name',"")
					}
					else if(r && r.status=="success"){
						frm.set_value("operator_name",r.message.employee_name);
						frm.set_value("operator_id",r.message.name);
					}
					else{
						frappe.msgprint("Somthing went wrong.");
						frm.set_value("scan_employee", "");
						frm.set_value('operator_id',"")
						frm.set_value('operator_name',"")
					}
				}
		})
		}
		else{
			frm.set_value("scan_employee", "");
			frm.set_value('operator_id',"")
			frm.set_value('operator_name',"")
		}
	},
	scan_approver(frm) {
		if(frm.doc.scan_approver && frm.doc.scan_approver != undefined){
			frappe.call({
				method:'shree_polymer_custom_app.shree_polymer_custom_app.doctype.compound_inspection.compound_inspection.validate_inspector_barcode',
				args:{
					"b__code":frm.doc.scan_approver,
					"operation_type":"Compound Maturation Approver"
				},
				freeze:true,
				callback:(r) =>{
					if(r && r.status=="failed"){
						frappe.msgprint(r.message);
						frm.set_value("scan_approver", "");
						frm.set_value('approver_id',"")
						frm.set_value('approver_name',"")
					}
					else if(r && r.status=="success"){
						frm.set_value("approver_name",r.message.employee_name);
						frm.set_value("approver_id",r.message.name);
					}
					else{
						frappe.msgprint("Somthing went wrong.");
						frm.set_value("scan_approver", "");
						frm.set_value('approver_id',"")
						frm.set_value('approver_name',"")
					}
				}
		})
		}
		else{
			frm.set_value("scan_approver", "");
			frm.set_value('approver_id',"")
			frm.set_value('approver_name',"")
		}
	},
	scan_quality_approver(frm) {
		if(frm.doc.scan_quality_approver && frm.doc.scan_quality_approver != undefined){
			frappe.call({
				method:'shree_polymer_custom_app.shree_polymer_custom_app.doctype.compound_inspection.compound_inspection.validate_inspector_barcode',
				args:{
					"b__code":frm.doc.scan_quality_approver,
					"operation_type":"Compound Inspection Approver"
				},
				freeze:true,
				callback:(r) =>{
					if(r && r.status=="failed"){
						frappe.msgprint(r.message);
						frm.set_value("scan_quality_approver", "");
						frm.set_value('quality_approver_id',"")
						frm.set_value('quality_approver_name',"")
					}
					else if(r && r.status=="success"){
						frm.set_value("quality_approver_name",r.message.employee_name);
						frm.set_value("quality_approver_id",r.message.name);
					}
					else{
						frappe.msgprint("Somthing went wrong.");
						frm.set_value("scan_quality_approver", "");
						frm.set_value('quality_approver_id',"")
						frm.set_value('quality_approver_name',"")
					}
				}
		})
		}
		else{
			frm.set_value("scan_quality_approver", "");
			frm.set_value('quality_approver_id',"")
			frm.set_value('quality_approver_name',"")
		}
	}
});
