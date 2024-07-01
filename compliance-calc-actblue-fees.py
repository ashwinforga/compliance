import csv

"""
INSTRUCTIONS:
- Go to "Downloads" and download "Merchant Account Activity" CSV. Filter it manually to fit the right date range.
- Then update the file name and run this script.
"""

# python get-emails.py

# actblue_file = 'ashwin-ramaswami-153140-account_activity_2024-02-01_2024-05-01.csv'
actblue_file = 'ashwin-ramaswami-153140-account_activity_2024-05-01_2024-06-30.csv'

stripe_fees_total = 0
actblue_fees_total = 0

with open(actblue_file, 'r') as f:
    csv_reader = csv.DictReader(f)
    for row in csv_reader:
        if row['Transaction Type'] in ('charge', 'refund', 'dispute'):
            stripe_fees_total += float(row['Stripe Fee Amount'].strip('$'))
            actblue_fees_total += float(row['Actblue Fee Amount'].strip('$'))
        elif 'actblue_fee_credit' in row['Transaction Type']:
            # Actblue refunds the Actblue fee for refunds.
            actblue_fees_total -= float(row['Actblue Fee Amount'].strip('$'))
        else:
            raise Exception(row)

print('stripe_fees_total', '${:.2f}'.format(stripe_fees_total))
print('actblue_fees_total', '${:.2f}'.format(actblue_fees_total))