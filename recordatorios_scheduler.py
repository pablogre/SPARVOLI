# Crear archivo: scheduler_recordatorios.py

import schedule
import time
import requests
import os
from datetime import datetime

def enviar_recordatorios_diarios():
    """Ejecuta el endpoint de recordatorios"""
    try:
        # Cambiar por tu URL real
        base_url = os.getenv("BASE_URL", "http://localhost:5000")
        
        response = requests.get(f"{base_url}/procesar_recordatorios", timeout=30)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ✅ Recordatorios ejecutados: {response.text}")
        
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ❌ Error ejecutando recordatorios: {e}")

def main():
    """Programa los recordatorios para ejecutarse diariamente"""
    
    # Ejecutar todos los días a las 10:00 AM
    schedule.every().day.at("10:00").do(enviar_recordatorios_diarios)
    
    # También a las 18:00 como respaldo
    schedule.every().day.at("18:00").do(enviar_recordatorios_diarios)
    
    print("📅 Scheduler iniciado - Recordatorios programados para las 10:00 y 18:00")
    print("Presiona Ctrl+C para detener")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    except KeyboardInterrupt:
        print("\n🛑 Scheduler detenido")

if __name__ == "__main__":
    main()

# ========================================
# INSTRUCCIONES DE USO:
# ========================================

# 1. MÉTODO 1: Ejecutar este script en background
#    python scheduler_recordatorios.py

# 2. MÉTODO 2: Usar CRON en Linux/Mac
#    Agregar a crontab (ejecutar: crontab -e):
#    0 10 * * * curl -s https://tu-dominio.com/procesar_recordatorios
#    0 18 * * * curl -s https://tu-dominio.com/procesar_recordatorios

# 3. MÉTODO 3: Task Scheduler en Windows
#    - Crear tarea programada
#    - Ejecutar: curl.exe -s https://tu-dominio.com/procesar_recordatorios
#    - Programar diariamente a las 10:00