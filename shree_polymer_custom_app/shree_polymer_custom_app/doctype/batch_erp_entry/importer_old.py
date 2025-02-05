# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import io
import json
import os
import re
import timeit
from datetime import date, datetime, time

import frappe
from frappe import _
from frappe.core.doctype.version.version import get_diff
from frappe.model import no_value_fields
from frappe.utils import cint, cstr, duration_to_seconds, flt, update_progress_bar,format_time, formatdate, getdate, nowdate,now
from frappe.utils.csvutils import get_csv_content_from_google_sheets, read_csv_content
from frappe.utils.xlsxutils import (
	read_xls_file_from_attached_file,
	read_xlsx_file_from_attached_file,
)

INVALID_VALUES = ("", None)
MAX_ROWS_IN_PREVIEW = 10
INSERT = "Insert New Records"
UPDATE = "Update Existing Records"
DURATION_PATTERN = re.compile(r"^(?:(\d+d)?((^|\s)\d+h)?((^|\s)\d+m)?((^|\s)\d+s)?)$")

# first check

class Importer:
	def __init__(self, doctype, data_import=None, file_path=None, import_type=None, console=False):
		self.doctype = doctype
		self.console = console

		self.data_import = data_import
		if not self.data_import:
			self.data_import = frappe.get_doc(doctype="Data Import")
			if import_type:
				self.data_import.import_type = import_type

		self.template_options = frappe.parse_json(self.data_import.template_options or "{}")
		self.import_type = self.data_import.import_type

		self.import_file = ImportFile(
			doctype,
			file_path or data_import.google_sheets_url or data_import.import_file,
			self.template_options,
			self.import_type,
		)


	def get_data_for_import_preview(self):
		out = self.import_file.get_data_for_import_preview()

		out.import_log = frappe.db.get_all(
			"Imported Batch Log",
			fields=["row_indexes", "success"],
			filters={"data_import": self.data_import.name},
			order_by="log_index",
			limit=10,
		)
		return out

	def before_import(self):
		# set user lang for translations
		frappe.cache().hdel("lang", frappe.session.user)
		frappe.set_user_lang(frappe.session.user)

		# set flags
		frappe.flags.in_import = True
		frappe.flags.mute_emails = self.data_import.mute_emails

		self.data_import.db_set("template_warnings", "")

	def import_data(self):
		self.before_import()

		# parse docs from rows
		payloads = self.import_file.get_payloads_for_import()
		# frappe.log_error(payloads,'payloads')
		# dont import if there are non-ignorable warnings
		warnings = self.import_file.get_warnings()
		warnings = [w for w in warnings if w.get("type") != "info"]
		# frappe.log_error('payloads','0')
		# frappe.log_error(warnings,'warnings')
		# if warnings:
		# 	if self.console:
		# 		self.print_grouped_warnings(warnings)
		# 	else:
		# 		self.data_import.db_set("template_warnings", json.dumps(warnings))
		# 	return

		# setup import log
		import_log = (
			frappe.db.get_all(
				"Imported Batch Log",
				fields=["row_indexes", "success", "log_index"],
				filters={"data_import": self.data_import.name},
				order_by="log_index",
			)
			or []
		)

		log_index = 0

		# Do not remove rows in case of retry after an error or pending data import
		if (
			self.data_import.status == "Partial Success"
			and len(import_log) >= self.data_import.payload_count
		):
			# remove previous failures from import log only in case of retry after partial success
			import_log = [log for log in import_log if log.get("success")]

		# get successfully imported rows
		imported_rows = []
		for log in import_log:
			log = frappe._dict(log)
			if log.success or len(import_log) < self.data_import.payload_count:
				imported_rows += json.loads(log.row_indexes)

			log_index = log.log_index
		# frappe.log_error('payloads','1')
		# start import
		total_payload_count = len(payloads)
		batch_size = frappe.conf.data_import_batch_size or 1000
		is_allow = 1
		spp_settings = frappe.get_single("SPP Settings")
		# is_allow = check_items_stock(payloads,batch_size,spp_settings.target_warehouse)
		bom_validate = validate_bom(payloads,batch_size)
		if bom_validate.get("status"):
			is_allow = 1
			for batch_index, batched_payloads in enumerate(frappe.utils.create_batch(payloads, batch_size)):
				for i, payload in enumerate(batched_payloads):
					doc = payload.doc
					if not frappe.db.get_all("Imported Batches",filters={"compound_code":doc.compound_code,"mixbatchno":doc.mixbatchno,"mix_barcode":doc.mix_barcode,"material":doc.material}):
						row_indexes = [row.row_number for row in payload.rows]
						current_index = (i + 1) + (batch_index * batch_size)

						if set(row_indexes).intersection(set(imported_rows)):
							print("Skipping imported rows", row_indexes)
							if total_payload_count > 5:
								frappe.publish_realtime(
									"data_import_progress",
									{
										"current": current_index,
										"total": total_payload_count,
										"skipping": True,
										"data_import": self.data_import.name,
									},
								)
							continue

						try:
							start = timeit.default_timer()
							doc = self.process_doc(doc)
							processing_time = timeit.default_timer() - start
							eta = self.get_eta(current_index, total_payload_count, processing_time)

							if self.console:
								update_progress_bar(
									f"Importing {total_payload_count} records",
									current_index,
									total_payload_count,
								)
							elif total_payload_count > 5:
								frappe.publish_realtime(
									"data_import_progress",
									{
										"current": current_index,
										"total": total_payload_count,
										"docname": doc.name,
										"data_import": self.data_import.name,
										"success": True,
										"row_indexes": row_indexes,
										"eta": eta,
									},
								)

							create_import_log(
								self.data_import.name,
								log_index,
								{"success": True, "docname": doc.name, "row_indexes": row_indexes},
							)
							
							log_index += 1

							if not self.data_import.status == "Partial Success":
								self.data_import.db_set("status", "Partial Success")

							# commit after every successful import
							frappe.db.commit()

						except Exception:
							messages = frappe.local.message_log
							frappe.clear_messages()

							# rollback if exception
							frappe.db.rollback()

							create_import_log(
								self.data_import.name,
								log_index,
								{
									"success": False,
									"exception": frappe.get_traceback(),
									"messages": messages,
									"row_indexes": row_indexes,
								},
							)

							log_index += 1
							frappe.log_error(message=frappe.get_traceback(),title="import_data in importer.py")

			# Logs are db inserted directly so will have to be fetched again
			import_log = (
				frappe.db.get_all(
					"Imported Batch Log",
					fields=["row_indexes", "success", "log_index"],
					filters={"data_import": self.data_import.name},
					order_by="log_index",
				)
				or []
			)

			# set status
			failures = [log for log in import_log if not log.get("success")]
			if len(failures) == total_payload_count:
				status = "Pending"
			elif len(failures) > 0:
				status = "Partial Success"
			else:
				status = "Success"

			if self.console:
				self.print_import_log(import_log)
			else:
				self.data_import.db_set("status", status)

			self.after_import()

			return import_log
		else:
			frappe.throw(bom_validate.get("message"))

	def after_import(self):
		from frappe.utils.background_jobs import enqueue
		create_wos(self.data_import.name)
		frappe.flags.in_import = False
		frappe.flags.mute_emails = False

	def process_doc(self, doc):
		if self.import_type == INSERT:
			return self.insert_record(doc)
		elif self.import_type == UPDATE:
			return self.update_record(doc)

	def insert_record(self, doc):
		meta = frappe.get_meta(self.doctype)
		new_doc = frappe.new_doc(self.doctype)
		if self.data_import.import_file:
			if "-" in str(doc.date):
				date_obj = str(doc.date).split(' ')[0].split('-')
				doc.date = getdate(str(date_obj[0])+"-"+str(date_obj[2])+"-"+str(date_obj[1]))
			if "/" in str(doc.date):
				date_obj = str(doc.date).split('/')
				doc.date = getdate(str(date_obj[2])+"-"+str(date_obj[1])+"-"+str(date_obj[0]))
		if self.data_import.google_sheets_url:
			date_obj = str(doc.date).split('/')
			doc.date = getdate(str(date_obj[2])+"-"+str(date_obj[1])+"-"+str(date_obj[0]))
		new_doc.update(doc)

		if not doc.name and (meta.autoname or "").lower() != "prompt":
			# name can only be set directly if autoname is prompt
			new_doc.set("name", None)

		new_doc.flags.updater_reference = {
			"doctype": self.data_import.doctype,
			"docname": self.data_import.name,
			"label": _("via Data Import"),
		}

		new_doc.insert()
		if meta.is_submittable and self.data_import.submit_after_import:
			new_doc.submit()
		return new_doc

	def update_record(self, doc):
		id_field = get_id_field(self.doctype)
		existing_doc = frappe.get_doc(self.doctype, doc.get(id_field.fieldname))

		updated_doc = frappe.get_doc(self.doctype, doc.get(id_field.fieldname))

		updated_doc.update(doc)

		if get_diff(existing_doc, updated_doc):
			# update doc if there are changes
			updated_doc.flags.updater_reference = {
				"doctype": self.data_import.doctype,
				"docname": self.data_import.name,
				"label": _("via Data Import"),
			}
			updated_doc.save()
			return updated_doc
		else:
			# throw if no changes
			frappe.throw(_("No changes to update"))

	def get_eta(self, current, total, processing_time):
		self.last_eta = getattr(self, "last_eta", 0)
		remaining = total - current
		eta = processing_time * remaining
		if not self.last_eta or eta < self.last_eta:
			self.last_eta = eta
		return self.last_eta

	def export_errored_rows(self):
		from frappe.utils.csvutils import build_csv_response

		if not self.data_import:
			return

		import_log = (
			frappe.db.get_all(
				"Imported Batch Log",
				fields=["row_indexes", "success"],
				filters={"data_import": self.data_import.name},
				order_by="log_index",
			)
			or []
		)

		failures = [log for log in import_log if not log.get("success")]
		row_indexes = []
		for f in failures:
			row_indexes.extend(json.loads(f.get("row_indexes", [])))

		# de duplicate
		row_indexes = list(set(row_indexes))
		row_indexes.sort()

		header_row = [col.header_title for col in self.import_file.columns]
		rows = [header_row]
		rows += [row.data for row in self.import_file.data if row.row_number in row_indexes]

		build_csv_response(rows, _(self.doctype))

	def export_import_log(self):
		from frappe.utils.csvutils import build_csv_response

		if not self.data_import:
			return

		import_log = frappe.db.get_all(
			"Imported Batch Log",
			fields=["row_indexes", "success", "messages", "exception", "docname"],
			filters={"data_import": self.data_import.name},
			order_by="log_index",
		)

		header_row = ["Row Numbers", "Status", "Message", "Exception"]

		rows = [header_row]

		for log in import_log:
			row_number = json.loads(log.get("row_indexes"))[0]
			status = "Success" if log.get("success") else "Failure"
			message = (
				"Successfully Imported {}".format(log.get("docname"))
				if log.get("success")
				else log.get("messages")
			)
			exception = frappe.utils.cstr(log.get("exception", ""))
			rows += [[row_number, status, message, exception]]

		build_csv_response(rows, self.doctype)

	def print_import_log(self, import_log):
		failed_records = [log for log in import_log if not log.success]
		successful_records = [log for log in import_log if log.success]

		if successful_records:
			print()
			print(f"Successfully imported {len(successful_records)} records out of {len(import_log)}")

		if failed_records:
			print(f"Failed to import {len(failed_records)} records")
			file_name = f"{self.doctype}_import_on_{frappe.utils.now()}.txt"
			print("Check {} for errors".format(os.path.join("sites", file_name)))
			text = ""
			for w in failed_records:
				text += "Row Indexes: {}\n".format(str(w.get("row_indexes", [])))
				text += "Messages:\n{}\n".format("\n".join(w.get("messages", [])))
				text += "Traceback:\n{}\n\n".format(w.get("exception"))

			with open(file_name, "w") as f:
				f.write(text)

	def print_grouped_warnings(self, warnings):
		warnings_by_row = {}
		other_warnings = []
		for w in warnings:
			if w.get("row"):
				warnings_by_row.setdefault(w.get("row"), []).append(w)
			else:
				other_warnings.append(w)

		for row_number, warnings in warnings_by_row.items():
			print(f"Row {row_number}")
			for w in warnings:
				print(w.get("message"))

		for w in other_warnings:
			print(w.get("message"))


