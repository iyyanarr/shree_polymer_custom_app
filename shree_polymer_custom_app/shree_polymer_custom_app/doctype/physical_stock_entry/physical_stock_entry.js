frappe.ui.form.on('Physical Stock Entry', {
    refresh: function(frm) {
      frm.add_custom_button(__('Add Physical Stock Entry'), function() {
        create_physical_stock_dialog(frm);
      });
    }
  });
  
  function create_physical_stock_dialog(frm) {
    let item_group = frm.doc.item_group;
    let is_compound_sheeting = (
      item_group === 'Compound-Sheeting' ||
      item_group === 'Compound - Sheeting'
    );
    
    let dialog = new frappe.ui.Dialog({
      title: 'Enter Physical Stock Details',
      fields: [
        {
          label: 'Batch / Barcode',
          fieldname: 'batch_or_mixed_barcode',
          fieldtype: 'Data',
          reqd: !is_compound_sheeting,
          hidden: is_compound_sheeting,
          onchange: () => {
            fetch_stock_information(dialog, frm);
          },
          description: 'Automatically fetches on scan'
        },
        {
          label: 'Manual Entry',
          fieldtype: 'Section Break'
        },
        {
          label: 'Manual Batch / Barcode',
          fieldname: 'manual_batch_or_barcode',
          fieldtype: 'Data',
          hidden: is_compound_sheeting
        },
        {
          fieldtype: 'Column Break'
        },
        {
          label: 'Fetch Manual Entry',
          fieldtype: 'Button',
          click: () => {
            const barcodeField = dialog.get_field('batch_or_mixed_barcode');
            const manualField = dialog.get_field('manual_batch_or_barcode');
            if (!barcodeField.get_value() && manualField.get_value()) {
              barcodeField.set_value(manualField.get_value());
            }
            fetch_stock_information(dialog, frm);
          }
        },
        {
          fieldtype: 'Section Break',
          label: 'Details'
        },
        {
          label: 'Scan Bin',
          fieldname: 'scan_bin',
          fieldtype: 'Data',
          reqd: false, // Not required by default
          hidden: !is_compound_sheeting,
          onchange: () => {
            if (is_compound_sheeting) {
              // No need to change the reqd property, validation will be handled by primary button
              fetch_stock_information_compound_sheeting(dialog, frm, 'bin');
            }
          }
        },
        {
          label: 'Scan Clip',
          fieldname: 'scan_clip',
          fieldtype: 'Data',
          reqd: false, // Not required by default
          hidden: !is_compound_sheeting,
          onchange: () => {
            if (is_compound_sheeting) {
              // No need to change the reqd property, validation will be handled by primary button
              fetch_stock_information_compound_sheeting(dialog, frm, 'clip');
            }
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
        // For Compound - Sheeting, use scan_bin or scan_clip as the batch identifier
        if (is_compound_sheeting) {
          if (values.scan_bin) {
            values.batch_or_mixed_barcode = values.scan_bin;
          } else if (values.scan_clip) {
            values.batch_or_mixed_barcode = values.scan_clip;
          }
        }
        
        // If we have a conversion field visible and filled, use it
        if (!dialog.get_field('physical_stock_in_nos').hidden && dialog.get_value('physical_stock_in_nos')) {
          let conversion_factor = dialog.conversion_factor || 1;
          let stock_uom = dialog.get_value('stock_uom');
          let item_group = dialog.get_value('item_group');
          
          // For Product Sales items, the physical_stock_in_nos is the primary input (in Nos)
          // We need to convert this to Kg for physical_stock
          if (item_group === 'Product Sales') {
            values.physical_stock = values.physical_stock_in_nos * conversion_factor;
          }
          // For other items, follow the existing logic
          else if (stock_uom === 'Nos') {
            // Using the formula nos/kg*qty
            values.physical_stock = (1/conversion_factor) * values.physical_stock_in_nos;
          } else {
            // Standard conversion
            values.physical_stock = values.physical_stock_in_nos * conversion_factor;
          }
        }
        
        // For bin scanning, transfer all the additional bin data to the values object
        if (values.scan_bin && dialog.bin_code) {
          // Add bin-related information to values object
          values.bin_code = dialog.bin_code;
          if (dialog.asset_name) values.asset_name = dialog.asset_name;
          if (dialog.blanking_dc_entry) values.blanking_dc_entry = dialog.blanking_dc_entry;
          if (dialog.available_quantity) values.available_quantity = dialog.available_quantity;
          if (dialog.spp_batch_number) values.spp_batch_number = dialog.spp_batch_number;
          if (dialog.batch_no) values.batch_no = dialog.batch_no;
          
          // Reference quantity from blanking DC
          if (dialog.get_value('reference_qty')) {
            values.reference_qty = dialog.get_value('reference_qty');
          }
        }
        
        add_entry_to_child_table(frm, values);
        dialog.hide();
      }
    });
  
    // Prevent dialog from closing on Enter key
    dialog.$wrapper.find('.modal-dialog').keydown(function(e) {
      if (e.which === 13) { // Enter key
        e.preventDefault();
        e.stopPropagation();
        // Don't submit the dialog on enter, just trigger the field's onchange event
        if (is_compound_sheeting) {
          const scanBinField = dialog.get_field('scan_bin');
          const scanClipField = dialog.get_field('scan_clip');
          if (document.activeElement === scanBinField.$input[0]) {
            fetch_stock_information_compound_sheeting(dialog, frm, 'bin');
          } else if (document.activeElement === scanClipField.$input[0]) {
            fetch_stock_information_compound_sheeting(dialog, frm, 'clip');
          }
        } else {
          const barcodeField = dialog.get_field('batch_or_mixed_barcode');
          if (document.activeElement === barcodeField.$input[0]) {
            fetch_stock_information(dialog, frm);
          }
        }
        return false;
      }
    });

    // Apply side-by-side styling for Compound - Sheeting fields
    if (is_compound_sheeting) {
      // Add validation to ensure at least one of scan_bin or scan_clip has a value
      dialog.set_df_property('scan_bin', 'reqd', false); // Start with neither as required
      dialog.set_df_property('scan_clip', 'reqd', false);
      
      // Override the dialog's standard behavior for the primary button
      const originalClickFunction = dialog.get_primary_btn().onclick;
      dialog.get_primary_btn().onclick = function() {
        // Custom validation to ensure at least one field has data
        const scanBinValue = dialog.get_value('scan_bin');
        const scanClipValue = dialog.get_value('scan_clip');
        
        if ((!scanBinValue || !scanBinValue.trim()) && 
            (!scanClipValue || !scanClipValue.trim())) {
          frappe.msgprint(__('Please scan either a Bin or a Clip'));
          return false;
        }
        
        // If validation passes, call the original click function
        originalClickFunction();
      };
      
      dialog.show();
      setTimeout(() => {
        // Add custom CSS to make scan fields side by side
        const scanBinWrapper = dialog.get_field('scan_bin').$wrapper;
        const scanClipWrapper = dialog.get_field('scan_clip').$wrapper;
        
        // Create a flex container
        scanBinWrapper.css({
          'display': 'inline-block',
          'width': '48%',
          'margin-right': '2%'
        });
        
        scanClipWrapper.css({
          'display': 'inline-block',
          'width': '48%',
          'vertical-align': 'top'
        });
      }, 100);
    } else {
      dialog.show();
    }
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
          let returned_item_group = data.item_group || "";
          let needsConversion = false;
          
          // Special handling for Product Sales items - these should be entered in Nos
          if (returned_item_group === 'Product Sales') {
            console.log("Product Sales item detected - will enter in Nos");
            
            // If stock_uom is Kg, show the conversion fields
            if (stock_uom === 'Kg') {
              needsConversion = true;
              
              // Change the labels to make it clear that Nos is the primary entry method
              dialog.get_field('physical_stock').set_label('Physical Stock (Kg)');
              dialog.get_field('physical_stock_in_nos').set_label('Physical Stock in Nos');
              dialog.get_field('stock_in_nos').set_label('Stock in Nos');
              
              // Show Nos field and hide Kg field
              dialog.get_field('physical_stock').toggle(false);
              dialog.get_field('physical_stock_in_nos').toggle(true);
              dialog.get_field('physical_stock_in_nos').df.reqd = true;
              dialog.get_field('physical_stock').df.reqd = false;
              
              // Also show current stock in Nos
              dialog.get_field('stock_in_nos').toggle(true);
              
              // Now handle the conversion just like before
              let conversion_item_code = item_code;
              
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
                    let target_uom = 'Nos';
                    
                    // Find UOM conversion to Nos if it exists
                    if (item.uoms && item.uoms.length > 0) {
                      for (let uom of item.uoms) {
                        if (uom.uom === target_uom) {
                          conversion_factor = parseFloat(uom.conversion_factor) || 1;
                          console.log(`Found ${target_uom} conversion factor:`, conversion_factor);
                          break;
                        }
                      }
                    }
                    
                    // Store conversion factor for later use
                    dialog.conversion_factor = conversion_factor;
                    dialog.target_uom = target_uom;
                    
                    // Convert current stock from Kg to Nos
                    let stock_in_nos = data.qty / conversion_factor;
                    dialog.set_value('stock_in_nos', stock_in_nos);
                    
                    // Set up handlers for conversion
                    dialog.get_field('physical_stock').$input.off('change');
                    dialog.get_field('physical_stock_in_nos').$input.off('change');
                    
                    // When Nos changes, update Kg
                    dialog.get_field('physical_stock_in_nos').$input.on('change', function() {
                      let nos_value = dialog.get_value('physical_stock_in_nos');
                      let kg_value = nos_value * conversion_factor;
                      dialog.set_value('physical_stock', kg_value);
                    });
                    
                    // When Kg changes, update Nos
                    dialog.get_field('physical_stock').$input.on('change', function() {
                      let kg_value = dialog.get_value('physical_stock');
                      let nos_value = kg_value / conversion_factor;
                      dialog.set_value('physical_stock_in_nos', nos_value);
                    });
                    
                    // Focus on Nos field for entry
                    dialog.get_field('physical_stock_in_nos').$input.focus();
                  }
                }
              });
            } else {
              // Product Sales item with non-Kg UOM - just focus on physical_stock field
              dialog.get_field('physical_stock').$input.focus();
            }
          } 
          // Regular conversion for special prefix items
          else if (item_code.startsWith('P') || item_code.startsWith('t.P') || 
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
                  // [Rest of the existing conversion code remains the same]
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
                  
                  // [Continue with existing conversion code]
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
                    // Using the formula nos/kg*qty where nos=1, kg=conversion_factor
                    converted_stock = (1/conversion_factor) * data.qty;
                    console.log(`Converting ${data.qty} Nos to ${converted_stock.toFixed(2)} Kg using formula: (1/${conversion_factor})*${data.qty}`);
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
                      // Convert from Kg to Nos
                      converted_value = physical_stock / conversion_factor;
                    } else if (stock_uom === 'Nos') {
                      // Convert from Nos to Kg
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
                      // Convert from Nos to Kg
                      physical_stock = physical_stock_in_nos * conversion_factor;
                    } else if (stock_uom === 'Nos') {
                      // Using the formula nos/kg*qty where nos=1, kg=conversion_factor
                      physical_stock = (1/conversion_factor) * physical_stock_in_nos;
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
            // Non-special items - no conversion needed
            dialog.get_field('stock_in_nos').toggle(false);
            dialog.get_field('physical_stock_in_nos').toggle(false);
            dialog.get_field('physical_stock').$input.focus();
          }
          
        } else if(r.message) {
          let msg = r.message.message || r.message.error;
          frappe.msgprint(msg);
        } else {
          frappe.msgprint(__('No stock information found.'));
        }
      }
    });
}

