frappe.ui.form.on('Receive Deflashing Entry', {
    refresh: function(frm) {
        // Adding HTML button for Get Items
        frm.fields_dict.get_items.$wrapper.html('<button class="btn btn-primary">Get Items</button>');

        // Adding button for creating stock entries from scanned items
        frm.events.render_create_stock_entries_button(frm);

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
                        frm.despatchInfo = despatchInfo; // Store for later use

                        frappe.model.get_value('SPP Settings', {'name': 'SPP Settings'}, 'weight_tolerance', function(d) {
                            const tolerance = d.weight_tolerance;

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

                            frm.fields_dict.despatch_info.$wrapper.html(despatchHtml);
                            frm.events.update_despatch_item_info(frm);
                            frm.events.render_create_stock_entries_button(frm);

                            // Add event listener for scan_lot_no field
                            frm.fields_dict.scan_lot_no.$input.on('change', function() {
                                const scanLotNumber = frm.doc.scan_lot_no;
                                // Check if lot is already scanned
                                const existingItem = frm.doc.items && frm.doc.items.find(row => row.lot_no === scanLotNumber);
                                if (existingItem) {
                                    frappe.msgprint({
                                        title: __('Duplicate Entry'),
                                        indicator: 'red',
                                        message: __(`Lot number ${scanLotNumber} has already been scanned and processed.`)
                                    });
                                    frm.set_value('scan_lot_no', '');
                                    return;
                                }

                                const item = despatchInfo.items.find(item => item.lot_no === scanLotNumber);
                                if (item) {
                                    frm.events.show_observed_weight_dialog(frm, item, tolerance);
                                } else {
                                    frappe.msgprint(__('Lot number not found in despatch.'));
                                }
                                frm.set_value('scan_lot_no', '');
                            });
                        });
                    }
                }
            });
        });
    },

    render_create_stock_entries_button: function(frm) {
        const items = frm.doc.items || [];
        const validItems = items.filter(item =>
            item.status === 'Received' || item.status === 'Miss Match'
        );

        const buttonHtml = `
            <button class="btn btn-primary ${validItems.length ? '' : 'disabled'}"
                ${validItems.length ? '' : 'disabled'}>
                Create Stock Entries (${validItems.length} items)
            </button>
        `;
        frm.fields_dict.receive_scanned_items.$wrapper.html(buttonHtml);

        if (validItems.length) {
            frm.fields_dict.receive_scanned_items.$wrapper.find('button').on('click', function() {
                frm.events.create_stock_entries(frm, validItems);
            });
        }
    },

    create_stock_entries: function(frm, items) {
        if (!items.length) {
            frappe.msgprint(__('No valid items to create stock entries for.'));
            return;
        }

        frappe.confirm(
            __(`This will create stock entries for ${items.length} items. Continue?`),
            function() {
                // Show processing indicator
                frappe.show_alert({
                    message: __('Creating stock entries...'),
                    indicator: 'blue'
                });

                // Call backend method to create stock entries
                frappe.call({
                    method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.receive_deflashing_entry.receive_deflashing_entry.create_stock_entries',
                    args: {
                        doc_name: frm.doc.name,
                        items: items.map(item => ({
                            lot_no: item.lot_no,
                            product_ref: item.product_ref,
                            received_weight: item.received_weight,
                            status: item.status,
                            stock_entry_reference: item.stock_entry_reference,
                            batch_no: item.batch_no
                        }))
                    },
                    freeze: true,
                    freeze_message: __('Creating Stock Entries...'),
                    callback: function(response) {
                        console.log(response);
                        if (response.message) {
                            // Update the status of processed items
                            const processedItems = response.message.processed_items || [];
                            const stockEntries = response.message.stock_entries || [];
                            if (processedItems.length) {
                                // Update item status in the table
                                frm.doc.items.forEach(item => {
                                    if (processedItems.includes(item.lot_no)) {
                                        item.stock_entry_created = 1;
                                        item.stock_entry_status = 'Created';
                                    }
                                });
                                frm.refresh_field('items');
                            }

                            // Show success message with links to created stock entries
                            let messageHtml = `<p>Successfully created ${stockEntries.length} stock entries:</p><ul>`;
                            stockEntries.forEach(entry => {
                                messageHtml += `<li><a href="/app/stock-entry/${entry}" target="_blank">${entry}</a></li>`;
                            });
                            messageHtml += `</ul>`;

                            frappe.msgprint(messageHtml);
                        }
                    }
                });
            }
        );
    },

    update_despatch_item_info: function(frm) {
        if (!frm.despatchInfo || !frm.despatchInfo.items) return;

        const items = frm.despatchInfo.items;
        const scannedLots = frm.doc.items ? frm.doc.items.map(item => item.lot_no) : [];

        let itemsHtml = `
            <div class="table-responsive">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Lot No.</th>
                            <th>Product</th>
                            <th>Weight (Kgs)</th>
                            <th>Qty (Nos)</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        items.forEach(item => {
            const isScanned = scannedLots.includes(item.lot_no);
            const scannedItem = isScanned ? frm.doc.items.find(i => i.lot_no === item.lot_no) : null;
            
            itemsHtml += `
                <tr class="${isScanned ? 'bg-light-green' : ''}">
                    <td>${item.lot_no}</td>
                    <td>${item.product_ref}</td>
                    <td>${item.weight_kgs}</td>
                    <td>${item.qty_nos}</td>
                    <td>${isScanned ? scannedItem.status : 'Pending'}</td>
                </tr>
            `;
        });

        itemsHtml += `
                    </tbody>
                </table>
            </div>
            <p class="text-muted">Scanned: ${scannedLots.length} of ${frm.despatchInfo.items.length} lots</p>
        `;

        frm.fields_dict.despatch_item_info.$wrapper.html(itemsHtml);
    },

    // Updated show_observed_weight_dialog function with the new conditions
    show_observed_weight_dialog: function(frm, item, tolerance) {
        const dialog = new frappe.ui.Dialog({
            title: 'Weight Measurement',
            fields: [
                { fieldname: 'item_name', label: 'Item Name', fieldtype: 'Data', default: item.product_ref, read_only: 1 },
                { fieldname: 'weight_kgs', label: 'System Weight (Kgs)', fieldtype: 'Float', default: item.weight_kgs, read_only: 1 },
                { fieldname: 'observed_weight', label: 'Observed Weight (Kgs)', fieldtype: 'Float', reqd: 1 }
            ],
            primary_action_label: 'Submit',
            primary_action(values) {
                const difference = values.observed_weight - values.weight_kgs;
                const abs_difference = Math.abs(difference);

                if (values.weight_kgs > values.observed_weight && abs_difference <= tolerance) {
                    // Condition: System weight is greater than observed weight, and the difference is within tolerance
                    frm.events.add_item_to_table(frm, item, values.observed_weight, 'Received');
                    dialog.hide();
                } else if (values.weight_kgs > values.observed_weight && abs_difference > tolerance) {
                    // Condition: System weight is greater than observed weight, but the difference exceeds tolerance
                    frm.events.add_item_to_table(frm, item, values.observed_weight, 'Miss Match');
                    frm.events.create_weight_mismatch_tracker(frm, item, values.observed_weight, difference);
                    dialog.hide();
                } else if (values.weight_kgs < values.observed_weight && abs_difference <= tolerance) {
                    // Condition: System weight is less than observed weight, but the difference is within tolerance
                    frm.events.add_item_to_table(frm, item, values.observed_weight, 'Received');
                    dialog.hide();
                } else if (values.weight_kgs < values.observed_weight && abs_difference > tolerance) {
                    // Condition: System weight is less than observed weight, and the difference exceeds tolerance
                    frappe.msgprint({
                        title: __('Weight Mismatch Tracker Created'),
                        indicator: 'red',
                        message: __('Observed weight exceeds system weight and difference is greater than tolerance. Raising a Weight Mismatch Tracker.')
                    });
                    frm.events.create_weight_mismatch_tracker(frm, item, values.observed_weight, difference);
                    dialog.hide();
                }
            }
        });
        dialog.show();
    },

    confirm_weight_mismatch_action: function(frm, item, observed_weight, difference) {
        let difference_description = difference < 0 ? "negative" : "excess";

        let confirm_dialog = new frappe.ui.Dialog({
            title: 'Confirm Action',
            fields: [
                {
                    fieldtype: 'HTML',
                    options: `<p>Weight difference of <b>${(Math.abs(difference) * 1000).toFixed(2)} grams</b> is ${difference_description}.</p>
                    <p>What would you like to do?</p>`
                }
            ],
            primary_action_label: 'Request Approval',
            primary_action: () => {
                frm.events.create_weight_mismatch_tracker(frm, item, observed_weight, difference);
                confirm_dialog.hide();
            }
        });

        confirm_dialog.set_secondary_action_label('Cancel Transaction');
        confirm_dialog.set_secondary_action(() => {
            confirm_dialog.hide();
            frappe.msgprint('Transaction cancelled by user.');
        });

        confirm_dialog.show();
    },

    create_weight_mismatch_tracker: function(frm, item, observed_weight, difference) {
        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Weight Mismatch Tracker",
                    ref_production_entry: item.stock_entry_reference || "",
                    ref_lot_number: item.lot_no || "",
                    observed_weight: observed_weight,
                    difference_in_weight: difference,
                    item_code: item.product_ref,
                    batch_number: item.batch_no,
                    system_weight: item.weight_kgs,
                    warehouse: item.warehouse,
                    observed_by: frappe.session.user,
                }
            },
            freeze: true,
            callback: function(response) {
                if (!response.exc) {
                    frappe.msgprint({
                        title: __("Success"),
                        indicator: "green",
                        message: __(
                            `Weight Mismatch Tracker <b>${response.message.name}</b> created successfully.`
                        )
                    });
                    // Only add to table for specific conditions - handled in the dialog function
                } else {
                    frappe.msgprint({
                        title: __("Error"),
                        indicator: "red",
                        message: __("Unable to create Weight Mismatch Tracker.")
                    });
                }
            }
        });
    },

    add_item_to_table: function(frm, item, observed_weight, status) {
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
        child.stock_entry_reference = item.stock_entry_reference;
        child.amount = item.amount;
        child.received_weight = observed_weight;
        child.weight_difference = Math.abs(observed_weight - item.weight_kgs).toFixed(3);
        child.status = status;
        child.stock_entry_created = 0;
        child.stock_entry_status = 'Pending';
        frm.refresh_field('items');
        // Update the despatch item info display
        frm.events.update_despatch_item_info(frm);
        // Re-render the create stock entries button
        frm.events.render_create_stock_entries_button(frm);
    }
});
