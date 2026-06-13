"""
economy.py — Ingredientes, recetas, learn tree, logros, combine, rebirth, nivel de figuras.
"""
import random

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


# ============================================================
#  FIGURE LEVEL MAX
# ============================================================
FIGURE_LEVEL_MAX = 30

def check_figure_levelup(fig_data: dict, interaction_hook=None) -> bool:
    """Sube de nivel la figura si tiene suficiente XP. Devuelve True si subió."""
    lvl = fig_data.get("level", 1)
    xp  = fig_data.get("xp", 0)
    if lvl >= FIGURE_LEVEL_MAX:
        return False
    needed = 100 * lvl
    if xp >= needed:
        fig_data["level"] = lvl + 1
        fig_data["xp"]    = xp - needed
        return True
    return False

# ============================================================
#  PLAYER LEVEL MAX + LEVELUP
# ============================================================
PLAYER_LEVEL_MAX = 100

def _check_player_levelup(user_data: dict) -> list:
    """Sube el nivel del jugador. Por cada nivel nuevo da 1 skill point."""
    new_levels = []
    while user_data.get("level", 1) < PLAYER_LEVEL_MAX:
        needed = 100 * user_data.get("level", 1)
        if user_data.get("xp", 0) >= needed:
            user_data["xp"]          = user_data["xp"] - needed
            user_data["level"]       = user_data.get("level", 1) + 1
            user_data["skill_points"]= user_data.get("skill_points", 0) + 1
            new_levels.append(user_data["level"])
        else:
            break
    return new_levels

# ============================================================
#  LEARN TREE
# ============================================================
LEARN_TREE = {
    "coin_boost_1":    {"name": "💰 Monedas+",       "desc": "+10% monedas por victoria.",          "cost": 1, "effect": "coin_multiplier",   "value": 0.10, "requires": []},
    "coin_boost_2":    {"name": "💰 Monedas++",      "desc": "+20% monedas por victoria.",          "cost": 2, "effect": "coin_multiplier",   "value": 0.20, "requires": ["coin_boost_1"]},
    "xp_boost_1":     {"name": "⬆️ XP+",            "desc": "+15% XP por batalla.",                "cost": 1, "effect": "xp_multiplier",     "value": 0.15, "requires": []},
    "xp_boost_2":     {"name": "⬆️ XP++",           "desc": "+30% XP por batalla.",                "cost": 2, "effect": "xp_multiplier",     "value": 0.30, "requires": ["xp_boost_1"]},
    "hp_passive":     {"name": "❤️ Vida Extra",      "desc": "+20 HP base a todas las figuras.",    "cost": 2, "effect": "hp_bonus",          "value": 20,   "requires": []},
    "atk_passive":    {"name": "⚔️ Ataque Extra",   "desc": "+5 ATK base a todas las figuras.",    "cost": 2, "effect": "atk_bonus",         "value": 5,    "requires": []},
    "def_passive":    {"name": "🛡️ Defensa Extra",  "desc": "+5 DEF base a todas las figuras.",    "cost": 2, "effect": "def_bonus",         "value": 5,    "requires": []},
    "energy_start":   {"name": "⚡ Energía Inicial","desc": "Empieza las batallas con +20 energía.","cost": 2, "effect": "energy_start",      "value": 20,   "requires": []},
    "ingredient_luck":{"name": "🧺 Suerte Ing.",    "desc": "+15% prob. de ingrediente en batallas.","cost":2, "effect": "ingredient_chance",  "value": 15,   "requires": []},
    "shop_discount":  {"name": "🛒 Descuento",       "desc": "-10% precios en tiendas.",            "cost": 3, "effect": "shop_discount",     "value": 0.10, "requires": ["coin_boost_1"]},
    "rebirth_bonus":  {"name": "🔄 Rebirth+",        "desc": "+50 monedas extra por Rebirth.",      "cost": 3, "effect": "rebirth_coins",     "value": 50,   "requires": ["coin_boost_2"]},
}

def get_learn_effect(user_data: dict, effect_key: str) -> int:
    """Devuelve el valor total de un efecto del árbol para el usuario."""
    tree = user_data.get("learn_tree", {})
    total = 0
    for node_id, node in LEARN_TREE.items():
        if tree.get(node_id) and node.get("effect") == effect_key:
            total += node.get("value", 0)
    return total

