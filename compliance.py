import csv
import json
from bs4 import BeautifulSoup
import re
from diskcache import Cache
from tqdm import tqdm
from openpyxl import load_workbook
from datetime import datetime, timedelta

# python get-emails.py

numero_contributions_file = 'all-contributions.csv'
out_file = "Apr30.xlsx"

LIMIT_DATES = False

def date_between(date, start, end):
    date = datetime.strptime(date, '%m/%d/%Y').date()
    start = datetime.strptime(start, '%m/%d/%Y').date()
    end = datetime.strptime(end, '%m/%d/%Y').date()
    return date >= start and date <= end

# # TODO: what if someone had an unitemized contribution in the past but now it increased their total to be >$100?

all_contributions = {}

# format_date = lambda x: x.split()[0]

def format_date(datestr):
    date = (datetime.strptime(datestr, '%m/%d/%Y %I:%M %p') + timedelta(hours=3)).date()
    return date.strftime("%m/%d/%Y")

assert format_date("12/31/2024 11:59 PM") == "01/01/2025"
assert format_date("12/31/2024 8:59 PM") == "12/31/2024"
assert format_date("12/31/2024 10:00 AM") == "12/31/2024"

with open(numero_contributions_file, 'r') as f:
    csv_reader = csv.DictReader(f)
    for row in csv_reader:
        contact_id = row["Contact ID"]
        if row["Status"] == "refunded":
            # TODO later: handle refunds when relevant.
            continue
        row["Date"] = format_date(row["Date"])
        # if LIMIT_DATES and not date_between(row["Date"], "12/01/2023", "01/31/2024"):
        #     continue
        if contact_id not in all_contributions: all_contributions[contact_id] = []
        all_contributions[contact_id].append(row)
        pass

# print(len(all_contributions))

CONTRIB_HEADERS = ["contributionID", "cbElectionType", "cbElectionDate", "cbContributionType", "cbContributionCode", "cbOrgID", "cbOrgName", "cbFilerID", "cbContributorID", "cbFirstName", "cbMiddleName", "cbLastName", "cbNameSuffix", "cbAddress1", "cbAddress2", "cbCity", "cbState", "cbZip", "cbEmployer", "cbOccupation", "cbOccupationOther", "cbAffiliatedCommittee", "cbDate", "cbAmount", "cbDescription", "cbCheckNumber", "cbRegulatedEntityName", "AmendFlag", "DeleteFlag"]

