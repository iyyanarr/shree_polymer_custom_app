// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('SPP Delivery Challan', {
	refresh: function(frm) {
		// if(frm.doc.status!="Completed" && !frm.doc.__islocal){
		// 	 frm.add_custom_button(__("Receive DC"), function() {
     	// 		frappe.route_options = {"dc_no":frm.doc.name};
		// 		frappe.new_doc("DC Receipt");

        //     })
        //     $('button[data-label="Receive%20DC"]').attr("class","btn btn-xs");
        //     $('button[data-label="Receive%20DC"]').attr("style","background:#1b8fdb;color:#fff;margin-left: 10px;");
		// }
	},
	
});
