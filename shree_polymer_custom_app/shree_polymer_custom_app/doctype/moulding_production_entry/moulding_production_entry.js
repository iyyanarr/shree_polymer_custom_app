// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Moulding Production Entry', {
	timeline_refresh: frm => {
		frm.events.view_stock_entry(frm)
		// if(frm.doc.batch_details){
		// 	console.log("---",JSON.parse(frm.doc.batch_details))
		// }
	},
	view_stock_entry: (frm) => {
		if (frm.doc.stock_entry_reference) {
			frm.add_custom_button(__("View Stock Entry"), function () {
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry_reference);
			});
		}
		else {
			frm.remove_custom_button('View Stock Entry');
		}
		if (!frm.doc.moulding_date) {
			frm.set_value('moulding_date', frappe.datetime.now_date())
			refresh_field('moulding_date')
		}
	},
	refresh: function (frm) {
		frm.events.view_stock_entry(frm)

		// Add "View Lot Details" button for submitted documents
		if (frm.doc.scan_lot_number && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Lot Details'), function () {
				show_lot_details_dialog(frm);
			});
		}

		frm.set_query("employee", function () {
			return {
				"query": "shree_polymer_custom_app.shree_polymer_custom_app.api.get_process_based_employess",
				"filters": {
					"process": "Moulding"
				}
			}
		});
	},
	"scan_lot_number": (frm) => {
		if (frm.doc.scan_lot_number && frm.doc.scan_lot_number != undefined) {
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.moulding_production_entry.validate_lot_number',
				args: {
					batch_no: frm.doc.scan_lot_number
				},
				freeze: false,
				callback: function (r) {
					console.log("r", r.message.message)
					if (r.message.status == "Failed") {
						frappe.msgprint(r.message.message)
						frm.set_value('scan_lot_number', '')
						// Clear display on failure
						if (frm.fields_dict.bin_tracking_display) {
							frm.fields_dict.bin_tracking_display.$wrapper.html('');
						}
						// Clear stored data
						frm._lot_breakdown_data = null;
					}
					else {
						let total_qty = 0
						r.message.message.map(recp => {
							total_qty += recp.qty
						})
						frm.set_value("scan_lot_number", frm.doc.scan_lot_number.toUpperCase())
						frm.set_value("job_card", r.message.message[0].job_card)
						frm.set_value("spp_batch_number", r.message.message[0].spp_batch_number)
						frm.set_value("batch_no", r.message.message[0].batch_no__)
						frm.set_value("item_to_produce", r.message.message[0].item_to_produce)
						frm.set_value("compound", r.message.message[0].compound)
						frm.set_value("mould_reference", r.message.message[0].mould_reference)
						frm.set_value("no_of_cavity_in_mspec", r.message.message[0].no_of_running_cavities)
						// ✅ FIX: Update availabe_qty calculation to account for balance bins
						let actual_available_qty = 0
						r.message.message.map(recp => {
							actual_available_qty += recp.qty
						})
						frm.set_value("availabe_qty", actual_available_qty)
						frm.set_value("batch_details", JSON.stringify(r.message.message))

						// Store batch details for later use in weight breakdown
						frm._lot_breakdown_data = {
							lot_number: frm.doc.scan_lot_number.toUpperCase(),
							mould_reference: r.message.message[0].mould_reference,
							batch_details: r.message.message
						};

						// Update weight breakdown if weight already entered
						if (frm.doc.weight) {
							update_weight_breakdown_display(frm);
						} else {
							// Show message that weight breakdown will appear after entering weight
							if (frm.fields_dict.bin_tracking_display) {
								frm.fields_dict.bin_tracking_display.$wrapper.html(
									'<div class="text-muted" style="padding: 10px;">Weight breakdown will appear after entering weight</div>'
								);
							}
						}
					}
				}
			});
		} else {
			// Clear display when lot number is cleared
			if (frm.fields_dict.bin_tracking_display) {
				frm.fields_dict.bin_tracking_display.$wrapper.html('');
			}
			frm._lot_breakdown_data = null;
		}
	},
	weight: (frm) => {
		// Update weight breakdown display when weight is entered
		if (frm.doc.weight && frm._lot_breakdown_data) {
			update_weight_breakdown_display(frm);
		}
	},
	"scan_supervisor": (frm) => {
		if (frm.doc.scan_supervisor && frm.doc.scan_supervisor != undefined) {
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.moulding_production_entry.validate_operator',
				args: {
					operator: frm.doc.scan_supervisor,
					supervisor: true
				},
				freeze: true,
				callback: function (r) {
					if (r.message.status == "Failed") {
						frm.set_value("scan_supervisor", "")
						frappe.msgprint(r.message.message)
					}
					else {
						frm.set_value("supervisor_id", r.message.message.name)
						frm.set_value("supervisor_name", r.message.message.employee_name)
					}
				}
			});
		}
	},
	"operator": (frm) => {
		if (frm.doc.operator && frm.doc.operator != undefined) {
			frappe.call({
				method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.moulding_production_entry.validate_operator',
				args: {
					operator: frm.doc.operator
				},
				freeze: true,
				callback: function (r) {
					if (r.message.status == "Failed") {
						frm.set_value("operator", "")
						frappe.msgprint(r.message.message)
					}
					else {
						frm.set_value("employee", r.message.message.name)
						frm.set_value("employee_name", r.message.message.employee_name)
					}
				}
			});
		}
	},
	"scan_bin": (frm) => {
		// if(!frm.doc.__islocal){
		if (frm.doc.scan_bin && frm.doc.scan_bin != undefined) {
			if (frm.doc.job_card) {
				let flag = true
				if (frm.doc.balance_bins) {
					frm.doc.balance_bins.map(resp => {
						if (resp.bin_barcode == frm.doc.scan_bin) {
							flag = false
							frappe.msgprint(`The bin - <b>${frm.doc.scan_bin}</b> is already added..!`)
							frm.set_value('scan_bin', '')
							return
						}
					})
				}
				else {
					flag = true
				}
				if (flag) {
					frappe.call({
						method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.moulding_production_entry.moulding_production_entry.validate_bin',
						args: {
							batch_no: frm.doc.scan_bin,
							job_card: frm.doc.job_card
						},
						freeze: false,
						callback: function (r) {
							if (r.message.status == "Failed") {
								frappe.msgprint(r.message.message)
							}
							else {
								frm.set_value("scan_bin", frm.doc.scan_bin.toUpperCase())
								frm.set_value("bin_weight", r.message.bin_weight)
								frm.set_value("bin_code", r.message.blanking_bin)
								frm.set_value("bin_name", r.message.asset_name)
							}
						}
					});
				}
			}
			else {
				frappe.msgprint("Please Scan Lot No. before scan Bin")
			}
		}
		// }
		// else{
		// 	frappe.msgprint("Please save the document,before scan bin..!")
		// }
	},
	add(frm) {
		if (!frm.doc.scan_bin || frm.doc.scan_bin == undefined) {
			frappe.msgprint("Please Scan <b>Bin</b> before add.");
			return
		}
		if (!frm.doc.weight_of_balance_bin || frm.doc.weight_of_balance_bin == undefined) {
			frappe.msgprint("Please enter <b>Gross weight</b> of balance bin.");
			return
		}
		if (!frm.doc.bin_weight || frm.doc.bin_weight == undefined) {
			frappe.msgprint("<b>Bin Weight</b> is missing.");
			return
		}
		if (!frm.doc.bin_code || frm.doc.bin_code == undefined) {
			frappe.msgprint("<b>Bin code</b> is missing.");
			return
		}
		if (!frm.doc.net_weight || frm.doc.net_weight == undefined) {
			frappe.msgprint("<b>Net Weight</b> of balance bin is missing.");
			return
		}
		let resp = update_bin_details(frm)
		if (resp) {
			let row = frappe.model.add_child(frm.doc, "Moulding Balance Bin", "balance_bins");
			row.bin_barcode = frm.doc.scan_bin
			row.weight_of_balance_bin = frm.doc.weight_of_balance_bin
			row.bin_weight = frm.doc.bin_weight
			row.bin_code = frm.doc.bin_code
			row.bin_name = frm.doc.bin_name
			row.net_weight = frm.doc.net_weight
			row.compound_consumed = frm.consumed__qty
			frm.refresh_field('balance_bins');
			frm.set_value('scan_bin', '')
			frm.set_value('weight_of_balance_bin', '')
			frm.set_value('bin_weight', ''),
				frm.set_value('bin_code', '')
			frm.set_value('bin_name', '')
			frm.set_value('net_weight', 0)
		}

		function update_bin_details(frm) {
			let bin_info;
			let batch_details = JSON.parse(frm.doc.batch_details)
			batch_details.map(res => {
				if (res.bin == frm.doc.bin_code) {
					bin_info = res
				}
			})
			if (bin_info) {
				let flag = false
				let net_weight = parseFloat((parseFloat(frm.doc.weight_of_balance_bin.toFixed(3)) - parseFloat((frm.doc.bin_weight.toFixed(3)))).toFixed(3))
				batch_details.map(res => {
					if (res.bin == frm.doc.bin_code) {
						if (parseFloat(res.qty.toFixed(3)) <= net_weight) {
							frappe.msgprint(`The balance bin net weight <b>${net_weight}</b> can't be greater than or equal to <b>Bin</b> Qty - ${res.qty.toFixed(3)}`)
							frm.set_value("net_weight", 0);
							frm.set_value("weight_of_balance_bin", 0);
							return
						}
						else {
							flag = true
							// ✅ FIX: Calculate actual consumed quantity (original - remaining)
							res["consumed__qty"] = parseFloat((parseFloat(res.qty.toFixed(3)) - net_weight).toFixed(3))
							res["balance__qty"] = net_weight
							res["is__consumed"] = 1
							res["is_balance_bin"] = 1
							frm.consumed__qty = res["consumed__qty"]
							return
						}
					}
				})
				if (flag) {
					var net_wt = parseFloat((frm.doc.weight_of_balance_bin - frm.doc.bin_weight).toFixed(3))
					frm.set_value("net_weight", net_wt);
					frm.set_value("batch_details", JSON.stringify(batch_details));
					return true
				}
				else {
					return false
				}
			}
			else {
				frappe.msgprint(`<b>The Scanned Bin</b> not exists in consumed bins..!`)
				return false
			}
		}
	},
	"weight_of_balance_bin": function (frm) {
		frm.consumed__qty = 0
		if (frm.doc.weight_of_balance_bin) {
			if (frm.doc.scan_bin && frm.doc.weight) {
				if (frm.doc.batch_details) {
					let in_flag = true
					if (parseFloat(frm.doc.weight_of_balance_bin.toFixed(3)) <= parseFloat(frm.doc.bin_weight.toFixed(3))) {
						in_flag = false
						frm.set_value("net_weight", 0);
						frm.set_value("weight_of_balance_bin", 0);
						frappe.msgprint(`The <b>Gross Weight</b> can't be less than the <b>Bin Weight</b>..!`)
						return
					}
					else if (in_flag) {
						let batch_details = JSON.parse(frm.doc.batch_details)
						let flag = false
						let net_weight = parseFloat((parseFloat(frm.doc.weight_of_balance_bin.toFixed(3)) - parseFloat((frm.doc.bin_weight.toFixed(3)))).toFixed(3))
						batch_details.map(res => {
							if (res.bin == frm.doc.bin_code) {
								if (parseFloat(res.qty.toFixed(3)) <= net_weight) {
									frappe.msgprint(`The balance bin net weight <b>${net_weight}</b> can't be greater than or equal to <b>Bin</b> Qty - ${res.qty.toFixed(3)}`)
									frm.set_value("net_weight", 0);
									frm.set_value("weight_of_balance_bin", 0);
									return
								}
								else {
									flag = true
									return
								}
							}
						})
						if (flag) {
							var net_wt = parseFloat((frm.doc.weight_of_balance_bin - frm.doc.bin_weight).toFixed(3))
							frm.set_value("net_weight", net_wt);
							return true
						}
					}
				}
				else {
					frappe.msgprint(`<b>Bin Details</b> not found..!`)
				}
			}
			else {
				if (!frm.doc.scan_bin) {
					frappe.msgprint("Please scan bin before enter gross weight of balance bin...!")
					frm.set_value("weight_of_balance_bin", 0);
					return
				}
				if (!frm.doc.weight) {
					frappe.msgprint("Please enter the <b>Production Weight</b> before enter gross weight of balance bin...!")
					frm.set_value("weight_of_balance_bin", 0);
				}

			}
		}
	},

});

