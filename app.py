from flask import Flask, render_template, request, redirect, flash, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
# Al principio del archivo, después de los imports existentes
#from email_functions import enviar_email_confirmacion, enviar_email_recordatorio, procesar_recordatorios, generar_token_cancelacion
import pymysql
import time
from datetime import datetime, timedelta, date
import re
from twilio.rest import Client
from dotenv import load_dotenv
import os



app = Flask(__name__)

app.secret_key = 'clave_secreta_segura'

def clean_env(var_name: str) -> str:
    raw = os.getenv(var_name, "")
    # Elimina comillas simples o dobles al inicio y al final
    return raw.strip('\'"')


load_dotenv()  # Carga las variables del archivo .env


# Configuración de la base de datos no se usa
""" DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'sparvoli'
} """

conexion = pymysql.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 3306)),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

####### enviar_mensage #######

def enviar_mensage():
    load_dotenv()  # <-- Esto carga las variables del .env
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    client = Client(account_sid, auth_token)

    message = client.messages.create(
    from_='+19786437420',
     body='hola estoy probando !!!',
    to='+543364537093'
    )
    print(message.sid)
    return 


def enviar_whatsapp(paciente, telefono, fecha, hora):
    load_dotenv()  # <-- Esto carga las variables del .env
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    client = Client(account_sid, auth_token)

    mensaje = f"Hola {paciente}, tu turno ha sido reservado con el Dr. Sparvoli para el día {fecha} a las {hora}. Gracias."

    try:
        message = client.messages.create(
            from_='whatsapp:+14155238886',  # Sandbox Twilio WhatsApp
            body=mensaje,
            to=f'whatsapp:{telefono}'       # El número del paciente con formato internacional
        )
        print("Mensaje enviado:", message.sid)
    except Exception as e:
        print("Error al enviar WhatsApp:", e)

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def formatear_numero_argentino(numero):
    """
    Formatea un número argentino al formato internacional +54...
    """
    # Eliminar todo lo que no sea número
    numero = re.sub(r'\D', '', numero)

    # Eliminar 0 inicial si está
    if numero.startswith('0'):
        numero = numero[1:]

    # Agregar prefijo de Argentina
    return f'+54{numero}'

