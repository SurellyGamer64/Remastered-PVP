"""
shops.py — Sistema de 6 tiendas con rareza, probabilidades actualizadas y sobres del Acertijo.

Probabilidades de disponibilidad de figuras por tienda:
  🛒 Super Mercado     60–80%
  🎮 La Tienda Gamer   76–90%
  🔬 Lab de Tails      75–89%
  🍺 El Bar Random     50–80%
  🍄 Tienda Toad       40–50%
  ❓ El Acertijo       100% (solo sobres — cualquier figura puede salir)
"""

import random
import time as _time

# ============================================================
#  TIENDAS — definición, pesos de rareza y slots
# ============================================================

SHOPS = {
    "gamer": {
        "name": "🎮 La Tienda Gamer",
        "desc": "La tienda clásica. Figuras de todas las rarezas, buena variedad.",
        "weights": {"común": 35, "raro": 40, "épico": 20, "legendario": 5, "mítico": 0},
        "slots": 5,
    },
    "bar": {
        "name": "🍺 El Bar Random",
        "desc": "Todo es un misterio. Cualquier figura puede aparecer aquí.",
        "weights": {"común": 30, "raro": 35, "épico": 25, "legendario": 10, "mítico": 0},
        "slots": 5,
        "refresh_on_visit": True,
    },
    "mercado": {
        "name": "🛒 Super Mercado",
        "desc": "Precios accesibles, figuras básicas. Sin legendarios ni míticos.",
        "weights": {"común": 40, "raro": 45, "épico": 15, "legendario": 0, "mítico": 0},
        "slots": 6,
        "discount": 10,
    },
    "toad": {
        "name": "🍄 Tienda Toad",
        "desc": "Stock exclusivo de figuras épicas y legendarias. ¡Raras de encontrar!",
        "weights": {"común": 0, "raro": 15, "épico": 55, "legendario": 30, "mítico": 0},
        "slots": 4,
    },
    "tails": {
        "name": "🔬 Laboratorio de Tails",
        "desc": "Figuras técnicas y poco comunes. Sin comunes, mayor calidad.",
        "weights": {"común": 0, "raro": 35, "épico": 45, "legendario": 20, "mítico": 0},
        "slots": 4,
    },
    "acertijo": {
        "name": "❓ El Acertijo de las Compras",
        "desc": (
            "¡Aquí no sabes lo que te llevas! Compra sobres con rarezas distintas.\n"
            "Cada sobre contiene **1 figura al azar** — puede tocarte cualquier figura del juego."
        ),
        "weights": {},       # sin stock fijo — solo sobres
        "has_packs": True,
        "slots": 0,
    },
}

# Probabilidad de que aparezca una figura mítica (% independiente, encima de los pesos)
SHOP_MYTHIC_CHANCE = {
    "gamer": 0, "bar": 0, "mercado": 0, "toad": 0,
    "tails": 0, "acertijo": 0,   # el acertijo usa sobres, no pool directo
}

# ============================================================
#  SOBRES DEL ACERTIJO
#  Cada sobre tiene pesos de rareza internos; cualquier figura
#  comprable puede salir (incluidas míticas según rareza del sobre).
# ============================================================

MYSTERY_PACKS = {
    "basic": {
        "name": "📦 Sobre Básico",
        "price": 300,
        "desc": "1 figura común o rara al azar.",
        "rarity_weights": {"común": 60, "raro": 40},
        "ing_chance": 0,
        "recipe_chance": 0,
    },
    "premium": {
        "name": "📫 Sobre Premium",
        "price": 800,
        "desc": "1 figura rara o épica al azar + 15% de conseguir ingrediente.",
        "rarity_weights": {"raro": 55, "épico": 45},
        "ing_chance": 15,
        "recipe_chance": 0,
    },
    "legend": {
        "name": "🌟 Sobre Legendario",
        "price": 2000,
        "desc": "1 figura épica o legendaria + 25% ingrediente + 10% receta.",
        "rarity_weights": {"épico": 60, "legendario": 40},
        "ing_chance": 25,
        "recipe_chance": 10,
    },
    "mythic": {
        "name": "💀 Sobre Mítico",
        "price": 5000,
        "desc": "1 figura legendaria o MÍTICA + 50% ingrediente + 20% receta.",
        "rarity_weights": {"legendario": 70, "mítico": 30},
        "ing_chance": 50,
        "recipe_chance": 20,
    },
}

# ============================================================
#  DISPONIBILIDAD DE TIENDAS (porcentaje del catálogo disponible)
#  Actualizado según las specs del proyecto:
#    🛒 Super Mercado     60–80%
#    🎮 La Tienda Gamer   76–90%
#    🔬 Lab de Tails      75–89%
#    🍺 El Bar Random     50–80%
#    🍄 Tienda Toad       40–50%
#    ❓ El Acertijo       100% (siempre abierto — solo vende sobres)
# ============================================================

