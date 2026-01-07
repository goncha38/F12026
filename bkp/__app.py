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

        cur.execute("SELECT id, nombre, password FROM usuarios WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["nombre"]
            return redirect("/dashboard")

        return render_template("login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")


# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html", username=session["user_name"])


# -------- PRONOSTICO --------
@app.route("/pronostico", methods=["GET", "POST"])
def pronostico():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        pole = request.form["pole"]
        p1 = request.form["p1"]
        p2 = request.form["p2"]
        p3 = request.form["p3"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO pronosticos (user_id, carrera, pole, p1, p2, p3)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session["user_id"], "GP Ejemplo", pole, p1, p2, p3))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("pronostico.html")


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

# -------------------- Helpers --------------------
def parse_datetime_field(value):
    """
    Intenta parsear un string de fecha/hora en varios formatos.
    Retorna datetime o None.
    """
    if not value:
        return None
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for f in formats:
        try:
            return datetime.strptime(value, f)
        except:
            continue
    return None


def is_pronostico_abierto_para_carrera(carrera_row):
    """
    Determina si el pronóstico está abierto comparando ahora con
    carrera_row['clasificacion'] si existe, si no con carrera_row['fecha'] (00:00 fallback).
    """
    # Preferimos campo 'clasificacion'
    clasif_field = None
    try:
        clasif_field = carrera_row["clasificacion"]
    except Exception:
        clasif_field = None

    if not clasif_field:
        # fallback a 'fecha' (solo fecha); asumimos que la clasificación es el día anterior a la carrera o a las 12:00.
        fecha_field = None
        try:
            fecha_field = carrera_row["fecha"]
        except Exception:
            fecha_field = None
        if not fecha_field:
            return True  # no hay información -> permitir por defecto (o podrías bloquear)
        d = parse_datetime_field(fecha_field)
        if d:
            # asumimos clasificación a las 12:00 del día de carrera (puedes ajustar)
            clasif_dt = datetime(d.year, d.month, d.day, 12, 0, 0)
        else:
            return True
    else:
        clasif_dt = parse_datetime_field(clasif_field)
        if not clasif_dt:
            # intenta parsear como fecha simple
            d = parse_datetime_field(carrera_row.get("fecha"))
            if d:
                clasif_dt = datetime(d.year, d.month, d.day, 12, 0, 0)
            else:
                return True

    ahora = datetime.now()
    return ahora < clasif_dt


def tiempo_restante_clasificacion(carrera_row):
    """
    Retorna el string con tiempo restante (hh:mm:ss) o 'Cerrado' si ya pasó.
    """
    # mismo manejo que is_pronostico_abierto_para_carrera
    clasif_field = carrera_row.get("clasificacion") if "clasificacion" in carrera_row.keys() else carrera_row.get("fecha")
    if not clasif_field:
        return "Sin fecha"
    dt = parse_datetime_field(clasif_field)
    if not dt:
        return "Sin fecha"
    # si solo tiene fecha (sin hora) asumimos 12:00
    if dt.hour == 0 and dt.minute == 0 and " " not in str(clasif_field):
        dt = datetime(dt.year, dt.month, dt.day, 12, 0, 0)
    ahora = datetime.now()
    delta = dt - ahora
    if delta.total_seconds() <= 0:
        return "Cerrado"
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h"
    return f"{hours}h {minutes}m"


# -------------------- Rutas pronósticos --------------------

@app.route("/mis_pronosticos")
def mis_pronosticos():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # traer carreras y si el usuario ya cargó pronóstico
    cur.execute("""
        SELECT c.*, 
               (SELECT 1 FROM pronosticos p WHERE p.usuario_id = ? AND p.carrera_id = c.id) AS tiene_pronostico
        FROM carreras c
        ORDER BY id ASC
    """, (session["user_id"],))
    carreras = cur.fetchall()
    conn.close()

    # pasamos la función tiempo_restante y is_pronostico_abierto a la plantilla
    return render_template("mis_pronosticos.html",
                           carreras=carreras,
                           tiempo_restante_clasificacion=tiempo_restante_clasificacion,
                           is_pronostico_abierto=is_pronostico_abierto_para_carrera)


