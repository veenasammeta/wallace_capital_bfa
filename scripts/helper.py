import numpy_financial as npf
import psycopg2
from scripts.report import  generate_combined_report
conn = psycopg2.connect( database="postgres", user='postgres', password='postgres', host='localhost', port= '5432')
dic_summary = {}

def execute_query( query, type):
    with conn.cursor() as cursor:
        cursor.execute(query)
        if type == 'select':
            data = cursor.fetchall()
            return data
    return ''
    
def calculate_combine_income(company_id):
    
    # Total business monthly income
    total_business_monthly_income_query = 'select round(cast(coalesce(avg(netincome)/12, 0.0 ) as numeric),2) business_inc from company_credit_information cci where id = {};'.format(company_id)
    total_business_monthly_income = execute_query(  total_business_monthly_income_query, 'select')  
    total_business_monthly_income = total_business_monthly_income[0][0]
    
    # Total business monthly debt
    total_business_monthly_debt_query = 'select round(cast(coalesce ( sum(monthly_payment), 0.0) as numeric),2) from company_debt_information cdi where id ={};'.format(company_id)
    total_business_monthly_debt = execute_query(  total_business_monthly_debt_query, 'select')  
    total_business_monthly_debt = total_business_monthly_debt[0][0]    
    
    # Total Personal Monthly debt
    total_person_monthly_debt_query = 'select round(cast(coalesce ( sum(monthly_payment), 0.0) as numeric),2) from  person_debt_info pdi  where company_id ={};'.format(company_id)
    total_person_monthly_debt = execute_query(  total_person_monthly_debt_query, 'select')  
    total_person_monthly_debt = total_person_monthly_debt[0][0]   
    
    # Total Personal Income
    total_personal_monthly_income_query = 'select round(cast(sum(agi+ schedulec +k1s +compensation)/12 as numeric),2) from  (select coalesce(avg(agi), 0) agi , coalesce ( avg(schedulec), 0) schedulec , coalesce (avg(k1s), 0) k1s, coalesce (avg(compensation),0) compensation from person_credit_info pci where company_id = {}  group by pid) t;'.format(company_id)
    total_personal_monthly_income = execute_query(  total_personal_monthly_income_query, 'select')  
    total_personal_monthly_income = total_personal_monthly_income[0][0]    
     
    # Gdscr 
    gdscr = (total_business_monthly_income + total_personal_monthly_income) / (total_business_monthly_debt + total_person_monthly_debt)
    gdscr = round(gdscr,2)
    
    # DTI
    if total_personal_monthly_income == 0:
        total_personal_monthly_income = 1
    dti = (total_person_monthly_debt / total_personal_monthly_income ) * 100
    dti = round(dti,2)
    
    # DTO
    dto_query = 'select  coalesce (sum(coalesce(total_owed)),0)/sum(coalesce(credit_limit,1)) *100  from person_debt_info pdi where debt_type= \'revolving\' and company_id= {};'.format(company_id)
    dto = execute_query(  dto_query, 'select')  
    dto = dto[0][0] 
    dto = round(dto,2)
    
    # Capacity
    capacity_query = 'select avg(avg_deposit) - avg(avg_withdraw) capacity from (select cbsi.deposit avg_deposit, cbsi.withdraw avg_withdraw  from company_bank_statement_information cbsi  where id ={} union select pbsi .deposit avg_deposit, pbsi .withdraw avg_withdraw from personal_bank_statement_information pbsi where company_id = {}) t1;'.format(company_id, company_id)
    capacity = execute_query(  capacity_query, 'select')
    capacity = capacity[0][0]
    
    # Balance Avg
    balance_avg_query = 'select avg(avg_balance) from (select cbsi.balance avg_balance  from company_bank_statement_information cbsi  where id = {} union select pbsi .balance avg_balance from personal_bank_statement_information pbsi where company_id = {}) t;'.format(company_id, company_id)
    balance_avg = execute_query(  balance_avg_query, 'select')
    balance_avg = balance_avg[0][0]
    
    # Loan Estimation
    loan_estimate_query = 'select company_id, requested_funds, prime_rate, additional_rate, tenure, estimated_monthly_payment, estimated_gdscr, is_eligible from loan_request_information where company_id = {};'.format(company_id)
    loan_estimate = execute_query(  loan_estimate_query, 'select')
    requested_funds = loan_estimate[0][1]
    prime_rate = loan_estimate[0][2]
    additional_rate = loan_estimate[0][3]
    tenure = loan_estimate[0][4]
    estimated_monthly_payment = loan_estimate[0][5]
    estimated_gdscr = loan_estimate[0][6]
    is_eligible = loan_estimate[0][7]
    
    # Person Data
    persons_query = 'select name, experian ,equifax, transunion  from person p where company_id ={} order  by pid;'.format(company_id)
    persons = execute_query(  persons_query, 'select')
    names_lst = [persons[i][0] for i in range(0,len(persons))]
    ex_lst = [persons[i][1] for i in range(0,len(persons))]
    eu_lst = [persons[i][2] for i in range(0,len(persons))]
    tr_lst = [persons[i][3] for i in range(0,len(persons))]
    
    # Company name
    company_name_query =  'select company_name  from company c where id = {};'.format(company_id)
    company_name = execute_query(  company_name_query, 'select')  
    company_name = company_name[0][0] 
    
    # Result dict preparation   
    dic_summary = {}
    dic_summary['name'] = names_lst
    dic_summary['company'] = company_name
    dic_summary['person_debt'] = total_person_monthly_debt
    dic_summary['business_debt'] = total_business_monthly_debt
    dic_summary['DTO'] = dto
    dic_summary['DTI'] = dti
    dic_summary['GDSCR'] = gdscr
    dic_summary['capacity'] = capacity
    dic_summary['balance'] = balance_avg
    dic_summary['ex'] = ex_lst
    dic_summary['eq'] = eu_lst
    dic_summary['tu'] = tr_lst   
    dic_summary['person_income'] = total_personal_monthly_income
    dic_summary['business_income'] = total_business_monthly_income
    dic_summary['requested_funds'] = requested_funds
    dic_summary['prime_rate'] = prime_rate
    dic_summary['additional_rate'] = additional_rate
    dic_summary['tenure'] = tenure
    dic_summary['estimated_monthly_payment'] = estimated_monthly_payment
    dic_summary['estimated_gdscr'] = estimated_gdscr
    dic_summary['is_eligible'] = is_eligible
    dic_summary['loan_monthly_limit'] = calculate_loan_limit(float(total_personal_monthly_income) + float(total_business_monthly_income), float(total_person_monthly_debt) + float(total_business_monthly_debt))
    path = generate_combined_report(dic_summary) 
    dict_inc = {'total_personal_monthly_income': total_personal_monthly_income, 'total_business_monthly_income': total_business_monthly_income, 'total_person_monthly_debt': total_person_monthly_debt, 'total_business_monthly_debt': total_business_monthly_debt}
    return path, dict_inc