function fetch_stock_information_compound_sheeting(dialog, frm, scan_type) {
    let scan_value = '';
    let item_group = frm.doc.item_group;
    
    if (scan_type === 'bin') {
        scan_value = dialog.get_value('scan_bin');
    } else if (scan_type === 'clip') {
        scan_value = dialog.get_value('scan_clip');
    }
    
    if (!scan_value || !item_group) {
        frappe.msgprint(__('Scan value or Item group missing.'));
        return;
    }

    // Get the warehouse for this item group
    let warehouse = get_warehouse_for_item_group(item_group);
    console.log(`Using warehouse: ${warehouse} for item group: ${item_group}`);
    
    frappe.call({
        method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.physical_stock_entry.physical_stock_entry.get_compound_sheeting_stock_info",
        args: {
            scan_value: scan_value,
            scan_type: scan_type,
            item_group: item_group
        },
        callback: function(r) {
            console.log('=== COMPOUND SHEETING SCAN DEBUG INFO ===');
            console.log('Full Response:', r);
            
            if (r.message) {
                console.log('Response Message:', r.message);
                
                // Log debug info if available
                if (r.message.debug_info) {
                    console.log('=== DEBUG INFO BREAKDOWN ===');
                    console.log('Scan Value:', r.message.debug_info.scan_value);
                    console.log('Warehouse:', r.message.debug_info.warehouse);
                    console.log('Steps Executed:', r.message.debug_info.steps);
                    
                    if (r.message.debug_info.sheeting_clip_data) {
                        console.log('STEP 1 - Sheeting Clip Data:', r.message.debug_info.sheeting_clip_data);
                    }
                    
                    if (r.message.debug_info.item_clip_mapping_data) {
                        console.log('STEP 2 - Item Clip Mapping Data:', r.message.debug_info.item_clip_mapping_data);
                    }
                    
                    if (r.message.debug_info.all_item_clip_mappings) {
                        console.log('All Item Clip Mappings for this clip:', r.message.debug_info.all_item_clip_mappings);
                    }
                    
                    if (r.message.debug_info.stock_entry_detail_data) {
                        console.log('STEP 3 - Stock Entry Detail Data:', r.message.debug_info.stock_entry_detail_data);
                    }
                    
                    if (r.message.debug_info.all_stock_entries) {
                        console.log('All Stock Entries with SPP Batch Number:', r.message.debug_info.all_stock_entries);
                    }
                    
                    if (r.message.batch_no) {
                        console.log('FOUND BATCH NUMBER:', r.message.batch_no);
                        console.log('ITEM CODE:', r.message.item_code);
                        console.log('ITEM NAME:', r.message.item_name);
                        console.log('STOCK UOM:', r.message.stock_uom);
                        
                        if (r.message.debug_info.stock_balance_data) {
                            console.log('STEP 4 - Stock Balance Data:', r.message.debug_info.stock_balance_data);
                            console.log('CURRENT STOCK:', r.message.qty, r.message.stock_uom, 'in', r.message.warehouse);
                        } else if (r.message.debug_info.similar_batches) {
                            console.log('Similar Batches Found:', r.message.debug_info.similar_batches);
                        } else {
                            console.log('NO STOCK BALANCE FOUND FOR BATCH:', r.message.batch_no);
                        }
                    }
                    
                    if (r.message.debug_info.stock_balance_data) {
                        console.log('STEP 4 - Stock Balance Data:', r.message.debug_info.stock_balance_data);
                    }
                    
                    if (r.message.debug_info.similar_batches) {
                        console.log('Similar Batches Found:', r.message.debug_info.similar_batches);
                    }
                    
                    if (r.message.debug_info.error) {
                        console.log('ERROR:', r.message.debug_info.error);
                    }
                }
                
                // Add debug info for bin scanning
                if (scan_type === 'bin' && r.message.debug_info) {
                    console.log('=== BIN SCAN DEBUG INFO ===');
                    
                    if (r.message.debug_info.blanking_dc_item_data) {
                        console.log('STEP 1 - Blanking DC Item Data:', r.message.debug_info.blanking_dc_item_data);
                        console.log('Blanking DC Entry:', r.message.blanking_dc_entry);
                        console.log('Posting Date:', r.message.posting_date);
                        console.log('BIN CODE:', r.message.bin_code);
                        console.log('ASSET NAME:', r.message.asset_name);
                    }
                    
                    if (r.message.debug_info.item_details) {
                        console.log('STEP 2 - Item Details:', r.message.debug_info.item_details);
                      }
                      
                      if (r.message.batch_no) {
                        console.log('FOUND BATCH NUMBER:', r.message.batch_no);
                        console.log('SPP BATCH NUMBER:', r.message.spp_batch_number);
                        console.log('ITEM CODE:', r.message.item_code);
                        console.log('ITEM NAME:', r.message.item_name);
                        console.log('STOCK UOM:', r.message.stock_uom);
                        console.log('AVAILABLE QUANTITY:', r.message.available_quantity);
                        console.log('GROSS WEIGHT:', r.message.gross_weight);
                        console.log('NET WEIGHT:', r.message.net_weight);
                      }
                      
                      if (r.message.debug_info.stock_balance_data) {
                        console.log('STEP 3 - Stock Balance Data:', r.message.debug_info.stock_balance_data);
                        console.log('CURRENT STOCK:', r.message.qty, r.message.stock_uom, 'in', r.message.warehouse);
                      } else if (r.message.debug_info.similar_batches) {
                        console.log('Similar Batches Found:', r.message.debug_info.similar_batches);
                      }
                      
                      console.log('=== END BIN SCAN DEBUG INFO ===');
                  }
            }
            console.log('=== END DEBUG INFO ===');
            
            if (r.message) {
                let data = r.message;
                
                // Check if we have item data from stock entry
                if (data.item_code) {
                    dialog.set_value('item_code', data.item_code);
                    dialog.set_value('item_name', data.item_name);
                    dialog.set_value('stock_uom', data.stock_uom);
                    
                    // Additional information for bin scanning
                    if (scan_type === 'bin' && data.bin_code) {
                        // Format bin details for display in the console and to store in the dialog
                        const binDetails = [
                            `Bin: ${data.bin_code} (${data.asset_name || ''})`,
                            `Blanking DC: ${data.blanking_dc_entry || ''} (${data.posting_date || ''})`,
                            `SPP Batch: ${data.spp_batch_number || ''}`,
                            `Available Qty: ${data.available_quantity || 0} ${data.stock_uom}`
                        ].join('\n');
                        
                        // Log the details to console for debugging
                        console.log('BIN DETAILS:');
                        console.log(binDetails);
                        
                        // Store all bin-related data as custom properties on the dialog for later use
                        dialog.bin_code = data.bin_code;
                        dialog.asset_name = data.asset_name;
                        dialog.blanking_dc_entry = data.blanking_dc_entry;
                        dialog.posting_date = data.posting_date;
                        dialog.spp_batch_number = data.spp_batch_number;
                        dialog.batch_no = data.batch_no;
                        dialog.available_quantity = data.available_quantity;
                        
                        // Show the blanking DC quantity in the Current Stock field
                        if (data.available_quantity) {
                            console.log(`Setting current stock to blanking DC available quantity: ${data.available_quantity}`);
                            dialog.set_value('current_stock', data.available_quantity);
                        }
                    }
                    
                    // If we have warehouse and quantity data from stock balance
                    if (data.warehouse && data.qty !== undefined) {
                        dialog.set_value('warehouse', data.warehouse);
                        dialog.set_value('current_stock', data.qty);
                        console.log('STOCK BALANCE FOUND:', data.qty, data.stock_uom, 'in', data.warehouse);
                    } else {
                        // Set the warehouse from the mapping but zero quantity
                        dialog.set_value('warehouse', get_warehouse_for_item_group('Compound-Sheeting'));
                        dialog.set_value('current_stock', 0);
                        console.log('NO STOCK FOUND FOR BATCH:', data.batch_no);
                        
                        // Show message but don't block the operation
                        frappe.show_alert({
                            message: __(`No current stock found for batch ${data.batch_no}, but you can still enter physical stock.`),
                            indicator: 'yellow'
                        }, 5);
                    }
                    
                    // Focus on the physical stock field for entry
                    dialog.get_field('physical_stock').$input.focus();
                    
                } else if (data.error) {
                    frappe.msgprint(data.error);
                } else if (data.message) {
                    frappe.msgprint(data.message);
                } else {
                    frappe.msgprint(__('Could not retrieve item data for the scanned clip.'));
                }
            } else {
                frappe.msgprint(__('No information found for Compound - Sheeting item.'));
            }
        }
    });
}

