"""
commands_battle.py — Comandos de batalla.

/pvp-enemy  → enemigos comunes (botón AZUL, dificultad 1–5)
/pvp-boss   → jefes difíciles  (botón ROJO, dificultad 6+)
/retar      → PvP entre jugadores
/ranking    → leaderboard
/diario     → recompensa diaria
/reset      → reiniciar batalla activa (admin)
"""

import random
from datetime import datetime, timezone

import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import (
    FIGURES, FIGURE_SKILLS,
    RARITY_COLOR, RARITY_STARS,
    XP_PER_WIN, XP_PER_LOSS, COINS_WIN, COINS_LOSS,
    apply_level_bonus,
)
from battle import (
    active_battles,
    BattleState, BattleView, get_battle_view,
    make_fighter, bot_turn, end_battle,
    ENERGY_MAX, ENERGY_PER_TURN,
)
from bosses import BOT_ROSTER, IMPOSTOR_REWARDS
from economy import (
    ACHIEVEMENTS, check_achievements, grant_achievement,
    _check_player_levelup,
)

ADMIN_ID = 1236293193893412975

# ── separar roster ───────────────────────────────────────────────────────────
_ENEMIES = [b for b in BOT_ROSTER if not b.get("is_boss")]
_BOSSES  = [b for b in BOT_ROSTER if b.get("is_boss")]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def _apply_recipe_buffs(user_data: dict, team: list, db) -> str | None:
    buffs = user_data.get("buffs", [])
    if not buffs:
        return None
    remaining = []
    papyrus_result = None
    papyrus_rolled = False
    papyrus_good   = False
    for b in buffs:
        effect = b.get("effect")
        val    = b.get("value", 0)
        turns  = b.get("turns", 1)
        if effect == "papyrus_special" and not papyrus_rolled:
            papyrus_good   = random.randint(1, 100) <= 90
            papyrus_rolled = True
            papyrus_result = "good" if papyrus_good else "bad"
        for fig in team:
            if effect == "hp_boost":
                fig["hp"] += val; fig["max_hp"] += val
            elif effect == "atk_boost":
                fig["atk"] = fig.get("atk", 0) + val
            elif effect == "all_boost":
                fig["atk"]    = fig.get("atk", 0) + b.get("atk_bonus", 0)
                hp_b           = b.get("hp_bonus", 0)
                fig["hp"]     += hp_b; fig["max_hp"] += hp_b
            elif effect == "papyrus_special":
                sign           = 1 if papyrus_good else -1
                fig["atk"]    = max(1, fig.get("atk", 0) + sign * b.get("atk_bonus", 25))
                hp_b           = b.get("hp_bonus", 40); def_b = b.get("def_bonus", 25)
                fig["hp"]     = max(1, fig["hp"] + sign * hp_b)
                fig["max_hp"] = max(1, fig["max_hp"] + sign * hp_b)
                fig["defense"]= max(0, fig.get("defense", 0) + sign * def_b)
        if effect in ("coins_boost", "xp_boost"):
            remaining.append(b)
        elif turns > 1:
            remaining.append({**b, "turns": turns - 1})
    user_data["buffs"] = remaining
    return papyrus_result


def _build_team(figs: list, team_indices: list, user_data: dict = None):
    """Construye equipo e inyecta variant_key desde variants_equipped del usuario."""
    keys, datas = [], []
    equipped = (user_data or {}).get("variants_equipped", {})
    for idx in (team_indices or []):
        if idx is not None and idx < len(figs):
            fd  = dict(figs[idx])  # copy to avoid mutating DB data
            key = fd["key"]
            if key in equipped:
                fd["variant_key"]      = equipped[key].get("key")
                fd["variant_seasonal"] = equipped[key].get("seasonal", False)
            keys.append(key); datas.append(fd)
    while len(keys) < 3 and figs:
        fd  = dict(figs[0])
        key = fd["key"]
        if key in equipped:
            fd["variant_key"]      = equipped[key].get("key")
            fd["variant_seasonal"] = equipped[key].get("seasonal", False)
        keys.append(key); datas.append(fd)
    return keys[:3], datas[:3]


