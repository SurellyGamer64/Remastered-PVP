"""
variants.py — Sistema completo de variantes del Androide PVP.

Incluye:
  - VARIANTS: todas las variantes por figura y sus stats/efectos
  - COLOR_WHEEL: rueda de atributos y quién vence a quién
  - SEASONAL_VARIANTS: variantes de temporada exclusivas
  - apply_variant(): aplica la variante a un fighter dict
  - calc_color_multiplier(): calcula el multiplicador de daño entre dos colores
  - apply_variant_on_attack(): aplica efectos de variante durante un ataque
  - CURRENT_SEASON: temporada activa del servidor
"""

import random

# ============================================================
#  TEMPORADA ACTIVA
#  Cambiar con /seasons → se guarda en db.json ["season"]
# ============================================================
SEASONS = {
    "none":       {"name": "⚔️ Sin temporada",   "emoji": "⚔️",  "color": 0x5865f2},
    "halloween":  {"name": "🎃 Halloween",         "emoji": "🎃",  "color": 0xff6b00},
    "christmas":  {"name": "❄️ Winter/Christmas",  "emoji": "❄️",  "color": 0x57d8ff},
    "summer":     {"name": "☀️ Verano",            "emoji": "☀️",  "color": 0xf1c40f},
    "april_fools":{"name": "🃏 April Fools",       "emoji": "🃏",  "color": 0xeb459e},
}

# ============================================================
#  RUEDA DE COLORES
#
#  Normales: Rojo > Amarillo > Azul > Morado > Verde > Rojo
#  Especiales de temporada: Halloween > Summer > Winter > Halloween
#              April Fools: neutro contra todos
#  Blanco & Negro: neutros entre sí... excepto entre ellos (x2 ambos)
# ============================================================

COLOR_BEATS = {
    "rojo":    "amarillo",
    "amarillo":"azul",
    "azul":    "morado",
    "morado":  "verde",
    "verde":   "rojo",
    # Temporada
    "halloween": "summer",
    "summer":    "winter",
    "winter":    "halloween",
    # April fools no vence a nadie
    # Negro y Blanco: neutros salvo entre sí
}

BONUS_MULTIPLIER   = 1.25   # color ganador → +25% daño
PENALTY_MULTIPLIER = 0.80   # color perdedor → -20% daño

# Colores que existen en el juego
ALL_COLORS = {"rojo","amarillo","azul","morado","verde",
              "negro","blanco","halloween","summer","winter","april_fools"}

def calc_color_multiplier(attacker_color: str, defender_color: str) -> float:
    """
    Devuelve el multiplicador de daño según la rueda de colores.
    1.0 = normal, 1.25 = ventaja, 0.8 = desventaja, 2.0 = negro vs blanco o blanco vs negro.
    """
    a = (attacker_color or "").lower()
    d = (defender_color or "").lower()

    if not a or not d or a == d:
        return 1.0

    # Negro vs Blanco o Blanco vs Negro → ambos hacen x2
    if {a, d} == {"negro", "blanco"}:
        return 2.0

    # Neutros: negro, blanco, april_fools no tienen ventaja/desventaja salvo lo anterior
    neutral = {"negro", "blanco", "april_fools"}
    if a in neutral or d in neutral:
        return 1.0

    # Ventaja
    if COLOR_BEATS.get(a) == d:
        return BONUS_MULTIPLIER

    # Desventaja
    if COLOR_BEATS.get(d) == a:
        return PENALTY_MULTIPLIER

    return 1.0


# ============================================================
#  VARIANTES POR FIGURA
#
#  Formato de cada variante:
#  {
#    "color":       str   — color de la variante
#    "name_suffix": str   — ej. "Rojo" → se añade al nombre en batalla
#    "hp_mod":      float — multiplicador de HP (1.0 = sin cambio)
#    "atk_mod":     float — multiplicador de ATK
#    "def_mod":     float — multiplicador de DEF
#    "passive":     str   — clave de pasiva especial de variante (ver apply_variant_on_attack)
#    "desc":        str   — descripción del efecto
#    "image":       str   — URL de imagen alternativa (vacío = usar la original)
#    "seasonal":    str   — temporada requerida para desbloquear (None = siempre disponible)
#  }
# ============================================================

