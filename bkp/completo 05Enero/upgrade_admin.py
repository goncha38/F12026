import sqlite3

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

cur.execute("""
    UPDATE usuarios
    SET admin = 1
    WHERE email = 'gonzalo.iglesias@f1.com'
""")

conn.commit()
conn.close()

print("Usuario convertido en admin")
