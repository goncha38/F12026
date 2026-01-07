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
@app.route("/pilotos", methods=["GET", "POST"])
def pilotos():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

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



# -------- INICIAR APP --------
if __name__ == "__main__":
    print("Flask está iniciando en http://localhost:5000 ...")
    app.run(debug=True)