# Copyright (c) 2023, Tridotstech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, cstr, duration_to_seconds, flt, update_progress_bar,format_time, formatdate, getdate, nowdate,now

def execute(filters=None):
	columns, data = get_columns(),get_datas(filters)
	return columns, data

def get_columns():
	col__ = []
	col__.append(_("Date")+":Date:100")
	col__.append(_("Shift")+":Data:130")
	col__.append(_("Compound Ref")+":Link/Item:150")
	col__.append(_("Compound Req Kgs")+":Float : 150")
	return col__

def get_datas(filters):
	condition = ""
	if filters.get('compound_ref'):
		condition += f" AND BOMI.item_code = '{filters.get('compound_ref')}' "
	if filters.get('date'):
		condition += f" AND DATE(WP.date) = '{filters.get('date')}' "
	if filters.get('shift'):
		condition += f" AND WP.shift_type = '{filters.get('shift')}' "
	
	acondition = ""
	if filters.get('compound_ref'):
		acondition += f" AND ABOMI.item_code = '{filters.get('compound_ref')}' "
	if filters.get('date'):
		acondition += f" AND DATE(AWP.date) = '{filters.get('date')}' "
	if filters.get('shift'):
		acondition += f" AND AWP.shift_type = '{filters.get('shift')}' "
	
	compound_query = "SUM((MS.wtlift_avg_gms/1000) * WPIT.target_qty)"
	a_compound_query = "SUM((AMS.wtlift_avg_gms/1000) * AWPIT.target_qty)"
	spp_settings = frappe.get_single("SPP Settings")
	if spp_settings.extra__of_compound_required:
		compound_query = f" (SUM((MS.wtlift_avg_gms/1000) * WPIT.target_qty)) + (((SUM((MS.wtlift_avg_gms/1000) * WPIT.target_qty))/100) * {spp_settings.extra__of_compound_required})"
		a_compound_query = f" (SUM((AMS.wtlift_avg_gms/1000) * AWPIT.target_qty)) + (((SUM((AMS.wtlift_avg_gms/1000) * AWPIT.target_qty))/100) * {spp_settings.extra__of_compound_required})"

	query = f"""
				SELECT DATE(WP.date) date,WP.shift_type shift,
				BOMI.item_code AS compound_ref,
				 	{compound_query}
				AS compound_req_kgs
				
				FROM `tabWork Planning` WP
					INNER JOIN `tabWork Plan Item` WPI ON WPI.parent = WP.name
					INNER JOIN `tabBOM Item` BOMI ON BOMI.parent = WPI.bom
					INNER JOIN `tabItem` I ON I.name = BOMI.item_code AND I.item_group = 'Compound'
					INNER JOIN `tabMould Specification` MS ON MS.mould_ref = WPI.mould 
						AND MS.spp_ref = WPI.item AND MS.mould_status = 'ACTIVE'

					INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = WPI.item 
							AND WPIT.shift_type = WP.shift_time
				WHERE 
					WP.docstatus = 1  {condition}
					GROUP BY BOMI.item_code,WP.shift_type,DATE(WP.date)

				UNION ALL

					SELECT DATE(AWP.date) date,AWP.shift_type shift,
				ABOMI.item_code AS compound_ref,
				CASE 
					WHEN AMS.wtlift_avg_gms = 0 THEN 0
					ELSE {a_compound_query}
				END AS compound_req_kgs
				
				FROM `tabAdd On Work Planning` AWP
					INNER JOIN `tabAdd On Work Plan Item` AWPI ON AWPI.parent = AWP.name
					INNER JOIN `tabBOM Item` ABOMI ON ABOMI.parent = AWPI.bom
					INNER JOIN `tabItem` AI ON AI.name = ABOMI.item_code AND AI.item_group = 'Compound'
					INNER JOIN `tabMould Specification` AMS ON AMS.mould_ref = AWPI.mould 
						AND AMS.spp_ref = AWPI.item AND AMS.mould_status = 'ACTIVE'

					INNER JOIN `tabWork Plan Item Target` AWPIT ON AWPIT.item = AWPI.item 
							AND AWPIT.shift_type = AWP.shift_time
				WHERE 
					AWP.docstatus = 1 {acondition}
					GROUP BY ABOMI.item_code,AWP.shift_type,DATE(AWP.date) 
				"""
	response =  frappe.db.sql(query,as_dict=1)
	return response

