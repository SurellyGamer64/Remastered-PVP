import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import asyncio
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file
import threading
import time

app = Flask('')

# Clave secreta para el backup — cambiala en Render como variable de entorno BACKUP_KEY

@app.route('/')
def home(): return "Bot Online"

@app.route('/backup')
def backup_db():
    key = request.args.get("key", "")
    if key != BACKUP_KEY:
        return "Clave incorrecta.", 403
    _db_file = "/etc/secrets/db.json" if os.path.exists("/etc/secrets/db.json") else "db.json"
    if os.path.exists(_db_file):
        return send_file(_db_file, mimetype="application/json", as_attachment=True, download_name="db.json")
    import json as _j2
    return _j2.dumps({"users": {}}), 200, {'Content-Type': 'application/json'}

@app.route('/upload_db', methods=['POST'])
def upload_db():
    key = request.args.get("key", "")
    if key != BACKUP_KEY:
        return "Clave incorrecta.", 403
    import json as _j2
    data = request.get_json(force=True)
    if not data:
        return "Sin datos.", 400
    _db_file = "/etc/secrets/db.json" if os.path.exists("/etc/secrets") else "db.json"
    with open(_db_file, "w", encoding="utf-8") as f:
        _j2.dump(data, f, indent=2, ensure_ascii=False)
    return "Database restaurada correctamente.", 200

def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run).start()


# ============================================================
#  HOOK EN FINISH_BATTLE PARA QUEST Y LEVEL UP DE FIGURAS

# --- SAY (solo matheogamer64) ---
GAMER_ID = 1236293193893412975

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

def _check_player_levelup(user_data: dict) -> list[int]:
    """Sube el nivel del jugador. Por cada nivel nuevo da 1 skill point."""
    new_levels = []
    while user_data.get("level", 1) < PLAYER_LEVEL_MAX:
        needed = xp_to_level_up(user_data.get("level", 1))
        if user_data.get("xp", 0) >= needed:
            user_data["xp"] -= needed
            user_data["level"] = user_data.get("level", 1) + 1
            user_data["skill_points"] = user_data.get("skill_points", 0) + 1
            new_levels.append(user_data["level"])
        else:
            break
    return new_levels

# ============================================================
#  ÁRBOL DE APRENDIZAJE (SKILL POINTS)
# ============================================================
# Estructura: id -> {name, desc, max_level, cost_per_level, rama, requires, effect_key, effect_per_level}
# effect aplicado en tiempo de ejecución según effect_key
LEARN_TREE = {
    # ── RAMA ORO ─────────────────────────────────────────────
    "gold_1": {
        "name": "💰 Buscador de Oro I",
        "desc": "Ganas +15% más monedas en batallas y recompensas diarias.",
        "rama": "💰 Oro",
        "max_level": 3,
        "cost": 1,          # SP por nivel
        "requires": None,
        "effect_key": "gold_bonus_pct",
        "effect_per_level": 15,
    },
    "gold_2": {
        "name": "💰 Mercader II",
        "desc": "Descuento del 10% en la tienda por nivel.",
        "rama": "💰 Oro",
        "max_level": 3,
        "cost": 2,
        "requires": "gold_1",   # necesitas gold_1 al máximo
        "effect_key": "shop_discount_pct",
        "effect_per_level": 10,
    },
    "gold_3": {
        "name": "💰 Magnate III",
        "desc": "Ganas +1 moneda extra por cada punto de daño que haces en batalla.",
        "rama": "💰 Oro",
        "max_level": 2,
        "cost": 3,
        "requires": "gold_2",
        "effect_key": "dmg_to_coins",
        "effect_per_level": 1,
    },
    # ── RAMA XP ──────────────────────────────────────────────
    "xp_1": {
        "name": "📚 Estudiante I",
        "desc": "+20% XP ganada en todas las acciones.",
        "rama": "📚 Experiencia",
        "max_level": 3,
        "cost": 1,
        "requires": None,
        "effect_key": "xp_bonus_pct",
        "effect_per_level": 20,
    },
    "xp_2": {
        "name": "📚 Erudito II",
        "desc": "Tus figuras también ganan +20% XP en batallas y exploraciones.",
        "rama": "📚 Experiencia",
        "max_level": 3,
        "cost": 2,
        "requires": "xp_1",
        "effect_key": "fig_xp_bonus_pct",
        "effect_per_level": 20,
    },
    "xp_3": {
        "name": "📚 Maestro III",
        "desc": "El tiempo de exploración se reduce un 20% por nivel.",
        "rama": "📚 Experiencia",
        "max_level": 2,
        "cost": 3,
        "requires": "xp_2",
        "effect_key": "explore_time_reduction_pct",
        "effect_per_level": 20,
    },
    # ── RAMA EXPLORACIÓN ─────────────────────────────────────
    "explore_1": {
        "name": "🗺️ Explorador I",
        "desc": "+1 objeto garantizado por exploración.",
        "rama": "🗺️ Exploración",
        "max_level": 3,
        "cost": 1,
        "requires": None,
        "effect_key": "explore_bonus_items",
        "effect_per_level": 1,
    },
    "explore_2": {
        "name": "🗺️ Rastreador II",
        "desc": "+15% de probabilidad de conseguir figuras en exploraciones.",
        "rama": "🗺️ Exploración",
        "max_level": 2,
        "cost": 2,
        "requires": "explore_1",
        "effect_key": "explore_fig_chance_bonus",
        "effect_per_level": 15,
    },
    "explore_3": {
        "name": "🗺️ Leyenda III",
        "desc": "Posibilidad de encontrar figuras épicas/legendarias en exploración.",
        "rama": "🗺️ Exploración",
        "max_level": 1,
        "cost": 4,
        "requires": "explore_2",
        "effect_key": "explore_rare_unlock",
        "effect_per_level": 1,
    },
    # ── RAMA COCINA ──────────────────────────────────────────
    "cook_1": {
        "name": "🧑‍🍳 Aprendiz de Cocina I",
        "desc": "+1 ingrediente de regalo al cocinar por nivel.",
        "rama": "🧑‍🍳 Cocina",
        "max_level": 2,
        "cost": 1,
        "requires": None,
        "effect_key": "cook_bonus_ingredient",
        "effect_per_level": 1,
    },
    "cook_2": {
        "name": "🧑‍🍳 Chef II",
        "desc": "50% de no consumir ingredientes al fallar una receta.",
        "rama": "🧑‍🍳 Cocina",
        "max_level": 1,
        "cost": 3,
        "requires": "cook_1",
        "effect_key": "cook_fail_save",
        "effect_per_level": 1,
    },
}

