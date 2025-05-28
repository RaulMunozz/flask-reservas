import sqlite3

conn = sqlite3.connect('reservas.db')
cursor = conn.cursor()

# Borrar reservas que solo tienen la fecha (sin hora)
cursor.execute("DELETE FROM reservas WHERE LENGTH(fecha) = 10")
conn.commit()
conn.close()

print("Reservas sin hora eliminadas correctamente.")
