import sqlite3

# Calendario oficial F1 2026 basado en la última publicación FIA 2024/2025
carreras = [
    (1, "Australia", "Albert Park", "2026-03-08", 0),
    (2, "China", "Shanghai International Circuit", "2026-03-22", 1),
    (3, "Japón", "Suzuka Circuit", "2026-04-05", 0),
    (4, "Bahrein", "Sakhir International Circuit", "2026-04-19", 1),
    (5, "Arabia Saudita", "Jeddah Corniche Circuit", "2026-05-03", 0),
    (6, "Emilia Romagna", "Imola", "2026-05-17", 0),
    (7, "Mónaco", "Circuit de Monaco", "2026-05-24", 0),
    (8, "España", "Circuit de Barcelona-Catalunya", "2026-06-07", 1),
    (9, "Canadá", "Gilles Villeneuve", "2026-06-14", 0),
    (10, "Austria", "Red Bull Ring", "2026-06-28", 1),
    (11, "Reino Unido", "Silverstone", "2026-07-05", 0),
    (12, "Hungría", "Hungaroring", "2026-07-19", 0),
    (13, "Bélgica", "Spa-Francorchamps", "2026-07-26", 1),
    (14, "Países Bajos", "Zandvoort", "2026-08-23", 0),
    (15, "Italia", "Monza", "2026-08-30", 0),
    (16, "Azerbaiyán", "Baku City Circuit", "2026-09-13", 1),
    (17, "Singapur", "Marina Bay", "2026-09-20", 0),
    (18, "Estados Unidos", "Circuit of The Americas", "2026-10-04", 1),
    (19, "México", "Autódromo Hermanos Rodríguez", "2026-10-11", 0),
    (20, "Brasil", "Interlagos", "2026-10-25", 1),
    (21, "Las Vegas", "Las Vegas Street Circuit", "2026-11-15", 0),
    (22, "Qatar", "Losail International Circuit", "2026-11-22", 1),
    (23, "Abu Dhabi", "Yas Marina", "2026-12-06", 0),
    (24, "Sudáfrica", "Kyalami Circuit", "2026-12-20", 1)
]

conn = sqlite3.connect("prode.db")
cur = conn.cursor()

# Opcional: limpiamos la tabla para evitar duplicados
cur.execute("DELETE FROM carreras")

# Insertamos todas las carreras
cur.executemany("""
INSERT INTO carreras (id, pais, autodromo, fecha, sprint)
VALUES (?, ?, ?, ?, ?)
""", carreras)

conn.commit()
conn.close()

print("Calendario 2026 cargado correctamente.")
