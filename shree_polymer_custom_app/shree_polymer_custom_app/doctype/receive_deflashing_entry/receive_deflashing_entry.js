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

            // Check if dd_number already exists in Receive Deflashing Entry
            if (frm.is_new()) {
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Receive Deflashing Entry',
                        filters: {
                            dd_number: ddNumber
                        },
                        fields: ['name']
                    },
                    callback: function(response) {
                        if (response && response.message && response.message.length > 0) {
                            frappe.msgprint(__('The Deflash Despatch Number is already created in Receive Deflashing Entry.'));
                            frappe.set_route('Form', 'Receive Deflashing Entry', response.message[0].name);
                            return;
                        }

                        // Proceed with fetching despatch info if dd_number does not exist
                        fetchDespatchInfo();
                    }
                });
            } else {
                fetchDespatchInfo();
            }

            function fetchDespatchInfo() {
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
                                frm.set_value('total_received_lots', despatchInfo.total_lots);
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
            }
        });

        // Add Report Discrepancy button with enhanced styling
        frm.add_custom_button(__('Report Discrepancy'), function() {
            frm.events.show_discrepancy_dialog(frm);
        }, __('Actions')).addClass('btn-warning report-discrepancy-btn');

        // Add custom CSS for the button
        if (!document.getElementById('report-discrepancy-styles')) {
            const styles = `
                <style id="report-discrepancy-styles">
                    .report-discrepancy-btn {
                        background-color: #ff6b6b !important;
                        color: white !important;
                        font-weight: 500 !important;
                        border: none !important;
                        padding: 8px 15px !important;
                        margin-left: 10px !important;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
                        transition: all 0.3s ease !important;
                    }
                    .report-discrepancy-btn:hover {
                        background-color: #ff5252 !important;
                        transform: translateY(-1px) !important;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
                    }
                    .report-discrepancy-btn:active {
                        transform: translateY(0) !important;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
                    }
                </style>
            `;
            $(styles).appendTo('head');
        }
    },

    render_create_stock_entries_button: function(frm) {
        const items = frm.doc.items || [];
        // Filter items that have status 'Received' or 'Miss Match' AND stock_entry_status 'Not Created'
        const validItems = items.filter(item => 
            (item.status === 'Received' || item.status === 'Miss Match') && 
            item.stock_entry_status === 'Not Created'
        );

        const buttonHtml = `
            <button class="btn btn-primary ${validItems.length ? '' : 'disabled'}"
                ${validItems.length ? '' : 'disabled'}>
                Create Stock Entries (${validItems.length} pending items)
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

        // Check if document is new/unsaved
        if (frm.is_new()) {
            frappe.msgprint(__('Please save the document before creating stock entries.'));
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
                            qty_nos: item.qty_nos,
                            received_product_qty_nos:item.received_product_qty_nos,
                            received_weight: item.received_weight,
                            status: item.status,
                            stock_entry_reference: item.stock_entry_reference,
                            batch_no: item.batch_no
                        }))
                    },
                    freeze: true,
                    freeze_message: __('Creating Stock Entries...'),
                    callback: function(response) {
                        if (response.message) {
                            // Update the status of processed items
                            const processedItems = response.message.processed_items || [];
                            const stockEntries = response.message.stock_entries || [];
                            
                            if (processedItems.length) {
                                frm.doc.items.forEach(item => {
                                    if (processedItems.includes(item.lot_no)) {
                                        frappe.model.set_value(item.doctype, item.name, 'stock_entry_status', 'Created');
                                    }
                                });
                                frm.refresh_field('items');
                                frm.reload_doc(); // Reload to get latest data
                            }

                            // Show success message
                            let messageHtml = `<p>Successfully created ${stockEntries.length} stock entries:</p><ul>`;
                            stockEntries.forEach(entry => {
                                messageHtml += `<li><a href="/app/stock-entry/${entry}" target="_blank">${entry}</a></li>`;
                            });
                            messageHtml += `</ul>`;

                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: messageHtml
                            });
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

        // Custom CSS styles for the table
        const customStyles = `
            <style>
                .item-table .scanned-row {
                    background-color: rgba(40, 167, 69, 0.15); /* Light green with transparency */
                    transition: background-color 0.3s ease;
                }
                .item-table .scanned-row:hover {
                    background-color: rgba(40, 167, 69, 0.25); /* Slightly darker on hover */
                }
                .status-indicator {
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    margin-right: 5px;
                }
                .status-received .status-indicator {
                    background-color: #28a745; /* Green */
                }
                .status-miss-match .status-indicator {
                    background-color: #ffc107; /* Yellow */
                }
                .status-pending .status-indicator {
                    background-color: #6c757d; /* Gray */
                }
                .progress-bar-container {
                    background-color: #e9ecef;
                    border-radius: 4px;
                    height: 20px;
                    margin-top: 10px;
                    overflow: hidden;
                }
                .progress-bar {
                    height: 100%;
                    background-color: #28a745;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    line-height: 20px;
                    transition: width 0.5s ease;
                }
            </style>
        `;

        let itemsHtml = customStyles + `
            <div class="table-responsive">
                <table class="table table-bordered item-table">
                    <thead class="thead-light">
                        <tr>
                            <th>Status</th>
                            <th>Lot No.</th>
                            <th>Product</th>
                            <th>Weight (Kgs)</th>
                            <th>Qty (Nos)</th>
                            <th>Received Weight</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        items.forEach(item => {
            const isScanned = scannedLots.includes(item.lot_no);
            const scannedItem = isScanned ? frm.doc.items.find(i => i.lot_no === item.lot_no) : null;
            
            let statusClass = 'status-pending';
            let statusLabel = 'Pending';
            let receivedWeight = '';
            
            if (isScanned) {
                statusClass = scannedItem.status === 'Received' ? 'status-received' : 'status-miss-match';
                statusLabel = scannedItem.status;
                receivedWeight = scannedItem.received_weight;
            }
            
            itemsHtml += `
                <tr class="${isScanned ? 'scanned-row' : ''}" ${isScanned ? 'title="Scanned"' : ''}>
                    <td class="${statusClass}"><span class="status-indicator"></span>${statusLabel}</td>
                    <td><strong>${item.lot_no}</strong></td>
                    <td>${item.product_ref}</td>
                    <td>${item.weight_kgs}</td>
                    <td>${item.qty_nos}</td>
                    <td>${isScanned ? `<strong>${receivedWeight}</strong>` : '-'}</td>
                </tr>
            `;
        });

        // Calculate progress percentage
        const progress = scannedLots.length / frm.despatchInfo.items.length * 100;
        
        itemsHtml += `
                    </tbody>
                </table>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${progress}%">
                    ${scannedLots.length} of ${frm.despatchInfo.items.length} (${Math.round(progress)}%)
                </div>
            </div>
            <p class="text-muted mt-2">
                <span class="badge badge-pill badge-light">
                    <i class="fa fa-info-circle"></i> 
                    Scan each lot number to process items
                </span>
            </p>
        `;

        frm.fields_dict.despatch_item_info.$wrapper.html(itemsHtml);
    },

    show_observed_weight_dialog: function(frm, item, tolerance) {
        console.log(item);
        // Fetch the target warehouse from SPP Settings
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'SPP Settings',
                fieldname: 'p_target_warehouse'
            },
            callback: function(settingsResponse) {
                if (settingsResponse && settingsResponse.message) {
                    const targetWarehouse = settingsResponse.message.p_target_warehouse;
                    console.log(targetWarehouse);

                    // Fetch the quantity from Item Batch Stock Balance
                    frappe.call({
                        method: 'frappe.client.get_value',
                        args: {
                            doctype: 'Item Batch Stock Balance',
                            filters: {
                                item_code: item.product_ref,
                                batch_no: item.batch_no,
                                warehouse: targetWarehouse
                            },
                            fieldname: ['qty'] // Assuming 'qty_nos' is the field for quantity in numbers
                        },
                        callback: function(response) {
                            if (response && response.message) {
                                const systemQtyNos = response.message.qty;

                                // Fetch the conversion factor for the item
                                frappe.call({
                                    method: 'frappe.client.get',
                                    args: {
                                        doctype: 'Item',
                                        name: item.product_ref
                                    },
                                    callback: function(itemResponse) {
                                        if (itemResponse && itemResponse.message) {
                                            const itemData = itemResponse.message;
                                            const conversionFactor = itemData.uoms.find(uom => uom.uom === 'Kg').conversion_factor;
                                            const systemWeight = systemQtyNos / conversionFactor;

                                            const dialog = new frappe.ui.Dialog({
                                                title: 'Weight Measurement',
                                                fields: [
                                                    { fieldname: 'item_name', label: 'Item Name', fieldtype: 'Data', default: item.product_ref, read_only: 1 },
                                                    { fieldname: 'weight_kgs', label: 'System Weight (Kgs)', fieldtype: 'Float', default: systemWeight, read_only: 1 },
                                                    { fieldname: 'observed_weight', label: 'Observed Weight (Kgs)', fieldtype: 'Float', reqd: 1 },
                                                    { fieldname: 'system_qty_nos', label: 'System Qty (Nos)', fieldtype: 'Float', default: systemQtyNos, read_only: 1 },
                                                    { fieldname: 'observed_qty_nos', label: 'Observed Qty (Nos)', fieldtype: 'Float', reqd: 1 },
                                                    { fieldname: 'conversion_factor', label: 'Conversion Factor', fieldtype: 'Float', default: conversionFactor, read_only: 1 }
                                                ],
                                                primary_action_label: 'Submit',
                                                primary_action: function(values) {
                                                    const weightDifference = values.observed_weight - values.weight_kgs;
                                                    const absWeightDifference = Math.abs(weightDifference);
                                                    const qtyDifference = values.observed_qty_nos - values.system_qty_nos;
                                                    const absQtyDifference = Math.abs(qtyDifference);

                                                    // Handle equal weights and quantities case
                                                    if (values.weight_kgs === values.observed_weight && values.system_qty_nos === values.observed_qty_nos) {
                                                        frm.events.add_item_to_table(frm, item, values.observed_weight, values.observed_qty_nos, 'Received');
                                                        dialog.hide();
                                                        return;
                                                    }

                                                    if (values.weight_kgs > values.observed_weight && absWeightDifference <= tolerance) {
                                                        // Within tolerance: Add item with Received status
                                                        frm.events.add_item_to_table(frm, item, values.observed_weight, values.observed_qty_nos, 'Received');
                                                        dialog.hide();
                                                    } else if (values.weight_kgs > values.observed_weight && absWeightDifference > tolerance) {
                                                        // Exceeds tolerance: Show alert and create weight mismatch
                                                        frappe.confirm(
                                                            __('Weight difference exceeds tolerance and system weight is greater than observed weight. Do you want to create a weight mismatch tracker?'),
                                                            () => {
                                                                // If confirmed, add item with Miss Match status and create tracker
                                                                frm.events.create_weight_mismatch_tracker(frm, item, values.observed_weight, weightDifference);
                                                                dialog.hide();
                                                            },
                                                            () => {
                                                                // If cancelled, just close the dialog
                                                                dialog.hide();
                                                            }
                                                        );
                                                    } else if (values.weight_kgs < values.observed_weight && absWeightDifference <= tolerance) {
                                                        // Within tolerance: Add item with Received status
                                                        frm.events.add_item_to_table(frm, item, values.observed_weight, values.observed_qty_nos, 'Received');
                                                        dialog.hide();
                                                    } else if (values.weight_kgs < values.observed_weight && absWeightDifference > tolerance) {
                                                        // Exceeds tolerance: Show alert and create weight mismatch
                                                        frappe.confirm(
                                                            __('Weight difference exceeds tolerance and observed weight is greater than system weight. Do you want to create a weight mismatch tracker?'),
                                                            () => {
                                                                // If confirmed, add item with Miss Match status and create tracker
                                                                frm.events.create_weight_mismatch_tracker(frm, item, values.observed_weight, weightDifference);
                                                                dialog.hide();
                                                            },
                                                            () => {
                                                                // If cancelled, just close the dialog
                                                                dialog.hide();
                                                            }
                                                        );
                                                    }
                                                }
                                            });

                                            // Update observed_qty_nos based on observed_weight and conversion_factor
                                            dialog.fields_dict.observed_weight.$input.on('change', function() {
                                                const observedWeight = parseFloat(dialog.get_value('observed_weight'));
                                                const conversionFactor = parseFloat(dialog.get_value('conversion_factor'));
                                                const observedQtyNos = observedWeight * conversionFactor;
                                                dialog.set_value('observed_qty_nos', observedQtyNos);
                                            });

                                            dialog.show();
                                        } else {
                                            frappe.msgprint(__('Unable to fetch conversion factor for the item.'));
                                        }
                                    }
                                });
                            } else {
                                frappe.msgprint(__('Unable to fetch system weight for the item.'));
                            }
                        }
                    });
                } else {
                    frappe.msgprint(__('Unable to fetch target warehouse from SPP Settings.'));
                }
            }
        });
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
                    source_document: frm.doc.dd_number,
                    dispatch_station: "U2 Store",
                    receiving_station: "U1 Store",
                    batch_number: item.batch_no,
                    system_weight: item.weight_kgs,
                    warehouse: 'U1-Transit Store - SPP INDIA',
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

    add_item_to_table: function(frm, item, observed_weight,observed_qty_nos, status) {
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
        child.received_product_qty_nos = observed_qty_nos;
        child.stock_entry_status = 'Not Created';
        child.weight_difference = Math.abs(observed_weight - item.weight_kgs).toFixed(3);
        child.status = status;
        frm.refresh_field('items');
        // Update the despatch item info display
        frm.events.update_despatch_item_info(frm);
        // Re-render the create stock entries button
        frm.events.render_create_stock_entries_button(frm);
    },

    show_discrepancy_dialog: function(frm) {
        const dialog = new frappe.ui.Dialog({
            title: __('Report Discrepancy'),
            fields: [
                {
                    fieldname: 'delivery_note',
                    label: __('Delivery Note (DC) Number'),
                    fieldtype: 'Data',
                    default: frm.doc.dd_number,
                    read_only: 1
                },
                {
                    fieldname: 'discrepancy_type',
                    label: __('Discrepancy Type'),
                    fieldtype: 'Select',
                    options: [
                        'Items Not Found',
                        'Items Found But Not Listed'
                    ],
                    reqd: 1
                },
                {
                    fieldname: 'warehouse_from',
                    label: __('Warehouse From'),
                    fieldtype: 'Link',
                    options: 'Warehouse',
                    default: 'U2 Store',
                    read_only: 1
                },
                {
                    fieldname: 'warehouse_to',
                    label: __('Warehouse To'),
                    fieldtype: 'Link',
                    options: 'Warehouse',
                    default: 'U1-Transit Store - SPP INDIA',
                    read_only: 1
                },
                {
                    fieldname: 'section_break_1',
                    fieldtype: 'Section Break',
                    label: __('Item Details')
                },
                {
                    fieldname: 'items',
                    fieldtype: 'Table',
                    label: __('Items'),
                    cannot_add_rows: false,
                    fields: [
                        {
                            fieldname: 'item_code',
                            fieldtype: 'Link',
                            options: 'Item',
                            in_list_view: 1,
                            label: __('Item Code'),
                            reqd: 1
                        },
                        {
                            fieldname: 'item_name',
                            fieldtype: 'Data',
                            in_list_view: 1,
                            label: __('Item Description'),
                            fetch_from: 'item_code.item_name'
                        },
                        {
                            fieldname: 'qty_as_per_dc',
                            fieldtype: 'Float',
                            in_list_view: 1,
                            label: __('Quantity as per DC'),
                            reqd: 1
                        },
                        {
                            fieldname: 'qty_found',
                            fieldtype: 'Float',
                            in_list_view: 1,
                            label: __('Quantity Found'),
                            reqd: 1
                        },
                        {
                            fieldname: 'comments',
                            fieldtype: 'Data',
                            in_list_view: 1,
                            label: __('Comments')
                        }
                    ]
                },
                {
                    fieldname: 'section_break_2',
                    fieldtype: 'Section Break'
                },
                {
                    fieldname: 'remarks',
                    label: __('Remarks'),
                    fieldtype: 'Text Editor'
                },
                {
                    fieldname: 'attachments',
                    label: __('Attachments'),
                    fieldtype: 'Attach',
                    allow_multiple: 1
                }
            ],
            primary_action_label: __('Submit'),
            primary_action: function(values) {
                frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'Discrepancy Report',
                            delivery_note: values.delivery_note,
                            discrepancy_type: values.discrepancy_type,
                            warehouse_from: values.warehouse_from,
                            warehouse_to: values.warehouse_to,
                            items: values.items,
                            remarks: values.remarks,
                            attachments: values.attachments,
                            status: 'Open',
                            reported_by: frappe.session.user
                        }
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: __('Discrepancy Report {0} created successfully', 
                                    [`<a href="/app/discrepancy-report/${r.message.name}" target="_blank">${r.message.name}</a>`])
                            });
                            dialog.hide();
                        }
                    }
                });
            }
        });

        dialog.show();
    }
});


