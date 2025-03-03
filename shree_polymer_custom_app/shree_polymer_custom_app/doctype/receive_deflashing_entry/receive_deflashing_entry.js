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

                        // Fetch tolerance value from spp_settings
                        frappe.model.get_value('SPP Settings', {'name': 'SPP Settings'}, 'weight_tolerance', function(d) {
                            const tolerance = d.weight_tolerance;

                            // Construct HTML to display despatch info
                            let despatchHtml = `
                                <h4>Despatch Info</h4>
                                <p>Name: ${despatchInfo.name}</p>
                                <p>Owner: ${despatchInfo.owner}</p>
                                <p>Vehicle No: ${despatchInfo.vehicle_no}</p>
                                <p>Vendor: ${despatchInfo.vendor}</p>
                                <p>Total Lots: ${despatchInfo.total_lots}</p>
                                <p>Total Qty (Kgs): ${despatchInfo.total_qty_kgs}</p>
                                <p>Total Qty (Nos): ${despatchInfo.total_qty_nos}</p>
                            `;

                            let itemsHtml = `
                                <h5>Number of Lots: ${despatchInfo.items.length}</h5>
                            `;

                            frm.fields_dict.despatch_info.$wrapper.html(despatchHtml);
                            frm.fields_dict.despatch_item_info.$wrapper.html(itemsHtml);

                            // Add event listener for scan_lot_no field
                            frm.fields_dict.scan_lot_no.$input.on('change', function() {
                                const scanLotNumber = frm.doc.scan_lot_no;
                                const item = despatchInfo.items.find(item => item.lot_no === scanLotNumber);

                                if (item) {
                                    // Show dialog box to enter observed weight
                                    const dialog = new frappe.ui.Dialog({
                                        title: 'Enter Observed Weight',
                                        fields: [
                                            { fieldname: 'item_name', label: 'Item Name', fieldtype: 'Data', default: item.product_ref, read_only: 1 },
                                            { fieldname: 'weight_kgs', label: 'Weight (Kgs)', fieldtype: 'Float', default: item.weight_kgs, read_only: 1 },
                                            { fieldname: 'observed_weight', label: 'Observed Weight (Kgs)', fieldtype: 'Float' }
                                        ],
                                        primary_action_label: 'Add Item',
                                        primary_action(values) {
                                            const weightDifference = Math.abs(item.weight_kgs - values.observed_weight);

                                            if (weightDifference <= tolerance) {
                                                // Add item to child table
                                                const child = frm.add_child('items');
                                                child.qty_uom = item.qty_uom;
                                                child.spp_batch_no = item.spp_batch_no;
                                                child.product_ref = item.product_ref;
                                                child.qty_nos = item.qty_nos;
                                                child.vendor = item.vendor;
                                                child.valuation_rate = item.valuation_rate;
                                                child.batch_no = item.batch_no;
                                                child.date = item.date;
                                                child.lot_no = item.lot_no;
                                                child.weight_kgs = item.weight_kgs;
                                                child.stock_entry_reference = despatchInfo.stock_entry_reference;
                                                child.amount = item.amount;
                                                child.received_weight = values.observed_weight;
                                                child.status = 'Received';
                                                frm.refresh_field('items');
                                                dialog.hide();
                                            } else {
                                                frappe.msgprint(__('Observed weight is out of tolerance range.'));
                                            }
                                        }
                                    });

                                    dialog.show();
                                } else {
                                    frappe.msgprint(__('Lot number not found.'));
                                }
                            });
                        });
                    }
                }
            });
        });
    }
});