import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS pronosticos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    carrera_id INTEGER NOT NULL,
    poleman INTEGER NOT NULL,
    sprint_ganador INTEGER,
    podio_1 INTEGER NOT NULL,
    podio_2 INTEGER NOT NULL,
    podio_3 INTEGER NOT NULL,
    fecha_carga TEXT,
    UNIQUE(usuario_id, carrera_id)
)
""")

conn.commit()
conn.close()

print("Tabla 'carreras' creada correctamente.")
