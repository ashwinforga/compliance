import csv
import json
from bs4 import BeautifulSoup
import re
from diskcache import Cache
from tqdm import tqdm
from openpyxl import load_workbook
from datetime import datetime, timedelta

# python get-emails.py

actblue_file = 'ashwin-ramaswami-153140-account_activity_2024-02-01_2024-05-01.csv'

stripe_fees_total = 0
actblue_fees_total = 0

with open(actblue_file, 'r') as f:
    csv_reader = csv.DictReader(f)
    for row in csv_reader:
        if row['Transaction Type'] == 'charge':
            stripe_fees_total += float(row['Stripe Fee Amount'].strip('$'))
            actblue_fees_total += float(row['Actblue Fee Amount'].strip('$'))
        elif 'actblue_fee_credit' in row['Transaction Type']:
            actblue_fees_total -= float(row['Actblue Fee Amount'].strip('$'))
        elif row['Transaction Type'] == 'refund':
            pass
        else:
            raise Exception(row)

print('stripe_fees_total', stripe_fees_total)
print('actblue_fees_total', actblue_fees_total)