class ImportFile:
	def __init__(self, doctype, file, template_options=None, import_type=None):
		self.doctype = doctype
		self.template_options = template_options or frappe._dict(column_to_field_map=frappe._dict())
		self.column_to_field_map = self.template_options.column_to_field_map
		self.import_type = import_type
		self.warnings = []

		self.file_doc = self.file_path = self.google_sheets_url = None
		if isinstance(file, str):
			if frappe.db.exists("File", {"file_url": file}):
				self.file_doc = frappe.get_doc("File", {"file_url": file})
			elif "docs.google.com/spreadsheets" in file:
				self.google_sheets_url = file
			elif os.path.exists(file):
				self.file_path = file

		if not self.file_doc and not self.file_path and not self.google_sheets_url:
			frappe.throw(_("Invalid template file for import"))

		self.raw_data = self.get_data_from_template_file()
		self.parse_data_from_template()

	def get_data_from_template_file(self):
		content = None
		extension = None
		if self.file_doc:
			parts = self.file_doc.get_extension()
			extension = parts[1]
			content = self.file_doc.get_content()
			extension = extension.lstrip(".")
		elif self.file_path:
			content, extension = self.read_file(self.file_path)

		elif self.google_sheets_url:
			content = get_csv_content_from_google_sheets(self.google_sheets_url)
			extension = "csv"

		if not content:
			frappe.throw(_("Invalid or corrupted content for import"))

		if not extension:
			extension = "csv"

		if content:
			return self.read_content(content, extension)

	def parse_data_from_template(self):
		header = None
		data = []
		for i, row in enumerate(self.raw_data):
			if all(v in INVALID_VALUES for v in row):
				# empty row
				continue

			if not header:
				header = Header(i, row, self.doctype, self.raw_data, self.column_to_field_map)
			else:
				# if row[14]!='Y':
				if not frappe.db.get_all("Imported Batches",filters={"compound_code":row[0],"mixbatchno":row[1],"mix_barcode":row[2],"material":row[4]}):
					row_obj = Row(i, row, self.doctype, header, self.import_type)
					data.append(row_obj)

		self.header = header
		self.columns = self.header.columns
		self.data = data
		if len(data) < 1:
			frappe.throw(
				_("Import template should contain a Header and atleast one row or data already is imported."),
				title=_("Template Error"),
			)

	def get_data_for_import_preview(self):
		"""Adds a serial number column as the first column"""

		columns = []
		columns += [col.as_dict() for col in self.columns]
		for col in columns:
			# only pick useful fields in docfields to minimise the payload
			if col.df:
				col.df = {
					"fieldtype": col.df.fieldtype,
					"fieldname": col.df.fieldname,
					"label": col.df.label,
					"options": col.df.options,
					"parent": col.df.parent,
					"reqd": col.df.reqd,
					"default": col.df.default,
					"read_only": col.df.read_only,
				}
	
		data = [row.as_list() for row in self.data]
		warnings = self.get_warnings()
		out = frappe._dict()
		out.data = data
		out.columns = columns
		out.warnings = warnings
		total_number_of_rows = len(out.data)
		if total_number_of_rows > MAX_ROWS_IN_PREVIEW:
			out.data = out.data[:MAX_ROWS_IN_PREVIEW]
			out.max_rows_exceeded = True
			out.max_rows_in_preview = MAX_ROWS_IN_PREVIEW
			out.total_number_of_rows = total_number_of_rows
		return out

	def get_payloads_for_import(self):
		payloads = []
		# make a copy
		data = list(self.data)
		while data:
			doc, rows, data = self.parse_next_row_for_import(data)
			payloads.append(frappe._dict(doc=doc, rows=rows))
		
		return payloads

	def parse_next_row_for_import(self, data):
		"""
		Parses rows that make up a doc. A doc maybe built from a single row or multiple rows.
		Returns the doc, rows, and data without the rows.
		"""
		doctypes = self.header.doctypes

		# first row is included by default
		first_row = data[0]
		rows = [first_row]

		# if there are child doctypes, find the subsequent rows
		if len(doctypes) > 1:
			# subsequent rows that have blank values in parent columns
			# are considered as child rows
			parent_column_indexes = self.header.get_column_indexes(self.doctype)
			parent_row_values = first_row.get_values(parent_column_indexes)

			data_without_first_row = data[1:]
			for row in data_without_first_row:
				row_values = row.get_values(parent_column_indexes)
				# if the row is blank, it's a child row doc
				if all(v in INVALID_VALUES for v in row_values):
					rows.append(row)
					continue
				# if we encounter a row which has values in parent columns,
				# then it is the next doc
				break

		parent_doc = None
		for row in rows:
			for doctype, table_df in doctypes:
				if doctype == self.doctype and not parent_doc:
					parent_doc = row.parse_doc(doctype)

				if doctype != self.doctype and table_df:
					child_doc = row.parse_doc(doctype, parent_doc, table_df)
					if child_doc is None:
						continue
					parent_doc[table_df.fieldname] = parent_doc.get(table_df.fieldname, [])
					parent_doc[table_df.fieldname].append(child_doc)

		doc = parent_doc

		return doc, rows, data[len(rows) :]

	def get_warnings(self):
		warnings = []

		# ImportFile warnings
		warnings += self.warnings

		# Column warnings
		for col in self.header.columns:
			warnings += col.warnings

		# Row warnings
		for row in self.data:
			warnings += row.warnings

		return warnings

	######

	def read_file(self, file_path):
		extn = os.path.splitext(file_path)[1][1:]

		file_content = None
		with open(file_path, mode="rb") as f:
			file_content = f.read()

		return file_content, extn

	def read_content(self, content, extension):
		error_title = _("Template Error")
		if extension not in ("csv", "xlsx", "xls"):
			frappe.throw(_("Import template should be of type .csv, .xlsx or .xls"), title=error_title)

		if extension == "csv":
			data = read_csv_content(content)
		elif extension == "xlsx":
			data = read_xlsx_file_from_attached_file(fcontent=content)
		elif extension == "xls":
			data = read_xls_file_from_attached_file(content)

		return data


