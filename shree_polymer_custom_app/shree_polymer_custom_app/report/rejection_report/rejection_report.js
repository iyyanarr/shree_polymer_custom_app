// Copyright (c) 2023, Tridotstech and contributors
// For license information, please see license.txt
/* eslint-disable */

/**
 * Rejection Report Configuration
 * 
 * This report provides comprehensive rejection analysis across different stages
 * of the manufacturing process including Line, Deflashing, and Final inspections.
 */

// Flag to track total row formatting
let isTotalRow = false;

// Report type constants
const REPORT_TYPES = {
    LINE: 'Line Rejection Report',
    DEFLASHING: 'Deflashing Rejection Report', 
    FINAL: 'Final Rejection Report'
};

// Item group mappings for different report types
const ITEM_GROUPS = {
    [REPORT_TYPES.LINE]: 'Mat',
    [REPORT_TYPES.DEFLASHING]: 'Products',
    [REPORT_TYPES.FINAL]: 'Finished Goods'
};

frappe.query_reports["Rejection Report"] = {
    "filters": [
        {
            "fieldname": "date",
            "fieldtype": "Date",
            "label": __("Date"),
            "reqd": 1,
            'default': frappe.datetime.nowdate()
        },
        {
            "fieldname": "report_type",
            "fieldtype": "Select",
            "options": Object.values(REPORT_TYPES).join('\n'),
            "default": REPORT_TYPES.LINE,
            "label": __("Report Type")
        },
        {
            "fieldname": "t_item",
            "fieldtype": "Link",
            "options": "Item",
            "label": __("Item"),
            "get_query": () => ({
                "filters": {
                    "item_group": ITEM_GROUPS[REPORT_TYPES.LINE]
                }
            }),
            "depends_on": `eval:doc.report_type == '${REPORT_TYPES.LINE}'`
        },
        {
            "fieldname": "p_item",
            "fieldtype": "Link",
            "options": "Item",
            "label": __("Item"),
            "get_query": () => ({
                "filters": {
                    "item_group": ITEM_GROUPS[REPORT_TYPES.DEFLASHING]
                }
            }),
            "depends_on": `eval:doc.report_type == '${REPORT_TYPES.DEFLASHING}'`
        },
        {
            "fieldname": "f_item",
            "fieldtype": "Link",
            "options": "Item",
            "label": __("Item"),
            "get_query": () => ({
                "filters": {
                    "item_group": ITEM_GROUPS[REPORT_TYPES.FINAL]
                }
            }),
            "depends_on": `eval:doc.report_type == '${REPORT_TYPES.FINAL}'`
        },
        {
            "fieldname": "compound_bom_no",
            "fieldtype": "Link",
            "options": "BOM",
            "label": __("Compound BOM No")
        },
        {
            "fieldname": "press_no",
            "fieldtype": "Link",
            "options": "Workstation",
            "label": __("Press No"),
            "get_query": () => ({
                "query": "shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_press_info"
            })
        },
        {
            "fieldname": "moulding_operator",
            "fieldtype": "Link",
            "options": "Employee",
            "label": __("Moulding Operator"),
            "get_query": () => ({
                "query": "shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulding_operator_info",
                "filters": {
                    "designation": "Moulding Supervisor"
                }
            })
        },
        {
            "fieldname": "deflashing_operator",
            "fieldtype": "Link",
            "options": "Warehouse",
            "label": __("Deflashing Operator"),
            "depends_on": `eval:doc.report_type == '${REPORT_TYPES.DEFLASHING}' || doc.report_type == '${REPORT_TYPES.FINAL}'`,
            "get_query": () => ({
                "filters": {
                    'parent_warehouse': "Deflashing Vendors - SPP INDIA"
                }
            })
        },
        {
            "fieldname": "mould_ref",
            "fieldtype": "Link",
            "options": "Item",
            "label": __("Mould Ref"),
            "get_query": () => ({
                "query": "shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulds"
            })
        },
        {
            "fieldname": "trimming_id__operator",
            "fieldtype": "Link",
            "options": "Employee",
            "label": __("Trimming ID Operator"),
            "depends_on": `eval:doc.report_type == '${REPORT_TYPES.FINAL}'`,
            "get_query": () => ({
                "query": "shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulding_operator_info",
                "filters": {
                    "designation": "ID Trimming,OD Trimming"
                }
            })
        },
        {
            "fieldname": "trimming_od_operator",
            "fieldtype": "Link",
            "options": "Employee",
            "label": __("Trimming OD Operator"),
            "depends_on": `eval:doc.report_type == '${REPORT_TYPES.FINAL}'`,
            "get_query": () => ({
                "query": "shree_polymer_custom_app.shree_polymer_custom_app.report.rejection_report.rejection_report.get_moulding_operator_info",
                "filters": {
                    "designation": "ID Trimming,OD Trimming"
                }
            })
        },
        {
            "fieldname": "show_rejection_qty",
            "fieldtype": "Check",
            "label": __("Show Rejection Qty")
        }
    ],
    
    /**
     * Format cells for better visual presentation
     * @param {*} value - Cell value
     * @param {*} row - Row index  
     * @param {*} column - Column definition
     * @param {*} data - Row data
     * @param {*} default_formatter - Default formatter function
     * @returns {string} Formatted cell content
     */
    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Check if this is a total row by looking for specific indicators
        if (column.fieldname === "item" && data && !data.item) {
            isTotalRow = true;
        }
        
        // Format total row in bold
        if (isTotalRow) {
            value = `<b>${value}</b>`;
        }
        
        return value;
    },
    
    /**
     * Reset formatting flag after datatable render
     */
    "after_datatable_render": function() {
        isTotalRow = false;
    }
};

