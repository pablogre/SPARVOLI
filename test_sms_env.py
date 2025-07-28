from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
test_number = "+543364007200"  # Poné tu número para prueba con código país

client = Client(account_sid, auth_token)

try:
    message = client.messages.create(
        body="Hola Ceci la verdad que no supe más nada de vos y solo quiero saber si estás bien",
        from_=twilio_number,
        to=test_number
    )
    print("Mensaje enviado, SID:", message.sid)
    
except Exception as e:
    print("Error enviando mensaje:", e)
