"""
commands_admin.py — Comandos de administrador y misceláneos (/oro, /bomb, /nuke, /gift, /say, /holy, /get, /ayuda).
"""
import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import FIGURES, SECRET_FIGURES, SECRET_OWNER_ID, secret_store_unlocked
from economy import INGREDIENTS, ACHIEVEMENTS, grant_achievement

ADMIN_ID = 1236293193893412975

# ============================================================
#  PERMISOS DE ADMINISTRADOR
# ============================================================
MATHEO_ID = 357067563842297857  # ID de matheogamer64 (siempre tiene acceso)

def is_admin(interaction: discord.Interaction) -> bool:
    """Devuelve True si el usuario es admin del servidor o es matheogamer64."""
    if interaction.user.id == MATHEO_ID:
        return True
    # Verificar permisos de administrador en el servidor
    if isinstance(interaction.user, discord.Member):
        return interaction.user.guild_permissions.administrator
    return False

# --- NUKE (solo admins) ---
# --- ROB ---
ROB_COOLDOWN = {}  # {user_id: timestamp}
# ============================================================
#  COMANDOS /gift y /trade
# ============================================================

# --- GIFT ---
# --- TRADE ---
pending_trades = {}  # {receiver_id: trade_data}

_RARITY_ORDER = ["común", "raro", "épico", "legendario", "mítico"]
_RARITY_EMOJI = {"común": "⚪", "raro": "🔵", "épico": "🟣", "legendario": "🌟", "mítico": "🔱"}
_RARITY_NORM  = {"común":"común","raro":"raro","épico":"épico","epico":"épico",
                 "legendario":"legendario","Legendario":"legendario",
                 "mítico":"mítico","Mítico":"mítico"}

def _get_all_by_rarity() -> dict:
    excluded = {"roblox_boss","santa_vaca","lobster","janedoe"}
    result = {r: [] for r in _RARITY_ORDER}
    for key, fig in FIGURES.items():
        if key in excluded: continue
        r = _RARITY_NORM.get(fig.get("rarity","común"), "común")
        if r in result:
            result[r].append((key, fig))
    return result

async def _give_figure(inter: discord.Interaction, fig_key: str, uid: int, db):
    """Entrega la figura al usuario y confirma."""
    db2 = load_db()
    u2  = get_user(db2, inter.user.id)
    u2.setdefault("figures",[]).append({"key": fig_key, "level":1, "xp":0})
    team = u2.get("team",[None,None,None])
    while len(team) < 3: team.append(None)
    for i in range(3):
        if team[i] is None:
            team[i] = len(u2["figures"]) - 1
            break
    u2["team"] = team
    save_db(db2)
    fig  = FIGURES.get(fig_key, {})
    norm = _RARITY_NORM.get(fig.get("rarity","común"),"común")
    ok   = discord.Embed(
        title=f"✅ ¡{fig.get('name', fig_key)} obtenida!",
        description=(
            f"{fig.get('emoji','')} **{fig.get('name', fig_key)}** añadida a tu colección.\n"
            f"{_RARITY_EMOJI.get(norm,'⚪')} {norm.capitalize()} · "
            f"❤️{fig.get('hp','?')} ⚔️{fig.get('attack','?')} "
            f"🛡️{fig.get('defense','?')} ⚡{fig.get('speed','?')}"
        ),
        color=0xffd700
    )
    if fig.get("image"):
        ok.set_thumbnail(url=fig["image"])
    await inter.response.edit_message(embed=ok, view=None)