VARIANTS = {

    # ── COMÚN ──────────────────────────────────────────────
    "lobster": {
        "rojo": {
            "color": "rojo", "name_suffix": "Rojo",
            "hp_mod": 1.1, "atk_mod": 1.1, "def_mod": 1.0,
            "passive": None,
            "desc": "Una langosta más agresiva. +10% HP y ATK.",
            "image": "", "seasonal": None,
        },
    },
    "don_manzanas": {
        "rojo": {
            "color": "rojo", "name_suffix": "Rojo",
            "hp_mod": 1.05, "atk_mod": 1.15, "def_mod": 0.95,
            "passive": None,
            "desc": "Más picante que de costumbre. +15% ATK, -5% DEF.",
            "image": "", "seasonal": None,
        },
    },

    # ── RARO ───────────────────────────────────────────────
    "gamer64": {
        "rojo": {
            "color": "rojo", "name_suffix": "Rojo",
            "hp_mod": 1.1, "atk_mod": 1.2, "def_mod": 0.95,
            "passive": None,
            "desc": "Modo turbo activado. +20% ATK, +10% HP, -5% DEF.",
            "image": "", "seasonal": None,
        },
    },
    "noob": {
        "amarillo": {
            "color": "amarillo", "name_suffix": "Amarillo",
            "hp_mod": 1.15, "atk_mod": 0.9, "def_mod": 1.2,
            "passive": None,
            "desc": "Noob miedoso pero tanque. +20% DEF, +15% HP, -10% ATK.",
            "image": "", "seasonal": None,
        },
    },

    # ── ÉPICO ──────────────────────────────────────────────
    "sonic": {
        "azul": {
            "color": "azul", "name_suffix": "Azul",
            "hp_mod": 0.95, "atk_mod": 1.2, "def_mod": 0.9,
            "passive": None,
            "desc": "Máxima velocidad. +20% ATK, -5% HP y DEF.",
            "image": "", "seasonal": None,
        },
    },
    "tails": {
        "amarillo": {
            "color": "amarillo", "name_suffix": "Amarillo",
            "hp_mod": 1.1, "atk_mod": 1.1, "def_mod": 1.1,
            "passive": None,
            "desc": "En modo inventor. +10% a todo.",
            "image": "", "seasonal": None,
        },
    },
    "agustoloco": {
        "azul": {
            "color": "azul", "name_suffix": "Azul",
            "hp_mod": 1.0, "atk_mod": 1.25, "def_mod": 0.9,
            "passive": None,
            "desc": "Modo caos. +25% ATK, -10% DEF.",
            "image": "", "seasonal": None,
        },
    },
    "007n7": {
        "azul": {
            "color": "azul", "name_suffix": "Azul",
            "hp_mod": 1.0, "atk_mod": 1.15, "def_mod": 1.1,
            "passive": None,
            "desc": "Operativo en campo. +15% ATK, +10% DEF.",
            "image": "", "seasonal": None,
        },
    },
    "two_time": {
        "negro": {
            "color": "negro", "name_suffix": "Negro",
            "hp_mod": 1.2, "atk_mod": 1.2, "def_mod": 1.0,
            "passive": None,
            "desc": "Doble de todo. +20% HP y ATK.",
            "image": "", "seasonal": None,
        },
    },
    "guest1337": {
        "azul": {
            "color": "azul", "name_suffix": "Azul",
            "hp_mod": 1.05, "atk_mod": 1.2, "def_mod": 1.0,
            "passive": None,
            "desc": "El invitado élite. +20% ATK.",
            "image": "", "seasonal": None,
        },
    },
    "janedoe": {
        "morado": {
            "color": "morado", "name_suffix": "Morado",
            "hp_mod": 1.1, "atk_mod": 1.1, "def_mod": 1.1,
            "passive": None,
            "desc": "Misteriosa y equilibrada. +10% a todo.",
            "image": "", "seasonal": None,
        },
    },

    # ── LEGENDARIO ─────────────────────────────────────────
    "alex": {
        "amarillo": {
            "color": "amarillo", "name_suffix": "Amarillo",
            "hp_mod": 1.15, "atk_mod": 1.15, "def_mod": 1.0,
            "passive": None,
            "desc": "Modo constructora. +15% HP y ATK.",
            "image": "", "seasonal": None,
        },
    },
    "ringmaster": {
        "rojo": {
            "color": "rojo", "name_suffix": "Rojo",
            "hp_mod": 1.0, "atk_mod": 1.3, "def_mod": 0.9,
            "passive": None,
            "desc": "¡Función de gala! +30% ATK, -10% DEF.",
            "image": "", "seasonal": None,
        },
    },
    "michibug": {
        "azul": {
            "color": "azul", "name_suffix": "Azul",
            "hp_mod": 1.2, "atk_mod": 1.0, "def_mod": 1.2,
            "passive": None,
            "desc": "Protección máxima. +20% HP y DEF.",
            "image": "", "seasonal": None,
        },
    },
    "1x1x1x1": {
        "verde": {
            "color": "verde", "name_suffix": "Verde",
            "hp_mod": 1.1, "atk_mod": 1.2, "def_mod": 1.0,
            "passive": None,
            "desc": "Odio puro. +20% ATK, +10% HP.",
            "image": "", "seasonal": None,
        },
    },
    "c00lkidd": {
        "rojo": {
            "color": "rojo", "name_suffix": "Rojo",
            "hp_mod": 1.0, "atk_mod": 1.25, "def_mod": 0.95,
            "passive": None,
            "desc": "El hacker enojado. +25% ATK.",
            "image": "", "seasonal": None,
        },
    },
    "noli": {
        "morado": {
            "color": "morado", "name_suffix": "Morado",
            "hp_mod": 1.1, "atk_mod": 1.1, "def_mod": 1.1,
            "passive": None,
            "desc": "Modo misterioso. +10% a todo.",
            "image": "", "seasonal": None,
        },
    },
    "chance": {
        "negro": {
            "color": "negro", "name_suffix": "Negro",
            "hp_mod": 1.2, "atk_mod": 1.1, "def_mod": 1.1,
            "passive": None,
            "desc": "Oscuridad total. +20% HP, +10% ATK y DEF.",
            "image": "", "seasonal": None,
        },
    },
    "johndoe": {
        "amarillo_negro": {
            "color": "amarillo",   # rueda usa amarillo
            "name_suffix": "Amarillo y Negro",
            "hp_mod": 1.0, "atk_mod": 0.5, "def_mod": 1.0,
            "passive": "john_half",   # afecta y es afectado al 50%
            "desc": "Todo a medias. Ataca y recibe la mitad del daño/curación.",
            "image": "", "seasonal": None,
        },
    },
    "kirby": {
        "blanco": {
            "color": "blanco", "name_suffix": "Blanco",
            "hp_mod": 1.2, "atk_mod": 1.0, "def_mod": 1.2,
            "passive": None,
            "desc": "Kirby puro. +20% HP y DEF.",
            "image": "", "seasonal": None,
        },
    },
    "papyrus": {
        "rojo": {
            "color": "rojo", "name_suffix": "Rojo",
            "hp_mod": 1.1, "atk_mod": 1.2, "def_mod": 1.0,
            "passive": None,
            "desc": "¡NYEHEHEH! Versión más fuerte. +20% ATK, +10% HP.",
            "image": "", "seasonal": None,
        },
    },
    "flowey": {
        "amarillo": {
            "color": "amarillo", "name_suffix": "Amarillo",
            "hp_mod": 1.1, "atk_mod": 1.15, "def_mod": 1.0,
            "passive": None,
            "desc": "Howdy! +15% ATK, +10% HP.",
            "image": "", "seasonal": None,
        },
    },
    "omega_flowey": {
        "negro": {
            "color": "negro", "name_suffix": "Negro",
            "hp_mod": 1.15, "atk_mod": 1.25, "def_mod": 1.0,
            "passive": None,
            "desc": "Modo dios oscuro. +25% ATK, +15% HP.",
            "image": "", "seasonal": None,
        },
    },

    # ── MÍTICO ─────────────────────────────────────────────
    "shedletsky": {
        "amarillo": {
            "color": "amarillo", "name_suffix": "Amarillo",
            "hp_mod": 1.1, "atk_mod": 1.2, "def_mod": 1.1,
            "passive": None,
            "desc": "+20% ATK, +10% HP y DEF.",
            "image": "", "seasonal": None,
        },
    },
    "impostor_negro": {
        "negro": {
            "color": "negro", "name_suffix": "Negro",
            "hp_mod": 1.2, "atk_mod": 1.2, "def_mod": 1.1,
            "passive": None,
            "desc": "El impostor. +20% HP y ATK, +10% DEF.",
            "image": "", "seasonal": None,
        },
    },
    "homero": {
        "amarillo": {
            "color": "amarillo", "name_suffix": "Amarillo",
            "hp_mod": 1.15, "atk_mod": 1.1, "def_mod": 1.1,
            "passive": None,
            "desc": "D'oh! +15% HP, +10% ATK y DEF.",
            "image": "", "seasonal": None,
        },
    },
    "jevil": {
        "morado": {
            "color": "morado", "name_suffix": "Morado",
            "hp_mod": 1.1, "atk_mod": 1.2, "def_mod": 1.0,
            "passive": None,
            "desc": "CHAOS CHAOS! +20% ATK, +10% HP.",
            "image": "", "seasonal": None,
        },
    },
    "annoying_dog": {
        "blanco": {
            "color": "blanco", "name_suffix": "Blanco",
            "hp_mod": 1.2, "atk_mod": 1.1, "def_mod": 1.2,
            "passive": None,
            "desc": "El perro misterioso. +20% HP y DEF, +10% ATK.",
            "image": "", "seasonal": None,
        },
    },
    "santa_vaca": {
        "blanco": {
            "color": "blanco", "name_suffix": "Blanco",
            "hp_mod": 1.15, "atk_mod": 1.15, "def_mod": 1.15,
            "passive": None,
            "desc": "¡SANTA VACA! Modo sagrado. +15% a todo.",
            "image": "", "seasonal": None,
        },
    },
    "sans": {
        "azul": {
            "color": "azul", "name_suffix": "Azul",
            "hp_mod": 1.0, "atk_mod": 1.3, "def_mod": 1.0,
            "passive": None,
            "desc": "heh. +30% ATK.",
            "image": "", "seasonal": None,
        },
    },
    "og_gamer64": {
        "blanco": {
            "color": "blanco", "name_suffix": "Blanco",
            "hp_mod": 1.2, "atk_mod": 1.2, "def_mod": 1.2,
            "passive": None,
            "desc": "El original. +20% a todo.",
            "image": "", "seasonal": None,
        },
    },
}


