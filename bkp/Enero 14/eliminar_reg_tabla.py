import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("DELETE FROM usuarios WHERE id BETWEEN 1 AND 2")

conn.commit()
conn.close()

print("Pilotos eliminados del ID 4 al 13.")
