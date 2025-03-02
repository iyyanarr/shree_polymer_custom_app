frappe.ui.form.on('Physical Stock Entry', {
    refresh: function(frm) {
      frm.add_custom_button(__('Add Physical Stock Entry'), function() {
        create_physical_stock_dialog(frm);
      });
    }
  });
  
  function create_physical_stock_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
      title: 'Enter Physical Stock Details',
      fields: [
        {
          label: 'Batch / Barcode',
          fieldname: 'batch_or_mixed_barcode',
          fieldtype: 'Data',
          reqd: true,
          onchange: () => {
            fetch_stock_information(dialog, frm);
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
          default: frm.doc.item_group,
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
        dialog.hide();
      }
    });
  
    dialog.show();
  }
  
  function fetch_stock_information(dialog, frm) {
    let batch_or_mixed_barcode = dialog.get_value('batch_or_mixed_barcode');
    let item_group = frm.doc.item_group;
    
    if (!batch_or_mixed_barcode || !item_group) {
      frappe.msgprint(__('Batch/Barcode or Item group missing.'));
      return;
    }
  
    frappe.call({
      method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.physical_stock_entry.physical_stock_entry.get_filtered_stock_by_parameters",
      args: {
        batch_or_mixed_barcode: batch_or_mixed_barcode,
        item_group: item_group
      },
      callback: function(r) {
        console.log('**************************',r);
        if (r.message && !r.message.error && !r.message.message) {
          let data = r.message;
          dialog.set_value('item_code', data.item_code);
          dialog.set_value('item_name', data.item_name);
          dialog.set_value('warehouse', data.warehouse);
          dialog.set_value('current_stock', data.qty);
          // Automatically focus physical stock for faster data entry
          dialog.get_field('physical_stock').$input.focus();
          
        } else if(r.message) {
          let msg = r.message.message || r.message.error;
          frappe.msgprint(msg);
        } else {
          frappe.msgprint(__('No stock information found.'));
        }
      }
    });
  }
  
  function add_entry_to_child_table(frm, values) {
    if (frm && frm.doc) {
      let child_entry = frm.add_child('details');
  
      if (child_entry) {
        child_entry.batch_number = values.batch_or_mixed_barcode;
        child_entry.item_code = values.item_code;
        child_entry.item_name = values.item_name;
        child_entry.item_group = values.item_group;
        child_entry.warehouse = values.warehouse;
        child_entry.current_stock = values.current_stock;
        child_entry.physical_stock = values.physical_stock;
  
        frm.refresh_field('details');
        frm.save();
      } else {
        frappe.msgprint(__('Could not append entry to details table.'));
      }
    } else {
      frappe.msgprint(__('Form not loaded correctly.'));
    }
  }