import pandas as pd
import numpy as np
import pdfplumber
from pdfplumber.utils import within_bbox, collate_chars
from operator import itemgetter
import datetime
import sys, os


COLUMNS = [
    "month",
    "state",
    "permit",
    "permit_recheck",
    "handgun",
    "long_gun",
    "other",
    "multiple",
    "admin",
    "prepawn_handgun",
    "prepawn_long_gun",
    "prepawn_other",
    "redemption_handgun",
    "redemption_long_gun",
    "redemption_other",
    "returned_handgun",
    "returned_long_gun",
    "returned_other",
    "rentals_handgun",
    "rentals_long_gun",
    "private_sale_handgun",
    "private_sale_long_gun",
    "private_sale_other",
    "return_to_seller_handgun",
    "return_to_seller_long_gun",
    "return_to_seller_other",
    "totals"
]

us_state_abbrev = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY',
}

def parse_month(month_str):
    d = datetime.datetime.strptime(month_str, "%B - %Y")
    return d.strftime("%Y-%m")

def parse_value(x):
    #if it's null or nothing leave it alone
    if pd.isnull(x) or x == "": return None
    #if it has a comma strip it out and return as an int
    return int(x.replace(",", ""))

def chk_data(checks):
    try:
        assert(len(checks) > 0)
    except:
        raise Exception("No data found.")

    ## Test vertical totals
    # [2:] because first two columns are month and state name
    for c in COLUMNS[2:]:
        # -1 so as not to include the totals column on the end
        v_total = checks[c].iloc[-1]
        v_colsum = checks[c].sum()
        try:
            assert(v_colsum == (v_total * 2))
        except:
            raise Exception("Vertical totals don't match on {0}.".format(c))

    ## Test horizontal totals
    h_colsums = checks.fillna(0).sum(axis=1)
    h_totals = checks["totals"].fillna(0)
    zipped = zip(checks["state"], h_colsums, h_totals)
    for state, h_colsum, h_total in zipped:
        try:
            assert(h_colsum == (h_total * 2))
        except:
            raise Exception("Horizontal totals don't match on {0}.".format(state))
            
def parse_pdf_page(page):
    #crop the top to get the month and year
    month_crop = page.within_bbox((0, 35, page.width, 65))
    month_text = month_crop.extract_text(x_tolerance=2)
    month = parse_month(month_text)
    
    #crop out the table itself
    table_crop = page.crop((0, 80, page.width, 485))

    _table = table_crop.extract_table({
        "horizontal_strategy": "text",
        "explicit_vertical_lines": [
            min(map(itemgetter("x0"), table_crop.chars))
        ],
        "intersection_tolerance": 5
    })

    table = pd.DataFrame([ [ month ] + row for row in _table ])
    
    #rename the columns
    table.columns = COLUMNS
    #get rid of commas and turn values back into int's
    table[table.columns[2:]] = table[table.columns[2:]].applymap(parse_value)
    
    #fix the illinois state name in some of the pdf's pages
    table.loc[(table["state"] == "llinois"), "state"] = "Illinois"
    try: chk_data(table)
    except: raise Exception("Invalid data for " + month)

    return table

def parse_pdf(file_obj):
    pdf = pdfplumber.load(file_obj)

    checks = pd.concat(list(map(parse_pdf_page, pdf.pages))).reset_index(drop=True)

    return checks[checks["state"] != "Totals"]

pdf_file = "NICS.pdf"
file = open(pdf_file, 'rb')
data_df = parse_pdf(file)
data_df["year"] = data_df['month'].str.split("-").str[0]
data_df["mon_num"] = data_df['month'].str.split("-").str[1]
final_df = data_df.loc[(data_df["state"] != "Guam") & (data_df["state"] != "District of Columbia") & (data_df["state"] != "Mariana Islands") & (data_df["state"] != "Virgin Islands") & (data_df["state"] != "Puerto Rico")]
sa = []
for n,v in final_df["state"].iteritems():
    sa.append(us_state_abbrev[v])
    
final_df["state_abbr"] = pd.Series(sa)
final_df.to_csv("Guns_output.csv", index=False)