class Row:
	link_values_exist_map = {}

	def __init__(self, index, row, doctype, header, import_type):
		self.index = index
		self.row_number = index + 1
		self.doctype = doctype
		self.data = row
		self.header = header
		self.import_type = import_type
		self.warnings = []

		len_row = len(self.data)
		len_columns = len(self.header.columns)
		if len_row != len_columns:
			less_than_columns = len_row < len_columns
			message = (
				"Row has less values than columns" if less_than_columns else "Row has more values than columns"
			)
			self.warnings.append(
				{
					"row": self.row_number,
					"message": message,
				}
			)

	def parse_doc(self, doctype, parent_doc=None, table_df=None):
		col_indexes = self.header.get_column_indexes(doctype, table_df)
		values = self.get_values(col_indexes)

		if all(v in INVALID_VALUES for v in values):
			# if all values are invalid, no need to parse it
			return None

		columns = self.header.get_columns(col_indexes)
		doc = self._parse_doc(doctype, columns, values, parent_doc, table_df)
		return doc

	def _parse_doc(self, doctype, columns, values, parent_doc=None, table_df=None):
		doc = frappe._dict()
		if self.import_type == INSERT:
			# new_doc returns a dict with default values set
			doc = frappe.new_doc(
				doctype,
				parent_doc=parent_doc,
				parentfield=table_df.fieldname if table_df else None,
				as_dict=True,
			)

		# remove standard fields and __islocal
		for key in frappe.model.default_fields  + ("__islocal",):
			doc.pop(key, None)

		for col, value in zip(columns, values):
			df = col.df
			if value in INVALID_VALUES:
				value = None

			if value is not None:
				value = self.validate_value(value, col)

			if value is not None:
				doc[df.fieldname] = self.parse_value(value, col)

		is_table = frappe.get_meta(doctype).istable
		is_update = self.import_type == UPDATE
		if is_table and is_update:
			# check if the row already exists
			# if yes, fetch the original doc so that it is not updated
			# if no, create a new doc
			id_field = get_id_field(doctype)
			id_value = doc.get(id_field.fieldname)
			if id_value and frappe.db.exists(doctype, id_value):
				existing_doc = frappe.get_doc(doctype, id_value)
				existing_doc.update(doc)
				doc = existing_doc
			else:
				# for table rows being inserted in update
				# create a new doc with defaults set
				new_doc = frappe.new_doc(doctype, as_dict=True)
				new_doc.update(doc)
				doc = new_doc

		return doc

	def validate_value(self, value, col):
		df = col.df
		if df.fieldtype == "Select":
			select_options = get_select_options(df)
			if select_options and value not in select_options:
				options_string = ", ".join(frappe.bold(d) for d in select_options)
				msg = _("Value must be one of {0}").format(options_string)
				self.warnings.append(
					{
						"row": self.row_number,
						"field": df_as_json(df),
						"message": msg,
					}
				)
				return

		elif df.fieldtype == "Link":
			exists = self.link_exists(value, df)
			if not exists:
				msg = _("Value {0} missing for {1}").format(frappe.bold(value), frappe.bold(df.options))
				self.warnings.append(
					{
						"row": self.row_number,
						"field": df_as_json(df),
						"message": msg,
					}
				)
				return
		elif df.fieldtype in ["Date", "Datetime"]:
			value = self.get_date(value, col)
			if isinstance(value, str):
				# value was not parsed as datetime object
				self.warnings.append(
					{
						"row": self.row_number,
						"col": col.column_number,
						"field": df_as_json(df),
						"message": _("Value {0} must in {1} format").format(
							frappe.bold(value), frappe.bold(get_user_format(col.date_format))
						),
					}
				)
				return
		elif df.fieldtype == "Duration":
			if not DURATION_PATTERN.match(value):
				self.warnings.append(
					{
						"row": self.row_number,
						"col": col.column_number,
						"field": df_as_json(df),
						"message": _("Value {0} must be in the valid duration format: d h m s").format(
							frappe.bold(value)
						),
					}
				)

		return value

	def link_exists(self, value, df):
		key = df.options + "::" + cstr(value)
		if Row.link_values_exist_map.get(key) is None:
			Row.link_values_exist_map[key] = frappe.db.exists(df.options, value)
		return Row.link_values_exist_map.get(key)

	def parse_value(self, value, col):
		df = col.df
		if isinstance(value, (datetime, date)) and df.fieldtype in ["Date", "Datetime"]:
			return value

		value = cstr(value)

		# convert boolean values to 0 or 1
		valid_check_values = ["t", "f", "true", "false", "yes", "no", "y", "n"]
		if df.fieldtype == "Check" and value.lower().strip() in valid_check_values:
			value = value.lower().strip()
			value = 1 if value in ["t", "true", "y", "yes"] else 0

		if df.fieldtype in ["Int", "Check"]:
			value = cint(value)
		elif df.fieldtype in ["Float", "Percent", "Currency"]:
			value = flt(value)
		elif df.fieldtype in ["Date", "Datetime"]:
			value = self.get_date(value, col)
		elif df.fieldtype == "Duration":
			value = duration_to_seconds(value)

		return value

	def get_date(self, value, column):
		if isinstance(value, (datetime, date)):
			return value

		date_format = column.date_format
		if date_format:
			try:
				return datetime.strptime(value, date_format)
			except ValueError:
				# ignore date values that dont match the format
				# import will break for these values later
				pass
		return value

	def get_values(self, indexes):
		return [self.data[i] for i in indexes]

	def get(self, index):
		return self.data[index]

	def as_list(self):
		return self.data


