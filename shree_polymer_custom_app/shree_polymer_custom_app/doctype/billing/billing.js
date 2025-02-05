// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Billing', {
	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			frm.set_df_property("qty", "hidden", 1)
			frm.set_df_property("add", "hidden", 1)
		}
		frm.events.view_sales_invoice(frm)
	},
	timeline_refresh:frm =>{
		frm.events.view_sales_invoice(frm)
	},
	view_sales_invoice:(frm) =>{
		if(frm.doc.sales_invoice_reference){
			frm.add_custom_button(__("View Sales Invoice"), function(){
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice_reference);
			  });
		}
		else{
			frm.remove_custom_button('View Sales Invoice');
		}
	},
	"scan_package": (frm) => {
		if (frm.doc.scan_package && frm.doc.scan_package != undefined) {
			if (frm.doc.customer && frm.doc.customer != undefined) {
				frappe.call({
					method: 'shree_polymer_custom_app.shree_polymer_custom_app.doctype.billing.billing.validate_lot_barcode',
					args: {
						bar__code: frm.doc.scan_package
					},
					freeze: true,
					callback: function (r) {
						if (r && r.status == "failed") {
							frappe.msgprint(r.message);
							frm.set_value("scan_package", "");
							frm.set_value("item_code", "");
							frm.set_value("spp_batch_no", "");
							frm.set_value("batch_no", "")
							frm.set_value("qty", 0)
							frm.set_value("item_name", '')
							frm.set_value("uom", '')
							frm.set_value("warehouse", '')
							frm.set_value("valuation_rate", 0)
							frm.set_value("amount", 0)
							frm.set_df_property("qty", "hidden", 1)
						}
						else if (r && r.status == "success") {
							frm.total_nos = 0
							if (frm.doc.items && frm.doc.items.length > 0) {
								let flag = false
								frm.doc.items.map(res => {
									if (res.package_barcode_text == frm.doc.scan_package) {
										flag = true
										frappe.validated = false
										frappe.msgprint(`Scanned lot <b>${frm.doc.scan_package}</b> is already added.`);
										frm.set_value("scan_package", "");
										return
									}
									frm.total_nos += res.qty
								})
								if (flag) {
									return
								}
							}
							frm.set_df_property("qty", "hidden", 0)
							frm.set_value("item_code", r.message.item_code);
							frm.set_value("spp_batch_no", r.message.spp_batch_number);
							frm.set_value("batch_no", r.message.batch_no)
							frm.set_value("qty", r.message.qty)
							frm.set_value("item_name", r.message.item_name)
							frm.set_value("uom", r.message.uom)
							frm.set_value("warehouse", r.message.from_warehouse)
							frm.set_value("valuation_rate", r.message.valuation_rate)
							frm.set_value("amount", r.message.amount)
						}
						else {
							frappe.msgprint("Something went wrong..!");
						}
					}
				});
			}
			else {
				frm.set_value("scan_package", "");
				frappe.validated = false;
				frappe.msgprint("Please choose <b>Customer</b> before scan..!")
			}
		}
	},
	"add": (frm) => {
		if (!frm.doc.customer) {
			frappe.validated = false
			frappe.msgprint("Please select <b>Customer</b> before add.");
			return false;
		}
		if (!frm.doc.scan_package) {
			frappe.validated = false
			frappe.msgprint("Please scan <b>Package</b> before add.");
			return false;
		}
		if (!frm.doc.amount) {
			frappe.validated = false
			frappe.msgprint("Product<b>Amount</b> is not found.");
			return false;
		}
		if (!frm.doc.valuation_rate) {
			frappe.validated = false
			frappe.msgprint("Product<b>Valuation Rate</b> is not found.");
			return false;
		}
		else {
			let row = frappe.model.add_child(frm.doc,"Billing Item","items")
			row.item_code = frm.doc.item_code
			row.spp_batch_no = frm.doc.spp_batch_no
			row.batch_no = frm.doc.batch_no
			row.qty = frm.doc.qty
			row.item_name = frm.doc.item_name
			row.uom = frm.doc.uom
			row.warehouse = frm.doc.warehouse
			row.package_barcode_text = frm.doc.scan_package
			row.amount = frm.doc.amount
			row.valuation_rate = frm.doc.valuation_rate
			frm.refresh_field('items');
			frm.set_value("scan_package", "");
			frm.set_value("item_code", "");
			frm.set_value("spp_batch_no", "");
			frm.set_value("batch_no", "")
			frm.set_value("qty", 0)
			frm.set_value("item_name", '')
			frm.set_value("uom", '')
			frm.set_value("warehouse", '')
			frm.set_df_property("qty", "hidden", 1)
			frm.set_value("valuation_rate", 0)
			frm.set_value("amount", 0)
		}
	}
});
