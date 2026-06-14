"""
commands_economy.py — Comandos de economía: cocina, trabajo, comercio, exploración, etc.
"""
import random
import asyncio
import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import FIGURES, FIGURE_SKILLS, apply_level_bonus
from economy import (
    INGREDIENTS, RECIPES, FAILED_RECIPE_MSGS, LEARN_TREE,
    FIGURE_LEVEL_MAX, BATTLE_INGREDIENT_DROP_CHANCE,
    find_recipe, give_battle_ingredient, check_figure_levelup,
    check_achievements, grant_achievement, get_learn_effect,
    _check_player_levelup,
)
from bosses import BOT_ROSTER

@bot.tree.command(name="lobster", description="🦞 Obtén una langosta misteriosa")
async def lobster_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    user["figures"].append({"key": "lobster", "level": 1, "xp": 0})
    # Añadir al equipo si hay hueco
    team = user.get("team", [None, None, None])
    while len(team) < 3: team.append(None)
    for i in range(3):
        if team[i] is None:
            team[i] = len(user["figures"]) - 1
            break
    user["team"] = team
    save_db(db)

    embed = discord.Embed(
        title="🦞 Una langosta ha aparecido",
        description="No sabes de dónde vino. No sabes qué quiere.\nPero ahora es tuya.",
        color=0xe74c3c
    )
    embed.add_field(name="❤️ Vida", value="1", inline=True)
    embed.add_field(name="⚔️ Ataque", value="1", inline=True)
    embed.add_field(name="🛡️ Defensa", value="1", inline=True)
    embed.add_field(
        name="✨ Habilidad: LOBSTER",
        value="No hace nada.\nO eso crees. Tiene un **0.01%** de matar a todas las figuras enemigas.",
        inline=False
    )
    embed.set_footer(text="Úsala con /equipar. Buena suerte.")
    await interaction.response.send_message(embed=embed)

# --- ORO (solo admins) ---
@bot.tree.command(name="rob", description="Intenta robarle monedas a otro usuario")
@app_commands.describe(usuario="Usuario al que intentar robar")
async def rob(interaction: discord.Interaction, usuario: discord.Member):
    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes robarte a ti mismo.", ephemeral=True)
        return

    now = datetime.now(timezone.utc).timestamp()
    cd_key = interaction.user.id
    if cd_key in ROB_COOLDOWN:
        diff = now - ROB_COOLDOWN[cd_key]
        if diff < 600:  # 10 minutos
            restante = int(600 - diff)
            m = restante // 60
            s = restante % 60
            await interaction.response.send_message(
                f"⏰ Cooldown activo. Puedes robar de nuevo en **{m}m {s}s**.", ephemeral=True
            )
            return

    db = load_db()
    robber = get_user(db, interaction.user.id)
    victim = get_user(db, usuario.id)

    if not robber:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    if not victim:
        await interaction.response.send_message("❌ Ese usuario no está registrado.", ephemeral=True)
        return
    if victim.get("coins", 0) <= 0:
        await interaction.response.send_message("❌ Ese usuario no tiene monedas que robar.", ephemeral=True)
        return

    ROB_COOLDOWN[cd_key] = now

    roll = random.randint(1, 100)
    if roll <= 10:       # 10% — robo grande
        pct = random.uniform(0.30, 0.50)
        result = "grande"
    elif roll <= 35:     # 25% — robo mediano
        pct = random.uniform(0.10, 0.29)
        result = "mediano"
    elif roll <= 60:     # 25% — robo pequeño
        pct = random.uniform(0.01, 0.09)
        result = "pequeño"
    else:                # 40% — fallo
        result = "fallo"
        pct = 0

    embed = discord.Embed(color=0x9b59b6)
    if result == "fallo":
        embed.title = "🚨 ¡Te atraparon!"
        embed.description = f"Intentaste robarle a **{victim['name']}** pero te pillaron con las manos en la masa. ¡Qué vergüenza!"
        fine = min(victim.get("coins",0), random.randint(20, 80))
        robber["coins"] = max(0, robber.get("coins",0) - fine)
        embed.add_field(name="💸 Multa", value=f"-**{fine:,}** monedas por torpe", inline=True)
    else:
        stolen = max(1, int(victim.get("coins", 0) * pct))
        victim["coins"]  = max(0, victim.get("coins",0) - stolen)
        robber["coins"]  = robber.get("coins",0) + stolen
        icons = {"grande":"💰💰💰", "mediano":"💰💰", "pequeño":"💰"}
        embed.title = f"🦹 ¡Robo {icons[result]} exitoso!"
        embed.description = f"Le robaste a **{victim['name']}** sin que se diera cuenta."
        embed.add_field(name="💰 Robado", value=f"+**{stolen:,}** monedas", inline=True)
        embed.add_field(name="📊 Tipo", value=result.capitalize(), inline=True)
        embed.add_field(name="💳 Tu saldo", value=f"**{robber['coins']:,}**", inline=True)

    save_db(db)
    embed.set_footer(text="Cooldown: 2 horas")
    await interaction.response.send_message(embed=embed)

# --- WORK ---
WORK_COOLDOWN = {}  # {user_id: timestamp}
WORK_COOLDOWN_SECS = 3600  # 1 hora entre trabajos

@bot.tree.command(name="work", description="Trabaja para ganar monedas con un minijuego")
async def work(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    now = datetime.now(timezone.utc).timestamp()
    if interaction.user.id in WORK_COOLDOWN:
        diff = now - WORK_COOLDOWN[interaction.user.id]
        if diff < WORK_COOLDOWN_SECS:
            restante = int(WORK_COOLDOWN_SECS - diff)
            m = restante // 60
            s = restante % 60
            await interaction.response.send_message(
                f"⏰ Ya trabajaste hoy. Descansa **{m}m {s}s** más.", ephemeral=True
            )
            return

    # Elegir trabajo
    embed = discord.Embed(
        title="💼 ¿En qué quieres trabajar hoy?",
        description="Elige tu trabajo y demuestra lo que vales:",
        color=0x2ecc71
    )
    embed.add_field(name="🍔 Preparar Hamburguesas", value="Secuencia de botones. Recompensa: 80-300🪙", inline=False)
    embed.add_field(name="🎣 Pescar",                value="Opción múltiple. Recompensa: 50-400🪙",    inline=False)
    embed.add_field(name="🎬 Crear Videos",          value="Escribe rápido. Recompensa: 100-500🪙",    inline=False)

    view = discord.ui.View(timeout=30)
    for job_id, label in [("burger","🍔 Hamburguesas"), ("fish","🎣 Pescar"), ("video","🎬 Videos")]:
        btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=f"job_{job_id}")
        btn.callback = make_job_callback(job_id, interaction.user.id)
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view)

def make_job_callback(job_id: str, user_discord_id: int):
    async def callback(inter: discord.Interaction):
        if inter.user.id != user_discord_id:
            await inter.response.send_message("❌ Este trabajo no es tuyo.", ephemeral=True)
            return
        WORK_COOLDOWN[inter.user.id] = datetime.now(timezone.utc).timestamp()
        if job_id == "burger":
            await start_burger_minigame(inter)
        elif job_id == "fish":
            await start_fish_minigame(inter)
        elif job_id == "video":
            await start_video_minigame(inter)
    return callback

# ── MINIJUEGO 1: HAMBURGUESAS (secuencia de botones) ──────────────────────────
BURGER_SEQUENCES = [
    ["🥩","🧀","🥬","🍅","🥚"],
    ["🥬","🥩","🧀","🥚","🍅"],
    ["🧀","🥚","🥩","🍅","🥬"],
    ["🍅","🥬","🥚","🧀","🥩"],
]

async def start_burger_minigame(inter: discord.Interaction):
    sequence = random.choice(BURGER_SEQUENCES)
    seq_display = " → ".join(sequence)
    embed = discord.Embed(
        title="🍔 ¡Prepara la hamburguesa!",
        description=f"Añade los ingredientes en este orden:\n**{seq_display}**\n\nTienes 20 segundos!",
        color=0xe67e22
    )
    state = {"sequence": sequence, "progress": [], "user_id": inter.user.id}

    view = make_burger_view(state, inter)
    await inter.response.edit_message(embed=embed, view=view)

def make_burger_view(state, orig_inter):
    view = discord.ui.View(timeout=20)
    ingredients = ["🥩","🧀","🥬","🍅","🥚"]
    random.shuffle(ingredients)

    for ing in ingredients:
        btn = discord.ui.Button(label=ing, style=discord.ButtonStyle.secondary, custom_id=f"ing_{ing}")
        async def ing_cb(inter: discord.Interaction, ingredient=ing, s=state, oi=orig_inter):
            if inter.user.id != s["user_id"]:
                await inter.response.send_message("❌ No es tu minijuego.", ephemeral=True)
                return
            s["progress"].append(ingredient)
            expected = s["sequence"][len(s["progress"])-1]
            if ingredient != expected:
                # Error — calcular recompensa parcial
                correct = len(s["progress"]) - 1
                coins = max(30, correct * 40)
                db = load_db(); u = get_user(db, inter.user.id)
                u["coins"] = u.get("coins",0) + coins; save_db(db)
                embed = discord.Embed(title="❌ ¡Ingrediente equivocado!",
                    description=f"Pusiste **{ingredient}** pero era **{expected}**.\n+**{coins}**🪙 por {correct} ingredientes correctos.",
                    color=0xe74c3c)
                await inter.response.edit_message(embed=embed, view=None)
                return
            if len(s["progress"]) == len(s["sequence"]):
                # ¡Perfecto!
                coins = random.randint(200, 300)
                db = load_db(); u = get_user(db, inter.user.id)
                u["coins"] = u.get("coins",0) + coins; save_db(db)
                embed = discord.Embed(title="🍔 ¡Hamburguesa perfecta!",
                    description=f"¡Orden completada! +**{coins}**🪙", color=0x2ecc71)
                await inter.response.edit_message(embed=embed, view=None)
                return
            # Siguiente ingrediente
            done = " ✅ ".join(s["progress"])
            remaining = len(s["sequence"]) - len(s["progress"])
            embed = discord.Embed(title="🍔 ¡Bien!",
                description=f"Añadido: {done}\nFaltan **{remaining}** ingredientes...",
                color=0xe67e22)
            await inter.response.edit_message(embed=embed, view=make_burger_view(s, oi))
        btn.callback = ing_cb
        view.add_item(btn)
    return view

# ── MINIJUEGO 2: PESCAR (opción múltiple) ─────────────────────────────────────
FISH_QUESTIONS = [
    {"q": "El agua está turbia y hay algas. ¿Qué cebo usas?", "opts": ["🪱 Gusano","🐟 Pececillo","🌽 Maíz","🦐 Camarón"], "ans": "🦐 Camarón", "coins": (200,400)},
    {"q": "Es de madrugada en un río. ¿Dónde lanzas?", "opts": ["🌊 Centro","🪨 Rocas","🌿 Orilla con plantas","🏖️ Playa abierta"], "ans": "🌿 Orilla con plantas", "coins": (150,350)},
    {"q": "El pez picó pero está resistiendo fuerte. ¿Qué haces?", "opts": ["💪 Tiro fuerte","⏳ Espero y suelto hilo","🎣 Recojo rápido","❌ Suelto la caña"], "ans": "⏳ Espero y suelto hilo", "coins": (180,380)},
    {"q": "¿Qué hora es mejor para pescar peces grandes?", "opts": ["🌅 Amanecer","☀️ Mediodía","🌆 Atardecer","🌙 Noche"], "ans": "🌅 Amanecer", "coins": (100,300)},
    {"q": "Ves burbujas en el agua. ¿Qué significa?", "opts": ["💨 Gas del fondo","🐟 Peces alimentándose","🐊 Peligro","🪨 Corriente"], "ans": "🐟 Peces alimentándose", "coins": (220,420)},
]

