import csv
import numpy

infile = open('C:/Users/willi/Downloads/atx_output_data.csv','rb')
reader = csv.DictReader(infile)

total_pd = 0.0
total_sb = 0.0
total_google = 0.0
total_trips = 0.0

sb_errors = []

for row in reader:
    try:
        prod_est = float(row['production_estimated'])
        sb_est = float(row['sandbox_estimated'])
        google_est = float(row['google_estimated'])


    except ValueError:
        continue

    total_pd += prod_est
    total_google += google_est
    total_sb += sb_est
    total_trips += 1.0

    sb_pct_error = int(((sb_est-google_est)  / google_est) * 100)
    sb_errors.append(sb_pct_error)

print "Average time difference between google and Production is {} minutes".format(abs(total_google-total_pd) / total_trips)
print "Average time difference between google and Sandbox is {} minutes".format(abs(total_google-total_sb) / total_trips)


