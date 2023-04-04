import os
from flask import Flask, render_template, request, session, send_file
from scripts.helper import prepare_query, find_estimates, get_total_income_debt_info, execute_query, persondata_to_db, fund_information_to_db, calculate_combine_income

app = Flask(__name__)
app.secret_key = "wallace123"
result_data = {'estimate_monthly_pmt': '', 'gdscr': '', 'loan_limit': None}
@app.route("/")
def home():
    return render_template('bfa_home.html')


@app.route("/request_funds", methods=["GET", "POST"])
def request_funds():
    if request.method == "POST": 
        form_data =  request.form.to_dict()
        if 'Generate' in request.form:
            company_id = session['company_id']
            estimated_data = find_estimates(form_data)
            company_id = session['company_id'] 
            fund_information_to_db(company_id, form_data, estimated_data)
            file_path_combined, analysis_dict = calculate_combine_income(company_id)
            session["file_path_combined"] = file_path_combined
            return render_template('outputCalc.html')
        
        analysis_dict = {'total_personal_monthly_income': form_data['personal_income'], 'total_business_monthly_income': form_data['business_income'], 'total_person_monthly_debt': form_data['total_person_monthly_debt'], 'total_business_monthly_debt': form_data['total_business_monthly_debt'] }
        result_data = find_estimates(form_data)
        print(result_data)
        return render_template('request_funds.html',  form_data=form_data, analysis_dict=analysis_dict, result_data=result_data)
    return render_template('request_funds.html', form_data='', analysis_dict='', result_data = result_data)


@app.route("/CombinedReportdownload")
def download_combined_file():
    file_path_combined = session.get("file_path_combined", None)   
    return send_file(file_path_combined, as_attachment=True)


@app.route("/page", methods=["GET", "POST"])
def page():
     result_data = {'estimate_monthly_pmt': None, 'gdscr': None, 'loan_limit': None, 'is_eligible': None}
     if request.method == "POST":  
        if 'AddAPerson' in request.form:
            company_id = session['company_id']
            persondata_to_db(company_id, request.form.to_dict())
            return render_template('person.html')
        if 'Next' in request.form:
            company_id = session['company_id']
            persondata_to_db(company_id, request.form.to_dict())
            analysis_dict = get_total_income_debt_info(company_id)
            print(result_data)
            return render_template('request_funds.html', analysis_dict = analysis_dict, form_data=None, result_data = result_data)
     return render_template('person.html')

@app.route("/company", methods=["GET", "POST"])
def company():
    if request.method == "POST":  
        form_data = request.form.to_dict()
        company = request.form['CompanyName']
        max_query = 'select coalesce(max(id),0) from company c'
        max_val = execute_query(  max_query, 'select')
        max_val = max_val[0][0] + 1
        company_query = prepare_query('insert into company values ({},\'{}\');commit;', [max_val, company])
        execute_query( company_query, 'dml')
        max_debt, max_inc, max_bnk = 1, 1, 1
        for k in form_data:
            if 'BusinessDebtType' in k:
                temp = int(k.split('-')[-1])
                if temp > max_debt:
                    max_debt = temp

            if 'GrossRevenue' in k:
                temp = int(k.split('-')[-1])
                if temp > max_inc:
                    max_inc = temp   
                                     
            if 'bBankStementYear' in k:
                temp = int(k.split('-')[-1])
                if temp > max_bnk:
                    max_bnk = temp                                          
        for iter in range(1, max_debt+1):
            BusinessDebtType = form_data['BusinessDebtType-' + str(iter)]
            BTotalowed = form_data['BTotalowed-' + str(iter)]
            BusinessMonthlypayment = form_data['BusinessMonthlypayment-' + str(iter)]
            company_debt_query =  prepare_query('insert into company_debt_information  values ({},\'{}\', {}, {});commit;', [max_val, BusinessDebtType, BTotalowed, BusinessMonthlypayment])
            execute_query( company_debt_query, 'dml')
            
        for iter in range(1, max_inc+1):
            businessIncomeYear = form_data['businessIncomeYear-' + str(iter)]
            Depreciation = form_data['Depreciation-' + str(iter)]
            GrossRevenue = form_data['GrossRevenue-' + str(iter)]
            Interest = form_data['Interest-'+ str(iter)]
            NetIncome = form_data['NetIncome-'+ str(iter)]
            company_income_query = prepare_query('insert into company_credit_information  values({}, {}, {}, {}, {}, {});commit;', [max_val, businessIncomeYear, GrossRevenue, NetIncome, Depreciation, Interest])
            execute_query(  company_income_query, 'dml')
        
        for iter in range(1, max_bnk+1):
            BBalance = form_data['BBalance-' + str(iter)]
            Bdeposit = form_data['Bdeposit-' + str(iter)]
            BusinessBankName = form_data['BusinessBankName-' + str(iter)]
            Bwithdrawal = form_data['Bwithdrawal-' + str(iter)]
            Last4Digits = form_data['Last4Digits-' + str(iter)]
            bBankStementMonth = form_data['bBankStementMonth-' + str(iter)]
            bBankStementYear = form_data['bBankStementYear-' + str(iter)]
            company_bnk_stmnt_query = prepare_query('insert into company_bank_statement_information values({}, {}, {}, \'{}\' , \'{}\', {}, {}, {});commit;', [max_val, bBankStementYear, bBankStementMonth, BusinessBankName, Last4Digits, Bdeposit, Bwithdrawal, BBalance ])
            execute_query(  company_bnk_stmnt_query, 'dml')
        session['company_id'] = max_val
        return render_template('person.html')
    return render_template('person.html')
    
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
