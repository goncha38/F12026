import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()
cur.execute("SELECT * FROM pilotos ORDER BY nombre")
data = cur.fetchall()
conn.close()

for p in data:
    print(p)

