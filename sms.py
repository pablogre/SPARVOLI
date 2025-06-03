from twilio.rest import Client

aload_dotenv()  # Carga las variables del archivo .env

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

message = client.messages.create(
  from_='+44 7426 797437',  # Este debe ser un número de Twilio habilitado para SMS
  body='Atento Dr. Fabircio Pablo Sparvoli este es un mensaje desde su sistema de asignacion de turnos a la brevedad estará online😃',
  to='+543364537093'     # Cualquier número válido con código de país
)

print(message.sid)