# ============================================================
#  QUESTS
# ============================================================
QUESTS = {
    "documentos_jane": {
        "name": "📄 Documentos de Jane",
        "desc": "Jane Doe escondió sus documentos. Consigue 6 ganando batallas para desbloquearla.",
        "goal": 6,
        "progress_key": "docs_collected",
        "reward_key": "jane_unlocked",
        "reward_desc": "🔓 ¡Jane Doe desbloqueada en la tienda!",
        "drop_chance": 60,
    },
}

def is_quest_unlocked(user: dict, quest_id: str) -> bool:
    return user.get("quests_completed", {}).get(quest_id, False)

def get_quest_progress(user: dict, quest_id: str) -> int:
    return user.get("quest_progress", {}).get(quest_id, 0)

async def check_quest_drops(user: dict, quest_id: str, channel, db=None):
    from database import save_db as _save_db
    quest = QUESTS.get(quest_id)
    if not quest or is_quest_unlocked(user, quest_id):
        return
    if quest_id not in user.get("active_quests", []):
        return
    if random.randint(1, 100) <= quest["drop_chance"]:
        user.setdefault("quest_progress", {})[quest_id] = user["quest_progress"].get(quest_id, 0) + 1
        prog = user["quest_progress"][quest_id]
        if db: _save_db(db)
        await channel.send(f"📄 **¡Documento encontrado!** ({prog}/{quest['goal']}) — **{quest['name']}**")
        if prog >= quest["goal"]:
            user.setdefault("quests_completed", {})[quest_id] = True
            if quest_id == "documentos_jane":
                user["jane_unlocked"] = True
            if db: _save_db(db)
            await channel.send(f"🎉 **¡MISIÓN COMPLETADA!** {quest['name']}\n{quest['reward_desc']}")

# ============================================================
#  LOVE SYSTEM (Sans)
# ============================================================

def _register_kill_for_love(owner_id, battle=None):
    if not owner_id:
        return
    try:
        from database import load_db as _load_db, save_db as _save_db, get_user as _get_user
        db   = _load_db()
        user = _get_user(db, owner_id)
        if user:
            user["total_kills"] = user.get("total_kills", 0) + 1
            _save_db(db)
    except Exception:
        pass

def _get_love_kills(battle, attacker) -> int:
    try:
        from database import load_db as _load_db, get_user as _get_user
        db   = _load_db()
        user = _get_user(db, getattr(battle, "p1_id", None))
        if user:
            return user.get("total_kills", 0)
    except Exception:
        pass
    return 0

# ============================================================
#  ACHIEVEMENTS
# ============================================================
ACHIEVEMENTS = {
    "first_figure":    {"name": "🎭 El principio...",          "desc": "Compra tu primera figura.",                        "secret": False},
    "first_win":       {"name": "🏆 Primera Victoria",         "desc": "Gana tu primera batalla.",                         "secret": False},
    "wins_10":         {"name": "⚔️ Guerrero",                 "desc": "Gana 10 batallas.",                                "secret": False},
    "wins_100":        {"name": "💀 Leyenda del PvP",          "desc": "Gana 100 batallas.",                               "secret": False},
    "first_level":     {"name": "⬆️ Subí de nivel!",           "desc": "Sube de nivel por primera vez.",                   "secret": False},
    "fig_first_level": {"name": "⬆️ Subamos las cosas!",       "desc": "Sube de nivel una figura.",                        "secret": False},
    "first_recipe":    {"name": "🧑‍🍳 Chef Novato",             "desc": "Descubre tu primera receta.",                      "secret": False},
    "recipes_10":      {"name": "🧑‍🍳 Chef Profesional",        "desc": "Descubre 10 recetas.",                             "secret": False},
    "first_explore":   {"name": "🗺️ Explorador Nato",          "desc": "Completa tu primera exploración.",                  "secret": False},
    "reach_level_10":  {"name": "🌟 Nivel 10",                 "desc": "Llega al nivel 10.",                               "secret": False},
    "reach_level_30":  {"name": "🌟 Nivel 30",                 "desc": "Llega al nivel 30.",                               "secret": False},
    "reach_level_50":  {"name": "🌟 Nivel 50",                 "desc": "Llega al nivel 50.",                               "secret": False},
    "reach_level_100": {"name": "👑 Nivel 100",                "desc": "Alcanza el nivel máximo.",                         "secret": False},
    "first_rebirth":   {"name": "🔄 He vuelto...",             "desc": "Haz tu primer Rebirth.",                           "secret": False},
    "first_combine":   {"name": "🔀 Experimento Loco!",        "desc": "Combina figuras por primera vez.",                  "secret": False},
    "first_learn":     {"name": "📚 Primer Conocimiento",      "desc": "Aprende tu primer nodo del árbol.",                "secret": False},
    "mythic_owned":    {"name": "🔱 Coleccionista Mítico",     "desc": "Consigue una figura mítica.",                      "secret": False},
    "secret_store":    {"name": "🔒 El Código Correcto",       "desc": "Desbloquea la tienda secreta.",                    "secret": True},
    "beat_nino":       {"name": "👦 Niños al recreo",          "desc": "Derrota al Niño Random.",                          "secret": False},
    "beat_paper":      {"name": "📄 Tijeras vence a Papel!",   "desc": "Derrota a Paper Mario.",                           "secret": False},
    "beat_steve":      {"name": "⛏️ Minero Retirado",          "desc": "Derrota a Steve.",                                 "secret": False},
    "beat_impostor_3": {"name": "🔪 VICTORY! 👑",             "desc": "Vence al Impostor con 3 figuras.",                 "secret": False},
    "beat_impostor_7": {"name": "😕 Aburrido...",              "desc": "Vence al Impostor con 7 figuras.",                 "secret": True},
    "beat_antifas":    {"name": "👑 EL NUEVO CAMPEON!",        "desc": "Derrota al Antifas Antifasado.",                   "secret": False},
    "daily_streak_7":  {"name": "📅 Racha de 7 días",          "desc": "Mantén racha diaria 7 días.",                      "secret": False},
    "coins_10000":     {"name": "💰 Rico Rico",                "desc": "Acumula 10,000 monedas.",                          "secret": False},
    "fig_max_level":   {"name": "⬆️ Al Límite",               "desc": "Sube una figura al nivel máximo (30).",            "secret": False},
    "kirby_no_mas":          {"name": "🚫 NO MAS KIRBY!",                   "desc": "... Nunca debiste intentar absorber eso...", "secret": True},
    "kirby_no_entendiste":   {"name": "🚫 NO ME ENTENDISTE!!?? NO MAS!!", "desc": "NO... SOLO.... NO!!",                    "secret": True},
}