async def start_fish_minigame(inter: discord.Interaction):
    q = random.choice(FISH_QUESTIONS)
    embed = discord.Embed(
        title="🎣 ¡Momento de pescar!",
        description=f"**{q['q']}**\n\nElige la respuesta correcta:",
        color=0x3498db
    )
    view = discord.ui.View(timeout=20)
    opts = q["opts"].copy(); random.shuffle(opts)
    for opt in opts:
        style = discord.ButtonStyle.primary
        btn = discord.ui.Button(label=opt, style=style, custom_id=f"fish_{opt}")
        async def fish_cb(fi: discord.Interaction, choice=opt, question=q, uid=inter.user.id):
            if fi.user.id != uid:
                await fi.response.send_message("❌ No es tu minijuego.", ephemeral=True)
                return
            if choice == question["ans"]:
                coins = random.randint(*question["coins"])
                db = load_db(); u = get_user(db, fi.user.id)
                u["coins"] = u.get("coins",0) + coins; save_db(db)
                embed2 = discord.Embed(title="🎣 ¡Pez capturado!",
                    description=f"¡Respuesta correcta! +**{coins}**🪙", color=0x2ecc71)
            else:
                coins = random.randint(30, 80)
                db = load_db(); u = get_user(db, fi.user.id)
                u["coins"] = u.get("coins",0) + coins; save_db(db)
                embed2 = discord.Embed(title="🎣 ¡Se escapó el pez!",
                    description=f"Respuesta incorrecta. La correcta era **{question['ans']}**.\n+**{coins}**🪙 de consolación.",
                    color=0xe74c3c)
            await fi.response.edit_message(embed=embed2, view=None)
        btn.callback = fish_cb
        view.add_item(btn)
    await inter.response.edit_message(embed=embed, view=view)

# ── MINIJUEGO 3: CREAR VIDEOS (escribe rápido) ────────────────────────────────
VIDEO_CHALLENGES = [
    {"prompt": "Tu video se llama: **'Top 10 momentos épicos'**\nEscribe exactamente: `epico`",       "answer": "epico",       "coins": (200,350)},
    {"prompt": "El algoritmo pide un hashtag. Escribe: `viral`",                                        "answer": "viral",       "coins": (150,300)},
    {"prompt": "Tu intro necesita energía. Escribe: `subscribe`",                                       "answer": "subscribe",   "coins": (180,380)},
    {"prompt": "El editor te pide la música. Escribe: `bangermusic`",                                   "answer": "bangermusic", "coins": (250,450)},
    {"prompt": "El thumbnail necesita texto. Escribe: `clickbait`",                                     "answer": "clickbait",   "coins": (200,400)},
]

async def start_video_minigame(inter: discord.Interaction):
    challenge = random.choice(VIDEO_CHALLENGES)
    embed = discord.Embed(
        title="🎬 ¡Estudio de grabación!",
        description=f"{challenge['prompt']}\n\n⏰ Tienes **30 segundos** para responder en el chat.",
        color=0x9b59b6
    )
    await inter.response.edit_message(embed=embed, view=None)
    msg = await inter.original_response()

    def check(m):
        return m.author.id == inter.user.id and m.channel.id == inter.channel_id

    try:
        response = await bot.wait_for("message", check=check, timeout=30)
        if response.content.strip().lower() == challenge["answer"]:
            coins = random.randint(*challenge["coins"])
            db = load_db(); u = get_user(db, inter.user.id)
            u["coins"] = u.get("coins",0) + coins; save_db(db)
            embed2 = discord.Embed(title="🎬 ¡Video viral!",
                description=f"¡Correcto! Tu video arrasa en internet.\n+**{coins}**🪙", color=0x2ecc71)
        else:
            coins = random.randint(40, 100)
            db = load_db(); u = get_user(db, inter.user.id)
            u["coins"] = u.get("coins",0) + coins; save_db(db)
            embed2 = discord.Embed(title="🎬 ¡Demonetizado!",
                description=f"Escribiste **{response.content}** pero era **{challenge['answer']}**.\n+**{coins}**🪙 de consuelo.",
                color=0xe74c3c)
        await msg.edit(embed=embed2)
        try: await response.delete()
        except: pass
    except asyncio.TimeoutError:
        coins = 0
        embed2 = discord.Embed(title="🎬 ¡Se venció el tiempo!",
            description="Tardaste demasiado. El video fue eliminado por copyright. +0🪙",
            color=0x95a5a6)
        await msg.edit(embed=embed2)



# ============================================================
#  SISTEMA DE COCINA
# ============================================================
INGREDIENTS = {
    "🦞": "Langosta",
    "🌶️": "Chile",
    "🧄": "Ajo",
    "🧅": "Cebolla",
    "🫙": "Salsa Secreta",
    "🍖": "Carne",
    "🌿": "Hierbas",
    "🥚": "Huevo",
    "🧀": "Queso",
    "🍫": "Chocolate",
    "🐮": "Santa Vaca",
    "🍝": "Spaghetti",
}

RECIPES = [
    {
        "name": "🦞🌶️🧄 Langosta Picante",
        "ingredients": ["🦞", "🌶️", "🧄"],
        "effect": "coins_boost",
        "value": 1.5,
        "desc": "¡+50% de monedas ganadas en batalla por 3 victorias!",
        "turns": 3,
    },
    {
        "name": "🦞🍖🧅 Estofado de Langosta",
        "ingredients": ["🦞", "🍖", "🧅"],
        "effect": "hp_boost",
        "value": 30,
        "desc": "¡+30 HP a todas las figuras de tu equipo en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🫙🌿 Langosta Gourmet",
        "ingredients": ["🦞", "🫙", "🌿"],
        "effect": "atk_boost",
        "value": 10,
        "desc": "¡+10 ATK a todas las figuras de tu equipo en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🥚🧀 Langosta con Queso",
        "ingredients": ["🦞", "🥚", "🧀"],
        "effect": "xp_boost",
        "value": 2.0,
        "desc": "¡XP x2 en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🍫🌿 Langosta Dulce",
        "ingredients": ["🦞", "🍫", "🌿"],
        "effect": "level_fig",
        "value": 1,
        "desc": "¡Sube 1 nivel a la figura frontal de tu equipo!",
        "turns": 1,
    },
    {
        "name": "🦞🧄🧅 Langosta Tradicional",
        "ingredients": ["🦞", "🧄", "🧅"],
        "effect": "coins_boost",
        "value": 1.3,
        "desc": "¡+30% de monedas por 2 victorias!",
        "turns": 2,
    },
    {
        "name": "🦞🍖🫙 Langosta a la Brasa",
        "ingredients": ["🦞", "🍖", "🫙"],
        "effect": "atk_boost",
        "value": 15,
        "desc": "¡+15 ATK a todas tus figuras en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🌶️🧀 Langosta Explosiva",
        "ingredients": ["🦞", "🌶️", "🧀"],
        "effect": "hp_boost",
        "value": 50,
        "desc": "¡+50 HP a todas las figuras de tu equipo en la próxima batalla!",
        "turns": 1,
    },
    # Recetas de 1 ingrediente
    {
        "name": "🦞🌶️ Langosta a la Brasa Rápida",
        "ingredients": ["🦞", "🌶️"],
        "effect": "atk_boost",
        "value": 5,
        "desc": "¡+5 ATK a tus figuras en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🍫 Langosta con Chocolate",
        "ingredients": ["🦞", "🍫"],
        "effect": "hp_boost",
        "value": 15,
        "desc": "¡+15 HP a tus figuras en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🌿 Langosta con Hierbas",
        "ingredients": ["🦞", "🌿"],
        "effect": "coins_boost",
        "value": 1.2,
        "desc": "¡+20% monedas en la próxima batalla!",
        "turns": 1,
    },
    # Receta épica (3 ingredientes específicos)
    {
        "name": "🦞🌶️🍖🧄 Langosta Suprema del Chef",
        "ingredients": ["🦞", "🌶️", "🍖", "🧄"],
        "effect": "all_boost",
        "value": 1,
        "desc": "¡+20 ATK, +30 HP y +50% monedas por 2 batallas! ¡La receta definitiva!",
        "turns": 2,
        "atk_bonus": 20,
        "hp_bonus": 30,
        "coins_mult": 1.5,
    },
    # Receta especial: Spaghetti de Langosta (requiere el ingrediente de Papyrus)
    {
        "name": "🦞🍝 Spaghetti de Langosta",
        "ingredients": ["🦞", "🍝"],
        "effect": "papyrus_special",
        "value": 1,
        "desc": (
            "¡La receta secreta de Papyrus! +25 ATK, +40 HP y +25 DEF a todas tus figuras "
            "en la próxima batalla. ¡NYEH HEH HEH!"
        ),
        "turns": 1,
        "atk_bonus": 25,
        "hp_bonus": 40,
        "def_bonus": 25,
    },
]

# Combinaciones fallidas (ingredientes sin sinergia)
FAILED_RECIPE_MSGS = [
    "💀 La langosta explotó. Mala idea mezclar eso.",
    "🤢 Eso huele horrible. Nadie en su sano juicio comería eso.",
    "😵 El plato resultante tiene vida propia. Lo tiraste.",
    "🔥 Se incendió la cocina. Ups.",
    "❓ Esto no es comida. Es algo más... ¿artístico?",
]

def find_recipe(selected_ings: list) -> dict | None:
    """Busca una receta que coincida con los ingredientes seleccionados."""
    selected_sorted = sorted(selected_ings)
    for recipe in RECIPES:
        recipe_sorted = sorted(recipe["ingredients"])
        if recipe_sorted == selected_sorted:
            return recipe
    # Buscar receta parcial (subset)
    for recipe in RECIPES:
        recipe_sorted = sorted(recipe["ingredients"])
        if all(i in selected_sorted for i in recipe_sorted) and len(recipe_sorted) <= len(selected_sorted):
            return recipe
    return None

TOTAL_RECIPES_FOR_EVENT = 40  # Recetas globales necesarias para Langosta Madre  # Recetas globales necesarias para Langosta Madre

# Contador global de recetas cocinadas
global_recipe_count = 0
lobster_madre_active = False

# Ingredientes que el jugador puede conseguir en batallas (se añaden a user["ingredients"])
BATTLE_INGREDIENT_DROP_CHANCE = 40  # 40% de probabilidad de conseguir ingrediente al ganar batalla

def give_battle_ingredient(user):
    """Da un ingrediente aleatorio al usuario (excepto langosta, que va por /lobster).
    Si Papyrus está en el equipo, 40% de probabilidad de obtener Spaghetti."""
    non_lobster = [k for k in INGREDIENTS if k != "🦞"]
    # Papyrus bonus: si está en el equipo, sube la prob de spaghetti
    team_keys = [user["figures"][i]["key"] for i in user.get("team", [])
                 if i is not None and i < len(user.get("figures", []))]
    if "papyrus" in team_keys and random.randint(1, 100) <= 40:
        ingredient = "🍝"
    else:
        ingredient = random.choice(non_lobster)
    if "ingredients" not in user:
        user["ingredients"] = {}
    user["ingredients"][ingredient] = user["ingredients"].get(ingredient, 0) + 1
    return ingredient

@bot.tree.command(name="ingredientes", description="Ve tus ingredientes de cocina actuales")
async def ingredientes_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    ings = user.get("ingredients", {})
    # Langosta del inventario de figuras
    lobster_count = sum(1 for f in user.get("figures", []) if f["key"] == "lobster")
    embed = discord.Embed(title="🧑‍🍳 Tu despensa", color=0xe67e22)
    ing_str = ""
    if lobster_count:
        ing_str += f"🦞 Langosta x{lobster_count}\n"
    for emoji, amount in ings.items():
        name = INGREDIENTS.get(emoji, emoji)
        ing_str += f"{emoji} {name} x{amount}\n"
    embed.description = ing_str or "_Sin ingredientes. ¡Gana batallas o consigue una langosta!_"
    embed.set_footer(text=f"Recetas globales cocinadas: {global_recipe_count}/{TOTAL_RECIPES_FOR_EVENT}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cook", description="Cocina una receta combinando una langosta con hasta 3 ingredientes")
