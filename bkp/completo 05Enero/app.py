from flask import Flask, render_template, request, redirect, session
import sqlite3
from flask_bcrypt import Bcrypt
from config import SECRET_KEY
from datetime import datetime  # import correcto

app = Flask(__name__)
app.secret_key = SECRET_KEY
bcrypt = Bcrypt(app)

#---- Funcion Fecha--------------
from datetime import datetime

def parse_fecha(fecha_str):
    """
    Convierte fechas guardadas como:
    - 'YYYY-MM-DD HH:MM:SS'
    - 'YYYY-MM-DDTHH:MM'   (datetime-local)
    """
    if not fecha_str:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(fecha_str, fmt)
        except ValueError:
            pass

    return None

# --- Filtro Jinja para formatear fechas ---
from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        fecha = datetime.strptime(value, "%Y-%m-%d")
        return fecha.strftime("%d-%m")
    except:
        return value
# ------------------------------------------

def get_db():
    conn = sqlite3.connect("prode.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")


# -------- REGISTRO --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]
        password2 = request.form["password2"]
        avatar = request.form.get("avatar", "default.png")

        # Validar contraseñas iguales
        if password != password2:
            return render_template(
                "register.html",
                error="Las contraseñas no coinciden."
            )

        conn = get_db()
        cur = conn.cursor()

        # Validar email existente
        cur.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        existe = cur.fetchone()

        if existe:
            conn.close()
            return render_template(
                "register.html",
                error="El email ya está registrado."
            )

        # Encriptar contraseña
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Fecha de registro
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insertar usuario
        cur.execute("""
            INSERT INTO usuarios (nombre, email, password, avatar, fecha_registro)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, email, hashed_password, avatar, fecha))

        conn.commit()
        conn.close()

        print("FORM DATA:", request.form)
        return redirect("/login")

    return render_template("register.html")
# -------- LOGIN --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        )
        user = cur.fetchone()
        conn.close()

        

        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["nombre"]
            session["avatar"] = user["avatar"] if user["avatar"] else "👤"
            session["admin"] = user["admin"]

            return redirect("/dashboard")

        return render_template("login.html", error="Login incorrecto")

    return render_template("login.html")

#--------LOGOUT------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Próximas carreras (ejemplo)
    cur.execute("""
        SELECT *
        FROM carreras
        WHERE fecha >= date('now')
        ORDER BY fecha ASC
        LIMIT 5
    """)
    carreras = cur.fetchall()

    primera = carreras[0] if carreras else None
    horas_restantes = None

    if primera and primera["fecha_limite_pronostico"]:
        fecha_limite = parse_fecha(primera["fecha_limite_pronostico"])
        if fecha_limite:
            delta = fecha_limite - datetime.now()
            horas_restantes = max(0, int(delta.total_seconds() // 3600))

    conn.close()

    return render_template(
        "dashboard.html",
        carreras=carreras,
        horas_restantes=horas_restantes
    )

#-------- LISTA DE USUARIOS --------
@app.route("/usuarios")
def usuarios():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nombre, email, fecha_registro
        FROM usuarios
        ORDER BY nombre ASC
    """)
    lista = cur.fetchall()
    conn.close()

    return render_template("usuarios.html", usuarios=lista)

#---------EDITAR PERFIL-------------
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        avatar = request.form.get("avatar")

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE usuarios SET avatar = ? WHERE id = ?",
            (avatar, session["user_id"])
        )
        conn.commit()
        conn.close()

        session["avatar"] = avatar
        return redirect("/dashboard")

    return render_template("perfil.html")




