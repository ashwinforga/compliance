import csv
from datetime import datetime, timedelta
import pandas as pd

"""
Instructions:
- Export expenditures, vendors from QuickBooks
- Ensure company names are filled out for vendors in QuickBooks, all addresses are filled out
"""

"""
Update itemized status based on later expenditures
"""


# From quickbooks
expenditures_file = "Expenses.xls"
vendors_file = "Vendors.xls"

LIMIT_DATES = False

def date_between(date, start, end):
    date = datetime.strptime(date, '%m/%d/%Y').date()
    start = datetime.strptime(start, '%m/%d/%Y').date()
    end = datetime.strptime(end, '%m/%d/%Y').date()
    return date >= start and date <= end

def date_before_primary(date):
    return date_between(date, "12/01/2023", "05/21/2024")


EXP_HEADERS = ["expenditureID", "exElectionType", "exElectionDate", "exExpenditureType", "exPayeeType", "exPaymentCode", "exPaymentCodeOther", "exOrgID", "exPayeeID", "exOrgName", "exFilerID", "exFirstName", "exMiddleName", "exLastName", "exNameSuffix", "exAddress1", "exAddress2", "exCity", "exState", "exZip", "exEmployer", "exOccupation", "exOccupationOther", "exCreditCardIssuedTo", "exDate", "exAmount", "exExplanation", "exCheckNumber", "exSuppOppCan", "exSuppOppBQ", "AmendFlag", "DeleteFlag"]

def generate_report(start_date, end_date):
    
    # {'selected': nan, 'Date': '12/07/2023', 'Type': 'Expenditure', 'No.': nan, 'Payee': nan, 'Category': 'misc', 'Memo': 'Voided', 'Total': 0.0, 'Action': nan}
    expenditures = pd.read_excel(expenditures_file, dtype=str)
    expenditures['dttime'] = pd.to_datetime(expenditures['Date'], format='%m/%d/%Y')
    expenditures = expenditures.sort_values(by='dttime')
    expenditures = expenditures.to_dict(orient='records')

    # {'Vendor': 'Zoom', 'Company': 'Zoom', 'Street Address': '55 Almaden Blvd\nSuite600', 'City': 'Almaden', 'State': 'CA', 'Country': 'US', 'Zip': '95113', '1099 Tracking': nan, 'Phone': nan, 'Email': nan, 'Attachments': nan, 'Open Balance': 0}
    vendors = pd.read_excel(vendors_file, dtype=str).to_dict(orient='records')
    
    payee_dict = {}
    for v in vendors:
        payee_dict[v["Vendor"]] = v

    payee_dict[""] = {}
    
    all_expenditures = {}
    i = 0
    for row in expenditures:
        row["id"] = str(i)
        payee = row["Payee"]
        if type(payee) is float: # nan
            row["payee"] = ""
            payee = ""
        if row["Category"] == "Reimbursement" or row["Total"] == "0": continue
        assert payee in payee_dict, row
        if not date_between(row["Date"], start_date, end_date):
            continue
        if payee not in all_expenditures: all_expenditures[payee] = []
        # print(row)
        all_expenditures[payee].append(row)
        i += 1

    rows = []
    for contact_id, expenditures in all_expenditures.items():
        total_individual_expenditures = sum(float(c["Total"]) for c in expenditures)
        if total_individual_expenditures < 100:
            for expenditure in expenditures:
                # print(row)
                row = {
                    "expenditureID": "exp-" + expenditure["id"],
                    "exElectionType": "P" if date_before_primary(expenditure["Date"]) else "G",
                    "exElectionDate": "05/21/2024" if date_before_primary(expenditure["Date"]) else "11/05/2024",
                    "exExpenditureType": "NIM", # NIM - non-itemized.
                    "exPaymentCode": "OTH", 
                    "exPaymentCodeOther": expenditure["Memo"],
                    "exDate": expenditure["Date"],
                    "exAmount": str(expenditure["Total"]),
                    # "exExplanation": ""
                }
                for k, v in row.items():
                    assert v.strip() != ""
                rows.append(row)
        else:
            for expenditure in expenditures:
                payee = expenditure["Payee"]
                vendor = payee_dict[payee]
                row = {
                    "expenditureID": "exp-" + expenditure["id"],
                    "exElectionType": "P" if date_before_primary(expenditure["Date"]) else "G",
                    "exElectionDate": "05/21/2024" if date_before_primary(expenditure["Date"]) else "11/05/2024",
                    "exExpenditureType": "MOI", # MOI - itemized.
                    "exPaymentCode": "OTH",
                    "exPaymentCodeOther": expenditure["Memo"],
                    "exDate": expenditure["Date"],
                    "exAmount": str(expenditure["Total"]),
                    "exPayeeID": "payee-" + expenditure["id"],
                    # "exExplanation": expenditure["Memo"],
                    "exAddress1": vendor["Street Address"],
                    "exCity": vendor["City"],
                    "exState": vendor["State"],
                    "exZip": vendor["Zip"]
                }
                if vendor["Company name"] and type(vendor["Company name"]) is not float:
                    row["exPayeeType"] = "OTH"
                    row["exOrgName"] = payee
                else:
                    row["exPayeeType"] = "IND"
                    assert " " in payee, payee
                    split = payee.split()
                    row["exFirstName"] = split[0]
                    row["exLastName"] = split[-1]
                # print(row)
                for k, v in row.items():
                    assert v.strip() != "", (k, v)
                rows.append(row)

    rows.sort(key = lambda r: r["exDate"])
    
    return rows


def filter_rows(rows, start_date, end_date):
    return [r for r in rows if date_between(r["exDate"], start_date, end_date)]

def write_to_file(rows, name):
    with open(f'expenditures-{name}.csv', 'w+') as f:
        writer = csv.DictWriter(f, fieldnames=EXP_HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def generate_report_for_reporting_period(start_date, end_date, name):
    rows = filter_rows(generate_report("12/01/2023", end_date), start_date, end_date)
    up_to_date_rows = filter_rows(generate_report("12/01/2023", "12/31/2024"), start_date, end_date)
    set1 = list(r["expenditureID"] for r in rows)
    set2 = list(r["expenditureID"] for r in up_to_date_rows)
    assert set1 == set2
    rows_to_update = []
    for i in range(0, len(rows)):
        assert up_to_date_rows[i]["expenditureID"] == rows[i]["expenditureID"]
        if rows[i]["exExpenditureType"] == "NIM" and up_to_date_rows[i]["exExpenditureType"] == "MOI":
            up_to_date_rows[i]["AmendFlag"] = "A"
            rows_to_update.append(up_to_date_rows[i])
    write_to_file(rows, name)
    write_to_file(rows_to_update, name + "-to-amend")
    


generate_report_for_reporting_period("12/01/2023", "01/31/2024", "jan31")
generate_report_for_reporting_period("02/01/2024", "04/30/2024", "apr30")
generate_report_for_reporting_period("05/01/2024", "06/30/2024", "jun30")
generate_report_for_reporting_period("07/01/2024", "09/30/2024", "sep30")
generate_report_for_reporting_period("10/01/2024", "10/25/2024", "oct25")
generate_report_for_reporting_period("10/26/2024", "12/31/2024", "dec31")
