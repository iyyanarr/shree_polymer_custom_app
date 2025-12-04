// // Copyright (c) 2023, Tridotstech and contributors
// // For license information, please see license.txt

frappe.ui.form.on('Deflashing Despatch Entry', {

    timeline_refresh: frm => {
        frm.events.view_stock_entry(frm);
    },

    view_stock_entry: frm => {
        if (frm.doc.docstatus == 1 && frm.doc.stock_entry_reference) {
            frm.add_custom_button(__("View Stock Entry"), function () {
                let dc_ids = frm.doc.stock_entry_reference.split(',');
                if (dc_ids.length > 1) {
                    frappe.route_options = { "name": ["in", dc_ids] };
                    frappe.set_route("List", "Stock Entry");
                } else {
                    frappe.set_route("Form", "Stock Entry", dc_ids[0]);
                }
            });
        } else {
            frm.remove_custom_button('View Stock Entry');
        }

        if (!frm.doc.posting_date) {
            frm.set_value('posting_date', frappe.datetime.now_date());
            refresh_field('posting_date');
        }
    },

    refresh: frm => {
        frm.events.view_stock_entry(frm);

        // Add "View Lot Details" button for submitted documents with items
        if (frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            // Check if any item has a lot number
            const hasLots = frm.doc.items.some(item => item.lot_number);
            if (hasLots) {
                frm.add_custom_button(__('View Lot Details'), function () {
                    show_deflashing_lot_selector(frm);
                });
            }
        }

        frm.set_df_property("qty", "hidden", 1);
        if (frm.doc.docstatus == 1) {
            frm.set_df_property("scan_section", "hidden", 1);
        }
        if (frm.doc.scan_deflashing_vendor) {
            frm.set_df_property("scan_deflashing_vendor", "hidden", 1);
        }
        if (frm.doc.docstatus == 0) {
            frm.trigger('add');
        }
    },

    scan_lot_number: frm => {
        if (frm.doc.scan_lot_number && frm.doc.scan_lot_number !== undefined) {
            // First, check if Lot Inspection is submitted for this lot
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Inspection Entry',
                    filters: {
                        lot_no: frm.doc.scan_lot_number,
                        inspection_type: 'Lot Inspection',
                        docstatus: 1
                    },
                    fieldname: ['name', 'batch_no', 'total_inspected_qty_nos', 'total_rejected_qty']
                },
                freeze: true,
                callback: function (r) {
                    if (!r.message) {
                        // Lot Inspection not found or not submitted
                        frappe.msgprint({
                            title: __('Lot Inspection Required'),
                            indicator: 'red',
                            message: __('Lot Inspection must be completed and submitted for lot <b>{0}</b> before it can be dispatched for deflashing.', [frm.doc.scan_lot_number])
                        });
                        frm.events.reset_scan_fields(frm);
                        return;
                    }

                    // Lot Inspection exists and is submitted - proceed with lot validation
                    frappe.msgprint({
                        title: __('Lot Inspection Verified'),
                        indicator: 'green',
                        message: __('Lot Inspection <b>{0}</b> found and verified ✓', [r.message.name])
                    });

                    // Now validate the lot barcode
                    frappe.call({
                        method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_lot_barcode',
                        args: { bar_code: frm.doc.scan_lot_number },
                        freeze: true,
                        callback: function (r) {
                            if (r && r.status == "failed") {
                                frappe.msgprint(r.message);
                                frm.events.reset_scan_fields(frm);
                            } else if (r && r.status == "success") {
                                if (frm.doc.items && frm.doc.items.length > 0) {
                                    let flag = false;
                                    frm.doc.items.map(res => {
                                        if (res.lot_number === frm.doc.scan_lot_number) {
                                            flag = true;
                                            frappe.validated = false;
                                            frappe.msgprint(`Scanned lot <b>${frm.doc.scan_lot_number}</b> already added.`);
                                            frm.set_value("scan_lot_number", "");
                                            return;
                                        }
                                    });
                                    if (flag) {
                                        return;
                                    }
                                }
                                frm.set_df_property("qty", "hidden", 0);
                                frm.set_value("batch_no", r.batch_no);
                                frm.set_value("spp_batch_no", r.spp_batch_number);
                                frm.set_value("job_card", r.job_card);
                                frm.set_value("item", r.item);
                                frm.set_value("qty", r.qty);
                                frm.set_value("lot_number", frm.doc.scan_lot_number.toUpperCase());
                                frm.set_value("source_warehouse_id", r.from_warehouse);
                                frm.set_value("valuation_rate", r.valuation_rate);
                                frm.set_value("amount", r.amount);
                                frm.events.enable_disable_btn(frm);

                                // Fetch and display bin details for the scanned lot
                                fetch_and_display_bin_details(frm, frm.doc.scan_lot_number);
                            } else {
                                frappe.msgprint("Something went wrong.");
                            }
                        }
                    });
                }
            });
        } else {
            frm.events.enable_disable_btn(frm);
            // Clear bin details display when lot number is cleared
            if (frm.fields_dict.bin_details_display) {
                frm.fields_dict.bin_details_display.$wrapper.html('');
            }
        }
    },

    scan_deflashing_vendor: frm => {
        if (frm.doc.scan_deflashing_vendor && frm.doc.scan_deflashing_vendor !== undefined) {
            frappe.call({
                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_warehouse',
                args: { bar_code: frm.doc.scan_deflashing_vendor },
                freeze: true,
                callback: function (r) {
                    if (r && r.status == "failed") {
                        frappe.msgprint(r.message);
                        frm.events.reset_scan_fields(frm);
                    } else if (r && r.status == "success") {
                        frm.set_value("warehouse", r.warehouse_name);
                        frm.set_value("warehouse_id", r.name);
                        if (frm.doc.scan_deflashing_vendor) {
                            frm.set_value("scan_deflashing_vendor", frm.doc.scan_deflashing_vendor.toUpperCase());
                            frm.set_df_property("scan_deflashing_vendor", "hidden", 1);
                        }
                        frm.events.enable_disable_btn(frm);
                    } else {
                        frappe.msgprint("Something went wrong.");
                    }
                }
            });
        } else {
            frm.events.enable_disable_btn(frm);
        }
    },

    enable_disable_btn: frm => {
        if (frm.doc.scan_lot_number && frm.doc.scan_deflashing_vendor) {
            $(frm.get_field('add').wrapper).find('.add-row').removeAttr("disabled");
        } else {
            $(frm.get_field('add').wrapper).find('.add-row').attr("disabled", "disabled");
        }
    },

    add: frm => {
        let wrapper = $(frm.get_field('add').wrapper).empty();
        $(`<button class="btn btn-xs btn-default add-row" disabled="disabled" style="background-color:#fff!important;color:var(--text-color);border-radius:var(--border-radius);box-shadow:var(--btn-shadow);font-size:var(--text-md);">Add</button>`).appendTo(wrapper);

        $(frm.get_field('add').wrapper).find('.add-row').on('click', function () {
            if (!frm.doc.scan_lot_number || frm.doc.scan_lot_number === undefined) {
                frappe.msgprint("Lot no is missing.");
                return;
            }
            if (!frm.doc.scan_deflashing_vendor || frm.doc.scan_deflashing_vendor === undefined) {
                frappe.msgprint("Deflashing Vendor code is missing.");
                return;
            }

            // Show the observed weight dialog before adding item to the table
            frm.events.show_observed_weight_dialog(frm);
        });
    },

    show_observed_weight_dialog: frm => {
        let dialog = new frappe.ui.Dialog({
            title: 'Weight Measurement',
            fields: [
                {
                    label: 'Observed Weight (kg)',
                    fieldname: 'observed_weight',
                    fieldtype: 'Float',
                    reqd: 1
                }
            ],
            primary_action_label: 'Submit',
            primary_action: (values) => {
                const observed_weight = values.observed_weight;
                const system_weight = frm.doc.qty;
                const difference = observed_weight - system_weight;
                const abs_difference = Math.abs(difference);

                if (abs_difference > 0.05) {
                    frappe.msgprint({
                        title: __('Approval Required'),
                        indicator: 'red',
                        message: __(
                            `Weight difference of <b>${(abs_difference * 1000).toFixed(2)} grams</b> exceeds tolerance.`
                        )
                    });

                    // Ask user for confirmation
                    frm.events.confirm_weight_mismatch_action(frm, observed_weight, difference);
                } else {
                    // Within tolerance: Add item to child table
                    frm.events.add_item_with_validation(frm, observed_weight);
                }
                dialog.hide();
            }
        });
        dialog.show();
    },

    confirm_weight_mismatch_action: (frm, observed_weight, difference) => {
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
                frm.events.create_weight_mismatch_tracker(frm, observed_weight, difference);
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

    create_weight_mismatch_tracker: (frm, observed_weight, difference) => {
        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Weight Mismatch Tracker",
                    ref_production_entry: frm.doc.ref_production_entry || "",
                    ref_lot_number: frm.doc.scan_lot_number || "",
                    observed_weight: observed_weight,
                    difference_in_weight: difference,
                    source_document: frm.doc.name || "",
                    received_station: 'Deflashing Despatch',
                    item_code: frm.doc.item, // Moved item_code to top-level
                    batch_number: frm.doc.batch_no, // Moved batch_no to top-level
                    system_weight: frm.doc.qty, // Moved system_weight to top-level
                    warehouse: frm.doc.source_warehouse_id, // Moved source_warehouse to top-level
                    observed_by: frappe.session.user, // Observed By
                },
            },
            freeze: true,
            callback: function (response) {
                if (!response.exc) {
                    frappe.msgprint({
                        title: __("Success"),
                        indicator: "green",
                        message: __(
                            `Weight Mismatch Tracker <b>${response.message.name}</b> created successfully.`
                        ),
                    });
                } else {
                    frappe.msgprint({
                        title: __("Error"),
                        indicator: "red",
                        message: __("Unable to create Weight Mismatch Tracker."),
                    });
                }
            },
        });
    }
    ,

    add_item_with_validation: (frm, observed_weight) => {
        let exists = (frm.doc.items || []).some(i => i.lot_number === frm.doc.lot_number);

        if (exists) {
            frappe.msgprint(__('Lot {0} already added!', [frm.doc.lot_number.bold()]));
            return;
        }

        var row = frappe.model.add_child(frm.doc, 'Deflashing Despatch Entry Item', 'items');
        row.lot_number = frm.doc.lot_number;
        row.batch_no = frm.doc.batch_no;
        row.spp_batch_no = frm.doc.spp_batch_no;
        row.warehouse_code = frm.doc.scan_deflashing_vendor;
        row.job_card = frm.doc.job_card;
        row.item = frm.doc.item || '';
        row.qty = frm.doc.qty;
        row.warehouse = frm.doc.warehouse;
        row.warehouse_id = frm.doc.warehouse_id;
        row.source_warehouse_id = frm.doc.source_warehouse_id;
        row.valuation_rate = frm.doc.valuation_rate;
        row.amount = frm.doc.amount;
        row.observed_weight = observed_weight;
        row.weight_difference = Math.abs(observed_weight - frm.doc.qty).toFixed(3);

        frm.refresh_field('items');
        frm.events.reset_scan_fields(frm);
    },

    reset_scan_fields: frm => {
        frm.set_value('scan_lot_number', '');
        frm.set_value('batch_no', '');
        frm.set_value('spp_batch_no', '');
        frm.set_value('job_card', '');
        frm.set_value('item', '');
        frm.set_value('qty', '');
        frm.set_value('lot_number', '');
        frm.set_value('source_warehouse_id', '');
        frm.set_value('valuation_rate', '');
        frm.set_value('amount', '');
    }
});
// Helper functions for Lot Details Dialog (Deflashing Despatch)
function show_deflashing_lot_selector(frm) {
    // Get unique lot numbers from items table
    const lotNumbers = [];
    const lotOptions = [];

    if (frm.doc.items && frm.doc.items.length > 0) {
        frm.doc.items.forEach(item => {
            if (item.lot_number && !lotNumbers.includes(item.lot_number)) {
                lotNumbers.push(item.lot_number);
                lotOptions.push({
                    label: `${item.lot_number} - ${item.item || 'N/A'}`,
                    value: item.lot_number
                });
            }
        });
    }

    // If only one lot, show details directly
    if (lotNumbers.length === 1) {
        show_deflashing_lot_details_dialog(frm, lotNumbers[0]);
        return;
    }

    // If multiple lots, show selector dialog
    let selector = new frappe.ui.Dialog({
        title: __('Select Lot to View Details'),
        fields: [
            {
                fieldtype: 'Select',
                fieldname: 'selected_lot',
                label: 'Lot Number',
                options: lotOptions.map(opt => opt.label),
                reqd: 1,
                description: 'Select a lot number to view its details'
            }
        ],
        primary_action_label: __('View Details'),
        primary_action: (values) => {
            // Extract lot number from selected label
            const selectedLabel = values.selected_lot;
            const selectedLot = lotNumbers[lotOptions.findIndex(opt => opt.label === selectedLabel)];
            selector.hide();
            show_deflashing_lot_details_dialog(frm, selectedLot);
        }
    });

    selector.show();
}

