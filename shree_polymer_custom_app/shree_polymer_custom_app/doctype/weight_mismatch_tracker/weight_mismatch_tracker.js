frappe.ui.form.on("Weight Mismatch Tracker", {
    refresh: function (frm) {
        frm.events.update_weight_approval_scenario(frm); // Update the scenario dynamically
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
            scenario_message = "Scenario On - System Weight is greater than Observed Weight";
            badge_color = "success";
        } else if (system_weight < observed_weight) {
            scenario_message = "Scenario Two - Observed Weight is greater than System Weight";
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

        // Disable buttons if the document is already submitted
        if (frm.doc.docstatus === 1) {
            frm.get_field("overview").$wrapper.find("#resolve-btn").prop("disabled", true);
            frm.get_field("overview").$wrapper.find("#rejection-btn").prop("disabled", true);
            return;
        }

        // Resolve button: Logic for handling both reasons
        frm.get_field("overview").$wrapper.find("#resolve-btn").on("click", function () {
            const reason = frm.doc.reason;
            const details = frm.doc.details;

            if (!reason) {
                frappe.msgprint({
                    title: __("Validation Error"),
                    indicator: "red",
                    message: __("Please select a Reason before resolving."),
                });
                return;
            }

            if (!details) {
                frappe.msgprint({
                    title: __("Validation Error"),
                    indicator: "red",
                    message: __("Details are mandatory for resolving this document."),
                });
                return;
            }

            if (reason === "Production Entry Wrong") {
                // Stock Reconciliation for "Production Entry Wrong"
                frappe.call({
                    method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.weight_mismatch_tracker.weight_mismatch_tracker.create_stock_reconciliation",
                    args: {
                        document_name: frm.doc.name,
                        posting_date: frappe.datetime.now_date(),
                    },
                    callback: function (response) {
                        if (response.message) {
                            frappe.msgprint({
                                title: __("Success"),
                                indicator: "green",
                                message: __(`Stock Reconciliation created: <b>${response.message}</b>`),
                            });
                            frm.reload_doc();
                        }
                    },
                });
            } else if (reason === "Spillage") {
                // Stock Transfer for "Spillage"
                const transfer_amount = frm.doc.system_weight - frm.doc.observed_weight;

                if (transfer_amount <= 0) {
                    frappe.msgprint({
                        title: __("Validation Error"),
                        indicator: "red",
                        message: __("Transfer amount must be greater than zero."),
                    });
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
                    },
                    callback: function (response) {
                        if (response.message) {
                            frappe.msgprint({
                                title: __("Success"),
                                indicator: "green",
                                message: __(`Stock Transfer created: <b>${response.message}</b>`),
                            });
                            frm.reload_doc();
                        }
                    },
                });
            } else {
                frappe.msgprint({
                    title: __("No Action"),
                    indicator: "orange",
                    message: __("This reason code doesn't have any specific action."),
                });
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
                            frappe.msgprint({
                                title: __("Rejection Complete"),
                                indicator: "green",
                                message: __("Rejection Reason updated and the Status set to Rejected."),
                            });
                            rejectionDialog.hide();
                            frm.reload_doc();
                        },
                    });
                },
            });

            rejectionDialog.show();
        });
    },
});