// Helper function to get warehouse for item group (matches the Python version)
function get_warehouse_for_item_group(item_group) {
  const WAREHOUSE_MAPPING = {
    'Raw Material': 'Incoming Store - SPP INDIA',
    'Compound': 'U3-Store - SPP INDIA',
    'Compound-Sheeting': 'Sheeting Warehouse - SPP INDIA',
    'Batch': 'U3-Store - SPP INDIA',
    'Final Batch': 'U3-Store - SPP INDIA',
    'Master Batch': 'U3-Store - SPP INDIA',
    'Mat': 'U2-Store - SPP INDIA',
    'Products': 'U2-Store - SPP INDIA',
    'Finished Product': 'U2-Store - SPP INDIA',
    'Cut Bit': 'Cutbit Warehouse - SPP INDIA',
    'Products Sales': 'U2-Store - SPP INDIA'
  };
  
  // Direct lookup first (exact match)
  if (WAREHOUSE_MAPPING[item_group]) {
    return WAREHOUSE_MAPPING[item_group];
  }
  
  // If no exact match, check if the item_group contains any of the keys
  for (let key in WAREHOUSE_MAPPING) {
    if (item_group.includes(key)) {
      return WAREHOUSE_MAPPING[key];
    }
  }
  
  console.log(`No warehouse mapping found for item group: ${item_group}`);
  return null;
}

