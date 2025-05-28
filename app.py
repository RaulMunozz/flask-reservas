from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'clave-secreta'

# Configuración del admin (puedes cambiar estos valores)
ADMIN_USER = 'admin'
ADMIN_PASSWORD = '1234'

def get_db_connection():
    conn = sqlite3.connect('reservas.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.template_filter('todatetime')
def todatetime(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M")

@app.route('/', methods=['GET', 'POST'])
def reservar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        fecha = request.form['fecha']
        hora = request.form['hora']

        if not nombre or not fecha or not hora:
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('reservar'))

        try:
            fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Fecha u hora no válidas.", "danger")
            return redirect(url_for('reservar'))

        if fecha_hora < datetime.now():
            flash("No puedes reservar en una fecha pasada.", "danger")
            return redirect(url_for('reservar'))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO reservas (nombre, fecha) VALUES (?, ?)',
            (nombre, fecha_hora.strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
        conn.close()

        flash("Reserva realizada con éxito.", "success")
        return redirect(url_for('reservar'))

    return render_template('formulario.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        if usuario == ADMIN_USER and password == ADMIN_PASSWORD:
            session['admin'] = True
            flash("Has iniciado sesión como administrador.", "success")
            return redirect(url_for('mostrar_reservas'))
        else:
            flash("Credenciales incorrectas.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash("Sesión cerrada.", "info")
    return redirect(url_for('reservar'))

@app.route('/reservas')
def mostrar_reservas():
    if not session.get('admin'):
        flash("Acceso restringido. Inicia sesión como administrador.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    reservas = conn.execute('SELECT * FROM reservas ORDER BY fecha').fetchall()
    conn.close()
    ahora = datetime.now()
    return render_template('reservas.html', reservas=reservas, ahora=ahora)

if __name__ == '__main__':
    app.run(debug=True)
