#!/usr/bin/env python3
"""
Script para hacer backup de base de datos MySQL en Railway
Requiere: pip install mysql-connector-python
"""

import mysql.connector
import os
import gzip
import shutil
from datetime import datetime, timedelta
import subprocess
import sys

# Configuración de la base de datos Railway
DB_CONFIG = {
    'host': 'yamanote.proxy.rlwy.net',
    'port': 27126,
    'user': 'root',
    'password': 'kRjKiUbLdBuqkkukGhtPgJQENuKwYmXE',
    'database': 'railway'
}

# Configuración del backup
BACKUP_DIR = os.path.expanduser('~/backups/railway_mysql')
COMPRESS_BACKUP = True
KEEP_DAYS = 7  # Mantener backups por 7 días

def create_backup_directory():
    """Crear directorio de backups si no existe"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"📁 Directorio creado: {BACKUP_DIR}")

def test_connection():
    """Verificar conexión a la base de datos"""
    try:
        print("🔍 Verificando conexión a la base de datos...")
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("✅ Conexión exitosa!")
            connection.close()
            return True
    except mysql.connector.Error as e:
        print(f"❌ Error de conexión: {e}")
        return False

def backup_with_mysqldump():
    """Hacer backup usando mysqldump (método recomendado)"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'railway_backup_{timestamp}.sql')
    
    # Comando mysqldump
    cmd = [
        'mysqldump',
        f'--host={DB_CONFIG["host"]}',
        f'--port={DB_CONFIG["port"]}',
        f'--user={DB_CONFIG["user"]}',
        f'--password={DB_CONFIG["password"]}',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--add-drop-database',
        '--comments',
        '--dump-date',
        DB_CONFIG['database']
    ]
    
    try:
        print(f"🚀 Iniciando backup con mysqldump...")
        print(f"📝 Archivo: {os.path.basename(backup_file)}")
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            print(f"✅ Backup completado exitosamente!")
            
            # Mostrar tamaño del archivo
            size = os.path.getsize(backup_file)
            size_mb = size / (1024 * 1024)
            print(f"📊 Tamaño: {size_mb:.2f} MB")
            
            # Comprimir si está habilitado
            if COMPRESS_BACKUP:
                compressed_file = compress_backup(backup_file)
                return compressed_file
            
            return backup_file
        else:
            print(f"❌ Error en mysqldump: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ mysqldump no encontrado. Instalando alternativa...")
        return backup_with_python()
    except Exception as e:
        print(f"❌ Error durante backup: {e}")
        return None

def backup_with_python():
    """Backup usando python y mysql-connector (alternativa)"""
    try:
        import mysql.connector
    except ImportError:
        print("❌ mysql-connector-python no instalado.")
        print("📦 Instala con: pip install mysql-connector-python")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'railway_backup_python_{timestamp}.sql')
    
    try:
        print("🐍 Haciendo backup con Python...")
        
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        with open(backup_file, 'w') as f:
            # Header del backup
            f.write(f"-- Backup de Railway MySQL\n")
            f.write(f"-- Fecha: {datetime.now()}\n")
            f.write(f"-- Base de datos: {DB_CONFIG['database']}\n\n")
            
            # Obtener lista de tablas
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                print(f"📋 Respaldando tabla: {table_name}")
                
                # Estructura de la tabla
                cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                create_table = cursor.fetchone()[1]
                f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
                f.write(f"{create_table};\n\n")
                
                # Datos de la tabla
                cursor.execute(f"SELECT * FROM `{table_name}`")
                rows = cursor.fetchall()
                
                if rows:
                    # Obtener nombres de columnas
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = [col[0] for col in cursor.fetchall()]
                    
                    f.write(f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in columns])}) VALUES\n")
                    
                    for i, row in enumerate(rows):
                        values = []
                        for value in row:
                            if value is None:
                                values.append('NULL')
                            elif isinstance(value, str):
                                values.append(f"'{value.replace(chr(39), chr(39)+chr(39))}'")
                            else:
                                values.append(str(value))
                        
                        if i == len(rows) - 1:
                            f.write(f"({', '.join(values)});\n\n")
                        else:
                            f.write(f"({', '.join(values)}),\n")
        
        connection.close()
        
        print("✅ Backup con Python completado!")
        size = os.path.getsize(backup_file)
        size_mb = size / (1024 * 1024)
        print(f"📊 Tamaño: {size_mb:.2f} MB")
        
        if COMPRESS_BACKUP:
            compressed_file = compress_backup(backup_file)
            return compressed_file
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Error durante backup con Python: {e}")
        return None

def compress_backup(backup_file):
    """Comprimir el archivo de backup"""
    compressed_file = backup_file + '.gz'
    
    try:
        print("🗜️  Comprimiendo backup...")
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Eliminar archivo original
        os.remove(backup_file)
        
        # Mostrar información del archivo comprimido
        original_size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0
        compressed_size = os.path.getsize(compressed_file)
        compression_ratio = (1 - compressed_size / max(original_size, 1)) * 100
        
        print(f"✅ Backup comprimido: {os.path.basename(compressed_file)}")
        print(f"📊 Tamaño comprimido: {compressed_size / (1024 * 1024):.2f} MB")
        print(f"🎯 Compresión: {compression_ratio:.1f}%")
        
        return compressed_file
        
    except Exception as e:
        print(f"❌ Error al comprimir: {e}")
        return backup_file

def cleanup_old_backups():
    """Eliminar backups antiguos"""
    if not os.path.exists(BACKUP_DIR):
        return
    
    cutoff_date = datetime.now() - timedelta(days=KEEP_DAYS)
    deleted_count = 0
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith('railway_backup_'):
            file_path = os.path.join(BACKUP_DIR, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            if file_time < cutoff_date:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"🗑️  Eliminado: {filename}")
                except Exception as e:
                    print(f"❌ Error eliminando {filename}: {e}")
    
    if deleted_count > 0:
        print(f"🧹 Limpieza completada: {deleted_count} archivos eliminados")
    else:
        print("🧹 No hay archivos antiguos para eliminar")

def main():
    """Función principal"""
    print("=" * 50)
    print("🚀 BACKUP BASE DE DATOS RAILWAY")
    print("=" * 50)
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Crear directorio de backups
    create_backup_directory()
    
    # Verificar conexión
    if not test_connection():
        print("❌ No se puede conectar a la base de datos. Verifica la configuración.")
        sys.exit(1)
    
    # Hacer backup
    backup_file = backup_with_mysqldump()
    
    if backup_file:
        print(f"📁 Backup guardado en: {backup_file}")
        
        # Limpiar backups antiguos
        cleanup_old_backups()
        
        print()
        print("🎉 ¡Proceso de backup completado exitosamente!")
    else:
        print("❌ El backup ha fallado.")
        sys.exit(1)

if __name__ == "__main__":
    main()