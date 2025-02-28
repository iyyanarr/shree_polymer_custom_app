frappe.ui.form.on('Receive Deflashing Entry', {
    refresh: function(frm) {
        // Adding HTML button
        frm.fields_dict.get_items.$wrapper.html('<button class="btn btn-primary">Get Items</button>');

        frm.fields_dict.get_items.$wrapper.find('button').on('click', function() {
            const ddNumber = frm.doc.dd_number; // Assuming dd_number is the fieldname for Deflash Despatch Number
            
            if (!ddNumber) {
                frappe.msgprint(__('Please enter a Deflash Despatch Number.'));
                return;
            }

            frappe.call({
                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.receive_deflashing_entry.receive_deflashing_entry.get_despatch_info',
                args: {
                    dd_number: ddNumber
                },
                callback: function(response) {
                    if (response && response.message) {
                        const despatchInfo = response.message;

                        // Construct HTML to display despatch info
                        let html = `
                            <h4>Despatch Info</h4>
                            <p>Name: ${despatchInfo.name}</p>
                            <p>Owner: ${despatchInfo.owner}</p>
                            <p>Vehicle No: ${despatchInfo.vehicle_no}</p>
                            <p>Vendor: ${despatchInfo.vendor}</p>
                            <p>Total Lots: ${despatchInfo.total_lots}</p>
                            <p>Total Qty (Kgs): ${despatchInfo.total_qty_kgs}</p>
                            <p>Total Qty (Nos): ${despatchInfo.total_qty_nos}</p>
                            <h5>Items:</h5>
                        `;

                        despatchInfo.items.forEach(item => {
                            html += `
                                <div>
                                    <p>Product Ref: ${item.product_ref}</p>
                                    <p>Qty Nos: ${item.qty_nos}</p>
                                    <p>Lot No: ${item.lot_no}</p>
                                    <p>Weight (Kgs): ${item.weight_kgs}</p>
                                </div>
                                <hr>
                            `;
                        });

                        frm.fields_dict.despatch_info.$wrapper.html(html);
                    }
                }
            });
        });
    }
});