async def cook_cmd(interaction: discord.Interaction):
    global global_recipe_count, lobster_madre_active
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    lobster_idx = next((i for i, f in enumerate(user.get("figures", [])) if f["key"] == "lobster"), None)
    if lobster_idx is None:
        await interaction.response.send_message("❌ Necesitas al menos una 🦞 Langosta. Consíguela con `/lobster`.", ephemeral=True)
        return
    ings = user.get("ingredients", {})
    available = {k: v for k, v in ings.items() if v > 0}
    if not available:
        await interaction.response.send_message("❌ No tienes ingredientes. ¡Gana batallas para conseguir algunos!", ephemeral=True)
        return

    ing_options = [
        discord.SelectOption(label=f"{INGREDIENTS.get(emoji, emoji)} x{amt}", value=emoji)
        for emoji, amt in available.items()
    ]
    state = {"selected": [], "user_id": interaction.user.id}

    def make_embed():
        selected_str = " + ".join(state["selected"]) if state["selected"] else "_Ninguno aún_"
        return discord.Embed(
            title="🧑‍🍳 ¡Hora de cocinar!",
            description=f"🦞 Langosta + **{selected_str}**\n\nElige hasta 3 ingredientes y luego **Cocinar**:",
            color=0xe67e22
        )

    def make_view():
        view = discord.ui.View(timeout=60)

        if len(state["selected"]) < 3:
            sel = discord.ui.Select(placeholder="Añadir ingrediente...", options=ing_options, max_values=1)
            async def add_ingredient(si: discord.Interaction):
                if si.user.id != state["user_id"]:
                    await si.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                state["selected"].append(sel.values[0])
                await si.response.edit_message(embed=make_embed(), view=make_view())
            sel.callback = add_ingredient
            view.add_item(sel)

        if len(state["selected"]) > 0:
            undo_btn = discord.ui.Button(label="↩️ Quitar último", style=discord.ButtonStyle.secondary)
            async def undo(ui: discord.Interaction):
                if ui.user.id != state["user_id"]:
                    await ui.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                state["selected"].pop()
                await ui.response.edit_message(embed=make_embed(), view=make_view())
            undo_btn.callback = undo
            view.add_item(undo_btn)

            cook_btn = discord.ui.Button(label="🍳 ¡Cocinar!", style=discord.ButtonStyle.success)
            async def do_cook(ci: discord.Interaction):
                if ci.user.id != state["user_id"]:
                    await ci.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                global global_recipe_count, lobster_madre_active
                db2 = load_db()
                user2 = get_user(db2, ci.user.id)
                lb_idx = next((i for i, f in enumerate(user2.get("figures", [])) if f["key"] == "lobster"), None)
                if lb_idx is None:
                    await ci.response.edit_message(content="❌ Ya no tienes langosta.", embed=None, view=None)
                    return
                ings2 = user2.get("ingredients", {})
                for ing in state["selected"]:
                    if ings2.get(ing, 0) <= 0:
                        await ci.response.edit_message(content=f"❌ Ya no tienes {ing}.", embed=None, view=None)
                        return
                # Consumir langosta e ingredientes
                user2["figures"].pop(lb_idx)
                for ing in state["selected"]:
                    ings2[ing] -= 1
                user2["ingredients"] = ings2
                # Buscar receta
                matched = None
                for recipe in RECIPES:
                    if set(recipe["ingredients"]) == set(["🦞"] + state["selected"]):
                        matched = recipe
                        break
                # Verificar hojas de receta conocidas
                if not matched:
                    for idx in user2.get("recipe_sheets", []):
                        if idx < len(RECIPES):
                            recipe = RECIPES[idx]
                            if set(recipe["ingredients"]) == set(["🦞"] + state["selected"]):
                                matched = recipe
                                break
                global_recipe_count += 1
                user2["recipe_count"] = user2.get("recipe_count", 0) + 1
                # Logros de receta
                new_achs = check_achievements(user2, {"action": "cook"})
                if new_achs:
                    ach_names = [ACHIEVEMENTS[a]["name"] for a in new_achs]
                    await interaction.followup.send(f"🏅 ¡Logro desbloqueado! {' · '.join(ach_names)}", ephemeral=True)
                # XP al jugador por cocinar
                user2["xp"] = user2.get("xp", 0) + 20
                _check_player_levelup(user2)
                if matched:
                    if "buffs" not in user2:
                        user2["buffs"] = []
                    user2["buffs"].append({"effect": matched["effect"], "value": matched["value"], "turns": matched["turns"]})
                    if matched["effect"] == "level_fig":
                        team = user2.get("team", [])
                        if team and team[0] is not None and team[0] < len(user2.get("figures", [])):
                            fig = user2["figures"][team[0]]
                            if fig.get("level", 1) < FIGURE_LEVEL_MAX:
                                fig["level"] = fig.get("level", 1) + 1
                    recipe_name = matched["name"]
                    result_desc = matched["desc"]
                    color = 0x2ecc71
                else:
                    recipe_name = "💀 Receta Fallida"
                    result_desc = "Los ingredientes no tienen sinergia entre sí... Se arruinó la comida. No obtienes ningún beneficio.\n\n💡 _Tip: explora para encontrar Hojas de Receta._"
                    color = 0xe74c3c
                save_db(db2)
                embed2 = discord.Embed(title=f"{'✅' if matched else '❌'} {recipe_name}", description=result_desc, color=color)
                embed2.set_footer(text=f"Recetas globales: {global_recipe_count}/{TOTAL_RECIPES_FOR_EVENT}")
                await ci.response.edit_message(embed=embed2, view=None)
                if global_recipe_count >= TOTAL_RECIPES_FOR_EVENT and not lobster_madre_active:
                    lobster_madre_active = True
                    await trigger_lobster_madre(ci.channel)
            cook_btn.callback = do_cook
            view.add_item(cook_btn)

        return view

    await interaction.response.send_message(embed=make_embed(), view=make_view(), ephemeral=True)

# ─── LANGOSTA MADRE (evento global) ───────────────────────────────────────────
LOBSTER_MADRE_HP = 300000
lobster_madre_state = {}

async def trigger_lobster_madre(channel):
    """Inicia el evento global de la Langosta Madre."""
    global lobster_madre_state
    lobster_madre_state = {
        "hp": LOBSTER_MADRE_HP,
        "max_hp": LOBSTER_MADRE_HP,
        "participants": {},  # user_id -> damage dealt
        "active": True,
    }
    embed = discord.Embed(
        title="🦞🦞🦞 ¡APARECE LA LANGOSTA MADRE! 🦞🦞🦞",
        description=(
            "¡40 recetas han sido cocinadas! ¡La **LANGOSTA MADRE** ha despertado!\n\n"
            "❤️ **HP:** 300,000\n⚔️ **ATK:** 70 | 🛡️ **DEF:** 30\n\n"
            "**¡Tienes 60 segundos para unirte!** Todos los jugadores que se unan atacarán juntos."
        ),
        color=0xe74c3c
    )
    view = discord.ui.View(timeout=60)
    join_btn = discord.ui.Button(label="⚔️ ¡UNIRME AL ATAQUE!", style=discord.ButtonStyle.danger, custom_id="join_lobster")
    async def join_cb(inter: discord.Interaction):
        uid = inter.user.id
        if not lobster_madre_state.get("active"):
            await inter.response.send_message("❌ El evento ya terminó.", ephemeral=True)
            return
        if uid in lobster_madre_state["participants"]:
            await inter.response.send_message("✅ Ya estás en el ataque!", ephemeral=True)
            return
        lobster_madre_state["participants"][uid] = 0
        await inter.response.send_message(f"⚔️ ¡<@{uid}> se unió al ataque! Ya somos **{len(lobster_madre_state['participants'])}** guerreros!", ephemeral=False)
    join_btn.callback = join_cb
    view.add_item(join_btn)
    msg = await channel.send(embed=embed, view=view)
    await asyncio.sleep(60)
    # ¡A pelear!
    await run_lobster_madre_battle(channel, msg)

