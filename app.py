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
    if "user_id" in session:
        return redirect("/dashboard")
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
        return render_template("index.html", error="Login incorrecto")


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

        return render_template("loguin.html", error="Login incorrecto")

    return render_template("login.html")

#--------LOGOUT------------
@app.route("/logout")
def logout():
    session.clear()
    return render_template("index.html")

# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return render_template("index.html", error="Login incorrecto")

    conn = get_db()
    cur = conn.cursor()

    # 1️⃣ CARRERA ACTIVA (Race Week)
    cur.execute("""
        SELECT *
        FROM carreras
        WHERE status = 'iniciada'
        ORDER BY fecha ASC
        LIMIT 1
    """)
    carrera_activa = cur.fetchone()

    horas_restantes = None
    ya_pronosticado = False

    if carrera_activa and carrera_activa["fecha_limite_pronostico"]:
        fecha_limite = datetime.strptime(
            carrera_activa["fecha_limite_pronostico"],
            "%Y-%m-%dT%H:%M"
        )
        delta = fecha_limite - datetime.now()
        horas_restantes = max(0, int(delta.total_seconds() // 3600))

        cur.execute("""
            SELECT 1
            FROM pronosticos
            WHERE user_id = ? AND carrera_id = ?
        """, (session["user_id"], carrera_activa["id"]))
        ya_pronosticado = cur.fetchone() is not None

    # 2️⃣ ÚLTIMA CARRERA CORRIDA
    cur.execute("""
        SELECT *
        FROM carreras
        WHERE status = 'corrida'
        ORDER BY fecha DESC
        LIMIT 1
    """)
    carrera_anterior = cur.fetchone()

    pronosticos_fecha = []
    if carrera_anterior:
        cur.execute("""
            SELECT u.nombre AS usuario,
                   p.puntos
            FROM pronosticos p
            JOIN usuarios u ON u.id = p.user_id
            WHERE p.carrera_id = ?
            ORDER BY p.puntos DESC
        """, (carrera_anterior["id"],))
        pronosticos_fecha = cur.fetchall()

    # 3️⃣ PRÓXIMAS CARRERAS
    cur.execute("""
        SELECT *
        FROM carreras
        WHERE status = 'futura'
        ORDER BY fecha ASC
        LIMIT 4
    """)
    proximas = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        carrera=carrera_activa,
        carrera_anterior=carrera_anterior,
        pronosticos_fecha=pronosticos_fecha,
        horas_restantes=horas_restantes,
        ya_pronosticado=ya_pronosticado,
        proximas=proximas
    )

#---------EDITAR PERFIL-------------
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "user_id" not in session:
        return render_template("index.html")


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
        return render_template("index.html", error="Login incorrecto")


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
        return render_template("index.html", error="Login incorrecto")


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
                (user_id, carrera_id, pole, sprint_ganador, p1, p2, p3)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session["user_id"], carrera_id, pole, sprint_ganador, p1, p2, p3))

        conn.commit()
        conn.close()
        return redirect("/dashboard")

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
@app.route("/pilotos", methods=["GET", "POST"])
def listar_pilotos():
    if "user_id" not in session:
        return render_template("index.html")


    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pilotos ORDER BY dorsal ASC")
    lista = cur.fetchall()
    conn.close()

    return render_template("pilotos.html", pilotos=lista)


