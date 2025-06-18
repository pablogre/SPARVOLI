from flask import Flask, render_template, request, redirect, flash, url_for
import pymysql
from datetime import datetime, timedelta, date
import re
from twilio.rest import Client
from dotenv import load_dotenv
import os



app = Flask(__name__)

app.secret_key = 'clave_secreta_segura'

load_dotenv()  # <-- Esto carga las variables del .env

# Configuración de la base de datos
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
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔒 Verificar si la fecha está completamente o parcialmente bloqueada
    cursor.execute("SELECT hora_desde FROM fechas_bloqueadas WHERE fecha = %s", (fecha,))
    bloqueo = cursor.fetchone()
    
    # Si está bloqueada sin especificar hora, se bloquea todo el día
    if bloqueo and bloqueo['hora_desde'] is None:
        cursor.close()
        conn.close()
        print("🔒 Fecha completamente bloqueada, no se generan turnos:", fecha)
        return    

    hora_inicio = datetime.strptime("08:00", "%H:%M")
    hora_fin = datetime.strptime("13:00", "%H:%M") if dia_semana == 1 else datetime.strptime("14:20", "%H:%M")
    intervalo = timedelta(minutes=20)

    hora_actual = hora_inicio

    while hora_actual < hora_fin:
        hora_str = hora_actual.strftime("%H:%M")

        # ⏱️ Si hay hora_desde en el bloqueo, saltear turnos dentro del rango bloqueado
        if bloqueo and bloqueo['hora_desde']:
            hora_bloqueada = datetime.strptime(bloqueo['hora_desde'], "%H:%M").time()
            if hora_actual.time() >= hora_bloqueada:
                print(f"⏩ Turno {hora_str} bloqueado por horario desde {hora_bloqueada}")
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
    load_dotenv()  # Carga las variables del archivo .env

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

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

    if request.method == "POST":
        dia = request.form["fecha"]
        hoy = date.today().isoformat()
        ahora = datetime.now().time()
        dia_semana = datetime.strptime(dia, "%Y-%m-%d").weekday()
        print("hoy:", hoy)
        
        # ✅ **NUEVA VALIDACIÓN: Verificar si la fecha es anterior al 3 de julio de 2025**
        fecha_limite = "2025-07-03"
        if dia < fecha_limite:
            mensaje = "No se pueden reservar turnos para fechas anteriores al 3 de julio de 2025."
        else:
            # Si es sábado o domingo, no hay turnos
            if dia_semana in (5, 6):
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

                # Consultar turnos existentes
                turnos = consultar_turnos()

                # Si no hay, generar y volver a consultar
                if not turnos:
                    generar_turnos(dia)

                    # Cerrar y reabrir conexión/cursor para evitar caché
                    cursor.close()
                    conn.close()
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    # Re-definir la función con nuevo cursor
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
                        if dia == hoy:
                            mensaje = "Ya pasaron todos los turnos disponibles para hoy."
                        else:
                            mensaje = "No hay turnos disponibles para este día."
                    else:
                        mensaje = None

            # Formatear hora para mostrar
            for t in turnos:
                try:
                    t['turno_str'] = t['turno'].strftime("%H:%M")
                except:
                    total_seg = t['turno'].seconds if hasattr(t['turno'], 'seconds') else 0
                    horas = total_seg // 3600
                    minutos = (total_seg % 3600) // 60
                    t['turno_str'] = f"{horas:02d}:{minutos:02d}"

    cursor.close()
    conn.close()
    return render_template("index.html", turnos=turnos, fecha=dia, mensaje=mensaje)


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

    # Enviamos el SMS
    enviar_sms(paciente, telefono, dia, hora)

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

    if request.method == "POST":
        fecha = request.form["fecha"]
        hoy = date.today().isoformat()
        ahora = datetime.now().time()
          # ✅ **NUEVA VALIDACIÓN: Verificar si la fecha es anterior a hoy**
        if fecha < hoy:
            mensaje = "No se pueden consultar turnos para fechas pasadas."
        else:
            # Consultar turnos disponibles según la fecha
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

            # Si no hay turnos generados, los crea
            if not disponibles:
                generar_turnos(fecha)
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

            # Consultar turnos reservados
            cursor.execute("""
                SELECT * FROM turnos 
                WHERE dia = %s AND paciente != ''
            """, (fecha,))
            reservados = cursor.fetchall()

            # Formatear horas para mostrar en HTML
            for lst in (disponibles, reservados):
                for t in lst:
                    total_sec = t['turno'].seconds
                    horas = total_sec // 3600
                    minutos = (total_sec % 3600) // 60
                    t['turno_str'] = f"{horas:02d}:{minutos:02d}"

        cursor.close()
        conn.close()
        return render_template("consulta.html", disponibles=disponibles, reservados=reservados, fecha=fecha)

    cursor.close()
    conn.close()
    return render_template("consulta.html", disponibles=[], reservados=[], fecha=None)



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
                cursor.execute("INSERT IGNORE INTO fechas_bloqueadas (fecha, hora_desde) VALUES (%s, %s)", (fecha_actual.date(), hora_desde))
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    #app.run(debug=True, host='0.0.0.0', port=5002)