frappe.ui.form.on('Moulding Balance Bin', {
	before_balance_bins_remove(frm, cdt, cdn) {
		let row = locals[cdt][cdn]
		let batch_details = JSON.parse(frm.doc.batch_details)
		batch_details.map(res => {
			if (res.bin == row.bin_code) {
				delete res["consumed__qty"]
				delete res["balance__qty"]
				delete res["is__consumed"]
				delete res["is_balance_bin"]
			}
		})
		frm.set_value("batch_details", JSON.stringify(batch_details));
	}
});



// Helper functions for Lot Details Dialog
function show_lot_details_dialog(frm) {
	frappe.call({
		method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.get_lot_details',
		args: {
			lot_number: frm.doc.scan_lot_number,
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
					generate_lot_details_html(r.message)
				);

				d.show();
			} else {
				frappe.msgprint(__('Failed to fetch lot details'));
			}
		}
	});
}

function generate_lot_details_html(data) {
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

//Update weight breakdown display when weight is entered
function update_weight_breakdown_display(frm) {
	if (!frm._lot_breakdown_data || !frm.doc.weight) {
		return;
	}

	// Fetch comprehensive lot details with blank weight
	frappe.call({
		method: 'shree_polymer_custom_app.shree_polymer_custom_app.api.get_lot_details',
		args: {
			lot_number: frm._lot_breakdown_data.lot_number,
			doctype: 'Moulding Production Entry',
			docname: frm.docname || '',
			mould_reference: frm._lot_breakdown_data.mould_reference
		},
		callback: function (r) {
			if (r.message && r.message.status === 'success' && frm.fields_dict.bin_tracking_display) {
				const html = generate_weight_breakdown_html(frm, r.message);
				frm.fields_dict.bin_tracking_display.$wrapper.html(html);
			}
		}
	});
}

// Generate comprehensive weight breakdown HTML
function generate_weight_breakdown_html(frm, lot_data) {
	const observed_weight = parseFloat(frm.doc.weight || 0);
	const blank_weight_kg = parseFloat(lot_data.blank_weight_kg || 0);
	const purged_compound = parseFloat(frm.doc.purged_compound || 0);
	const compound_leakage = parseFloat(frm.doc.compound_leakage || 0);
	const scrap_compound = purged_compound + compound_leakage;

	// Calculate rejection weights
	let patrol_rejection_weight = 0;
	let line_rejection_weight = 0;
	let patrol_rejected_nos = 0;
	let line_rejected_nos = 0;

	if (lot_data.rejection_details) {
		if (lot_data.rejection_details.patrol_inspection) {
			patrol_rejected_nos = lot_data.rejection_details.patrol_inspection.rejected_qty || 0;
			patrol_rejection_weight = lot_data.rejection_details.patrol_inspection.calculated_weight_kg || 0;
		}
		if (lot_data.rejection_details.line_inspection) {
			line_rejected_nos = lot_data.rejection_details.line_inspection.rejected_qty || 0;
			line_rejection_weight = lot_data.rejection_details.line_inspection.calculated_weight_kg || 0;
		}
	}

	// Calculations
	const total_production_weight = observed_weight + patrol_rejection_weight + line_rejection_weight;
	const estimated_nol = blank_weight_kg > 0 ? total_production_weight / blank_weight_kg : 0;
	const total_compound_consumption = total_production_weight + scrap_compound;

	let html = `
		<div style="border: 2px solid #2c5aa0; border-radius: 8px; padding: 16px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); margin-top: 12px; margin-bottom: 15px;">
			<h5 style="margin: 0 0 16px 0; color: #2c5aa0; font-size: 16px; border-bottom: 2px solid #2c5aa0; padding-bottom: 8px;">
				<i class="fa fa-calculator"></i> Weight Breakdown Display - Lot <b>${lot_data.lot_number}</b>
			</h5>
			
			<!-- Weight Calculations Section -->
			<div style="background: white; border-radius: 6px; padding: 14px; margin-bottom: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
				<table style="width: 100%; border-collapse: collapse; font-size: 13px;">
					<tr style="background: #e3f2fd;">
						<td style="padding: 10px; font-weight: bold; width: 50%; border-bottom: 1px solid #ddd;">Parameter</td>
						<td style="padding: 10px; text-align: right; font-weight: bold; border-bottom: 1px solid #ddd;">Value (Kg)</td>
					</tr>
					<tr>
						<td style="padding: 8px; border-bottom: 1px solid #eee;">a. Observed Weight</td>
						<td style="padding: 8px; text-align: right; font-size: 16px; font-weight: bold; color: #2c5aa0; border-bottom: 1px solid #eee;">${observed_weight.toFixed(3)}</td>
					</tr>
					<tr>
						<td style="padding: 8px; border-bottom: 1px solid #eee;">
							b. Rejection Weight (Patrol: ${patrol_rejected_nos} nos, Line: ${line_rejected_nos} nos)
							<div style="font-size: 11px; color: #666; margin-top: 4px;">
								• Patrol: ${patrol_rejection_weight.toFixed(3)} Kg<br/>
								• Line: ${line_rejection_weight.toFixed(3)} Kg
							</div>
						</td>
						<td style="padding: 8px; text-align: right; font-weight: bold; color: #d32f2f; border-bottom: 1px solid #eee;">${(patrol_rejection_weight + line_rejection_weight).toFixed(3)}</td>
					</tr>
					<tr style="background: #fff9e6;">
						<td style="padding: 10px; font-weight: bold; border-bottom: 2px solid #ffc107;">c. Total Production Weight (a + b)</td>
						<td style="padding: 10px; text-align: right; font-size: 17px; font-weight: bold; color: #f57c00; border-bottom: 2px solid #ffc107;">${total_production_weight.toFixed(3)}</td>
					</tr>
					<tr>
						<td style="padding: 8px; border-bottom: 1px solid #eee;">d. Estimated Number of Lifts (c ÷ Blank Wt: ${blank_weight_kg.toFixed(3)})</td>
						<td style="padding: 8px; text-align: right; font-size: 16px; font-weight: bold; color: #388e3c; border-bottom: 1px solid #eee;">${estimated_nol.toFixed(2)} lifts</td>
					</tr>
					<tr style="background: #f1f8ff;">
						<td style="padding: 10px; font-weight: bold;">
							e. Compound Consumption Working
							<div style="font-size: 11px; color: #666; font-weight: normal; margin-top: 4px;">
								Total Prod (${total_production_weight.toFixed(3)}) + Scrap (${scrap_compound.toFixed(3)})
							</div>
						</td>
						<td style="padding: 10px; text-align: right; font-size: 17px; font-weight: bold; color: #1565c0;">${total_compound_consumption.toFixed(3)}</td>
					</tr>
				</table>
			</div>`;

	// Add Bin Details Section
	if (lot_data.bin_details && lot_data.bin_details.length > 0) {
		html += `
			<div style="background: white; border-radius: 6px; padding: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
				<h6 style="margin: 0 0 10px 0; color: #2c5aa0; font-size: 14px;">
					<i class="fa fa-inbox"></i> f. Blank Bin Details
				</h6>
				<table style="width: 100%; border-collapse: collapse; font-size: 12px;">
					<thead style="background: #e5e7eb;">
						<tr>
							<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Bin</th>
							<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Compound</th>
							<th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Consumed (Kg)</th>
							<th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Balance (Kg)</th>
						</tr>
					</thead>
					<tbody>`;

		let total_consumed = 0;
		lot_data.bin_details.forEach(bin => {
			if (bin.is__consumed) {
				const consumed = parseFloat(bin.consumed__qty || 0);
				const balance = parseFloat(bin.balance__qty || 0);
				total_consumed += consumed;
				html += `
					<tr>
						<td style="padding: 6px; border: 1px solid #ddd;"><b>${bin.bin || '-'}</b></td>
						<td style="padding: 6px; border: 1px solid #ddd;">${bin.compound || '-'}</td>
						<td style="padding: 6px; text-align: right; border: 1px solid #ddd;">${consumed.toFixed(3)}</td>
						<td style="padding: 6px; text-align: right; border: 1px solid #ddd;">${balance.toFixed(3)}</td>
					</tr>`;
			}
		});

		html += `
					<tr style="font-weight: bold; background: #f3f4f6;">
						<td colspan="2" style="padding: 8px; border: 1px solid #ddd;">Total</td>
						<td style="padding: 8px; text-align: right; border: 1px solid #ddd;">${total_consumed.toFixed(3)} Kg</td>
						<td style="padding: 8px; border: 1px solid #ddd;"></td>
					</tr>
				</tbody>
			</table>
		</div>`;
	}

	html += '</div>';
	return html;
}
