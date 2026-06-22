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
    "season_not_found": {"name": "💾 [SEASON NOT FOUND]", "emoji": "💾", "color": 0x57f287},
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
    "lobster":      {"rojo":      {"color": "rojo",      "name_suffix": "Rojo"}},
    "don_manzanas": {"rojo":      {"color": "rojo",      "name_suffix": "Rojo"}},

    # ── RARO ───────────────────────────────────────────────
    "gamer64":      {"rojo":      {"color": "rojo",      "name_suffix": "Rojo"}},
    "noob":         {"amarillo":  {"color": "amarillo",  "name_suffix": "Amarillo"}},

    # ── ÉPICO ──────────────────────────────────────────────
    "sonic":        {"azul":      {"color": "azul",      "name_suffix": "Azul"}},
    "tails":        {"amarillo":  {"color": "amarillo",  "name_suffix": "Amarillo"}},
    "agustoloco":   {"azul":      {"color": "azul",      "name_suffix": "Azul"}},
    "007n7":        {"azul":      {"color": "azul",      "name_suffix": "Azul"}},
    "two_time":     {"negro":     {"color": "negro",     "name_suffix": "Negro"}},
    "guest1337":    {"azul":      {"color": "azul",      "name_suffix": "Azul"}},
    "janedoe":      {"morado":    {"color": "morado",    "name_suffix": "Morado"}},

    # ── LEGENDARIO ─────────────────────────────────────────
    "alex":         {"amarillo":  {"color": "amarillo",  "name_suffix": "Amarillo"}},
    "ringmaster":   {"rojo":      {"color": "rojo",      "name_suffix": "Rojo"}},
    "michibug":     {"azul":      {"color": "azul",      "name_suffix": "Azul"}},
    "1x1x1x1":      {"verde":     {"color": "verde",     "name_suffix": "Verde"}},
    "c00lkidd":     {"rojo":      {"color": "rojo",      "name_suffix": "Rojo"}},
    "noli":         {"morado":    {"color": "morado",    "name_suffix": "Morado"}},
    "chance":       {"negro":     {"color": "negro",     "name_suffix": "Negro"}},
    "johndoe": {
        "amarillo_negro": {
            "color": "amarillo",   # la rueda lo trata como amarillo
            "name_suffix": "Amarillo y Negro",
            "passive": "john_half",   # único caso especial: afecta y es afectado a la mitad
        },
    },
    "kirby":        {"blanco":    {"color": "blanco",    "name_suffix": "Blanco"}},
    "papyrus":      {"rojo":      {"color": "rojo",      "name_suffix": "Rojo"}},
    "flowey":       {"amarillo":  {"color": "amarillo",  "name_suffix": "Amarillo"}},
    "omega_flowey": {"negro":     {"color": "negro",     "name_suffix": "Negro"}},

    # ── MÍTICO ─────────────────────────────────────────────
    "shedletsky":     {"amarillo": {"color": "amarillo", "name_suffix": "Amarillo"}},
    "impostor_negro": {"negro":    {"color": "negro",    "name_suffix": "Negro"}},
    "homero":         {"amarillo": {"color": "amarillo", "name_suffix": "Amarillo"}},
    "jevil":          {"morado":   {"color": "morado",   "name_suffix": "Morado"}},
    "annoying_dog":   {"blanco":   {"color": "blanco",   "name_suffix": "Blanco"}},
    "santa_vaca":     {"blanco":   {"color": "blanco",   "name_suffix": "Blanco"}},
    "sans":           {"azul":     {"color": "azul",     "name_suffix": "Azul"}},
    "og_gamer64":     {"blanco":   {"color": "blanco",   "name_suffix": "Blanco"}},
    "ryu":            {"azul":     {"color": "azul",     "name_suffix": "Azul"}},
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
    # ── [SEASON NOT FOUND] ─────────────────────────────────────────────────
    "corrupted": {
        "name":    "💾 Corrupted",
        "color":   "season_not_found",
        "passive": "corrupted",
        "desc":    (
            "Con 50+ energia: 70% de aplicar Manipulation 2 turnos a una figura del oponente. "
            "Todos los ataques aplican veneno 2 turnos."
        ),
    },
    "glitched": {
        "name":    "💾 Glitched",
        "color":   "season_not_found",
        "passive": "glitched",
        "desc":    (
            "50% de aplicar Manipulation 3 turnos al atacar. "
            "40% de aplicar un efecto aleatorio con cada ataque."
        ),
    },
}

