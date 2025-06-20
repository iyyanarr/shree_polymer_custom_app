# Rejection Report

## Overview

The Rejection Report is a comprehensive custom report for the Shree Polymer Custom App that provides detailed rejection analysis across different stages of the manufacturing process. It supports three different report types: Line, Deflashing, and Final rejection reports.

## Features

### Report Types

1. **Line Rejection Report**
   - Focuses on rejections during the line inspection stage
   - Covers moulding production entries and related inspections
   - Includes data from both regular and add-on work planning

2. **Deflashing Rejection Report**
   - Analyzes rejections during the deflashing process
   - Tracks incoming inspection data for deflashed items
   - Links deflashing receipt entries with moulding production

3. **Final Rejection Report**
   - Comprehensive final stage rejection analysis
   - Includes trimming operator information
   - Covers final visual inspections and related processes

### Key Metrics Tracked

- Line Inspection rejections (quantity and percentage)
- Patrol Inspection rejections
- Lot Inspection rejections
- Incoming Inspection rejections (for Deflashing and Final reports)
- Final Visual Inspection rejections (for Final report only)
- Total rejection percentages

## Filters Available

- **Date**: Required filter for report date
- **Report Type**: Selection between Line, Deflashing, and Final reports
- **Item**: Different item groups based on report type (Mat, Products, Finished Goods)
- **Compound BOM No**: Filter by specific BOM
- **Press No**: Filter by specific workstation/press
- **Moulding Operator**: Filter by employee
- **Deflashing Operator**: Available for Deflashing and Final reports
- **Mould Ref**: Filter by specific mould
- **Trimming Operators**: ID and OD trimming operators (Final report only)
- **Show Rejection Qty**: Toggle to show rejection quantities

## Technical Implementation

### File Structure

```
rejection_report/
├── rejection_report.py      # Backend logic
├── rejection_report.js      # Frontend configuration
├── rejection_report.json    # Report metadata
└── README.md               # This documentation
```

### Backend Architecture

The Python backend follows a modular approach:

- `execute()`: Main entry point
- `build_report_columns()`: Dynamic column generation
- `get_rejection_data()`: Main data router
- `get_line_rejection_data()`: Line report specific data
- `get_deflashing_rejection_data()`: Deflashing report specific data
- `get_final_rejection_data()`: Final report specific data
- `add_totals_row()`: Calculate and append summary totals
- Helper functions for query building and data processing

### Key Improvements Made

1. **Code Organization**: Broke down monolithic functions into smaller, focused functions
2. **Error Handling**: Added try-catch blocks and error logging
3. **Code Readability**: Improved variable names and added comprehensive documentation
4. **SQL Safety**: Replaced string concatenation with parameterized queries where possible
5. **Performance**: Used COALESCE instead of verbose CASE statements for null handling
6. **Maintainability**: Added constants for report types and better separation of concerns

### Database Relationships

The report joins data from multiple doctypes:

- `Moulding Production Entry` (MPE)
- `Work Planning` / `Add On Work Planning` (WP)
- `Blank Bin Issue` (BBIS)
- `Stock Entry` and `Stock Entry Detail` (SE, SED)
- `Inspection Entry` (LINE, PINE, LOINE, INE, VSINE)
- `Mould Specification` (MSP)
- `BOM` and `BOM Item` (B, BI)
- `Deflashing Receipt Entry` (DFR)
- `Lot Resource Tagging` (LRT)

## Usage

1. Navigate to Reports > Rejection Report
2. Select the desired report type (Line, Deflashing, or Final)
3. Set the date filter (required)
4. Apply additional filters as needed
5. Toggle "Show Rejection Qty" to see rejection quantities alongside percentages
6. Click "Refresh" to generate the report

## Output

The report provides:

- Detailed rejection data for each lot
- Production quantities and compound consumption
- Rejection percentages for different inspection stages
- A summary totals row at the bottom
- Export capabilities to Excel/PDF

## Error Handling

The report includes comprehensive error handling:

- Invalid filter combinations
- Missing configuration in SPP Settings
- Database query failures
- Division by zero in percentage calculations

Errors are logged to the Frappe error log for debugging purposes.

## Performance Considerations

- The report uses complex SQL queries with multiple joins
- Large date ranges may impact performance
- Indexes on lot numbers and posting dates are recommended
- Consider using appropriate filters to limit data scope

## Future Enhancements

Potential improvements could include:

- Caching of frequently accessed configuration data
- Further query optimization
- Additional export formats
- Interactive charts and visualizations
- Mobile-responsive design improvements

## Support

For issues or questions related to this report:

1. Check the Frappe error logs for specific error messages
2. Verify that all required doctypes and fields exist
3. Ensure SPP Settings are properly configured
4. Contact the development team with specific error details

---

**Last Updated**: June 2025  
**Version**: 2.0 (Refactored)  
**Compatibility**: Frappe v14/v15, ERPNext v14/v15