def _team_preview(keys: list) -> str:
    parts = []
    for k in keys:
        fig = FIGURES.get(k)
        if fig: parts.append(f"{fig['emoji']} {fig['name']}")
    return " | ".join(parts) if parts else "—"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  LANZADOR GENÉRICO DE BATALLA vs BOT                                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _launch_bot_battle(inter: discord.Interaction, bot_data: dict, user: dict, db):
    channel_id = inter.channel_id

    if channel_id in active_battles:
        await inter.response.send_message("❌ Ya hay una batalla activa en este canal.", ephemeral=True)
        return

    if bot_data.get("special_7v3"):
        await _start_impostor_7v3(inter, bot_data, user["figures"], user, db)
        return

    p1_keys, p1_figs_data = _build_team(user["figures"], user.get("team", []), user)
    if not p1_keys:
        await inter.response.send_message("❌ Tu equipo está vacío. Usa /equipar primero.", ephemeral=True)
        return

    bot_level = bot_data["level"]
    hp_mult   = bot_data.get("hp_mult", 1.0)
    atk_mult  = bot_data.get("atk_mult", 1.0)
    nrg_bonus = bot_data.get("energy_bonus", 0)
    p2_keys   = [k for k in bot_data["team"] if k in FIGURES]
    p2_figs_data = [
        {"key": k, "level": bot_level, "xp": 0,
         "hp_mult": hp_mult, "atk_mult": atk_mult, "energy_bonus": nrg_bonus}
        for k in p2_keys
    ]
    if not p2_keys:
        await inter.response.send_message("❌ Error al cargar el equipo enemigo.", ephemeral=True)
        return

    battle = BattleState(
        p1_id=inter.user.id, p2_id=0,
        p1_team_keys=p1_keys, p2_team_keys=p2_keys,
        p1_figs_data=p1_figs_data, p2_figs_data=p2_figs_data,
        is_bot=True,
    )
    battle.p1_name = user.get("name", "Jugador")
    battle.p2_name = bot_data["name"]
    battle.bot_id  = bot_data.get("id", "")
    battle.bot_reward_coins = bot_data.get("reward_coins", COINS_WIN)
    battle.bot_reward_xp    = bot_data.get("reward_xp", XP_PER_WIN)

    db2 = load_db()
    usr2 = get_user(db2, inter.user.id)
    papyrus_res = _apply_recipe_buffs(usr2, battle.p1_team, db2)
    save_db(db2)

    active_battles[channel_id] = battle

    is_boss = bot_data.get("is_boss", False)
    title   = "💀 ¡BATALLA CONTRA JEFE!" if is_boss else f"⚔️ ¡BATALLA vs {bot_data['name']}!"
    embed   = battle.get_embed(title=title)

    if papyrus_res == "good":
        embed.add_field(name="🍝 Spaghetti de Langosta",
            value="**NYEHEHEH! MY COOKING SAVED THE DAY!**\n+25 ATK · +40 HP · +25 DEF a todo tu equipo.", inline=False)
    elif papyrus_res == "bad":
        embed.add_field(name="🍝 Spaghetti de Langosta",
            value="**Nyeh... heh... heh? Why is it moving?**\n-25 ATK · -40 HP · -25 DEF a todo tu equipo. 💀", inline=False)

    view = get_battle_view(battle)
    await inter.response.edit_message(embed=embed, view=view)
    battle.message = await inter.original_response()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /pvp-enemy                                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _pvp_enemy_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True); return
    if interaction.channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa aquí.", ephemeral=True); return
    if not user.get("figures"):
        await interaction.response.send_message("❌ No tienes figuras. Compra en `/tienda`.", ephemeral=True); return

    uid   = interaction.user.id
    embed = discord.Embed(
        title="🎮 Elige tu rival — Enemigos",
        description="🔵 **Botón azul** = enemigo normal. A más estrellas, más difícil.",
        color=0x3498db,
    )
    for b in _ENEMIES:
        embed.add_field(
            name  = f"{b['name']} {'⭐'*b['difficulty']}",
            value = f"{b['desc']}\n🎭 {_team_preview(b['team'])}\n💰 {b['reward_coins']}🪙 · +{b['reward_xp']} XP",
            inline=False,
        )

    view = discord.ui.View(timeout=60)
    for b in _ENEMIES:
        btn = discord.ui.Button(label=b["name"], style=discord.ButtonStyle.primary, custom_id=f"enemy_{b['id']}")
        def make_cb(bot_data=b):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ Este menú no es tuyo.", ephemeral=True); return
                db2 = load_db(); user2 = get_user(db2, inter.user.id)
                if not user2:
                    await inter.response.send_message("❌ No estás registrado.", ephemeral=True); return
                await _launch_bot_battle(inter, bot_data, user2, db2)
            return cb
        btn.callback = make_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /pvp-boss                                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _pvp_boss_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True); return
    if interaction.channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa aquí.", ephemeral=True); return
    if not user.get("figures"):
        await interaction.response.send_message("❌ No tienes figuras. Compra en `/tienda`.", ephemeral=True); return

    uid   = interaction.user.id
    embed = discord.Embed(
        title="💀 Elige tu rival — JEFES",
        description="🔴 **Botón rojo** = jefe difícil. Recompensas especiales y logros.",
        color=0xe74c3c,
    )
    for b in _BOSSES:
        tag = " 👑 JEFE FINAL" if b.get("id") == "jefe" else " 👑 JEFE"
        embed.add_field(
            name  = f"{b['name']}{tag} {'⭐'*b['difficulty']}",
            value = f"{b['desc']}\n🎭 {_team_preview(b['team'])}\n💰 {b['reward_coins']}🪙 · +{b['reward_xp']} XP",
            inline=False,
        )

    view = discord.ui.View(timeout=60)
    for b in _BOSSES:
        btn = discord.ui.Button(label=b["name"], style=discord.ButtonStyle.danger, custom_id=f"boss_{b['id']}")
        def make_cb(bot_data=b):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ Este menú no es tuyo.", ephemeral=True); return
                db2 = load_db(); user2 = get_user(db2, inter.user.id)
                if not user2:
                    await inter.response.send_message("❌ No estás registrado.", ephemeral=True); return
                await _launch_bot_battle(inter, bot_data, user2, db2)
            return cb
        btn.callback = make_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  BATALLA 7v3 DEL IMPOSTOR NEGRO                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _start_impostor_7v3(interaction, bot_data, user_figs, user_data, db):
    uid   = interaction.user.id
    embed = discord.Embed(
        title="🔪 DEFEAT — El Impostor Negro",
        description=(
            "**7 impostores** te esperan. Puedes llevar entre **3 y 7 figuras**.\n\n"
            "⚠️ Más figuras = peores recompensas:\n"
            "```\n3 figuras → 4,000🪙 + 2 niveles auto + 2 recetas + LOGRO\n"
            "4 figuras → 2,500🪙 + 1 nivel auto + 1 receta\n"
            "5 figuras → 1,500🪙\n6 figuras → 500🪙\n7 figuras → Sin recompensa 💀\n```\n"
            "Elige cuántas figuras usar:"
        ),
        color=0x2c2f33,
    )
    view = discord.ui.View(timeout=60)
    for count in range(3, 8):
        lbl = f"{count} figuras" + (" 👑" if count == 3 else " 💀" if count == 7 else "")
        style = (
            discord.ButtonStyle.danger    if count <= 3 else
            discord.ButtonStyle.primary   if count <= 5 else
            discord.ButtonStyle.secondary
        )
        btn = discord.ui.Button(label=lbl, style=style, custom_id=f"imp_{count}")
        def make_cb(ts=count):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True); return
                chosen = []
                for idx in user_data.get("team", []):
                    if idx is not None and idx < len(user_figs) and len(chosen) < ts:
                        chosen.append(user_figs[idx])
                if ts > 3:
                    used = set(id(f) for f in chosen)
                    for f in user_figs:
                        if len(chosen) >= ts: break
                        if id(f) not in used: chosen.append(f); used.add(id(f))
                await _launch_7v3_battle(inter, bot_data, chosen, user_data, db, ts)
            return cb
        btn.callback = make_cb()
        view.add_item(btn)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def _launch_7v3_battle(interaction, bot_data, player_figs, user_data, db, team_size):
    channel_id = interaction.channel_id
    if channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa.", ephemeral=True); return

    valid_figs = [fd for fd in player_figs[:team_size] if fd.get("key") in FIGURES]
    if not valid_figs:
        await interaction.response.send_message("❌ No tienes figuras válidas.", ephemeral=True); return

    p1_keys      = [fd["key"] for fd in valid_figs]
    p1_figs_data = valid_figs
    bot_level    = bot_data.get("level", 1)
    hp_mult      = bot_data.get("hp_mult", 1.0)
    atk_mult     = bot_data.get("atk_mult", 1.0)
    nrg_bonus    = bot_data.get("energy_bonus", 0)
    p2_keys      = [k for k in bot_data["team"] if k in FIGURES]
    p2_figs_data = [{"key": k, "level": bot_level, "xp": 0,
                     "hp_mult": hp_mult, "atk_mult": atk_mult, "energy_bonus": nrg_bonus}
                    for k in p2_keys]
    if not p2_keys:
        await interaction.response.send_message("❌ Error al cargar enemigos.", ephemeral=True); return

    battle = BattleState(
        p1_id=interaction.user.id, p2_id=0,
        p1_team_keys=p1_keys, p2_team_keys=p2_keys,
        p1_figs_data=p1_figs_data, p2_figs_data=p2_figs_data,
        is_bot=True,
    )
    battle.p1_name            = user_data.get("name", "Jugador")
    battle.p2_name            = bot_data["name"]
    battle.bot_id             = bot_data.get("id", "")
    battle.impostor_7v3       = True
    battle.impostor_team_size = team_size

    active_battles[channel_id] = battle
    embed = battle.get_embed(title=f"🔪 DEFEAT — {bot_data['name']}")
    embed.set_footer(text=f"Usas {team_size} figuras · Recompensa: {IMPOSTOR_REWARDS.get(team_size,{}).get('coins',0):,}🪙")
    view  = get_battle_view(battle)
    try:
        await interaction.response.edit_message(embed=embed, view=view)
    except Exception:
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            await interaction.followup.send(embed=embed, view=view)
    battle.message = await interaction.original_response()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /retar                                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _retar_cmd(interaction: discord.Interaction, rival: discord.Member):
    db         = load_db()
    user       = get_user(db, interaction.user.id)
    rival_data = get_user(db, rival.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True); return
    if not rival_data:
        await interaction.response.send_message("❌ Tu rival no está registrado.", ephemeral=True); return
    if rival.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes retarte a ti mismo.", ephemeral=True); return
    if not user.get("figures"):
        await interaction.response.send_message("❌ No tienes figuras. Compra en `/tienda`.", ephemeral=True); return
    if not rival_data.get("figures"):
        await interaction.response.send_message(f"❌ {rival.mention} no tiene figuras.", ephemeral=True); return
    if interaction.channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay batalla activa aquí.", ephemeral=True); return

    u1_keys, _ = _build_team(user["figures"],      user.get("team", []), user)
    u2_keys, _ = _build_team(rival_data["figures"], rival_data.get("team", []), rival_data)

    embed = discord.Embed(
        title="⚔️ ¡DESAFÍO PvP!",
        description=f"{interaction.user.mention} reta a {rival.mention} a un duelo!",
        color=0xe74c3c,
    )
    embed.add_field(name=f"🥊 {user['name']}",       value=_team_preview(u1_keys), inline=False)
    embed.add_field(name="⚡ VS ⚡",                  value="\u200b",              inline=False)
    embed.add_field(name=f"🥊 {rival_data['name']}", value=_team_preview(u2_keys), inline=False)

    accept_btn = discord.ui.Button(label="✅ Aceptar",  style=discord.ButtonStyle.success, custom_id="accept_pvp")
    reject_btn = discord.ui.Button(label="❌ Rechazar", style=discord.ButtonStyle.danger,  custom_id="reject_pvp")

    async def accept_callback(btn_inter: discord.Interaction):
        if btn_inter.user.id != rival.id:
            await btn_inter.response.send_message("❌ Solo el retado puede aceptar.", ephemeral=True); return
        if interaction.channel_id in active_battles:
            await btn_inter.response.send_message("❌ Ya hay una batalla activa.", ephemeral=True); return
        db2 = load_db()
        u1  = get_user(db2, interaction.user.id)
        u2  = get_user(db2, rival.id)
        k1, d1 = _build_team(u1["figures"], u1.get("team", []), u1)
        k2, d2 = _build_team(u2["figures"], u2.get("team", []), u2)
        battle = BattleState(
            p1_id=interaction.user.id, p2_id=rival.id,
            p1_team_keys=k1, p2_team_keys=k2,
            p1_figs_data=d1, p2_figs_data=d2, is_bot=False,
        )
        battle.p1_name = u1.get("name", "Jugador 1")
        battle.p2_name = u2.get("name", "Jugador 2")
        _apply_recipe_buffs(u1, battle.p1_team, db2)
        _apply_recipe_buffs(u2, battle.p2_team, db2)
        save_db(db2)
        active_battles[interaction.channel_id] = battle
        view = get_battle_view(battle)
        await btn_inter.response.edit_message(embed=battle.get_embed(title="⚔️ ¡LA BATALLA COMIENZA!"), view=view)
        battle.message = await btn_inter.original_response()

    async def reject_callback(btn_inter: discord.Interaction):
        if btn_inter.user.id != rival.id:
            await btn_inter.response.send_message("❌ Solo el retado puede rechazar.", ephemeral=True); return
        await btn_inter.response.edit_message(embed=discord.Embed(
            title="❌ Desafío rechazado", description=f"{rival.mention} rechazó el duelo.", color=0x95a5a6), view=None)

    accept_btn.callback = accept_callback
    reject_btn.callback = reject_callback
    v = discord.ui.View(timeout=60)
    v.add_item(accept_btn); v.add_item(reject_btn)
    await interaction.response.send_message(content=rival.mention, embed=embed, view=v)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /ranking                                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def _build_leaderboard_embed(users: dict, category: str) -> discord.Embed:
    medals = ["🥇", "🥈", "🥉"] + ["🔸"] * 7
    if category == "wins":
        title    = "🏆 Leaderboard — Victorias"; color = 0xf1c40f
        sorted_u = sorted(users.values(), key=lambda u: u.get("wins", 0), reverse=True)[:10]
        def row(u):
            t = u.get("wins", 0) + u.get("losses", 0)
            return f"✅ {u.get('wins',0)}V ❌ {u.get('losses',0)}D | WR: **{round(u.get('wins',0)/t*100,1) if t else 0}%**"
    elif category == "coins":
        title    = "💰 Leaderboard — Dinero"; color = 0x2ecc71
        sorted_u = sorted(users.values(), key=lambda u: u.get("coins", 0), reverse=True)[:10]
        def row(u): return f"💰 **{u.get('coins',0):,}** monedas"
    elif category == "figures":
        title    = "🎭 Leaderboard — Figuras"; color = 0x9b59b6
        sorted_u = sorted(users.values(), key=lambda u: len(set(f["key"] for f in u.get("figures",[]))), reverse=True)[:10]
        def row(u):
            uq = len(set(f["key"] for f in u.get("figures",[])))
            return f"🎭 **{uq}** únicas ({len(u.get('figures',[]))} totales)"
    elif category == "fig_level":
        title    = "⬆️ Leaderboard — Nivel de Figuras"; color = 0x3498db
        sorted_u = sorted(users.values(), key=lambda u: sum(f.get("level",1) for f in u.get("figures",[])), reverse=True)[:10]
        def row(u):
            lvls = [f.get("level",1) for f in u.get("figures",[])]
            return f"⬆️ Total: **{sum(lvls)}** | Máx: **{max(lvls) if lvls else 0}**"
    elif category == "recipes":
        title    = "🧑‍🍳 Leaderboard — Recetas"; color = 0xe67e22
        sorted_u = sorted(users.values(), key=lambda u: u.get("recipe_count",0), reverse=True)[:10]
        def row(u): return f"🧑‍🍳 **{u.get('recipe_count',0)}** recetas"
    elif category == "playerlevel":
        title    = "🏆 Leaderboard — Nivel Jugador"; color = 0x3498db
        sorted_u = sorted(users.values(), key=lambda u: u.get("rebirth_count",0)*1000+u.get("level",1), reverse=True)[:10]
        def row(u):
            rb = u.get("rebirth_count",0); lv = u.get("level",1)
            return f"🏆 Nivel **{lv}**{f' 🔄×{rb}' if rb else ''} · SP: {u.get('skill_points',0)}"
    else:
        return discord.Embed(title="❌ Categoría desconocida", color=0xe74c3c)
    embed = discord.Embed(title=title, color=color)
    for i, u in enumerate(sorted_u):
        embed.add_field(name=f"{medals[i]} {u.get('name','?')} (Nv.{u.get('level',1)})", value=row(u), inline=False)
    return embed