async def run_lobster_madre_battle(channel, msg):
    """Ejecuta la batalla contra la Langosta Madre con todos los participantes."""
    global lobster_madre_active
    participants = list(lobster_madre_state.get("participants", {}).keys())
    if not participants:
        await channel.send("🦞 Nadie se unió al ataque... La Langosta Madre se retira victoriosa.")
        lobster_madre_active = False
        return

    lm_hp = lobster_madre_state["hp"]
    lm_max = lobster_madre_state["max_hp"]
    lm_atk = 70
    all_skills_pool = [sk for skills in FIGURE_SKILLS.values() for sk in skills
                       if sk["type"] not in ("consumed_fury", "revive_team", "ban_hammer", "drain_fill", "lobster")]
    round_num = 0

    while lm_hp > 0 and participants:
        round_num += 1
        log = [f"**Ronda {round_num}**"]

        # Jugadores atacan
        db = load_db()
        total_dmg = 0
        for uid in participants[:]:
            user = get_user(db, uid)
            if not user:
                participants.remove(uid)
                continue
            # Ataque básico del jugador
            atk = random.randint(15, 40)
            lm_hp = max(0, lm_hp - atk)
            total_dmg += atk
            lobster_madre_state["participants"][uid] = lobster_madre_state["participants"].get(uid, 0) + atk
        log.append(f"⚔️ Los {len(participants)} guerreros hacen **{total_dmg}** daño total! (🦞 HP: {lm_hp:,}/{lm_max:,})")

        if lm_hp <= 0:
            break

        # Langosta Madre ataca con habilidad aleatoria
        skill_used = random.choice(all_skills_pool)
        dmg_to_all = random.randint(20, lm_atk)
        log.append(f"🦞 **¡LANGOSTA MADRE** usa **{skill_used['name']}**! ¡{dmg_to_all} daño a todos!")

        bar_len = 20
        filled = int((lm_hp / lm_max) * bar_len)
        hp_bar = "🟥" * filled + "⬛" * (bar_len - filled)

        embed = discord.Embed(
            title="🦞 LANGOSTA MADRE",
            description=f"{hp_bar}\n❤️ **{lm_hp:,}/{lm_max:,} HP**\n\n" + "\n".join(log),
            color=0xe74c3c if lm_hp > lm_max * 0.5 else 0x95a5a6
        )
        await msg.edit(embed=embed)
        await asyncio.sleep(3)

        if lm_hp <= 0:
            break

    # Resultado
    lobster_madre_active = False
    if lm_hp <= 0:
        db = load_db()
        rewards_text = []
        for uid, dmg in lobster_madre_state["participants"].items():
            user = get_user(db, uid)
            if user:
                coins_reward = 500 + (dmg // 10)
                user["coins"] = user.get("coins", 0) + coins_reward
                rewards_text.append(f"<@{uid}>: +{coins_reward}🪙 ({dmg} daño total)")
        save_db(db)
        embed = discord.Embed(
            title="🏆 ¡LANGOSTA MADRE DERROTADA!",
            description="¡Increíble! ¡Los guerreros lograron derrotar a la Langosta Madre!\n\n" + "\n".join(rewards_text[:10]),
            color=0x2ecc71
        )
    else:
        embed = discord.Embed(
            title="💀 La Langosta Madre sobrevivió...",
            description=f"¡La LANGOSTA MADRE sobrevivió con **{lm_hp:,} HP** restantes! ¡Mejor suerte la próxima vez!",
            color=0xe74c3c
        )
    await channel.send(embed=embed)


def _make_stat_up_view(fig_data: dict, fig_key: str, user_data: dict, user_id: int, db) -> discord.ui.View:
    """Crea la view de selección de stat para el level up. Sin async."""
    view = discord.ui.View(timeout=60)
    stats = [("hp","❤️ HP"),("attack","⚔️ ATK"),("defense","🛡️ DEF"),("speed","⚡ VEL")]
    for stat_key, stat_label in stats:
        btn = discord.ui.Button(label=f"{stat_label} +2", style=discord.ButtonStyle.primary, custom_id=f"su_{stat_key}_{fig_key}")
        async def cb(inter: discord.Interaction, sk=stat_key, fk=fig_key, uid=user_id):
            if inter.user.id != uid:
                await inter.response.send_message("❌ No es tu elección.", ephemeral=True)
                return
            db2 = load_db()
            u2 = get_user(db2, uid)
            target = next((f for f in u2.get("figures",[]) if f.get("key")==fk and f.get("pending_stat_up",0)>0), None)
            if not target:
                await inter.response.edit_message(content="✅ Ya procesado.", embed=None, view=None)
                return
            if "stat_ups" not in target: target["stat_ups"] = {}
            target["stat_ups"][sk] = target["stat_ups"].get(sk,0) + 2
            target["pending_stat_up"] = target.get("pending_stat_up",0) - 1
            save_db(db2)
            fig_base = FIGURES.get(fk,{})
            ok_embed = discord.Embed(
                title=f"✅ ¡+2 {sk.upper()} a {fig_base.get('name',fk)}!",
                description=f"Tu figura ahora tiene **+{target['stat_ups'].get(sk,0)}** de bonus en {sk}.",
                color=0x2ecc71
            )
            await inter.response.edit_message(embed=ok_embed, view=None)
            # Si quedan más pendientes, mostrar otro menú
            if target.get("pending_stat_up",0) > 0:
                db3 = load_db()
                u3 = get_user(db3, uid)
                t2 = next((f for f in u3.get("figures",[]) if f.get("key")==fk and f.get("pending_stat_up",0)>0), None)
                if t2:
                    v2 = _make_stat_up_view(t2, fk, u3, uid, db3)
                    again_embed = discord.Embed(
                        title=f"⬆️ ¡{fig_base.get('emoji','')} {fig_base.get('name',fk)} subió otro nivel!",
                        description="Elige otro stat:",
                        color=0xf1c40f
                    )
                    await inter.followup.send(embed=again_embed, view=v2)
        btn.callback = cb
        view.add_item(btn)
    return view

# ============================================================
#  SISTEMA DE LEVEL UP CON ELECCIÓN DE STAT (figuras)
# ============================================================
FIGURE_LEVEL_MAX = 30

def check_figure_levelup(fig_data, interaction_hook=None):
    """
    Verifica si una figura subió de nivel y devuelve (leveled_up, new_level).
    fig_data es el dict de la figura del usuario (con key, level, xp, stat_ups).
    """
    leveled = False
    while fig_data.get("level", 1) < FIGURE_LEVEL_MAX:
        needed = xp_to_level_up(fig_data.get("level", 1))
        if fig_data.get("xp", 0) >= needed:
            fig_data["xp"] -= needed
            fig_data["level"] = fig_data.get("level", 1) + 1
            fig_data["pending_stat_up"] = fig_data.get("pending_stat_up", 0) + 1
            leveled = True
        else:
            break
    return leveled

async def prompt_stat_up(interaction: discord.Interaction, fig_data: dict, fig_key: str, db):
    """Muestra un menú para elegir qué stat subir al subir de nivel."""
    pending = fig_data.get("pending_stat_up", 0)
    if pending <= 0:
        return
    fig_base  = FIGURES.get(fig_key, {})
    fig_name  = fig_base.get("name", fig_key)
    fig_emoji = fig_base.get("emoji", "🎭")
    lvl = fig_data.get("level", 1)

    embed = discord.Embed(
        title=f"⬆️ ¡{fig_emoji} {fig_name} subió al nivel {lvl}!",
        description="Elige **una mejora permanente**:",
        color=0xf1c40f
    )

    # Opciones: +10 HP | +5 ATK | +5 VEL | +10 Barra de carga
    STAT_OPTIONS = [
        ("hp",         "❤️ +10 Vida",          "hp",      10),
        ("attack",     "⚔️ +5 Ataque",          "attack",  5),
        ("speed",      "⚡ +5 Velocidad",        "speed",   5),
        ("energy_cap", "🔋 +10 Barra de carga", "energy_cap", 10),
    ]

    view = discord.ui.View(timeout=60)
    user_id = interaction.user.id

    def make_callback(stat_key, stat_label, stat_field, stat_amt):
        async def callback(inter: discord.Interaction):
            if inter.user.id != user_id:
                await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            db2 = load_db()
            u2 = get_user(db2, user_id)
            if not u2:
                await inter.response.send_message("❌ Error al cargar tu perfil.", ephemeral=True)
                return
            target = next((f for f in u2.get("figures", []) if f.get("key") == fig_key and f.get("pending_stat_up", 0) > 0), None)
            if not target:
                await inter.response.edit_message(content="✅ Ya fue procesado.", embed=None, view=None)
                return
            if "stat_ups" not in target:
                target["stat_ups"] = {}
            target["stat_ups"][stat_field] = target["stat_ups"].get(stat_field, 0) + stat_amt
            target["pending_stat_up"] = target.get("pending_stat_up", 0) - 1
            save_db(db2)
            result_embed = discord.Embed(
                title=f"✅ {fig_emoji} {fig_name} — ¡Mejora aplicada!",
                description=f"**{stat_label}** permanente! (Nv.{target.get('level',1)})\nTotal bonus {stat_field}: **+{target['stat_ups'].get(stat_field,0)}**",
                color=0x2ecc71
            )
            await inter.response.edit_message(embed=result_embed, view=None)
            if target.get("pending_stat_up", 0) > 0:
                await asyncio.sleep(1)
                await prompt_stat_up(inter, target, fig_key, db2)
        return callback

    for stat_key, stat_label, stat_field, stat_amt in STAT_OPTIONS:
        btn = discord.ui.Button(label=stat_label, style=discord.ButtonStyle.primary)
        btn.callback = make_callback(stat_key, stat_label, stat_field, stat_amt)
        view.add_item(btn)

    try:
        if hasattr(interaction, 'followup'):
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.channel.send(embed=embed, view=view)
    except Exception:
        pass

# ============================================================
#  LEADERBOARDS EXPANDIDOS
# ============================================================
@bot.tree.command(name="leaderboard", description="Ver los rankings del servidor")
async def leaderboard_cmd(interaction: discord.Interaction):
    view = discord.ui.View(timeout=60)

@bot.tree.command(name="verperfil", description="Ver el perfil de otro usuario")
@app_commands.describe(usuario="El usuario cuyo perfil quieres ver")
async def ver_perfil(interaction: discord.Interaction, usuario: discord.Member):
    db = load_db()
    u = get_user(db, usuario.id)
    if not u:
        await interaction.response.send_message(f"❌ {usuario.display_name} no está registrado.", ephemeral=True)
        return
    total = u.get("wins", 0) + u.get("losses", 0)
    wr = round(u["wins"] / total * 100, 1) if total > 0 else 0
    lvl = u.get("level", 1)
    xp = u.get("xp", 0)
    needed = xp_to_level_up(lvl)
    embed = discord.Embed(title=f"👤 Perfil de {u['name']}", color=0x3498db)
    embed.add_field(name="🏆 Nivel", value=lvl, inline=True)
    embed.add_field(name="✨ XP", value=f"{xp}/{needed}", inline=True)
    embed.add_field(name="💰 Monedas", value=f"{u.get('coins',0):,}", inline=True)
    embed.add_field(name="✅ Victorias", value=u.get("wins", 0), inline=True)
    embed.add_field(name="❌ Derrotas", value=u.get("losses", 0), inline=True)
    embed.add_field(name="📊 Win Rate", value=f"{wr}%", inline=True)
    embed.add_field(name="🎭 Figuras", value=len(u.get("figures", [])), inline=True)
    team_keys = [u.get("figures", [])[i]["key"] if i < len(u.get("figures", [])) else None
                 for i in (u.get("team", [None, None, None]) or [None, None, None])]
    team_str = " | ".join(FIGURES[k]["emoji"] + " " + FIGURES[k]["name"] if k and k in FIGURES else "—" for k in team_keys)
    embed.add_field(name="⚔️ Equipo activo", value=team_str or "—", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="verfiguras", description="Ver las figuras de otro usuario")
@app_commands.describe(usuario="El usuario cuyas figuras quieres ver")
async def ver_figuras(interaction: discord.Interaction, usuario: discord.Member):
    db = load_db()
    u = get_user(db, usuario.id)
    if not u or not u.get("figures"):
        await interaction.response.send_message(f"❌ {usuario.display_name} no tiene figuras o no está registrado.", ephemeral=True)
        return
    embed = discord.Embed(title=f"🎭 Figuras de {u['name']}", color=0x9b59b6)
    seen = {}
    for fd in u["figures"]:
        k = fd.get("key")
        if k not in seen or fd.get("level", 1) > seen[k].get("level", 1):
            seen[k] = fd
    for k, fd in seen.items():
        fig = FIGURES.get(k)
        if not fig:
            continue
        lvl = fd.get("level", 1)
        xp = fd.get("xp", 0)
        stat_ups = fd.get("stat_ups", {})
        sup_str = " ".join(f"+{v}{s}" for s, v in stat_ups.items()) if stat_ups else ""
        embed.add_field(
            name=f"{fig['emoji']} {fig['name']} Nv.{lvl}",
            value=f"❤️{apply_level_bonus(fig['hp'],lvl)+stat_ups.get('hp',0)} ⚔️{apply_level_bonus(fig['attack'],lvl)+stat_ups.get('attack',0)} 🛡️{apply_level_bonus(fig['defense'],lvl)+stat_ups.get('defense',0)} ⚡{apply_level_bonus(fig['speed'],lvl)+stat_ups.get('speed',0)}\nXP: {xp}/{xp_to_level_up(lvl)} {sup_str}",
            inline=True
        )
    await interaction.response.send_message(embed=embed)

# ============================================================
#  SISTEMA DE MISIONES (/quest)
# ============================================================
QUESTS = {
    "documentos_jane": {
        "name": "📄 Documentos de Jane",
        "desc": "Jane Doe escondió sus documentos de identidad. Consigue 6 documentos ganando batallas para desbloquear la posibilidad de comprarla.",
        "goal": 6,
        "progress_key": "docs_collected",
        "reward_key": "jane_unlocked",
        "reward_desc": "🔓 ¡Jane Doe desbloqueada en la tienda!",
        "drop_chance": 60,  # % de chance de documento al ganar batalla
    },
}

def is_quest_unlocked(user: dict, quest_id: str) -> bool:
    return user.get("quests_completed", {}).get(quest_id, False)

def get_quest_progress(user: dict, quest_id: str) -> int:
    return user.get("quest_progress", {}).get(quest_id, 0)

async def check_quest_drops(user: dict, quest_id: str, channel, db=None):
    """Llamar tras ganar una batalla para ver si cae progreso de misión."""
    quest = QUESTS.get(quest_id)
    if not quest:
        return
    if is_quest_unlocked(user, quest_id):
        return
    active = user.get("active_quests", [])
    if quest_id not in active:
        return
    if random.randint(1, 100) <= quest["drop_chance"]:
        if "quest_progress" not in user:
            user["quest_progress"] = {}
        user["quest_progress"][quest_id] = user["quest_progress"].get(quest_id, 0) + 1
        prog = user["quest_progress"][quest_id]
        goal = quest["goal"]
        if db: save_db(db)
        await channel.send(f"📄 **¡Documento encontrado!** ({prog}/{goal}) — Misión: **{quest['name']}**")
        if prog >= goal:
            if "quests_completed" not in user:
                user["quests_completed"] = {}
            user["quests_completed"][quest_id] = True
            if quest_id == "documentos_jane":
                user["jane_unlocked"] = True
            if db: save_db(db)
            await channel.send(f"🎉 **¡MISIÓN COMPLETADA!** {quest['name']}\n{quest['reward_desc']}\n¡Ya puedes comprar a Jane Doe en la `/tienda`!")

@bot.tree.command(name="quest", description="Ver y activar misiones disponibles")
async def quest_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Misiones disponibles", color=0xe67e22)
    view = discord.ui.View(timeout=60)

    for qid, quest in QUESTS.items():
        completed = is_quest_unlocked(user, qid)
        active = qid in user.get("active_quests", [])
        prog = get_quest_progress(user, qid)
        goal = quest["goal"]

        if completed:
            status = f"✅ Completada"
        elif active:
            status = f"🔄 En progreso: {prog}/{goal}"
        else:
            status = "❌ Inactiva"

        embed.add_field(
            name=f"{quest['name']} — {status}",
            value=f"{quest['desc']}\n**Recompensa:** {quest['reward_desc']}",
            inline=False
        )

        if not completed and not active:
            btn = discord.ui.Button(label=f"Activar: {quest['name']}", style=discord.ButtonStyle.success, custom_id=f"quest_{qid}")
            def make_activate(quest_id, quest_name):
                async def activate(inter: discord.Interaction):
                    if inter.user.id != interaction.user.id:
                        await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                        return
                    db2 = load_db()
                    u2 = get_user(db2, inter.user.id)
                    if "active_quests" not in u2:
                        u2["active_quests"] = []
                    if quest_id not in u2["active_quests"]:
                        u2["active_quests"].append(quest_id)
                    save_db(db2)
                    await inter.response.send_message(f"✅ ¡Misión **{quest_name}** activada! Gana batallas para progresar.", ephemeral=True)
                return activate
            btn.callback = make_activate(qid, quest["name"])
            view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view)