def get_learn_effect(user_data: dict, effect_key: str) -> int:
    """Devuelve el valor total de un efecto del árbol para un usuario."""
    tree = user_data.get("learn_tree", {})
    total = 0
    for nid, node in LEARN_TREE.items():
        if node["effect_key"] == effect_key:
            lvl = tree.get(nid, 0)
            total += lvl * node["effect_per_level"]
    return total

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
            async def make_cb(node_id=nid, node_data=node):
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
# ============================================================
REBIRTH_BASE_COST = 40_000
REBIRTH_COST_INC  = 20_000

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

        async def make_combine_cb(fig_key=k):
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

SHOPS = {
    "gamer": {
        "name": "🎮 La Tienda Gamer",
        "desc": "La tienda clásica. Figuras de todas las rarezas, buena variedad.",
        "weights": {"común":35,"raro":40,"épico":20,"legendario":5,"mítico":0},
        "slots": 5,
    },
    "bar": {
        "name": "🍺 El Bar Random",
        "desc": "Todo es un misterio. Cualquier figura puede aparecer aquí.",
        "weights": {"común":30,"raro":35,"épico":25,"legendario":10,"mítico":0},
        "slots": 5,
        "refresh_on_visit": True,  # siempre figuras distintas
    },
    "mercado": {
        "name": "🛒 Super Mercado",
        "desc": "Precios accesibles, figuras básicas. Sin legendarios ni míticos.",
        "weights": {"común":40,"raro":45,"épico":15,"legendario":0,"mítico":0},
        "slots": 6,
        "discount": 10,  # 10% de descuento
    },
    "toad": {
        "name": "🍄 Tienda Toad",
        "desc": "Stock exclusivo de figuras épicas y legendarias. ¡Raras de encontrar!",
        "weights": {"común":0,"raro":15,"épico":55,"legendario":30,"mítico":0},
        "slots": 4,
    },
    "tails": {
        "name": "🔬 Laboratorio de Tails",
        "desc": "Figuras técnicas y poco comunes. Sin comunes, mayor calidad.",
        "weights": {"común":0,"raro":35,"épico":45,"legendario":20,"mítico":0},
        "slots": 4,
    },
    "acertijo": {
        "name": "❓ El Acertijo de las Compras",
        "desc": "¡Cualquier cosa puede pasar! Posibilidad de figuras míticas y sobres misteriosos.",
        "weights": {"común":20,"raro":35,"épico":30,"legendario":15,"mítico":0},
        "has_packs": True,
        "slots": 4,
    },
}