# ============================================================
#  VARIANTES DE TEMPORADA (exclusivas)
#  seasonal: clave de SEASONS requerida para tener la variante
# ============================================================

SEASONAL_VARIANTS = {
    "halloween": {
        "name":    "🎃 Halloween",
        "color":   "halloween",
        "passive": "halloween_stun",
        "desc":    (
            "Si tienes 60+ energía: tus ataques aplican stun 2 turnos y +5 daño extra "
            "hasta que la energía baje. Al derrotar enemigos hay % de dropear 🍬 Dulces."
        ),
        "ingredient_drop": "🍬",   # nuevo ingrediente
        "ingredient_chance": 30,   # 30% al vencer figura enemiga
    },
    "trick_or_treat": {
        "name":    "🎃 Trick or Treat",
        "color":   "halloween",
        "passive": "trick_or_treat",
        "desc":    (
            "60% de prob. de curarte el daño que haces al oponente, "
            "40% de recibir ese daño tú y forzar cambio de figura en ambos lados."
        ),
    },
    "christmas": {
        "name":    "❄️ Christmas",
        "color":   "winter",
        "passive": "christmas_freeze",
        "desc":    "Cuando te atacan, 40% de congelar al oponente por 3 turnos.",
    },
    "ice_bender": {
        "name":    "❄️ Ice Bender",
        "color":   "winter",
        "passive": "ice_bender",
        "desc":    "Con 60+ energía: 50% de aplicar frozen 3 turnos con cada ataque.",
    },
    "fire_bender": {
        "name":    "☀️ Fire Bender",
        "color":   "summer",
        "passive": "fire_bender",
        "desc":    "Con 60+ energía: 50% de aplicar burning 4 turnos con cada ataque.",
    },
    "sun_god": {
        "name":    "☀️ Sun God",
        "color":   "summer",
        "passive": "sun_god",
        "desc":    (
            "70% de aplicar burning 2 turnos con cada ataque, "
            "50% de ganar +ATK extra por 4 turnos."
        ),
    },
    "april_fools": {
        "name":    "🃏 April Fools",
        "color":   "april_fools",
        "passive": "april_fools_swap",
        "desc":    "Al inicio de la batalla, intercambia stats y habilidades con el oponente. ¡QUIÉN ES QUIÉN!",
    },
    "toon": {
        "name":    "🃏 Toon",
        "color":   "april_fools",
        "passive": "toon_dodge",
        "desc":    "55% de esquivar el daño entrante y devolver 1/4 del daño original sin recibirlo.",
    },
    "low_effort_high_stats": {
        "name":    "🃏 Low Effort, High Stats",
        "color":   "april_fools",
        "passive": "lohs",
        "desc":    (
            "Pierdes 50% de HP inicial pero ganas +25% ATK "
            "y 20% de aplicar cualquier efecto negativo al oponente con cada ataque."
        ),
        "hp_mod": 0.5, "atk_mod": 1.25,
    },
}

