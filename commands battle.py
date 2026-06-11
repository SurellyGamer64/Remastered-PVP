"""
commands_battle.py — Comandos de batalla (/pvpbot, /retar, /multiplayer, /ranking, /reset).
"""
import random
import asyncio
import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import FIGURES, FIGURE_SKILLS, apply_level_bonus
from battle import (
    active_battles, pending_pvp,
    BattleState, get_battle_view, make_fighter,
    bot_turn, end_battle,
)
from bosses import BOT_ROSTER
from economy import ACHIEVEMENTS, check_achievements

    pos_names = ["🥇 Frontal", "🥈 Centro", "🥉 Trasero"]
    pos_desc  = ["primera en entrar al combate", "entra si la frontal cae", "la última en combatir"]
    figs = user.get("figures", [])

    options = []
    for i, fig_data in enumerate(figs):
        fig = FIGURES.get(fig_data["key"])
        if fig:
            lvl = fig_data.get("level", 1)
            raw_emoji = fig["emoji"]
            # Discord SelectOption acepta emojis unicode o PartialEmoji para emojis personalizados
            # Si el emoji tiene formato <:name:id>, parsearlo como PartialEmoji
            if raw_emoji.startswith("<:") or raw_emoji.startswith("<a:"):
                try:
                    emoji_obj = discord.PartialEmoji.from_str(raw_emoji)
                except Exception:
                    emoji_obj = None
            else:
                emoji_obj = raw_emoji
            option_kwargs = dict(
                label=f"#{i+1} {fig['name']} (Nv.{lvl})",
                value=str(i),
                description=f"{fig['rarity'].upper()} | ATK:{apply_level_bonus(fig['attack'],lvl)} HP:{apply_level_bonus(fig['hp'],lvl)}"
            )
            if emoji_obj:
                option_kwargs["emoji"] = emoji_obj
            options.append(discord.SelectOption(**option_kwargs))

    select = discord.ui.Select(
        placeholder=f"Elige tu figura {pos_names[step]}...",
        options=options[:25],  # Discord limita a 25 opciones por Select
        custom_id=f"equip_step_{step}"
    )

    async def select_callback(inter: discord.Interaction):
        chosen_idx = int(select.values[0])
        db2 = load_db()
        usr2 = get_user(db2, inter.user.id)
        team = usr2.get("team", [None, None, None])
        while len(team) < 3: team.append(None)
        team[step] = chosen_idx
        usr2["team"] = team
        save_db(db2)

        fig_data = usr2["figures"][chosen_idx]
        fig = FIGURES[fig_data["key"]]

        if step < 2:
            # Continuar al siguiente paso
            await inter.response.edit_message(
                content=f"✅ {pos_names[step]}: **{fig['emoji']} {fig['name']}** — Ahora elige la {pos_names[step+1]}",
                view=None
            )
            await show_equip_menu(inter, usr2, step + 1)
        else:
            # Equipo completo
            team_final = usr2["team"]
            resumen = []
            for i, idx in enumerate(team_final):
                if idx is not None and idx < len(usr2["figures"]):
                    fd = usr2["figures"][idx]
                    fg = FIGURES.get(fd["key"])
                    if fg:
                        resumen.append(f"{pos_names[i]}: {fg['emoji']} **{fg['name']}**")
            embed = discord.Embed(
                title="✅ ¡Equipo armado!",
                description="\n".join(resumen),
                color=0x2ecc71
            )
            embed.set_footer(text="¡Tu equipo está listo para batallar!")
            await inter.response.edit_message(content=None, embed=embed, view=None)

    select.callback = select_callback
    view = discord.ui.View(timeout=60)
    view.add_item(select)

    msg = f"**Paso {step+1}/3** — Elige tu figura **{pos_names[step]}** ({pos_desc[step]})"
    if hasattr(interaction, 'response') and not interaction.response.is_done():
        await interaction.response.send_message(msg, view=view, ephemeral=True)
    else:
        await interaction.followup.send(msg, view=view, ephemeral=True)