function add_entry_to_child_table(frm, values) {
    if (frm && frm.doc) {
      let child_entry = frm.add_child('details');
  
      if (child_entry) {
        // Set common fields
        child_entry.batch_number = values.batch_or_mixed_barcode;
        child_entry.item_code = values.item_code;
        child_entry.item_name = values.item_name;
        child_entry.item_group = values.item_group;
        child_entry.warehouse = values.warehouse;
        
        // Add scan_bin and scan_clip values if they exist (for Compound - Sheeting)
        if (values.scan_bin) {
          child_entry.scan_bin = values.scan_bin;
          
          // Add additional bin details if available
          if (values.bin_code) {
            child_entry.bin_code = values.bin_code;
            child_entry.asset_name = values.asset_name;
          }
          
          // Add Blanking DC details if available
          if (values.blanking_dc_entry) {
            child_entry.blanking_dc_entry = values.blanking_dc_entry;
            child_entry.reference_qty = values.available_quantity;
          }
        }
        
        if (values.scan_clip) {
          child_entry.scan_clip = values.scan_clip;
        }
        
        // If we have batch related info, save it as well
        if (values.batch_no) {
          child_entry.batch_no = values.batch_no;
        }
        
        if (values.spp_batch_number) {
          child_entry.spp_batch_number = values.spp_batch_number;
        }
        
        let stock_uom = values.stock_uom;
        let item_group = values.item_group;
        
        // Set stock and physical stock values based on UOM and item type
        if (stock_uom === 'Kg') {
          // Stock UOM is Kg
          child_entry.current_stock_kg = values.current_stock;
          child_entry.physical_stock_kg = values.physical_stock;
          
          // If we have Nos values available, use them
          if (values.stock_in_nos !== undefined) {
            child_entry.current_stock = values.stock_in_nos;
          }
          
          if (values.physical_stock_in_nos !== undefined) {
            child_entry.physical_stock = values.physical_stock_in_nos;
          }
        } else if (stock_uom === 'Nos') {
          // Stock UOM is Nos
          child_entry.current_stock = values.current_stock;
          child_entry.physical_stock = values.physical_stock;
          
          // If we have Kg values available, use them
          if (values.stock_in_nos !== undefined) {
            child_entry.current_stock_kg = values.stock_in_nos;
          }
          
          if (values.physical_stock_in_nos !== undefined) {
            child_entry.physical_stock_kg = values.physical_stock_in_nos;
          }
        } else {
          // Other UOMs - just set the values we have
          child_entry.current_stock = values.current_stock;
          child_entry.physical_stock = values.physical_stock;
          
          // If we have converted values available, use them
          if (values.stock_in_nos !== undefined) {
            child_entry.current_stock_kg = values.stock_in_nos;
          }
          
          if (values.physical_stock_in_nos !== undefined) {
            child_entry.physical_stock_kg = values.physical_stock_in_nos;
          }
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
