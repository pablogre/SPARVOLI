
import pymysql
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
conn = pymysql.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 3306)),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

# Obtener la fecha de mañana
mañana = (datetime.now() + timedelta(days=1)).date()
#mañana = datetime.now().date()
#print("dia=", mañana)
# Buscar turnos reservados para mañana
cursor.execute("SELECT paciente, telefono, dia, turno FROM turnos WHERE paciente != '' AND dia = %s", (mañana,))
turnos = cursor.fetchall()

print(turnos)
if not turnos:
    print("No hay mensajes que mandar")

# Enviar SMS
# Enviar SMS
for turno in turnos:
    paciente = turno['paciente']
    telefono = str(turno['telefono'])
    dia = turno['dia']
    hora = turno['turno']

    # Convertir hora (timedelta) a formato HH:MM
    if isinstance(hora, str):
        hora_str = hora
    else:
        hora_str = (datetime.min + hora).strftime('%H:%M')

    # Convertir fecha
    if isinstance(dia, str):
        dia_str = dia
    else:
        dia_str = dia.strftime('%d/%m/%Y')

    mensaje = f"Hola {paciente}, te recordamos tu turno con el Dr. Sparvoli para el {dia_str} a las {hora_str} hs."

    print(mensaje)
    print("telefono:", telefono)

    try:
        message = client.messages.create(
            from_=twilio_sms_number,
            to='+54' + telefono,  # Agregá el código de país si hace falta
            body=mensaje
        )
        print(f"✅ SMS enviado a {paciente} ({telefono})")
    except Exception as e:
        print(f"❌ Error enviando SMS a {telefono}: {e}")

cursor.close()
conn.close()