SHOP_AVAILABILITY = {
    "mercado":  (0.60, 0.80),
    "gamer":    (0.76, 0.90),
    "tails":    (0.75, 0.89),
    "bar":      (0.50, 0.80),
    "toad":     (0.40, 0.50),
    "acertijo": (1.0,  1.0),
}

SHOP_RESET_INTERVAL = 3 * 3600   # 3 horas en segundos

_shop_state = {
    "last_reset": 0.0,
    "available": {},
}


# ============================================================
#  HELPERS INTERNOS
# ============================================================

def _get_all_buyable_figures(FIGURES, SECRET_FIGURES) -> list:
    """Devuelve todas las claves de figuras comprables (price > 0, no exclusivas de jefe)."""
    excluded = {"roblox_boss", "santa_vaca", "lobster", "janedoe"}
    excluded.update(k for k in FIGURES if k.startswith("boss_") or k.startswith("antifas"))
    excluded.update(SECRET_FIGURES)
    return [k for k, v in FIGURES.items()
            if v.get("price", 0) > 0 and k not in excluded]


def _reset_shops(FIGURES, SECRET_FIGURES):
    """Genera un nuevo estado aleatorio para todas las tiendas."""
    all_figs = _get_all_buyable_figures(FIGURES, SECRET_FIGURES)
    for shop_id, (min_pct, max_pct) in SHOP_AVAILABILITY.items():
        pct   = random.uniform(min_pct, max_pct)
        count = max(3, int(len(all_figs) * pct))
        available = set(random.sample(all_figs, min(count, len(all_figs))))
        _shop_state["available"][shop_id] = available
    _shop_state["last_reset"] = _time.time()
    print("🔄 Tiendas reseteadas — próximo reset en 3 horas")


def check_shop_reset(FIGURES, SECRET_FIGURES):
    """Resetea las tiendas si han pasado 3 horas."""
    if _time.time() - _shop_state["last_reset"] >= SHOP_RESET_INTERVAL:
        _reset_shops(FIGURES, SECRET_FIGURES)