@frappe.whitelist()
def get_filter_compound_ref(doctype, compound_ref, searchfield, start, page_len, filters):
	search_condition = ""
	if compound_ref:
		search_condition = "AND I.name LIKE '%"+compound_ref+"%'"
	query = f""" SELECT I.name FROM `tabItem` I
	 		 WHERE I.item_group = 'Compound' {search_condition} """
	compounds = frappe.db.sql(query)
	return compounds

@frappe.whitelist()
def get_file_data():
	try:
		import json
		from frappe.desk.query_report import run,format_duration_fields,build_xlsx_data
		from frappe.utils.xlsxutils import make_xlsx
		data = frappe._dict(frappe.local.form_dict)
		email_ids = data.email_ids.split(',')
		data.pop("csrf_token", None)
		if isinstance(data.get("filters"), str):
			filters = json.loads(data["filters"])
		if data.get("report_name"):
			report_name = data["report_name"]
			frappe.permissions.can_export(
				frappe.get_cached_value("Report", report_name, "ref_doctype"),
				raise_exception=True,
			)
		file_format_type = data.get("file_format_type")
		custom_columns = frappe.parse_json(data.get("custom_columns", "[]"))
		include_indentation = data.get("include_indentation")
		visible_idx = data.get("visible_idx")
		if isinstance(visible_idx, str):
			visible_idx = json.loads(visible_idx)
		if file_format_type == "Excel":
			data = run(report_name, filters, custom_columns=custom_columns)
			data = frappe._dict(data)
			if not data.columns:
				frappe.respond_as_web_page(
					_("No data to export"),
					_("You can try changing the filters of your report."),
				)
				return
			format_duration_fields(data)
			xlsx_data, column_widths = build_xlsx_data(data, visible_idx, include_indentation)
			xlsx_file = make_xlsx(xlsx_data, "Query Report", column_widths=column_widths)
			report_name = report_name.replace(" ","")+'-'+nowdate()
			while True:
				if file_id:=frappe.db.exists("File",{"file_name":report_name + ".xlsx"}):
					rp = report_name.split('_')
					if len(rp) == 2:
						rp[1] = '_' + str(int(rp[1]) + 1)
						report_name = ''.join(rp)
					else:
						report_name = report_name +'_'+str(1)
					continue
				else:
					break
			resp_ = upload_files(report_name + ".xlsx", xlsx_file.getvalue())
			if resp_ and resp_.get('status') == 'success':
				resp__e,msg__e = send_email(resp_.get('message'),email_ids)
				if resp__e:
					frappe.response.status = 'success'
					frappe.response.message = msg__e
				else:
					frappe.response.status = 'failed'
					frappe.response.message = msg__e	
			else:
				frappe.response.status = 'failed'
				frappe.response.message = resp_.get('message')
	except Exception:
		frappe.response.status = 'failed'
		frappe.response.message = 'Something went wrong not able to generate <b>Excel</b> file with data..!'
		frappe.log_error(title='get_file_data failed',message= frappe.get_traceback())
	
def upload_files(filename,data):
	try:
		ret = frappe.get_doc({
				"doctype": "File",
				"file_name": filename,
				"is_private": 1,
				"content": data,
				# "decode": True
				  })
		ret.insert(ignore_permissions=True)
		frappe.db.commit()
		return {'status':"success",'message':ret}
	except Exception:
		frappe.log_error(title='upload_files failed',message= frappe.get_traceback())
		return {'status':"failed",'message':'Something went wrong not able to generate <b>Excel</b> file with data..!'}