# -------- CALENDARIO --------
@app.route("/calendario")
def calendario():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id AS nro_carrera, pais, autodromo, fecha, sprint
        FROM carreras
        ORDER BY id ASC
    """)

    carreras = cur.fetchall()
    conn.close()

    return render_template("calendario.html", carreras=carreras)
#-----------------------------------------------------------------
# -------- PRONOSTICO POR CARRERA --------
@app.route("/pronostico/<int:carrera_id>", methods=["GET", "POST"])
def pronostico_carrera(carrera_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()

    if not carrera:
        conn.close()
        return "Carrera no encontrada", 404

    # Pronóstico existente
    cur.execute("""
        SELECT * FROM pronosticos
        WHERE user_id = ? AND carrera_id = ?
    """, (session["user_id"], carrera_id))
    pronostico = cur.fetchone()

    # 🔒 Modo solo lectura
    solo_lectura = carrera["clasificacion_iniciada"] == 1

    # -------- POST --------
    if request.method == "POST":

        if solo_lectura:
            conn.close()
            return "El pronóstico para esta carrera está cerrado", 403

        pole = request.form["pole"]
        p1 = request.form["p1"]
        p2 = request.form["p2"]
        p3 = request.form["p3"]

        sprint_ganador = None
        if carrera["sprint"] == 1:
            sprint_ganador = request.form.get("sprint_ganador")

        if pronostico:
            cur.execute("""
                UPDATE pronosticos
                SET pole = ?, sprint_ganador = ?, p1 = ?, p2 = ?, p3 = ?
                WHERE id = ?
            """, (pole, sprint_ganador, p1, p2, p3, pronostico["id"]))
        else:
            cur.execute("""
                INSERT INTO pronosticos
                (user_id, carrera, pole, sprint_ganador, p1, p2, p3)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session["user_id"], carrera_id, pole, sprint_ganador, p1, p2, p3))

        conn.commit()
        conn.close()
        return redirect("/calendario")

    # -------- GET --------
    cur.execute("SELECT * FROM pilotos ORDER BY nombre")
    pilotos = [p["nombre"] for p in cur.fetchall()]

    conn.close()
    return render_template(
        "pronostico.html",
        carrera=carrera,
        pilotos=pilotos,
        pronostico=pronostico,
        solo_lectura=solo_lectura
    )

# -------- LISTA Y EDICIÓN DE PILOTOS --------
@app.route("/pilotos", methods=["GET"])
def listar_pilotos():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pilotos ORDER BY dorsal ASC")
    lista = cur.fetchall()
    conn.close()

    return render_template("pilotos.html", pilotos=lista)


@app.route("/pilotos/editar/<int:piloto_id>", methods=["POST"])
def editar_piloto(piloto_id):
    if "user_id" not in session:
        return redirect("/login")

    nombre = request.form["nombre"]
    equipo = request.form["equipo"]
    nacionalidad = request.form["nacionalidad"]
    dorsal = request.form["dorsal"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE pilotos
        SET nombre = ?, equipo = ?, nacionalidad = ?, dorsal = ?
        WHERE id = ?
    """, (nombre, equipo, nacionalidad, dorsal, piloto_id))

    conn.commit()
    conn.close()

    return redirect("/pilotos")

    # ----- MOSTRAR LISTA -----
    cur.execute("SELECT * FROM pilotos ORDER BY dorsal ASC")
    lista = cur.fetchall()
    conn.close()

    return render_template("pilotos.html", pilotos=lista)


    # ----- GUARDAR EDICIÓN -----
    if request.method == "POST":
        piloto_id = request.form["id"]
        nombre = request.form["nombre"]
        equipo = request.form["equipo"]
        nacionalidad = request.form["nacionalidad"]
        dorsal = request.form["dorsal"]

        cur.execute("""
            UPDATE pilotos
            SET nombre = ?, equipo = ?, nacionalidad = ?, dorsal = ?
            WHERE id = ?
        """, (nombre, equipo, nacionalidad, dorsal, piloto_id))

        conn.commit()

    # ----- MOSTRAR LISTA -----
    cur.execute("SELECT * FROM pilotos ORDER BY dorsal ASC")
    lista = cur.fetchall()
    conn.close()

    return render_template("pilotos.html", pilotos=lista)
# -------- PANEL ADMIN --------

from datetime import datetime
from flask import request

#--------------ADMIN USUARIOS---------
@app.route("/admin/usuarios", methods=["GET", "POST"])
def admin_usuarios():
    if "user_id" not in session or not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        user_id = request.form["user_id"]
        nombre = request.form["nombre"]
        avatar = request.form["avatar"]

        cur.execute("""
            UPDATE usuarios
            SET nombre = ?, avatar = ?
            WHERE id = ?
        """, (nombre, avatar, user_id))

        conn.commit()

    cur.execute("""
        SELECT id, nombre, email, avatar, admin
        FROM usuarios
        ORDER BY nombre
    """)
    usuarios = cur.fetchall()

    conn.close()
    return render_template("admin_usuarios.html", usuarios=usuarios)
#---------eliminar usuario---------
@app.route("/admin/usuarios/eliminar/<int:user_id>")
def eliminar_usuario(user_id):
    if "user_id" not in session or not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin/usuarios")
#-----------blanquear pass---------
@app.route("/admin/usuarios/reset_password/<int:user_id>")
def reset_password_usuario(user_id):
    if "user_id" not in session or not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE usuarios
        SET password = ''
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/usuarios")



# ==============================
# ADMIN – CARRERAS
@app.route("/admin_carreras", methods=["GET", "POST"])
def admin_carreras():
    if "user_id" not in session or not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        carrera_id = request.form["carrera_id"]

        fecha_limite = request.form.get("fecha_limite_pronostico")

        # ✅ CLAVE: checkbox
        pronostico_abierto = 1 if request.form.get("pronostico_abierto") else 0

        cur.execute("""
            UPDATE carreras
            SET
                fecha_limite_pronostico = ?,
                pronostico_abierto = ?
            WHERE id = ?
        """, (fecha_limite, pronostico_abierto, carrera_id))

        conn.commit()

    cur.execute("""
        SELECT
            id,
            pais,
            fecha,
            fecha_limite_pronostico,
            pronostico_abierto
        FROM carreras
        ORDER BY fecha
    """)
    carreras = cur.fetchall()

    conn.close()

    return render_template("admin_carreras.html", carreras=carreras)



# ==============================
# ADMIN – RESULTADOS
# ==============================
@app.route("/admin/resultados/<int:carrera_id>", methods=["GET", "POST"])
def admin_resultados(carrera_id):
    if "user_id" not in session:
        return redirect("/login")

    if not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    # Carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()

    if not carrera:
        conn.close()
        return "Carrera no encontrada", 404

    # Pilotos
    cur.execute("SELECT nombre FROM pilotos ORDER BY dorsal ASC")
    pilotos = [p["nombre"] for p in cur.fetchall()]

    # Resultado existente
    cur.execute("SELECT * FROM resultados WHERE carrera_id = ?", (carrera_id,))
    resultado = cur.fetchone()

    if request.method == "POST":
        pole = request.form["pole"]
        sprint = request.form.get("sprint")
        p1 = request.form["p1"]
        p2 = request.form["p2"]
        p3 = request.form["p3"]

        if resultado:
            cur.execute("""
                UPDATE resultados
                SET pole = ?, sprint_ganador = ?, p1 = ?, p2 = ?, p3 = ?
                WHERE carrera_id = ?
            """, (pole, sprint, p1, p2, p3, carrera_id))
        else:
            cur.execute("""
                INSERT INTO resultados (carrera_id, pole, sprint_ganador, p1, p2, p3)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (carrera_id, pole, sprint, p1, p2, p3))

        conn.commit()
        conn.close()
        return redirect("/admin/carreras")

    conn.close()

    return render_template(
        "admin_resultados.html",
        carrera=carrera,
        pilotos=pilotos,
        resultado=resultado
    )