def persondata_to_db(cid, person_dict):
    max_query = 'select coalesce(max(pid),0) from person p'
    max_val = execute_query(   max_query, 'select')
    max_val = max_val[0][0] + 1
    name = person_dict['Name']
    ex = person_dict['Experian']
    eu = person_dict['Equifax']
    tu = person_dict['Transunion']
    person_query = prepare_query("insert into person values ({}, \'{}\', {}, {} , {}, {});commit;", [max_val, name, cid, ex, eu, tu])
    execute_query(  person_query, 'dml')
    max_inc, max_bnk, mort, education, revolv, aut = 1, 1, 1, 1, 1, 1
    for k in person_dict:
        if 'AGI' in k:
            temp = int(k.split('-')[-1])
            if temp > max_inc:
                max_inc = temp

        if 'MortgageOwed' in k:
            temp = int(k.split('-')[-1])
            if temp > mort:
                mort = temp   
                
        if 'RevolvingOwed' in k:
            temp = int(k.split('-')[-1])
            if temp > revolv:
                revolv = temp   
                
        if 'EducationOwed' in k:
            temp = int(k.split('-')[-1])
            if temp > education:
                education = temp  
                
        if 'AutoOwed' in k:
            temp = int(k.split('-')[-1])
            if temp > aut:
                aut = temp                                   
        
        if 'PersonalBankName' in k:
            temp = int(k.split('-')[-1])
            if temp > max_bnk:
                max_bnk = temp      

    for iter in range(1, mort+1):
        MortgageOwed = person_dict['MortgageOwed-' + str(iter)]
        MortgageMonthlypayment = person_dict['MortgageMonthlypayment-' + str(iter)]
        mortage = 'mortage'
        person_mort_query = prepare_query('insert into person_debt_info  values ({},{}, \'{}\', {}, {}, {});commit;', [max_val ,cid, mortage, MortgageOwed, MortgageMonthlypayment ,0])
        execute_query(  person_mort_query, 'dml')
        
    for iter in range(1, revolv+1):
        RevolvingOwed = person_dict['RevolvingOwed-' + str(iter)]
        Revolvingmonthlypayment = person_dict['Revolvingmonthlypayment-' + str(iter)]
        Revolvingcreditlimit = person_dict['Revolvingcreditlimit-' + str(iter)]
        revolving = 'revolving'
        person_revolving_query = prepare_query('insert into person_debt_info  values ({},{}, \'{}\', {}, {}, {});commit;', [max_val ,cid, revolving, RevolvingOwed, Revolvingmonthlypayment ,Revolvingcreditlimit])
        execute_query(  person_revolving_query, 'dml')        
        
    for iter in range(1, aut+1):
        AutoOwed = person_dict['AutoOwed-' + str(iter)]
        Automonthlypayment = person_dict['Automonthlypayment-' + str(iter)]
        auto = 'auto'
        person_auto_query = prepare_query('insert into person_debt_info  values ({},{}, \'{}\', {}, {}, {});commit;', [max_val ,cid, auto, AutoOwed, Automonthlypayment ,0])
        execute_query(  person_auto_query, 'dml')    
        
    for iter in range(1, education+1):
        EducationOwed = person_dict['EducationOwed-' + str(iter)]
        Educationmonthlypayment = person_dict['Educationmonthlypayment-' + str(iter)]
        education = 'education'
        person_education_query = prepare_query('insert into person_debt_info  values ({},{}, \'{}\', {}, {}, {}); commit;', [max_val ,cid, education, EducationOwed, Educationmonthlypayment ,0])
        execute_query(  person_education_query, 'dml')                

    for iter in range(1, max_inc+1):
        creditYear = person_dict['creditYear-' + str(iter)]
        AGI = person_dict['AGI-' + str(iter)]
        ScheduleC = person_dict['ScheduleC-' + str(iter)]
        K1s = person_dict['K-1s-' + str(iter)]
        Compensation = person_dict['Compensation-' + str(iter)]
        Deduction = person_dict['Deduction-' + str(iter)]
        person_inc_query =  prepare_query('insert into person_credit_info values ({}, {}, {}, {} , {}, {}, {}, {});commit;', [max_val, cid, creditYear, AGI, ScheduleC, K1s, Compensation, Deduction])
        execute_query(  person_inc_query, 'dml')                                
        
    for iter in range(1, max_bnk+1):
        pBankStementYear = person_dict['pBankStementYear-' + str(iter)]
        pBankStementMonth = person_dict['pBankStementMonth-' + str(iter)]
        PersonalBankName = person_dict['PersonalBankName-' + str(iter)]
        PLast4Digits = person_dict['PLast4Digits-' + str(iter)]
        pdeposit = person_dict['pdeposit-' + str(iter)]
        pwithdrawal = person_dict['pwithdrawal-' + str(iter)]
        pBalance = person_dict['pBalance-' + str(iter)]
        person_bank_query = prepare_query('insert  into personal_bank_statement_information values ({}, {}, {}, {}, \'{}\', \'{}\', {}, {}, {});commit;', [max_val , cid, pBankStementYear, pBankStementMonth, PersonalBankName, PLast4Digits, pdeposit, pwithdrawal, pBalance])
        execute_query(  person_bank_query, 'dml')                                        
            