@app.route("/pilotos/editar/<int:piloto_id>", methods=["POST"])
def editar_piloto(piloto_id):
    if "user_id" not in session:
        return render_template("index.html", error="Login incorrecto")


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
@app.route("/admin/carreras", methods=["GET", "POST"])
def admin_carreras():
    if "user_id" not in session:
        return render_template("index.html", error="Login incorrecto")

    conn = get_db()
    cur = conn.cursor()

    # 🔐 verificar admin
    cur.execute("SELECT admin FROM usuarios WHERE id = ?", (session["user_id"],))
    user = cur.fetchone()
    if not user or user["admin"] != 1:
        conn.close()
        return "Acceso denegado", 403

    # ======================
    # POST – acciones
    # ======================
    if request.method == "POST":
        carrera_id = request.form["carrera_id"]
        accion = request.form.get("accion")

        # valores opcionales
        fecha_limite = request.form.get("fecha_limite_pronostico")
        status = request.form.get("status")
        imagen = request.form.get("imagen")

        # traer estado anterior
        cur.execute(
            "SELECT status FROM carreras WHERE id = ?",
            (carrera_id,)
        )
        estado_anterior = cur.fetchone()["status"]

        # 👉 GUARDAR (fecha, status, imagen)
        if accion == "guardar":
            cur.execute("""
                UPDATE carreras
                SET fecha_limite_pronostico = ?,
                    status = ?,
                    imagen = ?
                WHERE id = ?
            """, (fecha_limite, status, imagen, carrera_id))

            # ⭐ CLAVE: si pasa a CORRIDA → calcular puntos
        conn.commit()   # ⬅️ liberar el lock

        if estado_anterior != "corrida" and status == "corrida":
            calcular_puntos_carrera(carrera_id)



        # 👉 ABRIR PRONÓSTICO
        elif accion == "abrir":
            cur.execute("""
                UPDATE carreras
                SET pronostico_abierto = 1
                WHERE id = ?
            """, (carrera_id,))

        # 👉 CERRAR PRONÓSTICO
        elif accion == "cerrar":
            cur.execute("""
                UPDATE carreras
                SET pronostico_abierto = 0
                WHERE id = ?
            """, (carrera_id,))

        conn.commit()

    # ======================
    # GET – mostrar carreras
    # ======================
    cur.execute("""
        SELECT id, pais, fecha,
               fecha_limite_pronostico,
               status,
               imagen,
               pronostico_abierto
        FROM carreras
        ORDER BY fecha ASC
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
        return render_template("index.html", error="Login incorrecto")


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
def fecha_detalle(carrera_id):
    conn = get_db()
    cur = conn.cursor()

    # Carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()

    # Resultado oficial
    cur.execute("SELECT * FROM resultados WHERE carrera_id = ?", (carrera_id,))
    resultado = cur.fetchone()

    # Pronósticos de TODOS
    cur.execute("""
        SELECT
            u.nombre AS usuario,
            p.pole,
            p.sprint_ganador,
            p.p1, p.p2, p.p3,
            p.puntos
        FROM pronosticos p
        JOIN usuarios u ON u.id = p.user_id
        WHERE p.carrera_id = ?
        ORDER BY p.puntos DESC
    """, (carrera_id,))
    pronosticos = cur.fetchall()

    conn.close()

    return render_template(
        "pronosticos_fecha.html",
        carrera=carrera,
        resultado=resultado,
        pronosticos=pronosticos
    )



#----------CALCULAR PUNTOS NUEVA---------
def calcular_puntos_carrera(carrera_id):
    conn = get_db()
    cur = conn.cursor()

    # Resultado oficial
    cur.execute("""
        SELECT pole, sprint_ganador, p1, p2, p3
        FROM resultados
        WHERE carrera_id = ?
    """, (carrera_id,))
    resultado = cur.fetchone()

    if not resultado:
        conn.close()
        return

    podio_real = [resultado["p1"], resultado["p2"], resultado["p3"]]

    # Pronósticos
    cur.execute("""
        SELECT id, pole, sprint_ganador, p1, p2, p3
        FROM pronosticos
        WHERE carrera_id = ?
    """, (carrera_id,))
    pronosticos = cur.fetchall()

    for p in pronosticos:
        puntos = 0

        # POLE → 2 puntos
        if p["pole"] == resultado["pole"]:
            puntos += 2

        # SPRINT → 2 puntos (si existe)
        if resultado["sprint_ganador"]:
            if p["sprint_ganador"] == resultado["sprint_ganador"]:
                puntos += 2

        # P1
        if p["p1"] == resultado["p1"]:
            puntos += 3
        elif p["p1"] in podio_real:
            puntos += 1

        # P2
        if p["p2"] == resultado["p2"]:
            puntos += 3
        elif p["p2"] in podio_real:
            puntos += 1

        # P3
        if p["p3"] == resultado["p3"]:
            puntos += 3
        elif p["p3"] in podio_real:
            puntos += 1

        # Guardar total
        cur.execute("""
            UPDATE pronosticos
            SET puntos = ?
            WHERE id = ?
        """, (puntos, p["id"]))

    conn.commit()
    conn.close()

#----------VER PRONOSTICOS ----------
@app.route("/mis_pronosticos")
def mis_pronosticos():
    if "user_id" not in session:
        return render_template("index.html", error="Login incorrecto")


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
        return render_template("index.html", error="Login incorrecto")


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
        return render_template("index.html", error="Login incorrecto")


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
        return render_template("index.html", error="Login incorrecto")


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
        return render_template("index.html", error="Login incorrecto")


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