def send_email(file,recipients):
	try:
		import json
		senders = frappe.db.get_all("Email Account",filters={"default_outgoing":1},fields=['email_id'])
		if senders:
			from frappe.core.doctype.communication.email import make
			make(
				subject = file.file_name,
				content = frappe.render_template("Hi,<br><p>&nbsp;&nbsp; Please find below the <b>Compound Consume Report</b> attachement.</p>",{}),
				sender = senders[0].email_id,
				recipients = recipients,
				communication_medium = "Email",
				send_email = True,
				attachments = [file.name])
			return True,'Email send successfully.!'
		else:
			return False,"Default outgoing email account is not found, Please setup the <b>Default outgoing email account</b>..!"
	except frappe.exceptions.OutgoingEmailError:
		frappe.log_error(title='send email failed',message = frappe.get_traceback())
		return False, json.loads(frappe.local.message_log[0]).get('message')
	except Exception:
		frappe.log_error(title='send email failed',message = frappe.get_traceback())
		return False,"Something went wrong , Not able to send email..!"
	








# GROUP BY MS.mould_ref,BOMI.item_code,WP.shift_type,DATE(WP.date)
# GROUP BY AMS.mould_ref,ABOMI.item_code,AWP.shift_type,DATE(AWP.date) 

	# query = f"""
	# 			SELECT DATE(WP.date) date,WP.shift_number shift,
	# 			BOMI.item_code AS compound_ref,
	# 			CASE 
	# 				WHEN MS.wtlift_avg_gms = 0 THEN 0
	# 				ELSE SUM((MS.wtlift_avg_gms/1000) * WPIT.target_qty)
	# 			END AS compound_req
				
	# 			FROM `tabWork Planning` WP
	# 				INNER JOIN `tabWork Plan Item` WPI ON WPI.parent = WP.name
	# 				INNER JOIN `tabBOM` B ON B.item = WPI.item
	# 				INNER JOIN `tabBOM Item` BOMI ON BOMI.parent = B.name
	# 				INNER JOIN `tabItem` I ON I.name = BOMI.item_code AND I.item_group = 'Compound'
	# 				INNER JOIN `tabMould Specification` MS ON MS.mould_ref = WPI.mould
	# 				INNER JOIN `tabWork Plan Item Target` WPIT ON WPIT.item = WPI.item
	# 			WHERE 
	# 				WP.docstatus = 1 AND 
	# 				CASE 
	# 					WHEN WPI.bom IS NULL THEN B.is_default = 1 AND B.is_active = 1
	# 				ELSE 
	# 					B.name = WPI.bom END 
	# 				{condition}
	# 				GROUP BY MS.mould_ref,BOMI.item_code,WP.shift_number,DATE(WP.date)
	# 			UNION ALL

	# 				SELECT DISTINCT DATE(AWP.date) date,AWP.shift_number shift,
	# 			ABOMI.item_code AS compound_ref,
	# 			CASE 
	# 				WHEN AMS.wtlift_avg_gms = 0 THEN 0
	# 				ELSE SUM((AMS.wtlift_avg_gms/1000) * AWPIT.target_qty)
	# 			END AS compound_req
				
	# 			FROM `tabAdd On Work Planning` AWP
	# 				INNER JOIN `tabAdd On Work Plan Item` AWPI ON AWPI.parent = AWP.name
	# 				INNER JOIN `tabBOM` AB ON AB.item = AWPI.item
	# 				INNER JOIN `tabBOM Item` ABOMI ON ABOMI.parent = AB.name
	# 				INNER JOIN `tabItem` AI ON AI.name = ABOMI.item_code AND AI.item_group = 'Compound'
	# 				INNER JOIN `tabMould Specification` AMS ON AMS.mould_ref = AWPI.mould
	# 				INNER JOIN `tabWork Plan Item Target` AWPIT ON AWPIT.item = AWPI.item
	# 			WHERE 
	# 				AWP.docstatus = 1 AND 
	# 				CASE 
	# 					WHEN AWPI.bom IS NULL THEN AB.is_default = 1 AND AB.is_active = 1
	# 				ELSE 
	# 					AB.name = AWPI.bom END 
	# 				{acondition}
	# 				GROUP BY AMS.mould_ref,ABOMI.item_code,AWP.shift_number,DATE(AWP.date) 