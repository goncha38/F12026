from flask import Flask, render_template, request, redirect, session
import sqlite3
from flask_bcrypt import Bcrypt
from config import SECRET_KEY
from datetime import datetime  # import correcto

app = Flask(__name__)
app.secret_key = SECRET_KEY

bcrypt = Bcrypt(app)

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

        # Validar contraseñas iguales
        if password != password2:
            return render_template("register.html",
                                   error="Las contraseñas no coinciden.")

        conn = get_db()
        cur = conn.cursor()

        # Validar email existente
        cur.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        existe = cur.fetchone()

        if existe:
            conn.close()
            return render_template("register.html",
                                   error="El email ya está registrado.")

        # Encriptar contraseña
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        # Fecha de registro
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insertar usuario correctamente
        cur.execute("""
            INSERT INTO usuarios (nombre, email, password, fecha_registro)
            VALUES (?, ?, ?, ?)
        """, (nombre, email, hashed, fecha))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# -------- LOGIN --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nombre, password, admin
            FROM usuarios
            WHERE email = ?
        """, (email,))
        user = cur.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["nombre"]
            session["admin"] = user["admin"]  # 👈 CLAVE
            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Usuario o contraseña incorrectos"
        )

    return render_template("login.html")


# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html", username=session["user_name"])


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
        WHERE user_id = ? AND carrera = ?
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
    cur.execute("SELECT * FROM pilotos ORDER BY dorsal")
    pilotos = cur.fetchall()

    conn.close()
    return render_template(
        "pronostico.html",
        carrera=carrera,
        pilotos=pilotos,
        pronostico=pronostico,
        solo_lectura=solo_lectura
    )


# -------- LISTA DE USUARIOS --------
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
@app.route("/admin/carreras")
def admin_carreras():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Verificar si es admin
    cur.execute("SELECT admin FROM usuarios WHERE id = ?", (session["user_id"],))
    user = cur.fetchone()

    if not user or user["admin"] != 1:
        conn.close()
        return "Acceso denegado", 403

    cur.execute("""
        SELECT id, pais, autodromo, fecha, sprint, pronostico_abierto
        FROM carreras
        ORDER BY fecha ASC
    """)
    carreras = cur.fetchall()
    conn.close()

    return render_template("admin_carreras.html", carreras=carreras)
@app.route("/admin/carreras/toggle/<int:carrera_id>")
def toggle_pronostico(carrera_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Verificar admin
    cur.execute("SELECT admin FROM usuarios WHERE id = ?", (session["user_id"],))
    user = cur.fetchone()

    if not user or user["admin"] != 1:
        conn.close()
        return "Acceso denegado", 403

    # Cambiar estado
    cur.execute("""
        UPDATE carreras
        SET pronostico_abierto = CASE
            WHEN pronostico_abierto = 1 THEN 0
            ELSE 1
        END
        WHERE id = ?
    """, (carrera_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/carreras")
@app.route("/admin/resultados/<int:carrera_id>", methods=["GET", "POST"])
def admin_resultados(carrera_id):
    if "user_id" not in session or not session.get("admin"):
        return "Acceso denegado", 403

    conn = get_db()
    cur = conn.cursor()

    # carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()

    # pilotos
    cur.execute("SELECT nombre FROM pilotos ORDER BY dorsal ASC")
    pilotos = [p["nombre"] for p in cur.fetchall()]

    # resultado existente
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
                SET pole=?, sprint_ganador=?, p1=?, p2=?, p3=?
                WHERE carrera_id=?
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
            p.*,
            p.carrera AS pais,
            NULL AS fecha
        FROM pronosticos p
        WHERE p.user_id = ?
        ORDER BY p.id ASC
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


# -------- INICIAR APP --------
if __name__ == "__main__":
    print("Flask está iniciando en http://localhost:5000 ...")
    app.run(debug=True)