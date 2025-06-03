from flask import Flask, render_template, request, redirect
import mysql.connector
from datetime import datetime, timedelta

# Configura tu conexión MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'sparvoli'
}

# Datos
id_profesional = 1
hora_inicio = datetime.strptime("08:00", "%H:%M")
hora_fin = datetime.strptime("17:00", "%H:%M")
intervalo = timedelta(minutes=20)

# Rango de fechas (por ejemplo: próximos 7 días desde hoy)
hoy = datetime.today()
dias = [(hoy + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

# Conexión y carga
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

for dia in dias:
    hora_actual = hora_inicio
    while hora_actual < hora_fin:
        cursor.execute("""
            SELECT COUNT(*) FROM turnos
            WHERE id_profesional = %s AND dia = %s AND turno = %s
        """, (id_profesional, dia, hora_actual.time()))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO turnos (id_profesional, dia, turno)
                VALUES (%s, %s, %s)
            """, (id_profesional, dia, hora_actual.time()))
        hora_actual += intervalo

conn.commit()
cursor.close()
conn.close()
print("Turnos generados correctamente")
