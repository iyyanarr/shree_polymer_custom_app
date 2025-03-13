

frappe.ui.form.on("Revalidation Sticker", {
	refresh(frm) {

	},
    // lot_no: function(frm) {
    //     if (frm.doc.lot_no) {
    //         // Simple function to simulate barcode generation
    //         frm.set_value('barcode', generateBarcode(frm.doc.lot_no));
    //     }
    // }
});
// function generateBarcode(lot_no) {
//     // A simple transformation to simulate barcode generation
//     return lot_no.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
// }