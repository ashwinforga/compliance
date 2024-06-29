import csv
from datetime import datetime, timedelta

numero_contributions_file = 'all-contributions.csv'
CONTRIB_HEADERS = ["contributionID", "cbElectionType", "cbElectionDate", "cbContributionType", "cbContributionCode", "cbOrgID", "cbOrgName", "cbFilerID", "cbContributorID", "cbFirstName", "cbMiddleName", "cbLastName", "cbNameSuffix", "cbAddress1", "cbAddress2", "cbCity", "cbState", "cbZip", "cbEmployer", "cbOccupation", "cbOccupationOther", "cbAffiliatedCommittee", "cbDate", "cbAmount", "cbDescription", "cbCheckNumber", "cbRegulatedEntityName", "AmendFlag", "DeleteFlag"]

def date_between(date, start, end):
    date = datetime.strptime(date, '%m/%d/%Y').date()
    start = datetime.strptime(start, '%m/%d/%Y').date()
    end = datetime.strptime(end, '%m/%d/%Y').date()
    return date >= start and date <= end

def format_date(datestr):
    # Numero timestamps are in PST, so we have to convert to EST before getting the date.
    date = (datetime.strptime(datestr, '%m/%d/%Y %I:%M %p') + timedelta(hours=3)).date()
    return date.strftime("%m/%d/%Y")

def date_before_primary(date):
    return date_between(date, "12/01/2023", "05/21/2024")

assert format_date("12/31/2024 11:59 PM") == "01/01/2025"
assert format_date("12/31/2024 8:59 PM") == "12/31/2024"
assert format_date("12/31/2024 10:00 AM") == "12/31/2024"

# format_date = lambda x: x.split()[0]

def generate_report(start_date, end_date):
    all_contributions = {}
    with open(numero_contributions_file, 'r') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            contact_id = row["Contact ID"]
            if row["Status"] == "refunded":
                # TODO later: handle refunds when relevant.
                continue
            row["Date"] = format_date(row["Date"])
            if not date_between(row["Date"], start_date, end_date):
                continue
            if contact_id not in all_contributions: all_contributions[contact_id] = []
            all_contributions[contact_id].append(row)

    # print(len(all_contributions))

    # ["Contribution ID", "Date", "Amount", "Contact ID", "Contact Type", "Title", "First Name", "Middle Name", "Last Name", "Suffix", "Salutation", "Email", "Phone", "Address Line 1", "Address Line 2", "City", "State", "Zip", "County", "Country", "Employer", "Occupation", "Contact VANID", "Receipt First Name", "Receipt Last Name", "Receipt Line 1", "Receipt City", "Receipt State", "Receipt Zip", "Receipt Country", "Receipt Email", "Receipt Phone", "Receipt Employer", "Receipt Occupation", "Receipt Responsible Party First Name", "Receipt Responsible Party Last Name", "Payment Method", "Recurring", "Contribution Form", "External Form", "Designation", "Batch", "Source Code", "Member Code", "Reference Codes", "Calltime List", "Integration", "Raiser", "Status", "Notes", "Created Date", "Pledge", "Soft Credits"]
    rows = []
    for contact_id, contributions in all_contributions.items():
        # print(contributions)
        total_individual_contributions = sum(float(c["Amount"]) for c in contributions)
        if total_individual_contributions < 100 and not any(c["Payment Method"] == "InKind" for c in contributions):
            for contribution in contributions:
                row = {
                    "contributionID": "numero-" + contribution["Contribution ID"] + "-" + "P",
                    "cbElectionType": "P" if date_before_primary(contribution["Date"]) else "G",
                    "cbElectionDate": "05/21/2024" if date_before_primary(contribution["Date"]) else "11/05/2024",
                    "cbContributionType": "NIM", # NIM - non-itemized.
                    "cbDate": contribution["Date"],
                    "cbAmount": contribution["Amount"]
                }
                for k, v in row.items():
                    assert v.strip() != ""
                rows.append(row)
        else:
            contributions = all_contributions[contact_id]
            if total_individual_contributions > 3300 and not (contributions[0]["First Name"].lower() == "ashwin" and contributions[0]["Last Name"].lower() == "ramaswami"):
                new_contributions = []
                total_in_primary = 0
                for i in range(0, len(contributions)):
                    if not date_before_primary(contributions[i]["Date"]):
                        # Contribution happened in general election timeline.
                        new_contributions.append(contributions[i])
                        continue
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
                contributions = new_contributions
            
            for contribution in contributions:
                election_type = contribution.get("election_type", "P" if date_before_primary(contribution["Date"]) else "G")
                election_date = contribution.get("election_date", "05/21/2024" if date_before_primary(contribution["Date"]) else "11/05/2024")
                row = {
                    "contributionID": "numero-" + contribution["Contribution ID"] + "-" + election_type,
                    "cbElectionType": election_type,
                    "cbElectionDate": election_date,
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
                    assert v.strip() != "", (contribution, k, v)
                rows.append(row)


    rows.sort(key = lambda r: r["contributionID"])

    return rows

def filter_rows(rows, start_date, end_date):
    return [r for r in rows if date_between(r["cbDate"], start_date, end_date)]

def write_to_file(rows, name):
    with open(f'contributions-{name}.csv', 'w+') as f:
        writer = csv.DictWriter(f, fieldnames=CONTRIB_HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def generate_report_for_reporting_period(start_date, end_date, name):
    rows = filter_rows(generate_report("12/01/2023", end_date), start_date, end_date)
    up_to_date_rows = filter_rows(generate_report("12/01/2023", "12/31/2024"), start_date, end_date)
    set1 = list(r["contributionID"] for r in rows)
    set2 = list(r["contributionID"] for r in up_to_date_rows)
    assert set1 == set2
    rows_to_update = []
    for i in range(0, len(rows)):
        assert up_to_date_rows[i]["contributionID"] == rows[i]["contributionID"]
        if rows[i]["cbContributionType"] == "NIM" and up_to_date_rows[i]["cbContributionType"] == "MOI":
            up_to_date_rows[i]["AmendFlag"] = "A"
            rows_to_update.append(up_to_date_rows[i])
    write_to_file(rows, name)
    write_to_file(rows_to_update, name + "-to-amend")
    


generate_report_for_reporting_period("12/01/2023", "01/31/2024", "jan31")
generate_report_for_reporting_period("02/01/2024", "04/30/2024", "apr30")
generate_report_for_reporting_period("05/01/2024", "06/30/2024", "jun30")

