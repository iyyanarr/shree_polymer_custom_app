

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
                    frappe.route_options = {"name": ["in", dc_ids]};
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
            frappe.call({
                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_lot_barcode',
                args: {bar_code: frm.doc.scan_lot_number},
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
                    } else {
                        frappe.msgprint("Something went wrong.");
                    }
                }
            });
        } else {
            frm.events.enable_disable_btn(frm);
        }
    },

    scan_deflashing_vendor: frm => {
        if (frm.doc.scan_deflashing_vendor && frm.doc.scan_deflashing_vendor !== undefined) {
            frappe.call({
                method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.deflashing_despatch_entry.deflashing_despatch_entry.validate_warehouse',
                args: {bar_code: frm.doc.scan_deflashing_vendor},
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
                    received_station: 'Deflashing Despatch',
					item_code: frm.doc.item , // Moved item_code to top-level
					batch_number: frm.doc.batch_no , // Moved batch_no to top-level
					system_weight: frm.doc.qty, // Moved system_weight to top-level
					warehouse: frm.doc.source_warehouse_id , // Moved source_warehouse to top-level
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
