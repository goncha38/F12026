import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
ALTER TABLE carreras
ADD COLUMN imagen TEXT
""")

conn.commit()
conn.close()

print("Columna 'imagen' agregada correctamente.")