# Probabilidad de mítico (separada porque es especial)
SHOP_MYTHIC_CHANCE = {
    "gamer": 0, "bar": 0, "mercado": 0, "toad": 0,
    "tails": 0, "acertijo": 3,  # 3% de que aparezca una mítica en acertijo
}

MYSTERY_PACKS = {
    "basic":   {"name": "📦 Sobre Básico",     "price": 300,  "desc": "1 figura común/raro"},
    "premium": {"name": "📫 Sobre Premium",     "price": 800,  "desc": "1 figura raro/épico + 15% ingrediente"},
    "legend":  {"name": "🌟 Sobre Legendario",  "price": 2000, "desc": "1 figura épico/legendario + 25% ingrediente + 10% receta"},
    "mythic":  {"name": "💀 Sobre Mítico",      "price": 5000, "desc": "1 figura legendario/mítico + 50% ingrediente + 20% receta"},
}

def _pick_shop_figures(shop_id: str, count: int) -> list[str]:
    """Elige `count` figuras para mostrar en una tienda según sus pesos de rareza."""
    shop = SHOPS[shop_id]
    w    = shop["weights"]
    pool = []
    mythic_chance = SHOP_MYTHIC_CHANCE.get(shop_id, 0)

    # Construir pool ponderado
    rarity_map = {
        "común": ["común"], "raro": ["raro"],
        "épico": ["épico", "epico"], "legendario": ["legendario", "Legendario"],
        "mítico": ["mítico", "Mítico"],
    }
    for rarity, weight in w.items():
        if weight > 0:
            aliases = rarity_map.get(rarity, [rarity])
            figs = [k for k, v in FIGURES.items()
                    if v.get("rarity","").lower() in [a.lower() for a in aliases]
                    and v.get("price", 0) > 0
                    and k not in SECRET_FIGURES and k != "roblox_boss"]
            pool.extend(figs * weight)

    if not pool:
        return []

    chosen = []
    seen   = set()
    attempts = 0
    while len(chosen) < count and attempts < 200:
        attempts += 1
        # Intentar mítico con su chance separada
        if mythic_chance > 0 and random.randint(1, 100) <= mythic_chance:
            mythic_pool = [k for k, v in FIGURES.items()
                           if v.get("rarity","").lower() in ("mítico",)
                           and k not in SECRET_FIGURES and v.get("price",0) > 0]
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

def _open_mystery_pack(pack_id: str, user_data: dict, db) -> dict:
    """Abre un sobre misterioso y devuelve el resultado."""
    rarity_pools = {
        "basic":   ["común", "raro"],
        "premium": ["raro", "épico", "epico"],
        "legend":  ["épico", "epico", "legendario"],
        "mythic":  ["legendario", "mítico"],
    }
    ing_chances  = {"basic": 0,  "premium": 15, "legend": 25, "mythic": 50}
    rec_chances  = {"basic": 0,  "premium": 0,  "legend": 10, "mythic": 20}

    pool = [k for k, v in FIGURES.items()
            if v.get("rarity","").lower() in rarity_pools[pack_id]
            and k not in SECRET_FIGURES and k != "roblox_boss" and v.get("price",0) > 0]
    if not pool:
        return {"fig": None, "ingredient": None, "recipe": None}

    fig_key = random.choice(pool)
    user_data.setdefault("figures", []).append({"key": fig_key, "level": 1, "xp": 0})

    ingredient = None
    if random.randint(1,100) <= ing_chances[pack_id]:
        ingredient = give_battle_ingredient(user_data)

    recipe = None
    if random.randint(1,100) <= rec_chances[pack_id]:
        all_recipes = list(range(len(RECIPES))) if 'RECIPES' in globals() else []
        owned = user_data.get("recipe_sheets", [])
        available_rec = [r for r in all_recipes if r not in owned]
        if available_rec:
            idx = random.choice(available_rec)
            user_data.setdefault("recipe_sheets", []).append(idx)
            recipe = RECIPES[idx]["name"] if idx < len(RECIPES) else None

    return {"fig": fig_key, "ingredient": ingredient, "recipe": recipe}

