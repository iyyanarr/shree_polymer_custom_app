frappe.ui.form.on("Weight Mismatch Tracker", {
    refresh: function (frm) {
      frm.events.update_weight_approval_scenario(frm); // Dynamically display weight mismatch scenario
      frm.events.update_overview(frm); // Setup Resolve and Rejection buttons
  
      // Disable buttons if the document is submitted
      if (frm.doc.docstatus === 1) {
        frm.get_field("overview").$wrapper.find("#resolve-btn").prop("disabled", true);
        frm.get_field("overview").$wrapper.find("#rejection-btn").prop("disabled", true);
      }
  
      frm.trigger("setup_auto_save"); // Enable auto-save for key fields
    },
  
    update_weight_approval_scenario: function (frm) {
      const system_weight = frm.doc.system_weight || 0;
      const observed_weight = frm.doc.observed_weight || 0;
  
      let scenario_message = "";
      let alert_class = "alert-secondary";
      let scenario_icon = "fa-info-circle";
  
      if (system_weight > observed_weight) {
        scenario_message =
          "System Weight is greater than Observed Weight. There might be some missing items.";
        alert_class = "alert-warning";
        scenario_icon = "fa-exclamation-circle";
      } else if (system_weight < observed_weight) {
        scenario_message =
          "System Weight is less than Observed Weight. There might be some additional items.";
        alert_class = "alert-danger";
        scenario_icon = "fa-times-circle";
      } else {
        scenario_message = "System Weight equals Observed Weight. The weights match perfectly.";
        alert_class = "alert-success";
        scenario_icon = "fa-check-circle";
      }
  
      frm.get_field("weight_approval_scenario").$wrapper.html(`
        <div class="alert ${alert_class} d-flex align-items-center" role="alert" style="font-size: 14px;">
          <i class="fas ${scenario_icon} mr-2"></i>
          <div>
            ${scenario_message}
          </div>
        </div>
      `);
    },
  
    update_overview: function (frm) {
      const overview_html = `
        <div class="button-container">
          <button id="resolve-btn" class="btn btn-primary btn-lg w-100 mb-2">Resolve</button>
          <button id="rejection-btn" class="btn btn-danger btn-lg w-100">Rejection</button>
        </div>
      `;
  
      frm.get_field("overview").$wrapper.html(overview_html);
  
      // Setup Resolve Button Logic
      frm.get_field("overview").$wrapper.find("#resolve-btn").on("click", function () {
        frappe.dom.freeze("Resolving... Please wait");
  
        const reason = frm.doc.reason;
        const details = frm.doc.details;
  
        // Error handling for mandatory fields
        if (!reason) {
          frappe.msgprint({
            title: __("Validation Error"),
            indicator: "red",
            message: __("Please select a Reason before resolving."),
          });
          frappe.dom.unfreeze();
          return;
        }
  
        if (!details) {
          frappe.msgprint({
            title: __("Validation Error"),
            indicator: "red",
            message: __("Details are mandatory for resolving this document."),
          });
          frappe.dom.unfreeze();
          return;
        }
  
        // If reason is "Production Entry Wrong," ensure mandatory fields are filled
        if (reason === "Production Entry Wrong" || reason === "Stock Reconsile") {
          const approved_weight = frm.doc.approved_weight || 0;
          const updated_cavities = frm.doc.updated_cavities || 0;
          const update_no_of_lifts = frm.doc.update_no_of_lifts || 0;
  
          if (approved_weight <= 0 || updated_cavities <= 0 || update_no_of_lifts <= 0) {
            frappe.msgprint({
              title: __("Validation Error"),
              indicator: "red",
              message: __(
                "Please provide valid values for Approved Weight, Updated Cavities, and Update No of Lifts."
              ),
            });
            frappe.dom.unfreeze();
            return;
          }
        }
  
        // Call appropriate server-side methods for the selected reason
        if (reason === "Production Entry Wrong" || reason === "Stock Reconcile") { 
          frappe.call({
            method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.weight_mismatch_tracker.weight_mismatch_tracker.create_stock_reconciliation",
            args: {
              document_name: frm.doc.name,
              posting_date: frappe.datetime.now_date(),
            },
            callback: function (response) {
              frappe.dom.unfreeze();
              if (response.message) {
                frappe.msgprint({
                  title: __("Success"),
                  indicator: "green",
                  message: `Stock Reconciliation created: <b>${response.message}</b>`,
                });
                frm.reload_doc();
              }
            },
            error: function () {
              frappe.dom.unfreeze();
            },
          });
        } else if (reason === "Spillage" || reason === "Inspection Entry Wrong") {
          const transfer_amount = frm.doc.system_weight - frm.doc.observed_weight;
  
          if (transfer_amount <= 0) {
            frappe.msgprint({
              title: __("Validation Error"),
              indicator: "red",
              message: __("Transfer amount must be greater than zero."),
            });
            frappe.dom.unfreeze();
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
              reason_code: frm.doc.reason,
            },
            callback: function (response) {
              frappe.dom.unfreeze();
              if (response.message) {
                frappe.msgprint({
                  title: __("Success"),
                  indicator: "green",
                  message: `Stock Transfer created: <b>${response.message}</b>`,
                });
                frm.reload_doc();
              }
            },
            error: function () {
              frappe.dom.unfreeze();
            },
          });
        } else {
          frappe.msgprint({
            title: __("Unhandled Reason"),
            indicator: "orange",
            message: __("The selected reason is not associated with any action."),
          });
          frappe.dom.unfreeze();
        }
      });
  
      // Setup Rejection Button Logic
      frm.get_field("overview").$wrapper.find("#rejection-btn").on("click", function () {
        const rejection_dialog = new frappe.ui.Dialog({
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
            frappe.dom.freeze("Submitting rejection... Please wait");
  
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
                frappe.dom.unfreeze();
                frappe.msgprint({
                  title: __("Rejection Complete"),
                  indicator: "green",
                  message: __("Rejection Reason updated and the Status set to Rejected."),
                });
                rejection_dialog.hide();
                frm.reload_doc();
              },
              error: function () {
                frappe.dom.unfreeze();
              },
            });
          },
        });
        rejection_dialog.show();
      });
    },
  
    setup_auto_save: function (frm) {
          // Add auto-save for 'reason' field
    frm.fields_dict["reason"].df.change = function() {
      frm.save_or_update({
          freeze: true,
          freeze_message: "Saving Reason..."
      });
  };
      // Auto-save for 'approved_weight', 'updated_cavities', and 'update_no_of_lifts'
      frm.fields_dict["approved_weight"].df.change = function () {
        frm.save_or_update({
          freeze: true,
          freeze_message: "Saving Approved Weight...",
        });
      };
      frm.fields_dict["updated_cavities"].df.change = function () {
        frm.save_or_update({
          freeze: true,
          freeze_message: "Saving Updated Cavities...",
        });
      };
      frm.fields_dict["update_no_of_lifts"].df.change = function () {
        frm.save_or_update({
          freeze: true,
          freeze_message: "Saving Update No of Lifts...",
        });
      };
    },
  });
  