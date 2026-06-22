"""
battle.py — Sistema completo de batalla: BattleState, BattleView, execute_action,
            bot_turn, end_battle y helpers de combate.
"""
import random
import asyncio
import discord
from discord.ext import commands

from database import load_db, save_db, get_user
from figures import (
    FIGURES, FIGURE_SKILLS, RARITY_COLOR, RARITY_STARS,
    KIRBY_DEFAULT_SKILLS, KIRBY_TRANSFORMED_SLOT0,
    XP_PER_WIN, XP_PER_LOSS, COINS_WIN, COINS_LOSS,
    apply_level_bonus,
)
from variants import (
    apply_variant, apply_variant_on_attack, apply_variant_on_defense,
    apply_color_multiplier_to_dmg, get_active_variant,
    SEASONAL_VARIANTS, SEASONS,
)
from variants import (
    apply_variant, apply_variant_on_attack, apply_variant_on_defense,
    apply_color_multiplier_to_dmg, get_active_variant, SEASONAL_VARIANTS,
)
from economy import (
    INGREDIENTS, RECIPES, ACHIEVEMENTS, FIGURE_LEVEL_MAX,
    BATTLE_INGREDIENT_DROP_CHANCE,
    give_battle_ingredient, check_figure_levelup, check_achievements,
    grant_achievement, get_learn_effect, _check_player_levelup,
    _register_kill_for_love, _get_love_kills,
)
from bosses import IMPOSTOR_REWARDS

# Estado global de batallas activas
active_battles = {}
pending_pvp    = {}

ENERGY_PER_TURN = 20
ENERGY_MAX      = 100

def make_fighter(fig_key, owner_fig_data, hp_mult=1.0, atk_mult=1.0, energy_bonus=0):
    """Crea un luchador con HP, energía y habilidades listas."""
    fig = FIGURES[fig_key]
    lvl = owner_fig_data.get("level", 1)
    su  = owner_fig_data.get("stat_ups", {})  # bonuses elegidos al subir nivel

    base_hp  = int((apply_level_bonus(fig["hp"],     lvl) + su.get("hp", 0))  * hp_mult)
    base_atk = int((apply_level_bonus(fig["attack"],  lvl) + su.get("attack", 0)) * atk_mult)
    base_def = apply_level_bonus(fig["defense"], lvl)
    base_spd = fig.get("speed", 0) + su.get("speed", 0)
    energy_cap = ENERGY_MAX + su.get("energy_cap", 0)  # barra de carga ampliada

    fighter = {
        "key":          fig_key,
        "name":         fig["name"],
        "emoji":        fig["emoji"],
        "hp":           base_hp,
        "max_hp":       base_hp,
        "atk":          base_atk,
        "defense":      base_def,
        "speed":        base_spd,
        "level":        lvl,
        "energy":       0,
        "energy_cap":   energy_cap,
        "energy_bonus": energy_bonus,
        "skills":       FIGURE_SKILLS.get(fig_key, FIGURE_SKILLS["gamer64"]),
        "image":        fig.get("image", ""),
        "skill_upgrades": owner_fig_data.get("skill_upgrades_by_idx", {}),
        "total_kills": 0,   # kills en esta batalla (para LOVE Check en batalla)
    }
    # Pasiva de Gamer64: revive una vez con el 80% de su HP máximo
    if fig_key == "gamer64":
        fighter["passive_revive"] = True

    # Pasiva de OG GAMER 64: revive cambiando de fase (1→2→3→4→muerte)
    if fig_key == "og_gamer64":
        fighter["og_phase"] = 1
        fighter["passive_revive"] = False  # se maneja aparte con las fases

    # Pasiva de Caine: WHY DO YOU PEOPLE TORMENT ME
    # Cuando HP < 30%: daño x4 pero muere en 5 turnos
    if fig_key == "ringmaster":
        fighter["passive_torment_active"] = False
        fighter["passive_torment_turns"] = 0

    # Pasiva de Sans: MISS — barra de misses (120), 5 oportunidades vacías, luego daño normal
    if fig_key == "sans":
        fighter["sans_misses"]       = 120  # barra de misses (se gasta 10 por esquive)
        fighter["sans_empty_chances"]= 5    # oportunidades con barra vacía antes de recibir daño
        fighter["sans_sleeping"]     = False
        fighter["sans_woken"]        = False

    # Pasiva de Jevil: TRUE GOD OF CHAOS — 25% por turno de buff/debuff random a todos
    if fig_key == "jevil":
        fighter["chaos_passive_active"] = True

    # Annoying Dog: stats ocultas en /misfiguras (se muestran en batalla)
    if fig_key == "annoying_dog":
        fighter["secret_stats"] = True

    # Ryu: inicializar barra SUPER
    if fig_key == "ryu":
        fighter["super_bar"] = 0

    # Aplicar variante si viene en owner_fig_data
    variant_key = owner_fig_data.get("variant_key")
    variant_seasonal = owner_fig_data.get("variant_seasonal", False)
    if variant_key:
        apply_variant(fighter, variant_key, is_seasonal=variant_seasonal)

    return fighter

