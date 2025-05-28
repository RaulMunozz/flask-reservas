import sqlite3

conn = sqlite3.connect('reservas.db')
cursor = conn.cursor()

cursor.execute('SELECT fecha, hora FROM reservas LIMIT 10')
reservas = cursor.fetchall()

print("Reservas encontradas:\n")
for r in reservas:
    print(f"{r[0]} {r[1]}")

conn.close()
