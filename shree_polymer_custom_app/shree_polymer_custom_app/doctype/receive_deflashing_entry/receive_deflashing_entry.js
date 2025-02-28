// Copyright (c) 2025, Tridotstech and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Receive Deflashing Entry", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2025, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Receive Deflashing Entry", {
    scan_lot_number: function(frm) {
        if (frm.doc.scan_lot_number) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Deflashing Despatch Entry',
                    filters: {
                        'lot_number': frm.doc.scan_lot_number
                    },
                    fields: ['*']
                },
                callback: function(response) {
                    if (response.message && response.message.length > 0) {
                        // Found matching record
                        let despatch_entry = response.message[0];
                        console.log(despatch_entry);
                        // Set values from despatch entry to current form
                        // Add the fields you want to populate here
                        frm.refresh();
                    } else {
                        frappe.msgprint(__('No Deflashing Despatch Entry found for this Lot Number'));
                        frm.doc.scan_lot_number = '';
                        frm.refresh_field('scan_lot_number');
                    }
                }
            });
        }
    }
});