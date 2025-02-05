import frappe

def get_query_condition(user,doctype_):
    if not user : user = frappe.session.user
    roles = frappe.get_roles(user)
    if "System Manager" in roles:
        return None
    elif "U3 Supervisor" in roles:
        user_list = frappe.db.sql(f" SELECT parent FROM `tabHas Role` WHERE role IN ('Blanker','Mill Operator','Batch Operator') AND parenttype = 'User' ",as_dict = 1)
        if user_list:
            condt = f"('{user}',"
            for usr in user_list:
                condt += f"'{usr.parent}',"
            condt = condt[:-1]
            condt += ")"
            return f"(`tab{doctype_}`.owner IN {condt})"
        else:
            return f"(`tab{doctype_}`.owner = '{user}')"
    elif "U2 Supervisor" in roles:
        user_list = frappe.db.sql(f""" SELECT parent FROM `tabHas Role` WHERE role IN 
                                        ('Production Executive ','Quality Executive','Line Inspector','Lot Inspector',
                                        'Incoming Inspector','Despatcher','Packer','Compound Inspector') AND parenttype = 'User' """,as_dict = 1)
        if user_list:
            condt = f"('{user}',"
            for usr in user_list:
                condt += f"'{usr.parent}',"
            condt = condt[:-1]
            condt += ")"
            return f"(`tab{doctype_}`.owner IN {condt})"
        else:
            return f"(`tab{doctype_}`.owner = '{user}')"
    elif "U1 Supervisor" in roles:
        user_list = frappe.db.sql(f""" SELECT parent FROM `tabHas Role` WHERE role IN 
                                        ('Packer') AND parenttype = 'User' """,as_dict = 1)
        if user_list:
            condt = f"('{user}',"
            for usr in user_list:
                condt += f"'{usr.parent}',"
            condt = condt[:-1]
            condt += ")"
            return f"(`tab{doctype_}`.owner IN {condt})"
        else:
            return f"(`tab{doctype_}`.owner = '{user}')"
 
def get_filter_berp(user):
    return get_query_condition(user,"Batch ERP Entry")
        
def get_filter_se(user):
    return get_query_condition(user,"Stock Entry")

def get_filter_mt(user):
    return get_query_condition(user,"Material Transfer")

def get_filter_dcr(user):
    return get_query_condition(user,"Delivery Challan Receipt")

def get_filter_dn(user):
    return get_query_condition(user,"Delivery Note")

def get_filter_wo(user):
    return get_query_condition(user,"Work Order")

def get_filter_jc(user):
    return get_query_condition(user,"Job Card")

def get_filter_cbt(user):
    return get_query_condition(user,"Cut Bit Transfer")

def get_filter_bcr(user):
    return get_query_condition(user,"Bulk Clip Release")

def get_filter_bdce(user):
    return get_query_condition(user,"Blanking DC Entry")

def get_filter_mv(user):
    return get_query_condition(user,"Bin Movement")

def get_filter_amv(user):
    return get_query_condition(user,"Asset Movement")

def get_filter_wrkp(user):
    return get_query_condition(user,"Work Planning")

def get_filter_awrkp(user):
    return get_query_condition(user,"Add On Work Planning")

def get_filter_bbissue(user):
    return get_query_condition(user,"Blank Bin Issue")

def get_filter_moupe(user):
    return get_query_condition(user,"Moulding Production Entry")

def get_filter_sublc(user):
    return get_query_condition(user,"Sub Lot Creation")

def get_filter_dede(user):
    return get_query_condition(user,"Deflashing Despatch Entry")

def get_filter_drepe(user):
    return get_query_condition(user,"Deflashing Receipt Entry")

def get_filter_deu1e(user):
    return get_query_condition(user,"Despatch To U1 Entry")

def get_filter_loet(user):
    return get_query_condition(user,"Lot Resource Tagging")

def get_filter_bbnre(user):
    return get_query_condition(user,"Blank Bin Rejection Entry")

def get_filter_inspe(user):
    return get_query_condition(user,"Inspection Entry")

def get_filter_bilg(user):
    return get_query_condition(user,"Billing")

def get_filter_pack(user):
    return get_query_condition(user,"Packing")

def get_filter_qcins(user):
    return get_query_condition(user,"Quality Inspection")

def get_filter_cmins(user):
    return get_query_condition(user,"Compound Inspection")