def fund_information_to_db(company_id, data_dict, estimated_data):
    RequestedFund = data_dict['RequestedFund']
    PrimeRate = data_dict['PrimeRate']
    AdditionalRate = data_dict['AdditionalRate']
    tenure = data_dict['tenure']
    estimate_monthly_pmt = estimated_data['estimate_monthly_pmt']
    estimate_gdscr = estimated_data['gdscr']
    is_eligible = estimated_data['is_eligible']
    query = prepare_query('insert into loan_request_information values({}, {},{},{}, {}, {}, {}, {});commit;', [company_id, RequestedFund, PrimeRate, AdditionalRate,tenure, estimate_monthly_pmt, estimate_gdscr , is_eligible])
    execute_query(  query, 'dml')

def prepare_query(query, format_list):
    for q in range(len(format_list)):
        if type(format_list[q]) == str and (format_list[q] == None or format_list[q].strip() == ''):
            format_list[q] = 'null'
    query = query.format(*format_list)
    print('QUERY :', query)
    return query

def calculate_loan_limit(monthly_income, monthly_debt):
    max_amnt = monthly_income / 1.25
    loan_limit =  max_amnt - monthly_debt
    return round(loan_limit,2)
        
def estimate_monthly_pmt(interest_rate, number_of_periods, loan_amount):
    interest_rate = (interest_rate/100 )/12
    number_of_periods = number_of_periods * 12
    loan_amount = - loan_amount
    payment = npf.pmt(interest_rate, number_of_periods, loan_amount,0)
    print("Monthly payment: $", round(payment, 2))
    return round(payment, 2)      

