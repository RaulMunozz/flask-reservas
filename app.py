from flask import Flask, render_template, request
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

app = Flask(__name__)

# Carga la URL de la base de datos desde una variable de entorno
DATABASE_URL = os.environ.get("DATABASE_URL")

# Configura la conexión a PostgreSQL
engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()

class Reserva(Base):
    __tablename__ = 'reservas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    fecha = Column(String)
    hora = Column(String)
    correo = Column(String)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

@app.route('/', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        fecha = request.form['fecha']
        hora = request.form['hora']
        correo = request.form['correo']

        nueva_reserva = Reserva(nombre=nombre, fecha=fecha, hora=hora, correo=correo)
        session = Session()
        session.add(nueva_reserva)
        session.commit()
        session.close()

        return f"Reserva enviada para {nombre} a las {hora} del {fecha}. ¡Gracias!"

    return render_template('formulario.html')

@app.route('/reservas')
def ver_reservas():
    session = Session()
    reservas = session.query(Reserva).all()
    session.close()
    return render_template('reservas.html', reservas=reservas)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