def time_until_reset() -> str:
    """Devuelve string con el tiempo restante hasta el próximo reset."""
    remaining = max(0, SHOP_RESET_INTERVAL - (_time.time() - _shop_state["last_reset"]))
    h = int(remaining // 3600)
    m = int((remaining % 3600) // 60)
    s = int(remaining % 60)
    if h > 0:  return f"{h}h {m}m"
    if m > 0:  return f"{m}m {s}s"
    return f"{s}s"


def _pick_shop_figures(shop_id: str, count: int, FIGURES=None, SECRET_FIGURES=None) -> list:
    """
    Elige `count` figuras para mostrar en una tienda, respetando el STOCK ROTATIVO
    generado por _reset_shops() cada 3 horas. Solo se eligen figuras que estén
    dentro de _shop_state["available"][shop_id] Y que cumplan los pesos de rareza
    de la tienda.

    Si _shop_state no tiene stock todavía (primer arranque), genera uno temporal.
    """
    shop   = SHOPS[shop_id]
    w      = shop["weights"]
    mythic_chance = SHOP_MYTHIC_CHANCE.get(shop_id, 0)

    # Asegurar que existe stock rotativo. Si no, y tenemos FIGURES, generarlo.
    available_pool = _shop_state["available"].get(shop_id)
    if not available_pool and FIGURES is not None:
        _reset_shops(FIGURES, SECRET_FIGURES or [])
        available_pool = _shop_state["available"].get(shop_id)

    if FIGURES is None:
        # Fallback de emergencia: importar perezosamente para no romper si no se pasó
        from figures import FIGURES as _F, SECRET_FIGURES as _SF
        FIGURES = _F
        SECRET_FIGURES = SECRET_FIGURES or _SF
        if not available_pool:
            _reset_shops(FIGURES, SECRET_FIGURES)
            available_pool = _shop_state["available"].get(shop_id)

    SECRET_FIGURES = SECRET_FIGURES or []
    available_pool = available_pool or set()

    rarity_aliases = {
        "común":      ["común"],
        "raro":       ["raro"],
        "épico":      ["épico", "epico"],
        "legendario": ["legendario", "Legendario"],
        "mítico":     ["mítico", "Mítico"],
    }

    pool = []
    for rarity, weight in w.items():
        if weight <= 0:
            continue
        aliases = rarity_aliases.get(rarity, [rarity])
        figs = [k for k, v in FIGURES.items()
                if v.get("rarity", "").lower() in [a.lower() for a in aliases]
                and v.get("price", 0) > 0
                and k not in SECRET_FIGURES
                and k != "roblox_boss"
                and k in available_pool]      # ← respeta el stock rotativo
        pool.extend(figs * weight)

    # Si el stock rotativo dejó el pool vacío para esta tienda (mala suerte del rango
    # de disponibilidad), usamos todas las figuras válidas de la tienda como fallback
    # para que la tienda nunca se quede sin nada que vender.
    if not pool:
        for rarity, weight in w.items():
            if weight <= 0:
                continue
            aliases = rarity_aliases.get(rarity, [rarity])
            figs = [k for k, v in FIGURES.items()
                    if v.get("rarity", "").lower() in [a.lower() for a in aliases]
                    and v.get("price", 0) > 0
                    and k not in SECRET_FIGURES
                    and k != "roblox_boss"]
            pool.extend(figs * weight)

    if not pool:
        return []

    chosen, seen, attempts = [], set(), 0
    while len(chosen) < count and attempts < 300:
        attempts += 1
        if mythic_chance > 0 and random.randint(1, 100) <= mythic_chance:
            mythic_pool = [k for k, v in FIGURES.items()
                           if v.get("rarity", "").lower() == "mítico"
                           and k not in SECRET_FIGURES and v.get("price", 0) > 0
                           and k in available_pool]
            if mythic_pool:
                pick = random.choice(mythic_pool)
                if pick not in seen:
                    chosen.append(pick)
                    seen.add(pick)
                continue
        pick = random.choice(pool)
        if pick not in seen:
            chosen.append(pick)
            seen.add(pick)
    return chosen


def open_mystery_pack(pack_id: str, user_data: dict, FIGURES, SECRET_FIGURES,
                      INGREDIENTS, RECIPES, random_module) -> dict:
    """
    Abre un sobre del Acertijo.
    Devuelve {"fig": key, "ingredient": emoji_key|None, "recipe": name|None}.

    La rareza se elige ponderadamente según el pack, luego se filtra cualquier figura
    comprable de esa rareza (¡puede salir cualquier figura del juego!).
    """
    pack = MYSTERY_PACKS[pack_id]
    rarity_weights = pack["rarity_weights"]

    # Normalizar alias de rareza para comparar
    _aliases = {
        "común":      {"común"},
        "raro":       {"raro"},
        "épico":      {"épico", "epico"},
        "legendario": {"legendario", "Legendario"},
        "mítico":     {"mítico", "Mítico"},
    }

    # Elegir rareza según pesos del sobre
    rarity_pool = []
    for rar, wt in rarity_weights.items():
        rarity_pool.extend([rar] * wt)
    chosen_rarity = random_module.choice(rarity_pool)
    valid_aliases = _aliases.get(chosen_rarity, {chosen_rarity})

    # Filtrar figuras de esa rareza (cualquier figura comprable)
    excluded = {"roblox_boss", "santa_vaca", "lobster", "janedoe"}
    excluded.update(k for k in FIGURES if k.startswith("boss_") or k.startswith("antifas"))
    excluded.update(SECRET_FIGURES)

    candidates = [k for k, v in FIGURES.items()
                  if v.get("rarity", "").lower() in {a.lower() for a in valid_aliases}
                  and k not in excluded
                  and v.get("price", 0) > 0]

    # Fallback: cualquier figura comprable si la rareza no tiene candidatos
    if not candidates:
        candidates = [k for k, v in FIGURES.items()
                      if v.get("price", 0) > 0 and k not in excluded]

    fig_key = random_module.choice(candidates)
    user_data.setdefault("figures", []).append({"key": fig_key, "level": 1, "xp": 0})

    # Auto-equipar si hay hueco en el equipo
    team = user_data.get("team", [None, None, None])
    while len(team) < 3:
        team.append(None)
    for i in range(3):
        if team[i] is None:
            team[i] = len(user_data["figures"]) - 1
            break
    user_data["team"] = team

    # Bonus: ingrediente
    ingredient = None
    if pack["ing_chance"] > 0 and random_module.randint(1, 100) <= pack["ing_chance"]:
        non_lobster = [k for k in INGREDIENTS if k != "🦞"]
        ingredient = random_module.choice(non_lobster)
        user_data.setdefault("ingredients", {})[ingredient] = (
            user_data["ingredients"].get(ingredient, 0) + 1
        )

    # Bonus: receta
    recipe_name = None
    if pack["recipe_chance"] > 0 and random_module.randint(1, 100) <= pack["recipe_chance"]:
        owned = user_data.get("recipe_sheets", [])
        available_rec = [i for i in range(len(RECIPES)) if i not in owned]
        if available_rec:
            idx = random_module.choice(available_rec)
            user_data.setdefault("recipe_sheets", []).append(idx)
            recipe_name = RECIPES[idx].get("name") if idx < len(RECIPES) else None

    return {"fig": fig_key, "ingredient": ingredient, "recipe": recipe_name,
            "chosen_rarity": chosen_rarity}


# ============================================================
#  EMBED HELPER — descripción de sobres para el /tienda
# ============================================================

def build_acertijo_info_text() -> str:
    """Genera el texto de descripción de los sobres para el embed de /tienda."""
    lines = []
    for pid, pack in MYSTERY_PACKS.items():
        rw = pack["rarity_weights"]
        rarity_str = " · ".join(f"{r} {w}%" for r, w in rw.items())
        extras = []
        if pack["ing_chance"] > 0:
            extras.append(f"{pack['ing_chance']}% ingrediente")
        if pack["recipe_chance"] > 0:
            extras.append(f"{pack['recipe_chance']}% receta")
        bonus = f" + {', '.join(extras)}" if extras else ""
        lines.append(f"**{pack['name']}** `{pack['price']:,}🪙` — {rarity_str}{bonus}")
    return "\n".join(lines)


# ============================================================
#  TIENDA DE VARIANTES — stock rotativo cada 3 horas
#
#  Las variantes disponibles en la tienda dependen de:
#    1. La temporada activa (solo variantes desbloqueadas por temporada)
#    2. Su "op_tier" (qué tan fuerte es) — entre más fuerte, más rara su aparición
#
#  op_tier va de 1 (débil) a 5 (rotísimo). La probabilidad de que aparezca
#  en stock es inversamente proporcional a su op_tier.
# ============================================================

# Tabla de "qué tan OP" es cada variante de temporada (1=débil, 5=rotísimo)
SEASONAL_VARIANT_OP_TIER = {
    "halloween":              4,
    "trick_or_treat":         3,
    "christmas":               3,
    "ice_bender":              4,
    "fire_bender":             4,
    "sun_god":                 5,
    "april_fools":             2,
    "toon":                    3,
    "low_effort_high_stats":   5,
}

# Probabilidad base de aparición por tier (más alto = más raro)
OP_TIER_APPEARANCE_CHANCE = {
    1: 70,   # común, casi siempre disponible
    2: 50,
    3: 32,
    4: 18,
    5: 8,    # rotísimo, casi nunca aparece
}

# Precio sugerido por tier
OP_TIER_PRICE = {
    1: 800,
    2: 1500,
    3: 3000,
    4: 6000,
    5: 12000,
}

_variant_shop_state = {
    "last_reset": 0.0,
    "available_seasonal": [],   # claves de SEASONAL_VARIANTS en stock actual
}


def _reset_variant_shop(current_season: str = "none"):
    """
    Genera un nuevo stock de variantes EXCLUSIVAS DE TEMPORADA para la Tienda
    de Variantes. Las variantes de color son predeterminadas por figura y NO
    se venden aquí — cada figura ya viene con su color fijo al comprarla.
    La probabilidad de aparición de cada variante depende de su op_tier
    (más OP = más rara su aparición en stock).
    """
    from variants import SEASON_VARIANT_POOL

    seasonal_pool = SEASON_VARIANT_POOL.get(current_season, [])
    available_seasonal = []
    for vk in seasonal_pool:
        tier   = SEASONAL_VARIANT_OP_TIER.get(vk, 3)
        chance = OP_TIER_APPEARANCE_CHANCE.get(tier, 30)
        if random.randint(1, 100) <= chance:
            available_seasonal.append(vk)

    _variant_shop_state["available_seasonal"] = available_seasonal
    _variant_shop_state["last_reset"]         = _time.time()
    print(f"🎨 Tienda de Variantes reseteada — temporada: {current_season}")


def check_variant_shop_reset(current_season: str = "none"):
    """Resetea la tienda de variantes si pasaron 3 horas."""
    if _time.time() - _variant_shop_state["last_reset"] >= SHOP_RESET_INTERVAL:
        _reset_variant_shop(current_season)


def time_until_variant_reset() -> str:
    remaining = max(0, SHOP_RESET_INTERVAL - (_time.time() - _variant_shop_state["last_reset"]))
    h = int(remaining // 3600)
    m = int((remaining % 3600) // 60)
    s = int(remaining % 60)
    if h > 0: return f"{h}h {m}m"
    if m > 0: return f"{m}m {s}s"
    return f"{s}s"


def get_variant_shop_stock(current_season: str = "none") -> dict:
    """
    Devuelve el stock actual de la Tienda de Variantes:
    { "seasonal": [variant_key, ...] }
    Solo variantes exclusivas de temporada — las de color no se venden.
    Genera stock nuevo si no existe todavía.
    """
    if not _variant_shop_state["available_seasonal"]:
        _reset_variant_shop(current_season)
    return {
        "seasonal": list(_variant_shop_state["available_seasonal"]),
    }


def get_variant_price(variant_key: str) -> int:
    """Calcula el precio de una variante de temporada según su op_tier."""
    tier = SEASONAL_VARIANT_OP_TIER.get(variant_key, 3)
    return OP_TIER_PRICE.get(tier, 2000)
