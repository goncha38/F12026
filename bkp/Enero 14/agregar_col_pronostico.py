import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
ALTER TABLE pronosticos
ADD COLUMN sprint_ganador TEXT
""")

conn.commit()
conn.close()

print("Columna sprint_ganador agregada correctamente.")