def generar_turnos(fecha):
    id_profesional = 1
    dia_semana = datetime.strptime(fecha, "%Y-%m-%d").weekday()

    # 🚫 No generar si es viernes
    if dia_semana == 4:
        print("❌ Viernes: no se generan turnos.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔒 Verificar si hay bloqueo para esa fecha
    cursor.execute("SELECT hora_desde FROM fechas_bloqueadas WHERE fecha = %s", (fecha,))
    bloqueo = cursor.fetchone()

    hora_bloqueada = None
    if bloqueo and bloqueo['hora_desde'] is not None:
        if isinstance(bloqueo['hora_desde'], str):
            hora_bloqueada = datetime.strptime(bloqueo['hora_desde'], "%H:%M:%S").time()
        else:
            hora_bloqueada = bloqueo['hora_desde']

    # 🕒 Definir hora inicio y fin de turnos
    hora_inicio = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("13:00", "%H:%M") if dia_semana == 1 else datetime.strptime("14:20", "%H:%M")
    intervalo = timedelta(minutes=20)

    hora_actual = hora_inicio

    while hora_actual < hora_fin:
        hora_str = hora_actual.strftime("%H:%M")

        # ⏱️ Saltar si la hora está bloqueada (parcial)
        if hora_bloqueada and hora_actual.time() >= hora_bloqueada:
            print(f"⏩ Turno {hora_str} bloqueado desde {hora_bloqueada}")
            hora_actual += intervalo
            continue

        cursor.execute("""
            SELECT COUNT(*) as cantidad FROM turnos
            WHERE id_profesional = %s AND dia = %s AND turno = %s
        """, (id_profesional, fecha, hora_str))

        if cursor.fetchone()['cantidad'] == 0:
            cursor.execute("""
                INSERT INTO turnos (id_profesional, dia, turno)
                VALUES (%s, %s, %s)
            """, (id_profesional, fecha, hora_str))
            print("✅ Turno generado:", id_profesional, fecha, hora_str)

        hora_actual += intervalo

    conn.commit()
    cursor.close()
    conn.close()


def enviar_sms(nombre, telefono, fecha, hora):
   
    if not os.getenv("TWILIO_ACCOUNT_SID"):
        from dotenv import load_dotenv
        load_dotenv()  # Carga las variables del archivo .env

    '''
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
    '''
    # Limpia posibles comillas agregadas por Railway
    account_sid = clean_env("TWILIO_ACCOUNT_SID")
    auth_token = clean_env("TWILIO_AUTH_TOKEN")
    twilio_number = clean_env("TWILIO_PHONE_NUMBER")

    print("🧪 SID:", account_sid)
    print("🧪 Token is set:", "✅" if auth_token else "❌")
    print("🧪 From Number:", twilio_number)

    if not all([account_sid, auth_token, twilio_number]):
        print("❌ Error: Faltan variables de entorno.")
        print(f"TWILIO_ACCOUNT_SID: {account_sid}")
        print(f"TWILIO_AUTH_TOKEN: {auth_token}")
        print(f"TWILIO_PHONE_NUMBER: {twilio_number}")
        return

    try:
        client = Client(account_sid, auth_token)

        mensaje = f"Hola {nombre}, tu turno ha sido reservado con el Dr. Sparvoli para el día {fecha} a las {hora} hs."

        message = client.messages.create(
            body=mensaje,
            from_=twilio_number,
            to=f'+54{telefono[-10:]}'
        )

        print("✅ SMS enviado:", message.sid)

    except Exception as e:
        print("❌ Error al enviar el SMS:", e)





def generar_token_cancelacion():
    """Genera un token único para cancelación"""
    return secrets.token_urlsafe(32)

def enviar_email_confirmacion(nombre, email, fecha, hora, turno_id):
    """Envía email de confirmación al reservar el turno"""
    try:
        # CAMBIO: Usar SMTP_USER y SMTP_PASSWORD en lugar de EMAIL_USER y EMAIL_PASSWORD
        """ smtp_server = clean_env("SMTP_SERVER") or "smtp.gmail.com"
        smtp_port = int(clean_env("SMTP_PORT") or "587")
        email_user = clean_env("SMTP_USER")  # CAMBIO AQUÍ
        email_password = clean_env("SMTP_PASSWORD")  # CAMBIO AQUÍ """
        

        smtp_server = "smtp.gmail.com"
        smtp_port = 465
        email_user = "consultoriosparvoli@gmail.com"
        email_password = "rter jhov vucq zztn"
        
        print("🧪 USANDO VALORES HARDCODEADOS")
        print(f"Email user: {email_user}")
        print(f"Password configurado: SI")



        # Debug detallado
        print("🔍 DEBUG EMAIL:")
        print(f"SMTP_SERVER: {smtp_server}")
        print(f"SMTP_PORT: {smtp_port}")
        print(f"SMTP_USER: {'✅ Configurado' if email_user else '❌ Vacío'}")
        print(f"SMTP_PASSWORD: {'✅ Configurado' if email_password else '❌ Vacío'}")
        
        if not all([email_user, email_password]):
            print("❌ Error: Faltan credenciales de email")
            return False

        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email
        msg['Subject'] = "Confirmación de Turno - Dr. Sparvoli"

        # [resto del código igual...]
        cuerpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c5aa0;">Confirmación de Turno Médico</h2>
                
                <p>Estimado/a <strong>{nombre}</strong>,</p>
                
                <p>Su turno ha sido <strong>confirmado</strong> con los siguientes datos:</p>
                
                <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0;">
                    <p><strong>📅 Fecha:</strong> {fecha}</p>
                    <p><strong>🕐 Hora:</strong> {hora} hs</p>
                    <p><strong>👨‍⚕️ Médico:</strong> Dr. Sparvoli</p>
                </div>
                
                <p><strong>Importante:</strong></p>
                <ul>
                    <li>Llegue 10 minutos antes de su turno</li>
                    <li>Traiga su documento de identidad y obra social</li>
                    <li>Recibirá un recordatorio 24 horas antes</li>
                </ul>
                
                <div style="margin: 30px 0; text-align: center;">
                    <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/cancelar_turno/{turno_id}" 
                       style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        🗑️ Cancelar Turno
                    </a>
                </div>
                
                <p style="font-size: 12px; color: #666; margin-top: 30px;">
                    Si necesita reprogramar o tiene consultas, por favor comuníquese al consultorio.<br>
                    Tel: 4450551 - 3364176855 Este es un email automático, no responda a esta dirección.
                </p>
                <div class="mt-3 text-center">
                    <small>
                        <a href="https://pablore.com.ar" target="_blank" class="text-muted text-decoration-none" 
                           style="font-size: 0.75rem;">
                            Desarrollado por Pablo G. Ré
                        </a>
                    </small>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo, 'html'))

        # Enviar email
        print("🔄 Intentando conectar a SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        print("🔐 Intentando autenticar...")
        server.login(email_user, email_password)
        print("📧 Enviando mensaje...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email de confirmación enviado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar email de confirmación: {e}")
        print(f"❌ Tipo de error: {type(e).__name__}")
        return False

# También actualizar la ruta de debug
@app.route("/debug_email_vars")
def debug_email_vars():
    return {
        "HARDCODED_TEST": "Variables hardcodeadas para debugging",
        "SMTP_USER_hardcoded": "consultoriosparvoli@gmail.com",
        "SMTP_PASSWORD_hardcoded": "rter jhov vucq zztn",
        "SMTP_SERVER_hardcoded": "smtp.gmail.com",
        "SMTP_PORT_hardcoded": "465",
        "VARIABLES_DESDE_RAILWAY": {
            "SMTP_USER_raw": os.getenv("SMTP_USER"),
            "SMTP_PASSWORD_exists": "SÍ" if os.getenv("SMTP_PASSWORD") else "NO",
            "SMTP_SERVER": os.getenv("SMTP_SERVER"),
            "SMTP_PORT": os.getenv("SMTP_PORT")
        }
    }


def enviar_email_recordatorio(nombre, email, fecha, hora, turno_id):
    """Envía email recordatorio 24 horas antes del turno"""
    try:
        # Configuración SMTP
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")

        if not all([email_user, email_password]):
            print("❌ Error: Faltan credenciales de email")
            return False

        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email
        msg['Subject'] = "Recordatorio de Turno - Dr. Sparvoli (Mañana)"

        # Cuerpo del email
        cuerpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">⏰ Recordatorio de Turno</h2>
                
                <p>Estimado/a <strong>{nombre}</strong>,</p>
                
                <p>Le recordamos que <strong>mañana</strong> tiene turno médico:</p>
                
                <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0;">
                    <p><strong>📅 Fecha:</strong> {fecha}</p>
                    <p><strong>🕐 Hora:</strong> {hora} hs</p>
                    <p><strong>👨‍⚕️ Médico:</strong> Dr. Sparvoli</p>
                </div>
                
                <p><strong>Recuerde:</strong></p>
                <ul>
                    <li>✅ Llegar 10 minutos antes</li>
                    <li>🆔 Traer documento de identidad</li>
                    <li>💳 Traer credencial de obra social</li>
                    <li>📋 Si tiene estudios previos, tráigalos</li>
                </ul>
                
                <div style="margin: 30px 0; text-align: center;">
                    <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/cancelar_turno/{turno_id}" 
                       style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        🗑️ Cancelar Turno
                    </a>
                </div>
                
                <p style="font-size: 12px; color: #666; margin-top: 30px;">
                    Si necesita reagendar, hágalo con anticipación.<br>
                    Este es un email automático, no responda a esta dirección.
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo, 'html'))

        # Enviar email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        
        print("✅ Email recordatorio enviado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar email recordatorio: {e}")
        return False


