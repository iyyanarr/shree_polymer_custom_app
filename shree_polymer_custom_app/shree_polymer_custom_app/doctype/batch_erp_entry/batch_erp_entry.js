// Copyright (c) 2022, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Batch ERP Entry', {
	timeline_refresh:frm =>{
		frm.events.view_stock_entry(frm)
	},
	view_stock_entry:(frm) =>{
		if(frm.doc.status && frm.doc.status == "Success" && frm.doc.stock_entry_reference){
			frm.add_custom_button(__("View Stock Entry"), function(){
				frappe.route_options = {
					"name": ["in",frm.doc.stock_entry_reference.split(',')]
				};
				frappe.set_route("List", "Stock Entry");
			  });
		}
		else{
			frm.remove_custom_button('View Stock Entry');
		}
	},
	setup(frm) {
		frm.has_import_file = () => {
			return frm.doc.import_file || frm.doc.google_sheets_url;
		};
	},
	refresh(frm) {
		frm.events.view_stock_entry(frm)
		frm.page.hide_icon_group();
		frm.trigger("update_indicators");
		frm.trigger("import_file");

		if (frm.doc.status == "Success") {frm.trigger("show_import_status");}
		
	},
	onload_post_render(frm) {
		frm.trigger("update_primary_action");
	},

	update_primary_action(frm) {
		if (frm.is_dirty()) {
			frm.enable_save();
			return;
		}
		frm.disable_save();
		if (frm.doc.status !== "Success") {
			if (!frm.is_new() && frm.has_import_file()) {
				let label = frm.doc.status === "Pending" ? __("Upload Batches") : __("Retry");
				frm.page.set_primary_action(label, () => frm.events.start_import(frm));
			} else {
				frm.page.set_primary_action(__("Save"), () => frm.save());
			}
		}
	},

	start_import(frm) {
		frm.call({
			method: "form_start_import",
			args: { data_import: frm.doc.name },
			btn: frm.page.btn_primary,
		}).then((r) => {
			if (r.message === true) {
				frm.disable_save();
				cur_frm.reload_doc();
			}
		});
	},
	show_import_warnings(frm, preview_data) {
		let columns = preview_data.columns;
		let warnings = JSON.parse(frm.doc.template_warnings || "[]");
		warnings = warnings.concat(preview_data.warnings || []);

		frm.toggle_display("import_warnings_section", warnings.length > 0);
		if (warnings.length === 0) {
			frm.get_field("import_warnings").$wrapper.html("");
			return;
		}

		// group warnings by row
		let warnings_by_row = {};
		let other_warnings = [];
		for (let warning of warnings) {
			if (warning.row) {
				warnings_by_row[warning.row] = warnings_by_row[warning.row] || [];
				warnings_by_row[warning.row].push(warning);
			} else {
				other_warnings.push(warning);
			}
		}

		let html = "";
		html += Object.keys(warnings_by_row)
			.map((row_number) => {
				let message = warnings_by_row[row_number]
					.map((w) => {
						if (w.field) {
							let label =
								w.field.label +
								(w.field.parent !== frm.doc.reference_doctype
									? ` (${w.field.parent})`
									: "");
							return `<li>${label}: ${w.message}</li>`;
						}
						return `<li>${w.message}</li>`;
					})
					.join("");
				return `
				<div class="warning" data-row="${row_number}">
					<h5 class="text-uppercase">${__("Row {0}", [row_number])}</h5>
					<div class="body"><ul>${message}</ul></div>
				</div>
			`;
			})
			.join("");

		html += other_warnings
			.map((warning) => {
				let header = "";
				if (warning.col) {
					let column_number = `<span class="text-uppercase">${__("Column {0}", [
						warning.col,
					])}</span>`;
					let column_header = columns[warning.col].header_title;
					header = `${column_number} (${column_header})`;
				}
				return `
					<div class="warning" data-col="${warning.col}">
						<h5>${header}</h5>
						<div class="body">${warning.message}</div>
					</div>
				`;
			})
			.join("");
		frm.get_field("import_warnings").$wrapper.html(`
			<div class="row">
				<div class="col-sm-10 warnings">${html}</div>
			</div>
		`);
	},

	show_import_status(frm) {
		
		frappe.call({
			method: "shree_polymer_custom_app.shree_polymer_custom_app.doctype.batch_erp_entry.batch_erp_entry.get_import_status",
			args: {
				data_import_name: frm.doc.name,
			},
			callback: function (r) {
				let successful_records = cint(r.message.success);
				let failed_records = cint(r.message.failed);
				let total_records = cint(r.message.total_records);

				// if (!total_records) return;

				let message;
				frm.dashboard.set_headline("Successfully imported "+successful_records+" records.");
			},
		});
	},

	update_indicators(frm) {
		const indicator = frappe.get_indicator(frm.doc);
		if (indicator) {
			frm.page.set_indicator(indicator[0], indicator[1]);
		} else {
			frm.page.clear_indicator();
		}
	},
	import_file(frm) {
		frm.toggle_display("section_import_preview", frm.has_import_file());
		if (!frm.has_import_file()) {
			frm.get_field("import_preview").$wrapper.empty();
			return;
		} else {
			frm.trigger("update_primary_action");
		}

		// load import preview
		frm.get_field("import_preview").$wrapper.empty();
		$('<span class="text-muted">')
			.html(__("Loading import file..."))
			.appendTo(frm.get_field("import_preview").$wrapper);
		if(!frm.doc.__islocal && frm.doc.status!='Success'){
			frm.call({
				method: "get_preview_from_template",
				freeze:true,
				args: {
					data_import: frm.doc.name,
					google_sheets_url: frm.doc.google_sheets_url,
				},
				error_handlers: {
					TimestampMismatchError() {
						// ignore this error
					},
				},
			}).then((r) => {
				let preview_data = r.message;
				frm.events.show_import_preview(frm, preview_data);
				frm.events.show_import_warnings(frm, preview_data);
			});
		}
	},

	show_import_preview(frm, preview_data) {
		let import_log = preview_data.import_log;

		if (frm.import_preview && frm.import_preview.doctype === frm.doc.reference_doctype) {
			frm.import_preview.preview_data = preview_data;
			frm.import_preview.import_log = import_log;
			frm.import_preview.refresh();
			return;
		}

		frappe.require("data_import_tools.bundle.js", () => {
			frm.import_preview = new frappe.data_import.ImportPreview({
				wrapper: frm.get_field("import_preview").$wrapper,
				doctype: "Imported Batches",
				preview_data,
				import_log,
				frm,
				events: {
					remap_column(changed_map) {
						let template_options = JSON.parse(frm.doc.template_options || "{}");
						template_options.column_to_field_map =
							template_options.column_to_field_map || {};
						Object.assign(template_options.column_to_field_map, changed_map);
						frm.set_value("template_options", JSON.stringify(template_options));
						frm.save().then(() => frm.trigger("import_file"));
					},
				},
			});
		});
	},
});
