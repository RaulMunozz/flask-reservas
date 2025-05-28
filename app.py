from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'clave-secreta'  # Necesaria para mensajes flash

# Conexión a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('reservas.db')
    conn.row_factory = sqlite3.Row
    return conn

# Filtro para convertir texto a datetime
@app.template_filter('todatetime')
def todatetime(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M")

# Página principal con formulario
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

        # Guardar la reserva en un solo campo de fecha completa
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

# Página que muestra todas las reservas
@app.route('/reservas')
def mostrar_reservas():
    conn = get_db_connection()
    reservas = conn.execute('SELECT * FROM reservas ORDER BY fecha').fetchall()
    conn.close()
    ahora = datetime.now()
    return render_template('reservas.html', reservas=reservas, ahora=ahora)

if __name__ == '__main__':
    app.run(debug=True)
