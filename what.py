from twilio.rest import Client

from dotenv import load_dotenv
import os

load_dotenv()  # <-- Esto carga las variables del .env
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

message = client.messages.create(
  from_='whatsapp:+14155238886',  # Este es el número fijo de Twilio Sandbox
  body='Hola, este es un mensaje de prueba por WhatsApp desde Flask 😃',
  to='whatsapp:+543364537093'     # Debe estar unido al sandbox (haber enviado el código)
)

print(message.sid)