class Header(Row):
	def __init__(self, index, row, doctype, raw_data, column_to_field_map=None):
		self.index = index
		self.row_number = index + 1
		self.data = row
		self.doctype = doctype
		column_to_field_map = column_to_field_map or frappe._dict()

		self.seen = []
		self.columns = []

		for j, header in enumerate(row):
			column_values = [get_item_at_index(r, j) for r in raw_data]
			map_to_field = column_to_field_map.get(str(j))
			column = Column(j, header, self.doctype, column_values, map_to_field, self.seen)
			self.seen.append(header)
			self.columns.append(column)

		doctypes = []
		for col in self.columns:
			if not col.df:
				continue
			if col.df.parent == self.doctype:
				doctypes.append((col.df.parent, None))
			else:
				doctypes.append((col.df.parent, col.df.child_table_df))

		self.doctypes = sorted(list(set(doctypes)), key=lambda x: -1 if x[0] == self.doctype else 1)

	def get_column_indexes(self, doctype, tablefield=None):
		def is_table_field(df):
			if tablefield:
				return df.child_table_df.fieldname == tablefield.fieldname
			return True

		return [
			col.index
			for col in self.columns
			if not col.skip_import and col.df and col.df.parent == doctype and is_table_field(col.df)
		]

	def get_columns(self, indexes):
		return [self.columns[i] for i in indexes]


