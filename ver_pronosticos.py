import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(pronosticos)")
for fila in cur.fetchall():
    print(fila)

conn.close()
