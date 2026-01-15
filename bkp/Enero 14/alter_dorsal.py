import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
    ALTER TABLE pronosticos
    ADD COLUMN carrera_id INTEGER
""")

conn.commit()
conn.close()

print("Columna carrera_id agregada correctamente")