# ============================================================
#  SISTEMA DE EXPLORACIÓN (/exploracion)
# ============================================================
EXPLORATION_DURATION = 30 * 60  # 30 minutos en segundos
EXPLORATION_REWARDS = [
    {"type": "coins",      "weight": 35, "min": 100, "max": 400},
    {"type": "ingredient", "weight": 30},
    {"type": "xp_fig",    "weight": 20, "value": 80},
    {"type": "recipe_sheet","weight": 10},
    {"type": "figure",     "weight": 5},
]

RECIPE_SHEETS = [
    {"name": "📜 Hoja: Langosta Picante",   "recipe_idx": 0},
    {"name": "📜 Hoja: Estofado de Langosta","recipe_idx": 1},
    {"name": "📜 Hoja: Langosta Gourmet",   "recipe_idx": 2},
    {"name": "📜 Hoja: Langosta con Queso", "recipe_idx": 3},
    {"name": "📜 Hoja: Langosta Dulce",     "recipe_idx": 4},
]

def pick_exploration_reward(user: dict) -> dict:
    """Elige una recompensa de exploración según los pesos."""
    total = sum(r["weight"] for r in EXPLORATION_REWARDS)
    roll = random.randint(1, total)
    acc = 0
    for reward in EXPLORATION_REWARDS:
        acc += reward["weight"]
        if roll <= acc:
            if reward["type"] == "coins":
                amount = random.randint(reward["min"], reward["max"])
                user["coins"] = user.get("coins", 0) + amount
                return {"type": "coins", "desc": f"💰 +{amount} monedas"}
            elif reward["type"] == "ingredient":
                non_lobster = [k for k in INGREDIENTS if k != "🦞"]
                ing = random.choice(non_lobster)
                if "ingredients" not in user:
                    user["ingredients"] = {}
                user["ingredients"][ing] = user["ingredients"].get(ing, 0) + 1
                return {"type": "ingredient", "desc": f"{ing} {INGREDIENTS.get(ing, 'Ingrediente')} x1"}
            elif reward["type"] == "xp_fig":
                return {"type": "xp_fig", "desc": f"✨ +{reward['value']} XP a tus figuras exploradoras"}
            elif reward["type"] == "recipe_sheet":
                sheet = random.choice(RECIPE_SHEETS)
                if "recipe_sheets" not in user:
                    user["recipe_sheets"] = []
                user["recipe_sheets"].append(sheet["recipe_idx"])
                return {"type": "recipe_sheet", "desc": f"📜 ¡Hoja de receta: {sheet['name']}!"}
            elif reward["type"] == "figure":
                buyable = [k for k, v in FIGURES.items() if v.get("price", 0) > 0 and k not in ("roblox_boss", "janedoe", "santa_vaca", "lobster")]
                if buyable:
                    fig_key = random.choice(buyable)
                    user["figures"].append({"key": fig_key, "level": 1, "xp": 0})
                    fig = FIGURES[fig_key]
                    return {"type": "figure", "desc": f"🎭 ¡Encontraste a **{fig['emoji']} {fig['name']}**!"}
                else:
                    user["coins"] = user.get("coins", 0) + 200
                    return {"type": "coins", "desc": "💰 +200 monedas (sin figuras disponibles)"}
    return {"type": "nothing", "desc": "Nada especial..."}