# ============================================================
#  BOTS RIVALES — dificultad progresiva + jefe final
# ============================================================
BOT_ROSTER = [
    {
        "id": "facil",
        "name": "🪆 Maniquí de Combate",
        "desc": "Solo está ahí para recibir golpes. No te pongas nervioso.",
@bot.tree.command(name="pvpbot", description="Elige un rival bot y batalla con tu equipo")
async def pvpbot(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    if interaction.channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa en este canal.", ephemeral=True)
        return

    owned = user.get("figures", [])
    if not owned:
        await interaction.response.send_message("❌ No tienes figuras. Compra en `/tienda`.", ephemeral=True)
        return

    # Mostrar selector de bot rival
    embed = discord.Embed(
        title="⚔️ Elige tu rival",
        description="Selecciona contra quién quieres batallar:",
        color=0x3498db
    )
    for b in BOT_ROSTER:
        team_preview = " | ".join(FIGURES[k]["emoji"] + " " + FIGURES[k]["name"] for k in b["team"] if k in FIGURES)
        diff_stars = "⭐" * b["difficulty"]
        boss_tag = " 👑 **JEFE FINAL**" if b.get("is_boss") else ""
        embed.add_field(
            name=f"{b['name']}{boss_tag} {diff_stars}",
            value=f"{b['desc']}\n🎭 Equipo: {team_preview}\n💰 Recompensa: {b['reward_coins']}🪙 +{b['reward_xp']}XP",
            inline=False
        )


    view = discord.ui.View(timeout=60)
    for b in BOT_ROSTER:
        style = discord.ButtonStyle.danger if b.get("is_boss") else discord.ButtonStyle.primary
        btn = discord.ui.Button(
            label=b["name"],
            style=style,
            custom_id=f"fight_{b['id']}"
        )
        btn.callback = make_bot_fight_callback(b, user, interaction.user.id)
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view)

def make_bot_fight_callback(bot_data, user, user_discord_id):
    async def callback(inter: discord.Interaction):
        if inter.user.id != user_discord_id:
            await inter.response.send_message("❌ Este menú no es tuyo.", ephemeral=True)
            return
        if inter.channel_id in active_battles:
            await inter.response.send_message("❌ Ya hay una batalla activa.", ephemeral=True)
            return

        db = load_db()
        usr = get_user(db, inter.user.id)
        owned = usr.get("figures", [])

        # ── Batalla especial 7v3 del Impostor Negro ───────────────────────
        if bot_data.get("special_7v3"):
            await _start_impostor_7v3(inter, bot_data, owned, usr, db)
            return

        team_indices = usr.get("team", [None, None, None])
        p1_keys, p1_figs_data = [], []
        for idx in team_indices:
            if idx is not None and idx < len(owned):
                p1_keys.append(owned[idx]["key"])
                p1_figs_data.append(owned[idx])
        while len(p1_keys) < 3 and owned:
            p1_keys.append(owned[0]["key"])
            p1_figs_data.append(owned[0])

        bot_level  = bot_data["level"]
        hp_mult    = bot_data.get("hp_mult", 1.0)
        atk_mult   = bot_data.get("atk_mult", 1.0)
        nrg_bonus  = bot_data.get("energy_bonus", 0)
        p2_keys = bot_data["team"]
        p2_figs_data = [{"key": k, "level": bot_level, "xp": 0, "hp_mult": hp_mult, "atk_mult": atk_mult, "energy_bonus": nrg_bonus} for k in p2_keys]

        battle = BattleState(
            p1_id=inter.user.id,
            p2_id=0,
            p1_team_keys=p1_keys,
            p2_team_keys=p2_keys,
            p1_figs_data=p1_figs_data,
            p2_figs_data=p2_figs_data,
            is_bot=True
        )
        battle.p1_name = usr["name"]
        battle.p2_name = bot_data["name"]
        battle.bot_reward_coins = bot_data["reward_coins"]
        battle.bot_reward_xp = bot_data["reward_xp"]

        # Aplicar buffs de receta activos del usuario
        papyrus_result = _apply_recipe_buffs(usr, battle.p1_team, db2)

        active_battles[inter.channel_id] = battle

        boss_title = "💀 ¡BATALLA CONTRA EL JEFE FINAL!" if bot_data.get("is_boss") else f"⚔️ ¡BATALLA vs {bot_data['name']}!"
        embed = battle.get_embed(title=boss_title)
        if papyrus_result == "good":
            embed.add_field(
                name="🍝 Spaghetti de Langosta",
                value="**NYEHEHEH! MY COOKING SAVED THE DAY!**\n+25 ATK · +40 HP · +25 DEF a todo tu equipo.",
                inline=False
            )
        elif papyrus_result == "bad":
            embed.add_field(
                name="🍝 Spaghetti de Langosta",
                value="**Nyeh... heh... heh? Why is it moving?**\n-25 ATK · -40 HP · -25 DEF a todo tu equipo. 💀",
                inline=False
            )
        view = get_battle_view(battle)
        await inter.response.edit_message(embed=embed, view=view)
        battle.message = await inter.original_response()
    return callback


# ============================================================
#  SISTEMA MULTIPLAYER (hasta 4 jugadores)
# ============================================================
active_mp_battles = {}  # channel_id -> MPBattleState

GLOBAL_EVENTS = [
    {"name": "🌀 Inversión de Turnos", "desc": "¡El orden de turnos se invierte!", "type": "reverse_order"},
    {"name": "💥 Ronda de Fuego",      "desc": "¡Todas las figuras reciben 10 de daño extra este turno!", "type": "fire_round"},
    {"name": "⚡ Sobrecarga",          "desc": "¡Todas las barras de energía se llenan al máximo!", "type": "fill_energy"},
    {"name": "🛡️ Escudo Global",       "desc": "¡Todas las figuras reciben la mitad de daño este turno!", "type": "half_damage"},
    {"name": "🎲 Turno del Caos",      "desc": "¡El orden de turnos se baraja aleatoriamente!", "type": "shuffle_order"},
    {"name": "💚 Curación Masiva",     "desc": "¡Todas las figuras activas se curan 30 HP!", "type": "mass_heal"},
]

class MPBattleState:
    """Batalla de hasta 4 jugadores — todos contra todos en orden circular."""
    def __init__(self, players: list, teams: dict, names: dict):
        """
        players: lista de IDs de jugador en orden de turno
        teams: {player_id: [fighter, fighter, fighter]}
        names: {player_id: "nombre"}
        """
        self.players = players          # orden de turno
        self.teams   = teams            # {pid: [fighters]}
        self.active  = {pid: 0 for pid in players}   # figura activa por jugador
        self.names   = names
        self.turn_idx = 0               # índice en self.players
        self.log = []
        self.message = None
        self.event_cooldown = 0         # turnos hasta próximo evento

    def current_player(self):
        return self.players[self.turn_idx % len(self.players)]

    def current_fighter(self, pid):
        idx = self.active[pid]
        team = self.teams[pid]
        return team[idx] if idx < len(team) else None

    def active_fighter(self):
        return self.current_fighter(self.current_player())

    def alive_players(self):
        return [pid for pid in self.players
                if any(f["hp"] > 0 for f in self.teams[pid])]

    def next_active(self, pid):
        team = self.teams[pid]
        cur = self.active[pid]
        for i in range(cur+1, len(team)):
            if team[i]["hp"] > 0 and not team[i].get("force_locked",0) > 0:
                return i
        return None

    def hp_bar(self, cur, mx):
        ratio = max(0, cur/mx)
        filled = int(ratio * 8)
        return "🟩"*filled + "⬛"*(8-filled) + f" {cur}/{mx}"

    def energy_bar(self, energy, color="blue"):
        block = "🟦" if color=="blue" else "🟥"
        bar = ""
        for i in range(10):
            pos = (i+1)*10
            if pos <= energy:
                if pos==30: bar+="🟡"
                elif pos==60: bar+="🟠"
                elif pos==100: bar+="🔴"
                else: bar+=block
            else: bar+="⬛"
        return bar + f" {energy}/100"

    def get_embed(self, title="⚔️ BATALLA MULTIPLAYER"):
        embed = discord.Embed(title=title, color=0xe74c3c)
        cur_pid = self.current_player()

        # Mostrar todos los equipos
        for pid in self.players:
            fighter = self.current_fighter(pid)
            is_turn = (pid == cur_pid)
            turn_mark = " 🎮 **TU TURNO**" if is_turn else ""
            name = self.names.get(pid, str(pid))

            if not fighter or fighter["hp"] <= 0:
                val = "💀 Sin figuras"
            else:
                val = (
                    f"{fighter['emoji']} **{fighter['name']}**{turn_mark}\n"
                    f"Vida: {self.hp_bar(fighter['hp'], fighter['max_hp'])}\n"
                    f"Energía: {self.energy_bar(fighter['energy'], 'blue' if is_turn else 'red')}"
                )
            embed.add_field(name=f"👤 {name}", value=val, inline=True)

        if self.log:
            embed.add_field(name="📜 Último turno", value="\n".join(self.log[-4:]), inline=False)

        embed.set_footer(text=f"Turno de: {self.names.get(cur_pid, str(cur_pid))}")
        return embed

def get_mp_view(battle: MPBattleState, channel_id: int):
    """Genera botones para el jugador activo en la batalla MP."""
    view = BattleView.__new__(BattleView)
    discord.ui.View.__init__(view, timeout=None)

    cur_pid = battle.current_player()
    fighter = battle.active_fighter()
    if not fighter:
        return view

    # Ataque básico
    atk_btn = discord.ui.Button(label="⚔️ Atacar", style=discord.ButtonStyle.success, custom_id="mp_attack", row=0)

    # Botones de target (a quién atacar)
    targets = [pid for pid in battle.players if pid != cur_pid and any(f["hp"]>0 for f in battle.teams[pid])]

    async def atk_cb(inter: discord.Interaction):
        if inter.user.id != cur_pid:
            await inter.response.send_message("❌ No es tu turno.", ephemeral=True)
            return
        if len(targets) == 1:
            await execute_mp_action(inter, battle, channel_id, "basic", targets[0], None)
        else:
            await show_mp_target_select(inter, battle, channel_id, "basic", None)
    atk_btn.callback = atk_cb
    view.add_item(atk_btn)

    # Habilidades
    type_emoji = {"damage":"⚔️","heal":"💚","drain":"⚡","drain_fill":"🔴","parry":"🛡️",
                  "buff":"⭐","gamble":"🎲","gamble_fire":"🔥","team_atk_buff":"⭐","dot":"💣",
                  "bad_update":"🔳","ban_hammer":"🔨","fly_away":"✈️","michi_counter":"🦊",
                  "glitch_dmg":"🌀","corruption":"🌑","retribution":"🦷"}
    for i, skill in enumerate(fighter.get("skills", [])):
        can = fighter["energy"] >= skill["cost"]
        te = type_emoji.get(skill["type"], "⚡")
        btn = discord.ui.Button(
            label=f"{te} {skill['name']} [{skill['cost']}⚡]",
            style=discord.ButtonStyle.danger if can else discord.ButtonStyle.secondary,
            disabled=not can,
            custom_id=f"mp_skill_{i}",
            row=1
        )
        async def sk_cb(inter: discord.Interaction, si=i, sk=skill):
            if inter.user.id != cur_pid:
                await inter.response.send_message("❌ No es tu turno.", ephemeral=True)
                return
            heal_types = ("heal","team_atk_buff","heal_team_self","gamble","drain_fill")
            if sk["type"] in heal_types:
                await execute_mp_action(inter, battle, channel_id, "skill", cur_pid, si)
            elif len(targets) == 1:
                await execute_mp_action(inter, battle, channel_id, "skill", targets[0], si)
            else:
                await show_mp_target_select(inter, battle, channel_id, "skill", si)
        btn.callback = sk_cb
        view.add_item(btn)

    return view

async def show_mp_target_select(inter: discord.Interaction, battle: MPBattleState, channel_id: int, action_type: str, skill_idx):
    """Muestra selector de objetivo para ataques MP."""
    cur_pid = battle.current_player()
    targets = [pid for pid in battle.players if pid != cur_pid and any(f["hp"]>0 for f in battle.teams[pid])]

    options = []
    for pid in targets:
        f = battle.current_fighter(pid)
        if f:
            options.append(discord.SelectOption(
                label=f"{battle.names.get(pid,'?')} — {f['emoji']} {f['name']} ({f['hp']}HP)",
                value=str(pid)
            ))

    sel = discord.ui.Select(placeholder="¿A quién atacas?", options=options)
    async def sel_cb(si: discord.Interaction):
        if si.user.id != cur_pid:
            await si.response.send_message("❌ No es tu selección.", ephemeral=True)
            return
        target_id = int(sel.values[0])
        await execute_mp_action(si, battle, channel_id, action_type, target_id, skill_idx)
    sel.callback = sel_cb
    v = discord.ui.View(timeout=60)
    v.add_item(sel)
    await inter.response.edit_message(
        embed=battle.get_embed(title="🎯 Elige tu objetivo"),
        view=v
    )

async def execute_mp_action(inter: discord.Interaction, battle: MPBattleState, channel_id: int, action_type: str, target_id, skill_idx):
    """Ejecuta la acción del jugador activo en MP."""
    cur_pid = battle.current_player()
    attacker = battle.active_fighter()
    if not attacker:
        return

    battle.log = []

    # Subir energía
    attacker["energy"] = min(ENERGY_MAX, attacker["energy"] + ENERGY_PER_TURN + attacker.get("energy_bonus",0))

    if action_type == "basic":
        defender = battle.current_fighter(target_id)
        if not defender:
            await inter.response.send_message("❌ Objetivo inválido.", ephemeral=True)
            return
        bonus_atk = attacker.pop("atk_buff", 0)
        max_power = max((sk.get("power",0) for sk in attacker.get("skills",[])), default=20)
        base_dmg = max(1, round(max_power/2))
        dmg = max(1, base_dmg + random.randint(-2,3) - (defender["defense"]//6))
        defender["hp"] = max(0, defender["hp"] - dmg)
        tname = battle.names.get(target_id, "?")
        battle.log.append(f"⚔️ **{attacker['emoji']} {attacker['name']}** ataca a **{tname}** → **{dmg}** daño! (+20⚡)")

    elif action_type == "skill" and skill_idx is not None:
        skill = attacker["skills"][skill_idx]
        if attacker["energy"] < skill["cost"]:
            await inter.response.send_message("❌ No tienes energía suficiente.", ephemeral=True)
            return
        attacker["energy"] -= skill["cost"]
        stype = skill["type"]

        if stype == "damage":
            defender = battle.current_fighter(target_id)
            if not defender:
                await inter.response.send_message("❌ Objetivo inválido.", ephemeral=True)
                return
            bonus_atk = attacker.pop("atk_buff", 0)
            dmg = max(1, int(attacker["atk"] * skill["power"]/100) + random.randint(-3,8) - (defender["defense"]//4) + bonus_atk)
            defender["hp"] = max(0, defender["hp"] - dmg)
            tname = battle.names.get(target_id,"?")
            battle.log.append(f"⚔️ **{attacker['name']}** usa **{skill['name']}** en **{tname}** → **{dmg}** daño!")
        elif stype == "heal":
            heal = max(1, int(skill["power"] + random.randint(-2,5)))
            if not attacker.get("no_heal"):
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal)
            battle.log.append(f"💚 **{attacker['name']}** usa **{skill['name']}** → +**{heal}** HP!")
        elif stype == "team_atk_buff":
            buff = skill.get("atk_buff",10)
            for f in battle.teams[cur_pid]:
                if f["hp"] > 0:
                    f["atk_buff"] = f.get("atk_buff",0) + buff
            battle.log.append(f"⭐ **{attacker['name']}** usa **{skill['name']}**! Todo el equipo +{buff} ATK!")
        elif stype == "dot":
            defender = battle.current_fighter(target_id)
            if defender:
                if "dots" not in defender: defender["dots"] = []
                defender["dots"].append({"dmg": skill["power"], "turns": skill.get("dot_turns",3)})
                battle.log.append(f"💣 **{attacker['name']}** usa **{skill['name']}**! {skill['power']} daño/turno x{skill.get('dot_turns',3)}")
        else:
            battle.log.append(f"✨ **{attacker['name']}** usa **{skill['name']}**!")

    # Verificar si algún jugador perdió todas sus figuras
    eliminated = []
    for pid in list(battle.players):
        if pid == cur_pid: continue
        team = battle.teams[pid]
        if all(f["hp"] <= 0 for f in team):
            eliminated.append(pid)

    for pid in eliminated:
        battle.players.remove(pid)
        battle.log.append(f"💀 **{battle.names.get(pid,'?')}** fue eliminado!")

    # ¿Solo queda 1 jugador?
    alive = battle.alive_players()
    if len(alive) <= 1:
        await end_mp_battle(inter, battle, channel_id, alive[0] if alive else cur_pid)
        return

    # Avanzar turno (saltear jugadores eliminados)
    battle.turn_idx = (battle.turn_idx + 1) % len(battle.players)

    # Evento global aleatorio (5% por turno)
    event_triggered = None
    if random.random() < 0.05:
        event_triggered = random.choice(GLOBAL_EVENTS)
        await apply_global_event(battle, event_triggered)
        battle.log.append(f"🌀 **EVENTO GLOBAL: {event_triggered['name']}** — {event_triggered['desc']}")

    embed = battle.get_embed()
    if event_triggered:
        embed.color = 0x9b59b6
    view = get_mp_view(battle, channel_id)

    try:
        await inter.response.edit_message(embed=embed, view=view)
    except Exception:
        if battle.message:
            await battle.message.edit(embed=embed, view=view)

async def apply_global_event(battle: MPBattleState, event: dict):
    etype = event["type"]
    all_fighters = [battle.current_fighter(pid) for pid in battle.players if battle.current_fighter(pid)]

    if etype == "reverse_order":
        battle.players.reverse()
        battle.turn_idx = 0

    elif etype == "fire_round":
        for f in all_fighters:
            if f and f["hp"] > 0:
                f["hp"] = max(1, f["hp"] - 10)

    elif etype == "fill_energy":
        for f in all_fighters:
            if f: f["energy"] = ENERGY_MAX

    elif etype == "half_damage":
        for f in all_fighters:
            if f: f["half_damage_turn"] = True

    elif etype == "shuffle_order":
        random.shuffle(battle.players)
        battle.turn_idx = 0

    elif etype == "mass_heal":
        for f in all_fighters:
            if f and f["hp"] > 0 and not f.get("no_heal"):
                f["hp"] = min(f["max_hp"], f["hp"] + 30)

async def end_mp_battle(inter: discord.Interaction, battle: MPBattleState, channel_id: int, winner_id: int):
    if channel_id in active_mp_battles:
        del active_mp_battles[channel_id]

    embed = discord.Embed(
        title="🏆 ¡FIN DE LA BATALLA MULTIPLAYER!",
        description=f"🎉 ¡**{battle.names.get(winner_id,'?')}** gana la batalla!",
        color=0xf1c40f
    )

    # Recompensas
    db = load_db()
    for pid in battle.players + list(battle.teams.keys()):
        if pid == 0: continue
        u = get_user(db, pid)
        if not u: continue
        if pid == winner_id:
            u["wins"] = u.get("wins",0) + 1
            u["coins"] = u.get("coins",0) + COINS_WIN * 2
            u["xp"] = u.get("xp",0) + XP_PER_WIN
        else:
            u["losses"] = u.get("losses",0) + 1
            u["coins"] = u.get("coins",0) + COINS_LOSS
    save_db(db)

    embed.add_field(name="💰 Recompensas", value=f"Ganador: +{COINS_WIN*2}🪙 | Resto: +{COINS_LOSS}🪙", inline=False)

    try:
        await inter.response.edit_message(embed=embed, view=None)
    except Exception:
        if battle.message:
            await battle.message.edit(embed=embed, view=None)

# --- RETAR A JUGADOR ---
@bot.tree.command(name="retar", description="Reta a otro jugador a un duelo PvP de equipos")
@app_commands.describe(rival="El jugador al que quieres retar")
async def retar(interaction: discord.Interaction, rival: discord.Member):
    db = load_db()
    user = get_user(db, interaction.user.id)
    rival_data = get_user(db, rival.id)

    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    if not rival_data:
        await interaction.response.send_message("❌ Tu rival no está registrado.", ephemeral=True)
        return
    if rival.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes retarte a ti mismo.", ephemeral=True)
        return
    if not user.get("figures"):
        await interaction.response.send_message("❌ No tienes figuras. Compra en `/tienda`.", ephemeral=True)
        return
    if not rival_data.get("figures"):
        await interaction.response.send_message(f"❌ {rival.mention} no tiene figuras.", ephemeral=True)
        return
    if interaction.channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay batalla activa aquí.", ephemeral=True)
        return

    u1_figs = user["figures"]
    u2_figs = rival_data["figures"]

    def build_team(figs, team_indices):
        keys, datas = [], []
        for idx in (team_indices or []):
            if idx is not None and idx < len(figs):
                keys.append(figs[idx]["key"]); datas.append(figs[idx])
        while len(keys) < 3 and figs:
            keys.append(figs[0]["key"]); datas.append(figs[0])
        return keys[:3], datas[:3]

    u1_keys, u1_data = build_team(u1_figs, user.get("team", []))
    u2_keys, u2_data = build_team(u2_figs, rival_data.get("team", []))

    # Preview del equipo
    def team_preview(keys):
        names = []
        for k in keys:
            fig = FIGURES.get(k)
            if fig: names.append(f"{fig['emoji']} {fig['name']}")
        return " | ".join(names)

    embed = discord.Embed(
        title="⚔️ ¡DESAFÍO PvP!",
        description=f"{interaction.user.mention} reta a {rival.mention} a un duelo de equipos!",
        color=0xe74c3c
    )
    embed.add_field(name=f"🥊 {user['name']}", value=team_preview(u1_keys), inline=False)
    embed.add_field(name="⚡ VS ⚡", value="\u200b", inline=False)
    embed.add_field(name=f"🥊 {rival_data['name']}", value=team_preview(u2_keys), inline=False)

    accept_btn = discord.ui.Button(label="✅ Aceptar", style=discord.ButtonStyle.success, custom_id="accept_pvp")
    reject_btn = discord.ui.Button(label="❌ Rechazar", style=discord.ButtonStyle.danger, custom_id="reject_pvp")

    async def accept_callback(btn_inter: discord.Interaction):
        if btn_inter.user.id != rival.id:
            await btn_inter.response.send_message("❌ Solo el retado puede aceptar.", ephemeral=True)
            return
        if interaction.channel_id in active_battles:
            await btn_inter.response.send_message("❌ Ya hay una batalla activa.", ephemeral=True)
            return
        db2 = load_db()
        u1 = get_user(db2, interaction.user.id)
        u2 = get_user(db2, rival.id)
        def bteam(figs, tidx):
            ks, ds = [], []
            for i in (tidx or []):
                if i is not None and i < len(figs):
                    ks.append(figs[i]["key"]); ds.append(figs[i])
            while len(ks) < 3 and figs:
                ks.append(figs[0]["key"]); ds.append(figs[0])
            return ks[:3], ds[:3]

        k1, d1 = bteam(u1["figures"], u1.get("team", []))
        k2, d2 = bteam(u2["figures"], u2.get("team", []))

        battle = BattleState(
            p1_id=interaction.user.id,
            p2_id=rival.id,
            p1_team_keys=k1,
            p2_team_keys=k2,
            p1_figs_data=d1,
            p2_figs_data=d2,
            is_bot=False
        )
        battle.p1_name = get_user(db2, interaction.user.id)["name"]
        battle.p2_name = get_user(db2, rival.id)["name"]

        # Aplicar buffs de receta activos de ambos jugadores
        p1_papyrus = _apply_recipe_buffs(u1, battle.p1_team, db2)
        p2_papyrus = _apply_recipe_buffs(u2, battle.p2_team, db2)
        save_db(db2)
        active_battles[interaction.channel_id] = battle
        view = get_battle_view(battle)
        await btn_inter.response.edit_message(embed=battle.get_embed(title="⚔️ ¡LA BATALLA COMIENZA!"), view=view)
        battle.message = await btn_inter.original_response()

    async def reject_callback(btn_inter: discord.Interaction):
        if btn_inter.user.id != rival.id:
            await btn_inter.response.send_message("❌ Solo el retado puede rechazar.", ephemeral=True)
            return
        reject_embed = discord.Embed(title="❌ Desafío rechazado", description=f"{rival.mention} rechazó el duelo.", color=0x95a5a6)
        await btn_inter.response.edit_message(embed=reject_embed, view=None)

    accept_btn.callback = accept_callback
    reject_btn.callback = reject_callback
    view = discord.ui.View(timeout=60)
    view.add_item(accept_btn)
    view.add_item(reject_btn)
    await interaction.response.send_message(content=rival.mention, embed=embed, view=view)

# --- RANKING ---
def build_leaderboard_embed(users: dict, category: str) -> discord.Embed:
    medals = ["🥇","🥈","🥉"] + ["🔸"]*7

    if category == "wins":
        title = "🏆 Leaderboard — Victorias"
        color = 0xf1c40f
        sorted_u = sorted(users.values(), key=lambda u: u.get("wins",0), reverse=True)[:10]
        def row(u):
            total = u.get("wins",0) + u.get("losses",0)
            wr = round(u.get("wins",0)/total*100,1) if total>0 else 0
            return f"✅ {u.get('wins',0)}V ❌ {u.get('losses',0)}D | WR: **{wr}%**"

    elif category == "coins":
        title = "💰 Leaderboard — Dinero"
        color = 0x2ecc71
        sorted_u = sorted(users.values(), key=lambda u: u.get("coins",0), reverse=True)[:10]
        def row(u): return f"💰 **{u.get('coins',0):,}** monedas"

    elif category == "figures":
        title = "🎭 Leaderboard — Figuras"
        color = 0x9b59b6
        sorted_u = sorted(users.values(), key=lambda u: len(set(f["key"] for f in u.get("figures",[]))), reverse=True)[:10]
        def row(u):
            unique = len(set(f["key"] for f in u.get("figures",[])))
            total  = len(u.get("figures",[]))
            return f"🎭 **{unique}** únicas ({total} totales)"

    elif category == "fig_level":
        title = "⬆️ Leaderboard — Nivel de Figuras"
        color = 0x3498db
        def total_fig_lvl(u):
            return sum(f.get("level",1) for f in u.get("figures",[]))
        sorted_u = sorted(users.values(), key=total_fig_lvl, reverse=True)[:10]
        def row(u):
            lvls = [f.get("level",1) for f in u.get("figures",[])]
            return f"⬆️ Niveles totales: **{sum(lvls)}** | Máx: **{max(lvls) if lvls else 0}**"

    elif category == "recipes":
        title = "🧑‍🍳 Leaderboard — Recetas"
        color = 0xe67e22
        sorted_u = sorted(users.values(), key=lambda u: u.get("recipe_count",0), reverse=True)[:10]
        def row(u): return f"🧑‍🍳 **{u.get('recipe_count',0)}** recetas descubiertas"

    elif category == "playerlevel":
        title = "🏆 Leaderboard — Nivel de Jugador"
        color = 0x3498db
        sorted_u = sorted(users.values(), key=lambda u: u.get("rebirth_count",0)*1000 + u.get("level",1), reverse=True)[:10]
        def row(u):
            rb  = u.get("rebirth_count", 0)
            lvl = u.get("level", 1)
            rb_str = f" 🔄×{rb}" if rb > 0 else ""
            return f"🏆 Nivel **{lvl}**{rb_str} · SP: {u.get('skill_points',0)}"
    else:
        return discord.Embed(title="❌ Categoría desconocida", color=0xe74c3c)

    embed = discord.Embed(title=title, color=color)
    for i, u in enumerate(sorted_u):
        embed.add_field(
            name=f"{medals[i]} {u.get('name','?')} (Nv.{u.get('level',1)})",
            value=row(u),
            inline=False
        )
    return embed

@bot.tree.command(name="ranking", description="Leaderboards del servidor — elige la categoría")
async def ranking(interaction: discord.Interaction):
    db = load_db()
    users = db.get("users", {})
    if not users:
        await interaction.response.send_message("📭 Nadie registrado aún.", ephemeral=True)
        return

    # Mostrar con botones de selección de categoría
    async def send_lb(inter: discord.Interaction, category: str, edit=False):
        embed = build_leaderboard_embed(users, category)
        view = discord.ui.View(timeout=120)
        cats = [("wins","🏆 Victorias"),("coins","💰 Dinero"),("figures","🎭 Figuras"),("fig_level","⬆️ Niveles"),("recipes","🧑‍🍳 Recetas"),("playerlevel","🏆 Niv. Jugador")]
        for cat_id, cat_label in cats:
            btn = discord.ui.Button(
                label=cat_label,
                style=discord.ButtonStyle.primary if cat_id == category else discord.ButtonStyle.secondary,
                custom_id=f"lb_{cat_id}"
            )
            async def cb(i: discord.Interaction, c=cat_id):
                db2 = load_db()
                await send_lb(i, c, edit=True)
            btn.callback = cb
            view.add_item(btn)
        if edit:
            await inter.response.edit_message(embed=embed, view=view)
        else:
            await inter.response.send_message(embed=embed, view=view)

    await send_lb(interaction, "wins")

# --- RECOMPENSA DIARIA ---
DAILY_MAX_STREAK = 7

DAILY_STREAK_REWARDS = {
    1: {"coins": 300,  "emoji": "📦", "label": "Día 1"},
    2: {"coins": 350,  "emoji": "📦", "label": "Día 2"},
    3: {"coins": 450,  "emoji": "🎁", "label": "Día 3"},
    4: {"coins": 500,  "emoji": "🎁", "label": "Día 4"},
    5: {"coins": 600,  "emoji": "💎", "label": "Día 5"},
    6: {"coins": 700,  "emoji": "💎", "label": "Día 6"},
    7: {"coins": 1000, "emoji": "🌟", "label": "¡Racha Máxima!"},
}

# Probabilidad de figura según racha (día: % de chance)
DAILY_FIGURE_CHANCE = {
    1: 10,   # 10% día 1
    2: 12,
    3: 18,
    4: 22,
    5: 30,
    6: 40,
    7: 60,   # 60% en racha máxima
}

# Probabilidad de rareza según racha
def get_figure_rarity_pool(streak):
    """Devuelve un pool de claves de figuras ponderado por rareza según la racha."""
    pool = []
@bot.tree.command(name="diario", description="Reclama tu recompensa diaria (cada 24 horas)")
async def diario(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    now = datetime.now(timezone.utc)
    last_daily = user.get("last_daily")
    streak = user.get("daily_streak", 0)

    if last_daily:
        last_dt = datetime.fromisoformat(last_daily)
        diff_hours = (now - last_dt).total_seconds() / 3600

        if diff_hours < 24:
            remaining = 24 - diff_hours
            horas = int(remaining)
            minutos = int((remaining - horas) * 60)

            embed = discord.Embed(
                title="⏰ Ya reclamaste tu recompensa hoy",
                description=f"Vuelve en **{horas}h {minutos}m** para el siguiente diario.",
                color=0xe74c3c
            )
            embed.add_field(name="🔥 Racha actual", value=f"{streak} día(s)", inline=True)
            barra = "".join(
                DAILY_STREAK_REWARDS[d]["emoji"] if d <= streak else "⬛"
                for d in range(1, DAILY_MAX_STREAK + 1)
            )
            embed.add_field(name="📅 Racha semanal", value=barra, inline=False)
            # Mostrar % de figura del día siguiente
            next_streak = min(streak + 1, DAILY_MAX_STREAK)
            chance = DAILY_FIGURE_CHANCE[next_streak]
            embed.add_field(
                name="🎲 Mañana tendrás",
                value=f"**{chance}%** de probabilidad de ganar una figura gratis!",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        elif diff_hours >= 48:
            streak = 0

    # Reclamar recompensa
    streak = min(streak + 1, DAILY_MAX_STREAK)
    reward = DAILY_STREAK_REWARDS[streak]
    coins_earned = reward["coins"]

    user["coins"] = user.get("coins", 0) + coins_earned
    user["last_daily"] = now.isoformat()
    user["daily_streak"] = streak

    # ¿Gana figura?
    figure_won = None
    chance = DAILY_FIGURE_CHANCE[streak]
    owned_keys = [f["key"] for f in user.get("figures", [])]
    available_keys = [k for k in FIGURES.keys() if k not in owned_keys]

    if available_keys and random.randint(1, 100) <= chance:
        pool = [k for k in get_figure_rarity_pool(streak) if k in available_keys]
        if pool:
            figure_won = random.choice(pool)
            user["figures"].append({"key": figure_won, "level": 1, "xp": 0})
            if not user.get("active_figure"):
                user["active_figure"] = figure_won

    # XP al jugador por reclamar el diario
    user["xp"] = user.get("xp", 0) + 10 * streak  # más XP cuanto mayor es la racha
    _check_player_levelup(user)
    save_db(db)

    # Embed principal
    is_max = streak == DAILY_MAX_STREAK
    color = 0xf1c40f if is_max else (0x9b59b6 if streak >= 5 else (0x3498db if streak >= 3 else 0x2ecc71))

    desc = "🎊 ¡RACHA MÁXIMA! ¡INCREÍBLE! 🎊" if is_max else f"¡Buen trabajo, **{user['name']}**!"
    embed = discord.Embed(
        title=f"{reward['emoji']} ¡Recompensa Diaria Reclamada!",
        description=desc,
        color=color
    )

    embed.add_field(name="💰 Monedas ganadas", value=f"+**{coins_earned:,}** monedas", inline=True)
    embed.add_field(name="💳 Total actual", value=f"**{user['coins']:,}** monedas", inline=True)
    embed.add_field(name="🔥 Racha", value=f"**{streak}** día(s) seguidos", inline=True)

    barra = "".join(
        DAILY_STREAK_REWARDS[d]["emoji"] if d <= streak else "⬛"
        for d in range(1, DAILY_MAX_STREAK + 1)
    )
    embed.add_field(name="📅 Progreso semanal", value=barra, inline=False)

    # Bloque de figura ganada
    if figure_won:
        fig = FIGURES[figure_won]
        star = RARITY_STARS[fig["rarity"]]
        embed.add_field(
            name="🎉 ¡FIGURA SORPRESA!",
            value=(
                f"{fig['emoji']} **{fig['name']}** {star}\n"
                f"Rareza: **{fig['rarity'].upper()}**\n"
                f"❤️ HP:{fig['hp']} ⚔️ ATK:{fig['attack']} 🛡️ DEF:{fig['defense']} ⚡ VEL:{fig['speed']}\n" +
                " | ".join(f"✨{sk['name']}" for sk in FIGURE_SKILLS.get(key, []))
            ),
            inline=False
        )
        if fig.get("image"):
            embed.set_image(url=fig["image"])
        embed.color = RARITY_COLOR[fig["rarity"]]
    else:
        # Mostrar % de figura para motivar
        embed.add_field(
            name="🎲 Probabilidad de figura hoy",
            value=f"Tenías **{chance}%** de ganar una figura. ¡Sigue intentando mañana!",
            inline=False
        )

    # Próxima recompensa
    if streak < DAILY_MAX_STREAK:
        next_reward = DAILY_STREAK_REWARDS[streak + 1]
        next_chance = DAILY_FIGURE_CHANCE[streak + 1]
        embed.add_field(
            name="➡️ Mañana",
            value=(
                f"{next_reward['emoji']} **{next_reward['coins']:,}** monedas\n"
                f"🎲 **{next_chance}%** de probabilidad de figura!"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="🔄 Racha reiniciada",
            value="Mañana empieza una nueva racha semanal. ¡Eres una leyenda!",
            inline=False
        )
        user["daily_streak"] = 0
        save_db(db)

    embed.set_footer(text="Vuelve en 24 horas para mantener tu racha!")
    await interaction.response.send_message(embed=embed)

# --- AYUDA ---
@bot.tree.command(name="ayuda", description="Ver todos los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Androide del PvP — Comandos",
        description="¡Bienvenido al sistema de batallas de figuras!",
        color=0x3498db
@bot.tree.command(name="reset", description="Reinicia la batalla activa en este canal")
async def reset_battle(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Solo los admins pueden reiniciar batallas.", ephemeral=True)
        return
    removed = False
    if interaction.channel_id in active_battles:
        del active_battles[interaction.channel_id]
        removed = True
    # Limpiar también peleas PvP pendientes en este canal
    to_remove = [k for k, v in pending_pvp.items() if v.get("channel_id") == interaction.channel_id]
    for k in to_remove:
        del pending_pvp[k]
        removed = True
    if removed:
        embed = discord.Embed(
            title="🔄 Batalla reiniciada",
            description="La batalla activa en este canal ha sido cancelada. ¡Podéis iniciar una nueva!",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ No hay ninguna batalla activa en este canal.", ephemeral=True)

# --- BOMB (solo admins) ---
@bot.tree.command(name="bomb", description="[ADMIN] Quita monedas a un usuario")
@app_commands.describe(usuario="Usuario objetivo", cantidad="Monedas a quitar")
async def bomb(interaction: discord.Interaction, usuario: discord.Member, cantidad: int):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
        return
    db = load_db()
    target = get_user(db, usuario.id)
    if not target:
        await interaction.response.send_message("❌ Usuario no registrado.", ephemeral=True)
        return
    if cantidad <= 0:
        await interaction.response.send_message("❌ La cantidad debe ser mayor a 0.", ephemeral=True)
        return
    before = target.get("coins", 0)
    target["coins"] = max(0, before - cantidad)
    save_db(db)
    embed = discord.Embed(title="💣 ¡BOOM!", description=f"**{target['name']}** acaba de perder una fortuna.", color=0xe74c3c)
    embed.set_image(url="https://media.giphy.com/media/g2YdApKEna2sg/giphy.gif")
    embed.add_field(name="👤 Usuario", value=target["name"], inline=True)
    embed.add_field(name="💸 Monedas eliminadas", value=f"-**{cantidad:,}**", inline=True)
    embed.add_field(name="💳 Saldo restante", value=f"**{target['coins']:,}**", inline=True)
    await interaction.response.send_message(embed=embed)

# --- NUKE (solo admins) ---
@bot.tree.command(name="nuke", description="[ADMIN] Resetea a un usuario a nivel 1")
@app_commands.describe(usuario="Usuario a nukear")
async def nuke(interaction: discord.Interaction, usuario: discord.Member):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
@bot.tree.command(name="multiplayer", description="Crea una batalla multijugador (2-4 jugadores)")
async def multiplayer_cmd(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_multiplayer:
        await interaction.response.send_message("❌ Ya hay una partida multijugador en este canal.", ephemeral=True)
        return
    if channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa. Usa `/reset` primero.", ephemeral=True)
        return
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    if not user.get("team") or not user.get("figures"):
        await interaction.response.send_message("❌ Equipa tus figuras con `/equipar` primero.", ephemeral=True)
        return

    session = MultiplayerSession(interaction.user.id, interaction.user.display_name, channel_id)
    active_multiplayer[channel_id] = session

    # Guardar equipo del host
    team_indices = user.get("team", [])
    host_team_keys = []
    host_figs_data = []
    for ti in team_indices:
        if ti is not None and ti < len(user["figures"]):
            fd = user["figures"][ti]
            host_team_keys.append(fd["key"])
            host_figs_data.append(fd)
    session.players[interaction.user.id]["team"] = host_team_keys
    session.players[interaction.user.id]["figs_data"] = host_figs_data
    session.players[interaction.user.id]["ready"] = True

    embed = discord.Embed(
        title="⚔️ Sala Multijugador creada",
        description=f"👑 **{interaction.user.display_name}** creó la sala.\n\n¡Únete con el botón de abajo! (máx. 4 jugadores)\nEl host puede iniciar cuando haya al menos 2.",
        color=0x9b59b6
    )
    embed.add_field(name="Jugadores", value=f"1. {interaction.user.display_name} ✅", inline=False)

    view = discord.ui.View(timeout=180)

    join_btn = discord.ui.Button(label="🎮 Unirme", style=discord.ButtonStyle.primary)
    start_btn = discord.ui.Button(label="⚔️ Iniciar batalla", style=discord.ButtonStyle.success)
    cancel_btn = discord.ui.Button(label="❌ Cancelar", style=discord.ButtonStyle.danger)

    async def join_callback(inter: discord.Interaction):
        sess = active_multiplayer.get(channel_id)
        if not sess or sess.started:
            await inter.response.send_message("❌ La sala ya no está disponible.", ephemeral=True)
            return
        if inter.user.id in sess.players:
            await inter.response.send_message("⚠️ Ya estás en la sala.", ephemeral=True)
            return
        if len(sess.players) >= sess.max_players:
            await inter.response.send_message("❌ La sala está llena.", ephemeral=True)
            return
        db2 = load_db()
        u2 = get_user(db2, inter.user.id)
        if not u2:
            await inter.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
            return
        if not u2.get("team") or not u2.get("figures"):
            await inter.response.send_message("❌ Equipa tus figuras con `/equipar` primero.", ephemeral=True)
            return
        team_idxs = u2.get("team", [])
        p_keys, p_figs = [], []
        for ti in team_idxs:
            if ti is not None and ti < len(u2["figures"]):
                fd = u2["figures"][ti]
                p_keys.append(fd["key"])
                p_figs.append(fd)
        sess.players[inter.user.id] = {"name": inter.user.display_name, "ready": True, "team": p_keys, "figs_data": p_figs}
        player_list = "\n".join(f"{i+1}. {p['name']} ✅" for i, p in enumerate(sess.players.values()))
        new_embed = discord.Embed(title="⚔️ Sala Multijugador", description=f"¡Únete! (máx. 4)", color=0x9b59b6)
        new_embed.add_field(name=f"Jugadores ({len(sess.players)}/4)", value=player_list, inline=False)
        await inter.response.edit_message(embed=new_embed, view=view)

    async def start_callback(inter: discord.Interaction):
        sess = active_multiplayer.get(channel_id)
        if not sess:
            await inter.response.send_message("❌ Sala no encontrada.", ephemeral=True)
            return
        if inter.user.id != sess.host_id:
            await inter.response.send_message("❌ Solo el host puede iniciar.", ephemeral=True)
            return
        if len(sess.players) < 2:
            await inter.response.send_message("❌ Se necesitan al menos 2 jugadores.", ephemeral=True)
            return
        sess.started = True
        # Construir equipos
        sess.turn_order = list(sess.players.keys())
        random.shuffle(sess.turn_order)
        # Crear figuras listas para batalla
        sess.fighters = {}
        for uid, pdata in sess.players.items():
            fighters = []
            for i, fkey in enumerate(pdata["team"]):
                fd = pdata["figs_data"][i] if i < len(pdata["figs_data"]) else {"level": 1}
                f = make_fighter(fkey, fd)
                f["owner_id"] = uid
                f["owner_name"] = pdata["name"]
                fighters.append(f)
            sess.fighters[uid] = fighters

        await inter.response.edit_message(
            embed=discord.Embed(title="⚔️ ¡Batalla iniciada!", description=f"Orden de turnos: {' → '.join(sess.players[uid]['name'] for uid in sess.turn_order)}", color=0xe74c3c),
            view=None
        )
        await run_multiplayer_battle(inter.channel, sess)

    async def cancel_callback(inter: discord.Interaction):
        sess = active_multiplayer.get(channel_id)
        if sess and inter.user.id == sess.host_id:
            del active_multiplayer[channel_id]
            await inter.response.edit_message(embed=discord.Embed(title="❌ Sala cancelada", color=0xe74c3c), view=None)
        else:
            await inter.response.send_message("❌ Solo el host puede cancelar.", ephemeral=True)

    join_btn.callback = join_callback
    start_btn.callback = start_callback
    cancel_btn.callback = cancel_callback
    view.add_item(join_btn)
    view.add_item(start_btn)
    view.add_item(cancel_btn)

    await interaction.response.send_message(embed=embed, view=view)

async def run_multiplayer_battle(channel, sess: MultiplayerSession):
    """Motor de batalla multijugador. Turnos en círculos, elige a quién atacar."""
    import asyncio

    def alive_players():
        return [uid for uid in sess.turn_order if uid not in sess.eliminated and any(f["hp"] > 0 for f in sess.fighters.get(uid, []))]

    def get_active_fighter(uid):
        for f in sess.fighters.get(uid, []):
            if f["hp"] > 0:
                return f
        return None

    async def send_status(msg=None):
        lines = []
        for uid in sess.turn_order:
            if uid in sess.eliminated:
                lines.append(f"💀 ~~{sess.players[uid]['name']}~~")
                continue
            figs = sess.fighters.get(uid, [])
            fig_parts = []
            for f in figs:
                hp_str = "💀" if f["hp"] <= 0 else f"{f['hp']}HP"
                fig_parts.append(f"{f['emoji']} {hp_str}")
            fig_str = " | ".join(fig_parts)
            lines.append(f"**{sess.players[uid]['name']}**: {fig_str}")
        embed = discord.Embed(
            title=f"⚔️ Multijugador — Ronda {sess.round_num}",
            description="\n".join(lines),
            color=0x9b59b6
        )
        if sess.invert_event_active:
            embed.add_field(name="🔀 EVENTO GLOBAL", value="¡Los ejes están invertidos! Los ataques curan al enemigo y las curaciones dañan!", inline=False)
        if sess.log:
            embed.add_field(name="📋 Último turno", value="\n".join(sess.log[-5:]), inline=False)
        if msg:
            await msg.edit(embed=embed)
            return msg
        else:
            return await channel.send(embed=embed)

    status_msg = await send_status()

    while len(alive_players()) > 1:
        # Evento global aleatorio (10% por ronda)
        if random.randint(1, 100) <= 10:
            sess.invert_event_active = not sess.invert_event_active
            event_msg = "🔀 **¡EVENTO GLOBAL!** ¡Los ejes se han invertido!" if sess.invert_event_active else "🔀 **¡EVENTO GLOBAL!** ¡Los ejes vuelven a la normalidad!"
            await channel.send(event_msg)

        for uid in list(sess.turn_order):
            alives = alive_players()
            if len(alives) <= 1:
                break
            if uid in sess.eliminated:
                continue
            if not any(f["hp"] > 0 for f in sess.fighters.get(uid, [])):
                sess.eliminated.add(uid)
                continue

            attacker_fig = get_active_fighter(uid)
            if not attacker_fig:
                continue

            # Construir opciones de ataque
            enemies = [eid for eid in alives if eid != uid]
            if not enemies:
                break

            # Pedir al jugador que elija target
            target_options = []
            for eid in enemies:
                ef = get_active_fighter(eid)
                if ef:
                    target_options.append(discord.SelectOption(
                        label=f"Atacar a {sess.players[eid]['name']}",
                        value=str(eid),
                        description=f"{ef['emoji']} {ef['name']} — {ef['hp']}HP"
                    ))

            # Construir skill options
            skills = FIGURE_SKILLS.get(attacker_fig.get("key", ""), [])
            skill_options = []
            for i, sk in enumerate(skills):
                cost = sk.get("cost", 0)
                skill_options.append(discord.SelectOption(
                    label=f"{sk['name']} ({cost}⚡)",
                    value=str(i),
                    description=sk.get("desc", "")[:50]
                ))

            turn_embed = discord.Embed(
                title=f"🎮 Turno de {sess.players[uid]['name']}",
                description=f"**{attacker_fig['emoji']} {attacker_fig['name']}** — {attacker_fig['hp']}HP | {attacker_fig.get('energy',0)}⚡\n\nElige objetivo y habilidad:",
                color=0x3498db
            )
            turn_view = discord.ui.View(timeout=30)
            turn_state = {"target_id": None, "skill_idx": None, "done": False}

            if target_options:
                target_sel = discord.ui.Select(placeholder="🎯 Elegir objetivo...", options=target_options)
                async def target_cb(inter: discord.Interaction):
                    if inter.user.id != uid:
                        await inter.response.send_message("❌ No es tu turno.", ephemeral=True)
                        return
                    turn_state["target_id"] = int(inter.user.id if inter.data["values"][0] == str(uid) else inter.data["values"][0])
                    # Usar el valor seleccionado directamente
                    turn_state["target_id"] = int(inter.data["values"][0])
                    await inter.response.defer()
                target_sel.callback = target_cb
                turn_view.add_item(target_sel)

            if skill_options:
                skill_sel = discord.ui.Select(placeholder="✨ Elegir habilidad...", options=skill_options[:25])
                async def skill_cb(inter: discord.Interaction):
                    if inter.user.id != uid:
                        await inter.response.send_message("❌ No es tu turno.", ephemeral=True)
                        return
                    turn_state["skill_idx"] = int(inter.data["values"][0])
                    await inter.response.defer()
                skill_sel.callback = skill_cb
                turn_view.add_item(skill_sel)

            confirm_btn = discord.ui.Button(label="✅ Confirmar", style=discord.ButtonStyle.success)
            async def confirm_cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu turno.", ephemeral=True)
                    return
                if turn_state["target_id"] is None:
                    await inter.response.send_message("❌ Elige un objetivo primero.", ephemeral=True)
                    return
                turn_state["done"] = True
                await inter.response.defer()
            confirm_btn.callback = confirm_cb
            turn_view.add_item(confirm_btn)

            # Auto-confirm timer: si no actúa en 30s, ataque automático
            skip_btn = discord.ui.Button(label="⏩ Saltar (auto)", style=discord.ButtonStyle.secondary)
            async def skip_cb(inter: discord.Interaction):
                turn_state["done"] = True
                turn_state["target_id"] = int(enemies[0]) if enemies else None
                turn_state["skill_idx"] = 0
                await inter.response.defer()
            skip_btn.callback = skip_cb
            turn_view.add_item(skip_btn)

            turn_msg = await channel.send(f"<@{uid}>", embed=turn_embed, view=turn_view)

            # Esperar hasta 30 segundos
            for _ in range(30):
                if turn_state["done"]:
                    break
                await asyncio.sleep(1)

            # Auto-acción si no respondió
            if not turn_state["done"] or turn_state["target_id"] is None:
                turn_state["target_id"] = int(enemies[0]) if enemies else None
                turn_state["skill_idx"] = 0

            # Ejecutar ataque
            target_uid = turn_state["target_id"]
            defender_fig = get_active_fighter(target_uid)
            sess.log = []

            if defender_fig and attacker_fig:
                skill_idx = turn_state["skill_idx"] if turn_state["skill_idx"] is not None else 0
                skills_list = FIGURE_SKILLS.get(attacker_fig.get("key", ""), [])
                skill = skills_list[skill_idx] if skill_idx is not None and skill_idx < len(skills_list) else None

                if skill:
                    power = skill.get("power", 50)
                    dmg = max(1, int(attacker_fig["atk"] * (power / 100)) + random.randint(-3, 8) - (defender_fig["defense"] // 4))
                    if sess.invert_event_active:
                        # Invertido: el daño cura al defensor
                        defender_fig["hp"] = min(defender_fig["max_hp"], defender_fig["hp"] + dmg)
                        sess.log.append(f"🔀 **{sess.players[uid]['name']}** usa **{skill['name']}** en {sess.players[target_uid]['name']} → ¡**CURA {dmg}HP**! (invertido)")
                    else:
                        defender_fig["hp"] = max(0, defender_fig["hp"] - dmg)
                        sess.log.append(f"⚔️ **{sess.players[uid]['name']}** usa **{skill['name']}** en {sess.players[target_uid]['name']} → **{dmg} daño**")
                    if defender_fig["hp"] <= 0:
                        sess.log.append(f"💀 {defender_fig['emoji']} {defender_fig['name']} cayó!")
                else:
                    dmg = random.randint(10, 30)
                    defender_fig["hp"] = max(0, defender_fig["hp"] - dmg)
                    sess.log.append(f"⚔️ **{sess.players[uid]['name']}** ataca a {sess.players[target_uid]['name']} → **{dmg} daño**")

            # Verificar si el target fue eliminado
            if not any(f["hp"] > 0 for f in sess.fighters.get(target_uid, [])):
                sess.eliminated.add(target_uid)
                sess.log.append(f"💀 **{sess.players[target_uid]['name']}** fue eliminado!")

            try:
                await turn_msg.delete()
            except Exception:
                pass

            status_msg = await send_status(status_msg)

        sess.round_num += 1

        # Regenerar energía
        for uid, figs in sess.fighters.items():
            for f in figs:
                if f["hp"] > 0:
                    f["energy"] = min(100, f.get("energy", 0) + 20)

    # Fin de batalla
    winner_ids = alive_players()
    if channel_id in active_multiplayer:
        del active_multiplayer[channel_id]

    if winner_ids:
        wid = winner_ids[0]
        wname = sess.players[wid]["name"]
        db = load_db()
        wu = get_user(db, wid)
        if wu:
            wu["wins"] = wu.get("wins", 0) + 1
            wu["coins"] = wu.get("coins", 0) + COINS_WIN * (len(sess.players) - 1)
            wu["xp"] = wu.get("xp", 0) + XP_PER_WIN
            while wu["xp"] >= xp_to_level_up(wu["level"]):
                wu["xp"] -= xp_to_level_up(wu["level"])
                wu["level"] += 1
        for uid in sess.eliminated:
            lu = get_user(db, uid)
            if lu:
                lu["losses"] = lu.get("losses", 0) + 1
                lu["coins"] = lu.get("coins", 0) + COINS_LOSS
        save_db(db)
        final_embed = discord.Embed(
            title=f"🏆 ¡{wname} ganó el Multijugador!",
            description=f"¡**{wname}** es el último en pie!\n+{COINS_WIN * (len(sess.players)-1)}🪙 | +{XP_PER_WIN}XP",
            color=0xf1c40f
        )
    else:
        final_embed = discord.Embed(title="🤝 Empate multijugador", description="¡Nadie sobrevivió!", color=0x95a5a6)
    await channel.send(embed=final_embed)

# ============================================================
#  TIENDA: Jane Doe requiere quest completada