def procesar_recordatorios():
    """Procesa y envía recordatorios para turnos del día siguiente"""
    try:
        from datetime import datetime, timedelta
        manana = (datetime.now() + timedelta(days=1)).date()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar turnos para mañana que tengan email y no se haya enviado recordatorio
        cursor.execute("""
            SELECT id, paciente, email, dia, turno, recordatorio_enviado
            FROM turnos 
            WHERE dia = %s 
            AND paciente != '' 
            AND email IS NOT NULL 
            AND email != '' 
            AND (recordatorio_enviado IS NULL OR recordatorio_enviado = 0)
        """, (manana,))
        
        turnos = cursor.fetchall()
        enviados = 0
        
        for turno in turnos:
            # Formatear hora
            total_sec = turno['turno'].seconds
            horas = total_sec // 3600
            minutos = (total_sec % 3600) // 60
            hora_str = f"{horas:02d}:{minutos:02d}"
            
            fecha_str = turno['dia'].strftime("%d/%m/%Y")
            
            if enviar_email_recordatorio(
                turno['paciente'], 
                turno['email'], 
                fecha_str, 
                hora_str,
                turno['id']  # Pasamos el ID directamente
            ):
                # Marcar como enviado
                cursor.execute("""
                    UPDATE turnos SET recordatorio_enviado = 1 WHERE id = %s
                """, (turno['id'],))
                enviados += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Procesados {enviados} recordatorios de {len(turnos)} turnos")
        return enviados
        
    except Exception as e:
        print(f"❌ Error procesando recordatorios: {e}")
        return 0