# Mapeo temporada → variantes desbloqueables
SEASON_VARIANT_POOL = {
    "halloween":   ["halloween", "trick_or_treat"],
    "christmas":   ["christmas", "ice_bender"],
    "summer":      ["fire_bender", "sun_god"],
    "april_fools": ["april_fools", "toon", "low_effort_high_stats"],
}

# Efectos negativos que puede aplicar Low Effort, High Stats
LOHS_BAD_EFFECTS = ["frozen", "burning", "stunned", "poisoned", "weakened"]


# ============================================================
#  APLICAR VARIANTE A UN FIGHTER
# ============================================================

def apply_variant(fighter: dict, variant_key: str, is_seasonal: bool = False):
    """
    Modifica un fighter dict en-place aplicando su variante.
    variant_key: clave dentro de VARIANTS[fig_key] o SEASONAL_VARIANTS
    is_seasonal: True si es variante de temporada
    """
    if is_seasonal:
        vdata = SEASONAL_VARIANTS.get(variant_key)
    else:
        fig_key = fighter.get("key", "")
        fig_variants = VARIANTS.get(fig_key, {})
        vdata = fig_variants.get(variant_key)

    if not vdata:
        return

    # Aplicar modificadores de stats
    hp_mod  = vdata.get("hp_mod",  1.0)
    atk_mod = vdata.get("atk_mod", 1.0)
    def_mod = vdata.get("def_mod", 1.0)

    if hp_mod != 1.0:
        new_hp = max(1, int(fighter["hp"] * hp_mod))
        fighter["hp"]     = new_hp
        fighter["max_hp"] = new_hp
    if atk_mod != 1.0:
        fighter["atk"] = max(1, int(fighter["atk"] * atk_mod))
    if def_mod != 1.0:
        fighter["defense"] = max(0, int(fighter["defense"] * def_mod))

    # Registrar color y pasiva
    fighter["variant"]         = variant_key
    fighter["variant_color"]   = vdata.get("color", "")
    fighter["variant_passive"] = vdata.get("passive")
    fighter["variant_name"]    = vdata.get("name_suffix") or vdata.get("name", "")
    fighter["is_seasonal_var"] = is_seasonal

    # Pasiva especial: Low Effort, High Stats
    if vdata.get("passive") == "lohs":
        fighter["lohs_atk_boost"] = True

    # Pasiva especial: April Fools (swap se aplica en BattleState.start)
    if vdata.get("passive") == "april_fools_swap":
        fighter["april_fools_pending_swap"] = True

    # Cambio de nombre en batalla
    suffix = fighter.get("variant_name", "")
    if suffix:
        fighter["name"] = f"{fighter['name']} [{suffix}]"

    # Cambio de imagen si tiene
    img = vdata.get("image", "")
    if img:
        fighter["image"] = img


