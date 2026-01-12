import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS pronosticos")

cur.execute("""
CREATE TABLE pronosticos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    carrera_id INTEGER NOT NULL,
    pole TEXT,
    sprint_ganador TEXT,
    p1 TEXT,
    p2 TEXT,
    p3 TEXT,
    puntos INTEGER DEFAULT 0,
    UNIQUE(user_id, carrera_id)
)
""")

conn.commit()
conn.close()

print("Tabla pronosticos recreada correctamente")
