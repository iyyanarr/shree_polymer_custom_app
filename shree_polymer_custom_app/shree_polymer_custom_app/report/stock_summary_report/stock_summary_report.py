# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt



from operator import itemgetter
from typing import Any, Dict, List, Optional, TypedDict

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Coalesce, CombineDatetime
from frappe.utils import add_days, cint, date_diff, flt, getdate
from frappe.utils.nestedset import get_descendants_of

import erpnext
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.utils import add_additional_uom_columns


class StockBalanceFilter(TypedDict):
	company: Optional[str]
	from_date: str
	to_date: str
	item_group: Optional[str]
	item: Optional[str]
	warehouse: Optional[str]
	warehouse_type: Optional[str]
	include_uom: Optional[str]  # include extra info in converted UOM
	show_stock_ageing_data: bool
	show_variant_attributes: bool


SLEntry = Dict[str, Any]


def execute(filters: Optional[StockBalanceFilter] = None):
	return StockBalanceReport(filters).run()


class StockBalanceReport(object):
	def __init__(self, filters: Optional[StockBalanceFilter]) -> None:
		# Customize
		filters['company'] = "SPP"
		# filters['from_date'] = filters.get('posting_from_date')
		filters['from_date'] = filters.get('posting_to_date')
		filters['to_date']  = filters.get('posting_to_date')
		## End
		self.filters = filters
		self.from_date = getdate(filters.get("from_date"))
		self.to_date = getdate(filters.get("to_date"))

		self.start_from = None
		self.data = []
		self.columns = []
		self.sle_entries: List[SLEntry] = []
		self.set_company_currency()

	def set_company_currency(self) -> None:
		if self.filters.get("company"):
			self.company_currency = erpnext.get_company_currency(self.filters.get("company"))
		else:
			self.company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

	def run(self):
		#  Customize
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.exclude_warehouses:
			frappe.throw("Please select exclude warehouses in <b>SPP Settings</b>..!")
		# end
		self.float_precision = cint(frappe.db.get_default("float_precision")) or 3

		self.inventory_dimensions = self.get_inventory_dimension_fields()
		self.prepare_opening_data_from_closing_balance()
		self.prepare_stock_ledger_entries()
		self.prepare_new_data()

		if not self.columns:
			self.columns = self.get_columns()

		self.add_additional_uom_columns()

		return self.columns, self.data

	def prepare_opening_data_from_closing_balance(self) -> None:
		self.opening_data = frappe._dict({})

		closing_balance = self.get_closing_balance()
		if not closing_balance:
			return

		self.start_from = add_days(closing_balance[0].to_date, 1)
		res = frappe.get_doc("Closing Stock Balance", closing_balance[0].name).get_prepared_data()

		for entry in res.data:
			entry = frappe._dict(entry)

			group_by_key = self.get_group_by_key(entry)
			if group_by_key not in self.opening_data:
				self.opening_data.setdefault(group_by_key, entry)

	def prepare_new_data(self):
		if not self.sle_entries:
			return

		if self.filters.get("show_stock_ageing_data"):
			self.filters["show_warehouse_wise_stock"] = True
			item_wise_fifo_queue = FIFOSlots(self.filters, self.sle_entries).generate()

		_func = itemgetter(1)
		self.item_warehouse_map = self.get_item_warehouse_map()

		variant_values = {}
		if self.filters.get("show_variant_attributes"):
			variant_values = self.get_variant_values_for()

		for key, report_data in self.item_warehouse_map.items():
			if variant_data := variant_values.get(report_data.item_code):
				report_data.update(variant_data)

			if self.filters.get("show_stock_ageing_data"):
				opening_fifo_queue = self.get_opening_fifo_queue(report_data) or []

				fifo_queue = []
				if fifo_queue := item_wise_fifo_queue.get((report_data.item_code, report_data.warehouse)):
					fifo_queue = fifo_queue.get("fifo_queue")

				if fifo_queue:
					opening_fifo_queue.extend(fifo_queue)

				stock_ageing_data = {"average_age": 0, "earliest_age": 0, "latest_age": 0}
				if opening_fifo_queue:
					fifo_queue = sorted(filter(_func, opening_fifo_queue), key=_func)
					if not fifo_queue:
						continue

					to_date = self.to_date
					stock_ageing_data["average_age"] = get_average_age(fifo_queue, to_date)
					stock_ageing_data["earliest_age"] = date_diff(to_date, fifo_queue[0][1])
					stock_ageing_data["latest_age"] = date_diff(to_date, fifo_queue[-1][1])
					stock_ageing_data["fifo_queue"] = fifo_queue

				report_data.update(stock_ageing_data)

			self.data.append(report_data)

	def get_item_warehouse_map(self):
		item_warehouse_map = {}
		self.opening_vouchers = self.get_opening_vouchers()
		for entry in self.sle_entries:
			group_by_key = self.get_group_by_key(entry)
			if group_by_key not in item_warehouse_map:
				self.initialize_data(item_warehouse_map, group_by_key, entry)

			self.prepare_item_warehouse_map(item_warehouse_map, entry, group_by_key)

			if self.opening_data.get(group_by_key):
				del self.opening_data[group_by_key]

		for group_by_key, entry in self.opening_data.items():
			if group_by_key not in item_warehouse_map:
				self.initialize_data(item_warehouse_map, group_by_key, entry)

		item_warehouse_map = filter_items_with_no_transactions(
			item_warehouse_map, self.float_precision, self.inventory_dimensions
		)

		return item_warehouse_map

	def prepare_item_warehouse_map(self, item_warehouse_map, entry, group_by_key):
		qty_dict = item_warehouse_map[group_by_key]
		for field in self.inventory_dimensions:
			qty_dict[field] = entry.get(field)

		if entry.voucher_type == "Stock Reconciliation" and (not entry.batch_no or entry.serial_no):
			qty_diff = flt(entry.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(entry.actual_qty)

		value_diff = flt(entry.stock_value_difference)

		if entry.posting_date < self.from_date or entry.voucher_no in self.opening_vouchers.get(
			entry.voucher_type, []
		):
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif entry.posting_date >= self.from_date and entry.posting_date <= self.to_date:

			if flt(qty_diff, self.float_precision) >= 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = entry.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	def initialize_data(self, item_warehouse_map, group_by_key, entry):
		opening_data = self.opening_data.get(group_by_key, {})

		item_warehouse_map[group_by_key] = frappe._dict(
			{
				"item_code": entry.item_code,
				"warehouse": entry.warehouse,
				"item_group": entry.item_group,
				"company": entry.company,
				"currency": self.company_currency,
				"stock_uom": entry.stock_uom,
				"item_name": entry.item_name,
				"opening_qty": opening_data.get("bal_qty") or 0.0,
				"opening_val": opening_data.get("bal_val") or 0.0,
				"opening_fifo_queue": opening_data.get("fifo_queue") or [],
				"in_qty": 0.0,
				"in_val": 0.0,
				"out_qty": 0.0,
				"out_val": 0.0,
				"bal_qty": opening_data.get("bal_qty") or 0.0,
				"bal_val": opening_data.get("bal_val") or 0.0,
				"val_rate": 0.0,
			}
		)
		
	def get_group_by_key(self, row) -> tuple:
		group_by_key = [row.company, row.item_code, row.warehouse]

		for fieldname in self.inventory_dimensions:
			if self.filters.get(fieldname):
				group_by_key.append(row.get(fieldname))

		return tuple(group_by_key)

	def get_closing_balance(self) -> List[Dict[str, Any]]:
		if self.filters.get("ignore_closing_balance"):
			return []

		table = frappe.qb.DocType("Closing Stock Balance")

		query = (
			frappe.qb.from_(table)
			.select(table.name, table.to_date)
			.where(
				(table.docstatus == 1)
				& (table.company == self.filters.company)
				& ((table.to_date <= self.from_date))
			)
			.orderby(table.to_date, order=Order.desc)
			.limit(1)
		)

		for fieldname in ["warehouse", "item_code", "item_group", "warehouse_type"]:
			if self.filters.get(fieldname):
				query = query.where(table[fieldname] == self.filters.get(fieldname))

		return query.run(as_dict=True)

	def prepare_stock_ledger_entries(self):
		#customize
		spp_settings = frappe.get_single("SPP Settings")
		if not spp_settings.rejection_warehouse:
			frappe.throw(f'Rejection Warehouse not mapped in <p>SPP Settings</p>')
		if not spp_settings.pdir_visual_t__warehouse:
			frappe.throw(f'PDIR & Final Visual Rejection Warehouse not mapped in <p>SPP Settings</p>')
		if not spp_settings.scrap_warehouse:
			frappe.throw(f'Scrap Warehouse not mapped in <p>SPP Settings</p>')
		#end
		sle = frappe.qb.DocType("Stock Ledger Entry")
		item_table = frappe.qb.DocType("Item")
		query = (
			frappe.qb.from_(sle)
			.inner_join(item_table)
			.on(sle.item_code == item_table.name)
			.select(
				sle.item_code,
				sle.warehouse,
				sle.posting_date,
				sle.actual_qty,
				sle.valuation_rate,
				sle.company,
				sle.voucher_type,
				sle.qty_after_transaction,
				sle.stock_value_difference,
				sle.item_code.as_("name"),
				sle.voucher_no,
				sle.stock_value,
				sle.batch_no,
				sle.serial_no,
				item_table.item_group,
				item_table.stock_uom,
				item_table.item_name,
			)
			.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
			.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
			.orderby(sle.creation)
			.orderby(sle.actual_qty)
		)

		#customize
		spp_settings = frappe.get_single("SPP Settings")
		for k in spp_settings.exclude_warehouses:
			query = query.where(sle.warehouse != k.warhouse)	  				
		#end

		query = self.apply_inventory_dimensions_filters(query, sle)
		query = self.apply_warehouse_filters(query, sle)
		query = self.apply_items_filters(query, item_table)
		query = self.apply_date_filters(query, sle)

		if self.filters.get("company"):
			query = query.where(sle.company == self.filters.get("company"))
		self.sle_entries = query.run(as_dict=True)

	def apply_inventory_dimensions_filters(self, query, sle) -> str:
		inventory_dimension_fields = self.get_inventory_dimension_fields()
		if inventory_dimension_fields:
			for fieldname in inventory_dimension_fields:
				query = query.select(fieldname)
				if self.filters.get(fieldname):
					query = query.where(sle[fieldname].isin(self.filters.get(fieldname)))

		return query

	def apply_warehouse_filters(self, query, sle) -> str:
		warehouse_table = frappe.qb.DocType("Warehouse")

		if self.filters.get("warehouse"):
			query = apply_warehouse_filter(query, sle, self.filters)
		elif warehouse_type := self.filters.get("warehouse_type"):
			query = (
				query.join(warehouse_table)
				.on(warehouse_table.name == sle.warehouse)
				.where(warehouse_table.warehouse_type == warehouse_type)
			)

		return query

	def apply_items_filters(self, query, item_table) -> str:
		if item_group := self.filters.get("item_group"):
			children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
			query = query.where(item_table.item_group.isin(children + [item_group]))

		for field in ["item_code", "brand"]:
			if not self.filters.get(field):
				continue

			query = query.where(item_table[field] == self.filters.get(field))

		return query

	def apply_date_filters(self, query, sle) -> str:
		if not self.filters.ignore_closing_balance and self.start_from:
			query = query.where(sle.posting_date >= self.start_from)

		if self.to_date:
			query = query.where(sle.posting_date <= self.to_date)

		return query

	def get_columns(self):
		columns = [
			{
				"label": _("Item"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 200,
			},
			{
				"label": _("Stage"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 130,
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 400,
			},
		]

		for dimension in get_inventory_dimensions():
			columns.append(
				{
					"label": _(dimension.doctype),
					"fieldname": dimension.fieldname,
					"fieldtype": "Link",
					"options": dimension.doctype,
					"width": 110,
				}
			)

		columns.extend(
			[
				{
					"label": _("Balance Qty"),
					"fieldname": "bal_qty",
					"fieldtype": "Float",
					"width": 130,
					"convertible": "qty",
				},
				{
					"label": _("Stock UOM"),
					"fieldname": "stock_uom",
					"fieldtype": "Link",
					"options": "UOM",
					"width": 130,
				},
			]
		)

		if self.filters.get("show_stock_ageing_data"):
			columns += [
				{"label": _("Average Age"), "fieldname": "average_age", "width": 100},
				{"label": _("Earliest Age"), "fieldname": "earliest_age", "width": 100},
				{"label": _("Latest Age"), "fieldname": "latest_age", "width": 100},
			]

		if self.filters.get("show_variant_attributes"):
			columns += [
				{"label": att_name, "fieldname": att_name, "width": 100}
				for att_name in get_variants_attributes()
			]

		return columns

	def add_additional_uom_columns(self):
		if not self.filters.get("include_uom"):
			return

		conversion_factors = self.get_itemwise_conversion_factor()
		add_additional_uom_columns(self.columns, self.data, self.filters.include_uom, conversion_factors)

	def get_itemwise_conversion_factor(self):
		items = []
		if self.filters.item_code or self.filters.item_group:
			items = [d.item_code for d in self.data]

		table = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			frappe.qb.from_(table)
			.select(
				table.conversion_factor,
				table.parent,
			)
			.where((table.parenttype == "Item") & (table.uom == self.filters.include_uom))
		)

		if items:
			query = query.where(table.parent.isin(items))

		result = query.run(as_dict=1)
		if not result:
			return {}

		return {d.parent: d.conversion_factor for d in result}

	def get_variant_values_for(self):
		"""Returns variant values for items."""
		attribute_map = {}
		items = []
		if self.filters.item_code or self.filters.item_group:
			items = [d.item_code for d in self.data]

		filters = {}
		if items:
			filters = {"parent": ("in", items)}

		attribute_info = frappe.get_all(
			"Item Variant Attribute",
			fields=["parent", "attribute", "attribute_value"],
			filters=filters,
		)

		for attr in attribute_info:
			attribute_map.setdefault(attr["parent"], {})
			attribute_map[attr["parent"]].update({attr["attribute"]: attr["attribute_value"]})

		return attribute_map

	def get_opening_vouchers(self):
		opening_vouchers = {"Stock Entry": [], "Stock Reconciliation": []}

		se = frappe.qb.DocType("Stock Entry")
		sr = frappe.qb.DocType("Stock Reconciliation")

		vouchers_data = (
			frappe.qb.from_(
				(
					frappe.qb.from_(se)
					.select(se.name, Coalesce("Stock Entry").as_("voucher_type"))
					.where((se.docstatus == 1) & (se.posting_date <= self.to_date) & (se.is_opening == "Yes"))
				)
				+ (
					frappe.qb.from_(sr)
					.select(sr.name, Coalesce("Stock Reconciliation").as_("voucher_type"))
					.where(
						(sr.docstatus == 1) & (sr.posting_date <= self.to_date) & (sr.purpose == "Opening Stock")
					)
				)
			).select("voucher_type", "name")
		).run(as_dict=True)

		if vouchers_data:
			for d in vouchers_data:
				opening_vouchers[d.voucher_type].append(d.name)

		return opening_vouchers

	@staticmethod
	def get_inventory_dimension_fields():
		return [dimension.fieldname for dimension in get_inventory_dimensions()]

	@staticmethod
	def get_opening_fifo_queue(report_data):
		opening_fifo_queue = report_data.get("opening_fifo_queue") or []
		for row in opening_fifo_queue:
			row[1] = getdate(row[1])

		return opening_fifo_queue


def filter_items_with_no_transactions(
	iwb_map, float_precision: float, inventory_dimensions: list = None
):
	pop_keys = []
	for group_by_key in iwb_map:
		qty_dict = iwb_map[group_by_key]

		no_transactions = True
		for key, val in qty_dict.items():
			if inventory_dimensions and key in inventory_dimensions:
				continue

			if key in [
				"item_code",
				"warehouse",
				"item_name",
				"item_group",
				"project",
				"stock_uom",
				"company",
				"opening_fifo_queue",
			]:
				continue
			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			pop_keys.append(group_by_key)
	for key in pop_keys:
		iwb_map.pop(key)

	return iwb_map


def get_variants_attributes() -> List[str]:
	"""Return all item variant attributes."""
	return frappe.get_all("Item Attribute", pluck="name")








#---------------------------*-----------------*


# import frappe
# from frappe import _
# from frappe.utils import cint, date_diff, flt, getdate
# from erpnext.stock.utils import is_reposting_item_valuation_in_progress


# from frappe.query_builder.functions import CombineDatetime
# from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
# from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
# from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
# from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
# from erpnext.stock.utils import (is_reposting_item_valuation_in_progress,update_included_uom_in_report,)

# def get_spp_batch_no(sle):
# 	if sle.u_o_m == 'Nos':
# 		sle.qty_after_transaction = int(sle.qty_after_transaction)

# def execute(filters=None):
# 	filters['from_date'] = filters.get('manufacturing_date')
# 	filters['to_date']  = filters.get('manufacturing_date')
# 	filters['company'] = 'SPP'
# 	is_reposting_item_valuation_in_progress()
# 	include_uom = filters.get("include_uom")
# 	columns = get_columns(filters)
# 	items = get_items(filters)
# 	sl_entries = get_stock_ledger_entries(filters, items)
# 	item_details = get_item_details(items, sl_entries, include_uom)
# 	# opening_row = get_opening_balance(filters, columns, sl_entries)
# 	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
# 	data = []
# 	conversion_factors = []
# 	# if opening_row:
# 	# 	data.append(opening_row)
# 	# 	conversion_factors.append(0)

# 	actual_qty = stock_value = 0

# 	available_serial_nos = {}
# 	inventory_dimension_filters_applied = check_inventory_dimension_filters_applied(filters)

# 	for sle in sl_entries:
# 		get_spp_batch_no(sle)
# 		item_detail = item_details[sle.item_code]
# 		sle.update(item_detail)
# 		if filters.get("batch_no") or inventory_dimension_filters_applied:
# 			actual_qty += flt(sle.actual_qty, precision)
# 			stock_value += sle.stock_value_difference

# 			if sle.voucher_type == "Stock Reconciliation" and not sle.actual_qty:
# 				actual_qty = sle.qty_after_transaction
# 				stock_value = sle.stock_value

# 			sle.update({"qty_after_transaction": actual_qty, "stock_value": stock_value})

# 		sle.update({"in_qty": max(sle.actual_qty, 0), "out_qty": min(sle.actual_qty, 0)})

# 		if sle.serial_no:
# 			update_available_serial_nos(available_serial_nos, sle)

# 		if sle.actual_qty:
# 			sle["in_out_rate"] = flt(sle.stock_value_difference / sle.actual_qty, precision)

# 		elif sle.voucher_type == "Stock Reconciliation":
# 			sle["in_out_rate"] = sle.valuation_rate

# 		data.append(sle)

# 		if include_uom:
# 			conversion_factors.append(item_detail.conversion_factor)

# 	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
# 	return columns, data


# def update_available_serial_nos(available_serial_nos, sle):
# 	serial_nos = get_serial_nos(sle.serial_no)
# 	key = (sle.item_code, sle.warehouse)
# 	if key not in available_serial_nos:
# 		stock_balance = get_stock_balance_for(
# 			sle.item_code, sle.warehouse, sle.posting_date, sle.posting_time
# 		)
# 		serials = get_serial_nos(stock_balance["serial_nos"]) if stock_balance["serial_nos"] else []
# 		available_serial_nos.setdefault(key, serials)

# 	existing_serial_no = available_serial_nos[key]
# 	for sn in serial_nos:
# 		if sle.actual_qty > 0:
# 			if sn in existing_serial_no:
# 				existing_serial_no.remove(sn)
# 			else:
# 				existing_serial_no.append(sn)
# 		else:
# 			if sn in existing_serial_no:
# 				existing_serial_no.remove(sn)
# 			else:
# 				existing_serial_no.append(sn)

# 	sle.balance_serial_no = "\n".join(existing_serial_no)

# def get_columns(filters):
# 	columns = [
# 		{
# 			"label": _("Item Code"),
# 			"fieldname": "item_code",
# 			"fieldtype": "Link",
# 			"options": "Item",
# 			"width": 300,
# 		},
# 		{
# 			"label": _("Warehouse"),
# 			"fieldname": "warehouse",
# 			"fieldtype": "Link",
# 			"options": "Warehouse",
# 			"width": 250,
# 		},
# 		{
# 			"label": _("Balance Qty"),
# 			"fieldname": "qty_after_transaction",
# 			"fieldtype": "Float",
# 			"width": 100,
# 			"convertible": "qty",
# 		},
# 		{
# 			"label": _("Stock UOM"),
# 			"fieldname": "stock_uom",
# 			"fieldtype": "Link",
# 			"options": "UOM",
# 			"width": 130,
# 		},
# 		{
# 				"label": _("Stage"),
# 				"fieldname": "item_group",
# 				"fieldtype": "Link",
# 				"options": "Item Group",
# 				"width": 150,
# 			},	
# 	]

# 	return columns

# def get_stock_ledger_entries(filters, items):
# 	from frappe.query_builder.functions import Count,Sum,Max
# 	spp_settings = frappe.get_single("SPP Settings")
# 	if not spp_settings.rejection_warehouse:
# 		frappe.throw(f'Rejection Warehouse not mapped in <p>SPP Settings</p>')
# 	if not spp_settings.pdir_visual_t__warehouse:
# 		frappe.throw(f'PDIR & Final Visual Rejection Warehouse not mapped in <p>SPP Settings</p>')
# 	sle = frappe.qb.DocType("Stock Ledger Entry")
# 	# sum_qty = Sum(sle.qty_after_transaction).as_("qty_after_transaction")
# 	max = Max(sle.creation).as_("max_date")
# 	query = (
# 		frappe.qb.from_(sle)
# 		.select(
# 			sle.item_code,
# 			CombineDatetime(sle.posting_date, sle.posting_time).as_("date"),
# 			sle.warehouse,
# 			sle.posting_date,
# 			sle.posting_time,
# 			sle.actual_qty,
# 			sle.incoming_rate,
# 			sle.valuation_rate,
# 			sle.company,
# 			sle.voucher_type,
# 			# sum_qty,
# 			max,
# 			sle.qty_after_transaction,
# 			sle.stock_value_difference,
# 			sle.voucher_no,
# 			sle.stock_value,
# 			sle.batch_no,
# 			sle.serial_no,
# 			sle.project,
# 			sle.stock_uom.as_('u_o_m'),
# 		)
# 		.where(
# 			(sle.docstatus < 2)
# 			& (sle.is_cancelled == 0)
# 			& (sle.posting_date[filters.from_date : filters.to_date])
# 			& (sle.warehouse != spp_settings.rejection_warehouse)
# 			& (sle.warehouse != spp_settings.pdir_visual_t__warehouse)
# 		)
# 		.groupby(sle.item_code, sle.warehouse)
# 		# .orderby(CombineDatetime(sle.posting_date, sle.posting_time))
# 		.orderby(sle.creation, order=frappe.qb.desc)
# 	)

# 	inventory_dimension_fields = get_inventory_dimension_fields()
# 	if inventory_dimension_fields:
# 		for fieldname in inventory_dimension_fields:
# 			query = query.select(fieldname)
# 			if fieldname in filters and filters.get(fieldname):
# 				query = query.where(sle[fieldname].isin(filters.get(fieldname)))

# 	if items:
# 		query = query.where(sle.item_code.isin(items))

# 	for field in ["voucher_no", "batch_no", "project", "company"]:
# 		if filters.get(field) and field not in inventory_dimension_fields:
# 			query = query.where(sle[field] == filters.get(field))

# 	query = apply_warehouse_filter(query, sle, filters)

# 	# frappe.log_error(title='--summary query--',message = query)
# 	# frappe.log_error(title='--summary sle--',message = query.run(as_dict=True))

# 	return query.run(as_dict=True)


# def get_inventory_dimension_fields():
# 	return [dimension.fieldname for dimension in get_inventory_dimensions()]


# def get_items(filters):
# 	item = frappe.qb.DocType("Item")
# 	query = frappe.qb.from_(item).select(item.name)
# 	conditions = []

# 	if item_code := filters.get("item_code"):
# 		conditions.append(item.name == item_code)
# 	else:
# 		if brand := filters.get("brand"):
# 			conditions.append(item.brand == brand)
# 		if item_group := filters.get("item_group"):
# 			if condition := get_item_group_condition(item_group, item):
# 				conditions.append(condition)

# 	items = []
# 	if conditions:
# 		for condition in conditions:
# 			query = query.where(condition)
# 		items = [r[0] for r in query.run()]

# 	return items


# def get_item_details(items, sl_entries, include_uom):
# 	item_details = {}
# 	if not items:
# 		items = list(set(d.item_code for d in sl_entries))

# 	if not items:
# 		return item_details

# 	item = frappe.qb.DocType("Item")
# 	query = (
# 		frappe.qb.from_(item)
# 		.select(item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom)
# 		.where(item.name.isin(items))
# 	)

# 	if include_uom:
# 		ucd = frappe.qb.DocType("UOM Conversion Detail")
# 		query = (
# 			query.left_join(ucd)
# 			.on((ucd.parent == item.name) & (ucd.uom == include_uom))
# 			.select(ucd.conversion_factor)
# 		)

# 	res = query.run(as_dict=True)

# 	for item in res:
# 		item_details.setdefault(item.name, item)

# 	return item_details


# def get_sle_conditions(filters):
# 	conditions = []
# 	if filters.get("warehouse"):
# 		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
# 		if warehouse_condition:
# 			conditions.append(warehouse_condition)
# 	if filters.get("voucher_no"):
# 		conditions.append("voucher_no=%(voucher_no)s")
# 	if filters.get("batch_no"):
# 		conditions.append("batch_no=%(batch_no)s")
# 	if filters.get("project"):
# 		conditions.append("project=%(project)s")

# 	for dimension in get_inventory_dimensions():
# 		if filters.get(dimension.fieldname):
# 			conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")

# 	return "and {}".format(" and ".join(conditions)) if conditions else ""


# def get_opening_balance(filters, columns, sl_entries):
# 	if not (filters.item_code and filters.warehouse and filters.from_date):
# 		return

# 	from erpnext.stock.stock_ledger import get_previous_sle

# 	last_entry = get_previous_sle(
# 		{
# 			"item_code": filters.item_code,
# 			"warehouse_condition": get_warehouse_condition(filters.warehouse),
# 			"posting_date": filters.from_date,
# 			"posting_time": "00:00:00",
# 		}
# 	)

# 	# check if any SLEs are actually Opening Stock Reconciliation
# 	for sle in list(sl_entries):
# 		if (
# 			sle.get("voucher_type") == "Stock Reconciliation"
# 			and sle.posting_date == filters.from_date
# 			and frappe.db.get_value("Stock Reconciliation", sle.voucher_no, "purpose") == "Opening Stock"
# 		):
# 			last_entry = sle
# 			sl_entries.remove(sle)

# 	row = {
# 		"item_code": _("'Opening'"),
# 		"qty_after_transaction": last_entry.get("qty_after_transaction", 0),
# 		"valuation_rate": last_entry.get("valuation_rate", 0),
# 		"stock_value": last_entry.get("stock_value", 0),
# 	}

# 	return row


# def get_warehouse_condition(warehouse):
# 	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
# 	if warehouse_details:
# 		return (
# 			" exists (select name from `tabWarehouse` wh \
# 			where wh.lft >= %s and wh.rgt <= %s and warehouse = wh.name)"
# 			% (warehouse_details.lft, warehouse_details.rgt)
# 		)

# 	return ""


# def get_item_group_condition(item_group, item_table=None):
# 	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
# 	if item_group_details:
# 		if item_table:
# 			ig = frappe.qb.DocType("Item Group")
# 			return item_table.item_group.isin(
# 				(
# 					frappe.qb.from_(ig)
# 					.select(ig.name)
# 					.where(
# 						(ig.lft >= item_group_details.lft)
# 						& (ig.rgt <= item_group_details.rgt)
# 						& (item_table.item_group == ig.name)
# 					)
# 				)
# 			)
# 		else:
# 			return (
# 				"item.item_group in (select ig.name from `tabItem Group` ig \
# 				where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"
# 				% (item_group_details.lft, item_group_details.rgt)
# 			)


# def check_inventory_dimension_filters_applied(filters) -> bool:
# 	for dimension in get_inventory_dimensions():
# 		if dimension.fieldname in filters and filters.get(dimension.fieldname):
# 			return True

# 	return False

#------------------------------------------*=-------------------------------------*


# def execute(filters=None):
# 	columns, data = get_columns(), get_datas(filters)
# 	return columns, data

# def get_columns():
# 	c__ = []
# 	c__.append(_('Item Code')+':Link/Item:180')
# 	c__.append(_('Total Qty')+':Float:150')
# 	c__.append(_('UOM')+':Link/UOM:100')
# 	c__.append(_('Stage')+':Data:150')
# 	return c__

# def apply_get_filters(filters,type):
# 	condition = ''
# 	spp_settings = frappe.get_single("SPP Settings")
# 	if not spp_settings.rejection_warehouse:
# 		frappe.throw(f'Rejection Warehouse not mapped in <p>SPP Settings</p>')
# 	if type == 'Stock Entry':
# 		condition += f""" AND SED.t_warehouse != '{spp_settings.rejection_warehouse}' """
# 		if filters.get('item'):
# 			condition += f""" AND SED.item_code = '{filters.get('item')}' """
# 		if filters.get('manufacturing_date'):
# 			condition += f""" AND (DATE(SE.modified) = '{filters.get('manufacturing_date')}')"""
# 		if filters.get('stage'):
# 			condition += f""" AND I.item_group = '{filters.get('stage')}' """
# 	elif type == 'Delivery Note':
# 		condition += f""" AND DNI.target_warehouse != '{spp_settings.rejection_warehouse}' """
# 		if filters.get('item'):
# 			condition += f""" AND DNI.item_code = '{filters.get('item')}' """
# 		if filters.get('manufacturing_date'):
# 			condition += f""" AND (DATE(DN.modified) = '{filters.get('manufacturing_date')}')"""
# 		if filters.get('stage'):
# 			condition += f""" AND I.item_group = '{filters.get('stage')}' """
# 	return condition

# def get_datas(filters):
# 	if not filters.get("manufacturing_date"):
# 		frappe.msgprint(_("<b>Manufacturing Date</b> is required..!"))
# 		return []
# 	is_reposting_item_valuation_in_progress()
# 	if not filters:
# 		filters = {}
# 	condition = apply_get_filters(filters,'Stock Entry')
# 	# dn_condition = apply_get_filters(filters,'Delivery Note')
# 	query = f""" 	SELECT 
# 							SED.item_code,(CASE 
# 								WHEN 
# 									SED.uom = "Nos" THEN ROUND(SUM(B.batch_qty),0)  
# 								ELSE SUM(B.batch_qty) 
# 							END) total_qty,
# 							SED.uom,I.item_group stage
# 						FROM
# 							`tabStock Entry` SE INNER JOIN `tabStock Entry Detail` SED ON SED.parent = SE.name
# 							INNER JOIN `tabBatch` B ON B.name = SED.batch_no
# 							INNER JOIN `tabItem` I ON I.name = SED.item_code 
# 							INNER JOIN `tabStock Ledger Entry` SL ON B.name = SL.batch_no AND SL.voucher_no = SE.name AND SL.voucher_type = 'Stock Entry'
# 					WHERE
# 						SE.docstatus = 1 AND B.batch_qty !=0 AND B.batch_qty IS NOT NULL AND 
# 						SED.t_warehouse IS NOT NULL AND SL.warehouse = SED.t_warehouse AND 
# 						(CASE 
# 							WHEN 
# 								B.expiry_date IS NOT NULL THEN B.expiry_date >= CURDATE() 
# 							ELSE 
# 								1=1 END) 
# 						AND SL.is_cancelled = 0 and SL.docstatus < 2 AND IFNULL(SL.batch_no, '') != ''
# 						{condition} GROUP BY SED.item_code,SED.uom,I.item_group
# 				"""
# 	frappe.log_error(title='query',message=query)
# 	resp__ = frappe.db.sql(query, as_dict = 1)
# 	return resp__
	

