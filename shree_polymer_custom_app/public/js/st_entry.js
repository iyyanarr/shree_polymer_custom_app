frappe.ui.form.on("Stock Entry",{
    timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm);
	},
	refresh:(frm) =>{
		frm.events.view_stock_entry(frm)
	},
    view_stock_entry:(frm) =>{
		if(frm.doc.items){
            let doctype_ref;
            let doctype_ref_id;
            for(let i=0;i<frm.doc.items.length;i++){
                if(!doctype_ref && !doctype_ref_id && frm.doc.items[i].source_ref_document && frm.doc.items[i].source_ref_id){
                    doctype_ref = frm.doc.items[i].source_ref_document
                    doctype_ref_id = frm.doc.items[i].source_ref_id
                }
            }
            if(doctype_ref && doctype_ref_id){
                frm.add_custom_button(__(`View ${doctype_ref}`), function(){
                    frappe.set_route("Form", doctype_ref, doctype_ref_id);
                });
            }
		}
	},
    before_submit(frm){
        if(frm.doc.items){
            let doctype_ref;
            let doctype_ref_id;
            for(let i=0;i<frm.doc.items.length;i++){
                if(!doctype_ref && !doctype_ref_id && frm.doc.items[i].source_ref_document && frm.doc.items[i].source_ref_id){
                    doctype_ref = frm.doc.items[i].source_ref_document
                    doctype_ref_id = frm.doc.items[i].source_ref_id
                }
            }
            if(doctype_ref && doctype_ref_id){
                if(doctype_ref == "Delivery Challan Receipt" || doctype_ref == "Inspection Entry" || doctype_ref == "Moulding Production Entry" || doctype_ref == "Deflashing Receipt Entry"){
                    frappe.call({
                        method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.validate_document_submission',
                        args: {
                            doc_type:doctype_ref,
                            doc_name:doctype_ref_id,
                            stock_details:JSON.stringify(frm.doc)
                        },
                        freeze: true,
                        callback: function (f) {
                            if(f){
                                if(f.status == "failed"){
                                    frappe.validated = false
                                    frappe.msgprint(f.message)
                                }
                            }
                            else{
                                frappe.validated = false
                                frappe.msgprint(`Not able to fetch <b>${doctype_ref}</b> submission details..!`)
                            }
                        }
                    });
                }
            }
		}
    },
    before_cancel(frm){
        if(frm.doc.items){
            let doctype_ref;
            let doctype_ref_id;
            for(let i=0;i<frm.doc.items.length;i++){
                if(!doctype_ref && !doctype_ref_id && frm.doc.items[i].source_ref_document && frm.doc.items[i].source_ref_id){
                    doctype_ref = frm.doc.items[i].source_ref_document
                    doctype_ref_id = frm.doc.items[i].source_ref_id
                }
            }
            if(doctype_ref && doctype_ref_id){
                let docs = ["Inspection Entry","Packing","Sub Lot Creation","Material Transfer","Deflashing Receipt Entry","Delivery Challan Receipt",
                            "Batch ERP Entry","Lot Resource Tagging","Moulding Production Entry","Blank Bin Inward Entry",
                            "Blank Bin Rejection Entry","Cut Bit Transfer"]
                if(docs.includes(doctype_ref)){
                    frappe.call({
                        method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.validate_dc_document_cancellation',
                        args: {
                            doc_type:doctype_ref,
                            doc_name:doctype_ref_id,
                            ref_document:"Stock Entry"
                        },
                        freeze: true,
                        callback: function (f) {
                            if(f){
                                if(f.status == "failed"){
                                    frappe.validated = false
                                    frappe.msgprint(f.message)
                                }
                            }
                            else{
                                frappe.validated = false
                                frappe.msgprint(`Not able to fetch <b>${doctype_ref}</b> details..!`)
                            }
                        }
                    });
                }
            }
		}
    }
});

frappe.ui.form.on("Delivery Note",{
    timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm);
	},
	refresh:(frm) =>{
		frm.events.view_stock_entry(frm)
	},
    view_stock_entry:(frm) =>{
		if(frm.doc.reference_name && frm.doc.reference_document){
            frm.add_custom_button(__(`View ${frm.doc.reference_document}`), function(){
                frappe.set_route("Form", frm.doc.reference_document, frm.doc.reference_name);
            });
		}
	},
    before_cancel(frm){
        if(frm.doc.items){
            let doctype_ref = frm.doc.reference_document ? frm.doc.reference_document : ""
            let doctype_ref_id = frm.doc.reference_document ? frm.doc.reference_name : ""
            if(doctype_ref && doctype_ref_id){
                if(doctype_ref == "Deflashing Despatch Entry" || doctype_ref == "Despatch To U1 Entry" || doctype_ref == "Material Transfer"){
                    frappe.call({
                        method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.validate_dc_document_cancellation',
                        args: {
                            doc_type:doctype_ref,
                            doc_name:doctype_ref_id,
                            ref_document:"Delivery Note"
                        },
                        freeze: true,
                        callback: function (f) {
                            if(f){
                                if(f.status == "failed"){
                                    frappe.validated = false
                                    frappe.msgprint(f.message)
                                }
                            }
                            else{
                                frappe.validated = false
                                frappe.msgprint(`Not able to fetch <b>${doctype_ref}</b> details..!`)
                            }
                        }
                    });
                }
            }
		}
    }
});
