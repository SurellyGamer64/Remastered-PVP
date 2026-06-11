"""
commands_shop.py — Comandos de tiendas (/tienda, /secret-store).
Se importa desde main.py; usa bot como variable global del contexto.
"""
import random
import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import (
    FIGURES, SECRET_FIGURES, SECRET_CODE, SECRET_OWNER_ID,
    RARITY_COLOR, RARITY_STARS, XP_PER_WIN, apply_level_bonus,
    secret_store_unlocked,
)
from shops import (
    SHOPS, MYSTERY_PACKS, SHOP_MYTHIC_CHANCE,
    check_shop_reset, time_until_reset,
    _pick_shop_figures, open_mystery_pack,
)
from economy import (
    INGREDIENTS, RECIPES, ACHIEVEMENTS,
    give_battle_ingredient, grant_achievement, get_learn_effect,
)

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
    # Mostrar info de disponibilidad y probabilidades por tienda
    AVAIL_LABELS = {
        "mercado":  "60–80%",
        "gamer":    "76–90%",
        "tails":    "75–89%",
        "bar":      "50–80%",
        "toad":     "40–50%",
        "acertijo": "100%",
    }
    for sid, shop in SHOPS.items():
        w = shop["weights"]
        avail_pct = AVAIL_LABELS.get(sid, "?")
        if sid == "acertijo":
            value_txt = (
                f"{shop['desc']}
"
                f"`Disponibilidad: {avail_pct} · Solo vende sobres misteriosos`"
            )
        else:
            active_rarezas = [f"{r} {p}%" for r, p in w.items() if p > 0]
            mythic_c = SHOP_MYTHIC_CHANCE.get(sid, 0)
            if mythic_c > 0:
                active_rarezas.append(f"mítico {mythic_c}%")
            value_txt = (
                f"{shop['desc']}
"
                f"`Disponibilidad: {avail_pct} · {' · '.join(active_rarezas)}`"
            )
        embed.add_field(name=shop["name"], value=value_txt, inline=False)

    view = discord.ui.View(timeout=120)
    for sid, shop in SHOPS.items():
        btn = discord.ui.Button(label=shop["name"], style=discord.ButtonStyle.primary, custom_id=f"shop_{sid}")
        def make_shop_cb(shop_id=sid):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                await _show_shop(inter, shop_id, db, user, uid, edit=True)
            return cb
        btn.callback = make_shop_cb()
        view.add_item(btn)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def _show_acertijo(interaction: discord.Interaction, user: dict, uid: int, edit: bool):
    """
    Tienda El Acertijo — solo vende sobres misteriosos.
    Cada sobre tiene sus propios pesos de rareza; puede salir CUALQUIER figura comprable.
    Las probabilidades se muestran explícitamente en el embed.
    """
    pack_lines = []
    for pid, pack in MYSTERY_PACKS.items():
        rw = pack["rarity_weights"]
        rarity_str = " · ".join(f"**{r}** {w}%" for r, w in rw.items())
        extras = []
        if pack["ing_chance"] > 0:
            extras.append(f"{pack['ing_chance']}% 🧺 ingrediente")
        if pack["recipe_chance"] > 0:
            extras.append(f"{pack['recipe_chance']}% 📜 receta")
        bonus = f"\n  ↳ {' · '.join(extras)}" if extras else ""
        pack_lines.append(
            f"**{pack['name']}** `{pack['price']:,}🪙`\n  {rarity_str}{bonus}"
        )

    embed = discord.Embed(
        title="❓ El Acertijo de las Compras",
        description=(
            "¡Aquí no sabes lo que te llevas hasta que abres el sobre!\n"
            "Puede salir **cualquier figura** del juego según la rareza del sobre.\n\n"
            + "\n\n".join(pack_lines)
            + f"\n\n💰 Tu oro: **{user.get('coins', 0):,}🪙**"
        ),
        color=0x9b59b6,
    )

    view = discord.ui.View(timeout=120)
    for i, (pack_id, pack) in enumerate(MYSTERY_PACKS.items()):
        can_afford = user.get("coins", 0) >= pack["price"]
        btn = discord.ui.Button(
            label=f"{'🛒' if can_afford else '❌'} {pack['name']} ({pack['price']:,}🪙)",
            style=discord.ButtonStyle.primary if can_afford else discord.ButtonStyle.secondary,
            disabled=not can_afford,
            custom_id=f"pack_{pack_id}",
            row=i // 2,
        )

        def make_pack_cb(pid=pack_id, pprice=pack["price"], pname=pack["name"]):
            async def pack_cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                db2 = load_db()
                u2  = get_user(db2, inter.user.id)
                if u2.get("coins", 0) < pprice:
                    await inter.response.send_message(
                        f"❌ Necesitas **{pprice:,}🪙** y tienes **{u2.get('coins', 0):,}🪙**.",
                        ephemeral=True,
                    )
                    return

                # Abrir sobre usando la lógica centralizada de shops.py
                u2["coins"] -= pprice
                result = open_mystery_pack(
                    pid, u2, FIGURES, SECRET_FIGURES,
                    INGREDIENTS, RECIPES, random
                )
                save_db(db2)

                fig    = FIGURES.get(result["fig"], {}) if result["fig"] else {}
                rcolor = RARITY_COLOR.get(fig.get("rarity", "común"), 0x95a5a6)
                rstar  = RARITY_STARS.get(fig.get("rarity", "común"), "⚪")

                result_embed = discord.Embed(
                    title=f"🎁 ¡Abriste un {pname}!",
                    description=f"Conseguiste: **{fig.get('emoji','')} {fig.get('name','?')}** {rstar}",
                    color=rcolor,
                )
                result_embed.add_field(name="❤️ HP",     value=fig.get("hp", "?"),     inline=True)
                result_embed.add_field(name="⚔️ ATK",    value=fig.get("attack", "?"), inline=True)
                result_embed.add_field(name="🛡️ DEF",   value=fig.get("defense", "?"),inline=True)
                result_embed.add_field(name="🌟 Rareza",  value=fig.get("rarity", "?").upper(), inline=True)
                if result["ingredient"]:
                    result_embed.add_field(
                        name="🧺 ¡Bonus ingrediente!",
                        value=f"{result['ingredient']} {INGREDIENTS.get(result['ingredient'], '')}",
                        inline=True,
                    )
                if result["recipe"]:
                    result_embed.add_field(name="📜 ¡Receta desbloqueada!", value=result["recipe"], inline=True)
                result_embed.add_field(name="💳 Saldo", value=f"**{u2['coins']:,}🪙**", inline=True)
                if fig.get("image"):
                    result_embed.set_thumbnail(url=fig["image"])
                await inter.response.send_message(embed=result_embed, ephemeral=True)
            return pack_cb

        btn.callback = make_pack_cb()
        view.add_item(btn)

    # Botón volver
    back_btn = discord.ui.Button(
        label="◀ Cambiar tienda", style=discord.ButtonStyle.secondary,
        custom_id="back_acertijo", row=2
    )
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
        def make_buy(fig_key=k, fig_price=price):
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
            def make_pack_cb(pid=pack_id, pdata=pack):
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
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ============================================================
#  SISTEMA DE LOGROS
# ============================================================
ACHIEVEMENTS = {
    # Progresión básica
    "first_figure":     {"name":"🎭 El principio...",          "desc":"Compra tu primera figura.",                        "secret":False},
    "first_win":        {"name":"🏆 Primera Victoria",         "desc":"Gana tu primera batalla.",                         "secret":False},
    "wins_10":          {"name":"⚔️ Guerrero",                 "desc":"Gana 10 batallas.",                                "secret":False},
    "wins_100":         {"name":"💀 Leyenda del PvP",          "desc":"Gana 100 batallas.",                               "secret":False},
    "first_level":      {"name":"⬆️ Subí de nivel!",          "desc":"Sube de nivel por primera vez (tú como jugador).", "secret":False},
    "fig_first_level":  {"name":"⬆️ Subamos las cosas!",         "desc":"Sube de nivel una figura por primera vez.",        "secret":False},
    "first_recipe":     {"name":"🧑‍🍳 Chef Novato",             "desc":"Descubre tu primera receta.",                      "secret":False},
    "recipes_10":       {"name":"🧑‍🍳 Chef Profesional",        "desc":"Descubre 10 recetas.",                             "secret":False},
    "first_explore":    {"name":"🗺️ Explorador Nato",          "desc":"Completa tu primera exploración.",                  "secret":False},
    "reach_level_10":   {"name":"🌟 Nivel 10",                 "desc":"Llega al nivel 10 como jugador.",                  "secret":False},
    "reach_level_30":   {"name":"🌟 Nivel 30",                 "desc":"Llega al nivel 30 como jugador.",                  "secret":False},
    "reach_level_50":   {"name":"🌟 Nivel 50",                 "desc":"Llega al nivel 50 como jugador.",                  "secret":False},
    "reach_level_100":  {"name":"👑 Nivel 100",                "desc":"Alcanza el nivel máximo como jugador.",             "secret":False},
    "first_rebirth":    {"name":"🔄 He vuelto...",                 "desc":"Haz tu primer Rebirth.",                           "secret":False},
    "first_combine":    {"name":"🔀 Experimento Loco!",               "desc":"Combina figuras por primera vez.",                  "secret":False},
    "first_learn":      {"name":"📚 Primer Conocimiento",      "desc":"Aprende tu primer nodo del árbol.",                "secret":False},
    "mythic_owned":     {"name":"🔱 Coleccionista Mítico",     "desc":"Consigue una figura de rareza mítica.",            "secret":False},
    "secret_store":     {"name":"🔒 El Código Correcto",       "desc":"Desbloquea la tienda secreta.",                    "secret":True},
    # Boss fights
    "beat_nino":        {"name":"👦 Niños al recreo",          "desc":"Derrota al Niño Random.",                          "secret":False},
    "beat_paper":       {"name":"📄 Tijeras vence a Papel!",   "desc":"Derrota a Paper Mario.",                           "secret":False},
    "beat_steve":       {"name":"⛏️ Minero Retirado",          "desc":"Derrota a Steve.",                                 "secret":False},
    "beat_impostor_3":  {"name":"🔪 VICTORY! 👑",       "desc":"Vence al Impostor Negro con solo 3 figuras.",      "secret":False},
    "beat_impostor_7":  {"name":"😕 Aburrido...",     "desc":"Vence al Impostor Negro usando las 7 figuras.",    "secret":True},
    "beat_antifas":     {"name":"👑 EL NUEVO CAMPEON!",   "desc":"Derrota al Antifas Antifasado.",                   "secret":False},
    # Misceláneos
    "daily_streak_7":   {"name":"📅 Racha de 7 días",          "desc":"Mantén una racha diaria de 7 días seguidos.",      "secret":False},
    "coins_10000":      {"name":"💰 Rico Rico",                 "desc":"Acumula 10,000 monedas a la vez.",                 "secret":False},
    "fig_max_level":    {"name":"⬆️ Al Límite",                "desc":"Sube una figura al nivel máximo (30).",            "secret":False},
    # Logros de Kirby
    "kirby_no_mas":         {"name":"🚫 NO MAS KIRBY!",            "desc":"... Nunca debiste intentar absorber eso...",       "secret":True},
    "kirby_no_entendiste":  {"name":"🚫 NO ME ENTENDISTE!!?? NO MAS!!","desc":"NO... SOLO.... NO!!",                         "secret":True},
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

        def make_buy_cb(fig_key=key):
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
#  /get — Pase dorado exclusivo [GAMER64]
# ============================================================
GET_AUTHORIZED_ID = 1236293193893412975

# Normalización de rarezas para /get
_RARITY_NORM = {
    "común":"común","comun":"común",
    "raro":"raro",
    "épico":"épico","epico":"épico",
    "legendario":"legendario","Legendario":"legendario",
    "mítico":"mítico","Mítico":"mítico",
}
_RARITY_ORDER  = ["común","raro","épico","legendario","mítico"]
_RARITY_EMOJI  = {"común":"⚪","raro":"🔵","épico":"🟣","legendario":"🌟","mítico":"🔱"}
_RARITY_STYLE  = {
    "común":      discord.ButtonStyle.secondary,
    "raro":       discord.ButtonStyle.primary,
    "épico":      discord.ButtonStyle.primary,
    "legendario": discord.ButtonStyle.success,
    "mítico":     discord.ButtonStyle.danger,
}

def _get_all_by_rarity():
    """Agrupa TODAS las figuras (incluyendo boss y precio 0) por rareza normalizada."""
    by_r = {r: [] for r in _RARITY_ORDER}
    for key, fig in FIGURES.items():
        if not fig.get("name"):
            continue
        norm = _RARITY_NORM.get(fig.get("rarity","común"), "común")
        by_r[norm].append((key, fig))
    return by_r

@bot.tree.command(name="get", description="[GAMER64] El pase dorado y exclusivo...")
async def get_cmd(interaction: discord.Interaction):
    if interaction.user.id != GET_AUTHORIZED_ID:
        await interaction.response.send_message("❌ No tienes acceso a este comando.", ephemeral=True)