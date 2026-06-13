"""
commands_admin.py — Comandos de administrador y misceláneos (/oro, /bomb, /nuke, /gift, /say, /holy, /get, /ayuda).
"""
import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import FIGURES, SECRET_FIGURES, SECRET_OWNER_ID, secret_store_unlocked
from economy import INGREDIENTS, ACHIEVEMENTS, grant_achievement

ADMIN_ID = 1236293193893412975

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

# --- RESET (cualquier usuario, solo afecta su canal) ---
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

# --- ROB ---
ROB_COOLDOWN = {}  # {user_id: timestamp}

@bot.tree.command(name="rob", description="Intenta robarle monedas a otro usuario")
@app_commands.describe(usuario="Usuario al que intentar robar")
async def rob(interaction: discord.Interaction, usuario: discord.Member):
    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes robarte a ti mismo.", ephemeral=True)
        return

    now = datetime.now(timezone.utc).timestamp()
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


# --- LOBSTER ---
@bot.tree.command(name="lobster", description="🦞 Obtén una langosta misteriosa")
async def lobster_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
@bot.tree.command(name="say", description="[GAMER] Con este comando, puedes hacer que el bot diga lo que quieras")
@app_commands.describe(mensaje="Lo que dirá el bot")
async def say(interaction: discord.Interaction, mensaje: str):
    if interaction.user.id != GAMER_ID:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
        return
    # Borrar la interacción silenciosamente y enviar el mensaje como el bot
    await interaction.response.send_message("✅ Enviado.", ephemeral=True)
    await interaction.channel.send(mensaje)


# --- HOLY (solo usuario especial — NO aparece en /ayuda) ---
HOLY_USER_ID = 1236293193893412975

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


# ============================================================
#  COMANDOS /gift y /trade
# ============================================================

# --- GIFT ---
@bot.tree.command(name="gift", description="Regala oro, figuras o ingredientes a otro usuario")
@app_commands.describe(usuario="Usuario al que regalar")
async def gift(interaction: discord.Interaction, usuario: discord.Member):
    if interaction.user.id != 1236293193893412975:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
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


# --- TRADE ---
pending_trades = {}  # {receiver_id: trade_data}

@bot.tree.command(name="trade", description="Propone un intercambio de oro, figuras o ingredientes")
@app_commands.describe(usuario="Usuario con quien hacer el trade")
async def trade(interaction: discord.Interaction, usuario: discord.Member):
    if usuario.id == interaction.user.id:
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

async def _give_figure(inter: discord.Interaction, fig_key: str, uid: int, db):
    """Entrega la figura al usuario y confirma."""
    db2 = load_db()
    u2  = get_user(db2, inter.user.id)
    u2.setdefault("figures",[]).append({"key": fig_key, "level":1, "xp":0})
    team = u2.get("team",[None,None,None])
    while len(team) < 3:
        team.append(None)
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
