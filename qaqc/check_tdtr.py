import csv

'''
This program reads the TDTR file and alerts the user if any of the following occur:
1. Number of successors in restriction does not match the actual number of successors
2. Days of week part of restriction has a character other than 1 or 0
3. Days of week part of restriction does not have 7 days
4. The second time in restriction is earlier than the first
    -- The restriction should have format days of week, from time, to time.
    -- Things will fall apart if the to time is later than the from time
5. One of the times is out of bounds
    -- Times are in format of minutes in the day, so it must be between 0 and 1440
    -- Not actually sure if 1440 and 0 are allowed.  I would think midnight is 0 so 11:59 pm is 1439
        but not sure what parade thinks
6. Restriction lasts all day
    -- Not exactly an error because it will work fine but better practice to include with the permanent
        restrictions if it lasts all day every day
'''


def num_successor_mismatch(row):
    number_successors = len(row['successors'][:-1].split(" "))  # successor field has space at end, so clip it off
    restriction = row['time-depen'][1:-1]
    restriction_succ_count = restriction.count("[")  # strip the start and end brackets off
    if number_successors > restriction_succ_count:
        print row['LinkID_parade'] + ' is missing a successor in time-depen restriction'
    elif number_successors < restriction_succ_count:
        print row['LinkID_parade'] + ' has an extra successor in the time-depen restriction'


def parse_restriction(restriction):
    restriction_split = ['']
    within_brackets = False
    cur_index = 0
    for character in restriction:
        if character == '[':
            within_brackets = True
        if character == ']':
            within_brackets = False
            cur_index += 1
            restriction_split.append('')
        if within_brackets and character != '[':
            restriction_split[cur_index] += character
    return restriction_split[:-1]


def check_restriction_numbers(restriction_parsed, link_id):
    for each in restriction_parsed:
        if each != '':
            restriction_split = each.split(",")
            days_of_week = restriction_split[0]
            for character in days_of_week:
                if character != '1' and character != '0':
                    print link_id + ' has a ' + character + ' in the days of week part of restriction'
            if len(days_of_week) > 7:
                print link_id + ' has an extra character in days of week part of restriction'
            if len(days_of_week) < 7:
                print link_id + ' is missing a character in days of week part of restriction'

            times = restriction_split[1:]  # days of week are at 0
            for time in times:
                if int(time) < 0:
                    print link_id + ' has a negative time'
                if int(time) > 1440:
                    print link_id + ' has a time greater than max (1440)'


def check_stray_typo(restriction, link_id):
    if '.' in restriction:
        print link_id + 'has a . instead of ,'
    if restriction[:2] != '[[':
        print link_id + ' appears to be missing a [ at start'
    if restriction[-2:] != ']]':
        print link_id + ' appears to be missing a ] at end'

def check_permanent_restriction(restriction, link_id):
    for each in restriction:
        if each != '' and not '.' in each:
            restriction_split = each.split(",")
            days = restriction_split[0]
            time1 = int(restriction_split[1])
            time2 = int(restriction_split[2])
            if time2 - time1 < 0:
                print link_id + ' has a restriction where second time is earlier than the first time'
            if time2 - time1 > 1430 and days == '1111111':
                print link_id + ' appears to have an all day restriction.  Replace with permanent turn restriction?'



in_tdtr = 'D:/Will/Metropia/Network Updates/El Paso/Update 7-14-2016/elpaso/elpaso_TDTR.csv'
with open(in_tdtr,'rb') as infile:
    reader = csv.DictReader(infile)
    count = 0
    for row in reader:
        if row['time-depen'] != '':
            num_successor_mismatch(row)
            restriction = row['time-depen'][1:-1]
            restriction_parsed = parse_restriction(restriction)
            check_restriction_numbers(restriction_parsed, row['LinkID_parade'])
            check_stray_typo(row['time-depen'], row['LinkID_parade'])
            check_permanent_restriction(restriction_parsed, row['LinkID_parade'])