class Column:
	seen = []
	fields_column_map = {}

	def __init__(self, index, header, doctype, column_values, map_to_field=None, seen=None):
		if seen is None:
			seen = []
		self.index = index
		self.column_number = index + 1
		self.doctype = doctype
		self.header_title = header
		self.column_values = column_values
		self.map_to_field = map_to_field
		self.seen = seen

		self.date_format = None
		self.df = None
		self.skip_import = None
		self.warnings = []

		self.meta = frappe.get_meta(doctype)
		self.parse()
		self.validate_values()

	def parse(self):
		header_title = self.header_title
		column_number = str(self.column_number)
		skip_import = False

		if self.map_to_field and self.map_to_field != "Don't Import":
			df = get_df_for_column_header(self.doctype, self.map_to_field)
			if df:
				self.warnings.append(
					{
						"message": _("Mapping column {0} to field {1}").format(
							frappe.bold(header_title or "<i>Untitled Column</i>"), frappe.bold(df.label)
						),
						"type": "info",
					}
				)
			else:
				self.warnings.append(
					{
						"message": _("Could not map column {0} to field {1}").format(
							column_number, self.map_to_field
						),
						"type": "info",
					}
				)
		else:
			df = get_df_for_column_header(self.doctype, header_title)
			# df = df_by_labels_and_fieldnames.get(header_title)

		if not df:
			skip_import = True
		else:
			skip_import = False

		if header_title in self.seen:
			self.warnings.append(
				{
					"col": column_number,
					"message": _("Skipping Duplicate Column {0}").format(frappe.bold(header_title)),
					"type": "info",
				}
			)
			df = None
			skip_import = True
		elif self.map_to_field == "Don't Import":
			skip_import = True
			self.warnings.append(
				{
					"col": column_number,
					"message": _("Skipping column {0}").format(frappe.bold(header_title)),
					"type": "info",
				}
			)
		elif header_title and not df:
			self.warnings.append(
				{
					"col": column_number,
					"message": _("Cannot match column {0} with any field").format(frappe.bold(header_title)),
					"type": "info",
				}
			)
		elif not header_title and not df:
			self.warnings.append(
				{"col": column_number, "message": _("Skipping Untitled Column"), "type": "info"}
			)

		self.df = df
		self.skip_import = skip_import

	def guess_date_format_for_column(self):
		"""Guesses date format for a column by parsing all the values in the column,
		getting the date format and then returning the one which has the maximum frequency
		"""

		def guess_date_format(d):
			if isinstance(d, (datetime, date, time)):
				if self.df.fieldtype == "Date":
					return "%Y-%m-%d"
				if self.df.fieldtype == "Datetime":
					return "%Y-%m-%d %H:%M:%S"
				if self.df.fieldtype == "Time":
					return "%H:%M:%S"
			if isinstance(d, str):
				return frappe.utils.guess_date_format(d)

		date_formats = [guess_date_format(d) for d in self.column_values]
		date_formats = [d for d in date_formats if d]
		if not date_formats:
			return

		unique_date_formats = set(date_formats)
		max_occurred_date_format = max(unique_date_formats, key=date_formats.count)

		if len(unique_date_formats) > 1:
			# fmt: off
			message = _("The column {0} has {1} different date formats. Automatically setting {2} as the default format as it is the most common. Please change other values in this column to this format.")
			# fmt: on
			user_date_format = get_user_format(max_occurred_date_format)
			self.warnings.append(
				{
					"col": self.column_number,
					"message": message.format(
						frappe.bold(self.header_title),
						len(unique_date_formats),
						frappe.bold(user_date_format),
					),
					"type": "info",
				}
			)

		return max_occurred_date_format

	def validate_values(self):
		if not self.df:
			return

		if self.skip_import:
			return

		if self.df.fieldtype == "Link":
			# find all values that dont exist
			values = list({cstr(v) for v in self.column_values[1:] if v})
			exists = [d.name for d in frappe.db.get_all(self.df.options, filters={"name": ("in", values)})]
			not_exists = list(set(values) - set(exists))
			if not_exists:
				missing_values = ", ".join(not_exists)
				self.warnings.append(
					{
						"col": self.column_number,
						"message": (f"The following values do not exist for {self.df.options}: {missing_values}"),
						"type": "warning",
					}
				)
		elif self.df.fieldtype in ("Date", "Time", "Datetime"):
			# guess date/time format
			self.date_format = self.guess_date_format_for_column()
			if not self.date_format:
				if self.df.fieldtype == "Time":
					self.date_format = "%H:%M:%S"
					format = "HH:mm:ss"
				else:
					self.date_format = "%Y-%m-%d"
					format = "yyyy-mm-dd"

				self.warnings.append(
					{
						"col": self.column_number,
						"message": _(
							"{0} format could not be determined from the values in this column. Defaulting to {1}."
						).format(self.df.fieldtype, format),
						"type": "info",
					}
				)
		elif self.df.fieldtype == "Select":
			options = get_select_options(self.df)
			if options:
				values = {cstr(v) for v in self.column_values[1:] if v}
				invalid = values - set(options)
				if invalid:
					valid_values = ", ".join(frappe.bold(o) for o in options)
					invalid_values = ", ".join(frappe.bold(i) for i in invalid)
					self.warnings.append(
						{
							"col": self.column_number,
							"message": (
								"The following values are invalid: {}. Values must be"
								" one of {}".format(invalid_values, valid_values)
							),
						}
					)

	def as_dict(self):
		d = frappe._dict()
		d.index = self.index
		d.column_number = self.column_number
		d.doctype = self.doctype
		d.header_title = self.header_title
		d.map_to_field = self.map_to_field
		d.date_format = self.date_format
		d.df = self.df
		if hasattr(self.df, "is_child_table_field"):
			d.is_child_table_field = self.df.is_child_table_field
			d.child_table_df = self.df.child_table_df
		d.skip_import = self.skip_import
		d.warnings = self.warnings
		return d


def build_fields_dict_for_column_matching(parent_doctype):
	"""
	Build a dict with various keys to match with column headers and value as docfield
	The keys can be label or fieldname
	{
			'Customer': df1,
			'customer': df1,
			'Due Date': df2,
			'due_date': df2,
			'Item Code (Sales Invoice Item)': df3,
			'Sales Invoice Item:item_code': df3,
	}
	"""

	def get_standard_fields(doctype):
		meta = frappe.get_meta(doctype)
		if meta.istable:
			standard_fields = [
				{"label": "Parent", "fieldname": "parent"},
				{"label": "Parent Type", "fieldname": "parenttype"},
				{"label": "Parent Field", "fieldname": "parentfield"},
				{"label": "Row Index", "fieldname": "idx"},
			]
		else:
			standard_fields = [
				{"label": "Owner", "fieldname": "owner"},
				{"label": "Document Status", "fieldname": "docstatus", "fieldtype": "Int"},
			]

		out = []
		for df in standard_fields:
			df = frappe._dict(df)
			df.parent = doctype
			out.append(df)
		return out

	parent_meta = frappe.get_meta(parent_doctype)
	out = {}

	# doctypes and fieldname if it is a child doctype
	doctypes = [(parent_doctype, None)] + [(df.options, df) for df in parent_meta.get_table_fields()]

	for doctype, table_df in doctypes:
		translated_table_label = _(table_df.label) if table_df else None

		# name field
		name_df = frappe._dict(
			{
				"fieldtype": "Data",
				"fieldname": "name",
				"label": "ID",
				"reqd": 1,  # self.import_type == UPDATE,
				"parent": doctype,
			}
		)

		if doctype == parent_doctype:
			name_headers = (
				"name",  # fieldname
				"ID",  # label
				_("ID"),  # translated label
			)
		else:
			name_headers = (
				f"{table_df.fieldname}.name",  # fieldname
				f"ID ({table_df.label})",  # label
				"{} ({})".format(_("ID"), translated_table_label),  # translated label
			)

			name_df.is_child_table_field = True
			name_df.child_table_df = table_df

		for header in name_headers:
			out[header] = name_df

		fields = get_standard_fields(doctype) + frappe.get_meta(doctype).fields
		for df in fields:
			fieldtype = df.fieldtype or "Data"
			if fieldtype in no_value_fields:
				continue

			label = (df.label or "").strip()
			translated_label = _(label)
			parent = df.parent or parent_doctype

			if parent_doctype == doctype:
				# for parent doctypes keys will be
				# Label, fieldname, Label (fieldname)

				for header in (label, translated_label):
					# if Label is already set, don't set it again
					# in case of duplicate column headers
					if header not in out:
						out[header] = df

				for header in (
					df.fieldname,
					f"{label} ({df.fieldname})",
					f"{translated_label} ({df.fieldname})",
				):
					out[header] = df

			else:
				# for child doctypes keys will be
				# Label (Table Field Label)
				# table_field.fieldname

				# create a new df object to avoid mutation problems
				if isinstance(df, dict):
					new_df = frappe._dict(df.copy())
				else:
					new_df = df.as_dict()

				new_df.is_child_table_field = True
				new_df.child_table_df = table_df

				for header in (
					# fieldname
					f"{table_df.fieldname}.{df.fieldname}",
					# label
					f"{label} ({table_df.label})",
					# translated label
					f"{translated_label} ({translated_table_label})",
				):
					out[header] = new_df

	# if autoname is based on field
	# add an entry for "ID (Autoname Field)"
	autoname_field = get_autoname_field(parent_doctype)
	if autoname_field:
		for header in (
			f"ID ({autoname_field.label})",  # label
			"{} ({})".format(_("ID"), _(autoname_field.label)),  # translated label
			# ID field should also map to the autoname field
			"ID",
			_("ID"),
			"name",
		):
			out[header] = autoname_field

	return out