function show_deflashing_lot_details_dialog(frm, lotNumber) {
    frappe.call({
        method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.get_lot_details',
        args: {
            lot_number: lotNumber,
            doctype: frm.doctype,
            docname: frm.docname
        },
        callback: function (r) {
            if (r.message && r.message.status === "success") {
                let d = new frappe.ui.Dialog({
                    title: `Lot Details: ${r.message.lot_number}`,
                    size: 'large',
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'lot_details_html'
                        }
                    ]
                });

                d.fields_dict.lot_details_html.$wrapper.html(
                    generate_deflashing_lot_details_html(r.message)
                );

                d.show();
            } else {
                frappe.msgprint(__('Failed to fetch lot details'));
            }
        }
    });
}

function generate_deflashing_lot_details_html(data) {
    let html = '<div class="lot-details-container" style="padding: 15px;">';

    // Bin-wise consumption section
    html += '<h4 style="margin-bottom: 15px;">📦 Bin-wise Consumption</h4>';
    html += '<table class="table table-bordered table-sm">';
    html += '<thead><tr>';
    html += '<th>Bin Code</th>';
    html += '<th>Compound</th>';
    html += '<th>SPP Batch</th>';
    html += '<th style="text-align: right;">Consumed (Kg)</th>';
    html += '<th style="text-align: right;">Balance (Kg)</th>';
    html += '</tr></thead>';
    html += '<tbody>';

    let total_consumed = 0;
    let total_balance = 0;

    if (data.bin_details && data.bin_details.length > 0) {
        data.bin_details.forEach(bin => {
            if (bin.is__consumed) {
                html += '<tr>';
                html += `<td>${bin.bin || '-'}</td>`;
                html += `<td>${bin.compound || '-'}</td>`;
                html += `<td>${bin.spp_batch_number || '-'}</td>`;
                html += `<td style="text-align: right;">${parseFloat(bin.consumed__qty || 0).toFixed(3)}</td>`;
                html += `<td style="text-align: right;">${parseFloat(bin.balance__qty || 0).toFixed(3)}</td>`;
                html += '</tr>';

                total_consumed += parseFloat(bin.consumed__qty || 0);
                total_balance += parseFloat(bin.balance__qty || 0);
            }
        });
    } else {
        html += '<tr><td colspan="5" style="text-align: center;">No bin data available</td></tr>';
    }

    html += '</tbody>';
    html += '<tfoot>';
    html += '<tr style="font-weight: bold; background-color: #f0f0f0;">';
    html += '<td colspan="3">TOTAL</td>';
    html += `<td style="text-align: right;">${total_consumed.toFixed(3)}</td>`;
    html += `<td style="text-align: right;">${total_balance.toFixed(3)}</td>`;
    html += '</tr>';
    html += '</tfoot>';
    html += '</table>';

    // Rejection summary section
    html += '<h4 style="margin-top: 30px; margin-bottom: 15px;">🚫 Rejection Summary</h4>';
    html += '<table class="table table-bordered table-sm">';
    html += '<thead><tr>';
    html += '<th>Inspection Type</th>';
    html += '<th style="text-align: right;">Rejected (Nos)</th>';
    html += '<th style="text-align: right;">Rejected Weight (Kg)</th>';
    html += '</tr></thead>';
    html += '<tbody>';

    let total_rejected_nos = 0;
    let total_rejected_kg = 0;

    if (data.rejection_details) {
        if (data.rejection_details.line_inspection) {
            html += '<tr>';
            html += '<td>Line Inspection</td>';
            html += `<td style="text-align: right;">${data.rejection_details.line_inspection.rejected_qty || 0}</td>`;
            html += `<td style="text-align: right;">${parseFloat(data.rejection_details.line_inspection.rejected_kg || 0).toFixed(3)}</td>`;
            html += '</tr>';

            total_rejected_nos += parseInt(data.rejection_details.line_inspection.rejected_qty || 0);
            total_rejected_kg += parseFloat(data.rejection_details.line_inspection.rejected_kg || 0);
        }

        if (data.rejection_details.patrol_inspection) {
            html += '<tr>';
            html += '<td>Patrol Inspection</td>';
            html += `<td style="text-align: right;">${data.rejection_details.patrol_inspection.rejected_qty || 0}</td>`;
            html += `<td style="text-align: right;">${parseFloat(data.rejection_details.patrol_inspection.rejected_kg || 0).toFixed(3)}</td>`;
            html += '</tr>';

            total_rejected_nos += parseInt(data.rejection_details.patrol_inspection.rejected_qty || 0);
            total_rejected_kg += parseFloat(data.rejection_details.patrol_inspection.rejected_kg || 0);
        }
    }

    if (total_rejected_nos === 0) {
        html += '<tr><td colspan="3" style="text-align: center;">No rejection data available</td></tr>';
    }

    html += '</tbody>';

    if (total_rejected_nos > 0) {
        html += '<tfoot>';
        html += '<tr style="font-weight: bold; background-color: #f0f0f0;">';
        html += '<td>TOTAL</td>';
        html += `<td style="text-align: right;">${total_rejected_nos}</td>`;
        html += `<td style="text-align: right;">${total_rejected_kg.toFixed(3)}</td>`;
        html += '</tr>';
        html += '</tfoot>';
    }

    html += '</table>';
    html += '</div>';

    return html;
}
// Helper function to fetch and display bin details in real-time
function fetch_and_display_bin_details(frm, lot_number) {
    if (!lot_number) {
        if (frm.fields_dict.bin_details_display) {
            frm.fields_dict.bin_details_display.$wrapper.html('');
        }
        return;
    }
    
    frappe.call({
        method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.get_lot_details',
        args: {
            lot_number: lot_number,
            doctype: 'Deflashing Despatch Entry',
            docname: frm.docname || ''
        },
        callback: function(r) {
            if (r.message && r.message.status === "success" && frm.fields_dict.bin_details_display) {
                const html = generate_compact_bin_html(r.message);
                frm.fields_dict.bin_details_display.$wrapper.html(html);
            } else if (frm.fields_dict.bin_details_display) {
                frm.fields_dict.bin_details_display.$wrapper.html(
                    '<div class="text-muted" style="padding: 10px;">No bin consumption data  available for this lot</div>'
                );
            }
        }
    });
}

