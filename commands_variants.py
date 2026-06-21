"""
commands_variants.py — Comandos del sistema de variantes y temporadas.

/variante       → Equipa una variante a una de tus figuras
/mis-variantes  → Ve todas las variantes que posees
/seasons        → [ADMIN] Cambia la temporada activa del servidor
"""

import random
import discord
from discord import app_commands

from database import load_db, save_db, get_user
from figures import FIGURES, RARITY_COLOR, RARITY_STARS
from variants import (
    VARIANTS, SEASONAL_VARIANTS, SEASONS, SEASON_VARIANT_POOL,
    COLOR_BEATS, calc_color_multiplier, get_active_variant, get_owned_variants,
)

ADMIN_ID = 1236293193893412975

# ── Color emojis para UI ──────────────────────────────────────────────────────
COLOR_EMOJI = {
    "rojo":        "🔴", "amarillo":    "🟡", "azul":       "🔵",
    "morado":      "🟣", "verde":       "🟢", "negro":      "⬛",
    "blanco":      "⬜", "halloween":   "🎃", "winter":     "❄️",
    "summer":      "☀️", "april_fools": "🃏",
    "amarillo_negro": "🟡⬛",
}

# ── Rueda de colores para display ────────────────────────────────────────────
def _color_wheel_text() -> str:
    normal = "🔴Rojo→🟡Amarillo→🔵Azul→🟣Morado→🟢Verde→🔴Rojo"
    seasonal = "🎃Halloween→☀️Summer→❄️Winter→🎃Halloween"
    special = "⬛Negro + ⬜Blanco = ambos hacen **x2 daño** entre sí"
    neutral = "🃏April Fools: neutro contra todos"
    return f"{normal}\n{seasonal}\n{special}\n{neutral}"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /variante                                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _variante_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    figs = user.get("figures", [])
    if not figs:
        await interaction.response.send_message("❌ No tienes figuras.", ephemeral=True)
        return

    owned_variants = user.get("variants_owned", {})
    uid = interaction.user.id

    # Step 1: elegir figura
    options = []
    for i, fd in enumerate(figs[:25]):
        fig = FIGURES.get(fd["key"], {})
        v_key, v_sea = get_active_variant(user, fd["key"])
        active_txt = f" [{v_key}]" if v_key else ""
        options.append(discord.SelectOption(
            label=f"{fig.get('name','?')}{active_txt} (Nv.{fd.get('level',1)})",
            value=str(i),
            description=f"{fd['key']} · {fig.get('rarity','?')}",
            emoji=RARITY_STARS.get(fig.get("rarity","común"),"⚪"),
        ))

    embed = discord.Embed(
        title="🎨 Sistema de Variantes",
        description=(
            "Las variantes cambian los stats, colores y efectos de tus figuras.\n"
            f"**Rueda de colores:**\n{_color_wheel_text()}\n\n"
            "Elige una figura para ver sus variantes disponibles:"
        ),
        color=0x9b59b6,
    )

    view = discord.ui.View(timeout=120)
    select = discord.ui.Select(
        placeholder="🎭 Elige una figura...",
        options=options,
        custom_id="var_fig_select",
        row=0,
    )

    async def fig_selected(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
            return
        idx     = int(inter.data["values"][0])
        fig_data= figs[idx]
        fig_key = fig_data["key"]
        fig     = FIGURES.get(fig_key, {})

        # Recargar DB
        db2   = load_db()
        user2 = get_user(db2, inter.user.id)
        owned = user2.get("variants_owned", {}).get(fig_key, [])

        # Get regular variants for this figure
        reg_variants   = VARIANTS.get(fig_key, {})
        # Get seasonal variants the user owns
        sea_variants   = {k: SEASONAL_VARIANTS[k]
                          for k in user2.get("seasonal_variants_owned", [])
                          if k in SEASONAL_VARIANTS}

        all_available  = {**{k: {"seasonal": False, **v} for k, v in reg_variants.items()
                              if k in owned or True},  # show all, greyed if not owned
                          **{k: {"seasonal": True, **v} for k, v in sea_variants.items()}}

        if not all_available:
            await inter.response.send_message(
                f"❌ **{fig.get('name','?')}** no tiene variantes disponibles todavía.",
                ephemeral=True,
            )
            return

        # Build variant selection
        var_options = []
        current_var, _ = get_active_variant(user2, fig_key)

        for vk, vd in list(all_available.items())[:25]:
            is_owned  = vk in owned or vd.get("seasonal", False)
            is_active = vk == current_var
            col       = COLOR_EMOJI.get(vd.get("color",""), "⚪")
            label     = f"{'✅ ' if is_active else ''}{'🔒 ' if not is_owned else ''}{vd.get('name_suffix') or vd.get('name','?')}"
            var_options.append(discord.SelectOption(
                label=label[:100],
                value=vk,
                description=vd.get("desc","")[:100],
                emoji=col,
            ))

        # Add "remove variant" option if active
        if current_var:
            var_options.insert(0, discord.SelectOption(
                label="❌ Quitar variante",
                value="__none__",
                description="Vuelve a la versión base de la figura.",
                emoji="⬜",
            ))

        var_embed = discord.Embed(
            title=f"🎨 Variantes de {fig.get('emoji','')} {fig.get('name','?')}",
            description=(
                f"**Variante activa:** {current_var or 'Ninguna'}\n"
                f"**Color actual:** {COLOR_EMOJI.get(user2.get('variants_equipped',{}).get(fig_key,{}).get('color',''),'—')}\n\n"
                "Elige una variante para equiparla:"
            ),
            color=RARITY_COLOR.get(fig.get("rarity","común"), 0x9b59b6),
        )
        for vk, vd in list(all_available.items())[:6]:
            col_e = COLOR_EMOJI.get(vd.get("color",""), "⚪")
            is_owned = vk in owned or vd.get("seasonal", False)
            owned_txt = "✅ Desbloqueada" if is_owned else "🔒 No desbloqueada"
            var_embed.add_field(
                name=f"{col_e} {vd.get('name_suffix') or vd.get('name','?')} · {owned_txt}",
                value=vd.get("desc","")[:120],
                inline=False,
            )

        var_view = discord.ui.View(timeout=120)
        var_select = discord.ui.Select(
            placeholder="🎨 Elige una variante...",
            options=var_options,
            custom_id="var_choice",
            row=0,
        )

        async def var_chosen(vinter: discord.Interaction):
            if vinter.user.id != uid:
                await vinter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            chosen_key = vinter.data["values"][0]
            db3   = load_db()
            user3 = get_user(db3, vinter.user.id)

            if chosen_key == "__none__":
                user3.setdefault("variants_equipped", {}).pop(fig_key, None)
                save_db(db3)
                await vinter.response.send_message(
                    f"✅ Variante quitada de **{fig.get('name','?')}**. Vuelve a su forma base.",
                    ephemeral=True,
                )
                return

            is_seasonal = chosen_key in SEASONAL_VARIANTS
            vdata = SEASONAL_VARIANTS.get(chosen_key) if is_seasonal else VARIANTS.get(fig_key, {}).get(chosen_key)
            if not vdata:
                await vinter.response.send_message("❌ Variante no encontrada.", ephemeral=True)
                return

            # Check ownership
            owned3 = user3.get("variants_owned", {}).get(fig_key, [])
            sea_owned3 = user3.get("seasonal_variants_owned", [])
            if chosen_key not in owned3 and chosen_key not in sea_owned3:
                await vinter.response.send_message(
                    "🔒 No tienes esta variante desbloqueada.", ephemeral=True
                )
                return

            # Equip
            user3.setdefault("variants_equipped", {})[fig_key] = {
                "key":      chosen_key,
                "seasonal": is_seasonal,
                "color":    vdata.get("color",""),
            }
            save_db(db3)

            col_e   = COLOR_EMOJI.get(vdata.get("color",""), "⚪")
            vname   = vdata.get("name_suffix") or vdata.get("name","?")
            result_embed = discord.Embed(
                title=f"✅ ¡Variante equipada!",
                description=(
                    f"{fig.get('emoji','')} **{fig.get('name','?')}** → "
                    f"**{vname}** {col_e}\n\n"
                    f"{vdata.get('desc','')}"
                ),
                color=RARITY_COLOR.get(fig.get("rarity","común"), 0x9b59b6),
            )
            hp_mod  = vdata.get("hp_mod",  1.0)
            atk_mod = vdata.get("atk_mod", 1.0)
            def_mod = vdata.get("def_mod", 1.0)
            result_embed.add_field(
                name="📊 Modificadores de stats",
                value=(
                    f"❤️ HP: {'+'if hp_mod>=1 else ''}{int((hp_mod-1)*100)}%  "
                    f"⚔️ ATK: {'+'if atk_mod>=1 else ''}{int((atk_mod-1)*100)}%  "
                    f"🛡️ DEF: {'+'if def_mod>=1 else ''}{int((def_mod-1)*100)}%"
                ),
                inline=False,
            )
            await vinter.response.send_message(embed=result_embed, ephemeral=True)

        var_select.callback = var_chosen
        var_view.add_item(var_select)

        await inter.response.edit_message(embed=var_embed, view=var_view)

    select.callback = fig_selected
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /mis-variantes                                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _mis_variantes_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    owned     = user.get("variants_owned", {})
    sea_owned = user.get("seasonal_variants_owned", [])
    equipped  = user.get("variants_equipped", {})

    embed = discord.Embed(
        title="🎨 Mis Variantes",
        color=0x9b59b6,
    )

    total = 0
    for fig_key, var_list in owned.items():
        if not var_list:
            continue
        fig  = FIGURES.get(fig_key, {})
        lines = []
        for vk in var_list:
            vd = VARIANTS.get(fig_key, {}).get(vk, {})
            col = COLOR_EMOJI.get(vd.get("color",""), "⚪")
            is_eq = equipped.get(fig_key, {}).get("key") == vk
            lines.append(f"{'✅ ' if is_eq else ''}{col} {vd.get('name_suffix','?')}")
            total += 1
        embed.add_field(
            name=f"{fig.get('emoji','')} {fig.get('name','?')}",
            value="\n".join(lines),
            inline=True,
        )

    if sea_owned:
        sea_lines = []
        for vk in sea_owned:
            vd  = SEASONAL_VARIANTS.get(vk, {})
            col = COLOR_EMOJI.get(vd.get("color",""), "⚪")
            sea_lines.append(f"{col} {vd.get('name','?')}")
            total += 1
        embed.add_field(
            name="🌟 Variantes de Temporada",
            value="\n".join(sea_lines),
            inline=False,
        )

    if total == 0:
        embed.description = (
            "No tienes ninguna variante todavía.\n"
            "Consíguelas jugando durante temporadas activas o en la tienda."
        )
    else:
        embed.description = (
            f"Tienes **{total}** variante(s) desbloqueadas.\n"
            f"Usa `/variante` para equiparlas."
        )

    embed.add_field(
        name="🎡 Rueda de colores",
        value=_color_wheel_text(),
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /seasons  [ADMIN]                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _seasons_cmd(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(
            "❌ Este comando es exclusivo de GAMER64.", ephemeral=True
        )
        return

    db      = load_db()
    current = db.get("season", "none")
    uid     = interaction.user.id

    embed = discord.Embed(
        title="🌍 Gestión de Temporadas",
        description=(
            f"**Temporada activa:** {SEASONS.get(current,{}).get('name','Ninguna')}\n\n"
            "Al activar una temporada:\n"
            "› Los jugadores pueden conseguir variantes exclusivas de esa temporada.\n"
            "› Las variantes de temporada tienen colores especiales en la rueda.\n\n"
            "Elige una temporada para activarla:"
        ),
        color=SEASONS.get(current, {}).get("color", 0x5865f2),
    )

    for sid, sdata in SEASONS.items():
        var_list = SEASON_VARIANT_POOL.get(sid, [])
        var_names = ", ".join(
            SEASONAL_VARIANTS[v]["name"] for v in var_list if v in SEASONAL_VARIANTS
        )
        embed.add_field(
            name=f"{'▶️ ACTIVA — ' if sid == current else ''}{sdata['emoji']} {sdata['name']}",
            value=f"Variantes: {var_names or '—'}",
            inline=False,
        )

    view    = discord.ui.View(timeout=120)
    options = [
        discord.SelectOption(
            label=f"{v['emoji']} {v['name']}",
            value=k,
            description=", ".join(SEASONAL_VARIANTS[sv]["name"] for sv in SEASON_VARIANT_POOL.get(k,[]) if sv in SEASONAL_VARIANTS) or "Sin variantes",
            default=(k == current),
        )
        for k, v in SEASONS.items()
    ]
    select = discord.ui.Select(
        placeholder="🌍 Elige una temporada...",
        options=options,
        custom_id="season_select",
    )

    async def season_chosen(inter: discord.Interaction):
        if inter.user.id != uid:
            await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
            return
        chosen = inter.data["values"][0]
        db2    = load_db()
        db2["season"] = chosen
        save_db(db2)

        sdata = SEASONS.get(chosen, {})
        var_list  = SEASON_VARIANT_POOL.get(chosen, [])
        var_names = "\n".join(
            f"› {SEASONAL_VARIANTS[v]['name']}: {SEASONAL_VARIANTS[v]['desc'][:80]}..."
            for v in var_list if v in SEASONAL_VARIANTS
        )

        result = discord.Embed(
            title=f"{sdata.get('emoji','🌍')} ¡Temporada activada!",
            description=(
                f"**{sdata.get('name','?')}** está ahora activa.\n\n"
                f"**Variantes disponibles esta temporada:**\n{var_names or '—'}"
            ),
            color=sdata.get("color", 0x5865f2),
        )
        await inter.response.edit_message(embed=result, view=None)

    select.callback = season_chosen
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  HELPER: dar variante de temporada al jugador                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def give_seasonal_variant(user_data: dict, variant_key: str) -> bool:
    """Da una variante de temporada al jugador. Devuelve True si es nueva."""
    if variant_key not in SEASONAL_VARIANTS:
        return False
    owned = user_data.setdefault("seasonal_variants_owned", [])
    if variant_key in owned:
        return False
    owned.append(variant_key)
    return True


def give_variant(user_data: dict, fig_key: str, variant_key: str) -> bool:
    """Da una variante normal al jugador para una figura. Devuelve True si es nueva."""
    if fig_key not in VARIANTS or variant_key not in VARIANTS[fig_key]:
        return False
    owned = user_data.setdefault("variants_owned", {}).setdefault(fig_key, [])
    if variant_key in owned:
        return False
    owned.append(variant_key)
    return True


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  REGISTRO                                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  /atributos                                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def _atributos_cmd(interaction: discord.Interaction):
    """
    Muestra la rueda de atributos: qué color es débil/fuerte contra cuál.
    Las variantes de color NO dan stats extra — solo activan este multiplicador
    de daño según el matchup entre el atacante y el defensor.
    """
    embed = discord.Embed(
        title="🎡 Rueda de Atributos",
        description=(
            "Cada figura tiene un **color predeterminado** según su variante. "
            "El color no cambia stats — solo determina si haces **más** o **menos** "
            "daño contra el color del rival.\n\n"
            "Si ninguno de los dos colores tiene ventaja, la batalla se desarrolla normalmente "
            "(daño x1, sin buff ni debuff)."
        ),
        color=0x9b59b6,
    )

    embed.add_field(
        name="🔴🟡🔵🟣🟢 Rueda Normal",
        value=(
            "🔴 **Rojo** vence a 🟡 **Amarillo**\n"
            "🟡 **Amarillo** vence a 🔵 **Azul**\n"
            "🔵 **Azul** vence a 🟣 **Morado**\n"
            "🟣 **Morado** vence a 🟢 **Verde**\n"
            "🟢 **Verde** vence a 🔴 **Rojo**\n\n"
            "› El color ganador hace **+25% de daño**.\n"
            "› El color perdedor hace **-20% de daño**."
        ),
        inline=False,
    )

    embed.add_field(
        name="⬛⬜ Negro y Blanco",
        value=(
            "⬛ **Negro** y ⬜ **Blanco** no tienen ventaja ni desventaja contra "
            "ningún otro color — sus batallas se desarrollan siempre con daño normal.\n\n"
            "**Excepción:** si un ⬛ **Negro** se enfrenta a un ⬜ **Blanco**, "
            "**¡ambos hacen el DOBLE de daño!** (x2)"
        ),
        inline=False,
    )

    embed.add_field(
        name="🎃☀️❄️ Rueda de Temporada",
        value=(
            "🎃 **Halloween** vence a ☀️ **Summer**\n"
            "☀️ **Summer** vence a ❄️ **Winter**\n"
            "❄️ **Winter** vence a 🎃 **Halloween**\n\n"
            "🃏 **April Fools** no vence ni es vencido por ningún color del juego."
        ),
        inline=False,
    )

    embed.set_footer(text="Las variantes de color son predeterminadas por figura — no se compran ni se eligen libremente.")

    await interaction.response.send_message(embed=embed)


def register_commands(bot):

    @bot.tree.command(name="variante", description="Equipa una variante a una de tus figuras")
    async def variante(interaction: discord.Interaction):
        await _variante_cmd(interaction)

    @bot.tree.command(name="mis-variantes", description="Ve todas las variantes que posees")
    async def mis_variantes(interaction: discord.Interaction):
        await _mis_variantes_cmd(interaction)

    @bot.tree.command(name="atributos", description="Ve la rueda de atributos: qué color vence a cuál")
    async def atributos(interaction: discord.Interaction):
        await _atributos_cmd(interaction)

    @bot.tree.command(name="seasons", description="[ADMIN] Cambia la temporada activa del servidor")
    async def seasons(interaction: discord.Interaction):
        await _seasons_cmd(interaction)