#----------Resumen Fecha------------
from datetime import datetime

@app.route("/fecha/<int:carrera_id>")
def fecha(carrera_id):
    conn = get_db()
    cur = conn.cursor()

    # Carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()

    # Resultado
    cur.execute("SELECT * FROM resultados WHERE carrera_id = ?", (carrera_id,))
    resultado = cur.fetchone()

    # Pronósticos
    cur.execute("""
        SELECT p.*, u.nombre AS usuario
        FROM pronosticos p
        JOIN usuarios u ON u.id = p.user_id
        WHERE p.carrera_id = ?
        ORDER BY p.puntos DESC
    """, (carrera_id,))
    pronosticos = cur.fetchall()

    conn.close()

    # ⏱️ CUENTA REGRESIVA
    segundos_restantes = 0
    if carrera["fecha_clasificacion"]:
        cierre = datetime.strptime(
            carrera["fecha_clasificacion"], "%Y-%m-%d %H:%M"
        )
        ahora = datetime.now()
        diff = (cierre - ahora).total_seconds()
        if diff > 0:
            segundos_restantes = int(diff)

    return render_template(
        "fecha.html",
        carrera=carrera,
        resultado=resultado,
        pronosticos=pronosticos,
        segundos_restantes=segundos_restantes
    )

#---------CALCULAR PUNTOS -----------
def calcular_puntos(pron, res):
    puntos = 0

    # Pole
    if pron["pole"] == res["pole"]:
        puntos += 2

    # Sprint (si existe)
    if res["sprint_ganador"]:
        if pron["sprint_ganador"] == res["sprint_ganador"]:
            puntos += 2

    # Podio
    podio_res = [res["p1"], res["p2"], res["p3"]]
    podio_pron = [pron["p1"], pron["p2"], pron["p3"]]

    for i in range(3):
        if podio_pron[i] == podio_res[i]:
            puntos += 3
        elif podio_pron[i] in podio_res:
            puntos += 1

    return puntos