async def _ranking_cmd(interaction: discord.Interaction):
    db    = load_db(); users = db.get("users", {})
    if not users:
        await interaction.response.send_message("📭 Nadie registrado aún.", ephemeral=True); return
    cats = [("wins","🏆 Victorias"),("coins","💰 Dinero"),("figures","🎭 Figuras"),
            ("fig_level","⬆️ Niveles"),("recipes","🧑‍🍳 Recetas"),("playerlevel","🏆 Niv. Jugador")]
    async def send_lb(inter, category, edit=False):
        emb = _build_leaderboard_embed(users, category)
        v   = discord.ui.View(timeout=120)
        for cat_id, cat_lbl in cats:
            btn = discord.ui.Button(label=cat_lbl,
                style=discord.ButtonStyle.primary if cat_id==category else discord.ButtonStyle.secondary,
                custom_id=f"lb_{cat_id}")
            async def cb(i, c=cat_id): await send_lb(i, c, edit=True)
            btn.callback = cb; v.add_item(btn)
        if edit: await inter.response.edit_message(embed=emb, view=v)
        else:    await inter.response.send_message(embed=emb, view=v)
    await send_lb(interaction, "wins")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /diario                                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

DAILY_MAX_STREAK = 7
DAILY_STREAK_REWARDS = {
    1:{"coins":300,"emoji":"📦"}, 2:{"coins":350,"emoji":"📦"},
    3:{"coins":450,"emoji":"🎁"}, 4:{"coins":500,"emoji":"🎁"},
    5:{"coins":600,"emoji":"💎"}, 6:{"coins":700,"emoji":"💎"},
    7:{"coins":1000,"emoji":"🌟"},
}
DAILY_FIGURE_CHANCE = {1:10,2:12,3:18,4:22,5:30,6:40,7:60}