# ============================================================
#  EFECTOS DE VARIANTE DURANTE EL ATAQUE
#  Llamar desde execute_action DESPUÉS de calcular el daño base
# ============================================================

def apply_variant_on_attack(attacker: dict, defender: dict,
                             base_dmg: int, battle, log: list) -> int:
    """
    Aplica efectos pasivos de variante al atacante sobre el defensor.
    Devuelve el daño final (puede ser modificado por efectos).
    """
    passive = attacker.get("variant_passive")
    energy  = attacker.get("energy", 0)
    dmg     = base_dmg

    # ── HALLOWEEN: stun si energía >= 60 ────────────────────────────────
    if passive == "halloween_stun" and energy >= 60:
        dmg += 5
        if not defender.get("stun_immune"):
            defender["stun_turns"] = max(defender.get("stun_turns", 0), 2)
            log.append(f"   🎃 **Halloween**: +5 daño y ¡**{defender['name']}** queda stunned 2 turnos!")
        else:
            log.append(f"   🎃 **Halloween**: +5 daño extra (stun inmune)!")

    # ── TRICK OR TREAT ───────────────────────────────────────────────────
    elif passive == "trick_or_treat":
        roll = random.randint(1, 100)
        if roll <= 60:
            attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + dmg)
            log.append(f"   🍬 **Trick or Treat**: ¡{attacker['name']} se curó {dmg} HP!")
            return 0   # el daño se convierte en curación, no golpea al defensor
        else:
            attacker["hp"] = max(0, attacker["hp"] - dmg)
            log.append(
                f"   💀 **Trick or Treat**: ¡El truco salió mal! "
                f"{attacker['name']} recibe {dmg} daño y ambos cambian de figura!"
            )
            # Forzar cambio de figura en ambos equipos
            battle._force_switch_next(battle.p1_team, battle.p1_idx)
            battle._force_switch_next(battle.p2_team, battle.p2_idx)
            return 0

    # ── ICE BENDER: frozen si energía >= 60 ─────────────────────────────
    elif passive == "ice_bender" and energy >= 60:
        if random.randint(1, 100) <= 50:
            defender["frozen"] = True
            defender["frozen_turns"] = max(defender.get("frozen_turns", 0), 3)
            log.append(f"   ❄️ **Ice Bender**: ¡**{defender['name']}** congelado 3 turnos!")

    # ── FIRE BENDER: burning si energía >= 60 ───────────────────────────
    elif passive == "fire_bender" and energy >= 60:
        if random.randint(1, 100) <= 50:
            defender["burning"] = True
            defender["burning_turns"] = max(defender.get("burning_turns", 0), 4)
            log.append(f"   🔥 **Fire Bender**: ¡**{defender['name']}** quemado 4 turnos!")

    # ── SUN GOD ──────────────────────────────────────────────────────────
    elif passive == "sun_god":
        if random.randint(1, 100) <= 70:
            defender["burning"] = True
            defender["burning_turns"] = max(defender.get("burning_turns", 0), 2)
            log.append(f"   ☀️ **Sun God**: ¡**{defender['name']}** quemado 2 turnos!")
        if random.randint(1, 100) <= 50:
            attacker["atk_buff"] = attacker.get("atk_buff", 0) + 15
            attacker["sun_buff_turns"] = 4
            log.append(f"   ☀️ **Sun God**: ¡{attacker['name']} gana +15 ATK por 4 turnos!")

    # ── TOON: esquivar y contraatacar ────────────────────────────────────
    elif passive == "toon_dodge":
        # Este efecto se aplica en defensa (ver apply_variant_on_defense)
        pass

    # ── LOHS ─────────────────────────────────────────────────────────────
    elif passive == "lohs":
        if random.randint(1, 100) <= 20:
            bad = random.choice(LOHS_BAD_EFFECTS)
            if bad == "frozen":
                defender["frozen"] = True
                defender["frozen_turns"] = max(defender.get("frozen_turns", 0), 2)
            elif bad == "burning":
                defender["burning"] = True
                defender["burning_turns"] = max(defender.get("burning_turns", 0), 2)
            elif bad == "stunned":
                if not defender.get("stun_immune"):
                    defender["stun_turns"] = max(defender.get("stun_turns", 0), 1)
            elif bad == "poisoned":
                defender["poisoned"] = True
                defender["poison_turns"] = max(defender.get("poison_turns", 0), 2)
            elif bad == "weakened":
                defender["atk"] = max(1, int(defender["atk"] * 0.85))
            log.append(f"   🃏 **LEHS**: ¡Efecto **{bad}** aplicado a {defender['name']}!")

    # ── CHRISTMAS: congelar al ser atacado (se aplica en defensa) ────────
    # (ver apply_variant_on_defense)

    # ── JOHN HALF: daño a la mitad ───────────────────────────────────────
    if attacker.get("variant_passive") == "john_half":
        dmg = max(1, dmg // 2)
        log.append(f"   🖤 **John Doe [Amarillo y Negro]**: daño reducido a la mitad ({dmg}).")

    return dmg


def apply_variant_on_defense(defender: dict, attacker: dict,
                              incoming_dmg: int, battle, log: list) -> int:
    """
    Aplica efectos pasivos de variante AL DEFENDER cuando recibe un ataque.
    Devuelve el daño final recibido (puede reducirse o convertirse).
    """
    passive = defender.get("variant_passive")
    dmg     = incoming_dmg

    # ── CHRISTMAS: congelar al atacante al ser golpeado ──────────────────
    if passive == "christmas_freeze":
        if random.randint(1, 100) <= 40:
            attacker["frozen"] = True
            attacker["frozen_turns"] = max(attacker.get("frozen_turns", 0), 3)
            log.append(f"   ❄️ **Christmas**: ¡**{attacker['name']}** quedó congelado 3 turnos!")

    # ── TOON: esquivar y contraatacar ────────────────────────────────────
    elif passive == "toon_dodge":
        if random.randint(1, 100) <= 55:
            counter = max(1, incoming_dmg // 4)
            attacker["hp"] = max(0, attacker["hp"] - counter)
            log.append(
                f"   🎭 **Toon**: ¡{defender['name']} esquivó cómicamente y devolvió "
                f"{counter} daño a {attacker['name']}!"
            )
            return 0   # no recibe el daño

    # ── JOHN HALF: recibe la mitad ────────────────────────────────────────
    if defender.get("variant_passive") == "john_half":
        dmg = max(1, dmg // 2)
        log.append(f"   🖤 **John Doe**: recibe solo la mitad del daño ({dmg}).")

    return dmg


def apply_color_multiplier_to_dmg(dmg: int, attacker: dict, defender: dict, log: list) -> int:
    """
    Aplica el multiplicador de color/rueda de atributos al daño calculado.
    Muestra mensaje en log si hay ventaja/desventaja.
    """
    a_color = attacker.get("variant_color", "")
    d_color = defender.get("variant_color", "")

    mult = calc_color_multiplier(a_color, d_color)
    if mult == 1.0:
        return dmg

    final = max(1, int(dmg * mult))

    if mult > 1.0:
        if mult == 2.0:
            log.append(f"   ⬛⬜ **NEGRO vs BLANCO**: ¡Ambos hacen el DOBLE de daño! ({final})")
        else:
            log.append(
                f"   🎯 **Ventaja de color** ({a_color} vs {d_color}): "
                f"x{mult:.2f} → {final} daño!"
            )
    else:
        log.append(
            f"   🛡️ **Desventaja de color** ({a_color} vs {d_color}): "
            f"x{mult:.2f} → {final} daño."
        )
    return final


# ============================================================
#  HELPER: OBTENER VARIANTE ACTIVA DE UN USUARIO
# ============================================================

def get_active_variant(user_data: dict, fig_key: str) -> tuple[str | None, bool]:
    """
    Devuelve (variant_key, is_seasonal) de la variante equipada por el usuario
    para la figura dada, o (None, False) si no tiene ninguna.
    """
    variants_equipped = user_data.get("variants_equipped", {})
    entry = variants_equipped.get(fig_key)
    if not entry:
        return None, False
    return entry.get("key"), entry.get("seasonal", False)


def get_owned_variants(user_data: dict) -> dict:
    """Devuelve {fig_key: [variant_keys...]} de todas las variantes que posee el usuario."""
    return user_data.get("variants_owned", {})
