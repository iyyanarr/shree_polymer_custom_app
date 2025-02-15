frappe.ui.form.on("Weight Mismatch Tracker", {
    refresh: function (frm) {
        frm.events.update_weight_approval_scenario(frm); // Update scenario dynamically
        frm.events.update_overview(frm);                // Setup action buttons (Resolve & Rejection)

        // Disable buttons if the document is submitted
        if (frm.doc.docstatus === 1) {
            frm.get_field("overview").$wrapper.find("#resolve-btn").prop("disabled", true);
            frm.get_field("overview").$wrapper.find("#rejection-btn").prop("disabled", true);
        }
    },

    update_weight_approval_scenario: function (frm) {
        const system_weight = frm.doc.system_weight || 0;
        const observed_weight = frm.doc.observed_weight || 0;

        let scenario_message = "";
        let badge_color = "secondary";
        if (system_weight > observed_weight) {
            scenario_message = " System Weight > Observed Weight";
            badge_color = "warning";
        } else if (system_weight < observed_weight) {
            scenario_message = " System Weight < Observed Weight";
            badge_color = "danger";
        } else {
            scenario_message = "Scenario Neutral - System Weight equals Observed Weight";
            badge_color = "warning";
        }

        frm.get_field("weight_approval_scenario").$wrapper.html(`
            <div class="badge badge-${badge_color}" style="font-size: 14px; padding: 10px;">
                ${scenario_message}
            </div>
        `);
    },

    update_overview: function (frm) {
        const overview_html = `
            <div class="button-container">
                <button id="resolve-btn" class="btn btn-primary btn-lg w-100 mb-1">Resolve</button>
                <button id="rejection-btn" class="btn btn-danger btn-lg w-100">Rejection</button>
            </div>
        `;

        frm.get_field("overview").$wrapper.html(overview_html);

        // Resolve button logic
        frm.get_field("overview").$wrapper.find("#resolve-btn").on("click", function () {
            frappe.dom.freeze("Resolving... Please wait"); // Display the loading dialog (freeze UI)

            const reason = frm.doc.reason;
            const details = frm.doc.details;

            if (!reason) {
                frappe.msgprint({
                    title: __("Validation Error"),
                    indicator: "red",
                    message: __("Please select a Reason before resolving."),
                });
                frappe.dom.unfreeze(); // Unfreeze UI
                return;
            }

            if (!details) {
                frappe.msgprint({
                    title: __("Validation Error"),
                    indicator: "red",
                    message: __("Details are mandatory for resolving this document."),
                });
                frappe.dom.unfreeze(); // Unfreeze UI
                return;
            }

            if (reason === "Production Entry Wrong") {
                // Stock Reconciliation logic
                frappe.call({
                    method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.weight_mismatch_tracker.weight_mismatch_tracker.create_stock_reconciliation",
                    args: {
                        document_name: frm.doc.name,
                        posting_date: frappe.datetime.now_date(),
                    },
                    callback: function (response) {
                        frappe.dom.unfreeze(); // Remove the loading dialog
                        if (response.message) {
                            frappe.msgprint({
                                title: __("Success"),
                                indicator: "green",
                                message: __(`Stock Reconciliation created: <b>${response.message}</b>`),
                            });
                            frm.reload_doc(); // Reload the form to reflect changes
                        }
                    },
                    error: function () {
                        frappe.dom.unfreeze(); // Remove loading dialog on error
                    },
                });
            } else if (reason === "Spillage" || reason === "Inspection Entry Wrong") {
                // Stock Transfer logic
                const transfer_amount = frm.doc.system_weight - frm.doc.observed_weight;

                if (transfer_amount <= 0) {
                    frappe.msgprint({
                        title: __("Validation Error"),
                        indicator: "red",
                        message: __("Transfer amount must be greater than zero."),
                    });
                    frappe.dom.unfreeze(); // Remove loading dialog on error
                    return;
                }

                frappe.call({
                    method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.weight_mismatch_tracker.weight_mismatch_tracker.create_stock_transfer",
                    args: {
                        document_name: frm.doc.name,
                        item_code: frm.doc.item_code,
                        transfer_amount: transfer_amount,
                        from_warehouse: frm.doc.warehouse,
                        batch_no: frm.doc.batch_number,
                        posting_date: frappe.datetime.now_date(),
                        reason_code:frm.doc.reason
                    },
                    callback: function (response) {
                        frappe.dom.unfreeze(); // Remove the loading dialog after processing
                        if (response.message) {
                            frappe.msgprint({
                                title: __("Success"),
                                indicator: "green",
                                message: __(`Stock Transfer created: <b>${response.message}</b>`),
                            });
                            frm.reload_doc(); // Reload the form to reflect changes
                        }
                    },
                    error: function () {
                        frappe.dom.unfreeze(); // Remove loading dialog on error
                    },
                });
            } else {
                frappe.msgprint({
                    title: __("Unhandled Reason"),
                    indicator: "orange",
                    message: __("The selected reason is not associated with any action."),
                });
                frappe.dom.unfreeze(); // Unfreeze UI for unhandled reasons
            }
        });

        // Rejection button logic
        frm.get_field("overview").$wrapper.find("#rejection-btn").on("click", function () {
            const rejectionDialog = new frappe.ui.Dialog({
                title: "Rejection Reason",
                fields: [
                    {
                        label: "Rejection Reason",
                        fieldname: "rejection_reason",
                        fieldtype: "Small Text",
                        reqd: 1,
                    },
                ],
                primary_action_label: "Submit",
                primary_action: function (values) {
                    frappe.dom.freeze("Submitting rejection... Please wait"); // Show loading dialog
                    frappe.call({
                        method: "frappe.client.set_value",
                        args: {
                            doctype: "Weight Mismatch Tracker",
                            name: frm.doc.name,
                            fieldname: {
                                rejection_reason: values.rejection_reason,
                                status: "Rejected",
                            },
                        },
                        callback: function () {
                            frappe.dom.unfreeze(); // Remove loading dialog after success
                            frappe.msgprint({
                                title: __("Rejection Complete"),
                                indicator: "green",
                                message: __("Rejection Reason updated and the Status set to Rejected."),
                            });
                            rejectionDialog.hide();
                            frm.reload_doc();
                        },
                        error: function () {
                            frappe.dom.unfreeze(); // Remove loading dialog on error
                        },
                    });
                },
            });

            rejectionDialog.show();
        });
    },
});