#----------VER PRONOSTICOS ----------
@app.route("/mis_pronosticos")
def mis_pronosticos():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.pais,
            c.fecha,

            -- Resultado oficial
            r.pole AS res_pole,
            r.sprint_ganador AS res_sprint,
            r.p1 AS res_p1,
            r.p2 AS res_p2,
            r.p3 AS res_p3,

            -- Pronóstico del usuario
            p.pole AS pro_pole,
            p.sprint_ganador AS pro_sprint,
            p.p1 AS pro_p1,
            p.p2 AS pro_p2,
            p.p3 AS pro_p3,

            p.puntos
        FROM pronosticos p
        JOIN carreras c ON c.id = p.carrera_id
        LEFT JOIN resultados r ON r.carrera_id = c.id
        WHERE p.user_id = ?
        ORDER BY c.fecha ASC
    """, (session["user_id"],))


    pronosticos = cur.fetchall()

    print("DEBUG pronosticos:", pronosticos)

    conn.close()

    return render_template(
        "mis_pronosticos.html",
        pronosticos=pronosticos
    )

#--------CALCULAR PUNTOS-------------
@app.route("/admin/calcular_puntos/<int:carrera_id>")
def admin_calcular_puntos(carrera_id):
    if "user_id" not in session:
        return redirect("/login")

    if not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    # 1️⃣ Resultado oficial
    cur.execute("""
        SELECT *
        FROM resultados
        WHERE carrera_id = ?
    """, (carrera_id,))
    resultado = cur.fetchone()

    if not resultado:
        conn.close()
        return "No hay resultados cargados", 400

    # 2️⃣ Pronósticos de la carrera
    cur.execute("""
        SELECT *
        FROM pronosticos
        WHERE carrera_id = ?
    """, (carrera_id,))
    pronosticos = cur.fetchall()

    # 3️⃣ Calcular puntos
    for pron in pronosticos:
        puntos = calcular_puntos(pron, resultado)

        cur.execute("""
            UPDATE pronosticos
            SET puntos = ?
            WHERE id = ?
        """, (puntos, pron["id"]))

    conn.commit()
    conn.close()

    return "Puntos calculados correctamente"
# -------- RANKING GENERAL --------
@app.route("/ranking")
def ranking():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            u.nombre,
            COALESCE(SUM(p.puntos), 0) AS total_puntos
        FROM usuarios u
        LEFT JOIN pronosticos p ON p.user_id = u.id
        GROUP BY u.id, u.nombre
        ORDER BY total_puntos DESC
    """)

    ranking = cur.fetchall()
    conn.close()

    return render_template("ranking.html", ranking=ranking)

# -------- CONTROL DE PRONÓSTICOS (MATRIZ) --------
@app.route("/control_pronosticos")
def control_pronosticos():
    if "user_id" not in session:
        return redirect("/login")

    # solo admin
    if not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    # Usuarios
    cur.execute("SELECT id, nombre FROM usuarios ORDER BY nombre")
    usuarios = cur.fetchall()

    # Carreras
    cur.execute("""
        SELECT id, pais, fecha
        FROM carreras
        ORDER BY fecha
    """)
    carreras = cur.fetchall()

    # Pronósticos existentes
    cur.execute("""
        SELECT user_id, carrera_id
        FROM pronosticos
    """)
    pronosticos = cur.fetchall()

    conn.close()

    # Armar matriz user_id -> carrera_id -> True
    matriz = {}
    for u in usuarios:
        matriz[u["id"]] = {}

    for p in pronosticos:
        matriz[p["user_id"]][p["carrera_id"]] = True

    return render_template(
        "control_pronosticos.html",
        usuarios=usuarios,
        carreras=carreras,
        matriz=matriz
    )

#---------carrera visible--------
def obtener_carrera_actual(cur):
    cur.execute("""
        SELECT c.*
        FROM carreras c
        JOIN resultados r ON r.carrera_id = c.id
        ORDER BY c.fecha DESC
        LIMIT 1
    """)
    return cur.fetchone()
# ------------ MATRIZ RESULTADOS ---------
@app.route("/pronosticos_fecha")
def pronosticos_fecha():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    carrera = obtener_carrera_actual(cur)
    if not carrera:
        conn.close()
        return "Aún no hay resultados cargados", 400

    # Resultado oficial
    cur.execute("""
        SELECT *
        FROM resultados
        WHERE carrera_id = ?
    """, (carrera["id"],))
    resultado = cur.fetchone()

    if not resultado:
        conn.close()
        return "Aún no hay resultados cargados", 400

    # Pronósticos de TODOS los usuarios
    cur.execute("""
        SELECT
            u.nombre AS usuario,
            p.*
        FROM pronosticos p
        JOIN usuarios u ON u.id = p.user_id
        WHERE p.carrera_id = ?
        ORDER BY u.nombre
    """, (carrera["id"],))
    pronosticos = cur.fetchall()

    conn.close()

    return render_template(
        "pronosticos_fecha.html",
        carrera=carrera,
        resultado=resultado,
        pronosticos=pronosticos
    )


#---------HUB FECHA ----------


# -------- INICIAR APP --------
if __name__ == "__main__":
    print("Flask está iniciando en http://localhost:5000 ...")
    app.run(debug=True)