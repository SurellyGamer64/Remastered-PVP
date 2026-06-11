"""
main.py — Archivo principal del bot Androide PVP.
Importa los módulos de lógica y registra todos los comandos slash.

Estructura de archivos:
  main.py       ← este archivo (entrypoint de Render)
  database.py   ← carga/guarda db.json
  figures.py    ← FIGURES, FIGURE_SKILLS, constantes de rareza
  battle.py     ← lógica de batalla (BattleState, execute_action, etc.)
  shops.py      ← 6 tiendas con probabilidades y sobres del Acertijo
  bosses.py     ← BOT_ROSTER y figuras exclusivas de jefes
  economy.py    ← ingredientes, recetas, learn tree, combine, rebirth
  commands.py   ← comandos slash (/tienda, /pvpbot, /perfil, etc.)
"""

import os
import threading
import discord
from discord.ext import commands
from flask import Flask, request, send_file
import json

from database import load_db, save_db, get_user, create_user
from figures import (
    FIGURES, FIGURE_SKILLS, SECRET_FIGURES, SECRET_CODE, SECRET_OWNER_ID,
    RARITY_COLOR, RARITY_STARS, KIRBY_DEFAULT_SKILLS, KIRBY_TRANSFORMED_SLOT0,
    XP_PER_WIN, XP_PER_LOSS, COINS_WIN, COINS_LOSS,
    apply_level_bonus, xp_to_level_up,
    secret_store_unlocked,
)
from shops import (
    SHOPS, MYSTERY_PACKS, SHOP_AVAILABILITY, SHOP_MYTHIC_CHANCE,
    _reset_shops, check_shop_reset, time_until_reset,
    _pick_shop_figures, open_mystery_pack,
)
from bosses import BOT_ROSTER, IMPOSTOR_REWARDS
from economy import (
    INGREDIENTS, RECIPES, FAILED_RECIPE_MSGS, LEARN_TREE,
    ACHIEVEMENTS, FIGURE_LEVEL_MAX, BATTLE_INGREDIENT_DROP_CHANCE,
    find_recipe, give_battle_ingredient, check_figure_levelup,
    check_achievements, grant_achievement, get_learn_effect,
    _check_player_levelup,
)
from battle import (
    active_battles, pending_pvp,
    BattleState, BattleView, get_battle_view,
    make_skill_callback, make_switch_callback,
    execute_action, finish_turn, bot_turn, end_battle,
)

# ── Importar comandos (los registra en bot.tree) ──────────────────────────────
import commands_shop
import commands_battle
import commands_profile
import commands_economy
import commands_admin

# ============================================================
#  FLASK — keepalive para Render / UptimeRobot
# ============================================================

BACKUP_KEY = os.getenv("BACKUP_KEY", "mateo_backup_2024")
app = Flask("")


@app.route("/")
def home():
    return "Bot Online"


@app.route("/backup")
def backup_db_route():
    key = request.args.get("key", "")
    if key != BACKUP_KEY:
        return "Clave incorrecta.", 403
    _db_file = "/etc/secrets/db.json" if os.path.exists("/etc/secrets/db.json") else "db.json"
    if os.path.exists(_db_file):
        return send_file(_db_file, mimetype="application/json",
                         as_attachment=True, download_name="db.json")
    return json.dumps({"users": {}}), 200, {"Content-Type": "application/json"}


@app.route("/upload_db", methods=["POST"])
def upload_db_route():
    key = request.args.get("key", "")
    if key != BACKUP_KEY:
        return "Clave incorrecta.", 403
    data = request.get_json(force=True)
    if not data:
        return "Sin datos.", 400
    _db_file = "/etc/secrets/db.json" if os.path.exists("/etc/secrets") else "db.json"
    with open(_db_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return "Database restaurada correctamente.", 200


def run_flask():
    app.run(host="0.0.0.0", port=8080)


threading.Thread(target=run_flask, daemon=True).start()

# ============================================================
#  BOT SETUP
# ============================================================

TOKEN  = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

GUILD_ID = 1236294131534401647

# ============================================================
#  EVENTS
# ============================================================


@bot.event
async def on_ready():
    print(f"✅ {bot.user} está en línea!")
    _reset_shops(FIGURES, SECRET_FIGURES)
    await bot.tree.sync()
    if GUILD_ID:
        guild  = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} comandos sincronizados en el servidor!")
    else:
        print("⚠️ Pon tu GUILD_ID para sync instantáneo")


# ============================================================
#  ARRANCAR BOT
# ============================================================

if __name__ == "__main__":
    bot.run(TOKEN)