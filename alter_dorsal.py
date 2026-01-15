import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
    ALTER TABLE carreras
    ADD COLUMN status TEXT DEFAULT 'futura'
""")

conn.commit()
conn.close()

print("Columna status agregada correctamente")

