"""
main.py — Entrypoint de Render para Androide PVP.

Estructura de archivos:
  main.py              ← este archivo
  database.py          ← load_db / save_db
  figures.py           ← FIGURES, FIGURE_SKILLS, constantes
  battle.py            ← BattleState, execute_action, bot_turn, end_battle
  shops.py             ← 6 tiendas + sobres del Acertijo
  bosses.py            ← BOT_ROSTER, IMPOSTOR_REWARDS
  economy.py           ← ingredientes, recetas, learn tree, logros, quests
  commands_shop.py     ← /tienda, /secret-store
  commands_battle.py   ← /pvp-enemy, /pvp-boss, /retar, /ranking, /diario, /reset
  commands_profile.py  ← /registrar, /perfil, /misfiguras, /equipar
  commands_economy.py  ← /cook, /work, /rob, /trade, /explore, /quest, /learn, /rebirth, /combine
  commands_admin.py    ← /oro, /bomb, /nuke, /gift, /say, /holy, /get, /ayuda
"""

import os
import threading
import json

import discord
from discord.ext import commands
from flask import Flask, request, send_file

# ── Core imports ─────────────────────────────────────────────────────────────
from database import load_db, save_db, get_user, create_user
from figures import FIGURES, SECRET_FIGURES, RARITY_COLOR, RARITY_STARS
from shops import _reset_shops

# ── Command modules ───────────────────────────────────────────────────────────
import commands_shop
import commands_battle
import commands_profile
import commands_economy
import commands_admin

# ============================================================
#  FLASK — keepalive para Render / UptimeRobot
# ============================================================

BACKUP_KEY = os.getenv("BACKUP_KEY", "mateo_backup_2024")
flask_app  = Flask("")


@flask_app.route("/")
def home():
    return "Bot Online"


@flask_app.route("/backup")
def backup_db_route():
    key = request.args.get("key", "")
    if key != BACKUP_KEY:
        return "Clave incorrecta.", 403
    db_file = "/etc/secrets/db.json" if os.path.exists("/etc/secrets/db.json") else "db.json"
    if os.path.exists(db_file):
        return send_file(db_file, mimetype="application/json",
                         as_attachment=True, download_name="db.json")
    return json.dumps({"users": {}}), 200, {"Content-Type": "application/json"}


@flask_app.route("/upload_db", methods=["POST"])
def upload_db_route():
    key = request.args.get("key", "")
    if key != BACKUP_KEY:
        return "Clave incorrecta.", 403
    data = request.get_json(force=True)
    if not data:
        return "Sin datos.", 400
    db_file = "/etc/secrets/db.json" if os.path.exists("/etc/secrets") else "db.json"
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return "Database restaurada correctamente.", 200


threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080), daemon=True).start()


# ============================================================
#  BOT SETUP
# ============================================================

TOKEN    = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1236294131534401647

intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ============================================================
#  REGISTRAR COMANDOS SLASH
# ============================================================

# Módulos con register_commands(bot)
commands_battle.register_commands(bot)

# Módulos que registran sus comandos al importarse (usan @bot.tree directamente)
# → commands_shop, commands_profile, commands_economy, commands_admin
# Si aún no los migras a register_commands(), regístralos manualmente aquí:
# (por ahora los importamos arriba; sus decoradores @bot.tree.command se ejecutan al import)


# ============================================================
#  EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} está en línea!")
    _reset_shops(FIGURES, SECRET_FIGURES)

    if GUILD_ID:
        guild  = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} comandos sincronizados en el servidor!")
    else:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados globalmente")


# ============================================================
#  ARRANCAR BOT
# ============================================================

if __name__ == "__main__":
    bot.run(TOKEN)