def get_df_for_column_header(doctype, header):
	def build_fields_dict_for_doctype():
		return build_fields_dict_for_column_matching(doctype)

	df_by_labels_and_fieldname = frappe.cache().hget(
		"data_import_column_header_map", doctype, generator=build_fields_dict_for_doctype
	)
	return df_by_labels_and_fieldname.get(header)


# utilities


def get_id_field(doctype):
	autoname_field = get_autoname_field(doctype)
	if autoname_field:
		return autoname_field
	return frappe._dict({"label": "ID", "fieldname": "name", "fieldtype": "Data"})


def get_autoname_field(doctype):
	meta = frappe.get_meta(doctype)
	if meta.autoname and meta.autoname.startswith("field:"):
		fieldname = meta.autoname[len("field:") :]
		return meta.get_field(fieldname)


def get_item_at_index(_list, i, default=None):
	try:
		a = _list[i]
	except IndexError:
		a = default
	return a


def get_user_format(date_format):
	return (
		date_format.replace("%Y", "yyyy").replace("%y", "yy").replace("%m", "mm").replace("%d", "dd")
	)


def df_as_json(df):
	return {
		"fieldname": df.fieldname,
		"fieldtype": df.fieldtype,
		"label": df.label,
		"options": df.options,
		"parent": df.parent,
		"default": df.default,
	}


def get_select_options(df):
	return [d for d in (df.options or "").split("\n") if d]


def create_import_log(data_import, log_index, log_details):
	frappe.get_doc(
		{
			"doctype": "Imported Batch Log",
			"log_index": log_index,
			"success": log_details.get("success"),
			"data_import": data_import,
			"row_indexes": json.dumps(log_details.get("row_indexes")),
			"docname": log_details.get("docname"),
			"messages": json.dumps(log_details.get("messages", "[]")),
			"exception": log_details.get("exception"),
		}
	).db_insert()
	frappe.db.commit()
def validate_tqty(batch_entry_id):
	m_items = frappe.db.sql(""" SELECT  IB.material,SUM(IB.actual_weight) as qty FROM `tabImported Batch Log` L INNER JOIN  `tabImported Batches` IB ON L.docname = IB.name 
								  WHERE L.data_import=%(b_id)s AND success=1  GROUP BY IB.material """,{"b_id":batch_entry_id},as_dict=1)
	spp_settings = frappe.get_single("SPP Settings")
	for x in m_items:
		t_qty_list = frappe.db.sql(""" SELECT SUM(qty) as total_qty FROM `tabItem Batch Stock Balance` SB 
										INNER JOIN `tabBatch` B ON SB.batch_no = B.name
										WHERE SB.item_code = %(item_code)s AND B.expiry_date >= CURDATE() AND SB.warehouse=%(warehouse)s"""
										,{"item_code":x.material,"warehouse":spp_settings.source_warehouse},as_dict=1)
		if t_qty_list:
			if t_qty_list[0].total_qty:
				if not t_qty_list[0].total_qty>=x.qty:
					rollback_transaction(batch_entry_id)
					frappe.db.set_value("Batch ERP Entry",batch_entry_id,"status","Error")
					frappe.db.commit()
					frappe.throw("The total available quantity of <b>"+x.material+"</b> in warehouse <b>"+spp_settings.source_warehouse+"</b> is <b>"+str(t_qty_list[0].total_qty)+"</b>,but total required qty is <b>"+str(x.qty)+".</b>")
					return False
			else:
				rollback_transaction(batch_entry_id)
				frappe.db.set_value("Batch ERP Entry",batch_entry_id,"status","Error")
				frappe.db.commit()
				frappe.throw("The total available quantity of <b>"+x.material+"</b> in warehouse <b>"+spp_settings.source_warehouse+"</b> is <b>0</b>,but total required qty is <b>"+str(x.qty)+".</b>")
				return False
		else:
			rollback_transaction(batch_entry_id)
			frappe.db.set_value("Batch ERP Entry",batch_entry_id,"status","Error")
			frappe.db.commit()
			frappe.throw("The total available quantity of <b>"+x.material+"</b> in warehouse <b>"+spp_settings.source_warehouse+"</b> is <b>0</b>,but total required qty is <b>"+str(x.qty)+".</b>")
			return False
	return True
def create_wos(batch_entry_id):
	from operator import itemgetter
	logs = frappe.db.get_all("Imported Batch Log",filters={"data_import":batch_entry_id,"success":1},fields=['docname'])
	valid_stock = validate_tqty(batch_entry_id)
	if logs and valid_stock:
		items = frappe.db.sql(""" SELECT  IB.compound_code FROM `tabImported Batch Log` L INNER JOIN  `tabImported Batches` IB ON L.docname = IB.name 
								  WHERE L.data_import=%(b_id)s AND success=1 group by IB.compound_code""",{"b_id":batch_entry_id},as_dict=1
										)
		imported_batches = frappe.db.sql(""" SELECT IB.* FROM `tabImported Batch Log` L INNER JOIN 
											 `tabImported Batches` IB ON L.docname = IB.name 
											 WHERE L.data_import=%(b_id)s AND success=1""",{"b_id":batch_entry_id},as_dict=1
										)
		if items:
			spp_settings = frappe.get_single("SPP Settings")
			for item in items:
				if frappe.db.get_all("Item",filters={"name":item.get("compound_code")}):
					bom = frappe.db.get_value("Item",item.compound_code,"default_bom")
					if bom:
						bom_items = list(filter(lambda x: x.compound_code == item.compound_code, imported_batches))
						actual_weight = sum(flt(e_item.actual_weight) for e_item in imported_batches if e_item.compound_code == item.compound_code)
						import time
						wo = frappe.new_doc("Work Order")
						wo.naming_series = "MFG-WO-.YYYY.-"
						wo.company = "SPP"
						wo.fg_warehouse = spp_settings.target_warehouse
						wo.use_multi_level_bom = 0
						wo.skip_transfer = 1
						wo.source_warehouse = spp_settings.source_warehouse
						wo.wip_warehouse = spp_settings.wip_warehouse
						wo.transfer_material_against = "Work Order"
						wo.bom_no = bom
						wo.append("operations",{
							"operation":"Batch",
							"bom":bom,
							"workstation":spp_settings.workstation,
							"time_in_mins":len(bom_items)*10,
							})
						wo.referenceid = round(time.time() * 1000)
						wo.production_item = item.get("compound_code")
						wo.qty = actual_weight
						# date_obj = bom_items[0].date.split(' ')[0].split('-')
						wo.planned_start_date = getdate(get_aggr_date(item.get("compound_code"),bom_items[0].mixbatchno))
						wo.docstatus = 1
						try:
							wo.save(ignore_permissions=True)
							update_job_cards(wo.name,actual_weight,spp_settings.employee,spp_settings)
							se = make_stock_entry(batch_entry_id,spp_settings,wo.name,item.get("compound_code"),"Manufacture",)
							if se.get("status")=="Success":
								job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo.name})
								if job_cards:
									frappe.db.sql(""" UPDATE  `tabImported Batches` SET batch_complete='Y',wo=%(wo)s , sc_transfer=%(se_id)s,jc=%(jc_id)s WHERE compound_code=%(compound_code)s""",{"jc_id":job_cards[0].name,"wo":wo.name,"se_id":se.get("st_entry").get("name"),"compound_code":item.get("compound_code")})
							else:
								return False
						except Exception as e:
							rollback_transaction(batch_entry_id)
							frappe.log_error(message=frappe.get_traceback(),title="Data import failed")
							return False