@app.route("/pronostico/<int:carrera_id>", methods=["GET", "POST"])
def pronostico_por_carrera(carrera_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Traer carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()
    if not carrera:
        conn.close()
        return "Carrera no encontrada.", 404

    # Traer pilotos para selects
    cur.execute("SELECT id, nombre, equipo FROM pilotos ORDER BY nombre")
    pilotos = cur.fetchall()

    # Traer pronostico existente del usuario (si hay)
    cur.execute("""
        SELECT * FROM pronosticos
        WHERE usuario_id = ? AND carrera_id = ?
    """, (session["user_id"], carrera_id))
    existente = cur.fetchone()

    abierto = is_pronostico_abierto_para_carrera(carrera)

    # POST - guardar o actualizar
    if request.method == "POST":
        if not abierto:
            conn.close()
            return render_template("pronostico_form.html",
                                   carrera=carrera,
                                   pilotos=pilotos,
                                   existente=existente,
                                   abierto=False,
                                   error="La carga del pronóstico ya está cerrada.")

        # obtener ids de pilotos desde el form
        poleman = request.form.get("poleman")
        sprint_ganador = request.form.get("sprint_ganador") or None
        p1 = request.form.get("p1")
        p2 = request.form.get("p2")
        p3 = request.form.get("p3")

        # validaciones
        if not poleman or not p1 or not p2 or not p3:
            conn.close()
            return render_template("pronostico_form.html",
                                   carrera=carrera, pilotos=pilotos, existente=existente, abierto=abierto,
                                   error="Completar pole y podio (p1, p2, p3).")

        # no repetir en el podio
        if len({p1, p2, p3}) != 3:
            conn.close()
            return render_template("pronostico_form.html",
                                   carrera=carrera, pilotos=pilotos, existente=existente, abierto=abierto,
                                   error="No se pueden repetir pilotos en el podio.")

        fecha_carga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existente:
            cur.execute("""
                UPDATE pronosticos
                SET poleman = ?, sprint_ganador = ?, podio_1 = ?, podio_2 = ?, podio_3 = ?, fecha_carga = ?
                WHERE id = ?
            """, (poleman, sprint_ganador, p1, p2, p3, fecha_carga, existente["id"]))
        else:
            # insertar nuevo
            cur.execute("""
                INSERT INTO pronosticos (usuario_id, carrera_id, poleman, sprint_ganador, podio_1, podio_2, podio_3, fecha_carga)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session["user_id"], carrera_id, poleman, sprint_ganador, p1, p2, p3, fecha_carga))

        conn.commit()
        # recargar existente para mostrar edición si se desea
        cur.execute("""
            SELECT * FROM pronosticos WHERE usuario_id = ? AND carrera_id = ?
        """, (session["user_id"], carrera_id))
        existente = cur.fetchone()

        conn.close()
        return redirect("/mis_pronosticos")

    # GET -> mostrar formulario
    conn.close()
    return render_template("pronostico_form.html",
                           carrera=carrera,
                           pilotos=pilotos,
                           existente=existente,
                           abierto=abierto)
# ---------- CARGA / EDICIÓN DE PRONÓSTICO ----------
@app.route("/pronostico/<int:carrera_id>", methods=["GET", "POST"])
def pronostico(carrera_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Traer datos de la carrera
    cur.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,))
    carrera = cur.fetchone()
    if not carrera:
        conn.close()
        return "Carrera no encontrada"

    # ----------- CONTROL DE PLAZO -------------
    # No permitir cargar si ya pasó la clasificación
    from datetime import datetime, time

    hoy = datetime.now().date()
    ahora = datetime.now().time()

    fecha_clasificacion = carrera["fecha_clasificacion"]
    hora_clasificacion = carrera["hora_clasificacion"]

    # Si la clasificación es HOY pero ya pasó la hora
    if fecha_clasificacion < str(hoy) or (
        fecha_clasificacion == str(hoy) and hora_clasificacion < ahora.strftime("%H:%M")
    ):
        cierre = True
    else:
        cierre = False

    # Traer lista de pilotos
    cur.execute("SELECT id, nombre, dorsal FROM pilotos ORDER BY nombre ASC")
    pilotos = cur.fetchall()

    # Ver si ya existe un pronóstico del usuario para esta carrera
    cur.execute("""
        SELECT * FROM pronosticos
        WHERE carrera_id = ? AND usuario_id = ?
    """, (carrera_id, session["user_id"]))
    pronostico = cur.fetchone()

    # Si llegan datos por POST (guardar pronóstico)
    if request.method == "POST":
        if cierre:
            return "El plazo para cargar pronósticos ya cerró."

        pole = request.form["poleman"]
        sprint = request.form.get("sprint")  # puede no existir
        p1 = request.form["p1"]
        p2 = request.form["p2"]
        p3 = request.form["p3"]

        # impedir repetidos en podio
        if len({p1, p2, p3}) < 3:
            return "Los pilotos del podio no pueden repetirse."

        if pronostico:  # EDITAR
            cur.execute("""
                UPDATE pronosticos
                SET poleman=?, sprint=?, p1=?, p2=?, p3=?
                WHERE carrera_id=? AND usuario_id=?
            """, (pole, sprint, p1, p2, p3, carrera_id, session["user_id"]))
        else:  # NUEVO
            cur.execute("""
                INSERT INTO pronosticos
                (carrera_id, usuario_id, poleman, sprint, p1, p2, p3)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (carrera_id, session["user_id"], pole, sprint, p1, p2, p3))

        conn.commit()
        conn.close()
        return redirect("/calendario")

    conn.close()
    return render_template("pronostico.html",
                           carrera=carrera,
                           pilotos=pilotos,
                           pronostico=pronostico,
                           cierre=cierre)


# -------- INICIAR APP --------
if __name__ == "__main__":
    print("Flask está iniciando en http://localhost:5000 ...")
    app.run(debug=True)