# agregar_fecha_limite.py
import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
ALTER TABLE carreras
ADD COLUMN fecha_limite_pronostico TEXT
""")

conn.commit()
conn.close()

print("Columna fecha_limite_pronostico agregada")