def _get_figure_rarity_pool(streak: int) -> list:
    pool = []; excluded = {"roblox_boss","santa_vaca","lobster","omega_flowey"}
    for key, fig in FIGURES.items():
        if key in excluded or fig.get("price",0) <= 0: continue
        r = fig.get("rarity","común").lower()
        w = {"común":max(1,6-streak),"raro":max(1,4-streak//2),"épico":streak,"epico":streak,
             "legendario":max(0,streak-2),"mítico":max(0,streak-4)}.get(r,1)
        pool.extend([key]*w)
    return pool

async def _diario_cmd(interaction: discord.Interaction):
    db = load_db(); user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True); return
    now    = datetime.now(timezone.utc)
    streak = user.get("daily_streak", 0)
    if user.get("last_daily"):
        diff   = (now - datetime.fromisoformat(user["last_daily"])).total_seconds() / 3600
        if diff < 24:
            h,m = int(24-diff), int(((24-diff)%1)*60)
            await interaction.response.send_message(
                embed=discord.Embed(title="⏰ Ya reclamaste hoy", description=f"Vuelve en **{h}h {m}m**.", color=0xe74c3c),
                ephemeral=True); return
        elif diff >= 48:
            streak = 0
    streak = min(streak+1, DAILY_MAX_STREAK)
    reward = DAILY_STREAK_REWARDS[streak]
    user["coins"]        = user.get("coins",0) + reward["coins"]
    user["last_daily"]   = now.isoformat()
    user["daily_streak"] = streak
    user["xp"]           = user.get("xp",0) + 10*streak
    _check_player_levelup(user)
    figure_won = None
    pool       = [k for k in _get_figure_rarity_pool(streak) if k not in {f["key"] for f in user.get("figures",[])}]
    if pool and random.randint(1,100) <= DAILY_FIGURE_CHANCE[streak]:
        figure_won = random.choice(pool)
        user.setdefault("figures",[]).append({"key":figure_won,"level":1,"xp":0})
    save_db(db)
    color = 0xf1c40f if streak==7 else (0x9b59b6 if streak>=5 else (0x3498db if streak>=3 else 0x2ecc71))
    emb   = discord.Embed(title=f"{reward['emoji']} ¡Recompensa Diaria!", color=color)
    emb.add_field(name="💰 Ganadas", value=f"+**{reward['coins']:,}**🪙", inline=True)
    emb.add_field(name="💳 Total",   value=f"**{user['coins']:,}**🪙",    inline=True)
    emb.add_field(name="🔥 Racha",   value=f"**{streak}** día(s)",         inline=True)
    barra = "".join(DAILY_STREAK_REWARDS[d]["emoji"] if d<=streak else "⬛" for d in range(1,8))
    emb.add_field(name="📅 Semanal", value=barra, inline=False)
    if figure_won:
        fig = FIGURES[figure_won]; star = RARITY_STARS.get(fig.get("rarity","común"),"⚪")
        emb.add_field(name="🎉 ¡FIGURA SORPRESA!",
            value=f"{fig['emoji']} **{fig['name']}** {star}\n❤️ {fig['hp']} ⚔️ {fig['attack']} 🛡️ {fig['defense']}", inline=False)
        if fig.get("image"): emb.set_image(url=fig["image"])
        emb.color = RARITY_COLOR.get(fig.get("rarity","común"), color)
    emb.set_footer(text="Vuelve en 24 horas para mantener tu racha!")
    await interaction.response.send_message(embed=emb)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  REGISTRO DE COMANDOS                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def register_commands(bot):
    """Llama desde main.py: register_commands(bot) después de crear el bot."""

    @bot.tree.command(name="pvp-enemy", description="Pelea contra un enemigo normal")
    async def pvp_enemy(interaction: discord.Interaction):
        await _pvp_enemy_cmd(interaction)

    @bot.tree.command(name="pvp-boss", description="Pelea contra un jefe — difícil y con recompensas especiales")
    async def pvp_boss(interaction: discord.Interaction):
        await _pvp_boss_cmd(interaction)

    @bot.tree.command(name="retar", description="Reta a otro jugador a un duelo PvP")
    @app_commands.describe(rival="El jugador al que quieres retar")
    async def retar(interaction: discord.Interaction, rival: discord.Member):
        await _retar_cmd(interaction, rival)

    @bot.tree.command(name="ranking", description="Leaderboards del servidor — elige la categoría")
    async def ranking(interaction: discord.Interaction):
        await _ranking_cmd(interaction)

    @bot.tree.command(name="diario", description="Reclama tu recompensa diaria (cada 24 horas)")
    async def diario(interaction: discord.Interaction):
        await _diario_cmd(interaction)

    @bot.tree.command(name="reset", description="[ADMIN] Reinicia la batalla activa en este canal")
    async def reset(interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("❌ Solo el admin puede usar esto.", ephemeral=True); return
        if interaction.channel_id in active_battles:
            del active_battles[interaction.channel_id]
            await interaction.response.send_message("✅ Batalla reiniciada.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No hay batalla activa aquí.", ephemeral=True)
