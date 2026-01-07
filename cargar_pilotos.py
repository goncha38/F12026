import sqlite3

# Lista de pilotos 2025/2026 (puedo actualizarla si cambia el lineup oficial)
pilotos = [
    ("Max Verstappen", "Red Bull"),
    ("Yuki Tsunoda", "Red Bull"),
    ("Lewis Hamilton", "Ferrari"),
    ("Charles Leclerc", "Ferrari"),
    ("Lando Norris", "McLaren"),
    ("Oscar Piastri", "McLaren"),
    ("George Russell", "Mercedes"),
    ("Andrea Kimi Antonelli", "Mercedes"),
    ("Fernando Alonso", "Aston Martin"),
    ("Lance Stroll", "Aston Martin"),
    ("Esteban Ocon", "Haas"),
    ("Oliver Bearman", "Haas"),
    ("Alexander Albon", "Williams"),
    ("Franco Colapinto", "Williams"),
    ("Pierre Gasly", "Alpine"),
    ("Jack Doohan", "Alpine"),
    ("Sergio Pérez", "RB"),
    ("Isack Hadjar", "RB"),
    ("Guanyu Zhou", "Sauber"),
    ("Valtteri Bottas", "Sauber")
]

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

# Crear tabla si no existe
cur.execute("""
CREATE TABLE IF NOT EXISTS pilotos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    equipo TEXT
)
""")

# Insertar pilotos sin duplicar
cur.executemany("""
INSERT OR IGNORE INTO pilotos (nombre, equipo)
VALUES (?, ?)
""", pilotos)

conn.commit()
conn.close()

print("✔ Pilotos cargados correctamente.")