def grant_achievement(user_data: dict, achievement_id: str) -> bool:
    if achievement_id not in ACHIEVEMENTS:
        return False
    earned = user_data.setdefault("achievements", [])
    if achievement_id in earned:
        return False
    earned.append(achievement_id)
    return True

def check_achievements(user_data: dict, context: dict) -> list:
    from figures import FIGURES as _FIGURES
    new    = []
    w      = user_data.get("wins", 0)
    lvl    = user_data.get("level", 1)
    rc     = user_data.get("recipe_count", 0)
    figs   = user_data.get("figures", [])
    coins  = user_data.get("coins", 0)
    action = context.get("action", "")

    checks = {
        "first_figure":    len(figs) >= 1,
        "first_win":       w >= 1,
        "wins_10":         w >= 10,
        "wins_100":        w >= 100,
        "first_level":     lvl >= 2,
        "reach_level_10":  lvl >= 10,
        "reach_level_30":  lvl >= 30,
        "reach_level_50":  lvl >= 50,
        "reach_level_100": lvl >= 100,
        "first_recipe":    rc >= 1,
        "recipes_10":      rc >= 10,
        "first_rebirth":   user_data.get("rebirth_count", 0) >= 1,
        "coins_10000":     coins >= 10000,
        "mythic_owned":    any(_FIGURES.get(f["key"], {}).get("rarity", "").lower() in ("mítico",) for f in figs),
        "fig_max_level":   any(f.get("level", 1) >= FIGURE_LEVEL_MAX for f in figs),
        "fig_first_level": any(f.get("level", 1) >= 2 for f in figs),
    }
    if action == "explore":      checks["first_explore"] = True
    if action == "combine":      checks["first_combine"] = True
    if action == "learn":        checks["first_learn"]   = True
    if action == "secret_store": checks["secret_store"]  = True
    if action == "daily_7":      checks["daily_streak_7"]= True

    boss = context.get("boss_id", "")
    ts   = context.get("team_size", 3)
    if boss == "nino_random":   checks["beat_nino"]       = True
    if boss == "paper_mario":   checks["beat_paper"]      = True
    if boss == "steve":         checks["beat_steve"]      = True
    if boss == "jefe":          checks["beat_antifas"]    = True
    if boss == "impostor_negro":
        if ts <= 3: checks["beat_impostor_3"] = True
        if ts >= 7: checks["beat_impostor_7"] = True

    for aid, cond in checks.items():
        if cond and grant_achievement(user_data, aid):
            new.append(aid)
    return new