class BattleState:
    def __init__(self, p1_id, p2_id, p1_team_keys, p2_team_keys,
                 p1_figs_data, p2_figs_data, is_bot=False):
        self.p1 = p1_id
        self.p2 = p2_id
        self.is_bot = is_bot

        # Equipos: lista de fighters
        self.p1_team = [make_fighter(k, next((f for f in p1_figs_data if f["key"]==k), {"level":1})) for k in p1_team_keys]
        self.p2_team = [make_fighter(
            k,
            next((f for f in p2_figs_data if f["key"]==k), {"level":1}),
            hp_mult=next((f for f in p2_figs_data if f["key"]==k), {}).get("hp_mult", 1.0),
            atk_mult=next((f for f in p2_figs_data if f["key"]==k), {}).get("atk_mult", 1.0),
            energy_bonus=next((f for f in p2_figs_data if f["key"]==k), {}).get("energy_bonus", 0)
        ) for k in p2_team_keys]

        self.p1_active = 0   # índice del luchador activo
        self.p2_active = 0

        # Claves para recompensas
        self.p1_team_keys = p1_team_keys
        self.p2_team_keys = p2_team_keys

        self.turn = 1
        self.log = []
        self.message = None
        self.p1_name = "Jugador 1"   # se sobreescribe desde pvp-enemy/pvp-boss/retar
        self.p2_name = "Jugador 2"

    def current_p1(self): return self.p1_team[self.p1_active]
    def current_p2(self): return self.p2_team[self.p2_active]

    def hp_bar(self, current, maximum):
        ratio = max(0, current / maximum)
        filled = int(ratio * 10)
        return "🟩" * filled + "⬛" * (10 - filled) + f" {current}/{maximum}"

    def energy_bar(self, energy, color="blue"):
        """color="blue" para el jugador, color="red" para el enemigo."""
        filled_block = "🟦" if color == "blue" else "🟥"
        bar = ""
        for i in range(10):
            pos = (i + 1) * 10
            if pos <= energy:
                if pos == 30:   bar += "🟡"
                elif pos == 60: bar += "🟠"
                elif pos == 100:bar += "🔴"
                else:           bar += filled_block
            else:
                bar += "⬛"
        return bar + f" {energy}/100"

    def calc_damage(self, atk, defense, power, attacker_fig=None):
        eff_atk = atk
        if attacker_fig and attacker_fig.get("dizziness_turns", 0) > 0:
            eff_atk = int(eff_atk * 0.70)  # dizziness: -30% daño
        raw = int(eff_atk * (power / 100)) + random.randint(-3, 8)
        return max(1, raw - (defense // 4))

    def alive_team(self, team):
        return [f for f in team if f["hp"] > 0]

    def next_alive(self, team, current_idx):
        """Busca la siguiente figura viva en TODO el equipo (no solo después del índice actual)."""
        # Primero buscar después del índice actual (no bloqueada)
        for i in range(current_idx + 1, len(team)):
            if team[i]["hp"] > 0 and not team[i].get("force_locked", 0) > 0:
                return i
        # Luego buscar ANTES del índice actual (no bloqueada)
        for i in range(0, current_idx):
            if team[i]["hp"] > 0 and not team[i].get("force_locked", 0) > 0:
                return i
        # Si todas las vivas están bloqueadas, al menos devolver una viva
        for i in range(len(team)):
            if i != current_idx and team[i]["hp"] > 0:
                return i
        return None

    def any_alive(self, team):
        """Verifica si queda alguna figura viva en el equipo."""
        return any(f["hp"] > 0 for f in team)

    def _force_switch_next(self, team, current_idx):
        """Fuerza el cambio a la siguiente figura viva (para Trick or Treat, etc.)"""
        next_idx = self.next_alive(team, current_idx)
        if next_idx is not None and next_idx != current_idx:
            if team is self.p1_team:
                self.p1_active = next_idx
            else:
                self.p2_active = next_idx
            return True
        return False

    def tick_locks(self):
        """Reduce el contador force_locked y absorbed_turns al inicio de cada turno."""
        for fig in self.p1_team + self.p2_team:
            if fig.get("force_locked", 0) > 0:
                fig["force_locked"] -= 1
            if fig.get("absorbed_turns", 0) > 0:
                fig["absorbed_turns"] -= 1
                if fig["absorbed_turns"] == 0:
                    self.log.append(f"🌸 ¡**{fig['emoji']} {fig['name']}** regresa al campo después de ser absorbida por Kirby!")

    def get_embed(self, title="⚔️ BATALLA"):
        f1 = self.current_p1()
        f2 = self.current_p2()
        embed = discord.Embed(title=title, color=0xe74c3c)

        p1_label = self.p1_name
        p2_label = self.p2_name

        # --- Equipo jugador 1 ---
        team1_str = ""
        for i, f in enumerate(self.p1_team):
            active_mark = " ◀ EN COMBATE" if i == self.p1_active else ""
            if f["hp"] <= 0:
                team1_str += f"💀 ~~{f['emoji']} {f['name']}~~{active_mark}\n"
            else:
                team1_str += (
                    f"{f['emoji']} **{f['name']}**{active_mark}\n"
                    f"Vida: {self.hp_bar(f['hp'], f['max_hp'])}\n"
                )
        embed.add_field(name=f"👤 {p1_label}", value=team1_str, inline=True)

        # --- Equipo jugador 2 ---
        team2_str = ""
        for i, f in enumerate(self.p2_team):
            active_mark = " ◀ EN COMBATE" if i == self.p2_active else ""
            if f["hp"] <= 0:
                team2_str += f"💀 ~~{f['emoji']} {f['name']}~~{active_mark}\n"
            else:
                team2_str += (
                    f"{f['emoji']} **{f['name']}**{active_mark}\n"
                    f"Vida: {self.hp_bar(f['hp'], f['max_hp'])}\n"
                )
        # Discord limita campos a 1024 chars
        if len(team2_str) > 1000:
            team2_str = team2_str[:997] + "..."
        embed.add_field(name=f"👤 {p2_label}", value=team2_str or "?", inline=True)

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # --- Figura activa P1: vida + energía (azul) + habilidades ---
        type_emoji = {"damage":"⚔️","heal":"💚","drain":"⚡","drain_fill":"🔴","parry":"🛡️","buff":"⭐","gamble":"🎲","gamble_fire":"🔥","team_atk_buff":"⭐","dot":"💣","bad_update":"🔳","ban_hammer":"🔨"}
        skill_info = ""
        for sk in f1["skills"]:
            if sk.get("type") == "sans_rest":
                can = f1["energy"] > 0
                cost_display = f"{f1['energy']}⚡" if f1["energy"] > 0 else "0⚡"
            else:
                can = f1["energy"] >= sk["cost"]
                cost_display = f"{sk['cost']}⚡"
            lock = "✅" if can else "🔒"
            t = type_emoji.get(sk["type"], "⚡")
            skill_info += f"{lock} {t} **{sk['name']}** `[{cost_display}]`\n"

        # Barra de Misses para Sans
        sans_bar = ""
        if f1.get("key") == "sans":
            misses = f1.get("sans_misses", 0)
            empty  = f1.get("sans_empty_chances", 0)
            miss_filled = min(12, misses // 10)
            miss_bar = "🟦" * miss_filled + "⬛" * (12 - miss_filled)
            sans_bar = f"**Misses:** {miss_bar} `{misses}` | Oportunidades vacías: `{empty}/5`\n"

        embed.add_field(
            name=f"🔵 {p1_label} — {f1['emoji']} {f1['name']}",
            value=(
                f"**Vida:** {self.hp_bar(f1['hp'], f1['max_hp'])}\n"
                f"**Energía (tuya):** {self.energy_bar(f1['energy'], 'blue')}\n"
                f"{sans_bar}"
                f"─────────────────\n"
                f"{skill_info}"
            ),
            inline=False
        )

        # Barra de Misses del rival si es Sans
        sans_bar_rival = ""
        if f2.get("key") == "sans":
            misses2 = f2.get("sans_misses", 0)
            empty2  = f2.get("sans_empty_chances", 0)
            miss_filled2 = min(12, misses2 // 10)
            miss_bar2 = "🟦" * miss_filled2 + "⬛" * (12 - miss_filled2)
            sans_bar_rival = f"**Misses:** {miss_bar2} `{misses2}` | Oportunidades: `{empty2}/5`\n"

        # --- Figura activa P2: energía visible (roja) ---
        embed.add_field(
            name=f"🔴 {p2_label} — {f2['emoji']} {f2['name']}",
            value=(
                f"**Vida:** {self.hp_bar(f2['hp'], f2['max_hp'])}\n"
                f"**Energía (rival):** {self.energy_bar(f2['energy'], 'red')}\n"
                f"{sans_bar_rival}"
            ),
            inline=False
        )

        if self.log:
            embed.add_field(name="📜 Último turno", value="\n".join(self.log[-4:]), inline=False)

        if self.turn == 1:
            embed.set_footer(text=f"🎮 Turno de {p1_label} — elige una habilidad (✅ = disponible)")
        else:
            embed.set_footer(text=f"🎮 Turno de {p2_label}...")

        if f1.get("image"):
            embed.set_thumbnail(url=f1["image"])

        return embed

class BattleView(discord.ui.View):
    """View de batalla sin expiración."""
    def __init__(self, battle: BattleState):
        super().__init__(timeout=None)
        self.battle = battle

def get_battle_view(battle: BattleState):
    """Genera los botones de habilidad según la energía actual del luchador activo."""
    view = BattleView(battle)
    cur_team = battle.p1_team if battle.turn == 1 else battle.p2_team
    cur_idx   = battle.p1_active if battle.turn == 1 else battle.p2_active
    f = cur_team[cur_idx]

    # Fila 0: Atacar + Cambiar figura
    atk_btn = discord.ui.Button(
        label="⚔️ Atacar (gratis)",
        style=discord.ButtonStyle.success,
        custom_id="basic_attack",
        row=0
    )
    atk_btn.callback = make_skill_callback(-2, battle)
    view.add_item(atk_btn)

    # Botón cambiar figura (solo si hay otra figura viva y no bloqueada)
    switchable = [i for i, fig in enumerate(cur_team)
                  if i != cur_idx and fig["hp"] > 0 and not fig.get("force_locked", 0) > 0]
    if switchable:
        sw_btn = discord.ui.Button(
            label="🔄 Cambiar figura",
            style=discord.ButtonStyle.primary,
            custom_id="switch_figure",
            row=0
        )
        sw_btn.callback = make_switch_callback(battle, switchable, cur_team)
        view.add_item(sw_btn)

    # Botón de escape del ahorcamiento de Homero
    cur_fig = cur_team[cur_idx]
    if cur_fig.get("homer_choking") and cur_fig.get("stun_turns", 0) > 0:
        # Muestra botón de minijuego solo al jugador que está siendo ahorcado
        minigame_btn = discord.ui.Button(
            label="🎮 ¡ESCAPA DEL AHORCAMIENTO! (Presiona rápido)",
            style=discord.ButtonStyle.danger,
            custom_id="homer_escape",
            row=3,
        )
        async def homer_escape_cb(inter: discord.Interaction):
            if inter.user.id not in (battle.p1, battle.p2):
                await inter.response.send_message("❌ No eres parte de esta batalla.", ephemeral=True)
                return
            # Determina quién está siendo ahorcado
            choking_team = battle.p1_team if battle.turn == 2 else battle.p2_team
            choking_idx  = battle.p1_active if battle.turn == 2 else battle.p2_active
            choked_fig   = choking_team[choking_idx]
            # Encuentra a Homero (el ahorcador)
            homer_team   = battle.p2_team if battle.turn == 2 else battle.p1_team
            homer_idx    = battle.p2_active if battle.turn == 2 else battle.p1_active
            homer_fig    = homer_team[homer_idx]
            # Minijuego: probabilidad 65% de escapar (simplificado como botón de timing)
            success = random.random() < 0.65
            if success:
                # Libera al ahorcado, stunea a Homero
                choked_fig["homer_choking"]  = False
                choked_fig["stun_turns"]     = 0
                # Limpiar el DOT del ahorcamiento
                choked_fig["dots"] = [d for d in choked_fig.get("dots", [])
                                       if d.get("dmg") != 25]
                homer_fig["stun_turns"] = max(homer_fig.get("stun_turns", 0), 2)
                battle.log = [f"🎮 **¡MINIJUEGO COMPLETADO!** {choked_fig['name']} se libera del ahorcamiento!",
                               f"   😤 Homero queda stuneado 2 turnos de la sorpresa!"]
            else:
                battle.log = [f"🎮 **¡MINIJUEGO FALLIDO!** {choked_fig['name']} no logró liberarse..."]
            await inter.response.edit_message(embed=battle.get_embed(), view=get_battle_view(battle))
        minigame_btn.callback = homer_escape_cb
        view.add_item(minigame_btn)

    # Botón especial Switch Swords si Shedletsky está activo
    if f.get("key") == "chicken":
        swords = ["linked","firebrand","venomshank","windforce","darkheart","illumina","ghostwalker","ice_dagger"]
        sword_names = {"linked":"Linked Sword","firebrand":"Firebrand 🔥","venomshank":"Venomshank ☠️",
                       "windforce":"Windforce 🌪️","darkheart":"Darkheart 🖤","illumina":"Illumina ✨",
                       "ghostwalker":"Ghostwalker 👻","ice_dagger":"Ice Dagger 🧊"}
        current_sword = f.get("active_sword", "linked")
        options = [discord.SelectOption(
            label=sword_names[s],
            value=s,
            default=(s == current_sword)
        ) for s in swords]
        sword_select = discord.ui.Select(placeholder=f"🗡️ Espada actual: {sword_names[current_sword]}", options=options, row=2)
        async def sword_cb(inter: discord.Interaction, fig=f):
            if inter.user.id not in (battle.p1, battle.p2):
                await inter.response.send_message("❌ No eres parte de esta batalla.", ephemeral=True)
                return
            chosen = sword_select.values[0]
            prev = fig.get("active_sword", "linked")
            fig["active_sword"] = chosen
            # Resetear cargas de Ice Dagger si cambia de espada
            if prev != chosen and prev == "ice_dagger":
                fig["ice_dagger_charges"] = 0
                battle.log = [f"🗡️ **{fig['name']}** cambia a **{sword_names[chosen]}**! ❄️ Carga de Ice Dagger perdida."]
            else:
                battle.log = [f"🗡️ **{fig['name']}** equipa **{sword_names[chosen]}**!"]
            await inter.response.edit_message(embed=battle.get_embed(), view=get_battle_view(battle))
        sword_select.callback = sword_cb
        view.add_item(sword_select)

    # Fila 1: Habilidades especiales
    type_emoji = {"damage":"⚔️","heal":"💚","drain":"⚡","drain_fill":"🔴","parry":"🛡️",
                  "buff":"⭐","gamble":"🎲","gamble_fire":"🔥","team_atk_buff":"⭐",
                  "dot":"💣","bad_update":"🔳","ban_hammer":"🔨","fly_away":"✈️",
                  "charge_delete":"💥","og_ki_charge":"✨","instakill_random":"☠️",
                  "og_reset_phase":"🔄","og_its_over":"💣","og_its_over":"💥"}

    # Para OG GAMER 64 filtrar solo las habilidades de la fase activa
    all_skills = f["skills"]
    if f.get("key") == "og_gamer64" and any("phase" in sk for sk in all_skills):
        current_phase = f.get("og_phase", 1)
        skills_to_show = [sk for sk in all_skills if sk.get("phase") == current_phase]
    else:
        skills_to_show = all_skills

    for i, skill in enumerate(skills_to_show):
        real_idx = f["skills"].index(skill) if skill in f["skills"] else i
        # Rest de Sans: coste = toda la energía actual (usable si energy > 0)
        if skill.get("type") == "sans_rest":
            can_use  = f["energy"] > 0
            cost_lbl = f"{f['energy']}⚡" if f["energy"] > 0 else "0⚡"
        else:
            can_use  = f["energy"] >= skill["cost"]
            cost_lbl = f"{skill['cost']}⚡"
        t_emoji = type_emoji.get(skill["type"], "⚡")
        style = discord.ButtonStyle.danger if can_use else discord.ButtonStyle.secondary
        btn = discord.ui.Button(
            label=f"{t_emoji} {skill['name']} [{cost_lbl}]",
            style=style,
            disabled=not can_use,
            custom_id=f"skill_{real_idx}",
            row=1
        )
        btn.callback = make_skill_callback(real_idx, battle)
        view.add_item(btn)

    return view

def make_switch_callback(battle: BattleState, switchable: list, cur_team: list):
    """Muestra un selector de figura en el canal y ejecuta el cambio (cuesta el turno)."""
    async def callback(interaction: discord.Interaction):
        uid = interaction.user.id
        if battle.turn == 1 and uid != battle.p1:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return
        if battle.turn == 2 and not battle.is_bot and uid != battle.p2:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return

        options = []
        for i in switchable:
            fig = cur_team[i]
            options.append(discord.SelectOption(
                label=f"{fig['name']} (HP: {fig['hp']}/{fig['max_hp']})",
                value=str(i),
                emoji=fig["emoji"],
                description=f"Nv.{fig.get('level',1)} | ATK:{fig['atk']} DEF:{fig['defense']}"
            ))

        select = discord.ui.Select(placeholder="¿A qué figura cambias?", options=options)

        async def select_cb(inter: discord.Interaction):
            if inter.user.id != uid:
                await inter.response.send_message("❌ No es tu selección.", ephemeral=True)
                return

            chosen = int(select.values[0])
            old_fig = cur_team[battle.p1_active if battle.turn == 1 else battle.p2_active]
            if battle.turn == 1:
                battle.p1_active = chosen
            else:
                battle.p2_active = chosen
            new_fig = cur_team[chosen]
            battle.log = [
                f"🔄 **{old_fig['name']}** sale. ¡Entra **{new_fig['emoji']} {new_fig['name']}**!",
                "   (Cambio de figura — el rival ataca este turno)"
            ]

            # El cambio cuesta el turno: pasa al rival
            battle.turn = 2 if battle.turn == 1 else 1
            channel_id = inter.channel_id

            # Editar el mensaje del selector con el estado actualizado de la batalla
            # (el mensaje de batalla original nunca fue tocado)
            if battle.is_bot and battle.turn == 2:
                await inter.response.edit_message(embed=battle.get_embed(), view=None)
                # Sincronizar battle.message con este mensaje para que bot_turn pueda editarlo
                battle.message = await inter.original_response()
                await asyncio.sleep(1.2)
                await bot_turn(inter, battle, channel_id)
            else:
                await inter.response.edit_message(embed=battle.get_embed(), view=get_battle_view(battle))
                battle.message = await inter.original_response()

        select.callback = select_cb
        sw_view = discord.ui.View(timeout=120)
        sw_view.add_item(select)

        # Enviar el selector como mensaje NUEVO (sin tocar el mensaje de batalla)
        # y actualizar battle.message para que apunte a este nuevo mensaje
        await interaction.response.send_message(
            embed=battle.get_embed(title="🔄 Elige tu figura de reemplazo"),
            view=sw_view
        )
        battle.message = await interaction.original_response()

    return callback

def make_skill_callback(skill_idx, battle: BattleState):
    async def callback(interaction: discord.Interaction):
        uid = interaction.user.id
        channel_id = interaction.channel_id

        if channel_id not in active_battles:
            await interaction.response.send_message("❌ No hay batalla activa.", ephemeral=True)
            return
        if battle.turn == 1 and uid != battle.p1:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return
        if battle.turn == 2 and not battle.is_bot and uid != battle.p2:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return

        # ── Pasiva TIMING de Paper Mario ──────────────────────────────────
        # Si el atacante tiene passive2="timing" y va a usar un ataque de daño
        # mostrar el minijuego de timing ANTES de ejecutar la acción
        attacker_check = battle.current_p1() if battle.turn == 1 else battle.current_p2()
        is_damage_action = False
        if skill_idx == -2:
            is_damage_action = True  # ataque básico
        elif skill_idx >= 0 and skill_idx < len(attacker_check.get("skills", [])):
            sk = attacker_check["skills"][skill_idx]
            if sk.get("type") in ("damage", "slash", "fast_kill", "consumed_fury",
                                  "glitch_dmg", "holy_nuke", "lobster"):
                is_damage_action = True

        if (attacker_check.get("passive2") == "timing"
                and is_damage_action
                and not attacker_check.get("timing_used_this_turn")):
            await show_timing_minigame(interaction, battle, skill_idx, channel_id)
            return
        # ──────────────────────────────────────────────────────────────────

        await execute_action(interaction, battle, skill_idx, channel_id)
    return callback

async def show_timing_minigame(interaction, battle: BattleState, skill_idx: int, channel_id: int):
    """Minijuego de timing para Paper Mario.
    Muestra 3 botones — solo uno tiene el timing correcto.
    El jugador tiene 2 segundos para presionarlo."""
    import asyncio

    attacker = battle.current_p1() if battle.turn == 1 else battle.current_p2()
    attacker["timing_used_this_turn"] = True  # evitar loops

    # Elegir posición correcta aleatoriamente (0, 1 o 2)
    correct_pos = random.randint(0, 2)
    labels = ["⬅️ ¡Ahora!", "⬆️ ¡Ahora!", "➡️ ¡Ahora!"]
    dummy_labels = ["⬅️ ...", "⬆️ ...", "➡️ ..."]

    timing_result = {"success": False, "answered": False}


    embed = discord.Embed(
        title="⭐ ¡TIMING! — Pasiva de Paper Mario",
        description=(
            f"**{attacker['emoji']} {attacker['name']}** prepara su ataque...\n\n"
            f"Presiona el botón **¡Ahora!** correcto para conseguir **+20 ATK** en este golpe!\n"
            f"⏰ Tienes **2 segundos**!"
        ),
        color=0xf1c40f
    )
    view = discord.ui.View(timeout=2)

    async def make_timing_btn(pos: int):
        is_correct = (pos == correct_pos)
        label = labels[pos] if is_correct else dummy_labels[pos]
        btn = discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.success if is_correct else discord.ButtonStyle.secondary,
            custom_id=f"timing_{pos}",
            row=0
        )
        async def timing_cb(inter: discord.Interaction):
            if inter.user.id != interaction.user.id:
                await inter.response.send_message("❌ No es tu minijuego.", ephemeral=True)
                return
            timing_result["answered"] = True
            if is_correct:
                timing_result["success"] = True
                attacker["atk_buff"] = attacker.get("atk_buff", 0) + 20
                result_embed = discord.Embed(
                    title="⭐ ¡TIMING PERFECTO!",
                    description=f"**+20 ATK** para este ataque! ¡Brillante!",
                    color=0x2ecc71
                )
            else:
                result_embed = discord.Embed(
                    title="❌ ¡Timing fallido!",
                    description="No era ese botón... el ataque sale normal.",
                    color=0xe74c3c
                )
            await inter.response.edit_message(embed=result_embed, view=None)
            await asyncio.sleep(0.8)
            await execute_action(inter, battle, skill_idx, channel_id)
        btn.callback = timing_cb
        return btn

    for i in range(3):
        view.add_item(await make_timing_btn(i))

    async def on_timeout():
        if not timing_result["answered"]:
            # Se acabó el tiempo → ataque normal sin buff
            try:
                timeout_embed = discord.Embed(
                    title="⏰ ¡Tiempo agotado!",
                    description="El timing falló... el ataque sale sin buff.",
                    color=0x95a5a6
                )
                await interaction.edit_original_response(embed=timeout_embed, view=None)
                await asyncio.sleep(0.5)
                await execute_action(interaction, battle, skill_idx, channel_id)
            except Exception:
                pass

    view.on_timeout = on_timeout

    await interaction.response.edit_message(embed=embed, view=view)

async def execute_action(interaction, battle: BattleState, skill_idx: int, channel_id: int):
    """Ejecuta la acción del jugador activo."""
    attacker = battle.current_p1() if battle.turn == 1 else battle.current_p2()
    defender = battle.current_p2() if battle.turn == 1 else battle.current_p1()
    atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
    battle.log = []

    # ── APRIL FOOLS: intercambiar stats al inicio del primer turno ───────
    if not getattr(battle, "april_fools_swapped", False):
        for fighter in battle.p1_team + battle.p2_team:
            if fighter.get("april_fools_pending_swap"):
                opp_team = battle.p2_team if fighter in battle.p1_team else battle.p1_team
                opp = opp_team[0] if opp_team else None
                if opp:
                    # Intercambiar stats y habilidades
                    for stat in ("hp", "max_hp", "atk", "defense", "speed", "skills"):
                        fighter[stat], opp[stat] = opp[stat], fighter[stat]
                    battle.log.append(
                        f"   🃏 **APRIL FOOLS**: ¡Stats y habilidades de "
                        f"**{fighter['name']}** y **{opp['name']}** fueron intercambiadas!"
                    )
                    fighter.pop("april_fools_pending_swap", None)
        battle.april_fools_swapped = True
    # ─────────────────────────────────────────────────────────────────────

    # Reducir contadores de bloqueo
    battle.tick_locks()

    # Limpiar flag de timing de Paper Mario
    attacker = battle.current_p1() if battle.turn == 1 else battle.current_p2()
    attacker.pop("timing_used_this_turn", None)
    # Re-asignar attacker después del pop
    attacker = battle.current_p1() if battle.turn == 1 else battle.current_p2()

    # ── TICK: Efectos especiales de los Impostores FNF ────────────────────────

    # Ejected queue — cuenta atrás para el retorno de Green/Maroon
    if hasattr(battle, "ejected_queue") and battle.ejected_queue:
        still_pending = []
        for eq in battle.ejected_queue:
            eq["turns_left"] -= 1
            if eq["turns_left"] <= 0:
                # Comprobar si quedan figuras vivas en el bando enemigo del eyectado
                team     = battle.p1_team if eq["attacker_team"] == "p1" else battle.p2_team
                opp_team = battle.p2_team if eq["attacker_team"] == "p1" else battle.p1_team
                still_alive = any(f["hp"] > 0 for f in opp_team)
                if still_alive:
                    # VUELVE en segunda forma
                    idx  = eq["attacker_idx"]
                    sf   = eq["second_form"]
                    if sf in FIGURES and idx < len(team):
                        orig_fig  = FIGURES[sf]
                        new_entry = make_fighter(sf, {"level":1,"xp":0,"stat_ups":{}})
                        team[idx] = new_entry
                        # Reactivar esa figura si el equipo no tiene activo
                        idx_attr = "p1_active" if eq["attacker_team"] == "p1" else "p2_active"
                        if team[getattr(battle, idx_attr)]["hp"] <= 0:
                            setattr(battle, idx_attr, idx)
                        battle.log.append(f"🚀 **{orig_fig['name']}** VUELVE... ¡y está TRANSFORMADO!")
                # Si no quedan vivos, no vuelve (ya ganaste)
            else:
                still_pending.append(eq)
                if eq["turns_left"] <= 5:
                    battle.log.append(f"⏳ Los expulsados regresan en **{eq['turns_left']} turnos**...")
        battle.ejected_queue = still_pending

    # cant_attack_turns — Green no puede atacar
    for fig in battle.p1_team + battle.p2_team:
        if fig.get("cant_attack_turns", 0) > 0:
            fig["cant_attack_turns"] -= 1

    # hiding_turns — White Impostor emboscada
    for fig in battle.p1_team + battle.p2_team:
        if fig.get("hiding_turns", 0) > 0:
            fig["hiding_turns"] -= 1
            if fig["hiding_turns"] == 0:
                # Golpe sorpresa
                def_team = battle.p2_team if fig in battle.p1_team else battle.p1_team
                def_idx_attr = "p2_active" if fig in battle.p1_team else "p1_active"
                target = def_team[getattr(battle, def_idx_attr)]
                dmg = max(1, fig.get("hiding_strike_dmg", 30))
                target["hp"] = max(0, target["hp"] - dmg)
                # Volver a poner a White activo
                atk_team = battle.p1_team if fig in battle.p1_team else battle.p2_team
                atk_attr = "p1_active" if fig in battle.p1_team else "p2_active"
                for i, f in enumerate(atk_team):
                    if f is fig:
                        setattr(battle, atk_attr, i)
                        break
                fig.pop("hiding", None)
                battle.log.append(f"⚪ **{fig['name']}** sale de las sombras y ataca a {target['emoji']} {target['name']} por **{dmg}** de daño!")

    # flying_monstrosity — resolución al acabarse los turnos
    for fig in battle.p1_team + battle.p2_team:
        if fig.get("flying_hold_turns", 0) > 0:
            fig["flying_hold_turns"] -= 1
            if fig["flying_hold_turns"] == 0:
                # Si Green sobrevivió, la figura agarrada muere
                if fig["hp"] > 0:
                    # Encontrar la figura agarrada (la que tenía flying_held_turns)
                    def_team = battle.p2_team if fig in battle.p1_team else battle.p1_team
                    for held in def_team:
                        if held.get("flying_held_turns", 0) > 0:
                            held["flying_held_turns"] = 0
                            held["hp"] = 0
                            battle.log.append(f"🟢 **{fig['name']}** soltó a **{held['name']}**... demasiado tarde. ☠️")
                            break

    # rage_bait_debuff_turns
    for fig in battle.p1_team + battle.p2_team:
        if fig.get("rage_bait_debuff_turns", 0) > 0:
            fig["rage_bait_debuff_turns"] -= 1
            if fig["rage_bait_debuff_turns"] == 0:
                fig["atk"] = min(fig["atk"] + 10, fig.get("base_atk", fig["atk"] + 10))

    # friendship_shield — absorbe un ataque si tiene hits
    # (se procesa en el bloque de daño abajo)


    if attacker.get("passive_torment_active"):
        attacker["passive_torment_turns"] -= 1
        if attacker["passive_torment_turns"] <= 0:
            attacker["hp"] = 0
            battle.log.append(f"💀 **{attacker['emoji']} {attacker['name']}**: **¡¿PORQUE SIEMPRE ME ATORMENTAN?! ¡HUMANOS INSOLENTES!**")
            battle.log.append(f"   ...y cae derrotado por su propia furia.")
    elif attacker.get("key") == "ringmaster":
        hp_pct = attacker["hp"] / attacker["max_hp"]
        if hp_pct < 0.30 and not attacker.get("passive_torment_active"):
            attacker["passive_torment_active"] = True
            attacker["passive_torment_turns"] = 5
            attacker["atk"] = attacker["atk"] * 4   # daño x4
            battle.log.append(f"😡 **{attacker['emoji']} {attacker['name']}**: **¡¿POR QUÉ ME ATORMENTAN?!**")
            battle.log.append(f"   ¡Su daño se CUADRUPLICA... pero morirá en 5 turnos!")

    # Aplicar daño DOT (veneno/bomba) al atacante al inicio de su turno
    if attacker.get("dots"):
        total_dot = 0
        remaining = []
        for dot in attacker["dots"]:
            attacker["hp"] = max(0, attacker["hp"] - dot["dmg"])
            total_dot += dot["dmg"]
            dot["turns"] -= 1
            if dot["turns"] > 0:
                remaining.append(dot)
        attacker["dots"] = remaining
        battle.log.append(f"☠️ **{attacker['name']}** recibe **{total_dot}** de daño de veneno/bomba!")
        if attacker["hp"] <= 0:
            def_team = battle.p1_team if battle.turn == 1 else battle.p2_team
            def_idx_attr = "p1_active" if battle.turn == 1 else "p2_active"
            current_idx = getattr(battle, def_idx_attr)
            next_idx = battle.next_alive(def_team, current_idx)
            if next_idx is not None:
                setattr(battle, def_idx_attr, next_idx)
                battle.log.append(f"💀 **{attacker['name']}** murió por el veneno!")
            else:
                await end_battle(interaction, battle, channel_id, winner_turn=2 if battle.turn==1 else 1)
                return

    # Dizziness countdown y stun probabilístico (Map Revolving de Jevil)
    if attacker.get("dizziness_turns", 0) > 0:
        attacker["dizziness_turns"] -= 1
        stun_c = attacker.get("dizziness_stun_chance", 0)
        if stun_c > 0 and random.random() < stun_c:
            attacker["stun_turns"] = max(attacker.get("stun_turns", 0), 1)
            battle.log.append(f"💫 **{attacker['name']}** está tan mareado que pierde el turno!")

    # ── MANIPULATION TICK ────────────────────────────────────────────────────
    if attacker.get("manipulated"):
        mt = attacker.get("manipulation_turns", 0) - 1
        if mt <= 0:
            attacker["manipulated"]                = False
            attacker["manipulation_turns"]         = 0
            attacker["manipulation_energy_penalty"] = False
            attacker["manipulation_no_passive"]     = False
            battle.log.append(f"   💾 **{attacker['name']}** ya no está manipulada.")
        else:
            attacker["manipulation_turns"] = mt
            battle.log.append(f"   💾 **{attacker['name']}** sigue manipulada ({mt}T) — ataca a su propio equipo!")
    # ─────────────────────────────────────────────────────────────────────────

    # Verificar si está aturdido (con soporte de stun_turns)
    if attacker.get("stun_turns", 0) > 0:
        attacker["stun_turns"] -= 1
        battle.log.append(f"😵 **{attacker['name']}** está aturdido y pierde su turno! ({attacker['stun_turns']} turnos restantes)")
        battle.turn = 2 if battle.turn == 1 else 1
        await finish_turn(interaction, battle, channel_id)
        return

    # Can't attack (Keep the Act de Green)
    if attacker.get("cant_attack_turns", 0) > 0:
        battle.log.append(f"🟢 **{attacker['name']}** está fingiendo ser tripulante... no puede atacar aún.")
        battle.turn = 2 if battle.turn == 1 else 1
        await finish_turn(interaction, battle, channel_id)
        return
        # El turno VUELVE al rival (quien aturdo), no avanza
        battle.turn = 2 if battle.turn == 1 else 1
        await finish_turn(interaction, battle, channel_id)
        return
    elif attacker.get("stunned"):
        attacker["stunned"] = False
        battle.log.append(f"😵 **{attacker['name']}** está aturdido y pierde su turno!")
        # El turno VUELVE al rival (quien aturdo), no avanza
        battle.turn = 2 if battle.turn == 1 else 1
        await finish_turn(interaction, battle, channel_id)
        return

    # Siempre subir energía al inicio del turno
    _energy_gain = ENERGY_PER_TURN // 2 if attacker.get("manipulation_energy_penalty") else ENERGY_PER_TURN
    attacker["energy"] = min(ENERGY_MAX, attacker["energy"] + _energy_gain)

    if skill_idx == -2:
        # Resetear fast_kill si usa ataque básico
        if attacker.get("fast_kill_charges", 0) > 0:
            attacker["fast_kill_charges"] = 0
            battle.log.append(f"   ⚠️ **{attacker['name']}** interrumpió la carga de **Fast Kill**!")
        # Ataque básico — gana 20 de energía + daño = mitad del power máximo de la figura
        _energy_gain2 = ENERGY_PER_TURN // 2 if attacker.get("manipulation_energy_penalty") else ENERGY_PER_TURN
        attacker["energy"] = min(ENERGY_MAX, attacker["energy"] + _energy_gain2)
        bonus_atk = attacker.pop("atk_buff", 0)
        effective_atk = attacker["atk"] + bonus_atk
        # Daño = mitad del power de la habilidad más fuerte (skill cost 100), mínimo 1
        max_power = max((sk.get("power", 0) for sk in attacker["skills"]), default=20)
        base_dmg = max(1, round(max_power / 2))
        dmg = max(1, base_dmg + (bonus_atk // 2) + random.randint(-2, 3) - (defender["defense"] // 6))
        # ── Variante: efectos en ataque básico ───────────────────────────
        dmg = apply_variant_on_attack(attacker, defender, dmg, battle, battle.log)
        dmg = apply_color_multiplier_to_dmg(dmg, attacker, defender, battle.log)
        # Apple Armor: reduce el daño recibido
        if defender.get("apple_armor_turns", 0) > 0:
            reduction = defender.get("apple_armor_reduction", 0.5)
            dmg = max(1, int(dmg * reduction))
            defender["apple_armor_turns"] -= 1
            battle.log.append(f"   🍎🛡️ **Apple Armor** absorbe el golpe! (daño reducido al {int(reduction*100)}%, quedan {defender['apple_armor_turns']} turnos)")
        # Friendship Shield — absorbe el golpe completamente
        if defender.get("shield_hits", 0) > 0 and defender.get("shield_turns", 0) > 0:
            defender["shield_hits"] -= 1
            battle.log.append(f"   🩷 ¡El **Escudo de Amistad** absorbe el golpe! ({defender['shield_hits']} hits restantes)")
            dmg = 0

        # Bone Barrier de Sans — bloquea y hace daño al atacante
        if dmg > 0 and defender.get("bone_barrier"):
            defender["bone_barrier"] = False
            barrier_dmg = defender.get("bone_barrier_dmg", 15)
            attacker["hp"] = max(0, attacker["hp"] - barrier_dmg)
            battle.log.append(f"   🦴 ¡La **Bone Barrier** de Sans bloquea el ataque y hace {barrier_dmg} de daño a {attacker['name']}!")
            dmg = 0

        # Pasiva Sans: MISS — barra de misses
        if dmg > 0 and defender.get("key") == "sans" and not defender.get("sans_sleeping"):
            misses     = defender.get("sans_misses", 0)
            empty_left = defender.get("sans_empty_chances", 0)

            if misses > 0:
                # Tiene barra — esquiva y gasta 10
                defender["sans_misses"] = misses - 10
                remaining = defender["sans_misses"]
                battle.log.append(f"   <:SANS:1511160523775807588> **Sans** esquiva! [🟦 Misses: {remaining}/120]")
                # A los 30 misses gastados (90 restantes) se duerme
                if misses == 30 and not defender.get("sans_woken"):
                    defender["sans_sleeping"] = True
                    defender["stunned"]       = True
                    defender["stun_turns"]    = 1
                    battle.log.append(f"   😴 Sans... se está durmiendo... ¡Atácalo ahora!")
                dmg = 0

            elif empty_left > 0:
                # Barra vacía — pierde una oportunidad pero igual esquiva
                defender["sans_empty_chances"] = empty_left - 1
                left = empty_left - 1
                battle.log.append(f"   <:SANS:1511160523775807588> **Sans** aún esquiva... pero está exhausto. ({left} oportunidades restantes)")
                if left == 0:
                    battle.log.append(f"   💀 ¡Sans ya no puede esquivar más!")
                dmg = 0
            # Si misses=0 y empty_left=0 → cae el daño normal

        # Despertar de Sans — si estaba dormido y lo atacan, recibe buff
        if dmg > 0 and defender.get("key") == "sans" and defender.get("sans_sleeping") and not defender.get("sans_woken"):
            defender["sans_sleeping"] = False
            defender["sans_woken"]    = True
            defender["atk"] = defender.get("atk", 1) + 40
            battle.log.append(f"   😤 **Sans** despertó furioso. +40 ATK permanente!")

        dmg = apply_variant_on_defense(defender, attacker, dmg, battle, battle.log)
        defender["hp"] = max(0, defender["hp"] - dmg)
        # Parry check
        if defender.get("parrying"):
            defender["parrying"] = False
            if defender.get("parry_flat_bonus") is not None:
                # Alex: devuelve el daño recibido + flat bonus
                counter_dmg = max(1, dmg + defender["parry_flat_bonus"])
                defender.pop("parry_flat_bonus", None)
                attacker["hp"] = max(0, attacker["hp"] - counter_dmg)
                battle.log.append(f"   ⚡ **{defender['emoji']} {defender['name']}** hace **PARRY** y devuelve **{counter_dmg}** daño (tu daño +10)!")
            else:
                pct = defender.get("parry_dmg_pct", 25)
                counter_dmg = int(defender["max_hp"] * pct / 100)
                attacker["hp"] = max(0, attacker["hp"] - counter_dmg)
                battle.log.append(f"   ⚡ **{defender['emoji']} {defender['name']}** hace **COUNTER** y devuelve **{counter_dmg}** daño!")
    else:
        skill = attacker["skills"][skill_idx]
        # Rest de Sans: coste especial (consume toda la energía, se maneja en el stype)
        if skill.get("type") == "sans_rest":
            if attacker.get("energy", 0) <= 0:
                await interaction.response.send_message("❌ No tienes energía para descansar.", ephemeral=True)
                return
            # No descontar aquí — el stype lo maneja
        elif attacker["energy"] < skill["cost"]:
            await interaction.response.send_message("❌ No tienes suficiente energía.", ephemeral=True)
            return

        # Si no usa fast_kill, resetea los cargos acumulados
        if skill["type"] != "fast_kill" and attacker.get("fast_kill_charges", 0) > 0:
            attacker["fast_kill_charges"] = 0
            battle.log.append(f"   ⚠️ **{attacker['name']}** interrumpió la carga de **Fast Kill**!")

        # sans_rest maneja su propio consumo de energía
        if skill.get("type") != "sans_rest":
            attacker["energy"] -= skill["cost"]
        stype = skill["type"]

        if stype == "damage":
            # Bonus de combine (skill_upgrades)
            skill_upgrades = {}
            # Encontrar el índice real de esta habilidad para ver si tiene upgrade
            try:
                base_skills = FIGURE_SKILLS.get(attacker.get("key",""), [])
                real_skill_idx = next((i for i, sk in enumerate(base_skills) if sk.get("name") == skill.get("name")), None)
                # tier = 0→habilidad 0, 1→habilidad 1, 2→habilidad 2
                if real_skill_idx is not None:
                    # Recuperar skill_upgrades desde el estado de batalla (no disponible aquí directamente)
                    # Se pasa como atributo del fighter si se cargó al crear
                    su_bonus = attacker.get("skill_upgrades", {}).get(str(real_skill_idx), 0)
                else:
                    su_bonus = 0
            except Exception:
                su_bonus = 0

            # Aplicar buff de ATK temporal si existe (Carga Estelar de Alex)
            bonus_atk = attacker.pop("atk_buff", 0)
            # Bonus si el defensor está enredado
            entangle_bonus = 15 if defender.get("entangled") else 0
            effective_atk = attacker["atk"] + bonus_atk + entangle_bonus
            dmg = battle.calc_damage(effective_atk, defender["defense"], skill["power"] + su_bonus)
            # ── Variante: efectos en ataque ──────────────────────────────
            dmg = apply_variant_on_attack(attacker, defender, dmg, battle, battle.log)
            dmg = apply_color_multiplier_to_dmg(dmg, attacker, defender, battle.log)
            # Apple Armor: reduce el daño recibido
            if defender.get("apple_armor_turns", 0) > 0:
                reduction = defender.get("apple_armor_reduction", 0.5)
                dmg = max(1, int(dmg * reduction))
                defender["apple_armor_turns"] -= 1
                battle.log.append(f"   🍎🛡️ **Apple Armor** absorbe el golpe! (daño reducido al {int(reduction*100)}%, quedan {defender['apple_armor_turns']} turnos)")
            dmg = apply_variant_on_defense(defender, attacker, dmg, battle, battle.log)
            defender["hp"] = max(0, defender["hp"] - dmg)
            buff_txt = f" (⭐+{bonus_atk} ATK)" if bonus_atk else ""
            battle.log.append(f"⚔️ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**{buff_txt} → **{dmg}** daño!")
            battle.log.append(f"   _{skill['desc']}_")
            # revive_poisoner: figura revivida por 1x envenena al atacar
            if attacker.get("revive_poisoner"):
                if "dots" not in defender: defender["dots"] = []
                defender["dots"].append({"dmg": 6, "turns": 3})
                battle.log.append(f"   ☠️ ¡**{attacker['name']}** (revivida) envenena a **{defender['name']}**! (6 daño/turno x3)")

            # self_heal: Caine se cura al hacer daño
            if skill.get("self_heal") and not attacker.get("no_heal"):
                heal_amt = skill["self_heal"]
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amt)
                battle.log.append(f"   💚 **{attacker['name']}** se cura **{heal_amt}** HP!")

            # ¿El defensor está en parry o retribución? → contraataca
            if defender.get("retributing"):
                retrib_dmg = max(1, dmg // 2)
                attacker["hp"] = max(0, attacker["hp"] - retrib_dmg)
                defender["retrib_turns"] = defender.get("retrib_turns", 1) - 1
                if defender["retrib_turns"] <= 0:
                    defender["retributing"] = False
                battle.log.append(f"   🦷 **{defender['emoji']} {defender['name']}** devuelve **{retrib_dmg}** daño (¡Retribución!)!")

            if defender.get("parrying"):
                defender["parrying"] = False
                if defender.get("parry_return_half"):
                    defender.pop("parry_return_half", None)
                    counter_dmg = max(1, dmg // 2)
                    attacker["hp"] = max(0, attacker["hp"] - counter_dmg)
                    battle.log.append(f"   🦊 **{defender['emoji']} {defender['name']}** hace **COUNTER** y devuelve **{counter_dmg}** daño (mitad del recibido)!")
                elif defender.get("parry_flat_bonus") is not None:
                    counter_dmg = max(1, dmg + defender["parry_flat_bonus"])
                    defender.pop("parry_flat_bonus", None)
                    attacker["hp"] = max(0, attacker["hp"] - counter_dmg)
                    battle.log.append(f"   ⚡ **{defender['emoji']} {defender['name']}** hace **PARRY** y devuelve **{counter_dmg}** daño (tu daño +10)!")
                else:
                    pct = defender.get("parry_dmg_pct", 25)
                    counter_dmg = int(defender["max_hp"] * pct / 100)
                    attacker["hp"] = max(0, attacker["hp"] - counter_dmg)
                    battle.log.append(f"   ⚡ **{defender['emoji']} {defender['name']}** hace **COUNTER** y devuelve **{counter_dmg}** daño ({pct}% HP)!")

            # Entangle: la figura queda enredada (aliados le hacen más daño)
            if skill.get("entangle"):
                defender["entangled"] = True
                battle.log.append(f"   🕸️ ¡**{defender['name']}** queda enredado! Los aliados le harán +15 daño!")

            # Efecto stun (con soporte de stun_turns extendido)
            if skill.get("stun") and not defender.get("stun_immune"):
                stun_t = skill.get("stun_turns", 1)
                if stun_t > 1:
                    defender["stun_turns"] = stun_t
                    battle.log.append(f"   😵 ¡**{defender['name']}** queda aturdido {stun_t} turnos!")
                else:
                    defender["stunned"] = True
                    battle.log.append(f"   😵 ¡**{defender['name']}** queda aturdido 1 turno!")

            # Ryu: cualquier skill normal le llena la barra SUPER
            if attacker.get("key") == "ryu" and not skill.get("super_move"):
                attacker["super_bar"] = min(100, attacker.get("super_bar", 0) + 25)
                battle.log.append(f"   ⚡ SUPER de Ryu: **{attacker['super_bar']}%**")

            # Dot inline (Mass Infection de 1x1x1x1)
            if skill.get("dot"):
                if "dots" not in defender: defender["dots"] = []
                defender["dots"].append({"dmg": skill.get("dot_power", 8), "turns": skill.get("dot_turns", 4)})
                battle.log.append(f"   ☠️ ¡**{defender['name']}** infectado! ({skill.get('dot_power',8)} daño/turno x{skill.get('dot_turns',4)})")

            # Efecto AOE — daña a todo el equipo rival
            if skill.get("aoe"):
                def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                sec_power = skill.get("aoe_secondary_power", skill["power"])
                hit = []
                for fig in def_team:
                    if fig is not defender and fig["hp"] > 0:
                        sec_dmg = battle.calc_damage(attacker["atk"], fig["defense"], sec_power)
                        fig["hp"] = max(0, fig["hp"] - sec_dmg)
                        hit.append(f"{fig['emoji']} {fig['name']} -{sec_dmg}HP")
                if hit:
                    battle.log.append(f"   💥 AOE: {' | '.join(hit)}")

            # Efecto force_switch — bloquea la figura golpeada N turnos
            if skill.get("force_switch"):
                turns = skill.get("force_switch_turns", 3)
                def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                for fig in def_team:
                    if fig is defender:
                        fig["force_locked"] = turns
                        break
                # Forzar cambio al siguiente disponible no bloqueado
                def_idx_attr = "p2_active" if battle.turn == 1 else "p1_active"
                current_idx = getattr(battle, def_idx_attr)
                for i, fig in enumerate(def_team):
                    if fig["hp"] > 0 and not fig.get("force_locked", 0) > 0 and i != current_idx:
                        setattr(battle, def_idx_attr, i)
                        battle.log.append(f"   🔒 ¡**{defender['name']}** bloqueada {turns} turnos! Entra **{fig['emoji']} {fig['name']}**!")
                        break
                else:
                    battle.log.append(f"   🔒 ¡**{defender['name']}** bloqueada {turns} turnos!")

            # bar_drain — drena energía del oponente (Cannon Arm)
            if skill.get("bar_drain"):
                drain_amt = skill["bar_drain"]
                defender["energy"] = max(0, defender.get("energy", 0) - drain_amt)
                battle.log.append(f"   ⚡ ¡La barra de energía de **{defender['name']}** se redujo **{drain_amt}⚡**!")

            # def_debuff — baja defensa permanente (Spaghetti!)
            if skill.get("def_debuff"):
                dd = skill["def_debuff"]
                defender["defense"] = max(0, defender.get("defense", 0) - dd)
                battle.log.append(f"   🛡️ {defender['name']} pierde **{dd}** de defensa permanentemente!")

            # team_atk_buff inline en damage (Chaos Control)
            if skill.get("team_atk_buff"):
                buff_val = skill["team_atk_buff"]
                for ally in atk_team:
                    if ally["hp"] > 0:
                        ally["atk"] = ally.get("atk", 0) + buff_val
                battle.log.append(f"   ⭐ ¡Todas las figuras aliadas ganan +{buff_val} ATK permanente!")
            # Respetar no_heal
            if attacker.get("no_heal"):
                battle.log.append(f"❌ **{attacker['name']}** no puede recuperar vida hasta el fin de la batalla!")
            else:
                heal = int(skill["power"] + random.randint(-2, 5))
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal)
                battle.log.append(f"💚 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → +**{heal}** HP!")
            # Curación a compañeros
            if skill.get("team_heal"):
                t_heal = skill.get("team_heal_power", 10)
                healed = []
                for ally in atk_team:
                    if ally is not attacker and ally["hp"] > 0:
                        ally["hp"] = min(ally["max_hp"], ally["hp"] + t_heal)
                        healed.append(f"{ally['emoji']} {ally['name']} +{t_heal}HP")
                if healed:
                    battle.log.append(f"   💚 Compañeros curados: {', '.join(healed)}")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "drain":
            self_dmg = skill["power"]
            bar_bonus = skill.get("bar_bonus", 20)
            attacker["hp"] = max(1, attacker["hp"] - self_dmg)
            attacker["energy"] = min(ENERGY_MAX, attacker["energy"] + bar_bonus)
            battle.log.append(f"⚡ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   -{self_dmg} HP propio | +{bar_bonus}⚡ extra! _{skill['desc']}_")

        elif stype == "drain_fill":
            self_dmg = skill["power"]
            enemy_dmg = skill.get("dmg_enemy", 0)
            attacker["hp"] = max(1, attacker["hp"] - self_dmg)
            if skill.get("no_heal"):
                attacker["no_heal"] = True
            if skill.get("fill_bar"):
                attacker["energy"] = ENERGY_MAX
            if enemy_dmg > 0:
                defender["hp"] = max(0, defender["hp"] - enemy_dmg)
            battle.log.append(f"🔴 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   -{self_dmg} HP propio (¡irrecuperable!) | -{enemy_dmg} al rival | ¡Barra al máximo!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "team_atk_buff":
            # Heroic Pose — buff de ATK acumulable al equipo completo
            buff = skill.get("atk_buff", 15)
            for ally in atk_team:
                if ally["hp"] > 0:
                    ally["atk_buff"] = ally.get("atk_buff", 0) + buff
            battle.log.append(f"⭐ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   Todo el equipo gana +{buff} ATK (acumulable, se consume al atacar)!")
            battle.log.append(f"   _{skill['desc']}_")

        # ═══════════════════════════════════════════════════════════════════
        # RYU — Habilidades especiales
        # ═══════════════════════════════════════════════════════════════════

        elif stype == "hadouken":
            # Timing minigame: the View adds a button that the player must press
            # quickly. If already resolved (stored in battle.hadouken_hit), use it.
            # If not resolved yet, default to normal Hadouken.
            hit_timing = battle.__dict__.pop("hadouken_hit", None)
            if hit_timing:
                # FIRE HADOUKEN
                dmg = battle.calc_damage(effective_atk, defender["defense"], skill["fire_power"])
                dmg = apply_variant_on_attack(attacker, defender, dmg, battle, battle.log)
                dmg = apply_color_multiplier_to_dmg(dmg, attacker, defender, battle.log)
                dmg = apply_variant_on_defense(defender, attacker, dmg, battle, battle.log)
                defender["hp"] = max(0, defender["hp"] - dmg)
                defender["burning"]       = True
                defender["burning_turns"] = max(defender.get("burning_turns", 0), 2)
                battle.log.append(f"   🔥 **FIRE HADOUKEN!** {dmg} daño + burning 2T!")
            else:
                # Hadouken normal
                dmg = battle.calc_damage(effective_atk, defender["defense"], skill["power"])
                dmg = apply_variant_on_attack(attacker, defender, dmg, battle, battle.log)
                dmg = apply_color_multiplier_to_dmg(dmg, attacker, defender, battle.log)
                dmg = apply_variant_on_defense(defender, attacker, dmg, battle, battle.log)
                defender["hp"] = max(0, defender["hp"] - dmg)
                battle.log.append(f"   👊 Hadouken! {dmg} daño.")
            # Tick SUPER bar
            attacker["super_bar"] = min(100, attacker.get("super_bar", 0) + 25)
            battle.log.append(f"   ⚡ SUPER: **{attacker['super_bar']}%**")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "shin_hadoken":
            # Only usable when super_bar >= 100
            if attacker.get("super_bar", 0) < 100:
                # Refund energy, don't execute
                attacker["energy"] = min(ENERGY_MAX, attacker["energy"] + skill["cost"])
                battle.log.append(f"   ❌ Shin-Hadoken requiere la barra SUPER al 100%!")
                await finish_turn(interaction, battle, channel_id)
                return
            attacker["super_bar"] = 0
            # Main target
            dmg = battle.calc_damage(effective_atk, defender["defense"], skill["power"])
            dmg = apply_variant_on_attack(attacker, defender, dmg, battle, battle.log)
            dmg = apply_color_multiplier_to_dmg(dmg, attacker, defender, battle.log)
            dmg = apply_variant_on_defense(defender, attacker, dmg, battle, battle.log)
            defender["hp"] = max(0, defender["hp"] - dmg)
            battle.log.append(f"   🔱 **SHIN-HADOKEN!!** {dmg} daño a {defender['name']}!")
            # AOE to other enemy figures
            aoe_power = skill.get("aoe_secondary_power", 40)
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            for fig in def_team:
                if fig is not defender and fig["hp"] > 0:
                    sd = battle.calc_damage(effective_atk, fig["defense"], aoe_power)
                    fig["hp"] = max(0, fig["hp"] - sd)
                    battle.log.append(f"   💥 AOE Shin-Hadoken → {fig['name']} -{sd}HP!")
            # Ryu stuns himself
            attacker["stun_turns"] = skill.get("stun_turns", 2)
            battle.log.append(f"   😵 Ryu queda stunned {attacker['stun_turns']} turnos por el esfuerzo.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "tatsumaki":
            # DOT skill — opponent gets a memory minigame to cancel it
            # If battle.tatsumaki_cancelled is set, Ryu gets stunned instead
            cancelled = battle.__dict__.pop("tatsumaki_cancelled", False)
            if cancelled:
                attacker["stun_turns"] = 3
                battle.log.append(f"   ❌ El oponente completó el minijuego de memoria!")
                battle.log.append(f"   😵 **{attacker['name']}** queda stunned 3 turnos!")
            else:
                if "dots" not in defender:
                    defender["dots"] = []
                defender["dots"].append({"dmg": skill["power"], "turns": skill.get("dot_turns", 3)})
                battle.log.append(
                    f"   🌀 **Tatsumaki Senpuu Kyaku!** "
                    f"{skill['power']} daño/turno × {skill.get('dot_turns',3)}T!"
                )
            # Tick SUPER bar
            attacker["super_bar"] = min(100, attacker.get("super_bar", 0) + 30)
            battle.log.append(f"   ⚡ SUPER: **{attacker['super_bar']}%**")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "dot":
            # Throwable Bomb — daño por turnos acumulable
            dot_dmg = skill["power"]
            dot_turns = skill.get("dot_turns", 3)
            if "dots" not in defender:
                defender["dots"] = []
            defender["dots"].append({"dmg": dot_dmg, "turns": dot_turns})
            battle.log.append(f"💣 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   ¡{dot_dmg} de daño por turno durante {dot_turns} turnos! (¡Acumulable!)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "bad_update":
            # Roblox — daño aleatorio a enemigos + cura aliados
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            dmg_roll = random.choice([4, 6, 8])
            heal_roll = dmg_roll // 2
            dmg_hits = []
            for fig in def_team:
                if fig["hp"] > 0:
                    fig["hp"] = max(0, fig["hp"] - dmg_roll)
                    dmg_hits.append(f"{fig['emoji']} -{dmg_roll}HP")
            heal_hits = []
            for ally in atk_team:
                if ally["hp"] > 0 and not ally.get("no_heal"):
                    ally["hp"] = min(ally["max_hp"], ally["hp"] + heal_roll)
                    heal_hits.append(f"{ally['emoji']} +{heal_roll}HP")
            battle.log.append(f"🔳 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** (daño: {dmg_roll})!")
            if dmg_hits: battle.log.append(f"   💥 Enemigos: {' | '.join(dmg_hits)}")
            if heal_hits: battle.log.append(f"   💚 Aliados: {' | '.join(heal_hits)}")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "fly_away":
            # Tails — bloquea a Tails y al rival 3 turnos, entran sustitutos
            turns = skill.get("fly_turns", 3)
            attacker["force_locked"] = turns
            defender["force_locked"] = turns
            battle.log.append(f"🦊 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   ✈️ ¡**{attacker['name']}** y **{defender['name']}** vuelan lejos {turns} turnos!")
            # Forzar cambio de figura del atacante
            atk_idx_attr = "p1_active" if battle.turn == 1 else "p2_active"
            cur_atk_idx = getattr(battle, atk_idx_attr)
            next_atk = battle.next_alive(atk_team, cur_atk_idx)
            if next_atk is not None:
                setattr(battle, atk_idx_attr, next_atk)
                new_atk = atk_team[next_atk]
                battle.log.append(f"   🔄 Entra **{new_atk['emoji']} {new_atk['name']}** por tu equipo!")
            # Forzar cambio de figura del defensor
            def_team_fw = battle.p2_team if battle.turn == 1 else battle.p1_team
            def_idx_attr_fw = "p2_active" if battle.turn == 1 else "p1_active"
            cur_def_idx = getattr(battle, def_idx_attr_fw)
            next_def = battle.next_alive(def_team_fw, cur_def_idx)
            if next_def is not None:
                setattr(battle, def_idx_attr_fw, next_def)
                new_def = def_team_fw[next_def]
                battle.log.append(f"   🔄 Entra **{new_def['emoji']} {new_def['name']}** por el equipo rival!")
            elif battle.next_alive(def_team_fw, -1) is None:
                # Todo el equipo rival bloqueado = victoria
                await end_battle(interaction, battle, channel_id, winner_turn=battle.turn)
                return

        elif stype == "retribution":
            # Caine — Retributional Ringmaster: devuelve mitad del daño recibido 1 turno
            attacker["retributing"] = True
            attacker["retrib_turns"] = skill.get("retrib_turns", 1)
            battle.log.append(f"🦷 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   ¡Caine está listo para devolver la mitad del daño que reciba!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "michi_counter":
            # MichiBug — Counter: devuelve mitad del daño, 20% de que el rival no ataque
            evade = skill.get("evade_chance", 20)
            if random.randint(1, 100) <= evade:
                # El rival pierde su turno
                defender["stunned"] = True
                battle.log.append(f"🦊 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
                battle.log.append(f"   ✨ ¡**{defender['name']}** ni siquiera llega a atacar! Pierde su turno.")
            else:
                # Funciona como parry normal: devuelve mitad del daño del rival
                attacker["parrying"] = True
                attacker["parry_return_half"] = True   # flag especial: devuelve mitad del dmg recibido
                battle.log.append(f"🦊 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** y espera el ataque...")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "glitch_dmg":
            # MichiBug — Glitch Manipulation: daño aleatorio 2-45
            lo = skill.get("min_dmg", 2)
            hi = skill.get("max_dmg", 45)
            raw_dmg = random.randint(lo, hi)
            dmg = max(1, raw_dmg - (defender["defense"] // 4))
            defender["hp"] = max(0, defender["hp"] - dmg)
            battle.log.append(f"🌀 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → **{dmg}** daño! (roll: {raw_dmg})")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "corruption":
            # MichiBug — Corruption: copia habilidad aleatoria de cualquier figura
            all_skills = [(fig_key, sk) for fig_key, skills in FIGURE_SKILLS.items()
                          for sk in skills
                          if sk["type"] not in ("corruption",)]  # no puede copiarse a sí misma
            if all_skills:
                copied_fig_key, copied_skill = random.choice(all_skills)
                copied_fig_name = FIGURES.get(copied_fig_key, {}).get("name", copied_fig_key)
                battle.log.append(f"🌑 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
                battle.log.append(f"   ✨ ¡Copia **{copied_skill['name']}** de **{copied_fig_name}**!")
                # Ejecutar la habilidad copiada (recursión controlada)
                fake_skill = copied_skill.copy()
                # Reutilizar la lógica ejecutando inline el tipo copiado
                cstype = fake_skill["type"]
                if cstype == "damage":
                    dmg = battle.calc_damage(attacker["atk"], defender["defense"], fake_skill.get("power", 20))
                    defender["hp"] = max(0, defender["hp"] - dmg)
                    battle.log.append(f"   ⚔️ Daño copiado: **{dmg}**!")
                    if fake_skill.get("aoe"):
                        def_team_c = battle.p2_team if battle.turn == 1 else battle.p1_team
                        sec = fake_skill.get("aoe_secondary_power", fake_skill.get("power", 10))
                        for fig in def_team_c:
                            if fig is not defender and fig["hp"] > 0:
                                sd = battle.calc_damage(attacker["atk"], fig["defense"], sec)
                                fig["hp"] = max(0, fig["hp"] - sd)
                                battle.log.append(f"   💥 AOE → {fig['emoji']} -{sd}HP")
                elif cstype == "heal":
                    if not attacker.get("no_heal"):
                        heal = max(1, int(fake_skill.get("power", 20) + random.randint(-3, 5)))
                        attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal)
                        battle.log.append(f"   💚 Curación copiada: +**{heal}** HP!")
                elif cstype == "dot":
                    if "dots" not in defender: defender["dots"] = []
                    defender["dots"].append({"dmg": fake_skill.get("power", 10), "turns": fake_skill.get("dot_turns", 3)})
                    battle.log.append(f"   💣 DOT copiado: {fake_skill.get('power',10)} daño/turno x{fake_skill.get('dot_turns',3)}")
                elif cstype == "team_atk_buff":
                    buff = fake_skill.get("atk_buff", 10)
                    for ally in atk_team:
                        if ally["hp"] > 0:
                            ally["atk_buff"] = ally.get("atk_buff", 0) + buff
                    battle.log.append(f"   ⭐ Buff copiado: +{buff} ATK al equipo!")
                elif cstype == "drain_fill":
                    f_dmg = fake_skill.get("power", 15)
                    attacker["hp"] = max(1, attacker["hp"] - f_dmg)
                    if fake_skill.get("fill_bar"): attacker["energy"] = ENERGY_MAX
                    e_dmg = fake_skill.get("dmg_enemy", 0)
                    if e_dmg: defender["hp"] = max(0, defender["hp"] - e_dmg)
                    battle.log.append(f"   🔴 Drain copiado: -{f_dmg}HP propio, -{e_dmg} al rival!")
                elif cstype == "glitch_dmg":
                    raw = random.randint(fake_skill.get("min_dmg",2), fake_skill.get("max_dmg",45))
                    dmg = max(1, raw - (defender["defense"] // 4))
                    defender["hp"] = max(0, defender["hp"] - dmg)
                    battle.log.append(f"   🌀 Glitch copiado: **{dmg}** daño!")
                elif cstype == "bad_update":
                    dr = random.choice([4, 6, 8])
                    hr = dr // 2
                    def_team_c = battle.p2_team if battle.turn == 1 else battle.p1_team
                    for fig in def_team_c:
                        if fig["hp"] > 0: fig["hp"] = max(0, fig["hp"] - dr)
                    for ally in atk_team:
                        if ally["hp"] > 0 and not ally.get("no_heal"):
                            ally["hp"] = min(ally["max_hp"], ally["hp"] + hr)
                    battle.log.append(f"   🔳 Bad Update copiado: -{dr} a todos los rivales, +{hr} a aliados!")
                else:
                    # Para tipos complejos o raros, hace daño básico
                    dmg = max(1, attacker["atk"] - (defender["defense"] // 4) + random.randint(-2, 5))
                    defender["hp"] = max(0, defender["hp"] - dmg)
                    battle.log.append(f"   ⚔️ Efecto copiado (daño base): **{dmg}**!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "fast_kill":
            # Requiere 3 usos seguidos — al 3ro dispara
            charges = attacker.get("fast_kill_charges", 0) + 1
            needed = skill.get("charges_needed", 3)
            attacker["fast_kill_charges"] = charges
            if charges >= needed:
                attacker["fast_kill_charges"] = 0
                dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
                defender["hp"] = max(0, defender["hp"] - dmg)
                battle.log.append(f"🔪 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → ¡**{dmg}** DAÑO MASIVO!")
                battle.log.append(f"   _{skill['desc']}_")
            else:
                remaining = needed - charges
                battle.log.append(f"🔪 **{attacker['emoji']} {attacker['name']}** prepara **{skill['name']}**... ({charges}/{needed})")
                battle.log.append(f"   ¡{remaining} turno(s) más para activar!")

        elif stype == "revive_team":
            # 1x1x1x1 — se daña a sí mismo y revive figuras aliadas caídas
            self_dmg = skill["power"]
            attacker["hp"] = max(1, attacker["hp"] - self_dmg)
            revive_hp  = skill.get("revive_hp", 20)
            revive_atk = skill.get("revive_atk", 10)
            revive_def = skill.get("revive_def", 15)
            revived = []
            for ally in atk_team:
                if ally["hp"] <= 0 and ally is not attacker:
                    ally["hp"] = revive_hp
                    ally["atk"] = revive_atk
                    ally["defense"] = revive_def
                    ally["energy"] = 0
                    if skill.get("revive_poison"):
                        ally["revive_poisoner"] = True  # envenena al atacar
                    revived.append(f"{ally['emoji']} {ally['name']}")
            battle.log.append(f"⚔️ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** (-{self_dmg} HP propio)!")
            if revived:
                battle.log.append(f"   💀➡️💚 ¡Reviven: {', '.join(revived)}! (HP:{revive_hp} ATK:{revive_atk} DEF:{revive_def})")
                battle.log.append(f"   ☠️ ¡Las figuras revividas envenenarán al atacar!")
            else:
                battle.log.append(f"   No había figuras caídas que revivir.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "heal_self_small":
            # Shedletsky — Chicken Leg: cura solo a sí mismo 20-25 HP
            heal_amt = random.randint(skill.get("heal_min", 20), skill.get("heal_max", 25))
            if not attacker.get("no_heal"):
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amt)
            battle.log.append(f"🍗 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   💚 {attacker['name']} se cura +{heal_amt}HP")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "heal_team_self":
            # Shedletsky — Chicken Legs: +30 propio, +25 aliados
            self_heal = skill["power"]
            team_heal = skill.get("team_heal_power", 25)
            if not attacker.get("no_heal"):
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + self_heal)
            healed = []
            for ally in atk_team:
                if ally is not attacker and ally["hp"] > 0 and not ally.get("no_heal"):
                    ally["hp"] = min(ally["max_hp"], ally["hp"] + team_heal)
                    healed.append(f"{ally['emoji']} {ally['name']} +{team_heal}HP")
            battle.log.append(f"🍗 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   💚 {attacker['name']} +{self_heal}HP | {' | '.join(healed) if healed else 'sin aliados vivos'}")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "switch_sword":
            # Shedletsky — muestra menú de espadas (se maneja en get_battle_view)
            # Este tipo no hace nada directamente — la selección se hace via botón especial
            battle.log.append(f"🐔 **{attacker['emoji']} {attacker['name']}** guarda su espada actual...")
            battle.log.append(f"   _(Elige tu espada en el menú)_")

        elif stype == "slash":
            # Shedletsky — ataca con la espada activa y aplica su efecto
            sword = attacker.get("active_sword", "linked")
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
            SWORD_NAMES = {
                "linked":      "Linked Sword",
                "firebrand":   "Firebrand 🔥",
                "venomshank":  "Venomshank ☠️",
                "windforce":   "Windforce 🌪️",
                "darkheart":   "Darkheart 🖤",
                "illumina":    "Illumina ✨",
                "ghostwalker": "Ghostwalker 👻",
                "ice_dagger":  "Ice Dagger 🧊",
            }
            sword_name = SWORD_NAMES.get(sword, "Linked Sword")
            defender["hp"] = max(0, defender["hp"] - dmg)
            battle.log.append(f"⚔️ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** con {sword_name} → **{dmg}** daño!")

            # Efectos de espada
            if sword == "linked":
                pass  # sin efecto extra
            elif sword == "firebrand":
                attacker["fire_immune"] = True
                # Carga de fuego: daño extra al lanzarse
                dash_dmg = battle.calc_damage(attacker["atk"], defender["defense"], 20)
                defender["hp"] = max(0, defender["hp"] - dash_dmg)
                battle.log.append(f"   🔥 ¡{attacker['name']} se lanza con Firebrand! +{dash_dmg} daño extra!")
                battle.log.append(f"   🔥 ¡{attacker['name']} es inmune a Ice Dagger!")
                # Si Shedletsky tiene menos del 30% HP → +30 ATK a aliados
                hp_pct = attacker["hp"] / attacker["max_hp"]
                if hp_pct < 0.30:
                    for ally in atk_team:
                        if ally is not attacker and ally["hp"] > 0:
                            ally["atk_buff"] = ally.get("atk_buff", 0) + 30
                    battle.log.append(f"   🔥 ¡Shedletsky a baja vida! +30 ATK a todos los aliados!")
            elif sword == "venomshank":
                if "dots" not in defender: defender["dots"] = []
                defender["dots"].append({"dmg": 8, "turns": 3})
                battle.log.append(f"   ☠️ ¡{defender['name']} envenenado! (8 daño/turno x3)")
            elif sword == "windforce":
                defender["stunned"] = True
                battle.log.append(f"   🌪️ ¡{defender['name']} empujado y aturdido 1 turno!")
            elif sword == "darkheart":
                lifesteal = max(1, int(dmg * 0.4))
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + lifesteal)
                battle.log.append(f"   🖤 Robo de vida: +{lifesteal} HP a {attacker['name']}!")
            elif sword == "illumina":
                illumina_dmg = battle.calc_damage(attacker["atk"], defender["defense"], 80)
                defender["hp"] = max(0, defender["hp"] - illumina_dmg)
                battle.log.append(f"   ✨ ¡Illumina hace daño masivo adicional! -{illumina_dmg} HP!")
            elif sword == "ghostwalker":
                kills = attacker.get("ghostwalker_kills", 0)
                bonus = kills * 5
                attacker["atk"] = attacker["atk"] + bonus if bonus > 0 else attacker["atk"]
                battle.log.append(f"   👻 Ghostwalker: +{bonus} ATK acumulado ({kills} kills)")
            elif sword == "ice_dagger":
                if not defender.get("fire_immune"):
                    ice_charges = attacker.get("ice_dagger_charges", 0) + 1
                    attacker["ice_dagger_charges"] = ice_charges
                    if ice_charges >= 3:
                        attacker["ice_dagger_charges"] = 0
                        ice_dmg = 120  # daño fijo al 3er toque
                        defender["hp"] = max(0, defender["hp"] - ice_dmg)
                        battle.log.append(f"   🧊❄️ ¡ICE DAGGER CARGADA! **{ice_dmg}** daño masivo de hielo!")
                    else:
                        battle.log.append(f"   🧊 Ice Dagger cargando... ({ice_charges}/3 — mantén la espada equipada!)")
                else:
                    attacker["ice_dagger_charges"] = 0
                    battle.log.append(f"   🧊 Ice Dagger bloqueada por Firebrand!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "consumed_fury":
            # 50 daño al activo + 15 splash + impostor pierde 50% vida
            dmg_fury = 50
            defender["hp"] = max(0, defender["hp"] - dmg_fury)
            def_team_fury = battle.p2_team if battle.turn == 1 else battle.p1_team
            splash = skill.get("splash_dmg", 15)
            hit = []
            for fig in def_team_fury:
                if fig is not defender and fig["hp"] > 0:
                    fig["hp"] = max(0, fig["hp"] - splash)
                    hit.append(f"{fig['emoji']} {fig['name']} -{splash}HP")
            # El impostor pierde 50% de su vida en lugar de morir
            self_dmg = max(1, attacker["max_hp"] // 2)
            attacker["hp"] = max(1, attacker["hp"] - self_dmg)
            battle.log.append(f"💥 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   💥 **{defender['name']}** recibe **{dmg_fury}** daño!")
            if hit:
                battle.log.append(f"   💥 Explosión: {' | '.join(hit)}")
            battle.log.append(f"   😵 **{attacker['name']}** pierde el 50% de su vida por la explosión!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "holy_buff":
            # Santa Vaca — evoluciona con DEF y ATK masivos
            attacker["defense"] = attacker.get("defense", 0) + skill.get("def_buff", 10000000000)
            attacker["atk"]     = attacker.get("atk", 0) + skill.get("atk_buff_holy", 1000000)
            attacker["holy_turns"] = skill.get("holy_turns", 20)
            battle.log.append(f"🐮 **SANTA VACA** usa **{skill['name']}**!")
            battle.log.append(f"   ¡LA VACA HA EVOLUCIONADO! +10B DEF | +1M ATK por 20 turnos! 🌟")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "holy_heal":
            # Santa Vaca — cura cantidad absurda a todo el equipo
            heal_amt = skill.get("heal_all", 10000000000000)
            for ally in atk_team:
                if ally["hp"] > 0:
                    ally["hp"] = min(ally["max_hp"], ally["hp"] + heal_amt)
            battle.log.append(f"🐮 **SANTA VACA** usa **{skill['name']}**!")
            battle.log.append(f"   🥩 Se arranca un trozo de sí misma... ¡y todo el equipo recibe {heal_amt:,} HP!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "holy_nuke":
            # Santa Vaca — mata a TODAS las figuras enemigas
            def_team_holy = battle.p2_team if battle.turn == 1 else battle.p1_team
            killed = []
            for fig in def_team_holy:
                if fig["hp"] > 0:
                    fig["hp"] = 0
                    killed.append(f"{fig['emoji']} {fig['name']}")
            battle.log.append(f"🐮 **SANTA VACA** usa **{skill['name']}**...")
            battle.log.append(f"   ...")
            battle.log.append(f"   💀 **{', '.join(killed)}** {'han sido' if len(killed)>1 else 'ha sido'} aniquilado(s) instantáneamente.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "lobster":
            # 0.01% de probabilidad de matar a TODAS las figuras del oponente
            roll = random.randint(1, 10000)
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            if roll == 1:
                for fig in def_team:
                    fig["hp"] = 0
                battle.log.append(f"🦞 **Lobster** usa **LOBSTER**...")
                battle.log.append(f"   ...")
                battle.log.append(f"   🦞 **¡LA LANGOSTA LO HA HECHO! ¡TODAS LAS FIGURAS ENEMIGAS ESTÁN MUERTAS!** 🦞")
            else:
                battle.log.append(f"🦞 **Lobster** usa **LOBSTER**...")
                battle.log.append(f"   ...")
                battle.log.append(f"   No pasa nada. (Como siempre)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "ban_hammer":
            # Roblox — 50/50: mata al enemigo activo O a un aliado
            roll = random.randint(1, 2)
            if roll == 1:
                defender["hp"] = 0
                battle.log.append(f"🔨 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
                battle.log.append(f"   💀 ¡**{defender['name']}** fue BANEADO! HP = 0!")
            else:
                alive_allies = [f for f in atk_team if f["hp"] > 0 and f is not attacker]
                if alive_allies:
                    victim = random.choice(alive_allies)
                    victim["hp"] = 0
                    battle.log.append(f"🔨 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**...")
                    battle.log.append(f"   💀 ¡El martillo se fue de lado y mató a **{victim['name']}** aliado! 😂")
                else:
                    # Solo queda Roblox — se auto-daña 40 HP
                    attacker["hp"] = max(1, attacker["hp"] - 40)
                    battle.log.append(f"🔨 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**...")
                    battle.log.append(f"   💥 ¡El martillo rebota contra sí mismo! **-40 HP** a Roblox!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "parry":
            # Alex — contraataca si el rival ataca en su siguiente turno
            attacker["parrying"] = True
            if "parry_flat_bonus" in skill:
                attacker["parry_flat_bonus"] = skill["parry_flat_bonus"]
                attacker.pop("parry_dmg_pct", None)
            else:
                attacker["parry_dmg_pct"] = skill.get("parry_dmg_pct", 25)
            battle.log.append(f"🛡️ **{attacker['emoji']} {attacker['name']}** se prepara para un **Parry**!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "buff":
            # Alex — Carga Estelar: potencia el próximo ataque
            attacker["atk_buff"] = skill.get("atk_buff", 15)
            battle.log.append(f"⭐ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   Su próximo ataque tendrá +{skill.get('atk_buff',15)} ATK!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "agus_fumada":
            # Nuevo Fumada: HP cambia a valor aleatorio entre hp_min y hp_max
            hp_min = skill.get("hp_min", 100)
            hp_max = skill.get("hp_max", 200)
            new_hp = random.randint(hp_min, hp_max)
            attacker["max_hp"] = max(attacker["max_hp"], new_hp)
            attacker["hp"] = new_hp
            if new_hp >= attacker["max_hp"] * 0.7:
                battle.log.append(f"💨 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**... UFF QUE GOD 🌿")
                battle.log.append(f"   ¡HP cambia a **{new_hp}**! (rango: {hp_min}-{hp_max})")
            else:
                battle.log.append(f"💨 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**... no era tan bueno 😵")
                battle.log.append(f"   HP cambia a **{new_hp}**... (rango: {hp_min}-{hp_max})")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "agus_mechero":
            # Mechero: 40% al rival, 40% a Agus, 20% ambos
            burn_dmg   = skill.get("burn_dmg", 20)
            burn_turns = skill.get("burn_turns", 4)
            roll = random.randint(1, 100)
            battle.log.append(f"🔥 **{attacker['emoji']} {attacker['name']}** saca el **{skill['name']}**...")

            def apply_burn(target, dmg, turns):
                target["hp"] = max(0, target["hp"] - dmg)
                if "dots" not in target: target["dots"] = []
                target["dots"].append({"dmg": turns, "turns": turns})
                battle.log.append(f"   🔥 **{target['name']}** recibe {dmg} daño y burning {turns} turnos!")

            if roll <= 40:
                apply_burn(defender, burn_dmg, burn_turns)
                battle.log.append(f"   ¡Le prendió fuego al rival! (40%)")
            elif roll <= 80:
                apply_burn(attacker, burn_dmg, burn_turns)
                battle.log.append(f"   ¡Se quemó a sí mismo! (40%)")
            else:
                apply_burn(defender, burn_dmg, burn_turns)
                apply_burn(attacker, burn_dmg, burn_turns)
                battle.log.append(f"   ¡Se quemaron AMBOS! (20%) 💀")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "gamble":
            # Legacy — por si queda alguna referencia
            roll = random.randint(1, 2)
            if roll == 1:
                new_max = skill.get("gamble_heal", 150)
                attacker["max_hp"] = max(attacker["max_hp"], new_max)
                attacker["hp"] = new_max
                battle.log.append(f"🍀 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → ¡SUERTE! HP sube a {new_max}!")
            else:
                attacker["hp"] = 1
                debuff = skill.get("gamble_atk_debuff", 5)
                attacker["atk"] = max(1, attacker["atk"] - debuff)
                battle.log.append(f"💀 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → ¡MAL VIAJE!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "gamble_fire":
            # AgustoLoco — Mechero: <1% de chance
            is_immune = defender.get("fire_immune", False)
            if is_immune:
                battle.log.append(f"🔥 **{attacker['emoji']} {attacker['name']}** intenta el **{skill['name']}**...")
                battle.log.append(f"   ❌ ¡El rival es **inmune al fuego**! No pasa nada.")
            else:
                chance = skill.get("fire_chance", 1)
                roll = random.randint(1, 100)
                if roll <= chance:
                    fire_dmg = skill.get("fire_dmg", 80)
                    defender["hp"] = max(0, defender["hp"] - fire_dmg)
                    battle.log.append(f"🔥🔥🔥 **¡EL MECHERO FUNCIONÓ!** **{attacker['name']}** quema al rival por **{fire_dmg}** daño!")
                else:
                    battle.log.append(f"🔥 **{attacker['emoji']} {attacker['name']}** intenta encender el mechero...")
                    battle.log.append(f"   💨 ...no funciona. (Como siempre)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "clone_switch":
            # 007n7 — cambia tipo de clon
            types = ["def", "atk", "heal"]
            current = attacker.get("clone_type", "def")
            idx = types.index(current)
            nxt = types[(idx + 1) % 3]
            attacker["clone_type"] = nxt
            labels = {"def": "🛡️ DEF (bloquea 2 golpes)", "atk": "⚔️ ATK (parry mitad del daño)", "heal": "💚 HEAL (cura según daño recibido)"}
            battle.log.append(f"🔄 **{attacker['emoji']} {attacker['name']}** cambia tipo de clon → **{labels[nxt]}**!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "clone_action":
            # 007n7 — ejecuta según tipo activo
            ctype = attacker.get("clone_type", "def")
            if ctype == "def":
                attacker["clone_shield"] = 2
                battle.log.append(f"🍔 **{attacker['emoji']} {attacker['name']}** invoca un **Clon DEF**: ¡absorberá los próximos 2 golpes!")
            elif ctype == "atk":
                attacker["parrying"] = True
                attacker["parry_return_half"] = True
                battle.log.append(f"🍔 **{attacker['emoji']} {attacker['name']}** invoca un **Clon ATK**: ¡hará parry devolviendo mitad del daño!")
            elif ctype == "heal":
                attacker["clone_heal_on_hit"] = True
                battle.log.append(f"🍔 **{attacker['emoji']} {attacker['name']}** invoca un **Clon HEAL**: ¡se curará según el daño del próximo golpe!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "teleport_007":
            # 007n7 — se teletransporta, cede turnos, se cura 10/turno
            attacker["teleporting"] = True
            attacker["teleport_heals"] = 10
            battle.log.append(f"🌀 **{attacker['emoji']} {attacker['name']}** se **teletransporta** lejos, cediendo sus turnos!")
            battle.log.append(f"   Se curará 10 HP por turno hasta tener vida completa.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "fling_brick":
            # c00lkidd — daño + reduce ATK rival, 20% fuerza cambio
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
            defender["hp"] = max(0, defender["hp"] - dmg)
            atk_reduction = 5
            defender["atk"] = max(1, defender.get("atk", 10) - atk_reduction)
            battle.log.append(f"🧱 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → **{dmg}** daño! ATK rival -{atk_reduction}!")
            if random.randint(1, 100) <= 20:
                def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                def_idx_attr = "p2_active" if battle.turn == 1 else "p1_active"
                current_idx = getattr(battle, def_idx_attr)
                next_idx = battle.next_alive(def_team, current_idx)
                if next_idx is not None and next_idx != current_idx:
                    setattr(battle, def_idx_attr, next_idx)
                    battle.log.append(f"   💥 ¡El ladrillo manda a volar a **{defender['name']}**! Entra **{def_team[next_idx]['emoji']} {def_team[next_idx]['name']}**!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "minion_shield":
            # c00lkidd — escudo de 2 golpes con contraataque
            attacker["minion_shield"] = 2
            battle.log.append(f"😎 **{attacker['emoji']} {attacker['name']}** invoca sus **Minions**: ¡escudo de 2 golpes!")
            battle.log.append(f"   Si el rival ataca, recibirá 10 daño + quemadura!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "backstab":
            # Two Time — daño + stun + recarga barra
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
            defender["hp"] = max(0, defender["hp"] - dmg)
            battle.log.append(f"🗡️ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → **{dmg}** daño!")
            if not defender.get("stun_immune"):
                defender["stunned"] = True
                battle.log.append(f"   😵 ¡**{defender['name']}** queda aturdido 1 turno!")
            bonus_bar = skill.get("bar_bonus", 20)
            attacker["energy"] = min(100, attacker["energy"] + bonus_bar)
            battle.log.append(f"   ⚡ **{attacker['name']}** recarga +{bonus_bar} energía!")
            # Contar backstabs para pasiva de revive
            attacker["backstab_count"] = attacker.get("backstab_count", 0) + 1
            if attacker.get("spawnpoint_active") and attacker["backstab_count"] >= 4 and attacker["energy"] >= 100:
                attacker["can_revive"] = True
                battle.log.append(f"   ⚡ ¡**{attacker['name']}** ha acumulado 4 backstabs con barra llena! **¡Pasiva de Respawn lista!**")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "spawnpoint":
            # Two Time — coloca punto de respawn
            attacker["spawnpoint_active"] = True
            attacker["backstab_count"] = attacker.get("backstab_count", 0)
            battle.log.append(f"🗡️ **{attacker['emoji']} {attacker['name']}** clava su daga y coloca un **Spawnpoint**!")
            battle.log.append(f"   Pasiva activa: 4 Backstabs con barra llena = revive con 50% HP.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "crouch":
            # Two Time — se agacha: reduce daño recibido, buff ATK 2 turnos
            attacker["crouching"] = True
            attacker["atk_buff"] = attacker.get("atk_buff", 0) + 15
            battle.log.append(f"🗡️ **{attacker['emoji']} {attacker['name']}** se agacha (menos daño recibido este turno, +15 ATK por 2 turnos)!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "voidstar":
            # Noli — daño + prepara próximo ataque para +15
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
            defender["hp"] = max(0, defender["hp"] - dmg)
            attacker["voidstar_charged"] = True
            battle.log.append(f"✨ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → **{dmg}** daño! ¡Próximo ataque +15!")
            # Pasiva de alucinaciones: 20% de que rival falle
            if attacker.get("key") == "noli" or attacker.get("hallucination_aura"):
                defender["hallucinated"] = True
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "voidrush":
            # Noli — daño, +15 si rival tiene alucinaciones
            bonus = 15 if defender.get("hallucinated") else 0
            total_power = skill["power"] + bonus
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], total_power)
            defender["hp"] = max(0, defender["hp"] - dmg)
            bonus_txt = f" (¡+15 Alucinaciones!)" if bonus else ""
            battle.log.append(f"✨ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**{bonus_txt} → **{dmg}** daño!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "observant":
            # Noli — desaparece 5 turnos, genera alucinaciones
            attacker["observant_turns"] = 5
            attacker["observant_dmg_ready"] = False
            defender["hallucinated"] = True
            battle.log.append(f"✨ **{attacker['emoji']} {attacker['name']}** **desaparece** entre alucinaciones por 5 turnos!")
            battle.log.append(f"   🌀 El rival queda alucinado. Al volver, Noli hará daño masivo.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "guest_block":
            # Guest1337 — bloquea próximo ataque + gana carga
            attacker["blocking"] = True
            attacker["punch_charges"] = attacker.get("punch_charges", 0) + 1
            battle.log.append(f"👊 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**: ¡bloqueará el próximo ataque!")
            battle.log.append(f"   Cargas de Punch: {attacker['punch_charges']}")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "guest_punch":
            # Guest1337 — requiere carga, 55 daño + stun 2 turnos
            if not attacker.get("punch_charges", 0) > 0:
                battle.log.append(f"❌ **{attacker['name']}**: ¡Necesitas una carga de **Block** para usar Punch!")
            else:
                attacker["punch_charges"] -= 1
                dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
                defender["hp"] = max(0, defender["hp"] - dmg)
                stun_t = skill.get("stun_turns", 2)
                defender["stun_turns"] = stun_t
                battle.log.append(f"👊 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → **{dmg}** daño! ¡Stun {stun_t} turnos!")
                battle.log.append(f"   _{skill['desc']}_")

        elif stype == "bloxy_cola":
            # Noob — +15 energía extra por turno por 2 turnos
            attacker["energy_bonus_temp"] = attacker.get("energy_bonus_temp", 0) + 15
            attacker["energy_bonus_turns"] = 2
            battle.log.append(f"😃 **{attacker['emoji']} {attacker['name']}** bebe la **Bloxy Cola**: +15 energía/turno por 2 turnos!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "slateskin":
            # Noob — próximo golpe recibido: mitad daño + devuelve mitad
            attacker["slateskin"] = True
            battle.log.append(f"😃 **{attacker['emoji']} {attacker['name']}** toma la **Slateskin**: ¡el próximo ataque hará mitad del daño y lo devolverá!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "ghostburger":
            # Noob — evasión aumentada + 10 HP/turno por 4 turnos
            attacker["ghostburger_turns"] = 4
            attacker["evade_chance"] = attacker.get("evade_chance", 0) + 30
            battle.log.append(f"😃 **{attacker['emoji']} {attacker['name']}** come la **GhostBurger**: ¡+30% evasión y se curará 10 HP/turno x4!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "coin_flip":
            # Chance — cara = carga, sello = rival hace más daño
            roll = random.randint(1, 2)
            if roll == 1:
                charges = min(3, attacker.get("coin_charges", 0) + 1)
                attacker["coin_charges"] = charges
                battle.log.append(f"🔫 **{attacker['emoji']} {attacker['name']}** gira la moneda → **¡CARA!** Cargas: {charges}/3")
            else:
                attacker["coin_debuff"] = True
                battle.log.append(f"🔫 **{attacker['emoji']} {attacker['name']}** gira la moneda → **SELLO**. El próximo ataque le hará más daño!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "gun_shot":
            # Chance — dispara con prob según cargas
            charges = attacker.get("coin_charges", 0)
            if charges == 0:
                battle.log.append(f"🔫 **{attacker['emoji']} {attacker['name']}** intenta disparar... sin cargas. ¡Nada!")
            else:
                prob = {1: 40, 2: 70, 3: 100}.get(charges, 40)
                roll = random.randint(1, 100)
                if roll <= prob:
                    attacker["coin_charges"] = 0
                    dmg = battle.calc_damage(attacker["atk"], defender["defense"], 60)
                    defender["hp"] = max(0, defender["hp"] - dmg)
                    stun_t = 2
                    defender["stun_turns"] = stun_t
                    battle.log.append(f"🔫 **{attacker['emoji']} {attacker['name']}** **DISPARA** → **{dmg}** daño! ¡Stun {stun_t} turnos! ({prob}% probabilidad)")
                elif charges < 3 and random.randint(1, 100) <= 30:
                    attacker["coin_charges"] = 0
                    self_dmg = 20
                    attacker["hp"] = max(1, attacker["hp"] - self_dmg)
                    battle.log.append(f"💥 **¡La pistola de {attacker['name']} explotó en su cara!** -{self_dmg} HP!")
                else:
                    battle.log.append(f"🔫 **{attacker['emoji']} {attacker['name']}** dispara... ¡Falla! ({100-prob}% sin disparo)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "reload_stats":
            # Chance — cambia su vida aleatoriamente
            new_hp = random.randint(150, 250)
            old_hp = attacker["hp"]
            attacker["max_hp"] = new_hp
            attacker["hp"] = min(attacker["hp"], new_hp) if attacker["hp"] > new_hp else new_hp
            attacker["coin_charges"] = 0  # también recarga el revólver
            battle.log.append(f"🔫 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   ¡Nueva vida máxima: **{new_hp}** HP! (tenía {old_hp}) ¡Revólver recargado!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "spikes":
            # John Doe — daño + bloquea 2 ataques + John pierde 20 HP
            self_cost = 20
            attacker["hp"] = max(1, attacker["hp"] - self_cost)
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
            defender["hp"] = max(0, defender["hp"] - dmg)
            attacker["spike_shield"] = 2
            battle.log.append(f"💢 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → **{dmg}** daño + escudo 2 golpes! (-{self_cost} HP propio)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "error404":
            # John Doe — -10 HP propio, barra llena, +20 ATK 4 turnos
            self_cost = 10
            attacker["hp"] = max(1, attacker["hp"] - self_cost)
            attacker["energy"] = 100
            attacker["atk_buff_turns"] = 4
            attacker["atk_buff_amount"] = 20
            attacker["atk"] = attacker["atk"] + 20
            battle.log.append(f"💢 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** (-{self_cost} HP)!")
            battle.log.append(f"   ⚡ ¡Barra llena! +20 ATK por 4 turnos!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "traps":
            # John Doe — requiere 3 usos
            charges = attacker.get("trap_charges", 0) + 1
            attacker["trap_charges"] = charges
            if charges >= 3:
                attacker["trap_charges"] = 0
                if "dots" not in defender: defender["dots"] = []
                for _ in range(3):
                    defender["dots"].append({"dmg": 20, "turns": 1})
                battle.log.append(f"💢 **{attacker['emoji']} {attacker['name']}** activa la **TRAMPA**! ¡20 daño/turno x3!")
            else:
                battle.log.append(f"💢 **{attacker['emoji']} {attacker['name']}** coloca una trampa... ({charges}/3)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "apple_shot":
            # Don Manzanas — se concentra 3 turnos; al 3er uso dispara con daño máximo
            charges = attacker.get("apple_shot_charges", 0) + 1
            attacker["apple_shot_charges"] = charges
            needed = skill.get("charges_needed", 3)
            if charges >= needed:
                attacker["apple_shot_charges"] = 0
                max_pow = skill.get("max_power", 33)
                dmg = battle.calc_damage(attacker["atk"], defender["defense"], max_pow)
                defender["hp"] = max(0, defender["hp"] - dmg)
                battle.log.append(f"🍎 **{attacker['emoji']} {attacker['name']}** lanza su **Apple Shot** con TODO su poder → **{dmg}** daño!")
                battle.log.append(f"   💥 ¡La manzana sale disparada como un misil!")
                battle.log.append(f"   _{skill['desc']}_")
            else:
                battle.log.append(f"🍎 **{attacker['emoji']} {attacker['name']}** se **concentra**... ({charges}/{needed})")
                battle.log.append(f"   ⚠️ ¡{needed - charges} turno(s) más para liberar la manzana!")
                battle.log.append(f"   _{skill['desc']}_")

        elif stype == "apple_armor":
            # Don Manzanas — armadura de manzanas: reduce daño recibido N turnos
            turns = skill.get("armor_turns", 2)
            reduction = skill.get("armor_reduction", 0.5)
            attacker["apple_armor_turns"] = turns
            attacker["apple_armor_reduction"] = reduction
            battle.log.append(f"🍎🛡️ **{attacker['emoji']} {attacker['name']}** construye su **Apple Armor**!")
            battle.log.append(f"   ¡Recibirá solo el {int(reduction*100)}% del daño durante {turns} turnos!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "golden_apple":
            # Don Manzanas — potencia el próximo ataque (acumulable)
            buff = skill.get("atk_buff", 14)
            attacker["atk_buff"] = attacker.get("atk_buff", 0) + buff
            total = attacker["atk_buff"]
            battle.log.append(f"🍏✨ **{attacker['emoji']} {attacker['name']}** saca una **Golden Apple**!")
            battle.log.append(f"   ¡Su próximo ataque tendrá +{buff} ATK extra! (Total acumulado: +{total})")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "crystal_switch":
            # Jane Doe — cambia tipo de cristal
            current = attacker.get("crystal_type", "damage")
            nxt = "heal" if current == "damage" else "damage"
            attacker["crystal_type"] = nxt
            labels = {"damage": "⚔️ DAÑO (stun + 20 daño)", "heal": "💚 CURACIÓN (cura aliado con menos HP + inmunidad)"}
            battle.log.append(f"🪓 **{attacker['emoji']} {attacker['name']}** cambia cristal → **{labels[nxt]}**!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "crystal_throw":
            # Jane Doe — ejecuta según tipo activo
            ctype = attacker.get("crystal_type", "damage")
            if ctype == "damage":
                dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
                defender["hp"] = max(0, defender["hp"] - dmg)
                defender["stun_turns"] = 3
                battle.log.append(f"🪓 **{attacker['emoji']} {attacker['name']}** lanza **Cristal de Daño** → **{dmg}** daño + stun 3 turnos!")
                # Pasiva Resonancia
                defender["resonance"] = defender.get("resonance", 0) + 1
                res = defender["resonance"]
                defender["atk"] = max(1, defender["atk"] - 3)
                battle.log.append(f"   💜 Resonancia x{res}: ATK rival -3, daño recibido aumentado!")
            else:
                # Cura al aliado con menos HP
                ally_team = atk_team
                weakest = min((f for f in ally_team if f["hp"] > 0), key=lambda f: f["hp"], default=None)
                if weakest:
                    heal_amt = 20
                    weakest["hp"] = min(weakest["max_hp"], weakest["hp"] + heal_amt)
                    weakest["immune_turns"] = 3
                    battle.log.append(f"🪓 **{attacker['emoji']} {attacker['name']}** lanza **Cristal de Curación** → **{weakest['emoji']} {weakest['name']}** +{heal_amt} HP + inmunidad 3 turnos!")
                else:
                    battle.log.append(f"🪓 No hay aliados que curar.")
            battle.log.append(f"   _{skill['desc']}_")

        # ── OG GAMER 64 habilidades especiales ──────────────────────────

        elif stype == "charge_delete":
            # [[TEXT NOT FOUND]] — usada 2 veces seguidas elimina la figura activa del oponente
            prev_charges = attacker.get("charge_delete_count", 0)
            attacker["charge_delete_count"] = prev_charges + 1
            if attacker["charge_delete_count"] >= 2:
                attacker["charge_delete_count"] = 0
                defender["hp"] = 0
                battle.log.append(f"💥 **{attacker['emoji']} {attacker['name']}** terminó de recargar... ¡la energía explota sobre **{defender['emoji']} {defender['name']}**!")
                battle.log.append(f"   ☠️ **{defender['name']}** fue eliminado instantáneamente!")
            else:
                battle.log.append(f"⚡ **{attacker['emoji']} {attacker['name']}** empieza a recargar... (**1/2**) ¡Usa la habilidad otra vez para eliminar a {defender['name']}!")

        elif stype == "og_ki_charge":
            # Ki Charge — +100 HP, +20 ATK/DEF, acumulable, permanente
            ki_hp   = skill.get("ki_hp", 100)
            ki_stat = skill.get("ki_stat", 20)
            attacker["max_hp"] += ki_hp
            attacker["hp"]     = min(attacker["max_hp"], attacker["hp"] + ki_hp)
            attacker["atk"]     += ki_stat
            attacker["defense"] += ki_stat
            stacks = attacker.get("ki_stacks", 0) + 1
            attacker["ki_stacks"] = stacks
            battle.log.append(f"✨ **{attacker['emoji']} {attacker['name']}** carga su Ki! (x{stacks})")
            battle.log.append(f"   ❤️ +{ki_hp} HP máx · ⚔️ +{ki_stat} ATK · 🛡️ +{ki_stat} DEF — ¡Acumulable!")

        elif stype == "instakill_random":
            # Godlike — mata a una figura aleatoria del oponente
            alive_enemies = [f for f in def_team if f["hp"] > 0]
            if alive_enemies:
                chosen = random.choice(alive_enemies)
                chosen["hp"] = 0
                battle.log.append(f"☠️ **{attacker['emoji']} {attacker['name']}** flota... agarra a **{chosen['emoji']} {chosen['name']}** y la aplasta con sus manos!")
                battle.log.append(f"   ¡**{chosen['name']}** fue eliminada instantáneamente!")
            else:
                battle.log.append(f"☠️ No hay figuras enemigas que eliminar.")

        elif stype == "og_reset_phase":
            # Prismatic Energy — regresa a Fase 1 con vida completa
            attacker["og_phase"] = 1
            all_skills = FIGURE_SKILLS.get("og_gamer64", [])
            attacker["skills"] = [sk for sk in all_skills if sk.get("phase") == 1]
            attacker["hp"]     = attacker["max_hp"]
            attacker["energy"] = 0
            battle.log.append(f"🔄 **{attacker['emoji']} {attacker['name']}** regresa el tiempo...")
            battle.log.append(f"   ¡Vuelve a **🔵 FASE 1** con **{attacker['hp']} HP** completos!")

        elif stype == "og_its_over":
            # ITS OVER! — mata a todos los enemigos y a sí mismo, -20 HP a aliados
            splash = skill.get("power", 20)
            # Matar todos los enemigos
            killed = []
            for enemy in def_team:
                if enemy["hp"] > 0:
                    enemy["hp"] = 0
                    killed.append(f"{enemy['emoji']} {enemy['name']}")
            # Daño splash a aliados
            splashed = []
            for ally in atk_team:
                if ally is not attacker and ally["hp"] > 0:
                    ally["hp"] = max(0, ally["hp"] - splash)
                    splashed.append(f"{ally['emoji']} {ally['name']} (-{splash} HP)")
            # Matar al propio Gamer
            attacker["hp"] = 0
            battle.log.append(f"💥 **{attacker['emoji']} {attacker['name']}** explota con todo su poder... ¡ITS OVER!")
            if killed:
                battle.log.append(f"   ☠️ Eliminados: {', '.join(killed)}")
            if splashed:
                battle.log.append(f"   💥 Daño de explosión a aliados: {', '.join(splashed)}")
            battle.log.append(f"   💀 **{attacker['name']}** también cae en la explosión...")

        elif stype == "keep_the_act":
            bar_bonus = skill.get("bar_bonus", 50)
            attacker["energy"] = min(attacker.get("energy_cap", ENERGY_MAX), attacker.get("energy", 0) + bar_bonus)
            attacker["cant_attack_turns"] = skill.get("cant_attack_turns", 2)
            battle.log.append(f"🟢 **{attacker['name']}** finge ser tripulante... +{bar_bonus}⚡ barra.")
            battle.log.append(f"   ⚠️ No puede atacar por {skill.get('cant_attack_turns',2)} turnos.")

        elif stype == "lights_out":
            stun_t = skill.get("stun_turns", 3)
            atk_buff = skill.get("self_atk_buff", 10)
            # Stun a TODOS menos al propio Green
            all_figs = battle.p1_team + battle.p2_team
            stunned_names = []
            for fig in all_figs:
                if fig is not attacker and fig["hp"] > 0:
                    fig["stunned"] = True
                    fig["stun_turns"] = stun_t
                    stunned_names.append(fig["name"])
            attacker["atk"] = attacker.get("atk", 0) + atk_buff
            attacker["lights_out_buff_turns"] = skill.get("self_atk_buff_turns", 2)
            battle.log.append(f"🟢 **{attacker['name']}** apaga las luces! 🌑")
            battle.log.append(f"   😵 Stun {stun_t}T a todos: {', '.join(stunned_names)}")
            battle.log.append(f"   ⚔️ Green +{atk_buff} ATK por {skill.get('self_atk_buff_turns',2)} turnos.")

        elif stype == "ejected":
            return_turns = skill.get("return_turns", 18)
            second_form  = skill.get("second_form_key", attacker.get("key","") + "2")
            # "Matar" al atacante y al defensor pero guardar info para retorno
            attacker["ejected"] = True
            attacker["ejected_return_turns"] = return_turns
            attacker["ejected_second_form"]  = second_form
            attacker["hp"] = 0
            defender["hp"] = 0
            battle.log.append(f"🚀 **{attacker['name']}** y **{defender['name']}** son expulsados al espacio...")
            battle.log.append(f"   ☠️ Ambos 'mueren'... ¿o no? Si quedan figuras en pie en {return_turns} turnos, **vuelven**.")
            # Guardar para el tick de turnos
            battle.ejected_queue = getattr(battle, "ejected_queue", [])
            battle.ejected_queue.append({
                "attacker_key": attacker.get("key"),
                "attacker_team": "p1" if attacker in battle.p1_team else "p2",
                "attacker_idx": (battle.p1_team if attacker in battle.p1_team else battle.p2_team).index(attacker),
                "second_form": second_form,
                "turns_left": return_turns,
            })

        elif stype == "hide_and_seek":
            hide_t = skill.get("hide_turns", 2)
            dmg    = skill.get("power", 30)
            attacker["hiding"] = True
            attacker["hiding_turns"] = hide_t
            attacker["hiding_strike_dmg"] = dmg
            # Forzar cambio de figura aliada
            atk_team     = battle.p1_team if battle.turn == 1 else battle.p2_team
            atk_idx_attr = "p1_active" if battle.turn == 1 else "p2_active"
            cur_idx = getattr(battle, atk_idx_attr)
            for i, fig in enumerate(atk_team):
                if i != cur_idx and fig["hp"] > 0:
                    setattr(battle, atk_idx_attr, i)
                    battle.log.append(f"⚪ **{attacker['name']}** se esconde... fuerza cambio a {fig['emoji']} {fig['name']}.")
                    battle.log.append(f"   ⏳ En {hide_t} turnos atacará por {dmg} de daño.")
                    break

        elif stype == "rage_baiting":
            if random.randint(1,100) <= 50:
                # 50%: oponente -10 ATK por 3 turnos
                defender["atk"] = max(0, defender.get("atk",0) - skill.get("atk_debuff",10))
                defender["rage_bait_debuff_turns"] = skill.get("atk_debuff_turns",3)
                battle.log.append(f"🟤 **{attacker['name']}** finge atacar... ¡el oponente cae en la trampa!")
                battle.log.append(f"   ⬇️ {defender['name']} -10 ATK por 3 turnos.")
            else:
                # 50%: stun al oponente 3 turnos
                defender["stunned"] = True
                defender["stun_turns"] = skill.get("stun_turns",3)
                battle.log.append(f"🟤 **{attacker['name']}** ¡ATACA REALMENTE! {defender['name']} queda stuneado 3 turnos.")

        elif stype == "lulz_git_gut":
            drain_pct = skill.get("hp_drain_pct", 80) / 100
            self_dmg  = skill.get("self_dmg", 30)
            hp_loss   = max(1, int(defender["hp"] * drain_pct))
            defender["hp"] = max(0, defender["hp"] - hp_loss)
            attacker["hp"] = max(0, attacker["hp"] - self_dmg)
            battle.log.append(f"🟤 **{attacker['name']}** LULZ GIT GUT XD — ¡-{hp_loss} HP a {defender['name']}!")
            battle.log.append(f"   💥 Maroon también pierde {self_dmg} HP por el esfuerzo.")

        elif stype == "convincment":
            # Pink y la figura activa enemiga mueren
            attacker["hp"] = 0
            defender["hp"] = 0
            battle.log.append(f"🩷 **{attacker['name']}** y **{defender['name']}** llegan a un acuerdo...")
            battle.log.append(f"   ✌️ Ambos se van de la batalla. Adiós.")

        elif stype == "friendship_shield":
            shield_t = skill.get("shield_turns", 10)
            shield_h = skill.get("shield_hits", 5)
            attacker["shield_turns"] = shield_t
            attacker["shield_hits"]  = shield_h
            battle.log.append(f"🩷 **{attacker['name']}** genera un escudo de amistad!")
            battle.log.append(f"   🛡️ Absorbe {shield_h} ataques por {shield_t} turnos.")

        elif stype == "flying_monstrosity":
            hold_t = skill.get("hold_turns", 5)
            attacker["flying_hold_turns"] = hold_t
            attacker["stunned"] = True
            attacker["stun_turns"] = hold_t
            defender["flying_held_turns"] = hold_t
            defender["stunned"] = True
            defender["stun_turns"] = hold_t
            # Forzar cambio de la figura enemiga
            def_team     = battle.p2_team if battle.turn == 1 else battle.p1_team
            def_idx_attr = "p2_active" if battle.turn == 1 else "p1_active"
            for i, fig in enumerate(def_team):
                if fig is not defender and fig["hp"] > 0:
                    setattr(battle, def_idx_attr, i)
                    break
            battle.log.append(f"🟢 **{attacker['name']}** agarra a **{defender['name']}**!")
            battle.log.append(f"   🔒 Ambos bloqueados {hold_t} turnos. Si Green sobrevive... {defender['name']} muere.")


            defender["absorbed_turns"] = 2
            defender["absorbed_by_kirby"] = True
            absorbed_key    = defender.get("key", "")
            absorbed_skills = FIGURE_SKILLS.get(absorbed_key, [])
            if absorbed_key == "og_gamer64":
                absorbed_skills = [sk for sk in absorbed_skills if sk.get("phase", 1) == defender.get("og_phase", 1)]
            attacker["kirby_original_skills"] = list(KIRBY_DEFAULT_SKILLS)
            attacker["kirby_absorbed_from"]   = absorbed_key
            transformed_skills = [KIRBY_TRANSFORMED_SLOT0]
            costs = [40, 60, 100]
            for i, sk in enumerate(absorbed_skills[:3]):
                copied = dict(sk)
                copied["cost"] = costs[i]
                transformed_skills.append(copied)
            attacker["skills"] = transformed_skills
            def_team     = battle.p2_team if battle.turn == 1 else battle.p1_team
            def_idx_attr = "p2_active" if battle.turn == 1 else "p1_active"
            swapped = False
            for i, fig in enumerate(def_team):
                if fig is not defender and fig["hp"] > 0:
                    setattr(battle, def_idx_attr, i)
                    battle.log.append(f"🌸 **Kirby** absorbe a **{defender['emoji']} {defender['name']}**!")
                    battle.log.append(f"   😵 {defender['name']} desaparece **2 turnos** y Kirby copia sus habilidades!")
                    battle.log.append(f"   🔄 Entra **{fig['emoji']} {fig['name']}** en su lugar.")
                    swapped = True
                    break
            if not swapped:
                battle.log.append(f"🌸 **Kirby** absorbe a **{defender['emoji']} {defender['name']}**!")
                battle.log.append(f"   😵 {defender['name']} desaparece **2 turnos** y Kirby copia sus habilidades!")

            # Logros de Kirby
            try:
                db_ach = load_db()
                u_ach  = get_user(db_ach, battle.p1)
                if u_ach:
                    new_achs = []
                    is_second_form = (
                        absorbed_key in ("omega_flowey","boss_impostor_green2","boss_impostor_maroon2") or
                        (absorbed_key == "og_gamer64" and defender.get("og_phase", 1) >= 2)
                    )
                    if is_second_form and grant_achievement(u_ach, "kirby_no_mas"):
                        new_achs.append("kirby_no_mas")
                    if absorbed_key == "omega_flowey":
                        if grant_achievement(u_ach, "kirby_no_mas"):
                            new_achs.append("kirby_no_mas")
                        if grant_achievement(u_ach, "kirby_no_entendiste"):
                            new_achs.append("kirby_no_entendiste")
                    if new_achs:
                        save_db(db_ach)
                        for aid in new_achs:
                            ach = ACHIEVEMENTS.get(aid, {})
                            battle.log.append(f"   🏅 ¡Logro desbloqueado! **{ach.get('name','?')}**")
            except Exception:
                pass

        elif stype == "kirby_spit":
            attacker["skills"] = list(KIRBY_DEFAULT_SKILLS)
            attacker.pop("kirby_absorbed_from", None)
            attacker.pop("kirby_original_skills", None)
            battle.log.append(f"🌸 **Kirby** escupe la habilidad absorbida y vuelve a sus poderes originales!")

        elif stype == "kirby_flamethrower":
            dot_dmg  = skill.get("dot_power", 6)
            dot_t    = skill.get("dot_turns", 8)
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            hit = []
            for fig in def_team:
                if fig["hp"] > 0:
                    dmg = battle.calc_damage(attacker["atk"], fig["defense"], skill.get("power", 20))
                    fig["hp"] = max(0, fig["hp"] - dmg)
                    fig.setdefault("dots", []).append({"dmg": dot_dmg, "turns": dot_t})
                    hit.append(f"{fig['emoji']} {fig['name']} -{dmg}HP🔥")
            battle.log.append(f"🔥 **Kirby** echa llamas sobre todos los enemigos!")
            if hit:
                battle.log.append(f"   {' · '.join(hit)}")
            battle.log.append(f"   ☠️ Burning {dot_dmg}/turno por {dot_t} turnos!")

        # ── SANS ─────────────────────────────────────────────────────

        elif stype == "bone_barrier":
            # Activa la barrera: el siguiente ataque recibido se bloquea y hace 15 daño al atacante
            attacker["bone_barrier"] = True
            attacker["bone_barrier_dmg"] = skill.get("power", 15)
            battle.log.append(f"🦴 **Sans** genera una barrera de huesos...")
            battle.log.append(f"   🛡️ El próximo ataque será bloqueado y hará {skill.get('power',15)} de daño al atacante.")

        elif stype == "sans_rest":
            energy_now = attacker.get("energy", 0)
            if energy_now <= 0:
                battle.log.append(f"   <:SANS:1511160523775807588> **Sans** intenta descansar... pero no tiene energía que convertir.")
            else:
                attacker["energy"] = 0
                old_misses = attacker.get("sans_misses", 0)
                attacker["sans_misses"] = old_misses + energy_now
                battle.log.append(f"   <:SANS:1511160523775807588> **Sans** descansa un momento...")
                battle.log.append(f"   🟦 +{energy_now} Misses! [{old_misses} → {attacker['sans_misses']}]")

        elif stype == "love_check":
            kills = _get_love_kills(battle, attacker)
            dmg   = kills * skill.get("dmg_per_kill", 20)
            if dmg <= 0:
                dmg = 1
                battle.log.append(f"<:SANS:1511160523775807588> **Sans** mira tus pecados... no has matado a nadie aún. Pero algo es algo.")
            else:
                battle.log.append(f"<:SANS:1511160523775807588> **Sans** mira todos tus pecados... has matado a **{kills}** figuras.")
                battle.log.append(f"   ☠️ **{kills} × 20 = {dmg}** de daño. Hora de pagar.")
            defender["hp"] = max(0, defender["hp"] - dmg)

        # ── JEVIL ────────────────────────────────────────────────────

        elif stype == "chaos_chaos":
            _CHAOS_EFFECTS = ["frozen", "burning", "stun", "force_switch", "poison", "dizziness"]
            effect = random.choice(_CHAOS_EFFECTS)
            battle.log.append(f"🃏 **Jevil**: *THE CHAOS IS THE ONLY THING I'M HERE FOR!*")
            if effect == "frozen":
                defender["stun_turns"] = 2
                defender.setdefault("dots", []).append({"dmg": 3, "turns": 2})
                battle.log.append(f"   ❄️ CHAOS: ¡{defender['name']} congelado! Stun 2t + 3 daño/turno!")
            elif effect == "burning":
                defender.setdefault("dots", []).append({"dmg": 5, "turns": 5})
                battle.log.append(f"   🔥 CHAOS: ¡{defender['name']} en llamas! 5 daño/turno x5t!")
            elif effect == "stun":
                defender["stun_turns"] = 2
                battle.log.append(f"   😵 CHAOS: ¡{defender['name']} aturdido 2 turnos!")
            elif effect == "force_switch":
                defender["force_switch_turns"] = 1
                battle.log.append(f"   🔄 CHAOS: ¡{defender['name']} forzado a cambiar de figura!")
            elif effect == "poison":
                defender.setdefault("dots", []).append({"dmg": 8, "turns": 4})
                battle.log.append(f"   ☠️ CHAOS: ¡{defender['name']} envenenado! 8 daño/turno x4t!")
            elif effect == "dizziness":
                defender["dizziness_turns"] = 3
                battle.log.append(f"   💫 CHAOS: ¡{defender['name']} mareado 3 turnos! (daño reducido)")

        elif stype == "map_revolving":
            diz_t = skill.get("dizziness_turns", 6)
            defender["dizziness_turns"] = diz_t
            defender["dizziness_stun_chance"] = skill.get("stun_chance", 0.50)
            battle.log.append(f"🃏 **Jevil**: *El mapa empieza a girar...*")
            battle.log.append(f"   💫 {defender['name']}: dizziness {diz_t} turnos (50% de stun cada turno)!")

        elif stype == "metamorphosis":
            dur = skill.get("duration", 6)
            battle.metamorphosis_turns = dur
            battle.log.append(f"🃏 **Jevil**: *¡METAMORPHOSIS!*")
            battle.log.append(f"   🔀 ¡Cambio forzado de figura al final de cada turno por {dur} turnos!")

        # ── ANNOYING DOG ─────────────────────────────────────────────

        elif stype == "code_consumer":
            _BUFFS = ["atk_up", "def_up", "hp_up", "energy_up", "heal"]
            _DEBUFFS = ["stun", "poison", "burning", "dizziness", "force_switch"]
            self_effect = random.choice(_BUFFS + _DEBUFFS)
            enemy_effect = random.choice(_DEBUFFS)
            battle.log.append(f"🐶 **Toby** se comió parte del código... OH NO!")
            # Self effect
            if self_effect == "atk_up":
                attacker["atk"] = int(attacker["atk"] * 1.2)
                battle.log.append(f"   📈 Toby +20% ATK!")
            elif self_effect == "def_up":
                attacker["defense"] = int(attacker["defense"] * 1.2)
                battle.log.append(f"   🛡️ Toby +20% DEF!")
            elif self_effect == "hp_up":
                attacker["max_hp"] += 30
                attacker["hp"] += 30
                battle.log.append(f"   ❤️ Toby +30 HP máximo!")
            elif self_effect == "energy_up":
                attacker["energy"] = min(attacker.get("energy_cap", 100), attacker.get("energy", 0) + 30)
                battle.log.append(f"   ⚡ Toby +30 energía!")
            elif self_effect == "heal":
                h = random.randint(15, 35)
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + h)
                battle.log.append(f"   💚 Toby +{h} HP!")
            elif self_effect == "stun":
                attacker["stun_turns"] = 2
                battle.log.append(f"   😵 Toby... se stuneó a sí mismo...?")
            elif self_effect == "poison":
                attacker.setdefault("dots", []).append({"dmg": 5, "turns": 3})
                battle.log.append(f"   ☠️ Toby se envenenó a sí mismo...!")
            elif self_effect == "burning":
                attacker.setdefault("dots", []).append({"dmg": 4, "turns": 4})
                battle.log.append(f"   🔥 Toby... se prendió fuego...?")
            elif self_effect == "dizziness":
                attacker["dizziness_turns"] = 3
                battle.log.append(f"   💫 Toby se mareó... bien...")
            elif self_effect == "force_switch":
                battle.log.append(f"   🔄 Toby decidió irse a pasear...")
                atk_idx_attr = "p1_active" if battle.turn == 1 else "p2_active"
                atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                cur = getattr(battle, atk_idx_attr)
                alive_others = [i for i, f2 in enumerate(atk_team) if i != cur and f2["hp"] > 0]
                if alive_others:
                    setattr(battle, atk_idx_attr, random.choice(alive_others))
            # Enemy effect
            if enemy_effect == "stun":
                defender["stun_turns"] = max(defender.get("stun_turns", 0), 2)
                battle.log.append(f"   😵 {defender['name']} aturdido 2 turnos!")
            elif enemy_effect == "poison":
                defender.setdefault("dots", []).append({"dmg": 6, "turns": 3})
                battle.log.append(f"   ☠️ {defender['name']} envenenado!")
            elif enemy_effect == "burning":
                defender.setdefault("dots", []).append({"dmg": 5, "turns": 4})
                battle.log.append(f"   🔥 {defender['name']} en llamas!")
            elif enemy_effect == "dizziness":
                defender["dizziness_turns"] = 3
                battle.log.append(f"   💫 {defender['name']} mareado!")
            elif enemy_effect == "force_switch":
                defender["force_switch_turns"] = 1
                battle.log.append(f"   🔄 {defender['name']} forzado a cambiar!")

        elif stype == "bark":
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill.get("power", 15))
            defender["hp"] = max(0, defender["hp"] - dmg)
            battle.log.append(f"🐶 **Toby**: *BARK!*")
            battle.log.append(f"   ⚔️ {defender['name']} -{dmg}HP")
            _DEBUFFS2 = ["stun", "poison", "burning", "dizziness", "force_switch", "frozen"]
            deb = random.choice(_DEBUFFS2)
            if deb == "stun":
                defender["stun_turns"] = max(defender.get("stun_turns", 0), 2)
                battle.log.append(f"   😵 {defender['name']} aturdido 2 turnos!")
            elif deb == "poison":
                defender.setdefault("dots", []).append({"dmg": 6, "turns": 3})
                battle.log.append(f"   ☠️ {defender['name']} envenenado! 6/turno x3")
            elif deb == "burning":
                defender.setdefault("dots", []).append({"dmg": 5, "turns": 4})
                battle.log.append(f"   🔥 {defender['name']} en llamas! 5/turno x4")
            elif deb == "dizziness":
                defender["dizziness_turns"] = 3
                battle.log.append(f"   💫 {defender['name']} mareado 3 turnos!")
            elif deb == "force_switch":
                defender["force_switch_turns"] = 1
                battle.log.append(f"   🔄 {defender['name']} forzado a cambiar!")
            elif deb == "frozen":
                defender["stun_turns"] = 2
                defender.setdefault("dots", []).append({"dmg": 3, "turns": 2})
                battle.log.append(f"   ❄️ {defender['name']} congelado 2t + 3 daño/turno!")

        elif stype == "strange_twirl":
            battle.log.append(f"🐶 **Toby**: *Este es solo el comienzo de algo más grande...*")
            playable_keys = [k for k, f2 in FIGURES.items()
                             if f2.get("price", 0) > 0 and k not in ("santa_vaca", "lobster")]
            # Replace attacker
            new_atk_key = random.choice(playable_keys)
            new_atk = make_fighter(new_atk_key, {"level": attacker.get("level", 1), "xp": 0})
            atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
            atk_idx_attr = "p1_active" if battle.turn == 1 else "p2_active"
            cur_atk_idx = getattr(battle, atk_idx_attr)
            atk_team[cur_atk_idx] = new_atk
            # Replace defender
            new_def_key = random.choice(playable_keys)
            new_def = make_fighter(new_def_key, {"level": defender.get("level", 1), "xp": 0})
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            def_idx_attr = "p2_active" if battle.turn == 1 else "p1_active"
            cur_def_idx = getattr(battle, def_idx_attr)
            def_team[cur_def_idx] = new_def
            battle.log.append(f"   🌀 ¡Toby fue reemplazado por **{new_atk['emoji']} {new_atk['name']}**!")
            battle.log.append(f"   🌀 ¡{defender['name']} fue reemplazado por **{new_def['emoji']} {new_def['name']}**!")

        # ── HOMERO SIMPSON ───────────────────────────────────────────

        elif stype == "random_food":
            foods = skill.get("foods", [])
            food = random.choice(foods) if foods else None
            if not food:
                battle.log.append(f"🍩 **Homero** busca comida... su bolsillo está vacío!")
            else:
                eff = food.get("effect")
                lbl = food.get("label", "Comida")
                battle.log.append(f"🍩 **Homero** saca: {lbl}!")
                atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                def_team = battle.p2_team if battle.turn == 1 else battle.p1_team

                if eff == "self_heal":
                    hp = food.get("power", 20)
                    attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + hp)
                    battle.log.append(f"   💚 Homero +{hp}HP. Mmm... donut...")

                elif eff == "duff_heal":
                    sh = food.get("self_heal", 30)
                    ah = food.get("ally_heal", 10)
                    attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + sh)
                    battle.log.append(f"   🍺 Homero +{sh}HP")
                    for fig in atk_team:
                        if fig is not attacker and fig["hp"] > 0:
                            fig["hp"] = min(fig["max_hp"], fig["hp"] + ah)
                            battle.log.append(f"   💚 {fig['name']} +{ah}HP")

                elif eff == "chiles":
                    sd = food.get("self_dmg", 10)
                    ed = food.get("enemy_dmg", 5)
                    dp = food.get("dot_power", 4)
                    dt = food.get("dot_turns", 3)
                    st = food.get("stun_turns", 1)
                    attacker["hp"] = max(0, attacker["hp"] - sd)
                    battle.log.append(f"   🌶️ Homero -{sd}HP (¡PICANTE!)")
                    for fig in def_team:
                        if fig["hp"] > 0:
                            fig["hp"] = max(0, fig["hp"] - ed)
                            fig.setdefault("dots", []).append({"dmg": dp, "turns": dt})
                            fig["stun_turns"] = max(fig.get("stun_turns", 0), st)
                            battle.log.append(f"   🌶️ {fig['name']} -{ed}HP + burning {dp}/t x{dt}t + stun {st}t!")

                elif eff == "mariscos":
                    sh = food.get("self_heal", 20)
                    eb = food.get("energy_bonus", 20)
                    attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + sh)
                    attacker["energy"] = min(attacker.get("max_energy", 100), attacker.get("energy", 0) + eb)
                    battle.log.append(f"   🦐 Homero +{sh}HP y +{eb} energía!")

                elif eff == "krusty_burger":
                    sh = food.get("self_heal", 20)
                    dn = food.get("def_nerf", 10)
                    nt = food.get("nerf_turns", 2)
                    attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + sh)
                    attacker["defense"] = max(0, attacker.get("defense", 0) - dn)
                    attacker.setdefault("temp_def_nerf", []).append({"amount": dn, "turns": nt})
                    battle.log.append(f"   🍔 Homero +{sh}HP pero -{dn} DEF por {nt} turnos...")

                elif eff == "submarine":
                    sh = food.get("self_heal", 100)
                    hb = food.get("hp_bonus", 40)
                    st = food.get("stun_turns", 3)
                    attacker["hp"] = min(attacker["max_hp"] + hb, attacker["hp"] + sh)
                    attacker["max_hp"] = attacker.get("max_hp", 100) + hb
                    attacker["stun_turns"] = st
                    battle.log.append(f"   🥖 ¡Homero +{sh}HP y +{hb} HP máximo permanente!")
                    battle.log.append(f"   😴 ...pero Homero se queda dormido {st} turnos de tanto comer.")

                elif eff == "random_heal":
                    rh = random.randint(food.get("min", 15), food.get("max", 45))
                    attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + rh)
                    battle.log.append(f"   🍫 Homero +{rh}HP. (sabor misterioso)")

        elif stype == "homer_choke":
            dot_t    = skill.get("dot_turns", 5)
            dot_dmg  = skill.get("power", 25)
            self_blk = skill.get("self_block_turns", 5)
            e_stun   = skill.get("enemy_stun_turns", 5)
            defender.setdefault("dots", []).append({"dmg": dot_dmg, "turns": dot_t})
            defender["stun_turns"] = e_stun
            defender["homer_choking"] = True
            attacker["stun_turns"] = self_blk
            battle.log.append(f"😠 **Homero**: *Why, you little...!* ¡Agarra a {defender['name']} del cuello!")
            battle.log.append(f"   🔴 {defender['name']}: {dot_dmg} daño/turno x{dot_t}t + stuneado {e_stun}t")
            battle.log.append(f"   😤 Homero queda bloqueado {self_blk} turnos...")
            if skill.get("escape_minigame"):
                battle.log.append(f"   🎮 ¡{defender['name']} puede intentar escapar completando el minijuego!")

        elif stype == "nuclear_missfunction":
            success = random.random() < 0.50
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            alive = [f for f in def_team if f["hp"] > 0]
            if success:
                battle.log.append(f"☢️ **Homero**: *Puede que haya presionado el botón incorrecto... D'OH!*")
                battle.log.append(f"   🎉 **¡WOO-HOO!** ¡Algo salió bien por una vez!")
                killed = 0
                for fig in alive:
                    if killed < 2:
                        battle.log.append(f"   💀 ¡{fig['name']} fue eliminado por la explosión nuclear!")
                        fig["hp"] = 0
                        killed += 1
                    else:
                        fig["hp"] = max(0, fig["hp"] - 100)
                        battle.log.append(f"   💥 {fig['name']} -{100}HP (sobrevivió... por poco)")
            else:
                battle.log.append(f"☢️ **Homero**: *Puede que haya presionado el botón incorrecto... D'OH!*")
                battle.log.append(f"   😭 *We tried our best and we failed miserably. The lesson is: never try.*")
                atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                alive_own = [f for f in atk_team if f["hp"] > 0]
                killed = 0
                for fig in alive_own:
                    if killed < 2:
                        battle.log.append(f"   💀 ¡{fig['name']} fue eliminado por el accidente nuclear!")
                        fig["hp"] = 0
                        killed += 1
                    else:
                        fig["hp"] = max(0, fig["hp"] - 100)
                        battle.log.append(f"   💥 {fig['name']} -{100}HP (daño colateral)")

        # ── PAPER MARIO ──────────────────────────────────────────────

        elif stype == "object_menu":
            # Bot elige un objeto al azar ponderado; en PvP el jugador elige via select
            items = skill.get("items", [])
            chosen = random.choice(items) if items else None
            if not chosen:
                battle.log.append(f"📄 **Paper Mario** busca en su mochila pero no encuentra nada...")
            else:
                itype = chosen.get("type", "damage")
                ilabel = chosen.get("label", "Objeto")
                battle.log.append(f"📦 **Paper Mario** saca: {ilabel}!")
                if itype == "heal":
                    hp_gain = chosen.get("power", 50)
                    attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + hp_gain)
                    battle.log.append(f"   💚 {attacker['name']} +{hp_gain}HP")
                    if chosen.get("team_heal"):
                        th = chosen.get("team_heal_power", 25)
                        atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                        for fig in atk_team:
                            if fig is not attacker and fig["hp"] > 0:
                                fig["hp"] = min(fig["max_hp"], fig["hp"] + th)
                                battle.log.append(f"   💚 {fig['name']} +{th}HP")
                elif itype == "damage":
                    dmg = battle.calc_damage(attacker["atk"], defender["defense"], chosen.get("power", 20))
                    defender["hp"] = max(0, defender["hp"] - dmg)
                    battle.log.append(f"   ⚔️ {defender['name']} -{dmg}HP")
                    if chosen.get("dot"):
                        dp = chosen.get("dot_power", 5)
                        dt = chosen.get("dot_turns", 10)
                        defender.setdefault("dots", []).append({"dmg": dp, "turns": dt})
                        battle.log.append(f"   🔥 Burning! {dp} daño/turno x{dt} turnos!")
                    if chosen.get("frozen"):
                        ft = chosen.get("frozen_turns", 2)
                        fd = chosen.get("frozen_dot", 3)
                        defender["stun_turns"] = ft
                        defender.setdefault("dots", []).append({"dmg": fd, "turns": ft})
                        battle.log.append(f"   ❄️ Frozen! Aturdido {ft} turnos y {fd} daño/turno!")
                    if chosen.get("stun"):
                        st = chosen.get("stun_turns", 2)
                        if not defender.get("stun_immune"):
                            defender["stun_turns"] = st
                            battle.log.append(f"   💥 ¡Bloqueado! {defender['name']} aturdido {st} turnos!")
                    if chosen.get("aoe"):
                        def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                        for fig in def_team:
                            if fig is not defender and fig["hp"] > 0:
                                sdmg = battle.calc_damage(attacker["atk"], fig["defense"], chosen.get("aoe_secondary_power", 15))
                                fig["hp"] = max(0, fig["hp"] - sdmg)
                                if chosen.get("stun"):
                                    fig["stun_turns"] = chosen.get("stun_turns", 2)
                                battle.log.append(f"   💥 {fig['name']} -{sdmg}HP")
                    if chosen.get("force_switch"):
                        fs_turns = chosen.get("force_switch_turns", 1)
                        defender["force_switch_turns"] = fs_turns
                        battle.log.append(f"   🐢 ¡{defender['name']} es forzado a cambiar de figura!")

        elif stype == "ally_help":
            allies = skill.get("allies", [])
            chosen = random.choice(allies) if allies else None
            if not chosen:
                battle.log.append(f"📄 **Paper Mario** llama a sus aliados... pero nadie responde.")
            else:
                atype = chosen.get("type", "damage")
                alabel = chosen.get("label", "Aliado")
                fail_chance = chosen.get("fail_chance", 0.0)
                failed = random.random() < fail_chance
                battle.log.append(f"❗ **Paper Mario** llama a: {alabel}!")
                if failed:
                    battle.log.append(f"   💨 ...pero {alabel} no llegó a tiempo!")
                else:
                    if atype == "damage":
                        dmg = battle.calc_damage(attacker["atk"], defender["defense"], chosen.get("power", 20))
                        defender["hp"] = max(0, defender["hp"] - dmg)
                        battle.log.append(f"   ⚔️ {defender['name']} -{dmg}HP")
                        if chosen.get("stun"):
                            st = chosen.get("stun_turns", 2)
                            if not defender.get("stun_immune"):
                                defender["stun_turns"] = st
                                battle.log.append(f"   😵 {defender['name']} aturdido {st} turnos!")
                        if chosen.get("dot"):
                            dp = chosen.get("dot_power", 6)
                            dt = chosen.get("dot_turns", 5)
                            defender.setdefault("dots", []).append({"dmg": dp, "turns": dt})
                            battle.log.append(f"   🔥 Burning! {dp}/turno x{dt} turnos!")
                        if chosen.get("aoe_splash"):
                            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                            for fig in def_team:
                                if fig is not defender and fig["hp"] > 0:
                                    fig["hp"] = max(0, fig["hp"] - chosen["aoe_splash"])
                                    battle.log.append(f"   💣 Splash: {fig['name']} -{chosen['aoe_splash']}HP")
                        if chosen.get("coin_bonus"):
                            battle.log.append(f"   💰 ¡+{chosen['coin_bonus']} monedas extra al ganar!")
                            attacker.setdefault("coin_bonus", 0)
                            attacker["coin_bonus"] = attacker.get("coin_bonus", 0) + chosen["coin_bonus"]
                    elif atype == "dot":
                        dp = chosen.get("dot_power", 15)
                        dt = chosen.get("dot_turns", 3)
                        defender.setdefault("dots", []).append({"dmg": dp, "turns": dt})
                        battle.log.append(f"   ☠️ {defender['name']} recibe {dp} daño/turno x{dt} turnos!")
                    elif atype == "team_heal":
                        hp_bonus = chosen.get("power", 40)
                        atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                        for fig in atk_team:
                            if fig["hp"] > 0:
                                fig["hp"] = min(fig["max_hp"], fig["hp"] + hp_bonus)
                                battle.log.append(f"   🌸 {fig['name']} +{hp_bonus}HP")

        # ── PAPYRUS ──────────────────────────────────────────────

        elif stype == "papyrus_pose":
            atk_b = skill.get("atk_buff", 10)
            def_b = skill.get("def_buff", 10)
            attacker["atk"]     = attacker.get("atk", 0) + atk_b
            attacker["defense"] = attacker.get("defense", 0) + def_b
            battle.log.append(f"💀 **Papyrus** hace una pose increíblemente genial! NYEH HEH HEH!")
            battle.log.append(f"   ⚔️ +{atk_b} ATK · 🛡️ +{def_b} DEF permanentes!")

        elif stype == "papyrus_laugh":
            self_h = skill.get("self_heal", 35)
            ally_h = skill.get("ally_heal", 20)
            attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + self_h)
            atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
            healed = []
            for fig in atk_team:
                if fig is not attacker and fig["hp"] > 0:
                    fig["hp"] = min(fig["max_hp"], fig["hp"] + ally_h)
                    healed.append(f"{fig['emoji']} {fig['name']} +{ally_h}HP")
            battle.log.append(f"💀 **{attacker['name']}**: NYEH HEH HEH! ¡A seguir luchando!")
            battle.log.append(f"   💚 {attacker['name']} +{self_h}HP" + (f" · {' · '.join(healed)}" if healed else ""))

        # ── FLOWEY ───────────────────────────────────────────────

        elif stype == "flowey_save_reload":
            uses = attacker.get("save_reload_uses", 0)
            if uses == 0:
                # Primer uso: guardar estado
                snapshot = {
                    "hp":      attacker["hp"],
                    "atk":     attacker.get("atk", 0),
                    "defense": attacker.get("defense", 0),
                    "energy":  attacker.get("energy", 0),
                }
                atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                snapshot["team_hps_atk"] = [f["hp"] for f in atk_team]
                snapshot["team_hps_def"] = [f["hp"] for f in def_team]
                attacker["save_snapshot"] = snapshot
                attacker["save_reload_uses"] = 1
                battle.log.append(f"🌼 **Flowey** guarda la partida... 💾 *Savefile guardado!*")
            else:
                # Segundo uso: restaurar estado
                snap = attacker.get("save_snapshot", {})
                if snap:
                    attacker["hp"]      = snap["hp"]
                    attacker["atk"]     = snap["atk"]
                    attacker["defense"] = snap["defense"]
                    attacker["energy"]  = snap["energy"]
                    atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                    def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                    for i, fig in enumerate(atk_team):
                        if i < len(snap["team_hps_atk"]):
                            fig["hp"] = max(0, snap["team_hps_atk"][i])
                    for i, fig in enumerate(def_team):
                        if i < len(snap["team_hps_def"]):
                            fig["hp"] = max(0, snap["team_hps_def"][i])
                    attacker["save_reload_uses"] = 0
                    attacker.pop("save_snapshot", None)
                    battle.log.append(f"🌼 **Flowey** regresa el tiempo... ⏪ *Estado restaurado!*")
                else:
                    battle.log.append(f"🌼 **Flowey** no tiene nada guardado...")

        elif stype == "flowey_fake_help":
            uses = attacker.get("fake_help_uses", 0) + 1
            attacker["fake_help_uses"] = uses
            if uses <= 2:
                # "Curación" al oponente
                defender["hp"] = min(defender["max_hp"], defender["hp"] + 5)
                battle.log.append(f"🌼 **Flowey**: ¡Hola amigo! Toma estas balitas de amistad~")
                battle.log.append(f"   💚 {defender['name']} +5 HP... ¿de verdad confías en él?")
            else:
                # Tercer uso: DAÑO REAL
                dmg_fh = skill.get("power", 40)
                defender["hp"] = max(0, defender["hp"] - dmg_fh)
                attacker["fake_help_uses"] = 0
                battle.log.append(f"🌼 **Flowey**: Jajaja, ¿de verdad pensaste que te iba a ayudar?")
                battle.log.append(f"   ☠️ ¡{dmg_fh} de daño real!")

        elif stype == "flowey_soul":
            uses = attacker.get("soul_uses", 0) + 1
            attacker["soul_uses"] = uses
            hp_gain = skill.get("hp_per_soul", 10)
            if uses <= 6:
                attacker["max_hp"] += hp_gain
                attacker["hp"]     += hp_gain
                battle.log.append(f"🌼 **Flowey** roba un alma... ({uses}/7)")
                battle.log.append(f"   ❤️ +{hp_gain} HP permanente! HP: {attacker['hp']}/{attacker['max_hp']}")
            else:
                # 7mo uso: desbloquear pasiva OMEGA
                attacker["omega_unlocked"] = True
                battle.log.append(f"🌼 **Flowey** ha recolectado 7 almas...")
                battle.log.append(f"   🌸 **PASIVA OMEGA DESBLOQUEADA.** Si muere ahora... evolucionará.")

        elif stype == "omega_its_the_end":
            splash = skill.get("power", 110)
            # Matar activo enemigo
            defender["hp"] = 0
            battle.log.append(f"🌸 **OMEGA FLOWEY**: ¡JAJAJAJA! ¡TERMINARE CON TODOS USTEDES!")
            # 110 a los otros 2 enemigos
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            for fig in def_team:
                if fig is not defender and fig["hp"] > 0:
                    fig["hp"] = max(0, fig["hp"] - splash)
                    battle.log.append(f"   ☠️ {fig['emoji']} {fig['name']} -{splash} HP!")
            # 110 a aliados y Flowey muere
            atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
            for fig in atk_team:
                if fig is not attacker and fig["hp"] > 0:
                    fig["hp"] = max(0, fig["hp"] - splash)
                    battle.log.append(f"   💥 {fig['emoji']} {fig['name']} -{splash} HP (daño propio)!")
            attacker["hp"] = 0
            battle.log.append(f"   💀 **OMEGA FLOWEY** cayó en su propia explosión...")


    # ── Halloween candy drop al matar una figura ─────────────────────────
    if defender["hp"] <= 0:
        _atk_variant = attacker.get("variant_passive")
        if _atk_variant == "halloween_stun":
            import random as _r
            if _r.randint(1, 100) <= 30:
                from database import load_db as _ldb, save_db as _sdb, get_user as _gu
                _uid = battle.p1 if battle.turn == 1 else battle.p2
                if _uid and _uid != 0:
                    _db = _ldb(); _u = _gu(_db, _uid)
                    if _u:
                        _u.setdefault("ingredients", {})["🍬"] = _u["ingredients"].get("🍬", 0) + 1
                        _sdb(_db)
                        battle.log.append("   🍬 **Halloween**: ¡Encontraste **Dulces** al ganar!")
    # ─────────────────────────────────────────────────────────────────────

    if defender["hp"] <= 0:
        # Pasiva de Gamer64: revive una vez con 80% HP
        if defender.get("passive_revive"):
            defender["passive_revive"] = False
            revive_hp = max(1, int(defender["max_hp"] * 0.80))
            defender["hp"] = revive_hp
            defender["energy"] = 0
            battle.log.append(f"💫 **{defender['emoji']} {defender['name']}** se cansó de rodeos, ¡se arranca el brazo y entra a su **Fase 2**!")
            battle.log.append(f"   Se levanta con **{revive_hp} HP** (80% de su vida máxima)!")

        # Pasiva OMEGA de Flowey: evoluciona a Omega Flowey si desbloqueó la pasiva
        elif defender.get("key") == "flowey" and defender.get("omega_unlocked"):
            def_team     = battle.p2_team if battle.turn == 1 else battle.p1_team
            def_idx_attr = "p2_active"    if battle.turn == 1 else "p1_active"
            idx = getattr(battle, def_idx_attr)
            # Transformar en Omega Flowey
            omega = make_fighter("omega_flowey", {"level": defender.get("level", 1), "xp": 0, "stat_ups": {}})
            def_team[idx] = omega
            battle.log.append(f"🌼 **Flowey** cae... pero las 7 almas reaccionan...")
            battle.log.append(f"   🌸 ¡¡**OMEGA FLOWEY** ha despertado!!")
            # Logro Kirby si fue absorbido por Kirby
            if defender.get("absorbed_by_kirby"):
                battle._kirby_absorbed_omega = True
            battle.turn = 2 if battle.turn == 1 else 1
            await finish_turn(interaction, battle, channel_id)
            return
            battle.turn = 2 if battle.turn == 1 else 1
            await finish_turn(interaction, battle, channel_id)
            return

        # Pasiva de OG GAMER 64: cambio de fase al morir (1→2→3→4→muerte definitiva)
        if defender.get("key") == "og_gamer64":
            current_phase = defender.get("og_phase", 1)
            if current_phase < 4:
                next_phase = current_phase + 1
                defender["og_phase"] = next_phase
                # Buffs por fase: +HP, +ATK, +DEF, +VEL
                phase_buffs = {
                    2: {"hp": 30,  "atk": 5,  "defense": 5,  "label": "🟣 FASE 2 — Glitched"},
                    3: {"hp": 60,  "atk": 10, "defense": 10, "label": "🟡 FASE 3 — Ki"},
                    4: {"hp": 100, "atk": 20, "defense": 20, "label": "🔴 FASE 4 — Godlike"},
                }
                buffs = phase_buffs[next_phase]
                new_max_hp = defender["max_hp"] + buffs["hp"]
                defender["max_hp"] = new_max_hp
                defender["hp"] = new_max_hp
                defender["atk"] = defender["atk"] + buffs["atk"]
                defender["defense"] = defender["defense"] + buffs["defense"]
                defender["energy"] = 0
                # Reemplazar habilidades por las de la nueva fase
                all_skills = FIGURE_SKILLS.get("og_gamer64", [])
                defender["skills"] = [sk for sk in all_skills if sk.get("phase") == next_phase]
                battle.log.append(f"💀 ¡**ＯＧ　ＧＡＭＥＲ　６４** no puede morir así!")
                battle.log.append(f"🔱 ¡Entra en **{buffs['label']}**!")
                battle.log.append(f"   ❤️ +{buffs['hp']} HP máx · ⚔️ +{buffs['atk']} ATK · 🛡️ +{buffs['defense']} DEF · ¡Vida completa!")
                battle.turn = 2 if battle.turn == 1 else 1
                await finish_turn(interaction, battle, channel_id)
                return
            # Fase 4 → muerte definitiva, continúa el flujo normal

        def_team     = battle.p2_team if battle.turn == 1 else battle.p1_team
        def_idx_attr = "p2_active"    if battle.turn == 1 else "p1_active"
        current_def_idx = getattr(battle, def_idx_attr)

        # ¿Queda alguna figura viva en el equipo defensor?
        if not battle.any_alive(def_team):
            # Todo el equipo cayó → fin de batalla
            await end_battle(interaction, battle, channel_id, winner_turn=battle.turn)
            return

        # Buscar siguiente figura viva
        next_idx = battle.next_alive(def_team, current_def_idx)
        if next_idx is None:
            # Fallback: buscar desde el inicio
            next_idx = next((i for i, f in enumerate(def_team) if f["hp"] > 0), None)

        if next_idx is not None:
            setattr(battle, def_idx_attr, next_idx)
            new_fig = def_team[next_idx]
            battle.log.append(f"💀 **{defender['name']}** fue derrotado!")
            battle.log.append(f"🔄 ¡Entra **{new_fig['emoji']} {new_fig['name']}**!")
            # Registrar kill en el atacante para el LOVE Check de Sans
            attacker["total_kills"] = attacker.get("total_kills", 0) + 1
            # Pasiva Papelemental: 20% de que aparezca un círculo elemental al derrotar una figura
            if attacker.get("passive") == "papelemental" and random.random() < 0.20:
                circles = [
                    ("🔥 Brazos Desplegables", "dot", 10, 5),
                    ("💧 Agua", "water", 24, 4),
                    ("🔥 Fuego", "fire", 26, 0),
                    ("🌍 Tierra", "earth", 24, 0),
                    ("❄️ Hielo", "ice", 28, 3),
                ]
                circle = random.choice(circles)
                cname, ctype, cpower, cturns = circle
                battle.log.append(f"📄 **¡Círculo Papelemental activado!** {cname} aparece!")
                atk_team = battle.p1_team if battle.turn == 1 else battle.p2_team
                def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
                cur_def_idx = getattr(battle, "p2_active" if battle.turn == 1 else "p1_active")
                cur_def = def_team[cur_def_idx] if cur_def_idx < len(def_team) else None
                if ctype == "dot" and cur_def:
                    cur_def.setdefault("dots", []).append({"dmg": cpower, "turns": cturns})
                    battle.log.append(f"   ☠️ Brazos: {cur_def['name']} {cpower} daño/turno x{cturns} turnos!")
                elif ctype == "water" and cur_def:
                    dmg_w = battle.calc_damage(attacker["atk"], cur_def["defense"], cpower)
                    cur_def["hp"] = max(0, cur_def["hp"] - dmg_w)
                    cur_def["stun_turns"] = 2
                    cur_def["atk"] = max(1, int(cur_def["atk"] * 0.85))
                    cur_def["defense"] = max(0, int(cur_def["defense"] * 0.85))
                    battle.log.append(f"   💧 Agua: {cur_def['name']} -{dmg_w}HP, aturdido 2t, -15% ATK/DEF!")
                elif ctype == "fire":
                    for fig in def_team:
                        if fig["hp"] > 0:
                            dmg_f = battle.calc_damage(attacker["atk"], fig["defense"], cpower)
                            fig["hp"] = max(0, fig["hp"] - dmg_f)
                            fig.setdefault("dots", []).append({"dmg": 5, "turns": 3})
                            battle.log.append(f"   🔥 Fuego: {fig['name']} -{dmg_f}HP + burning!")
                elif ctype == "earth" and cur_def:
                    dmg_e = battle.calc_damage(attacker["atk"], cur_def["defense"], cpower)
                    cur_def["hp"] = max(0, cur_def["hp"] - dmg_e)
                    cur_def["force_switch_turns"] = 1
                    battle.log.append(f"   🌍 Tierra: {cur_def['name']} -{dmg_e}HP y forzado a cambiar!")
                elif ctype == "ice" and cur_def:
                    dmg_i = battle.calc_damage(attacker["atk"], cur_def["defense"], cpower)
                    cur_def["hp"] = max(0, cur_def["hp"] - dmg_i)
                    cur_def["stun_turns"] = 3
                    cur_def.setdefault("dots", []).append({"dmg": 8, "turns": 3})
                    battle.log.append(f"   ❄️ Hielo: {cur_def['name']} -{dmg_i}HP, frozen 3t (8 daño/turno)!")
            # También guardar en la DB del usuario para kills globales (LOVE Check permanente)
            _register_kill_for_love(attacker.get("owner_id"), battle)
            battle.turn = 2 if battle.turn == 1 else 1
            await finish_turn(interaction, battle, channel_id)
            return
        else:
            await end_battle(interaction, battle, channel_id, winner_turn=battle.turn)
            return

    # Metamorphosis de Jevil: forzar cambio al final del turno
    if getattr(battle, "metamorphosis_turns", 0) > 0:
        battle.metamorphosis_turns -= 1
        for team, idx_attr in [(battle.p1_team, "p1_active"), (battle.p2_team, "p2_active")]:
            cur = getattr(battle, idx_attr)
            alive_others = [i for i, f2 in enumerate(team) if i != cur and f2["hp"] > 0]
            if alive_others:
                new_idx = random.choice(alive_others)
                setattr(battle, idx_attr, new_idx)
                battle.log.append(f"🃏 **¡METAMORPHOSIS!** ¡{team[new_idx]['emoji']} {team[new_idx]['name']} entra al campo!")
        if battle.metamorphosis_turns == 0:
            battle.log.append(f"🃏 El efecto de METAMORPHOSIS ha terminado.")

    # Jevil Passive: TRUE GOD OF CHAOS — 25% por turno de buff/debuff random a TODOS
    all_teams = list(battle.p1_team) + list(battle.p2_team)
    all_alive = [f for f in all_teams if f["hp"] > 0]
    for fig in all_alive:
        if fig.get("chaos_passive_active") and fig["hp"] > 0:
            if random.random() < 0.25:
                _ALL_FIGS_ALIVE = [f2 for f2 in all_alive]
                target = random.choice(_ALL_FIGS_ALIVE)
                _CHAOS_ALL = ["atk_up", "def_up", "hp_heal", "stun", "poison", "burning", "dizziness", "frozen"]
                eff = random.choice(_CHAOS_ALL)
                battle.log.append(f"🃏 **¡TRUE GOD OF CHAOS!** El caos afecta a **{target['name']}**...")
                if eff == "atk_up":
                    target["atk"] = int(target["atk"] * 1.15)
                    battle.log.append(f"   ⚔️ {target['name']} +15% ATK!")
                elif eff == "def_up":
                    target["defense"] = int(target["defense"] * 1.15)
                    battle.log.append(f"   🛡️ {target['name']} +15% DEF!")
                elif eff == "hp_heal":
                    h = random.randint(10, 25)
                    target["hp"] = min(target["max_hp"], target["hp"] + h)
                    battle.log.append(f"   💚 {target['name']} +{h}HP!")
                elif eff == "stun":
                    target["stun_turns"] = max(target.get("stun_turns", 0), 1)
                    battle.log.append(f"   😵 {target['name']} aturdido 1t!")
                elif eff == "poison":
                    target.setdefault("dots", []).append({"dmg": 6, "turns": 3})
                    battle.log.append(f"   ☠️ {target['name']} envenenado!")
                elif eff == "burning":
                    target.setdefault("dots", []).append({"dmg": 4, "turns": 4})
                    battle.log.append(f"   🔥 {target['name']} en llamas!")
                elif eff == "dizziness":
                    target["dizziness_turns"] = max(target.get("dizziness_turns", 0), 2)
                    battle.log.append(f"   💫 {target['name']} mareado!")
                elif eff == "frozen":
                    target["stun_turns"] = max(target.get("stun_turns", 0), 2)
                    target.setdefault("dots", []).append({"dmg": 3, "turns": 2})
                    battle.log.append(f"   ❄️ {target['name']} congelado!")

    # Cambiar turno
    battle.turn = 2 if battle.turn == 1 else 1
    await finish_turn(interaction, battle, channel_id)

async def finish_turn(interaction, battle: BattleState, channel_id: int):
    """Actualiza el embed y, si toca el bot, ejecuta su turno."""
    view = get_battle_view(battle)
    embed = battle.get_embed()

    if battle.is_bot and battle.turn == 2:
        await _safe_edit(interaction, battle, embed, None)
        await asyncio.sleep(1.2)
        await bot_turn(interaction, battle, channel_id)
        return

    await _safe_edit(interaction, battle, embed, view)

async def _safe_edit(interaction, battle, embed, view):
    """Edita el mensaje de batalla de forma segura.
    Si la interaction ya expiró (>15 min), edita directamente el mensaje."""
    try:
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.edit_original_response(embed=embed, view=view)
    except Exception:
        # Fallback: editar el mensaje directamente si la interaction expiró
        try:
            if battle.message:
                await battle.message.edit(embed=embed, view=view)
        except Exception as e:
            print(f"⚠️ No se pudo editar mensaje de batalla: {e}")

async def bot_turn(interaction, battle: BattleState, channel_id: int):
    """IA del bot: ataque básico siempre disponible + habilidades cuando hay energía."""
    f = battle.current_p2()
    p1_fig = battle.current_p1()
    battle.log = []

    # Filtrar habilidades disponibles
    available = [i for i, sk in enumerate(f["skills"]) if f["energy"] >= sk["cost"]]

    # Prioridad: curación si HP < 40%
    chosen_idx = None
    hp_ratio = f["hp"] / f["max_hp"]
    if hp_ratio < 0.4:
        heal_skills = [i for i in available if f["skills"][i]["type"] in ("heal",)]
        if heal_skills:
            chosen_idx = heal_skills[-1]

    # Si hay habilidad disponible y no eligió curar, usarla con 60% de probabilidad
    if chosen_idx is None and available and random.random() < 0.6:
        chosen_idx = max(available, key=lambda i: f["skills"][i]["cost"])

    if chosen_idx is not None:
        # Usar habilidad especial
        skill = f["skills"][chosen_idx]
        f["energy"] -= skill["cost"]
        stype = skill["type"]

        if stype == "damage":
            dmg = battle.calc_damage(f["atk"], p1_fig["defense"], skill["power"])
            p1_fig["hp"] = max(0, p1_fig["hp"] - dmg)
            battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}** → **{dmg}** daño!")
            if skill.get("stun"):
                stun_t = skill.get("stun_turns", 1)
                if stun_t > 1:
                    p1_fig["stun_turns"] = stun_t
                else:
                    p1_fig["stunned"] = True
                battle.log.append(f"   😵 ¡**{p1_fig['name']}** queda aturdido!")
            if skill.get("aoe"):
                sec = skill.get("aoe_secondary_power", skill["power"])
                for fig in battle.p1_team:
                    if fig is not p1_fig and fig["hp"] > 0:
                        sd = battle.calc_damage(f["atk"], fig["defense"], sec)
                        fig["hp"] = max(0, fig["hp"] - sd)
                        battle.log.append(f"   💥 AOE → {fig['emoji']} {fig['name']} -{sd}HP")
            if skill.get("force_switch"):
                turns = skill.get("force_switch_turns", 3)
                p1_fig["force_locked"] = turns
                next_idx = battle.next_alive(battle.p1_team, battle.p1_active)
                if next_idx:
                    battle.p1_active = next_idx
                    battle.log.append(f"   🔒 **{p1_fig['name']}** bloqueada {turns} turnos!")

        elif stype == "heal":
            heal = max(1, int(skill["power"] + random.randint(-3, 5)))
            if not f.get("no_heal"):
                f["hp"] = min(f["max_hp"], f["hp"] + heal)
                battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}** → +**{heal}** HP!")
            if skill.get("team_heal"):
                th = skill.get("team_heal_power", 10)
                for ally in battle.p2_team:
                    if ally is not f and ally["hp"] > 0:
                        ally["hp"] = min(ally["max_hp"], ally["hp"] + th)

        elif stype == "drain":
            f["hp"] = max(1, f["hp"] - skill["power"])
            bonus = skill.get("bar_bonus", 20)
            f["energy"] = min(ENERGY_MAX, f["energy"] + bonus)
            battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}**! (+{bonus}⚡)")

        elif stype == "drain_fill":
            f["hp"] = max(1, f["hp"] - skill["power"])
            if skill.get("fill_bar"): f["energy"] = ENERGY_MAX
            if skill.get("no_heal"): f["no_heal"] = True
            ed = skill.get("dmg_enemy", 0)
            if ed > 0:
                p1_fig["hp"] = max(0, p1_fig["hp"] - ed)
            battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}**! (-{skill['power']}HP propio, -{ed} al rival)")

        elif stype == "dot":
            if "dots" not in p1_fig: p1_fig["dots"] = []
            p1_fig["dots"].append({"dmg": skill["power"], "turns": skill.get("dot_turns", 3)})
            battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}**! ({skill['power']} daño/turno x{skill.get('dot_turns',3)})")

        elif stype == "team_atk_buff":
            buff = skill.get("atk_buff", 15)
            for ally in battle.p2_team:
                if ally["hp"] > 0:
                    ally["atk_buff"] = ally.get("atk_buff", 0) + buff
            battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}**! (Todo el equipo +{buff} ATK)")

        elif stype == "bad_update":
            dmg_roll = random.choice([4, 6, 8])
            heal_roll = dmg_roll // 2
            for fig in battle.p1_team:
                if fig["hp"] > 0:
                    fig["hp"] = max(0, fig["hp"] - dmg_roll)
            for ally in battle.p2_team:
                if ally["hp"] > 0 and not ally.get("no_heal"):
                    ally["hp"] = min(ally["max_hp"], ally["hp"] + heal_roll)
            battle.log.append(f"🤖 **{f['emoji']} {f['name']}** usa **{skill['name']}**! ({dmg_roll} a todos los rivales, +{heal_roll} a aliados)")

        elif stype == "fast_kill":
            # Requiere 3 usos seguidos — al 3ro dispara
            charges = attacker.get("fast_kill_charges", 0) + 1
            needed = skill.get("charges_needed", 3)
            attacker["fast_kill_charges"] = charges
            if charges >= needed:
                attacker["fast_kill_charges"] = 0
                dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
                defender["hp"] = max(0, defender["hp"] - dmg)
                battle.log.append(f"🔪 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** → ¡**{dmg}** DAÑO MASIVO!")
                battle.log.append(f"   _{skill['desc']}_")
            else:
                remaining = needed - charges
                battle.log.append(f"🔪 **{attacker['emoji']} {attacker['name']}** prepara **{skill['name']}**... ({charges}/{needed})")
                battle.log.append(f"   ¡{remaining} turno(s) más para activar!")

        elif stype == "revive_team":
            # 1x1x1x1 — se daña a sí mismo y revive figuras aliadas caídas
            self_dmg = skill["power"]
            attacker["hp"] = max(1, attacker["hp"] - self_dmg)
            revive_hp  = skill.get("revive_hp", 20)
            revive_atk = skill.get("revive_atk", 10)
            revive_def = skill.get("revive_def", 15)
            revived = []
            for ally in atk_team:
                if ally["hp"] <= 0 and ally is not attacker:
                    ally["hp"] = revive_hp
                    ally["atk"] = revive_atk
                    ally["defense"] = revive_def
                    ally["energy"] = 0
                    if skill.get("revive_poison"):
                        ally["revive_poisoner"] = True  # envenena al atacar
                    revived.append(f"{ally['emoji']} {ally['name']}")
            battle.log.append(f"⚔️ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** (-{self_dmg} HP propio)!")
            if revived:
                battle.log.append(f"   💀➡️💚 ¡Reviven: {', '.join(revived)}! (HP:{revive_hp} ATK:{revive_atk} DEF:{revive_def})")
                battle.log.append(f"   ☠️ ¡Las figuras revividas envenenarán al atacar!")
            else:
                battle.log.append(f"   No había figuras caídas que revivir.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "heal_self_small":
            # Shedletsky — Chicken Leg: cura solo a sí mismo 20-25 HP
            heal_amt = random.randint(skill.get("heal_min", 20), skill.get("heal_max", 25))
            if not attacker.get("no_heal"):
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amt)
            battle.log.append(f"🍗 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   💚 {attacker['name']} se cura +{heal_amt}HP")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "heal_team_self":
            # Shedletsky — Chicken Legs: +30 propio, +25 aliados
            self_heal = skill["power"]
            team_heal = skill.get("team_heal_power", 25)
            if not attacker.get("no_heal"):
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + self_heal)
            healed = []
            for ally in atk_team:
                if ally is not attacker and ally["hp"] > 0 and not ally.get("no_heal"):
                    ally["hp"] = min(ally["max_hp"], ally["hp"] + team_heal)
                    healed.append(f"{ally['emoji']} {ally['name']} +{team_heal}HP")
            battle.log.append(f"🍗 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   💚 {attacker['name']} +{self_heal}HP | {' | '.join(healed) if healed else 'sin aliados vivos'}")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "switch_sword":
            # Shedletsky — muestra menú de espadas (se maneja en get_battle_view)
            # Este tipo no hace nada directamente — la selección se hace via botón especial
            battle.log.append(f"🐔 **{attacker['emoji']} {attacker['name']}** guarda su espada actual...")
            battle.log.append(f"   _(Elige tu espada en el menú)_")

        elif stype == "slash":
            # Shedletsky — ataca con la espada activa y aplica su efecto
            sword = attacker.get("active_sword", "linked")
            dmg = battle.calc_damage(attacker["atk"], defender["defense"], skill["power"])
            SWORD_NAMES = {
                "linked":      "Linked Sword",
                "firebrand":   "Firebrand 🔥",
                "venomshank":  "Venomshank ☠️",
                "windforce":   "Windforce 🌪️",
                "darkheart":   "Darkheart 🖤",
                "illumina":    "Illumina ✨",
                "ghostwalker": "Ghostwalker 👻",
                "ice_dagger":  "Ice Dagger 🧊",
            }
            sword_name = SWORD_NAMES.get(sword, "Linked Sword")
            defender["hp"] = max(0, defender["hp"] - dmg)
            battle.log.append(f"⚔️ **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}** con {sword_name} → **{dmg}** daño!")

            # Efectos de espada
            if sword == "linked":
                pass  # sin efecto extra
            elif sword == "firebrand":
                attacker["fire_immune"] = True
                # Carga de fuego: daño extra al lanzarse
                dash_dmg = battle.calc_damage(attacker["atk"], defender["defense"], 20)
                defender["hp"] = max(0, defender["hp"] - dash_dmg)
                battle.log.append(f"   🔥 ¡{attacker['name']} se lanza con Firebrand! +{dash_dmg} daño extra!")
                battle.log.append(f"   🔥 ¡{attacker['name']} es inmune a Ice Dagger!")
                # Si Shedletsky tiene menos del 30% HP → +30 ATK a aliados
                hp_pct = attacker["hp"] / attacker["max_hp"]
                if hp_pct < 0.30:
                    for ally in atk_team:
                        if ally is not attacker and ally["hp"] > 0:
                            ally["atk_buff"] = ally.get("atk_buff", 0) + 30
                    battle.log.append(f"   🔥 ¡Shedletsky a baja vida! +30 ATK a todos los aliados!")
            elif sword == "venomshank":
                if "dots" not in defender: defender["dots"] = []
                defender["dots"].append({"dmg": 8, "turns": 3})
                battle.log.append(f"   ☠️ ¡{defender['name']} envenenado! (8 daño/turno x3)")
            elif sword == "windforce":
                defender["stunned"] = True
                battle.log.append(f"   🌪️ ¡{defender['name']} empujado y aturdido 1 turno!")
            elif sword == "darkheart":
                lifesteal = max(1, int(dmg * 0.4))
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + lifesteal)
                battle.log.append(f"   🖤 Robo de vida: +{lifesteal} HP a {attacker['name']}!")
            elif sword == "illumina":
                illumina_dmg = battle.calc_damage(attacker["atk"], defender["defense"], 80)
                defender["hp"] = max(0, defender["hp"] - illumina_dmg)
                battle.log.append(f"   ✨ ¡Illumina hace daño masivo adicional! -{illumina_dmg} HP!")
            elif sword == "ghostwalker":
                kills = attacker.get("ghostwalker_kills", 0)
                bonus = kills * 5
                attacker["atk"] = attacker["atk"] + bonus if bonus > 0 else attacker["atk"]
                battle.log.append(f"   👻 Ghostwalker: +{bonus} ATK acumulado ({kills} kills)")
            elif sword == "ice_dagger":
                if not defender.get("fire_immune"):
                    ice_charges = attacker.get("ice_dagger_charges", 0) + 1
                    attacker["ice_dagger_charges"] = ice_charges
                    if ice_charges >= 3:
                        attacker["ice_dagger_charges"] = 0
                        ice_dmg = 120  # daño fijo al 3er toque
                        defender["hp"] = max(0, defender["hp"] - ice_dmg)
                        battle.log.append(f"   🧊❄️ ¡ICE DAGGER CARGADA! **{ice_dmg}** daño masivo de hielo!")
                    else:
                        battle.log.append(f"   🧊 Ice Dagger cargando... ({ice_charges}/3 — mantén la espada equipada!)")
                else:
                    attacker["ice_dagger_charges"] = 0
                    battle.log.append(f"   🧊 Ice Dagger bloqueada por Firebrand!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "consumed_fury":
            # 50 daño al activo + 15 splash + impostor pierde 50% vida
            dmg_fury = 50
            defender["hp"] = max(0, defender["hp"] - dmg_fury)
            def_team_fury = battle.p2_team if battle.turn == 1 else battle.p1_team
            splash = skill.get("splash_dmg", 15)
            hit = []
            for fig in def_team_fury:
                if fig is not defender and fig["hp"] > 0:
                    fig["hp"] = max(0, fig["hp"] - splash)
                    hit.append(f"{fig['emoji']} {fig['name']} -{splash}HP")
            # El impostor pierde 50% de su vida en lugar de morir
            self_dmg = max(1, attacker["max_hp"] // 2)
            attacker["hp"] = max(1, attacker["hp"] - self_dmg)
            battle.log.append(f"💥 **{attacker['emoji']} {attacker['name']}** usa **{skill['name']}**!")
            battle.log.append(f"   💥 **{defender['name']}** recibe **{dmg_fury}** daño!")
            if hit:
                battle.log.append(f"   💥 Explosión: {' | '.join(hit)}")
            battle.log.append(f"   😵 **{attacker['name']}** pierde el 50% de su vida por la explosión!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "holy_buff":
            # Santa Vaca — evoluciona con DEF y ATK masivos
            attacker["defense"] = attacker.get("defense", 0) + skill.get("def_buff", 10000000000)
            attacker["atk"]     = attacker.get("atk", 0) + skill.get("atk_buff_holy", 1000000)
            attacker["holy_turns"] = skill.get("holy_turns", 20)
            battle.log.append(f"🐮 **SANTA VACA** usa **{skill['name']}**!")
            battle.log.append(f"   ¡LA VACA HA EVOLUCIONADO! +10B DEF | +1M ATK por 20 turnos! 🌟")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "holy_heal":
            # Santa Vaca — cura cantidad absurda a todo el equipo
            heal_amt = skill.get("heal_all", 10000000000000)
            for ally in atk_team:
                if ally["hp"] > 0:
                    ally["hp"] = min(ally["max_hp"], ally["hp"] + heal_amt)
            battle.log.append(f"🐮 **SANTA VACA** usa **{skill['name']}**!")
            battle.log.append(f"   🥩 Se arranca un trozo de sí misma... ¡y todo el equipo recibe {heal_amt:,} HP!")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "holy_nuke":
            # Santa Vaca — mata a TODAS las figuras enemigas
            def_team_holy = battle.p2_team if battle.turn == 1 else battle.p1_team
            killed = []
            for fig in def_team_holy:
                if fig["hp"] > 0:
                    fig["hp"] = 0
                    killed.append(f"{fig['emoji']} {fig['name']}")
            battle.log.append(f"🐮 **SANTA VACA** usa **{skill['name']}**...")
            battle.log.append(f"   ...")
            battle.log.append(f"   💀 **{', '.join(killed)}** {'han sido' if len(killed)>1 else 'ha sido'} aniquilado(s) instantáneamente.")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "lobster":
            # 0.01% de probabilidad de matar a TODAS las figuras del oponente
            roll = random.randint(1, 10000)
            def_team = battle.p2_team if battle.turn == 1 else battle.p1_team
            if roll == 1:
                for fig in def_team:
                    fig["hp"] = 0
                battle.log.append(f"🦞 **Lobster** usa **LOBSTER**...")
                battle.log.append(f"   ...")
                battle.log.append(f"   🦞 **¡LA LANGOSTA LO HA HECHO! ¡TODAS LAS FIGURAS ENEMIGAS ESTÁN MUERTAS!** 🦞")
            else:
                battle.log.append(f"🦞 **Lobster** usa **LOBSTER**...")
                battle.log.append(f"   ...")
                battle.log.append(f"   No pasa nada. (Como siempre)")
            battle.log.append(f"   _{skill['desc']}_")

        elif stype == "ban_hammer":
            if random.randint(1,2) == 1:
                p1_fig["hp"] = 0
                battle.log.append(f"🤖🔨 **¡BAN HAMMER!** **{p1_fig['name']}** eliminada!")
            else:
                alive = [fig for fig in battle.p2_team if fig["hp"] > 0 and fig is not f]
                if alive:
                    v = random.choice(alive)
                    v["hp"] = 0
                    battle.log.append(f"🤖🔨 Ban Hammer sale mal... ¡mata a **{v['name']}** aliada! 😂")

        elif stype in ("parry", "buff", "gamble", "gamble_fire"):
            # Para estos tipos el bot simplemente ataca normal
            chosen_idx = None

    if chosen_idx is None:
        # Ataque básico — siempre disponible, gana 20 energía
        f["energy"] = min(ENERGY_MAX, f["energy"] + ENERGY_PER_TURN + f.get("energy_bonus", 0))
        bonus_atk = f.pop("atk_buff", 0)
        max_power = max((sk.get("power", 0) for sk in f["skills"]), default=20)
        base_dmg = max(1, round(max_power / 2))
        dmg = max(1, base_dmg + (bonus_atk // 2) + random.randint(-2, 3) - (p1_fig["defense"] // 6))
        p1_fig["hp"] = max(0, p1_fig["hp"] - dmg)
        buff_txt = f" (+{bonus_atk} ATK)" if bonus_atk else ""
        battle.log.append(f"🤖 **{f['emoji']} {f['name']}** ataca básico{buff_txt} → **{dmg}** daño! (+20⚡)")
        if p1_fig.get("retributing"):
            retrib_dmg = max(1, dmg // 2)
            f["hp"] = max(0, f["hp"] - retrib_dmg)
            p1_fig["retrib_turns"] = p1_fig.get("retrib_turns", 1) - 1
            if p1_fig["retrib_turns"] <= 0:
                p1_fig["retributing"] = False
            battle.log.append(f"   🦷 **{p1_fig['name']}** devuelve **{retrib_dmg}** daño (¡Retribución!)!")
        if p1_fig.get("parrying"):
            p1_fig["parrying"] = False
            pct = p1_fig.get("parry_dmg_pct", 25)
            cdmg = int(p1_fig["max_hp"] * pct / 100)
            f["hp"] = max(0, f["hp"] - cdmg)
            battle.log.append(f"   ⚡ **{p1_fig['name']}** hace COUNTER y devuelve **{cdmg}** daño!")

    # ¿Cayó alguna figura del jugador?
    if p1_fig["hp"] <= 0:
        # Pasiva de Gamer64
        if p1_fig.get("passive_revive"):
            p1_fig["passive_revive"] = False
            revive_hp = max(1, int(p1_fig["max_hp"] * 0.80))
            p1_fig["hp"] = revive_hp
            p1_fig["energy"] = 0
            battle.log.append(f"💫 **{p1_fig['emoji']} {p1_fig['name']}** se cansó de rodeos, ¡se arranca el brazo y entra a su **Fase 2**!")
            battle.log.append(f"   Se levanta con **{revive_hp} HP** (80% de su vida máxima)!")
        # Pasiva de OG GAMER 64
        elif p1_fig.get("key") == "og_gamer64":
            current_phase = p1_fig.get("og_phase", 1)
            if current_phase < 4:
                next_phase = current_phase + 1
                p1_fig["og_phase"] = next_phase
                phase_buffs = {
                    2: {"hp": 30,  "atk": 5,  "defense": 5,  "label": "🟣 FASE 2 — Glitched"},
                    3: {"hp": 60,  "atk": 10, "defense": 10, "label": "🟡 FASE 3 — Ki"},
                    4: {"hp": 100, "atk": 20, "defense": 20, "label": "🔴 FASE 4 — Godlike"},
                }
                buffs = phase_buffs[next_phase]
                new_max_hp = p1_fig["max_hp"] + buffs["hp"]
                p1_fig["max_hp"] = new_max_hp
                p1_fig["hp"] = new_max_hp
                p1_fig["atk"] = p1_fig["atk"] + buffs["atk"]
                p1_fig["defense"] = p1_fig["defense"] + buffs["defense"]
                p1_fig["energy"] = 0
                all_skills = FIGURE_SKILLS.get("og_gamer64", [])
                p1_fig["skills"] = [sk for sk in all_skills if sk.get("phase") == next_phase]
                battle.log.append(f"💀 ¡**ＯＧ　ＧＡＭＥＲ　６４** no puede morir así!")
                battle.log.append(f"🔱 ¡Entra en **{buffs['label']}**!")
                battle.log.append(f"   ❤️ +{buffs['hp']} HP máx · ⚔️ +{buffs['atk']} ATK · 🛡️ +{buffs['defense']} DEF · ¡Vida completa!")
            else:
                # Fase 4 muerta → muerte definitiva
                if not battle.any_alive(battle.p1_team):
                    await end_battle(interaction, battle, channel_id, winner_turn=2)
                    return
                next_idx = battle.next_alive(battle.p1_team, battle.p1_active)
                if next_idx is None:
                    next_idx = next((i for i, f in enumerate(battle.p1_team) if f["hp"] > 0), None)
                if next_idx is not None:
                    battle.p1_active = next_idx
                    new_fig = battle.p1_team[next_idx]
                    battle.log.append(f"💀 **{p1_fig['name']}** fue derrotado definitivamente!")
                    battle.log.append(f"🔄 ¡Entra **{new_fig['emoji']} {new_fig['name']}**!")
                else:
                    await end_battle(interaction, battle, channel_id, winner_turn=2)
                    return
        else:
            # ¿Queda alguna figura viva?
            if not battle.any_alive(battle.p1_team):
                await end_battle(interaction, battle, channel_id, winner_turn=2)
                return
            next_idx = battle.next_alive(battle.p1_team, battle.p1_active)
            if next_idx is None:
                next_idx = next((i for i, f in enumerate(battle.p1_team) if f["hp"] > 0), None)
            if next_idx is not None:
                battle.p1_active = next_idx
                new_fig = battle.p1_team[next_idx]
                battle.log.append(f"💀 **{p1_fig['name']}** fue derrotado!")
                battle.log.append(f"🔄 ¡Entra **{new_fig['emoji']} {new_fig['name']}**!")
            else:
                await end_battle(interaction, battle, channel_id, winner_turn=2)
                return

    # Verificación extra: si la figura activa sigue muerta, buscar otra
    if battle.current_p1()["hp"] <= 0:
        if not battle.any_alive(battle.p1_team):
            await end_battle(interaction, battle, channel_id, winner_turn=2)
            return
        fallback = next((i for i, f in enumerate(battle.p1_team) if f["hp"] > 0), None)
        if fallback is not None:
            battle.p1_active = fallback
        else:
            await end_battle(interaction, battle, channel_id, winner_turn=2)
            return

    battle.turn = 1
    view = get_battle_view(battle)
    try:
        await battle.message.edit(embed=battle.get_embed(), view=view)
    except Exception:
        try:
            await interaction.edit_original_response(embed=battle.get_embed(), view=view)
        except Exception as e:
            print(f"⚠️ bot_turn edit error: {e}")

async def end_battle(interaction, battle: BattleState, channel_id: int, winner_turn: int):
    """Cierra la batalla y da recompensas."""
    p1_won = (winner_turn == 1)
    winner_id = battle.p1 if p1_won else battle.p2
    loser_id  = battle.p2 if p1_won else battle.p1

    # Asegurarse de que los HP queden en 0
    for f in battle.p1_team + battle.p2_team:
        f["hp"] = max(0, f["hp"])

    embed = battle.get_embed(title="🏆 ¡FIN DE LA BATALLA!")

    if p1_won:
        win_text = f"🎉 ¡<@{winner_id}> ganó con su equipo!"
    else:
        win_text = f"🤖 ¡El BOT ganó!" if battle.is_bot else f"🎉 ¡<@{winner_id}> ganó con su equipo!"
    embed.add_field(name="🏆 GANADOR", value=win_text, inline=False)

    db = load_db()
    # Recompensas al ganador
    if p1_won or not battle.is_bot:
        winner_data = get_user(db, winner_id)
        if winner_data:
            # ── Recompensas especiales 7v3 del Impostor Negro ────────────────
            if getattr(battle, "impostor_7v3", False) and p1_won:
                ts  = getattr(battle, "impostor_team_size", 3)
                rew = IMPOSTOR_REWARDS.get(ts, IMPOSTOR_REWARDS[7])
                winner_data["coins"] = winner_data.get("coins",0) + rew["coins"]
                winner_data["xp"]    = winner_data.get("xp",0)    + rew["xp"]
                _check_player_levelup(winner_data)
                # Auto-niveles a las figuras del equipo
                if rew["auto_levels"] > 0:
                    for fd in winner_data.get("figures",[]):
                        if fd["key"] in battle.p1_team_keys:
                            for _ in range(rew["auto_levels"]):
                                fd["level"] = min(FIGURE_LEVEL_MAX, fd.get("level",1) + 1)
                # Recetas bonus
                if rew["recipe_sheets"] > 0:
                    all_recipe_ids = list(range(len(RECIPES))) if "RECIPES" in globals() else []
                    owned_recipes  = winner_data.get("recipe_sheets",[])
                    available_rec  = [r for r in all_recipe_ids if r not in owned_recipes]
                    random.shuffle(available_rec)
                    for r in available_rec[:rew["recipe_sheets"]]:
                        winner_data.setdefault("recipe_sheets",[]).append(r)
                # Logro
                new_achs = check_achievements(winner_data, {"boss_id":"impostor_negro","team_size":ts})
                rew_text = (
                    f"{'🏆 ¡LOGRO DESBLOQUEADO! · ' if rew['achievement'] and new_achs else ''}"
                    f"+{rew['coins']:,}🪙"
                    + (f" · +{rew['auto_levels']} niveles auto" if rew["auto_levels"] else "")
                    + (f" · +{rew['recipe_sheets']} receta(s)" if rew["recipe_sheets"] else "")
                    + (f" · +{rew['xp']} XP" if rew["xp"] else "")
                    + (f"\n*(Usaste {ts} figuras)*" if ts > 3 else "")
                )
                embed.add_field(name="🔪 Recompensas DEFEAT", value=rew_text, inline=False)
                for aid in new_achs:
                    ach = ACHIEVEMENTS.get(aid,{})
                    embed.add_field(name=f"🏅 {ach.get('name','Logro')}", value=ach.get("desc",""), inline=True)
            else:
                # Recompensas normales
                winner_data["wins"] = winner_data.get("wins", 0) + 1
                winner_data["coins"] = winner_data.get("coins", 0) + COINS_WIN
                winner_data["xp"] = winner_data.get("xp", 0) + XP_PER_WIN
                _check_player_levelup(winner_data)
                # XP a las figuras del equipo ganador
                team_keys = battle.p1_team_keys if p1_won else battle.p2_team_keys
                leveled_figs = []
                for fig_data in winner_data["figures"]:
                    if fig_data["key"] in team_keys:
                        if fig_data.get("level", 1) < FIGURE_LEVEL_MAX:
                            fig_data["xp"] = fig_data.get("xp", 0) + XP_PER_WIN // 3
                            if check_figure_levelup(fig_data):
                                leveled_figs.append(fig_data)
                if leveled_figs:
                    fig_names = [FIGURES.get(fd["key"], {}).get("name", fd["key"]) for fd in leveled_figs]
                    embed.add_field(name="⬆️ ¡Level Up!", value=f"{'  '.join(fig_names)} subieron de nivel. Usa `/subirstat`.", inline=False)

                # Logros normales
                new_achs = check_achievements(winner_data, {
                    "boss_id": getattr(battle, "bot_id", ""),
                    "team_size": len(getattr(battle, "p1_team_keys", [])),
                })
                for aid in new_achs:
                    ach = ACHIEVEMENTS.get(aid, {})
                    embed.add_field(name=f"🏅 {ach.get('name','Logro')}", value=ach.get("desc",""), inline=True)

    # Recompensas al perdedor
    if not battle.is_bot or not p1_won:
        loser_data = get_user(db, loser_id)
        if loser_data:
            loser_data["losses"] = loser_data.get("losses", 0) + 1
            loser_data["coins"] = loser_data.get("coins", 0) + COINS_LOSS
    elif battle.is_bot and not p1_won:
        p1_data = get_user(db, battle.p1)
        if p1_data:
            p1_data["losses"] = p1_data.get("losses", 0) + 1
            p1_data["coins"] = p1_data.get("coins", 0) + COINS_LOSS

    save_db(db)
    embed.add_field(name="💰 Recompensas", value=f"Ganador: +{COINS_WIN}🪙 +{XP_PER_WIN}XP | Perdedor: +{COINS_LOSS}🪙", inline=False)

    # Dar ingrediente al ganador si tiene suerte (40% de prob)
    if winner_id and winner_id != 0 and random.randint(1, 100) <= BATTLE_INGREDIENT_DROP_CHANCE:
        db_ing = load_db()
        winner_ing = get_user(db_ing, winner_id)
        if winner_ing:
            ing = give_battle_ingredient(winner_ing)
            save_db(db_ing)
            ing_name = INGREDIENTS.get(ing, "")
            embed.add_field(
                name="🧑‍🍳 ¡Ingrediente encontrado!",
                value=f"¡{winner_ing['name']} consiguió {ing} **{ing_name}** para cocinar!",
                inline=False
            )

    if channel_id in active_battles:
        del active_battles[channel_id]

    try:
        await _safe_edit(interaction, battle, embed, None)
    except Exception as e:
        print(f"⚠️ end_battle edit error: {e}")

    # Drops de misión activa (quest) — post-batalla
    db3 = load_db()
    winner3 = get_user(db3, winner_id)
    if winner3:
        changed = False
        for qid in winner3.get("active_quests", []):
            prev = winner3.get("quest_progress", {}).get(qid, 0)
            await check_quest_drops(winner3, qid, interaction.channel, db3)
            if winner3.get("quest_progress", {}).get(qid, 0) != prev:
                changed = True
        if changed:
            save_db(db3)

