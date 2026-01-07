import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("ALTER TABLE pronosticos ADD COLUMN puntos INTEGER DEFAULT 0")

conn.commit()
conn.close()

print("Columna puntos agregada")
