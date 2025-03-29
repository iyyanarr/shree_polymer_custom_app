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
          label: 'Stock UOM',
          fieldname: 'stock_uom',
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
          label: 'Stock in Nos',
          fieldname: 'stock_in_nos',
          fieldtype: 'Float',
          read_only: 1,
          hidden: 1 // Hidden by default, will show only for special items
        },
        {
          label: 'Physical Stock',
          fieldname: 'physical_stock',
          fieldtype: 'Float',
          reqd: true
        },
        {
          label: 'Physical Stock in Nos',
          fieldname: 'physical_stock_in_nos',
          fieldtype: 'Float',
          hidden: 1 // Hidden by default, will show only for special items
        }
      ],
      primary_action_label: 'Add',
      primary_action(values) {
        // If we have a conversion field visible and filled, use it
        if (!dialog.get_field('physical_stock_in_nos').hidden && dialog.get_value('physical_stock_in_nos')) {
          // Calculate the actual physical stock based on the Nos value and conversion factor
          let conversion_factor = dialog.conversion_factor || 1;
          values.physical_stock = values.physical_stock_in_nos * conversion_factor;
        }
        
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
          dialog.set_value('stock_uom', data.stock_uom);
          dialog.set_value('warehouse', data.warehouse);
          dialog.set_value('current_stock', data.qty);
          
          // Check if item_code starts with any of the special prefixes: P, t.P, F, t.F, T
          let item_code = data.item_code || "";
          let stock_uom = data.stock_uom || "";
          let needsConversion = false;
          
          if (item_code.startsWith('P') || item_code.startsWith('t.P') || 
              item_code.startsWith('F') || item_code.startsWith('t.F') ||
              item_code.startsWith('T')) {
            needsConversion = true;
            
            // Determine which item code to use for UOM conversion
            let conversion_item_code = item_code;
            
            // For F items, look up corresponding P item
            if (item_code.startsWith('F')) {
              conversion_item_code = 'P' + item_code.substring(1);
              console.log('Using P item for conversion:', conversion_item_code);
            }
            // For t.F items, look up corresponding t.P item
            else if (item_code.startsWith('t.F')) {
              conversion_item_code = 't.P' + item_code.substring(3);
              console.log('Using t.P item for conversion:', conversion_item_code);
            }
            
            // Get conversion factor from the appropriate item
            frappe.call({
              method: "frappe.client.get",
              args: {
                doctype: "Item",
                name: conversion_item_code
              },
              callback: function(item_r) {
                if (item_r.message) {
                  let item = item_r.message;
                  let conversion_factor = 1;
                  let target_uom = '';
                  
                  // Based on stock_uom, determine which conversion to use
                  if (stock_uom === 'Kg') {
                    target_uom = 'Nos';
                    // Update labels to show we're converting from Kg to Nos
                    dialog.get_field('stock_in_nos').set_label('Stock in Nos');
                    dialog.get_field('physical_stock_in_nos').set_label('Physical Stock in Nos');
                  } else if (stock_uom === 'Nos') {
                    target_uom = 'Kg';
                    // Update labels to show we're converting from Nos to Kg
                    dialog.get_field('stock_in_nos').set_label('Stock in Kg');
                    dialog.get_field('physical_stock_in_nos').set_label('Physical Stock in Kg');
                  } else {
                    // For other UOMs, try to convert to Nos by default
                    target_uom = 'Nos';
                  }
                  
                  // Find UOM conversion to target UOM if it exists
                  if (item.uoms && item.uoms.length > 0) {
                    for (let uom of item.uoms) {
                      if (uom.uom === target_uom) {
                        conversion_factor = parseFloat(uom.conversion_factor) || 1;
                        console.log(`Found ${target_uom} conversion factor:`, conversion_factor);
                        break;
                      }
                    }
                  }
                  
                  // Show the conversion fields
                  dialog.get_field('stock_in_nos').toggle(true);
                  dialog.get_field('physical_stock_in_nos').toggle(true);
                  
                  // Store conversion factor and target UOM for later use
                  dialog.conversion_factor = conversion_factor;
                  dialog.target_uom = target_uom;
                  
                  console.log('Current stock:', data.qty, stock_uom);
                  console.log('Conversion factor:', conversion_factor, `(1 Nos = ${conversion_factor} ${stock_uom})`);
                  
                  // Calculate and set converted stock value
                  let converted_stock;
                  if (stock_uom === 'Kg') {
                    // Convert from Kg to Nos: Kg ÷ conversion_factor
                    converted_stock = data.qty / conversion_factor;
                    console.log(`Converting ${data.qty} Kg to ${converted_stock.toFixed(2)} Nos`);
                  } else if (stock_uom === 'Nos') {
                    // Convert from Nos to Kg: Nos × conversion_factor
                    converted_stock = data.qty * conversion_factor;
                    console.log(`Converting ${data.qty} Nos to ${converted_stock.toFixed(2)} Kg`);
                  } else {
                    // Default conversion
                    converted_stock = data.qty / conversion_factor;
                  }
                  
                  dialog.set_value('stock_in_nos', converted_stock);
                  
                  // Clear previous event handlers to prevent duplicates
                  dialog.get_field('physical_stock').$input.off('change');
                  dialog.get_field('physical_stock_in_nos').$input.off('change');
                  
                  // Set up event handler for physical_stock to update physical_stock_in_nos
                  dialog.get_field('physical_stock').$input.on('change', function() {
                    let physical_stock = dialog.get_value('physical_stock');
                    let converted_value;
                    
                    if (stock_uom === 'Kg') {
                      // Convert from Kg to Nos (1 Nos = 532 Kg)
                      converted_value = physical_stock / conversion_factor;
                    } else if (stock_uom === 'Nos') {
                      // Convert from Nos to Kg (1 Nos = 532 Kg)
                      converted_value = physical_stock * conversion_factor;
                    } else {
                      converted_value = physical_stock / conversion_factor;
                    }
                    
                    dialog.set_value('physical_stock_in_nos', converted_value);
                  });
                  
                  // Set up event handler for physical_stock_in_nos to update physical_stock
                  dialog.get_field('physical_stock_in_nos').$input.on('change', function() {
                    let physical_stock_in_nos = dialog.get_value('physical_stock_in_nos');
                    let physical_stock;
                    
                    if (stock_uom === 'Kg') {
                      // Convert from Nos to Kg (1 Nos = 532 Kg)
                      physical_stock = physical_stock_in_nos * conversion_factor;
                    } else if (stock_uom === 'Nos') {
                      // Convert from Kg to Nos (1 Nos = 532 Kg)
                      physical_stock = physical_stock_in_nos / conversion_factor;
                    } else {
                      physical_stock = physical_stock_in_nos * conversion_factor;
                    }
                    
                    dialog.set_value('physical_stock', physical_stock);
                  });
                } else {
                  // If conversion item not found, handle gracefully
                  console.log('Conversion item not found:', conversion_item_code);
                  frappe.msgprint(__(`Could not find item ${conversion_item_code} for UOM conversion.`));
                  // Hide the conversion fields if we can't get a conversion
                  dialog.get_field('stock_in_nos').toggle(false);
                  dialog.get_field('physical_stock_in_nos').toggle(false);
                }
              }
            });
          } else {
            // Hide the conversion fields for other items
            dialog.get_field('stock_in_nos').toggle(false);
            dialog.get_field('physical_stock_in_nos').toggle(false);
          }
          
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
        
        // Store Nos value if available
        if (values.physical_stock_in_nos) {
          child_entry.physical_stock_in_nos = values.physical_stock_in_nos;
        }
  
        frm.refresh_field('details');
        frm.save();
      } else {
        frappe.msgprint(__('Could not append entry to details table.'));
      }
    } else {
      frappe.msgprint(__('Form not loaded correctly.'));
    }
}