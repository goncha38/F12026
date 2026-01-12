import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()
cur.execute("SELECT * FROM carreras ORDER BY id")
data = cur.fetchall()
conn.close()

for p in data:
    print(p)