// Helper function to generate compact HTML for bin details
function generate_compact_bin_html(data) {
    if (!data.bin_details || data.bin_details.length === 0) {
        return '<div class="text-muted" style="padding: 10px;">No bin consumption data</div>';
    }
    
    let html = `
        <div style="border: 1px solid #d1d5db; border-radius: 6px; padding: 12px; background: #f9fafb; margin-top: 8px;">
            <h6 style="margin: 0 0 10px 0; color: #374151; font-size: 13px;">
                📦 Bins Used for Lot <b>${data.lot_number}</b>
            </h6>
            <table class="table table-sm table-bordered" style="margin-bottom: 10px; font-size: 12px;">
                <thead style="background: #e5e7eb;">
                    <tr>
                        <th>Bin</th>
                        <th>Compound</th>
                        <th style="text-align: right;">Consumed (Kg)</th>
                    </tr>
                </thead>
                <tbody>`;
    
    let total = 0;
    data.bin_details.forEach(bin => {
        if (bin.is__consumed) {
            const consumed = parseFloat(bin.consumed__qty || 0);
            total += consumed;
            html += `
                <tr>
                    <td><b>${bin.bin || '-'}</b></td>
                    <td>${bin.compound || '-'}</td>
                    <td style="text-align: right;">${consumed.toFixed(3)}</td>
                </tr>`;
        }
    });
    
    html += `
                <tr style="font-weight: bold; background: #f3f4f6;">
                    <td colspan="2">Total</td>
                    <td style="text-align: right;">${total.toFixed(3)} Kg</td>
                </tr>
            </tbody>
        </table>`;
    
    // Add rejection summary if available
    if (data.rejection_details) {
        const line = data.rejection_details.line_inspection;
        const patrol = data.rejection_details.patrol_inspection;
        
        if (line || patrol) {
            html += `
                <div style="margin-top: 8px; font-size: 11px; color: #6b7280; padding: 6px; background: #fef3c7; border-radius: 4px;">
                    <b>🚫 Rejections:</b>`;
            
            if (line) {
                html += ` <span style="color: #991b1b;">Line: ${line.rejected_qty} nos (${line.rejected_kg.toFixed(3)} kg)</span>`;
            }
            if (patrol) {
                html += ` ${line ? ' | ' : ''} <span style="color: #991b1b;">Patrol: ${patrol.rejected_qty} nos (${patrol.rejected_kg.toFixed(3)} kg)</span>`;
            }
            
            html += `</div>`;
        }
    }
    
    html += '</div>';
    return html;
}