def get_aggr_date(compound,mixbatchno):
	c_date = mixbatchno.split(compound+"_")[1].split('X')
	d_split = c_date[0]
	c_year = d_split[:2]
	c_month_code = d_split.split(c_year)[1][:1]
	c_month = getmonth(c_month_code)
	c_day = d_split.split(c_year+c_month_code)[1]
	full_date = "20"+c_year+"-"+c_month+"-"+c_day
	return full_date

def getmonth(code):
	if code == "A":
		return "01"
	if code == "B":
		return "02"
	if code == "C":
		return "03"
	if code == "D":
		return "04"
	if code == "E":
		return "05"
	if code == "F":
		return "06"
	if code == "G":
		return "07"
	if code == "H":
		return "08"
	if code == "I":
		return "09"
	if code == "J":
		return "10"
	if code == "K":
		return "11"
	if code == "L":
		return "12"

def update_job_cards(wo,actual_weight,employee,spp_settings):
	job_cards = frappe.db.get_all("Job Card",filters={"work_order":wo})
	for job_card in job_cards:
		jc = frappe.get_doc("Job Card",job_card.name)
		for time_log in jc.time_logs:
			time_log.completed_qty =flt(actual_weight,3)
			time_log.time_in_mins = 1
		jc.total_completed_qty =flt(actual_weight,3)
		jc.for_quantity =flt(actual_weight,3)
		jc.save(ignore_permissions=True)
		jc_doc = frappe.get_doc("Job Card",job_card.name)
		# frappe.log_error(jc_doc.for_quantity,"for_quantity")
		# frappe.log_error(jc_doc.total_completed_qty,"total_completed_qty")
		jc_doc.docstatus = 1
		jc_doc.save(ignore_permissions=True)

		

def make_stock_entry(batch_entry_id,spp_settings,work_order_id,compound_code, purpose, qty=None):
	stock_entry = frappe.new_doc("Stock Entry")
	try:
		m_res_entries = []
		work_order = frappe.get_doc("Work Order", work_order_id)
		if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
			wip_warehouse = work_order.wip_warehouse
		else:
			wip_warehouse = None

		
		stock_entry.purpose = purpose
		stock_entry.work_order = work_order_id
		stock_entry.company = work_order.company
		stock_entry.from_bom = 1
		stock_entry.bom_no = work_order.bom_no
		stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
		stock_entry.stock_entry_type = "Manufacture"
		stock_entry.posting_date = work_order.planned_start_date
		# accept 0 qty as well
		stock_entry.fg_completed_qty = work_order.qty
		if work_order.bom_no:
			stock_entry.inspection_required = frappe.db.get_value(
				"BOM", work_order.bom_no, "inspection_required"
			)
		stock_entry.from_warehouse = work_order.source_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		for x in work_order.required_items:
			t_qty_list = frappe.db.sql(""" SELECT SUM(qty) as total_qty FROM `tabItem Batch Stock Balance` SB 
													INNER JOIN `tabBatch` B ON SB.batch_no = B.name
													WHERE SB.item_code = %(item_code)s AND B.expiry_date >= CURDATE() AND SB.warehouse=%(warehouse)s"""
													,{"item_code":x.item_code,"warehouse":spp_settings.source_warehouse},as_dict=1)
			if t_qty_list:
				if t_qty_list[0].total_qty:
					if t_qty_list[0].total_qty>=x.required_qty:
						batch_wise_stock = frappe.db.sql(""" SELECT SB.batch_no,SB.qty  FROM `tabItem Batch Stock Balance` SB 
														INNER JOIN `tabBatch` B ON SB.batch_no = B.name
														WHERE SB.item_code = %(item_code)s AND B.expiry_date >= CURDATE() AND SB.warehouse=%(warehouse)s
														ORDER BY B.creation """
														,{"item_code":x.item_code,"warehouse":spp_settings.source_warehouse},as_dict=1)
						s_qty = 0
						remaining_qty = x.required_qty
						batches_list = []
						for batch in batch_wise_stock:
							res_qtys = frappe.db.sql(""" SELECT sum(qty) as qty FROM `tabMaterial Reserved Stock` WHERE item_code=%(item_code)s AND batch_no=%(batch_no)s AND is_consumed=0 """,{"batch_no":batch.batch_no,"item_code":x.item_code},as_dict=1)
							if res_qtys:
								if res_qtys[0].qty:
									batch.qty = batch.qty - res_qtys[0].qty
							if batch.qty>0:
								if batch.qty > remaining_qty:
									s_qty = remaining_qty
								else:
									s_qty = batch.qty
								remaining_qty = remaining_qty - s_qty
								if round(s_qty,3)>0:
									stock_entry.append("items",{
										"item_code":x.item_code,
										"s_warehouse":spp_settings.source_warehouse,
										"stock_uom": "Kg",
										"to_uom": "Kg",
										"batch_no":batch.batch_no,
										"uom": "Kg",
										"is_finished_item":0,
										"transfer_qty":s_qty,
										"qty":s_qty,
									})
									m_res_entries.append({"item_code":x.item_code,"batch_no":batch.batch_no,"qty":s_qty})
									batches_list.append(batch.batch_no)
									if not remaining_qty > 0:
										break
					else:
						rollback_transaction(batch_entry_id)
						frappe.throw("The available quantity of "+x.item_code+" in the warehouse <b>"+work_order.source_warehouse+"</b> is <b>"+str(t_qty_list[0].total_qty)+"</b>,but required qty is <b>"+str(x.required_qty)+".</b>")
					
						
				else:
					rollback_transaction(batch_entry_id)
					frappe.throw("The available quantity of "+x.item_code+" in the warehouse <b>"+work_order.source_warehouse+"</b> is <b> 0 </b>,but required qty is <b>"+str(x.required_qty)+".</b>")
					

			else:
				rollback_transaction(batch_entry_id)
				frappe.throw("The available quantity of "+x.item_code+" in warehouse </b>"+work_order.source_warehouse+"</b> is <b>0</b>,but required qty is <b>"+str(x.required_qty)+".</b>")
		items = frappe.db.sql(""" SELECT  IB.compound_code,IB.mixbatchno,IB.mix_barcode FROM `tabImported Batch Log` L INNER JOIN  `tabImported Batches` IB ON L.docname = IB.name 
									  WHERE L.data_import=%(b_id)s AND IB.compound_code=%(compound_code)s AND success=1 group by IB.compound_code,IB.mixbatchno,IB.mix_barcode""",{"b_id":batch_entry_id,"compound_code":compound_code},as_dict=1
											)
		imported_batches = frappe.db.sql(""" SELECT IB.* FROM `tabImported Batch Log` L INNER JOIN 
												 `tabImported Batches` IB ON L.docname = IB.name 
												 WHERE L.data_import=%(b_id)s AND IB.compound_code=%(compound_code)s AND  success=1 """,{"b_id":batch_entry_id,"compound_code":compound_code},as_dict=1
											)
		for x in items:
			a_qty = sum(flt(e_item.actual_weight) for e_item in imported_batches if e_item.compound_code == x.compound_code and e_item.mixbatchno == x.mixbatchno and e_item.mix_barcode == x.mix_barcode)
			s_nos = x.mixbatchno.split(x.compound_code)
			spp_bno = s_nos[1].replace("_22","")
			stock_entry.append("items",{
				"item_code":x.compound_code,
				"t_warehouse":spp_settings.target_warehouse,
				"stock_uom": "Kg",
				"to_uom": "Kg",
				"uom": "Kg",
				"is_finished_item":1,
				"transfer_qty":a_qty,
				"qty":a_qty,
				"spp_batch_number":spp_bno,
				"mix_barcode":x.mix_barcode,
				})
		if spp_settings.auto_submit_stock_entries:
				st_entry.docstatus=1
		
		stock_entry.insert()
		data_import = frappe.get_doc("Batch ERP Entry", batch_entry_id)
		data_import.db_set("status", "Success")
		for res_entry in m_res_entries:
			frappe.get_doc({
				"doctype":"Material Reserved Stock",
				"item_code":res_entry.get("item_code"),
				"batch_no":res_entry.get("batch_no"),
				"qty":res_entry.get("qty"),
				"stock_entry_reference":stock_entry.name,
				"is_consumed":0
				}).insert()
		return {"status":"Success","st_entry":stock_entry}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(),title="Data import failed")
		rollback_transaction(batch_entry_id)
		return {"status":"Failed"}