@bot.tree.command(name="exploracion", description="Manda 3 figuras a explorar (30 min) para conseguir recompensas")
async def exploracion_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    # Ver si ya hay exploración activa
    exp = user.get("exploration")
    now = time.time()
    if exp and now < exp.get("end_time", 0):
        remaining = int(exp["end_time"] - now)
        m, s = divmod(remaining, 60)
        fig_names = [FIGURES.get(k, {}).get("name", k) for k in exp.get("fig_keys", [])]
        embed = discord.Embed(
            title="🗺️ Exploración en curso",
            description=f"Tus figuras **{', '.join(fig_names)}** regresan en **{m}m {s}s**.",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Recoger resultados si ya terminó
    if exp and now >= exp.get("end_time", 0):
        rewards = []
        db2 = load_db()
        u2 = get_user(db2, interaction.user.id)
        for fig_key in exp.get("fig_keys", []):
            reward = pick_exploration_reward(u2)
            rewards.append(reward)
            # XP a las figuras exploradoras
            for fd in u2.get("figures", []):
                if fd.get("key") == fig_key:
                    fd["xp"] = fd.get("xp", 0) + 60
                    if check_figure_levelup(fd):
                        pass
                    break
        # XP al jugador por explorar
        u2["xp"] = u2.get("xp", 0) + 30
        _check_player_levelup(u2)
        u2["exploration"] = None
        save_db(db2)
        embed = discord.Embed(
            title="🎒 ¡Tu equipo regresó de la exploración!",
            description=f"Estuvieron fuera **30 minutos** y esto encontraron:",
            color=0xf1c40f
        )
        total_coins = 0
        total_ings = []
        total_figs = []
        for i, r in enumerate(rewards):
            fig_key = exp["fig_keys"][i] if i < len(exp["fig_keys"]) else "?"
            fig_name = FIGURES.get(fig_key, {}).get("name", fig_key)
            embed.add_field(name=f"🗺️ {fig_name} encontró:", value=r["desc"], inline=False)
            if r["type"] == "coins":
                total_coins += int(r["desc"].replace("💰 +","").replace(" monedas","").replace(",","") if "monedas" in r["desc"] else 0)
            elif r["type"] == "ingredient":
                total_ings.append(r["desc"])
            elif r["type"] == "figure":
                total_figs.append(r["desc"])

        if total_coins > 0:
            embed.add_field(name="💰 Total monedas", value=f"+{total_coins:,}🪙", inline=True)
        if total_ings:
            embed.add_field(name="🧺 Ingredientes", value="\n".join(total_ings), inline=True)
        if total_figs:
            embed.add_field(name="🎭 Figuras", value="\n".join(total_figs), inline=True)
        embed.set_footer(text="Usa /exploracion de nuevo para mandar a explorar!")
        await interaction.response.send_message(embed=embed)
        return

    # Elegir figuras para explorar
    figs = user.get("figures", [])
    exploring_keys = [f["key"] for f in (user.get("exploration", {}) or {}).get("fig_keys", [])]
    team_indices = user.get("team", [])

    # Filtrar figuras disponibles (no en exploración activa)
    available_figs = []
    seen_keys = set()
    for i, fd in enumerate(figs):
        k = fd.get("key")
        if k and k not in seen_keys and k not in exploring_keys:
            seen_keys.add(k)
            available_figs.append((i, fd))

    if len(available_figs) < 1:
        await interaction.response.send_message("❌ No tienes figuras disponibles para explorar.", ephemeral=True)
        return

    options = []
    for idx, fd in available_figs[:25]:
        fig = FIGURES.get(fd["key"])
        if fig:
            raw_emoji = fig["emoji"]
            emoji_obj = discord.PartialEmoji.from_str(raw_emoji) if raw_emoji.startswith("<") else raw_emoji
            opt = discord.SelectOption(
                label=f"{fig['name']} Nv.{fd.get('level',1)}",
                value=fd["key"],
                description=f"{fig['rarity'].upper()} | HP:{fig['hp']} ATK:{fig['attack']}"
            )
            try:
                opt.emoji = emoji_obj
            except Exception:
                pass
            options.append(opt)

    state = {"selected": [], "user_id": interaction.user.id}

    async def show_exp_menu(inter, is_first=False):
        embed = discord.Embed(
            title="🗺️ Preparar Exploración",
            description=f"Elige hasta 3 figuras para explorar **(30 minutos)**.\nNo podrán batallar durante la exploración.\n\nSeleccionadas: **{', '.join(FIGURES.get(k,{}).get('name',k) for k in state['selected']) or 'Ninguna'}**",
            color=0x2ecc71
        )
        view = discord.ui.View(timeout=60)
        sel = discord.ui.Select(placeholder="Elige una figura...", options=options, max_values=1)

        async def add_fig(si: discord.Interaction):
            if si.user.id != state["user_id"]:
                await si.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            k = sel.values[0]
            if k in state["selected"]:
                await si.response.send_message("⚠️ Ya seleccionaste esa figura.", ephemeral=True)
                return
            if len(state["selected"]) >= 3:
                await si.response.send_message("❌ Máximo 3 figuras.", ephemeral=True)
                return
            state["selected"].append(k)
            new_embed = discord.Embed(
                title="🗺️ Preparar Exploración",
                description=f"Seleccionadas: **{', '.join(FIGURES.get(k2,{}).get('name',k2) for k2 in state['selected'])}**\n\nAñade más o pulsa **¡Explorar!**",
                color=0x2ecc71
            )
            await si.response.edit_message(embed=new_embed, view=build_exp_view(state))
        sel.callback = add_fig
        view.add_item(sel)

        start_btn = discord.ui.Button(
            label="🗺️ ¡Explorar!",
            style=discord.ButtonStyle.success,
            disabled=len(state["selected"]) == 0
        )
        async def start_exp(si: discord.Interaction):
            if si.user.id != state["user_id"]:
                await si.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            db2 = load_db()
            u2 = get_user(db2, si.user.id)
            end_time = time.time() + EXPLORATION_DURATION
            u2["exploration"] = {
                "fig_keys": state["selected"],
                "end_time": end_time,
                "started": time.time()
            }
            save_db(db2)
            names = [FIGURES.get(k, {}).get("name", k) for k in state["selected"]]
            conf_embed = discord.Embed(
                title="✅ ¡Exploración iniciada!",
                description=f"**{', '.join(names)}** salieron a explorar.\nRegresarán en **30 minutos**.\nUsa `/exploracion` de nuevo para recoger sus recompensas.",
                color=0x2ecc71
            )
            await si.response.edit_message(embed=conf_embed, view=None)
        start_btn.callback = start_exp
        view.add_item(start_btn)
        return embed, view

    def build_exp_view(st):
        """Reconstruye el view con los datos actuales."""
        v = discord.ui.View(timeout=60)
        sel2 = discord.ui.Select(placeholder="Añadir figura...", options=options, max_values=1)
        async def add2(si: discord.Interaction):
            if si.user.id != st["user_id"]: return
            k = sel2.values[0]
            if k not in st["selected"] and len(st["selected"]) < 3:
                st["selected"].append(k)
            new_embed = discord.Embed(
                title="🗺️ Preparar Exploración",
                description=f"Seleccionadas: **{', '.join(FIGURES.get(k2,{}).get('name',k2) for k2 in st['selected'])}**",
                color=0x2ecc71
            )
            await si.response.edit_message(embed=new_embed, view=build_exp_view(st))
        sel2.callback = add2
        v.add_item(sel2)
        sb = discord.ui.Button(label="🗺️ ¡Explorar!", style=discord.ButtonStyle.success)
        async def do_start(si: discord.Interaction):
            if si.user.id != st["user_id"]: return
            db2 = load_db()
            u2 = get_user(db2, si.user.id)
            u2["exploration"] = {"fig_keys": st["selected"], "end_time": time.time() + EXPLORATION_DURATION, "started": time.time()}
            save_db(db2)
            names = [FIGURES.get(k, {}).get("name", k) for k in st["selected"]]
            await si.response.edit_message(embed=discord.Embed(title="✅ ¡Exploración iniciada!", description=f"**{', '.join(names)}** salieron. Regresan en 30 min.", color=0x2ecc71), view=None)
        sb.callback = do_start
        v.add_item(sb)
        return v

    embed, view = await show_exp_menu(interaction, is_first=True)
    await interaction.response.send_message(embed=embed, view=view)

# ============================================================
#  SISTEMA MULTIPLAYER (/multiplayer) — hasta 4 jugadores
# ============================================================
active_multiplayer = {}  # channel_id -> MultiplayerSession

class MultiplayerSession:
    def __init__(self, host_id, host_name, channel_id):
        self.channel_id = channel_id
        self.host_id = host_id
        self.players = {host_id: {"name": host_name, "ready": False, "team": None, "figs_data": None}}
        self.max_players = 4
        self.started = False
        self.turn_order = []
        self.current_turn_idx = 0
        self.round_num = 1
        self.eliminated = set()
        self.log = []
        self.invert_event_active = False  # evento de inversión

@bot.tree.command(name="multiplayer", description="Crea una batalla multijugador (2-4 jugadores)")
async def multiplayer_cmd(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_multiplayer:
        await interaction.response.send_message("❌ Ya hay una partida multijugador en este canal.", ephemeral=True)
        return
    if channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa. Usa `/reset` primero.", ephemeral=True)
        return
@bot.tree.command(name="subirstat", description="Elige qué stat subir en tus figuras con nivel pendiente")
async def subir_stat_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    # Buscar figuras con pending
    pending_figs = [(i, fd) for i, fd in enumerate(user.get("figures", [])) if fd.get("pending_stat_up", 0) > 0]
    if not pending_figs:
        await interaction.response.send_message("✅ No hay figuras esperando subir stat.", ephemeral=True)
        return

    idx, fd = pending_figs[0]
    fig = FIGURES.get(fd["key"], {})
    fig_name = fig.get("name", fd["key"])
    fig_emoji = fig.get("emoji", "🎭")
    lvl = fd.get("level", 1)

    embed = discord.Embed(
        title=f"⬆️ {fig_emoji} {fig_name} — Nv.{lvl}",
        description=f"Tienes **{fd['pending_stat_up']}** punto(s) de stat pendiente.\n¿Qué stat quieres subir **+2**?",
        color=0xf1c40f
    )
    view = discord.ui.View(timeout=60)
    stats = [("hp", "❤️ HP +2"), ("attack", "⚔️ ATK +2"), ("defense", "🛡️ DEF +2"), ("speed", "⚡ VEL +2")]

    for stat_key, label in stats:
        btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
        def make_cb(sk, sl, fig_idx):
            async def cb(inter: discord.Interaction):
                if inter.user.id != interaction.user.id:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                db2 = load_db()
                u2 = get_user(db2, inter.user.id)
                target_fd = u2["figures"][fig_idx]
                if "stat_ups" not in target_fd:
                    target_fd["stat_ups"] = {}
                target_fd["stat_ups"][sk] = target_fd["stat_ups"].get(sk, 0) + 2
                target_fd["pending_stat_up"] = max(0, target_fd.get("pending_stat_up", 0) - 1)
                save_db(db2)
                result = discord.Embed(
                    title=f"✅ ¡{FIGURES.get(target_fd['key'],{}).get('emoji','🎭')} {FIGURES.get(target_fd['key'],{}).get('name',target_fd['key'])} mejorado!",
                    description=f"**{sl}** permanente aplicado. (Nv.{target_fd.get('level',1)})",
                    color=0x2ecc71
                )
                await inter.response.edit_message(embed=result, view=None)
                # Verificar si quedan más pending
                if target_fd.get("pending_stat_up", 0) > 0:
                    await asyncio.sleep(1)
                    await subir_stat_cmd.callback(inter)
            return cb
        btn.callback = make_cb(stat_key, label, idx)
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view)

# --- SAY (solo matheogamer64) ---
GAMER_ID = 1236293193893412975

@bot.tree.command(name="say", description="[GAMER] Con este comando, puedes hacer que el bot diga lo que quieras")
@app_commands.describe(mensaje="Lo que dirá el bot")
async def say(interaction: discord.Interaction, mensaje: str):
    if interaction.user.id != GAMER_ID:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
@bot.tree.command(name="trade", description="Propone un intercambio de oro, figuras o ingredientes")
@app_commands.describe(usuario="Usuario con quien hacer el trade")
async def trade(interaction: discord.Interaction, usuario: discord.Member):
    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes tradear contigo mismo.", ephemeral=True)
        return
    db = load_db()
    offerer = get_user(db, interaction.user.id)
    receiver = get_user(db, usuario.id)
    if not offerer:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    if not receiver:
        await interaction.response.send_message("❌ Ese usuario no está registrado.", ephemeral=True)
        return
    if usuario.id in pending_trades:
        await interaction.response.send_message("❌ Ese usuario ya tiene un trade pendiente.", ephemeral=True)
        return

    # Estado del trade: lo que ofrece cada lado
    trade_state = {
        "offerer_id":  interaction.user.id,
        "receiver_id": usuario.id,
        "offer":       {"coins": 0, "figures": [], "ingredients": {}},
        "request":     {"coins": 0, "figures": [], "ingredients": {}},
        "confirmed":   {"offerer": False, "receiver": False},
    }

    def build_trade_embed():
        db2 = load_db()
        o2 = get_user(db2, interaction.user.id)
        r2 = get_user(db2, usuario.id)
        embed = discord.Embed(title="🔄 Propuesta de Trade", color=0x3498db)

        def side_value(side):
            lines = []
            if trade_state[side]["coins"] > 0:
                lines.append(f"💰 {trade_state[side]['coins']:,}🪙")
            for fk in trade_state[side]["figures"]:
                fig = FIGURES.get(fk, {})
                lines.append(f"🎭 {fig.get('name', fk)}")
            for k, v in trade_state[side]["ingredients"].items():
                if v > 0:
                    lines.append(f"{k} {INGREDIENTS.get(k,k)} x{v}")
            return "\n".join(lines) if lines else "_(nada aún)_"

        embed.add_field(name=f"📤 {o2['name']} ofrece", value=side_value("offer"), inline=True)
        embed.add_field(name=f"📥 {r2['name']} ofrece", value=side_value("request"), inline=True)

        confirmed_str = []
        if trade_state["confirmed"]["offerer"]: confirmed_str.append(f"✅ {o2['name']}")
        if trade_state["confirmed"]["receiver"]: confirmed_str.append(f"✅ {r2['name']}")
        if confirmed_str:
            embed.set_footer(text="Confirmado por: " + ", ".join(confirmed_str))
        return embed

    def build_trade_view():
        view = discord.ui.View(timeout=120)

        # Botón añadir a mi oferta
        add_offer_btn = discord.ui.Button(label="📤 Añadir a mi oferta", style=discord.ButtonStyle.primary, custom_id="add_offer")
        # Botón añadir a lo que pido
        add_req_btn   = discord.ui.Button(label="📥 Añadir lo que pido", style=discord.ButtonStyle.secondary, custom_id="add_req")
        # Confirmar
        confirm_btn   = discord.ui.Button(label="✅ Confirmar", style=discord.ButtonStyle.success, custom_id="confirm_trade")
        # Cancelar
        cancel_btn    = discord.ui.Button(label="❌ Cancelar", style=discord.ButtonStyle.danger, custom_id="cancel_trade")

        async def add_offer_cb(inter: discord.Interaction):
            if inter.user.id not in (interaction.user.id, usuario.id):
                await inter.response.send_message("❌ No eres parte de este trade.", ephemeral=True)
                return
            side = "offer" if inter.user.id == interaction.user.id else "request"
            await show_trade_add_menu(inter, trade_state, side, interaction, usuario, build_trade_view, build_trade_embed)

        async def add_req_cb(inter: discord.Interaction):
            if inter.user.id not in (interaction.user.id, usuario.id):
                await inter.response.send_message("❌ No eres parte de este trade.", ephemeral=True)
                return
            side = "request" if inter.user.id == interaction.user.id else "offer"
            await show_trade_add_menu(inter, trade_state, side, interaction, usuario, build_trade_view, build_trade_embed)

        async def confirm_cb(inter: discord.Interaction):
            if inter.user.id == interaction.user.id:
                trade_state["confirmed"]["offerer"] = True
            elif inter.user.id == usuario.id:
                trade_state["confirmed"]["receiver"] = True
            else:
                await inter.response.send_message("❌ No eres parte de este trade.", ephemeral=True)
                return

            if trade_state["confirmed"]["offerer"] and trade_state["confirmed"]["receiver"]:
                # Ejecutar el trade
                await execute_trade(inter, trade_state, interaction, usuario)
            else:
                emb = build_trade_embed()
                await inter.response.edit_message(embed=emb, view=build_trade_view())

        async def cancel_cb(inter: discord.Interaction):
            if inter.user.id not in (interaction.user.id, usuario.id):
                await inter.response.send_message("❌ No eres parte de este trade.", ephemeral=True)
                return
            pending_trades.pop(usuario.id, None)
            cancel_embed = discord.Embed(title="❌ Trade cancelado.", color=0xe74c3c)
            await inter.response.edit_message(embed=cancel_embed, view=None)

        add_offer_btn.callback = add_offer_cb
        add_req_btn.callback   = add_req_cb
        confirm_btn.callback   = confirm_cb
        cancel_btn.callback    = cancel_cb

        view.add_item(add_offer_btn)
        view.add_item(add_req_btn)
        view.add_item(confirm_btn)
        view.add_item(cancel_btn)
        return view

    pending_trades[usuario.id] = trade_state
    emb = build_trade_embed()
    await interaction.response.send_message(
        content=f"{usuario.mention} — **{offerer['name']}** quiere hacer un trade contigo!",
        embed=emb,
        view=build_trade_view()
    )


async def show_trade_add_menu(inter, trade_state, side, orig_inter, target_member, build_view_fn, build_embed_fn):
    """Muestra el menú para añadir oro/figura/ingrediente al lado del trade."""
    user_id = inter.user.id
    embed = discord.Embed(title="➕ ¿Qué quieres añadir?", color=0x3498db)
    view = discord.ui.View(timeout=60)

    gold_btn = discord.ui.Button(label="💰 Oro", style=discord.ButtonStyle.primary)
    fig_btn  = discord.ui.Button(label="🎭 Figura", style=discord.ButtonStyle.primary)
    ing_btn  = discord.ui.Button(label="🧺 Ingrediente", style=discord.ButtonStyle.primary)

    async def gold_trade_cb(gi: discord.Interaction):
        if gi.user.id != user_id: return
        modal = discord.ui.Modal(title="💰 Añadir oro al trade")
        amt = discord.ui.TextInput(label="¿Cuánto oro?", placeholder="Ej: 200", max_length=10)
        modal.add_item(amt)
        async def gold_submit(mi: discord.Interaction):
            try: amount = int(amt.value.strip())
            except: await mi.response.send_message("❌ Inválido.", ephemeral=True); return
            db2 = load_db()
            u2 = get_user(db2, user_id)
            if u2.get("coins",0) < amount:
                await mi.response.send_message(f"❌ No tienes suficiente. Tienes {u2.get('coins',0):,}🪙", ephemeral=True)
                return
            trade_state[side]["coins"] += amount
            emb2 = build_embed_fn()
            await mi.response.edit_message(embed=emb2, view=build_view_fn())
        modal.on_submit = gold_submit
        await gi.response.send_modal(modal)

    async def fig_trade_cb(fi: discord.Interaction):
        if fi.user.id != user_id: return
        db2 = load_db()
        u2 = get_user(db2, user_id)
        figs = u2.get("figures", [])
        if not figs:
            await fi.response.send_message("❌ No tienes figuras.", ephemeral=True)
            return
        seen = {}
        for i, fd in enumerate(figs):
            k = fd["key"]
            if k not in seen and k not in trade_state[side]["figures"]:
                seen[k] = i
        if not seen:
            await fi.response.send_message("❌ Sin figuras disponibles para añadir.", ephemeral=True)
            return
        options = []
        for k, idx in list(seen.items())[:25]:
            fig = FIGURES.get(k, {})
            options.append(discord.SelectOption(label=f"{fig.get('name',k)}", value=k, emoji=fig.get("emoji","🎭")))
        sel = discord.ui.Select(placeholder="Figura a añadir...", options=options)
        async def fig_sel_cb(si: discord.Interaction):
            trade_state[side]["figures"].append(sel.values[0])
            emb2 = build_embed_fn()
            await si.response.edit_message(embed=emb2, view=build_view_fn())
        sel.callback = fig_sel_cb
        sv = discord.ui.View(timeout=60)
        sv.add_item(sel)
        await fi.response.edit_message(embed=discord.Embed(title="🎭 Elige figura", color=0x9b59b6), view=sv)

    async def ing_trade_cb(ii: discord.Interaction):
        if ii.user.id != user_id: return
        db2 = load_db()
        u2 = get_user(db2, user_id)
        ings = {k: v for k, v in u2.get("ingredients", {}).items() if v > 0}
        if not ings:
            await ii.response.send_message("❌ No tienes ingredientes.", ephemeral=True)
            return
        options = [
            discord.SelectOption(label=f"{INGREDIENTS.get(k,k)} x{v}", value=k, emoji=k)
            for k, v in list(ings.items())[:25]
        ]
        sel = discord.ui.Select(placeholder="Ingrediente a añadir...", options=options)
        async def ing_sel_cb(si: discord.Interaction):
            chosen = sel.values[0]
            modal = discord.ui.Modal(title="🧺 ¿Cuántos?")
            qty_inp = discord.ui.TextInput(label=f"Tienes {ings[chosen]}x. ¿Cuántos añades?", placeholder="Ej: 1", max_length=5)
            modal.add_item(qty_inp)
            async def ing_modal_sub(mi: discord.Interaction):
                try: qty = int(qty_inp.value.strip())
                except: await mi.response.send_message("❌ Inválido.", ephemeral=True); return
                if qty <= 0 or qty > ings[chosen]:
                    await mi.response.send_message(f"❌ Máximo {ings[chosen]}.", ephemeral=True); return
                trade_state[side]["ingredients"][chosen] = trade_state[side]["ingredients"].get(chosen,0) + qty
                emb2 = build_embed_fn()
                await mi.response.edit_message(embed=emb2, view=build_view_fn())
            modal.on_submit = ing_modal_sub
            await si.response.send_modal(modal)
        sel.callback = ing_sel_cb
        sv = discord.ui.View(timeout=60)
        sv.add_item(sel)
        await ii.response.edit_message(embed=discord.Embed(title="🧺 Elige ingrediente", color=0xe67e22), view=sv)

    gold_btn.callback = gold_trade_cb
    fig_btn.callback  = fig_trade_cb
    ing_btn.callback  = ing_trade_cb
    view.add_item(gold_btn)
    view.add_item(fig_btn)
    view.add_item(ing_btn)
    await inter.response.edit_message(embed=embed, view=view)


async def execute_trade(inter: discord.Interaction, trade_state, orig_inter, target_member):
    """Ejecuta el intercambio final."""
    db = load_db()
    offerer = get_user(db, trade_state["offerer_id"])
    receiver = get_user(db, trade_state["receiver_id"])

    offer   = trade_state["offer"]
    request = trade_state["request"]

    # Validar que ambos tienen suficiente
    if offerer.get("coins",0) < offer["coins"]:
        await inter.response.edit_message(embed=discord.Embed(title="❌ Trade fallido", description=f"{offerer['name']} no tiene suficiente oro.", color=0xe74c3c), view=None)
        pending_trades.pop(trade_state["receiver_id"], None)
        return
    if receiver.get("coins",0) < request["coins"]:
        await inter.response.edit_message(embed=discord.Embed(title="❌ Trade fallido", description=f"{receiver['name']} no tiene suficiente oro.", color=0xe74c3c), view=None)
        pending_trades.pop(trade_state["receiver_id"], None)
        return

    # Intercambiar oro
    offerer["coins"] = offerer.get("coins",0) - offer["coins"] + request["coins"]
    receiver["coins"] = receiver.get("coins",0) - request["coins"] + offer["coins"]

    # Intercambiar figuras (offerer → receiver)
    for fig_key in offer["figures"]:
        idx = next((i for i, f in enumerate(offerer.get("figures",[])) if f["key"]==fig_key), None)
        if idx is not None:
            fig_data = offerer["figures"].pop(idx)
            receiver.setdefault("figures", []).append(fig_data)

    # Intercambiar figuras (receiver → offerer)
    for fig_key in request["figures"]:
        idx = next((i for i, f in enumerate(receiver.get("figures",[])) if f["key"]==fig_key), None)
        if idx is not None:
            fig_data = receiver["figures"].pop(idx)
            offerer.setdefault("figures", []).append(fig_data)

    # Intercambiar ingredientes
    for k, v in offer["ingredients"].items():
        offerer.setdefault("ingredients",{})[k] = offerer["ingredients"].get(k,0) - v
        receiver.setdefault("ingredients",{})[k] = receiver["ingredients"].get(k,0) + v
    for k, v in request["ingredients"].items():
        receiver.setdefault("ingredients",{})[k] = receiver["ingredients"].get(k,0) - v
        offerer.setdefault("ingredients",{})[k] = offerer["ingredients"].get(k,0) + v

    save_db(db)
    pending_trades.pop(trade_state["receiver_id"], None)

    embed = discord.Embed(
        title="✅ ¡Trade completado!",
        description=f"**{offerer['name']}** y **{receiver['name']}** completaron el intercambio exitosamente.",
        color=0x2ecc71
    )
    if offer["coins"] > 0 or request["coins"] > 0:
        embed.add_field(name="💰 Oro intercambiado", value=f"{offerer['name']}: -{offer['coins']:,}🪙 +{request['coins']:,}🪙\n{receiver['name']}: -{request['coins']:,}🪙 +{offer['coins']:,}🪙", inline=False)
    await inter.response.edit_message(embed=embed, view=None)

# ============================================================
#  ARRANQUE
# ============================================================
# ============================================================
#  NIVEL DEL JUGADOR — helper
# ============================================================
PLAYER_LEVEL_MAX = 100

@bot.tree.command(name="rebirth", description="Reinicia desde el nivel 1, manteniendo tu árbol de aprendizaje")
async def rebirth_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    rb_count = user.get("rebirth_count", 0)
    cost     = REBIRTH_BASE_COST + rb_count * REBIRTH_COST_INC
    coins    = user.get("coins", 0)
    lvl      = user.get("level", 1)

    embed = discord.Embed(
        title="🔄 REBIRTH",
        description=(
            f"¿Estás seguro de que quieres hacer **Rebirth #{rb_count + 1}**?\n\n"
            f"**Se reiniciará:**\n"
            f"• Nivel → 1 · XP → 0\n"
            f"• Skill Points no gastados → 0\n\n"
            f"**Se conservará:**\n"
            f"• Tu árbol de aprendizaje\n"
            f"• Figuras · Monedas · Victorias\n\n"
            f"💰 Coste: **{cost:,}🪙** | Tienes: **{coins:,}🪙**\n"
            f"📈 Próximo rebirth costará: **{cost + REBIRTH_COST_INC:,}🪙**"
        ),
        color=0xe74c3c
    )

    if coins < cost:
        embed.set_footer(text=f"❌ No tienes suficientes monedas. Te faltan {cost - coins:,}🪙.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    view = discord.ui.View(timeout=60)
    uid  = interaction.user.id

    confirm_btn = discord.ui.Button(label="✅ Confirmar Rebirth", style=discord.ButtonStyle.danger)
    cancel_btn  = discord.ui.Button(label="❌ Cancelar",          style=discord.ButtonStyle.secondary)

    async def confirm_cb(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
            return
        db2  = load_db()
        u2   = get_user(db2, inter.user.id)
        cost2 = REBIRTH_BASE_COST + u2.get("rebirth_count", 0) * REBIRTH_COST_INC
        if u2.get("coins", 0) < cost2:
            await inter.response.edit_message(content="❌ Ya no tienes suficiente oro.", embed=None, view=None)
            return
        # Preservar
        tree      = u2.get("learn_tree", {})
        figures   = u2.get("figures", [])
        team      = u2.get("team", [None, None, None])
        wins      = u2.get("wins", 0)
        losses    = u2.get("losses", 0)
        rc        = u2.get("recipe_count", 0)
        name      = u2.get("name", "")
        active    = u2.get("active_figure")
        rb_new    = u2.get("rebirth_count", 0) + 1
        # Resetear
        u2["level"]         = 1
        u2["xp"]            = 0
        u2["skill_points"]  = 0
        u2["learn_tree"]    = tree       # árbol preservado
        u2["figures"]       = figures
        u2["team"]          = team
        u2["wins"]          = wins
        u2["losses"]        = losses
        u2["recipe_count"]  = rc
        u2["name"]          = name
        u2["active_figure"] = active
        u2["coins"]         = u2.get("coins", 0) - cost2
        u2["rebirth_count"] = rb_new
        save_db(db2)
        ok_embed = discord.Embed(
            title=f"🔄 ¡Rebirth #{rb_new} completado!",
            description=(
                f"Has reiniciado al nivel 1.\n"
                f"Tu árbol de aprendizaje sigue intacto — ¡sigue creciendo!\n"
                f"💰 Saldo restante: **{u2['coins']:,}🪙**"
            ),
            color=0xe74c3c
        )
        await inter.response.edit_message(embed=ok_embed, view=None)

    async def cancel_cb(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
            return
        await inter.response.edit_message(content="❌ Rebirth cancelado.", embed=None, view=None)

    confirm_btn.callback = confirm_cb
    cancel_btn.callback  = cancel_cb
    view.add_item(confirm_btn)
    view.add_item(cancel_btn)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ============================================================
#  /combine — Fusionar figuras del mismo tipo
# ============================================================
# Por cada 10 fusiones de la misma figura se mejora una habilidad (máx 3 mejoras = 30 fusiones)
COMBINE_COST      = 200   # monedas por fusión
COMBINE_BATCH     = 10    # fusiones para mejorar una habilidad
COMBINE_MAX_TIERS = 3     # máximo de mejoras (3 habilidades)

# Cuánto sube cada stat de cada habilidad mejorada (daño/curación/etc)
SKILL_UPGRADE_BONUS = 15  # +15 de poder por tier

@bot.tree.command(name="combine", description="Fusiona 10 copias de una figura para mejorar sus habilidades")
async def combine_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    # Contar copias por tipo de figura
    fig_counts: dict[str, int] = {}
    for fd in user.get("figures", []):
        k = fd.get("key")
        if k:
            fig_counts[k] = fig_counts.get(k, 0) + 1

    # Sólo figuras con al menos 10 copias y que aún puedan mejorar
    combine_upgrades = user.setdefault("combine_upgrades", {})
    eligible = {
        k: cnt for k, cnt in fig_counts.items()
        if cnt >= COMBINE_BATCH and combine_upgrades.get(k, 0) < COMBINE_MAX_TIERS
    }

    if not eligible:
        await interaction.response.send_message(
            "❌ Necesitas al menos **10 copias** de una figura que aún pueda mejorar (máx 3 mejoras por figura).",
            ephemeral=True
        )
        return

    # Mostrar opciones
    embed = discord.Embed(
        title="🔀 Combinar Figuras",
        description=(
            f"Fusionar **10 copias** de una figura mejora su siguiente habilidad.\n"
            f"Coste: **{COMBINE_COST}🪙** · Máximo **{COMBINE_MAX_TIERS}** mejoras por figura.\n"
        ),
        color=0x9b59b6
    )

    for k, cnt in list(eligible.items())[:10]:
        fig      = FIGURES.get(k, {})
        tier     = combine_upgrades.get(k, 0)
        skills   = FIGURE_SKILLS.get(k, [])
        # Para OG GAMER 64 solo contar habilidades de Fase 1
        if k == "og_gamer64":
            skills = [sk for sk in skills if sk.get("phase", 1) == 1]
        next_skill = skills[tier]["name"] if tier < len(skills) else "—"
        embed.add_field(
            name=f"{fig.get('emoji','')} {fig.get('name', k)} ×{cnt}",
            value=f"Mejora {tier+1}/3 → **{next_skill}** (+{SKILL_UPGRADE_BONUS} poder)\nNecesitas: 10 copias · Tienes: {cnt}",
            inline=False
        )

    view = discord.ui.View(timeout=120)
    uid  = interaction.user.id

    for k in list(eligible.keys())[:5]:  # máx 5 botones
        fig = FIGURES.get(k, {})

        def make_combine_cb(fig_key=k):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                db2   = load_db()
                u2    = get_user(db2, inter.user.id)
                if not u2:
                    await inter.response.send_message("❌ Error de perfil.", ephemeral=True)
                    return

                # Re-verificar
                cnt2  = sum(1 for f in u2.get("figures", []) if f.get("key") == fig_key)
                cu2   = u2.setdefault("combine_upgrades", {})
                tier2 = cu2.get(fig_key, 0)

                if cnt2 < COMBINE_BATCH:
                    await inter.response.send_message(f"❌ Ya no tienes suficientes copias ({cnt2}/10).", ephemeral=True)
                    return
                if tier2 >= COMBINE_MAX_TIERS:
                    await inter.response.send_message("❌ Esta figura ya alcanzó el máximo de mejoras.", ephemeral=True)
                    return
                if u2.get("coins", 0) < COMBINE_COST:
                    await inter.response.send_message(f"❌ No tienes suficiente oro. Necesitas {COMBINE_COST}🪙.", ephemeral=True)
                    return

                # Cobrar y eliminar 10 copias (excepto la primera del equipo)
                u2["coins"] -= COMBINE_COST
                team_indices = u2.get("team", [])
                team_fig_keys = [u2["figures"][i]["key"] if i is not None and i < len(u2["figures"]) else None for i in team_indices]
                removed = 0
                new_figures = []
                kept_one = False
                for fd in u2["figures"]:
                    if fd.get("key") == fig_key and removed < COMBINE_BATCH:
                        if not kept_one:
                            new_figures.append(fd)
                            kept_one = True
                        else:
                            removed += 1
                    else:
                        new_figures.append(fd)
                u2["figures"] = new_figures

                # Reasignar índices del equipo (pueden haber cambiado)
                new_team = []
                for ti in team_indices:
                    if ti is None:
                        new_team.append(None)
                    else:
                        # Buscar el índice nuevo de esa clave
                        key_at = None
                        for ni, nf in enumerate(u2["figures"]):
                            if nf.get("key") == (u2["figures"][ti]["key"] if ti < len(u2["figures"]) else None):
                                key_at = ni
                                break
                        new_team.append(key_at)
                u2["team"] = new_team

                # Aplicar mejora
                cu2[fig_key] = tier2 + 1
                new_tier = tier2 + 1

                # Guardar el bonus de la habilidad mejorada
                skill_upgrades = u2.setdefault("skill_upgrades", {})
                skill_upgrades.setdefault(fig_key, {})[tier2] = SKILL_UPGRADE_BONUS

                save_db(db2)

                fig2      = FIGURES.get(fig_key, {})
                skills2   = FIGURE_SKILLS.get(fig_key, [])
                if fig_key == "og_gamer64":
                    skills2 = [sk for sk in skills2 if sk.get("phase", 1) == 1]
                up_skill  = skills2[tier2]["name"] if tier2 < len(skills2) else "???"

                ok_embed = discord.Embed(
                    title=f"✅ ¡{fig2.get('emoji','')} {fig2.get('name', fig_key)} mejorada!",
                    description=(
                        f"10 copias fusionadas.\n"
                        f"🔺 **{up_skill}** +{SKILL_UPGRADE_BONUS} de poder\n"
                        f"Mejora **{new_tier}/{COMBINE_MAX_TIERS}** aplicada."
                        + (f"\n⛔ Combinación bloqueada para esta figura." if new_tier >= COMBINE_MAX_TIERS else "")
                    ),
                    color=0x9b59b6
                )
                await inter.response.edit_message(embed=ok_embed, view=None)
            return cb

        btn = discord.ui.Button(
            label=f"{fig.get('emoji','')} {fig.get('name', k)}",
            style=discord.ButtonStyle.primary,
            custom_id=f"combine_{k}"
        )
        btn.callback = make_combine_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================================
#  SISTEMA DE 6 TIENDAS CON RAREZA
# ============================================================

# Pool de figuras por rareza (excluye secretas y price=0)
def _shop_pool(rarities: list[str]) -> list[str]:
    return [k for k, v in FIGURES.items()
            if v.get("rarity","").lower() in rarities
            and v.get("price", 0) > 0
            and k not in SECRET_FIGURES
            and k != "roblox_boss"]

@bot.tree.command(name="learn", description="Gasta Skill Points para mejorar tu árbol de habilidades")
async def learn_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    uid = interaction.user.id

    def build_learn_embed(user_data):
        sp   = user_data.get("skill_points", 0)
        tree = user_data.get("learn_tree", {})
        embed = discord.Embed(
            title="📚 Árbol de Aprendizaje",
            description=f"✨ **{sp} Skill Points** disponibles\nElige un nodo para invertir un SP.",
            color=0x9b59b6
        )
        ramas = {}
        for nid, node in LEARN_TREE.items():
            ramas.setdefault(node["rama"], []).append((nid, node))
        for rama, nodes in ramas.items():
            lines = []
            for nid, node in nodes:
                cur = tree.get(nid, 0)
                maxl = node["max_level"]
                req  = node.get("requires")
                req_met = (req is None) or (tree.get(req, 0) >= LEARN_TREE[req]["max_level"])
                bars = "█" * cur + "░" * (maxl - cur)
                lock = "🔒 " if not req_met else ("✅ " if cur >= maxl else "")
                lines.append(f"{lock}**{node['name']}** [{bars}] {cur}/{maxl}\n_{node['desc']}_  *({node['cost']} SP/nv)*")
            embed.add_field(name=rama, value="\n\n".join(lines), inline=False)
        return embed

    def build_learn_view(user_data):
        sp   = user_data.get("skill_points", 0)
        tree = user_data.get("learn_tree", {})
        view = discord.ui.View(timeout=120)
        for nid, node in LEARN_TREE.items():
            cur  = tree.get(nid, 0)
            req  = node.get("requires")
            req_met = (req is None) or (tree.get(req, 0) >= LEARN_TREE[req]["max_level"])
            maxed   = cur >= node["max_level"]
            can_buy = req_met and not maxed and sp >= node["cost"]
            btn = discord.ui.Button(
                label=f"{node['name'].split(' ')[0]} Nv{cur+1}" if not maxed else f"✅ {node['name'].split(' ')[0]}",
                style=discord.ButtonStyle.success if can_buy else discord.ButtonStyle.secondary,
                disabled=not can_buy,
                custom_id=f"learn_{nid}",
                row=list(LEARN_TREE.keys()).index(nid) // 5
            )
            def make_cb(node_id=nid, node_data=node):
                async def cb(inter: discord.Interaction):
                    if inter.user.id != uid:
                        await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                        return
                    db2   = load_db()
                    u2    = get_user(db2, inter.user.id)
                    sp2   = u2.get("skill_points", 0)
                    tree2 = u2.setdefault("learn_tree", {})
                    cur2  = tree2.get(node_id, 0)
                    req2  = node_data.get("requires")
                    req_met2 = (req2 is None) or (tree2.get(req2, 0) >= LEARN_TREE[req2]["max_level"])
                    if not req_met2:
                        await inter.response.send_message("❌ Desbloquea el nodo anterior primero.", ephemeral=True)
                        return
                    if cur2 >= node_data["max_level"]:
                        await inter.response.send_message("❌ Este nodo ya está al máximo.", ephemeral=True)
                        return
                    if sp2 < node_data["cost"]:
                        await inter.response.send_message(f"❌ Necesitas **{node_data['cost']} SP** y tienes **{sp2}**.", ephemeral=True)
                        return
                    u2["skill_points"] = sp2 - node_data["cost"]
                    tree2[node_id] = cur2 + 1
                    save_db(db2)
                    await inter.response.edit_message(embed=build_learn_embed(u2), view=build_learn_view(u2))
                return cb
            btn.callback = make_cb()
            view.add_item(btn)
        return view

    await interaction.response.send_message(
        embed=build_learn_embed(user),
        view=build_learn_view(user),
        ephemeral=True
    )

# ============================================================
#  /rebirth — Reinicio con árbol preservado
@bot.tree.command(name="logros", description="Ver tus logros conseguidos y los que faltan")
async def logros_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    uid    = interaction.user.id
    earned = set(user.get("achievements", []))
    total  = len(ACHIEVEMENTS)
    done   = len(earned)

    # Construir lista completa: conseguidos primero, luego pendientes
    items = []
    for aid, ach in ACHIEVEMENTS.items():
        if aid in earned:
            items.append(("done", aid, ach))
    for aid, ach in ACHIEVEMENTS.items():
        if aid not in earned:
            items.append(("pending", aid, ach))

    PAGE_SIZE = 8  # fields por página (bien dentro del límite de 25)
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)

    def build_logros_embed(page: int) -> discord.Embed:
        embed = discord.Embed(
            title=f"🏅 Logros — {user['name']}",
            description=f"**{done}/{total}** conseguidos  |  Página {page+1}/{total_pages}",
            color=0xf1c40f
        )
        start = page * PAGE_SIZE
        for status, aid, ach in items[start:start + PAGE_SIZE]:
            if status == "done":
                embed.add_field(name=f"✅ {ach['name']}", value=ach["desc"], inline=True)
            else:
                if ach.get("secret"):
                    embed.add_field(name="🔒 ???", value="*Logro secreto*", inline=True)
                else:
                    embed.add_field(name=f"⬜ {ach['name']}", value=ach["desc"], inline=True)
        embed.set_footer(text="✅ Conseguido  ·  ⬜ Pendiente  ·  🔒 Secreto")
        return embed

    def build_logros_view(page: int) -> discord.ui.View:
        view = discord.ui.View(timeout=120)
        prev_btn = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary, disabled=page == 0)
        next_btn = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary, disabled=page >= total_pages - 1)

        def make_nav(new_page):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                await inter.response.edit_message(
                    embed=build_logros_embed(new_page),
                    view=build_logros_view(new_page)
                )
            return cb

        prev_btn.callback = make_nav(page - 1)
        next_btn.callback = make_nav(page + 1)
        view.add_item(prev_btn)
        view.add_item(next_btn)
        return view

    await interaction.response.send_message(
        embed=build_logros_embed(0),
        view=build_logros_view(0),
        ephemeral=True
    )