##################################################################################################################################
#
#                                 RUTAS DEL SISTEMA
##################################################################################################################################

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    turnos = []
    dia = None
    mensaje = None
    hoy = date.today().isoformat()
    ahora = datetime.now().time()

    if request.method == "POST":
        dia = request.form["fecha"]
    else:
        # 🧠 Buscar la próxima fecha con turnos disponibles (paciente vacío)
        cursor.execute("""
            SELECT dia FROM turnos 
            WHERE dia >= %s AND paciente = '' 
            ORDER BY dia ASC, turno ASC 
            LIMIT 1
        """, (hoy,))
        resultado = cursor.fetchone()
        if resultado:
            dia = resultado["dia"].isoformat()
        else:
            mensaje = "No hay turnos disponibles en los próximos días."

    if dia:
        dia_semana = datetime.strptime(dia, "%Y-%m-%d").weekday()

        # Validar límite de fechas
        fecha_limite = "2025-07-03"
        if dia < fecha_limite:
            mensaje = "No se pueden reservar turnos para fechas anteriores al 3 de julio de 2025."
        elif dia_semana in (5, 6):
            mensaje = "No hay turnos disponibles para este día."
        else:
            def consultar_turnos():
                if dia == hoy:
                    cursor.execute("""
                        SELECT * FROM turnos 
                        WHERE paciente = '' AND dia = %s AND turno > %s
                    """, (dia, ahora))
                else:
                    cursor.execute("""
                        SELECT * FROM turnos 
                        WHERE paciente = '' AND dia = %s
                    """, (dia,))
                return cursor.fetchall()

            turnos = consultar_turnos()

            if not turnos:
                generar_turnos(dia)
                cursor.close()
                conn.close()
                conn = get_db_connection()
                cursor = conn.cursor()
                turnos = consultar_turnos()

                if not turnos:
                    if dia == hoy:
                        mensaje = "Ya pasaron todos los turnos disponibles para hoy."
                    else:
                        mensaje = "No hay turnos disponibles para este día."

        for t in turnos:
            try:
                t["turno_str"] = t["turno"].strftime("%H:%M")
            except:
                total_seg = t["turno"].seconds if hasattr(t["turno"], "seconds") else 0
                horas = total_seg // 3600
                minutos = (total_seg % 3600) // 60
                t["turno_str"] = f"{horas:02d}:{minutos:02d}"

    cursor.close()
    conn.close()
    return render_template("index.html", turnos=turnos, fecha=dia, mensaje=mensaje)


