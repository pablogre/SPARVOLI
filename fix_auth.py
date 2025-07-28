import pymysql
from urllib.parse import urlparse
import os

def run_fix():
    db_url = urlparse(os.getenv("MYSQL_URL"))

    connection = pymysql.connect(
        host=db_url.hostname,
        user=db_url.username,
        password=db_url.password,
        database="mysql",  # usamos la base de datos 'mysql' del sistema
        port=db_url.port or 3306
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY %s;
            """, (db_url.password,))
            cursor.execute("FLUSH PRIVILEGES;")
        connection.commit()
        print("✅ Usuario 'root' actualizado exitosamente a mysql_native_password")
    except Exception as e:
        print("❌ Error al ejecutar el comando:", e)
    finally:
        connection.close()

if __name__ == "__main__":
    run_fix()
