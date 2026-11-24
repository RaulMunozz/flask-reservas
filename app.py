import hmac
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta

from flask import (
    Flask,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

app = Flask(__name__)


def _load_secret_key():
    configured = os.environ.get("SECRET_KEY")
    if configured:
        return configured

    # Local fallback: persist a random key so sessions survive restarts and workers.
    path = os.path.join(app.instance_path, "secret_key")
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        with open(path, "rb") as handle:
            data = handle.read()
            if data:
                return data
    except OSError:
        pass

    data = secrets.token_bytes(32)
    try:
        with open(path, "wb") as handle:
            handle.write(data)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except OSError:
        pass
    return data


app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "1") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    MAX_CONTENT_LENGTH=8 * 1024,
)
if app.config["SESSION_COOKIE_SECURE"]:
    app.config["SESSION_COOKIE_NAME"] = "__Host-session"

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "reservas.db")

_login_attempts = {}
_attempts_lock = threading.Lock()


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT,
                correo TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


init_db()


@app.template_filter("todatetime")
def todatetime(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


@app.context_processor
def inject_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"]}


@app.before_request
def csrf_protect():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        sent = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not secrets.compare_digest(sent, expected):
            abort(400, "CSRF token inválido")


@app.after_request
def harden_responses(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'none'; object-src 'none'; "
        "style-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:; "
        "form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests",
    )
    if os.environ.get("HSTS", "0") == "1":
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return resp


def login_rate_limited(key, limit=5, window_seconds=300):
    now = time.time()
    with _attempts_lock:
        recent = [t for t in _login_attempts.get(key, []) if now - t < window_seconds]
        _login_attempts[key] = recent
        if len(recent) >= limit:
            return True
        recent.append(now)
        return False


def valid_reservation(nombre, fecha, hora):
    nombre = (nombre or "").strip()
    if not nombre or len(nombre) > 100:
        return None

    if not fecha or len(fecha) != 10 or not hora or len(hora) != 5:
        return None

    try:
        fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None

    if fecha_hora < datetime.now() or fecha_hora.minute % 15 != 0:
        return None

    return nombre, fecha_hora.strftime("%Y-%m-%d %H:%M")


@app.route("/", methods=["GET", "POST"])
def reservar():
    if request.method == "POST":
        valid = valid_reservation(
            request.form.get("nombre"),
            request.form.get("fecha"),
            request.form.get("hora"),
        )
        if not valid:
            flash("Datos de reserva no válidos.", "danger")
            return redirect(url_for("reservar"))

        nombre, fecha_hora = valid
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO reservas (nombre, fecha) VALUES (?, ?)",
                (nombre, fecha_hora),
            )
            conn.commit()
        finally:
            conn.close()

        flash("Reserva realizada con éxito.", "success")
        return redirect(url_for("reservar"))

    return render_template("formulario.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        if login_rate_limited(ip):
            return "Demasiados intentos. Inténtalo más tarde.", 429

        if not ADMIN_PASSWORD_HASH:
            app.logger.error("ADMIN_PASSWORD_HASH is not configured")
            return "Login no configurado", 503

        usuario = request.form.get("usuario", "")
        password = request.form.get("password", "")
        if hmac.compare_digest(usuario, ADMIN_USER) and check_password_hash(
            ADMIN_PASSWORD_HASH, password
        ):
            session.clear()
            session["admin"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            with _attempts_lock:
                _login_attempts.pop(ip, None)
            flash("Has iniciado sesión como administrador.", "success")
            return redirect(url_for("mostrar_reservas"))

        app.logger.warning("Login fallido para usuario=%r desde %s", usuario, ip)
        flash("Credenciales incorrectas.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("reservar"))


@app.route("/reservas")
def mostrar_reservas():
    if not session.get("admin"):
        flash("Acceso restringido. Inicia sesión como administrador.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        reservas = conn.execute("SELECT * FROM reservas ORDER BY fecha").fetchall()
    finally:
        conn.close()

    resp = make_response(
        render_template("reservas.html", reservas=reservas, ahora=datetime.now())
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
