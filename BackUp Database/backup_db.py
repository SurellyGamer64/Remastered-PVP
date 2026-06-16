"""
╔══════════════════════════════════════════════════════╗
║         BACKUP / RESTORE - DATABASE BACKUP           ║
║  Corre este script en tu PC para bajar o subir la db ║
╚══════════════════════════════════════════════════════╝

USO:
  Permite descargar la database del bot y mantenerla
  Guardada en tu dispositivo.
"""

import requests
import json
import os
import sys
from datetime import datetime

# ══════════════════════════════════════════
#   CONFIGURACIÓN — edita estas 2 líneas
# ══════════════════════════════════════════
BOT_URL =  """Pon la URL de tu bot"""
CLAVE   =  """Clave usada en render"""
# ══════════════════════════════════════════

# Siempre guardar en la misma carpeta que este script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_LOCAL   = os.path.join(SCRIPT_DIR, "db.json")


def descargar():
    print(f"📥 Descargando database desde {BOT_URL}...")
    print(f"   Guardando en: {DB_LOCAL}")
    try:
        r = requests.get(f"{BOT_URL}/backup", params={"key": CLAVE}, timeout=30)
        if r.status_code == 403:
            print("❌ Clave incorrecta.")
            return
        if r.status_code != 200:
            print(f"❌ Error {r.status_code}: {r.text}")
            return

        data = r.json()
        usuarios = len(data.get("users", {}))

        # Backup del archivo anterior con timestamp
        if os.path.exists(DB_LOCAL):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = os.path.join(SCRIPT_DIR, f"db_backup_{ts}.json")
            os.rename(DB_LOCAL, backup_name)
            print(f"   💾 Backup anterior guardado como: {backup_name}")

        with open(DB_LOCAL, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Verificar que el archivo realmente se creó
        if os.path.exists(DB_LOCAL):
            size = os.path.getsize(DB_LOCAL)
            print(f"✅ ¡Database descargada! {usuarios} usuario(s) | {size} bytes")
            print(f"   Archivo guardado en: {DB_LOCAL}")
        else:
            print("❌ El archivo no se creó correctamente.")

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar. ¿Está el bot online en Render?")
    except json.JSONDecodeError:
        print("❌ La respuesta del servidor no es JSON válido.")
        print(f"   Respuesta recibida: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


def restaurar():
    if not os.path.exists(DB_LOCAL):
        print(f"❌ No encontré '{DB_LOCAL}'.")
        print(f"   Buscado en: {DB_LOCAL}")
        return

    with open(DB_LOCAL, "r", encoding="utf-8") as f:
        data = json.load(f)

    usuarios = len(data.get("users", {}))
    print(f"📤 Subiendo database al bot ({usuarios} usuario(s))...")
    print(f"   URL: {BOT_URL}")

    confirm = input("   ¿Confirmas? Esto SOBREESCRIBE la db del bot. (s/n): ").strip().lower()
    if confirm != "s":
        print("   Cancelado.")
        return

    try:
        r = requests.post(
            f"{BOT_URL}/upload_db",
            params={"key": CLAVE},
            json=data,
            timeout=30
        )
        if r.status_code == 403:
            print("❌ Clave incorrecta.")
            return
        if r.status_code == 200:
            print("✅ ¡Database restaurada en el bot!")
        else:
            print(f"❌ Error {r.status_code}: {r.text}")

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar. ¿Está el bot online en Render?")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restaurar()
    else:
        descargar()