############## reservar turno 
@app.route("/reservar", methods=["POST"])
def reservar():
    turno_id = request.form["turno_id"]
    paciente = request.form["paciente"]
    o_social = request.form["o_social"]
    telefono = request.form["telefono"]
    email = request.form["email"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Buscar el turno para obtener fecha y hora antes de actualizar
    cursor.execute("SELECT dia, turno FROM turnos WHERE id = %s", (turno_id,))
    turno_data = cursor.fetchone()
    dia = turno_data['dia'].strftime("%d/%m/%Y")
    # turno_data[1] es timedelta, por ejemplo: 2:20:00
    horas, resto = divmod(turno_data['turno'].seconds, 3600)
    minutos = resto // 60
    hora = f"{horas:02d}:{minutos:02d}"


    if turno_data:
        fecha = turno_data['dia'].strftime("%Y-%m-%d")  # Formato YYYY-MM-DD
        hora = str(turno_data['turno'])[:4]     # Formato HH:MM
    else:
        flash("Turno no encontrado", "error")
        return redirect(url_for("index"))

    # 2. Actualizar los datos del turno con la información del paciente
    cursor.execute("""
        UPDATE turnos SET paciente=%s, o_social=%s, telefono=%s, email=%s
        WHERE id=%s
    """, (paciente, o_social, telefono, email, turno_id))
    conn.commit()
    cursor.close()
    conn.close()

    # Enviamos el SMS lo comento porque no se paga más Twilio
    #enviar_sms(paciente, telefono, dia, hora)

    #  NUEVO: Enviar EMAIL DE CONFIRMACIÓN
    if email and email.strip():  # Solo si se proporcionó email
        try:
            enviar_email_confirmacion(paciente, email, dia, hora, turno_id)
            print("❌  enviando email:") 
        except Exception as e:
            print(f"❌ Error enviando email: {e}")

    """ # 3. Enviar WhatsApp
    print('hora: ', hora)
    enviar_whatsapp(
        paciente=paciente,
        telefono=telefono,
        fecha=fecha,
        hora=hora,
    ) """

    flash("Turno reservado correctamente", "success")
    return redirect(url_for("index"))

@app.route("/consulta", methods=["GET", "POST"])
def consulta():
    conn = get_db_connection()
    cursor = conn.cursor()
    disponibles = []
    reservados = []
    fecha = None
    mensaje = None

    if request.method == "POST":
        fecha = request.form["fecha"]
        hoy = date.today().isoformat()
        ahora = datetime.now().time()

        if fecha < hoy:
            mensaje = "No se pueden consultar turnos para fechas pasadas."
        else:
            # Turnos disponibles
            if fecha == hoy:
                cursor.execute("""
                    SELECT * FROM turnos 
                    WHERE dia = %s AND paciente = '' AND turno > %s
                """, (fecha, ahora))
            else:
                cursor.execute("""
                    SELECT * FROM turnos 
                    WHERE dia = %s AND paciente = ''
                """, (fecha,))
            disponibles = cursor.fetchall()

            # 🔁 Filtrar los que están dentro del rango bloqueado
            cursor.execute("SELECT hora_desde FROM fechas_bloqueadas WHERE fecha = %s", (fecha,))
            bloqueo = cursor.fetchone()
            if bloqueo and bloqueo["hora_desde"]:
                hora_bloqueada = datetime.strptime(str(bloqueo["hora_desde"]), "%H:%M:%S").time()
                disponibles = [t for t in disponibles if t["turno"] < hora_bloqueada]

            # Turnos reservados
            cursor.execute("""
                SELECT * FROM turnos 
                WHERE dia = %s AND paciente != ''
            """, (fecha,))
            reservados = cursor.fetchall()

            # Formatear horas
            for lst in (disponibles, reservados):
                for t in lst:
                    total_sec = t['turno'].seconds
                    horas = total_sec // 3600
                    minutos = (total_sec % 3600) // 60
                    t['turno_str'] = f"{horas:02d}:{minutos:02d}"

        cursor.close()
        conn.close()
        return render_template("consulta.html", disponibles=disponibles, reservados=reservados, fecha=fecha, mensaje=mensaje)

    # ⚠️ Este return FALTABA para método GET
    cursor.close()
    conn.close()
    return render_template("consulta.html", disponibles=[], reservados=[], fecha=None, mensaje=None)



@app.route("/cancelar", methods=["POST"])
def cancelar():
    turno_id = request.form["turno_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE turnos SET paciente='', o_social='', telefono='', email=''
        WHERE id=%s
    """, (turno_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Turno cancelado correctamente", "success")
    return redirect(url_for("consulta"))

@app.route("/bloquear_fechas", methods=["GET", "POST"])
def bloquear_fechas():
    if request.method == "POST":
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin") or fecha_inicio
        hora_desde = request.form.get("hora_desde") or None

        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")

            conn = get_db_connection()
            cursor = conn.cursor()

            fecha_actual = fecha_inicio_dt
            fechas_a_bloquear = []

            while fecha_actual <= fecha_fin_dt:
                fechas_a_bloquear.append(fecha_actual.date())
                cursor.execute("INSERT IGNORE INTO fechas_bloqueadas (fecha, hora_desde) VALUES (%s, %s)", (fecha_actual.date(), hora_desde if hora_desde else None))
                
                # 🔥 Si se especificó una hora, borrar los turnos desde esa hora en adelante
                if hora_desde:
                    cursor.execute("""
                        DELETE FROM turnos
                        WHERE dia = %s AND turno >= %s
                    """, (fecha_actual.date(), hora_desde))

                else:
                    # 🔥 Si no se especificó hora, eliminar todos los turnos del día
                    cursor.execute("""
                        DELETE FROM turnos
                        WHERE dia = %s
                    """, (fecha_actual.date(),))
                
                fecha_actual += timedelta(days=1)

            conn.commit()
            cursor.close()
            conn.close()

            if fechas_a_bloquear:
                flash(f"Se bloquearon {len(fechas_a_bloquear)} fechas.", "success")
            else:
                flash("No se bloquearon fechas nuevas.", "warning")
        except Exception as e:
            print("ERROR AL BLOQUEAR:", e)
            flash("Error al bloquear las fechas.", "danger")

        return redirect(url_for("bloquear_fechas"))

    # GET: Mostrar fechas bloqueadas
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT fecha FROM fechas_bloqueadas ORDER BY fecha")
    fechas_bloqueadas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("bloquear_fechas.html", fechas_bloqueadas=fechas_bloqueadas)


@app.route("/eliminar_fecha_bloqueada", methods=["POST"])
def eliminar_fecha_bloqueada():
    fecha = request.form.get("fecha")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fechas_bloqueadas WHERE fecha = %s", (fecha,))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Fecha {fecha} eliminada correctamente.", "success")
    return redirect(url_for("bloquear_fechas"))

@app.route("/test_twilio_auth")
def test_twilio_auth():
    """ account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN") """
     # Limpia posibles comillas agregadas por Railway
    account_sid = clean_env("TWILIO_ACCOUNT_SID")
    auth_token = clean_env("TWILIO_AUTH_TOKEN")
    
    try:
        client = Client(account_sid, auth_token)
        incoming_numbers = client.incoming_phone_numbers.list(limit=1)
        return f"✅ Conexión exitosa. Número: {incoming_numbers[0].phone_number}" if incoming_numbers else "✅ Autenticado, pero sin números asociados."
    except Exception as e:
        return f"❌ Error de autenticación: {e}"


@app.route("/debug_vars")
def debug_vars():
    return {
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": "✅ Presente" if os.getenv("TWILIO_AUTH_TOKEN") else "❌ Faltante"
    }


# Agregar estas rutas a tu app.py después de las rutas existentes



@app.route("/cancelar_turno/<int:turno_id>", methods=["GET", "POST"])
def cancelar_turno_simple(turno_id):
    """Cancela un turno usando directamente el ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar el turno por ID
    cursor.execute("""
        SELECT id, paciente, dia, turno, email FROM turnos 
        WHERE id = %s AND paciente != ''
    """, (turno_id,))
    
    turno = cursor.fetchone()
    
    if not turno:
        cursor.close()
        conn.close()
        return render_template("cancelacion_resultado.html", 
                             exito=False, 
                             mensaje="Turno no encontrado o ya cancelado.")
    
    if request.method == "POST":
        # EJECUTAR LA CONSULTA QUE PEDISTE
        cursor.execute("""
            UPDATE turnos SET 
                paciente='', 
                o_social='', 
                telefono='', 
                email='',
                token_cancelacion=NULL,
                recordatorio_enviado=NULL
            WHERE id = %s
        """, (turno['id'],))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return render_template("cancelacion_resultado.html", 
                             exito=True, 
                             mensaje="Su turno ha sido cancelado correctamente.")
    
    # GET: Mostrar confirmación
    # Formatear fecha y hora para mostrar
    fecha_formateada = turno['dia'].strftime("%d/%m/%Y")
    total_sec = turno['turno'].seconds
    horas = total_sec // 3600
    minutos = (total_sec % 3600) // 60
    hora_formateada = f"{horas:02d}:{minutos:02d}"
    
    cursor.close()
    conn.close()
    
    return render_template("cancelar_turno.html", 
                         turno=turno,
                         fecha=fecha_formateada,
                         hora=hora_formateada,
                         turno_id=turno_id)

@app.route("/procesar_recordatorios")
def ejecutar_recordatorios():
    """Endpoint para procesar recordatorios (usar con cron job)"""
    enviados = procesar_recordatorios()
    return f"✅ Recordatorios procesados: {enviados}"


@app.route("/test_recordatorio")
def test_recordatorio():
    """Prueba manual de recordatorio"""
    # Cambia estos valores por un turno real de tu BD
    resultado = enviar_email_recordatorio(
        "Usuario Prueba",
        "tu-email@ejemplo.com",  # Cambia por tu email
        "04/09/2025",
        "10:00",
        999  # ID de prueba
    )
    return "✅ Recordatorio de prueba enviado" if resultado else "❌ Error enviando recordatorio"

@app.route("/test_email")
def test_email():
    """Prueba la configuración de email"""
    try:
        # Datos de prueba
        resultado = enviar_email_confirmacion(
            "Usuario Prueba",
            "tu-email@ejemplo.com",  # Cambia por tu email
            "01/01/2025",
            "10:00",
            999
        )
        return "✅ Email de prueba enviado" if resultado else "❌ Error enviando email"
    except Exception as e:
        return f"❌ Error: {e}"







if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    #app.run(debug=True, host='0.0.0.0', port=5002)
