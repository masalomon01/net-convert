import pg8000 as pg


def cal_direct(bearing):
    if (bearing >= 0 and bearing <= 22.5)or(bearing > 337.5 and bearing <= 360):
        return "N"
    elif bearing > 22.5 and bearing <= 67.5:
        return "NE"
    elif bearing > 67.5 and bearing <= 112.5:
        return "E"
    elif bearing > 112.5 and bearing <= 157.5:
        return "SE"
    elif bearing > 157.5 and bearing <=202.5:
        return "S"
    elif bearing > 202.5 and bearing <=247.5:
        return "SW"
    elif bearing > 247.5 and bearing <=302.5:
        return "W"
    elif bearing > 302.5 and bearing <=337.5:
        return "NW"

conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
cursor.execute("SELECT gid,bearing FROM austin WHERE direction IS NULL OR direction='None'")
results = cursor.fetchall()
print len(results)
count = 0
for row in results:
    direct = cal_direct(row[1])
    update = "UPDATE austin SET direction='" + str(direct) + "' WHERE gid=" + str(row[0])
    cursor.execute(update)
    conn.commit()
    count += 1
    if count % 10000 == 0:
        print count
conn.commit()
