import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS carreras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nro_carrera INTEGER,
    pais TEXT,
    autodromo TEXT,
    fecha TEXT,
    sprint INTEGER
)
""")

conn.commit()
conn.close()

print("Tabla 'carreras' creada correctamente.")
