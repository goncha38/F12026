import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("SELECT id, email, password FROM usuarios")
for u in cur.fetchall():
    print(u)

conn.close()
