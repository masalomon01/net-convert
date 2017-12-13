import pg8000 as pg
import titlecase

conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
query = 'SELECT id, "Sign_Text" FROM elpaso_signs WHERE "Sign_Text" IS NOT NULL'
cursor.execute(query)
results = cursor.fetchall()
for sign in results:
    new_sign = titlecase.titlecase(sign[1])
    new_sign = new_sign.replace('\'','')
    query = 'UPDATE elpaso_signs SET "Sign_Text"=\'' + new_sign + '\' WHERE id=' + str(sign[0]) + ';'
    print query
    cursor.execute(query)
cursor.close()
