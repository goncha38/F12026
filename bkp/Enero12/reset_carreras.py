import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS carreras")

cur.execute("""
CREATE TABLE carreras (
    id INTEGER PRIMARY KEY,
    pais TEXT,
    autodromo TEXT,
    fecha TEXT,
    sprint INTEGER
)
""")

conn.commit()
conn.close()

print("Tabla carreras recreada correctamente.")



