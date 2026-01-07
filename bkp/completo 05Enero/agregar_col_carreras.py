import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
ALTER TABLE usuarios
ADD COLUMN avatar TEXT
""")

conn.commit()
conn.close()

print("Columna 'avatar' agregada correctamente.")