@bot.tree.command(name="tienda", description="Elige entre 6 tiendas y compra figuras")
async def tienda(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    uid = interaction.user.id

    # ── Menú de selección de tienda ──────────────────────────
    embed = discord.Embed(
        title="🏪 ¿Qué tienda quieres visitar?",
        description="Cada tienda tiene su propio stock y probabilidades de rareza.",
        color=0xf39c12
    )
    for sid, shop in SHOPS.items():
        w   = shop["weights"]
        active_rarezas = [f"{r} {p}%" for r, p in w.items() if p > 0]
        mythic_c = SHOP_MYTHIC_CHANCE.get(sid, 0)
        if mythic_c > 0:
            active_rarezas.append(f"mítico {mythic_c}%")
        embed.add_field(
            name=shop["name"],
            value=f"{shop['desc']}\n`{' · '.join(active_rarezas)}`",
            inline=False
        )

    view = discord.ui.View(timeout=120)
    for sid, shop in SHOPS.items():
        btn = discord.ui.Button(label=shop["name"], style=discord.ButtonStyle.primary, custom_id=f"shop_{sid}")
        async def make_shop_cb(shop_id=sid):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                await _show_shop(inter, shop_id, db, user, uid, edit=True)
            return cb
        btn.callback = make_shop_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def _show_shop(interaction: discord.Interaction, shop_id: str, db, user, uid: int, edit=False):
    shop     = SHOPS[shop_id]
    discount = shop.get("discount", 0)
    # Descuento del árbol de learn
    learn_disc = get_learn_effect(user, "shop_discount_pct")
    total_disc = discount + learn_disc

    fig_keys = _pick_shop_figures(shop_id, shop["slots"])
    figs     = [(k, FIGURES[k]) for k in fig_keys]

    embed = discord.Embed(
        title=shop["name"],
        description=shop["desc"] + (f"\n💸 Descuento activo: **{total_disc}%**" if total_disc > 0 else ""),
        color=0xf39c12
    )
    embed.add_field(name="💰 Tu oro", value=f"**{user.get('coins',0):,}🪙**", inline=True)

    rarity_star = {"común":"⚪","raro":"🔵","épico":"🟣","legendario":"🌟","mítico":"🔱","Mítico":"🔱","Legendario":"🌟"}
    for k, fig in figs:
        base_price = fig.get("price", 0)
        price = max(1, int(base_price * (1 - total_disc/100))) if total_disc > 0 else base_price
        star  = rarity_star.get(fig.get("rarity",""), "⚪")
        embed.add_field(
            name=f"{fig['emoji']} {fig['name']} — {price:,}🪙 {star}",
            value=(f"❤️ {fig['hp']} ⚔️ {fig['attack']} 🛡️ {fig['defense']} ⚡ {fig['speed']}\n"
                   f"Rareza: **{fig['rarity'].upper()}**"),
            inline=False
        )

    view = discord.ui.View(timeout=120)
    # Botones de compra
    for k, fig in figs:
        base_price = fig.get("price", 0)
        price = max(1, int(base_price * (1 - total_disc/100))) if total_disc > 0 else base_price
        async def make_buy(fig_key=k, fig_price=price):
            async def buy_cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                db2  = load_db()
                u2   = get_user(db2, inter.user.id)
                if u2.get("coins",0) < fig_price:
                    await inter.response.send_message(f"❌ Necesitas **{fig_price:,}🪙** y tienes **{u2.get('coins',0):,}🪙**.", ephemeral=True)
                    return
                u2["coins"] -= fig_price
                u2.setdefault("figures",[]).append({"key": fig_key, "level":1, "xp":0})
                # Auto-equipar si hay hueco
                team = u2.get("team",[None,None,None])
                while len(team) < 3: team.append(None)
                for i in range(3):
                    if team[i] is None:
                        team[i] = len(u2["figures"]) - 1
                        break
                u2["team"] = team
                save_db(db2)
                fig2 = FIGURES[fig_key]
                ok   = discord.Embed(title=f"✅ ¡{fig2['name']} comprada!", color=0x2ecc71)
                ok.add_field(name="💳 Saldo", value=f"**{u2['coins']:,}🪙**")
                if fig2.get("image"): ok.set_thumbnail(url=fig2["image"])
                await inter.response.send_message(embed=ok, ephemeral=True)
            return buy_cb
        btn = discord.ui.Button(label=f"Comprar {fig['name']}", style=discord.ButtonStyle.success, custom_id=f"buy_{k}")
        btn.callback = make_buy()
        view.add_item(btn)

    # Sobres del Acertijo
    if shop.get("has_packs"):
        for pack_id, pack in MYSTERY_PACKS.items():
            async def make_pack_cb(pid=pack_id, pdata=pack):
                async def pack_cb(inter: discord.Interaction):
                    if inter.user.id != uid:
                        await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                        return
                    db2 = load_db()
                    u2  = get_user(db2, inter.user.id)
                    if u2.get("coins",0) < pdata["price"]:
                        await inter.response.send_message(f"❌ Necesitas **{pdata['price']:,}🪙**.", ephemeral=True)
                        return
                    u2["coins"] -= pdata["price"]
                    result = _open_mystery_pack(pid, u2, db2)
                    save_db(db2)
                    fig2 = FIGURES.get(result["fig"],{}) if result["fig"] else {}
                    ok   = discord.Embed(
                        title=f"📦 {pdata['name']} abierto!",
                        description=f"🎭 Figura: **{fig2.get('name','?')}** {fig2.get('emoji','')}",
                        color=0x9b59b6
                    )
                    if result["ingredient"]:
                        ok.add_field(name="🧺 Ingrediente", value=str(result["ingredient"]), inline=True)
                    if result["recipe"]:
                        ok.add_field(name="📜 Receta", value=str(result["recipe"]), inline=True)
                    ok.add_field(name="💳 Saldo", value=f"**{u2['coins']:,}🪙**", inline=True)
                    await inter.response.send_message(embed=ok, ephemeral=True)
                return pack_cb
            pbtn = discord.ui.Button(
                label=f"{pack['name']} ({pack['price']:,}🪙)",
                style=discord.ButtonStyle.danger,
                custom_id=f"pack_{pack_id}"
            )
            pbtn.callback = make_pack_cb()
            view.add_item(pbtn)

    # Botón de volver
    back_btn = discord.ui.Button(label="◀ Cambiar tienda", style=discord.ButtonStyle.secondary, custom_id="back_shop")
    async def back_cb(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
            return
        await tienda.callback(inter)
    back_btn.callback = back_cb
    view.add_item(back_btn)

    if edit:
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ============================================================
#  SISTEMA DE LOGROS
# ============================================================
ACHIEVEMENTS = {
    # Progresión básica
    "first_figure":     {"name":"🎭 Primera Figura",          "desc":"Compra tu primera figura.",                        "secret":False},
    "first_win":        {"name":"🏆 Primera Victoria",         "desc":"Gana tu primera batalla.",                         "secret":False},
    "wins_10":          {"name":"⚔️ Guerrero",                 "desc":"Gana 10 batallas.",                                "secret":False},
    "wins_100":         {"name":"💀 Leyenda del PvP",          "desc":"Gana 100 batallas.",                               "secret":False},
    "first_level":      {"name":"⬆️ ¡Subí de nivel!",          "desc":"Sube de nivel por primera vez (tú como jugador).", "secret":False},
    "fig_first_level":  {"name":"⬆️ Mi figura creció",         "desc":"Sube de nivel una figura por primera vez.",        "secret":False},
    "first_recipe":     {"name":"🧑‍🍳 Chef Novato",             "desc":"Descubre tu primera receta.",                      "secret":False},
    "recipes_10":       {"name":"🧑‍🍳 Chef Profesional",        "desc":"Descubre 10 recetas.",                             "secret":False},
    "first_explore":    {"name":"🗺️ Explorador Nato",          "desc":"Completa tu primera exploración.",                  "secret":False},
    "reach_level_10":   {"name":"🌟 Nivel 10",                 "desc":"Llega al nivel 10 como jugador.",                  "secret":False},
    "reach_level_30":   {"name":"🌟 Nivel 30",                 "desc":"Llega al nivel 30 como jugador.",                  "secret":False},
    "reach_level_50":   {"name":"🌟 Nivel 50",                 "desc":"Llega al nivel 50 como jugador.",                  "secret":False},
    "reach_level_100":  {"name":"👑 Nivel 100",                "desc":"Alcanza el nivel máximo como jugador.",             "secret":False},
    "first_rebirth":    {"name":"🔄 Renacido",                 "desc":"Haz tu primer Rebirth.",                           "secret":False},
    "first_combine":    {"name":"🔀 Fusionista",               "desc":"Combina figuras por primera vez.",                  "secret":False},
    "first_learn":      {"name":"📚 Primer Conocimiento",      "desc":"Aprende tu primer nodo del árbol.",                "secret":False},
    "mythic_owned":     {"name":"🔱 Coleccionista Mítico",     "desc":"Consigue una figura de rareza mítica.",            "secret":False},
    "secret_store":     {"name":"🔒 El Código Correcto",       "desc":"Desbloquea la tienda secreta.",                    "secret":True},
    # Boss fights
    "beat_nino":        {"name":"👦 Niños al recreo",          "desc":"Derrota al Niño Random.",                          "secret":False},
    "beat_paper":       {"name":"📄 Papel, Mármol, Tijeras",   "desc":"Derrota a Paper Mario.",                           "secret":False},
    "beat_steve":       {"name":"⛏️ Minero Retirado",          "desc":"Derrota a Steve.",                                 "secret":False},
    "beat_impostor_3":  {"name":"🔪 DEFEAT (3 figuras)",       "desc":"Vence al Impostor Negro con solo 3 figuras.",      "secret":False},
    "beat_impostor_7":  {"name":"🔪 Hazlo con desventaja",     "desc":"Vence al Impostor Negro usando las 7 figuras.",    "secret":True},
    "beat_antifas":     {"name":"💀 Jefe Supremo Derrotado",   "desc":"Derrota al Antifas Antifasado.",                   "secret":False},
    # Misceláneos
    "daily_streak_7":   {"name":"📅 Racha de 7 días",          "desc":"Mantén una racha diaria de 7 días seguidos.",      "secret":False},
    "coins_10000":      {"name":"💰 Rico Rico",                 "desc":"Acumula 10,000 monedas a la vez.",                 "secret":False},
    "fig_max_level":    {"name":"⬆️ Al Límite",                "desc":"Sube una figura al nivel máximo (30).",            "secret":False},
}

def grant_achievement(user_data: dict, achievement_id: str) -> bool:
    """Da un logro al usuario si no lo tiene ya. Devuelve True si es nuevo."""
    if achievement_id not in ACHIEVEMENTS:
        return False
    earned = user_data.setdefault("achievements", [])
    if achievement_id in earned:
        return False
    earned.append(achievement_id)
    return True

def check_achievements(user_data: dict, context: dict) -> list[str]:
    """
    Verifica logros basados en el estado del usuario y el contexto de la acción.
    context puede tener: action, wins, level, recipe_count, fig_level, coins, boss_id, team_size
    Devuelve lista de IDs de logros nuevos conseguidos.
    """
    new = []
    w   = user_data.get("wins", 0)
    lvl = user_data.get("level", 1)
    rc  = user_data.get("recipe_count", 0)
    figs = user_data.get("figures", [])
    coins = user_data.get("coins", 0)
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
        "mythic_owned":    any(FIGURES.get(f["key"],{}).get("rarity","").lower() in ("mítico","Mítico") for f in figs),
        "fig_max_level":   any(f.get("level",1) >= FIGURE_LEVEL_MAX for f in figs),
        "fig_first_level": any(f.get("level",1) >= 2 for f in figs),
    }
    # Basados en acción específica
    if action == "explore":       checks["first_explore"] = True
    if action == "combine":       checks["first_combine"] = True
    if action == "learn":         checks["first_learn"]   = True
    if action == "secret_store":  checks["secret_store"]  = True
    if action == "daily_7":       checks["daily_streak_7"]= True

    boss = context.get("boss_id", "")
    ts   = context.get("team_size", 3)
    if boss == "nino_random":    checks["beat_nino"]  = True
    if boss == "paper_mario":    checks["beat_paper"] = True
    if boss == "steve":          checks["beat_steve"] = True
    if boss == "jefe":           checks["beat_antifas"] = True
    if boss == "impostor_negro":
        if ts <= 3:              checks["beat_impostor_3"] = True
        if ts >= 7:              checks["beat_impostor_7"] = True

    for aid, cond in checks.items():
        if cond and grant_achievement(user_data, aid):
            new.append(aid)
    return new

@bot.tree.command(name="logros", description="Ver tus logros conseguidos y los que faltan")
async def logros_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    earned  = set(user.get("achievements", []))
    total   = len(ACHIEVEMENTS)
    done    = len(earned)

    embed = discord.Embed(
        title=f"🏅 Logros — {user['name']}",
        description=f"**{done}/{total}** conseguidos",
        color=0xf1c40f
    )

    # Agrupar: conseguidos primero, luego pendientes (secretos ocultos)
    for aid, ach in ACHIEVEMENTS.items():
        if aid in earned:
            embed.add_field(
                name=f"✅ {ach['name']}",
                value=ach["desc"],
                inline=True
            )

    pending = [(aid, ach) for aid, ach in ACHIEVEMENTS.items() if aid not in earned]
    for aid, ach in pending:
        if ach.get("secret"):
            embed.add_field(name="🔒 ???", value="*Logro secreto*", inline=True)
        else:
            embed.add_field(name=f"⬜ {ach['name']}", value=ach["desc"], inline=True)

    embed.set_footer(text=f"Completa acciones en el bot para desbloquear logros.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ── RECOMPENSAS VARIABLES DEL IMPOSTOR NEGRO (7v3) ──────────────────────────
IMPOSTOR_REWARDS = {
    3: {"coins": 4000, "recipe_sheets": 2, "auto_levels": 2,  "xp": 600,  "achievement": True},
    4: {"coins": 2500, "recipe_sheets": 1, "auto_levels": 1,  "xp": 450,  "achievement": False},
    5: {"coins": 1500, "recipe_sheets": 0, "auto_levels": 0,  "xp": 300,  "achievement": False},
    6: {"coins": 500,  "recipe_sheets": 0, "auto_levels": 0,  "xp": 100,  "achievement": False},
    7: {"coins": 0,    "recipe_sheets": 0, "auto_levels": 0,  "xp": 0,    "achievement": False},
}

async def _start_impostor_7v3(interaction: discord.Interaction, bot_data: dict, user_figs: list, user_data: dict, db):
    """Muestra el menú de selección de figuras para la batalla 7v3 del Impostor Negro."""
    uid = interaction.user.id

    embed = discord.Embed(
        title="🔪 DEFEAT — El Impostor Negro",
        description=(
            "**7 impostores** te esperan. Tú puedes llevar entre **3 y 7 figuras**.\n\n"
            "⚠️ Cuantas más figuras uses, **peores recompensas** recibirás:\n"
            "```\n"
            "3 figuras → 4,000🪙 + 2 niveles auto + 2 recetas + LOGRO\n"
            "4 figuras → 2,500🪙 + 1 nivel auto + 1 receta\n"
            "5 figuras → 1,500🪙\n"
            "6 figuras → 500🪙\n"
            "7 figuras → Sin recompensa 💀\n"
            "```\n"
            "Elige cuántas figuras quieres usar:"
        ),
        color=0x2c2f33
    )

    view = discord.ui.View(timeout=60)
    for count in range(3, 8):
        r = IMPOSTOR_REWARDS[count]
        lbl = f"{count} figuras"
        if count == 3: lbl += " 👑"
        if count == 7: lbl += " 💀"
        btn = discord.ui.Button(
            label=lbl,
            style=discord.ButtonStyle.danger if count <= 3 else (discord.ButtonStyle.primary if count <= 5 else discord.ButtonStyle.secondary),
            custom_id=f"impostor_team_{count}"
        )
        async def make_cb(team_size=count):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                # Seleccionar figuras del usuario (las primeras N del equipo + relleno)
                chosen_figs = []
                team_indices = user_data.get("team", [None, None, None])
                figs_list    = user_data.get("figures", [])
                # Primero las del equipo activo
                for idx in team_indices:
                    if idx is not None and idx < len(figs_list) and len(chosen_figs) < team_size:
                        chosen_figs.append(figs_list[idx])
                # Rellenar con otras figuras si el jugador quiere más de 3
                if team_size > 3:
                    team_set = set(id(f) for f in chosen_figs)
                    for f in figs_list:
                        if len(chosen_figs) >= team_size:
                            break
                        if id(f) not in team_set:
                            chosen_figs.append(f)
                            team_set.add(id(f))

                # Iniciar la batalla con equipo especial
                await _launch_7v3_battle(inter, bot_data, chosen_figs, user_data, db, team_size)
            return cb
        btn.callback = make_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def _launch_7v3_battle(interaction, bot_data, player_figs, user_data, db, team_size):
    """Lanza la batalla 7v3 con el equipo elegido."""
    channel_id = interaction.channel_id
    if channel_id in active_battles:
        await interaction.response.send_message("❌ Ya hay una batalla activa en este canal.", ephemeral=True)
        return

    p1_team = []
    for fd in player_figs[:team_size]:
        try:
            p1_team.append(make_fighter(fd["key"], fd))
        except Exception:
            pass

    p2_team = []
    for bk in bot_data["team"]:
        if bk in FIGURES:
            fd_bot = {"level": bot_data.get("level", 1), "xp": 0, "stat_ups": {}}
            p2_team.append(make_fighter(
                bk, fd_bot,
                hp_mult=bot_data.get("hp_mult", 1.0),
                atk_mult=bot_data.get("atk_mult", 1.0),
                energy_bonus=bot_data.get("energy_bonus", 0)
            ))

    battle = BattleState(
        p1=interaction.user.id, p2=0,
        p1_team=p1_team, p2_team=p2_team,
        p1_name=user_data.get("name","Jugador"), p2_name=bot_data["name"],
        is_bot=True
    )
    battle.p1_team_keys = [fd["key"] for fd in player_figs[:team_size]]
    battle.impostor_7v3 = True
    battle.impostor_team_size = team_size

    active_battles[channel_id] = battle

    embed = battle.get_embed(title=f"🔪 DEFEAT — {bot_data['name']}")
    embed.set_footer(text=f"Usas {team_size} figuras · Recompensa: {IMPOSTOR_REWARDS[team_size]['coins']:,}🪙")
    view  = get_battle_view(battle, channel_id)
    await interaction.response.edit_message(embed=embed, view=view)

# ============================================================
#  /secret-store — Tienda secreta (no aparece en /ayuda)
# ============================================================
@bot.tree.command(name="secret-store", description="???")
@app_commands.describe(codigo="Código de acceso (si no lo sabes, buena suerte)")
async def secret_store(interaction: discord.Interaction, codigo: str = ""):
    uid = interaction.user.id

    # Verificar acceso
    if uid not in secret_store_unlocked:
        if codigo == SECRET_CODE:
            secret_store_unlocked.add(uid)
        else:
            await interaction.response.send_message(
                "🔒 Acceso denegado. Necesitas el código correcto.",
                ephemeral=True
            )
            return

    # Construir embed de la tienda secreta
    embed = discord.Embed(
        title="🔱 TIENDA SECRETA",
        description=(
            "Bienvenido a la tienda que no debería existir.\n"
            "Aquí encontrarás las figuras más **OP** del juego.\n"
            "⚠️ *Información clasificada. No compartas este lugar.*"
        ),
        color=0xff00ff
    )

    for key in SECRET_FIGURES:
        fig = FIGURES.get(key)
        if not fig:
            continue
        rarity_star = RARITY_STARS.get(fig["rarity"].lower(), "🔱")
        embed.add_field(
            name=f"{fig['emoji']} {fig['name']} — {fig['price']:,}🪙",
            value=(
                f"{rarity_star} **{fig['rarity'].upper()}**\n"
                f"❤️ Vida: `{fig['hp']}` ⚔️ Ataque: `{fig['attack']}`\n"
                f"🛡️ Defensa: `{fig['defense']}` ⚡ Velocidad: `{fig['speed']}`"
            ),
            inline=False
        )

    embed.set_footer(text="Usa los botones de abajo para comprar. ¡Que no se entere nadie!")

    # Botones de compra
    view = discord.ui.View(timeout=120)
    for key in SECRET_FIGURES:
        fig = FIGURES.get(key)
        if not fig:
            continue

        async def make_buy_cb(fig_key=key):
            async def buy_cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ Esta tienda es tuya, no de otros.", ephemeral=True)
                    return
                db2 = load_db()
                buyer = get_user(db2, inter.user.id)
                if not buyer:
                    await inter.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
                    return
                fig2 = FIGURES[fig_key]
                price = fig2["price"]
                if buyer.get("coins", 0) < price:
                    await inter.response.send_message(
                        f"❌ No tienes suficiente oro. Necesitas **{price:,}**🪙 y tienes **{buyer.get('coins',0):,}**🪙.",
                        ephemeral=True
                    )
                    return
                buyer["coins"] -= price
                buyer.setdefault("figures", []).append({"key": fig_key, "level": 1, "xp": 0})
                # Auto-equipar si hay hueco
                team = buyer.get("team", [None, None, None])
                while len(team) < 3:
                    team.append(None)
                for i in range(3):
                    if team[i] is None:
                        team[i] = len(buyer["figures"]) - 1
                        break
                buyer["team"] = team
                save_db(db2)
                confirm_embed = discord.Embed(
                    title=f"🔱 ¡Adquirida! {fig2['name']}",
                    description=f"Has obtenido **{fig2['name']}** {fig2['emoji']}.\n¡Úsala con sabiduría!",
                    color=0xff00ff
                )
                confirm_embed.add_field(name="💳 Saldo restante", value=f"**{buyer['coins']:,}**🪙", inline=True)
                if fig2.get("image"):
                    confirm_embed.set_thumbnail(url=fig2["image"])
                await inter.response.send_message(embed=confirm_embed, ephemeral=True)
            return buy_cb

        btn = discord.ui.Button(
            label=f"Comprar {fig['name']} ({fig['price']:,}🪙)",
            style=discord.ButtonStyle.danger,
            custom_id=f"secret_buy_{key}"
        )
        btn.callback = make_buy_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================================
#  ARRANQUE
# ============================================================
bot.run(TOKEN)

