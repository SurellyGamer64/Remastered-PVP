"""
╔══════════════════════════════════════════════════════╗
║         BACKUP / RESTORE - Androide PVP Bot          ║
║  Corre este script en tu PC para bajar o subir la db ║
╚══════════════════════════════════════════════════════╝

USO:
  python backup_db.py           → descarga la db del bot
  python backup_db.py restore   → sube db.json al bot
"""

import requests
import json
import os
import sys
from datetime import datetime

# ══════════════════════════════════════════
#   CONFIGURACIÓN — edita estas 2 líneas
# ══════════════════════════════════════════
BOT_URL   = "https://TU-BOT.onrender.com"   # URL de tu bot en Render
CLAVE     = "mateo_backup_2024"              # La misma que BACKUP_KEY en Render
# ══════════════════════════════════════════

DB_LOCAL  = "db.json"   # Archivo local donde se guarda/lee la db


def descargar():
    print(f"📥 Descargando database desde {BOT_URL}...")
    try:
        r = requests.get(f"{BOT_URL}/backup", params={"key": CLAVE}, timeout=30)
        if r.status_code == 403:
            print("❌ Clave incorrecta. Revisa CLAVE en este script y BACKUP_KEY en Render.")
            return
        if r.status_code != 200:
            print(f"❌ Error {r.status_code}: {r.text}")
            return

        data = r.json()
        usuarios = len(data.get("usuarios", {}))

        # Hacer backup con timestamp antes de sobreescribir
        if os.path.exists(DB_LOCAL):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"db_backup_{ts}.json"
            os.rename(DB_LOCAL, backup_name)
            print(f"   💾 Backup anterior guardado como: {backup_name}")

        with open(DB_LOCAL, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ ¡Database descargada! {usuarios} usuario(s) guardados en '{DB_LOCAL}'")
        print(f"   Ahora puedes hacer commit + push a GitHub para sincronizar.")

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar. ¿Está el bot online en Render?")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


def restaurar():
    if not os.path.exists(DB_LOCAL):
        print(f"❌ No encontré '{DB_LOCAL}' en esta carpeta.")
        return

    with open(DB_LOCAL, "r", encoding="utf-8") as f:
        data = json.load(f)

    usuarios = len(data.get("usuarios", {}))
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