async def _show_get_select(interaction, rarity: str, by_r: dict, uid: int, db, page: int = 0, user: dict = None):
    """Muestra un Select dropdown con las figuras de la rareza elegida."""
    import re as _re
    if user is None:
        db2  = load_db()
        user = get_user(db2, uid) or {}
    figs        = by_r.get(rarity, [])
    PAGE_SIZE   = 25
    total_pages = max(1, (len(figs) + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = max(0, min(page, total_pages - 1))
    page_figs   = figs[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    embed = discord.Embed(
        title=f"🥇 {_RARITY_EMOJI.get(rarity,'')} {rarity.capitalize()} — Selecciona una figura",
        description=f"Página {page+1}/{total_pages}  ·  {len(figs)} figuras",
        color=0xffd700
    )
    for key, fig in page_figs:
        embed.add_field(
            name=f"{fig['emoji']} {fig['name']}",
            value=f"❤️{fig.get('hp','?')} ⚔️{fig.get('attack','?')} 🛡️{fig.get('defense','?')} ⚡{fig.get('speed','?')}",
            inline=True
        )

    options = []
    for key, fig in page_figs:
        raw_emoji = fig.get("emoji","")
        emoji_val = None
        if raw_emoji and not raw_emoji.startswith("<"):
            emoji_val = raw_emoji
        elif raw_emoji.startswith("<"):
            m = _re.match(r"<(a?):([^:]+):(\d+)>", raw_emoji)
            if m:
                emoji_val = discord.PartialEmoji(
                    name=m.group(2), id=int(m.group(3)), animated=m.group(1)=="a")
        owned = any(f["key"] == key for f in user.get("figures", []))
        options.append(discord.SelectOption(
            label=f"{'✅ ' if owned else ''}{fig['name']}"[:100],
            value=key,
            description=f"❤️{fig.get('hp','?')} ⚔️{fig.get('attack','?')} 🛡️{fig.get('defense','?')} ⚡{fig.get('speed','?')}",
            emoji=emoji_val
        ))

    view   = discord.ui.View(timeout=180)
    select = discord.ui.Select(
        placeholder=f"🥇 Elige una figura {_RARITY_EMOJI.get(rarity,'')} {rarity.capitalize()}...",
        options=options, custom_id="get_select", row=0
    )
    async def select_cb(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True); return
        await _give_figure(inter, inter.data["values"][0], uid, db)
    select.callback = select_cb
    view.add_item(select)

    if page > 0:
        prev_btn = discord.ui.Button(label="◀ Anterior", style=discord.ButtonStyle.secondary, custom_id="get_prev", row=1)
        def make_prev(p=page):
            async def cb(inter):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True); return
                await _show_get_select(inter, rarity, by_r, uid, db, p - 1)
            return cb
        prev_btn.callback = make_prev(); view.add_item(prev_btn)
    if page < total_pages - 1:
        next_btn = discord.ui.Button(label="Siguiente ▶", style=discord.ButtonStyle.secondary, custom_id="get_next", row=1)
        def make_next(p=page):
            async def cb(inter):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True); return
                await _show_get_select(inter, rarity, by_r, uid, db, p + 1)
            return cb
        next_btn.callback = make_next(); view.add_item(next_btn)

    back_btn = discord.ui.Button(label="◀ Rarezas", style=discord.ButtonStyle.secondary, custom_id="get_back", row=1)
    async def back_cb(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True); return
        by_r3  = _get_all_by_rarity()
        embed3 = discord.Embed(title="🥇 PASE DORADO — /get",
            description="Elige una rareza y luego selecciona la figura.", color=0xffd700)
        for r in _RARITY_ORDER:
            figs3 = by_r3[r]
            if not figs3: continue
            preview3 = " · ".join(f"{f['emoji']} {f['name']}" for _, f in figs3[:8])
            if len(figs3) > 8: preview3 += f" *(+{len(figs3)-8} más)*"
            embed3.add_field(name=f"{_RARITY_EMOJI[r]} {r.capitalize()} ({len(figs3)})", value=preview3, inline=False)
        opts3  = [discord.SelectOption(label=f"{r.capitalize()} ({len(by_r3[r])} figuras)", value=r, emoji=_RARITY_EMOJI[r])
                  for r in _RARITY_ORDER if by_r3[r]]
        sel3   = discord.ui.Select(placeholder="🥇 Elige una rareza...", options=opts3, row=0)
        async def rarity_cb3(si: discord.Interaction):
            if si.user.id != uid:
                await si.response.send_message("❌ No es tu menú.", ephemeral=True); return
            await _show_get_select(si, si.data["values"][0], by_r3, uid, db, page=0)
        sel3.callback = rarity_cb3
        view3 = discord.ui.View(timeout=180); view3.add_item(sel3)
        await inter.response.edit_message(embed=embed3, view=view3)
    back_btn.callback = back_cb
    view.add_item(back_btn)
    await interaction.response.edit_message(embed=embed, view=view)


def register_commands(bot):
    """Registra los comandos slash de este módulo. Llamar desde main.py."""

    @bot.tree.command(name="oro", description="[ADMIN] Regala monedas a un usuario")
    @app_commands.describe(usuario="Usuario al que regalar monedas", cantidad="Cantidad de monedas a regalar")
    async def oro(interaction: discord.Interaction, usuario: discord.Member, cantidad: int):
        if interaction.user.id != 1236293193893412975:
            await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
            return
        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser mayor a 0.", ephemeral=True)
            return
        db = load_db()
        target = get_user(db, usuario.id)
        if not target:
            await interaction.response.send_message(f"❌ {usuario.mention} no está registrado.", ephemeral=True)
            return
        target["coins"] = target.get("coins", 0) + cantidad
        save_db(db)
        embed = discord.Embed(title="💰 ¡LLUVIA DE ORO!", description=f"**{target['name']}** acaba de recibir una fortuna.", color=0xf1c40f)
        embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUydmF6Njd6dnd5a20xbzJsdXI1bnFsZmhkbDIwdTlvYmc5eG10MnQ1cyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bMycGOQLESDCEnLNUz/giphy.gif")
        embed.add_field(name="👤 Receptor", value=f"{target['name']} ({usuario.mention})", inline=True)
        embed.add_field(name="💰 Cantidad", value=f"+**{cantidad:,}** monedas", inline=True)
        embed.add_field(name="💳 Nuevo saldo", value=f"**{target['coins']:,}** monedas", inline=True)
        embed.set_footer(text=f"Otorgado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

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


    @bot.tree.command(name="nuke", description="[ADMIN] Resetea a un usuario a nivel 1")
    @app_commands.describe(usuario="Usuario a nukear")
    async def nuke(interaction: discord.Interaction, usuario: discord.Member):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
            return
        db = load_db()
        target = get_user(db, usuario.id)
        if not target:
            await interaction.response.send_message("❌ Usuario no registrado.", ephemeral=True)
            return
        nombre = target["name"]
        target["coins"]   = 0
        target["figures"] = []
        target["team"]    = [None, None, None]
        target["level"]   = 1
        target["xp"]      = 0
        target["wins"]    = 0
        target["losses"]  = 0
        save_db(db)
        embed = discord.Embed(
            title="☢️ NUKE ACTIVADO",
            description=f"**{nombre}** ha sido reseteado a nivel 1.\nSin monedas. Sin figuras. Sin nada.",
            color=0xff0000
        )
        embed.set_image(url="https://media.tenor.com/FwNuvPzK6IIAAAAM/nuke-it-olliesblog-olliesblog-nuke-it.gif")
        embed.set_footer(text="F en el chat 🕯️")
        await interaction.response.send_message(embed=embed)


    @bot.tree.command(name="ayuda", description="Ver todos los comandos disponibles")
    async def ayuda(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Androide del PvP — Comandos",
            description="¡Bienvenido al sistema de batallas de figuras!",
            color=0x3498db
        )
        # ── Básicos ────────────────────────────────────────────────
        embed.add_field(name="📋 Inicio",     value="`/registrar` — Créate una cuenta y recibe 1,000 monedas", inline=False)
        embed.add_field(name="👤 Perfil",     value="`/perfil [@usuario]` — Ve tus stats o los de otro jugador", inline=False)
        embed.add_field(name="🏪 Tienda",     value="`/tienda` — Compra nuevas figuras", inline=False)
        embed.add_field(name="🎭 Figuras",    value="`/misfiguras [@usuario]` — Colección de figuras con flechas\n`/verperfil @usuario` · `/verfiguras @usuario` — Ver info de otro jugador", inline=False)
        embed.add_field(name="⚡ Equipar",    value="`/equipar` — Arma tu equipo de 3 figuras (Frontal/Centro/Trasero)", inline=False)
        embed.add_field(name="🦞 Langosta",   value="`/lobster` — Obtén una langosta misteriosa", inline=False)
        # ── Batallas ───────────────────────────────────────────────
        embed.add_field(name="⚔️ Batallas",  value=(
            "`/pvpbot` — Elige un rival bot (5 niveles + 4 jefes)\n"
            "`/retar @usuario` — Reta a otro jugador 1v1\n"
            "`/multiplayer` — Batalla de 2 a 4 jugadores\n"
            "`/reset` — Cancela la batalla activa del canal"
        ), inline=False)
        # ── Economía ───────────────────────────────────────────────
        embed.add_field(name="💰 Economía",  value=(
            "`/diario` — Recompensa diaria + racha semanal\n"
            "`/work` — Trabaja con minijuegos para ganar monedas (cooldown 1h)\n"
            "`/rob @usuario` — Intenta robarle monedas (cooldown 2h)\n"
            "`/perfil` — Ve tus monedas y stats actuales"
        ), inline=False)
        # ── Cocina ─────────────────────────────────────────────────
        embed.add_field(name="🧑‍🍳 Cocina",   value=(
            "`/cook` — Cocina 🦞 Langosta + hasta 3 ingredientes para conseguir buffs\n"
            "`/ingredientes` — Ve tu despensa de ingredientes\n"
            "`/recetas` — Ver tus hojas de receta descubiertas"
        ), inline=False)
        # ── Intercambios ───────────────────────────────────────────
        embed.add_field(name="🔄 Intercambios", value=(
            "`/trade @usuario` — Propone un intercambio de oro, figuras o ingredientes"
        ), inline=False)
        # ── Exploración & Quests ───────────────────────────────────
        embed.add_field(name="🗺️ Exploración & Quests", value=(
            "`/exploracion` — Manda 3 figuras a explorar (30 min) para conseguir recompensas\n"
            "`/quest` — Activa misiones especiales (ej: desbloquear a Jane Doe)"
        ), inline=False)
        # ── Rankings ───────────────────────────────────────────────
        embed.add_field(name="🏆 Rankings",  value="`/ranking` — 4 leaderboards: Victorias · Dinero · Figuras · Niveles", inline=False)
        # ── Admin (solo matheogamer64) ─────────────────────────────
        embed.add_field(name="🔒 Solo Matheo", value=(
            "`/oro @usuario cantidad` — Regala monedas\n"
            "`/bomb @usuario cantidad` — Quita monedas\n"
            "`/nuke @usuario` — Resetea a un jugador\n"
            "`/say [mensaje]` — El bot habla"
        ), inline=False)
        embed.set_footer(text="¡Colecciona, mejora y conquista la arena! | Androide del PvP")
        await interaction.response.send_message(embed=embed)


    @bot.tree.command(name="holy", description="...")
    async def holy_cmd(interaction: discord.Interaction):
        if interaction.user.id != HOLY_USER_ID:
            await interaction.response.send_message("❌ ...", ephemeral=True)
            return

        db = load_db()
        user = get_user(db, interaction.user.id)
        if not user:
            await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
            return

        # Añadir Santa Vaca a su colección
        user["figures"].append({"key": "santa_vaca", "level": 1, "xp": 0})
        # Añadir como ingrediente también
        if "ingredients" not in user: user["ingredients"] = {}
        user["ingredients"]["🐮"] = user["ingredients"].get("🐮", 0) + 1
        # Llenar equipo si hay huecos
        team = user.get("team", [None, None, None])
        while len(team) < 3: team.append(None)
        for i in range(3):
            if team[i] is None:
                team[i] = len(user["figures"]) - 1
                break
        user["team"] = team
        save_db(db)

        embed = discord.Embed(
            title="🐮 SANTA VACA HA APARECIDO",
            description="No sabes cómo llegó hasta aquí.\nNo sabes qué quiere.\n\n**Pero ahora es tuya.**",
            color=0xffffff
        )
        embed.add_field(name="❤️ HP",     value="1,234,567,890", inline=True)
        embed.add_field(name="⚔️ ATK",    value="1,234,567,890", inline=True)
        embed.add_field(name="⚡ VEL",    value="1,234,567,890", inline=True)
        embed.add_field(name="✨ Habilidades", value=(
            "🟡 **Holy!** — Evoluciona: +10B DEF y +1M ATK por 20 turnos\n"
            "🟠 **Steak** — Cura 10T HP a todo el equipo\n"
            "🔴 **GOD WHAT IS THAT-** — Mata a todas las figuras enemigas"
        ), inline=False)
        embed.add_field(name="🧑‍🍳 Ingrediente", value="La vaca también es un ingrediente de cocina.\nCombínala con una 🦞 Langosta para algo... especial.", inline=False)
        embed.set_image(url="https://emblibrary.com/cdn/shop/files/M33422.jpg?v=1750188343&width=1214")
        embed.set_footer(text="SANTA VACA! 🐮")
        await interaction.response.send_message(embed=embed)



    @bot.tree.command(name="gift", description="Regala oro, figuras o ingredientes a otro usuario")
    @app_commands.describe(usuario="Usuario al que regalar")
    async def gift(interaction: discord.Interaction, usuario: discord.Member):
        if interaction.user.id != 1236293193893412975:
            await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
            return
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("❌ No puedes regalarte a ti mismo.", ephemeral=True)
            return
        db = load_db()
        giver = get_user(db, interaction.user.id)
        receiver = get_user(db, usuario.id)
        if not giver:
            await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
            return
        if not receiver:
            await interaction.response.send_message("❌ Ese usuario no está registrado.", ephemeral=True)
            return

        # Menú para elegir qué tipo de regalo
        embed = discord.Embed(
            title=f"🎁 Regalar a {receiver['name']}",
            description="¿Qué quieres regalar?",
            color=0x2ecc71
        )
        view = discord.ui.View(timeout=60)

        gold_btn = discord.ui.Button(label="💰 Oro", style=discord.ButtonStyle.primary, custom_id="gift_gold")
        fig_btn  = discord.ui.Button(label="🎭 Figura", style=discord.ButtonStyle.primary, custom_id="gift_fig")
        ing_btn  = discord.ui.Button(label="🧺 Ingrediente", style=discord.ButtonStyle.primary, custom_id="gift_ing")

        async def gift_gold_cb(inter: discord.Interaction):
            if inter.user.id != interaction.user.id:
                await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            # Modal para pedir cantidad
            modal = discord.ui.Modal(title="💰 Regalar Oro")
            amount_input = discord.ui.TextInput(label="¿Cuánto oro quieres regalar?", placeholder="Ej: 500", max_length=10)
            modal.add_item(amount_input)

            async def modal_submit(mi: discord.Interaction):
                try:
                    amount = int(amount_input.value.strip())
                except ValueError:
                    await mi.response.send_message("❌ Cantidad inválida.", ephemeral=True)
                    return
                if amount <= 0:
                    await mi.response.send_message("❌ La cantidad debe ser mayor a 0.", ephemeral=True)
                    return
                db2 = load_db()
                g2 = get_user(db2, interaction.user.id)
                r2 = get_user(db2, usuario.id)
                if g2.get("coins", 0) < amount:
                    await mi.response.send_message(f"❌ No tienes suficiente oro. Tienes {g2.get('coins',0):,}🪙", ephemeral=True)
                    return
                g2["coins"] = g2.get("coins", 0) - amount
                r2["coins"] = r2.get("coins", 0) + amount
                save_db(db2)
                embed2 = discord.Embed(
                    title="🎁 ¡Regalo enviado!",
                    description=f"**{g2['name']}** le regaló **{amount:,}🪙** a **{r2['name']}**!",
                    color=0xf1c40f
                )
                embed2.add_field(name="💳 Tu saldo", value=f"{g2['coins']:,}🪙", inline=True)
                await mi.response.send_message(embed=embed2)

            modal.on_submit = modal_submit
            await inter.response.send_modal(modal)

        async def gift_fig_cb(inter: discord.Interaction):
            if inter.user.id != interaction.user.id:
                await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            db2 = load_db()
            g2 = get_user(db2, interaction.user.id)
            figs = g2.get("figures", [])
            if not figs:
                await inter.response.send_message("❌ No tienes figuras que regalar.", ephemeral=True)
                return

            # Mostrar figuras únicas
            seen = {}
            for i, fd in enumerate(figs):
                k = fd["key"]
                if k not in seen:
                    seen[k] = i
            options = []
            for k, idx in list(seen.items())[:25]:
                fig = FIGURES.get(k, {})
                lvl = figs[idx].get("level", 1)
                options.append(discord.SelectOption(
                    label=f"{fig.get('name', k)} (Nv.{lvl})",
                    value=str(idx),
                    emoji=fig.get("emoji", "🎭"),
                    description=fig.get("rarity", "").upper()
                ))

            sel = discord.ui.Select(placeholder="Elige la figura a regalar...", options=options)
            async def sel_cb(si: discord.Interaction):
                if si.user.id != interaction.user.id:
                    await si.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                chosen_idx = int(sel.values[0])
                db3 = load_db()
                g3 = get_user(db3, interaction.user.id)
                r3 = get_user(db3, usuario.id)
                if chosen_idx >= len(g3.get("figures", [])):
                    await si.response.send_message("❌ Figura no encontrada.", ephemeral=True)
                    return
                fig_data = g3["figures"].pop(chosen_idx)
                # Ajustar team si apuntaba a esa figura
                team = g3.get("team", [None, None, None])
                for ti, tidx in enumerate(team):
                    if tidx == chosen_idx:
                        team[ti] = None
                    elif tidx is not None and tidx > chosen_idx:
                        team[ti] = tidx - 1
                g3["team"] = team
                if "figures" not in r3: r3["figures"] = []
                r3["figures"].append(fig_data)
                save_db(db3)
                fig = FIGURES.get(fig_data["key"], {})
                embed3 = discord.Embed(
                    title="🎁 ¡Figura regalada!",
                    description=f"**{g3['name']}** le regaló **{fig.get('emoji','')} {fig.get('name', fig_data['key'])}** a **{r3['name']}**!",
                    color=0x9b59b6
                )
                if fig.get("image"):
                    embed3.set_thumbnail(url=fig["image"])
                await si.response.edit_message(embed=embed3, view=None)

            sel.callback = sel_cb
            sv = discord.ui.View(timeout=60)
            sv.add_item(sel)
            await inter.response.edit_message(
                embed=discord.Embed(title="🎭 ¿Qué figura regalas?", color=0x9b59b6),
                view=sv
            )

        async def gift_ing_cb(inter: discord.Interaction):
            if inter.user.id != interaction.user.id:
                await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            db2 = load_db()
            g2 = get_user(db2, interaction.user.id)
            ings = {k: v for k, v in g2.get("ingredients", {}).items() if v > 0}
            if not ings:
                await inter.response.send_message("❌ No tienes ingredientes que regalar.", ephemeral=True)
                return
            options = [
                discord.SelectOption(label=f"{INGREDIENTS.get(k, k)} x{v}", value=k, emoji=k)
                for k, v in list(ings.items())[:25]
            ]
            sel = discord.ui.Select(placeholder="Elige el ingrediente...", options=options)

            async def ing_sel_cb(si: discord.Interaction):
                if si.user.id != interaction.user.id:
                    await si.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                chosen_ing = sel.values[0]
                # Modal para cantidad
                modal = discord.ui.Modal(title="🧺 ¿Cuántos regalar?")
                qty_input = discord.ui.TextInput(label=f"Tienes {ings[chosen_ing]}x {INGREDIENTS.get(chosen_ing,chosen_ing)}. ¿Cuántos?", placeholder="Ej: 1", max_length=5)
                modal.add_item(qty_input)
                async def ing_modal_submit(mi: discord.Interaction):
                    try:
                        qty = int(qty_input.value.strip())
                    except ValueError:
                        await mi.response.send_message("❌ Cantidad inválida.", ephemeral=True)
                        return
                    db3 = load_db()
                    g3 = get_user(db3, interaction.user.id)
                    r3 = get_user(db3, usuario.id)
                    available = g3.get("ingredients", {}).get(chosen_ing, 0)
                    if qty <= 0 or qty > available:
                        await mi.response.send_message(f"❌ Cantidad inválida. Tienes {available}.", ephemeral=True)
                        return
                    g3["ingredients"][chosen_ing] = available - qty
                    if "ingredients" not in r3: r3["ingredients"] = {}
                    r3["ingredients"][chosen_ing] = r3["ingredients"].get(chosen_ing, 0) + qty
                    save_db(db3)
                    ing_name = INGREDIENTS.get(chosen_ing, chosen_ing)
                    embed4 = discord.Embed(
                        title="🎁 ¡Ingrediente regalado!",
                        description=f"**{g3['name']}** le regaló **{qty}x {chosen_ing} {ing_name}** a **{r3['name']}**!",
                        color=0xe67e22
                    )
                    await mi.response.send_message(embed=embed4)
                modal.on_submit = ing_modal_submit
                await si.response.send_modal(modal)

            sel.callback = ing_sel_cb
            sv = discord.ui.View(timeout=60)
            sv.add_item(sel)
            await inter.response.edit_message(
                embed=discord.Embed(title="🧺 ¿Qué ingrediente regalas?", color=0xe67e22),
                view=sv
            )

        gold_btn.callback = gift_gold_cb
        fig_btn.callback  = gift_fig_cb
        ing_btn.callback  = gift_ing_cb
        view.add_item(gold_btn)
        view.add_item(fig_btn)
        view.add_item(ing_btn)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



    @bot.tree.command(name="get", description="[GAMER64] El pase dorado y exclusivo...")
    async def get_cmd(interaction: discord.Interaction):
        if interaction.user.id != GET_AUTHORIZED_ID:
            await interaction.response.send_message("❌ No tienes acceso a este comando.", ephemeral=True)
            return
        db   = load_db()
        user = get_user(db, interaction.user.id)
        if not user:
            await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
            return
        uid    = interaction.user.id
        by_r   = _get_all_by_rarity()

        def build_main_embed():
            embed = discord.Embed(
                title="🥇 PASE DORADO — /get",
                description="Elige una rareza y luego selecciona la figura del menú desplegable.",
                color=0xffd700
            )
            for r in _RARITY_ORDER:
                figs = by_r[r]
                if not figs:
                    continue
                preview = " · ".join(f"{f['emoji']} {f['name']}" for _, f in figs[:8])
                if len(figs) > 8:
                    preview += f" *(+{len(figs)-8} más)*"
                embed.add_field(
                    name=f"{_RARITY_EMOJI[r]} {r.capitalize()} ({len(figs)})",
                    value=preview, inline=False
                )
            return embed

        def build_main_view():
            view = discord.ui.View(timeout=180)
            options = []
            for r in _RARITY_ORDER:
                if not by_r[r]:
                    continue
                options.append(discord.SelectOption(
                    label=f"{r.capitalize()} ({len(by_r[r])} figuras)",
                    value=r,
                    description=f"{_RARITY_EMOJI[r]} Elige una figura de rareza {r}",
                    emoji=_RARITY_EMOJI[r],
                ))
            select = discord.ui.Select(
                placeholder="🥇 Elige una rareza...",
                options=options,
                custom_id="get_rarity_select",
                row=0,
            )
            async def rarity_select_cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                chosen_rarity = inter.data["values"][0]
                await _show_get_select(inter, chosen_rarity, by_r, uid, db, page=0, user=user)
            select.callback = rarity_select_cb
            view.add_item(select)
            return view

        await interaction.response.send_message(
            embed=build_main_embed(), view=build_main_view(), ephemeral=True
        )