def estimate_gdscr(mnt_inc_personal, mnt_inc_business, mnt_deb_personal, mnt_debt_business, pmt):
    gdscr = round((mnt_inc_personal + mnt_inc_business)/( mnt_deb_personal + mnt_debt_business + pmt), 2)
    return gdscr 

def get_total_income_debt_info(company_id):
    
    # Total business monthly income
    total_business_monthly_income_query = 'select coalesce ( avg(netincome)/12, 0 ) business_inc from company_credit_information cci where id = {};'.format(company_id)
    total_business_monthly_income = execute_query(   total_business_monthly_income_query, 'select')  
    total_business_monthly_income = round(total_business_monthly_income[0][0],2)
    
    # Total business monthly debt
    total_business_monthly_debt_query = 'select coalesce ( sum(monthly_payment), 0) from company_debt_information cdi where id ={};'.format(company_id)
    total_business_monthly_debt = execute_query(   total_business_monthly_debt_query, 'select')  
    total_business_monthly_debt = round(total_business_monthly_debt[0][0],2)
    
    # Total Personal Monthly debt
    total_person_monthly_debt_query = 'select coalesce ( sum(monthly_payment), 0) from  person_debt_info pdi  where company_id ={};'.format(company_id)
    total_person_monthly_debt = execute_query(   total_person_monthly_debt_query, 'select')  
    total_person_monthly_debt = round(total_person_monthly_debt[0][0],2)
    # Total Personal Income
    total_personal_monthly_income_query = 'select sum(agi+ schedulec +k1s +compensation)/12 from  (select coalesce(avg(agi), 0) agi , coalesce ( avg(schedulec), 0) schedulec , coalesce (avg(k1s), 0) k1s, coalesce (avg(compensation),0) compensation from person_credit_info pci where company_id = {}  group by pid) t;'.format(company_id)
    total_personal_monthly_income = execute_query(   total_personal_monthly_income_query, 'select')  
    total_personal_monthly_income = round(total_personal_monthly_income[0][0], 2)
    
    inc = {'total_personal_monthly_income':total_personal_monthly_income, 'total_business_monthly_income':total_business_monthly_income, 'total_person_monthly_debt':total_person_monthly_debt, 'total_business_monthly_debt': total_business_monthly_debt}
    return inc

def find_estimates(form_data):
    try:
        tenure = float(form_data['tenure'])
    except Exception as err:
        tenure = 0
    try:
        PrimeRate = float(form_data['PrimeRate'])
    except Exception as err:
        PrimeRate = 0
    try:
        AdditionalRate = float(form_data['AdditionalRate'])
    except Exception as err:
        AdditionalRate = 0                          
            
    est = estimate_monthly_pmt( PrimeRate + AdditionalRate , tenure, float(form_data['RequestedFund']) )
    gdscr = estimate_gdscr(float(form_data['personal_income']), float(form_data['business_income']), float(form_data['total_person_monthly_debt']), float(form_data['total_business_monthly_debt']) , est)
    total_income = float(form_data['personal_income']) + float(form_data['business_income'])
    total_debt = float(form_data['total_person_monthly_debt']) + float(form_data['total_business_monthly_debt'])
    loan_limit = calculate_loan_limit( total_income , total_debt)
    if loan_limit >= est:
        is_eligible = 1
    else:
        is_eligible = 0
    result_data = {'estimate_monthly_pmt': est, 'gdscr': gdscr, 'loan_limit': loan_limit, 'is_eligible': is_eligible}
    return result_data
