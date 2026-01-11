import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("SELECT nombre, avatar, admin, email FROM usuarios;")
filas = cur.fetchall()



print("Cantidad de carreras:", len(filas))
for fila in filas:
    print(fila)

conn.close()