# ["Contribution ID", "Date", "Amount", "Contact ID", "Contact Type", "Title", "First Name", "Middle Name", "Last Name", "Suffix", "Salutation", "Email", "Phone", "Address Line 1", "Address Line 2", "City", "State", "Zip", "County", "Country", "Employer", "Occupation", "Contact VANID", "Receipt First Name", "Receipt Last Name", "Receipt Line 1", "Receipt City", "Receipt State", "Receipt Zip", "Receipt Country", "Receipt Email", "Receipt Phone", "Receipt Employer", "Receipt Occupation", "Receipt Responsible Party First Name", "Receipt Responsible Party Last Name", "Payment Method", "Recurring", "Contribution Form", "External Form", "Designation", "Batch", "Source Code", "Member Code", "Reference Codes", "Calltime List", "Integration", "Raiser", "Status", "Notes", "Created Date", "Pledge", "Soft Credits"]
rows = []
for contact_id, contributions in all_contributions.items():
    total_individual_contributions = sum(float(c["Amount"]) for c in contributions)
    if total_individual_contributions < 100:
        for contribution in contributions:
            row = {
                "contributionID": "numero-" + contribution["Contribution ID"] + "-" + "P",
                "cbElectionType": "P",
                "cbElectionDate": "05/21/2024", # 11/05/2024
                "cbContributionType": "NIM", # NIM - non-itemized.
                "cbDate": contribution["Date"],
                "cbAmount": contribution["Amount"]
            }
            for k, v in row.items():
                assert v.strip() != ""
            rows.append(row)
    else:
        if total_individual_contributions > 3300 and not (contributions[0]["First Name"].lower() == "ashwin" and contributions[0]["Last Name"].lower() == "ramaswami"):
            new_contributions = []
            total_in_primary = 0
            for i in range(0, len(contributions)):
                amount = float(contributions[i].pop("Amount"))
                if total_in_primary + amount <= 3300:
                    # All in primary
                    total_in_primary += amount
                    new_contributions.append(
                        dict(**contributions[i], Amount=str(amount), election_type="P", election_date="05/21/2024")
                    )
                elif total_in_primary < 3300 and total_in_primary + amount > 3300:
                    # Split
                    amount_in_primary = 3300 - total_in_primary
                    amount_in_general = amount - amount_in_primary
                    total_in_primary += amount_in_primary
                    new_contributions.append(
                        dict(**contributions[i], Amount=str(amount_in_primary), election_type="P", election_date="05/21/2024")
                    )
                    new_contributions.append(
                        dict(**contributions[i], Amount=str(amount_in_general), election_type="G", election_date="11/05/2024")
                    )
                else:
                    # All in general
                    new_contributions.append(
                        dict(**contributions[i], Amount=str(amount), election_type="G", election_date="11/05/2024")
                    )
            all_contributions[contact_id] = new_contributions
        
        contributions = all_contributions[contact_id]
        for contribution in contributions:
            row = {
                "contributionID": "numero-" + contribution["Contribution ID"] + "-" + contribution.get("election_type", "P"),
                "cbElectionType": contribution.get("election_type", "P"),
                "cbElectionDate": contribution.get("election_date", "05/21/2024"), # 11/05/2024
                "cbContributorID": "numero-" + contribution["Contact ID"],
                "cbAddress1": contribution["Address Line 1"],
                "cbCity": contribution["City"],
                "cbState": contribution["State"],
                "cbZip": contribution["Zip"],
                "cbDate": contribution["Date"],
                "cbAmount": contribution["Amount"]
            }
            if contribution["Payment Method"] == "InKind":
                row["cbContributionType"] = "IKD" # In-kind
                row["cbDescription"] = contribution["Notes"]
            else:
                row["cbContributionType"] = "MOI" # MOI - itemized.
            
            if contribution["Contact Type"] == "Individual":
                row["cbContributionCode"] = "IND"
                row["cbFirstName"] = contribution["First Name"]
                row["cbLastName"] = contribution["Last Name"]
                row["cbEmployer"] = contribution["Employer"]
                row["cbOccupation"] = "597"
                row["cbOccupationOther"] = contribution["Occupation"]
                if contribution["First Name"].lower() == "ashwin" and contribution["Last Name"].lower() == "ramaswami":
                    row["cbContributionCode"] = "SELF" # SELF - candidate.
            else:
                row["cbContributionCode"] = "OTH" # COM - committee, OTH - other. TODO
                row["cbOrgName"] = contribution["First Name"]
            for k, v in row.items():
                assert v.strip() != "", (contribution["First Name"], k, v)
            rows.append(row)

total = sum(float(r["cbAmount"]) for r in rows)
print("total should be", 282495, "total is", total)

print(sum(float(r["cbAmount"]) for r in rows if date_between(r["cbDate"], "12/01/2023", "01/31/2024")))

print(sum(float(r["cbAmount"]) for r in rows if r["cbContributionType"] == "MOI" and date_between(r["cbDate"], "12/01/2023", "01/31/2024")))
print(sum(float(r["cbAmount"]) for r in rows if r["cbContributionType"] == "NIM" and date_between(r["cbDate"], "12/01/2023", "01/31/2024")))

print(sum(float(r["cbAmount"]) for r in rows if date_between(r["cbDate"], "02/01/2024", "04/30/2024")))

146303

rows.sort(key = lambda r: r["cbDate"])

with open('contributions.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=CONTRIB_HEADERS)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

with open('contributions-jan31.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=CONTRIB_HEADERS)
    writer.writeheader()
    for r in rows:
        if date_between(r["cbDate"], "12/01/2023", "01/31/2024"):
            writer.writerow(r)

with open('contributions-apr30.csv', 'w+') as f:
    writer = csv.DictWriter(f, fieldnames=CONTRIB_HEADERS)
    writer.writeheader()
    for r in rows:
        if date_between(r["cbDate"], "02/01/2024", "04/30/2024"):
            writer.writerow(r)

# with open('report.json', 'w+') as out_file:
#     print("total", len(known)) 
#     for source_name in SOURCES:
#         print(source_name, len([k for k in known if source_name in known[k]]))
#     json.dump({
#         "len": len(known),
#         "known": known
#     }, out_file)