import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carrera_id INTEGER UNIQUE,
    pole TEXT,
    sprint_ganador TEXT,
    p1 TEXT,
    p2 TEXT,
    p3 TEXT,
    FOREIGN KEY (carrera_id) REFERENCES carreras(id)
)
""")

conn.commit()
conn.close()

print("Tabla resultados creada correctamente")
