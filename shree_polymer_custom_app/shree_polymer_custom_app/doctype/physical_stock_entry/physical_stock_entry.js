frappe.ui.form.on('Physical Stock Entry', {
    refresh: function(frm) {
        frm.add_custom_button(__('Add Physical Stock Entry'), function() {
            create_physical_stock_dialog(frm);
        });
    }
});

function create_physical_stock_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: 'Enter Physical Stock Details',
        fields: [
            {
                label: 'Batch Number',
                fieldname: 'batch_number',
                fieldtype: 'Data',
                reqd: true,
                onchange: () => {
                    onBatchNumberScanned(d, frm);
                }
            },
            {
                label: 'Item Code',
                fieldname: 'item_code',
                fieldtype: 'Link',
                options: 'Item',
                read_only: 1
            },
            {
                label: 'Item Name',
                fieldname: 'item_name',
                fieldtype: 'Data',
                read_only: 1
            },
            {
                label: 'Item Group',
                fieldname: 'item_group',
                fieldtype: 'Link',
                options: 'Item Group',
                read_only: 1
            },
            {
                label: 'Warehouse',
                fieldname: 'warehouse',
                fieldtype: 'Link',
                options: 'Warehouse',
                read_only: 1
            },
            {
                label: 'Current Stock',
                fieldname: 'current_stock',
                fieldtype: 'Float',
                read_only: 1
            },
            {
                label: 'Physical Stock',
                fieldname: 'physical_stock',
                fieldtype: 'Float',
                reqd: true
            }
        ],
        primary_action_label: 'Add',
        primary_action(values) {
            add_entry_to_child_table(frm, values);
            d.hide();
        }
    });

    d.show();
}

function onBatchNumberScanned(dialog, frm) {
    let batch_number = dialog.get_value('batch_number');

    if (batch_number) {
        frappe.call({
            method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.physical_stock_entry.physical_stock_entry.get_filtered_stock_by_parameters",
            args: {
                mixed_barcode: batch_number,
                item_group: frm.doc.item_group
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let data = r.message[0];
                    console.log(data);
                    dialog.set_value('item_code', data.item_code);
                    dialog.set_value('item_name', data.item_name);
                    dialog.set_value('item_group', data.item_group);
                    dialog.set_value('warehouse', data.t_warehouse); // Assuming t_warehouse is your warehouse field
                    dialog.set_value('current_stock', data.total_quantity);

                    // Set focus to the Physical Stock field
                    dialog.get_field('physical_stock').$input.focus();
                } else {
                    frappe.msgprint(__('No item found with this Batch Number'));
                }
            }
        });
    }
}

function add_entry_to_child_table(frm, values) {
    if (frm && frm.doc) {
        let child = frm.add_child('details');

        if (child) {
            child.batch_number = values.batch_number;
            child.item_code = values.item_code;
            child.item_name = values.item_name;
            child.item_group = values.item_group;
            child.warehouse = values.warehouse;
            child.current_stock = values.current_stock;
            child.physical_stock = values.physical_stock;

            frm.refresh_field('details');
            frm.save(); // Save the document after adding the child
        } else {
            frappe.msgprint(__('Failed to add child entry.'));
        }
    } else {
        frappe.msgprint(__('Form not loaded properly.'));
    }
}