import sqlite3

conn = sqlite3.connect("prode.db")
cursor = conn.cursor()

# ... haces consultas, inserts, etc ...

conn.close()   # <- cierra la conexión

