# test_env.py
import os
from dotenv import load_dotenv

load_dotenv()

print("TWILIO_ACCOUNT_SID =", os.getenv("TWILIO_ACCOUNT_SID"))
print("TWILIO_AUTH_TOKEN =", os.getenv("TWILIO_AUTH_TOKEN"))
print("TWILIO_PHONE_NUMBER =", os.getenv("TWILIO_PHONE_NUMBER"))

if not all([os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"), os.getenv("TWILIO_PHONE_NUMBER")]):
    print("❌ Faltan variables de entorno o no se están leyendo.")
else:
    print("✅ Todas las variables están cargadas correctamente.")
