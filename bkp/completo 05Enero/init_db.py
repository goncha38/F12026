import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

# Tabla usuarios
cur.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    email TEXT UNIQUE,
    password TEXT,
    fecha_registro TEXT
)
""")

# Tabla pronósticos
cur.execute("""
CREATE TABLE IF NOT EXISTS pronosticos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    carrera TEXT,
    pole TEXT,
    p1 TEXT,
    p2 TEXT,
    p3 TEXT,
    FOREIGN KEY (user_id) REFERENCES usuarios(id)
)
""")

conn.commit()
conn.close()

print("Base de datos creada correctamente.")
