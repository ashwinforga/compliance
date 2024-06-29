import csv
import json
from bs4 import BeautifulSoup
import re
from diskcache import Cache
from tqdm import tqdm
from openpyxl import load_workbook
from datetime import datetime, timedelta
import pandas as pd

# From quickbooks
expenditures_file = "Expenses.xls"
vendors_file = "vendor.xls"

# {'selected': nan, 'Date': '12/07/2023', 'Type': 'Expenditure', 'No.': nan, 'Payee': nan, 'Category': 'misc', 'Memo': 'Voided', 'Total': 0.0, 'Action': nan}
expenditures = pd.read_excel(expenditures_file, dtype=str).to_dict(orient='records')

# {'Vendor': 'Zoom', 'Company': 'Zoom', 'Street Address': '55 Almaden Blvd\nSuite600', 'City': 'Almaden', 'State': 'CA', 'Country': 'US', 'Zip': '95113', '1099 Tracking': nan, 'Phone': nan, 'Email': nan, 'Attachments': nan, 'Open Balance': 0}
vendors = pd.read_excel(vendors_file, dtype=str).to_dict(orient='records')

# for expenditure in expenditures:
#     print(dict(expenditure))

LIMIT_DATES = False

def date_between(date, start, end):
    date = datetime.strptime(date, '%m/%d/%Y').date()
    start = datetime.strptime(start, '%m/%d/%Y').date()
    end = datetime.strptime(end, '%m/%d/%Y').date()
    return date >= start and date <= end

# # TODO: what if someone had an unitemized contribution in the past but now it increased their total to be >$100?

payee_dict = {}
for v in vendors:
    payee_dict[v["Vendor"]] = v

payee_dict[""] = {}

all_expenditures = {}
for row in expenditures:
    payee = row["Payee"]
    if type(payee) is float: # nan
        # print(row)
        row["payee"] = ""
        payee = ""
    if row["Category"] == "Reimbursement" or row["Total"] == "0": continue
    assert payee in payee_dict, row
    if payee not in all_expenditures: all_expenditures[payee] = []
    all_expenditures[payee].append(row)

def date_before_primary(date):
    return date_between(date, "12/01/2023", "05/21/2024")

# print(len(all_expenditures))

EXP_HEADERS = ["expenditureID", "exElectionType", "exElectionDate", "exExpenditureType", "exPayeeType", "exPaymentCode", "exPaymentCodeOther", "exOrgID", "exPayeeID", "exOrgName", "exFilerID", "exFirstName", "exMiddleName", "exLastName", "exNameSuffix", "exAddress1", "exAddress2", "exCity", "exState", "exZip", "exEmployer", "exOccupation", "exOccupationOther", "exCreditCardIssuedTo", "exDate", "exAmount", "exExplanation", "exCheckNumber", "exSuppOppCan", "exSuppOppBQ", "AmendFlag", "DeleteFlag"]

# {'selected': nan, 'Date': '12/07/2023', 'Type': 'Expenditure', 'No.': nan, 'Payee': nan, 'Category': 'misc', 'Memo': 'Voided', 'Total': 0.0, 'Action': nan}
rows = []
i = 0
for contact_id, expenditures in all_expenditures.items():
    total_individual_expenditures = sum(float(c["Total"]) for c in expenditures)
    if total_individual_expenditures < 100:
        for expenditure in expenditures:
            i += 1
            row = {
                "expenditureID": "exp-4_31_" + str(i),
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
        expenditures = all_expenditures[contact_id]
        for expenditure in expenditures:
            i += 1
            payee = expenditure["Payee"]
            vendor = payee_dict[payee]
            row = {
                "expenditureID": "exp-4_31_" + str(i),
                "exElectionType": "P" if date_before_primary(expenditure["Date"]) else "G",
                "exElectionDate": "05/21/2024" if date_before_primary(expenditure["Date"]) else "11/05/2024",
                "exExpenditureType": "MOI", # MOI - itemized.
                "exPaymentCode": "OTH",
                "exPaymentCodeOther": expenditure["Memo"],
                "exDate": expenditure["Date"],
                "exAmount": str(expenditure["Total"]),
                "exPayeeID": "payee-4_31_" + str(i),
                # "exExplanation": expenditure["Memo"],
                "exAddress1": vendor["Street Address"],
                "exCity": vendor["City"],
                "exState": vendor["State"],
                "exZip": vendor["Zip"]
            }
            if vendor["Company"] and type(vendor["Company"]) is not float:
                row["exPayeeType"] = "OTH"
                row["exOrgName"] = payee
            else:
                row["exPayeeType"] = "IND"
                assert " " in payee, payee
                split = payee.split()
                row["exFirstName"] = split[0]
                row["exLastName"] = split[-1]
            print(row)
            for k, v in row.items():
                assert v.strip() != "", (k, v)
            rows.append(row)

total = sum(float(r["exAmount"]) for r in rows)
print("total should be", 282495, "total is", total)

print(sum(float(r["exAmount"]) for r in rows if date_between(r["exDate"], "12/01/2023", "01/31/2024")))

print("1/31 itemized", sum(float(r["exAmount"]) for r in rows if r["exExpenditureType"] == "MOI" and date_between(r["exDate"], "12/01/2023", "01/31/2024")))
print("1/31 non-itemized", sum(float(r["exAmount"]) for r in rows if r["exExpenditureType"] == "NIM" and date_between(r["exDate"], "12/01/2023", "01/31/2024")))

print("4/30 itemized", sum(float(r["exAmount"]) for r in rows if r["exExpenditureType"] == "MOI" and date_between(r["exDate"], "02/01/2024", "04/30/2024")))
print("4/30 non-itemized", sum(float(r["exAmount"]) for r in rows if r["exExpenditureType"] == "NIM" and date_between(r["exDate"], "02/01/2024", "04/30/2024")))

print("expenditures 4/30", sum(float(r["exAmount"]) for r in rows if date_between(r["exDate"], "02/01/2024", "04/30/2024")))

146303

rows.sort(key = lambda r: r["exDate"])

with open('expenditures.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=EXP_HEADERS)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

with open('expenditures-jan31.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=EXP_HEADERS)
    writer.writeheader()
    for r in rows:
        if date_between(r["exDate"], "12/01/2023", "01/31/2024"):
            writer.writerow(r)

with open('expenditures-apr30.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=EXP_HEADERS)
    writer.writeheader()
    for r in rows:
        if date_between(r["exDate"], "02/01/2024", "04/30/2024"):
            writer.writerow(r)

with open('expenditures-jun30.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=EXP_HEADERS)
    writer.writeheader()
    for r in rows:
        if date_between(r["exDate"], "05/01/2024", "06/30/2024"):
            writer.writerow(r)
