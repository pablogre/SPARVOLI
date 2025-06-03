import mysql.connector
from twilio.rest import Client
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Configuración de Twilio
load_dotenv()  # Carga las variables del archivo .env

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

# Número SMS comprado (por ejemplo, Reino Unido)
twilio_sms_number = '+44 7426 797437'  # ← Reemplazá con el tuyo

# Conexión a la base de datos
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="sparvoli"
)
cursor = conn.cursor()

# Obtener la fecha de mañana
mañana = (datetime.now() + timedelta(days=1)).date()

# Buscar turnos reservados para mañana
cursor.execute("SELECT paciente, telefono, dia, turno FROM turnos WHERE paciente != '' AND dia = %s", (mañana,))
turnos = cursor.fetchall()
if not turnos:
    print("No hay mensajes que mandar")

# Enviar SMS
for paciente, telefono, dia, hora in turnos:
    # Convertir hora (timedelta) a formato HH:MM
    hora_str = (datetime.min + hora).strftime('%H:%M')
    mensaje = f"Hola {paciente}, te recordamos tu turno para el {dia.strftime('%d/%m/%Y')} a las {hora_str} hs."
    print("telefono: ",telefono)
    try:
        message = client.messages.create(
            from_=twilio_sms_number,
            to= '+54'+telefono,  # Debe ser en formato internacional, ej: +5493364537093
            body=mensaje
        )
        print(f"✅ SMS enviado a {paciente} ({telefono})")
    except Exception as e:
        print(f"❌ Error enviando SMS a {telefono}: {e}")

cursor.close()
conn.close()