# Mapeo temporada → variantes desbloqueables
SEASON_VARIANT_POOL = {
    "halloween":   ["halloween", "trick_or_treat"],
    "christmas":   ["christmas", "ice_bender"],
    "summer":      ["fire_bender", "sun_god"],
    "april_fools":      ["april_fools", "toon", "low_effort_high_stats"],
    "season_not_found": ["corrupted", "glitched"],
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

ALL_RANDOM_EFFECTS = ["frozen", "burning", "stunned", "poisoned", "dizziness"]


def _apply_manipulation(target: dict, battle, turns: int, log: list):
    """
    Aplica el efecto MANIPULATION a 'target'.
    La figura es marcada como manipulada por 'turns' turnos.
    La logica de mover la figura al equipo contrario se maneja en execute_action.
    """
    if target.get("hp", 0) <= 0:
        log.append(f"   💾 Manipulation fallo: {target.get('name','?')} ya esta derrotada.")
        return
    if target.get("manipulated"):
        log.append(f"   💾 {target.get('name','?')} ya esta manipulada.")
        return

    target["manipulated"]        = True
    target["manipulation_turns"] = turns
    target["manipulation_energy_penalty"] = True   # gana menos energia
    target["manipulation_no_passive"]     = True   # no puede activar pasivas
    log.append(
        f"   💾 **MANIPULATION**: {target.get('name','?')} ha sido manipulada "
        f"por {turns} turnos! La figura ataca a su propio equipo."
    )


def _apply_random_effect(target: dict, log: list):
    """Aplica un efecto negativo aleatorio al objetivo (usado por Glitched)."""
    effect = random.choice(ALL_RANDOM_EFFECTS)
    if effect == "frozen":
        target["frozen"] = True
        target["frozen_turns"] = max(target.get("frozen_turns", 0), 2)
        log.append(f"   💾 **Glitched** — Efecto random: {target.get('name','?')} FROZEN 2T!")
    elif effect == "burning":
        target["burning"] = True
        target["burning_turns"] = max(target.get("burning_turns", 0), 2)
        log.append(f"   💾 **Glitched** — Efecto random: {target.get('name','?')} BURNING 2T!")
    elif effect == "stunned":
        target["stun_turns"] = max(target.get("stun_turns", 0), 1)
        log.append(f"   💾 **Glitched** — Efecto random: {target.get('name','?')} STUNNED 1T!")
    elif effect == "poisoned":
        target.setdefault("dots", []).append({"dmg": 6, "turns": 2})
        log.append(f"   💾 **Glitched** — Efecto random: {target.get('name','?')} POISONED 2T!")
    elif effect == "dizziness":
        target["dizziness"] = True
        target["dizziness_turns"] = max(target.get("dizziness_turns", 0), 2)
        log.append(f"   💾 **Glitched** — Efecto random: {target.get('name','?')} DIZZY 2T!")


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

    # ── CORRUPTED: manipulation + poison con 50+ energia ─────────────────
    elif passive == "corrupted":
        defender.setdefault("dots", []).append({"dmg": 8, "turns": 2})
        log.append(f"   💾 **Corrupted**: {defender['name']} envenenado 2 turnos!")
        if energy >= 50 and random.randint(1, 100) <= 70:
            _apply_manipulation(defender, battle=battle, turns=2, log=log)

    # ── GLITCHED: manipulation + efecto random ───────────────────────────
    elif passive == "glitched":
        if random.randint(1, 100) <= 50:
            _apply_manipulation(defender, battle=battle, turns=3, log=log)
        if random.randint(1, 100) <= 40:
            _apply_random_effect(defender, log)

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