def rollback_transaction(batch_entry_id):
	frappe.db.rollback()
	frappe.db.sql(""" DELETE FROM `tabImported Batches` WHERE name in(SELECT docname FROM `tabImported Batch Log` WHERE data_import =%(batch_entry_id)s ) """,{"batch_entry_id":batch_entry_id})
	frappe.db.sql(""" DELETE FROM `tabImported Batch Log` WHERE data_import =%(batch_entry_id)s """,{"batch_entry_id":batch_entry_id})
	frappe.db.commit()
	data_import = frappe.get_doc("Batch ERP Entry", batch_entry_id)
	data_import.db_set("status", "Error")
	
def is_negative_stock_allowed(item_code):
	if cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock", cache=True)):
		return True
	return False
def sort_nos(no):
	return no[0].get("item_code")
def validate_bom(payloads,batch_size):
	batch_items = []
	for batch_index, batched_payloads in enumerate(frappe.utils.create_batch(payloads, batch_size)):
		for i, payload in enumerate(batched_payloads):
			d = payload.doc
			batch_items.append({"compound_code":d.compound_code,"material":d.material,"actual_qty":d.actual_weight,'mixbatchno':d.mixbatchno})
	compounds = []
	for x in batch_items:
		if not list(filter(lambda i: i.get("compound_code") == x.get("compound_code") and i.get("mixbatchno") == x.get("mixbatchno"), compounds)):
			compounds.append({"compound_code":x.get("compound_code"),"mixbatchno":x.get("mixbatchno")})
	for item in compounds:
		item["materials"] = list(filter(lambda x: x.get("compound_code") == item.get("compound_code") and x.get("mixbatchno") == item.get("mixbatchno"), batch_items))
		materials = []
		for mt in item["materials"]:
			materials.append({"item_code":mt.get("material")})
		item["material_list"] = sorted(materials, key=lambda k: k['item_code'])
	for compound in compounds:
		# bom = frappe.db.get_all("BOM",filters={"is_active":1,"item":compound.get("compound_code")},order_by="is_default DESC",limit_page_length=1)
		bom = frappe.db.get_all("BOM", filters={"is_active":1,"item":compound.get("compound_code")})
		if bom:
			b_materials = frappe.db.get_all("BOM Item",filters={"parent":bom[0].name},fields=['item_code'],order_by="item_code")
			c_materials = compound.get("material_list")
			if not b_materials == c_materials:
				return {"status":False,"message":"BOM items not matched with batched items of batch <b>"+compound.get("mixbatchno")+"</b> for the Compound <b>"+compound.get("compound_code")+"</b>"}
		else:
			return {"status":False,"message":"BOM not found for the item <b> "+compound.get("compound_code")+"</b>"}
	return {"status":True}
def check_items_stock(payloads,batch_size,target_warehouse):
	is_allow = 1
	from erpnext.stock.stock_ledger import get_previous_sle
	from erpnext.stock.stock_ledger import NegativeStockError
	from datetime import datetime
	for batch_index, batched_payloads in enumerate(frappe.utils.create_batch(payloads, batch_size)):
		for i, payload in enumerate(batched_payloads):
			d = payload.doc
			d.s_warehouse = target_warehouse
			d.item_code = d.material
			allow_negative_stock = is_negative_stock_allowed(item_code= d.material)
			cur_date = getdate()
			now = datetime.strptime(frappe.utils.now(), '%Y-%m-%d %H:%M:%S.%f')
			cur_time =  now.strftime('%H:%M:%S')
			previous_sle = get_previous_sle(
				{
					"item_code": d.material,
					"warehouse": target_warehouse,
					"posting_date": cur_date,
					"posting_time": cur_time,
				}
			)
			d.s_warehouse = target_warehouse
			# get actual stock at source warehouse
			d.actual_qty = previous_sle.get("qty_after_transaction") or 0

			# validate qty during submit
			if (
				not allow_negative_stock
				and flt(d.actual_qty)
				< flt(d.actual_weight)
			):
				frappe.throw(
					_(
						"Row {0}: Quantity not available for {4} in warehouse {1} at posting time of the entry ({2} {3})"
					).format(
						d.idx,
						frappe.bold(d.s_warehouse),
						formatdate(cur_date),
						format_time(cur_time),
						frappe.bold(d.item_code),
					)
					+ "<br><br>"
					+ _("Available quantity is {0}, you need {1}").format(
						frappe.bold(flt(d.actual_qty)), frappe.bold(d.actual_weight)
					),
					NegativeStockError,
					title=_("Insufficient Stock"),
				)
				is_allow = 0
				return is_allow
	return is_allow