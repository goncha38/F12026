import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(carreras);")
columnas = cur.fetchall()

for col in columnas:
    print(col)



conn.close()
