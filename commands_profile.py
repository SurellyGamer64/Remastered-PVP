"""
commands_profile.py — Comandos de perfil y colección (/registrar, /perfil, /misfiguras, /equipar).
"""
import discord
from discord import app_commands

from database import load_db, save_db, get_user, create_user
from figures import (
    FIGURES, FIGURE_SKILLS, RARITY_COLOR, RARITY_STARS,
    XP_PER_WIN, apply_level_bonus, xp_to_level_up,
)
from economy import LEARN_TREE, get_learn_effect, ACHIEVEMENTS

# --- PERFIL ---
# --- TIENDA ---
# --- MIS FIGURAS ---
def get_unique_figs(figs):
    """Devuelve lista de figuras únicas (sin duplicados) con conteo de copias.
    Cada entrada: (key, fig_data_mejor_nivel, count)
    Ordenadas según aparecen por primera vez en la colección."""
    seen = {}   # key -> {"data": fig_data, "count": n, "order": i}
    for i, fd in enumerate(figs):
        k = fd["key"]
        if k not in seen:
            seen[k] = {"data": fd, "count": 1, "order": i}
        else:
            seen[k]["count"] += 1
            # Guardar la copia de mayor nivel
            if fd.get("level", 1) > seen[k]["data"].get("level", 1):
                seen[k]["data"] = fd
    # Ordenar por orden de primera aparición
    ordered = sorted(seen.values(), key=lambda x: x["order"])
    return [(v["data"]["key"], v["data"], v["count"]) for v in ordered]

def build_figure_embed(user, unique_figs, page, viewed_user_id=None):
    key, fig_data, count = unique_figs[page]
    fig = FIGURES.get(key, {})
    lvl = fig_data.get("level", 1)
    xp  = fig_data.get("xp", 0)
    team = user.get("team", [None, None, None])
    all_figs = user.get("figures", [])
    pos_names = ["🥇 Frontal", "🥈 Centro", "🥉 Trasero"]
    rarity = fig.get("rarity", "común")
    star  = RARITY_STARS.get(rarity, "⚪")
    color = RARITY_COLOR.get(rarity, 0x95a5a6)

    # Nombre especial en fuente wide (fullwidth unicode) para OG GAMER 64
    fig_name = fig.get("name", key)
    if key == "og_gamer64":
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
        wide   = "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９　"
        fig_name = "".join(wide[normal.index(c)] if c in normal else c for c in fig_name)

    # ¿Está en el equipo?
    in_team = ""
    for t_pos, t_idx in enumerate(team):
        if t_idx is not None and t_idx < len(all_figs) and all_figs[t_idx]["key"] == key:
            in_team += f" **[{pos_names[t_pos]}]**"

    # Título con contador de copias
    copies_txt = f" ×{count}" if count > 1 else ""
    embed = discord.Embed(
        title=f"{fig.get('emoji','')} {fig_name}{copies_txt} {star}{in_team}",
        description=f"Rareza: **{rarity.upper()}** | Precio: **{fig.get('price',0):,}🪙**",
        color=color
    )

    # Copias
    if count > 1:
        embed.add_field(name="📦 Copias", value=f"Tienes **{count}** de esta figura", inline=False)

    # Annoying Dog: stats ocultas en /misfiguras
    if key == "annoying_dog":
        embed.add_field(
            name="📊 Stats",
            value=(
                "❤️ **Vida:** 290\n"
                "⚔️ **Ataque:** ???\n"
                "🛡️ **Defensa:** ???\n"
                "⚡ **Velocidad:** ???\n"
                "\n*Toby se comió sus propias stats...*"
            ),
            inline=True
        )
    else:
        embed.add_field(
            name="📊 Stats",
            value=(
                f"❤️ **Vida:** {apply_level_bonus(fig.get('hp',0), lvl)}\n"
                f"⚔️ **Ataque:** {apply_level_bonus(fig.get('attack',0), lvl)}\n"
                f"🛡️ **Defensa:** {apply_level_bonus(fig.get('defense',0), lvl)}\n"
                f"⚡ **Velocidad:** {fig.get('speed',0)}"
            ),
            inline=True
        )
    embed.add_field(
        name="🏅 Progreso",
        value=(f"Nivel: **{lvl}**\nXP: **{xp}/{xp_to_level_up(lvl)}**"),
        inline=True
    )

    # Equipo
    team_str = ""
    for i, idx in enumerate(team):
        if idx is not None and idx < len(all_figs):
            fd = all_figs[idx]
            fg = FIGURES.get(fd["key"])
            name  = fg.get("name", fd["key"]) if fg else fd["key"]
            emoji = fg.get("emoji", "") if fg else ""
            team_str += f"{pos_names[i]}: {emoji} {name}\n"
        else:
            team_str += f"{pos_names[i]}: _(vacío)_\n"
    embed.add_field(name="⚔️ Tu equipo", value=team_str, inline=False)

    # Habilidades — para OG GAMER 64 agrupar por fase
    skills = FIGURE_SKILLS.get(key, [])
    type_emoji = {
        "damage":"⚔️","heal":"💚","drain":"⚡","drain_fill":"🔴","parry":"🛡️",
        "buff":"⭐","gamble":"🎲","gamble_fire":"🔥","team_atk_buff":"⭐","dot":"💣",
        "bad_update":"🔳","ban_hammer":"🔨","fly_away":"✈️","michi_counter":"🦊",
        "glitch_dmg":"🌀","corruption":"🌑","retribution":"🦷","fast_kill":"🔪",
        "consumed_fury":"💥","revive_team":"💀","heal_team_self":"🍗",
        "switch_sword":"🗡️","slash":"⚔️","lobster":"🦞",
        "charge_delete":"💥","og_ki_charge":"✨","instakill_random":"☠️",
        "og_reset_phase":"🔄","og_its_over":"💣",
    }
    bar_labels = {30:"🟡[30⚡]", 60:"🟠[60⚡]", 100:"🔴[100⚡]"}

    if key == "og_gamer64" and any("phase" in sk for sk in skills):
        # Agrupar por fase
        phases_map = {}
        for sk in skills:
            ph = sk.get("phase", 1)
            phases_map.setdefault(ph, []).append(sk)
        phase_names = {1:"🔵 Fase 1", 2:"🟣 Fase 2", 3:"🟡 Fase 3", 4:"🔴 Fase 4"}
        for ph in sorted(phases_map.keys()):
            skill_str = ""
            for sk in phases_map[ph]:
                te = type_emoji.get(sk["type"], "⚡")
                bl = bar_labels.get(sk["cost"], f"[{sk['cost']}⚡]")
                skill_str += f"{bl} {te} **{sk['name']}**\n_{sk['desc']}_\n\n"
            embed.add_field(name=phase_names.get(ph, f"Fase {ph}"), value=skill_str.strip(), inline=False)
        embed.add_field(
            name="🔱 Pasiva: Fases",
            value="Gamer puede revivir después de morir. Cada muerte cambia su fase en orden numérico. Si muere en Fase 4, muere definitivamente.",
            inline=False
        )
    else:
        skill_str = ""
        for sk in skills:
            te = type_emoji.get(sk["type"], "⚡")
            bl = bar_labels.get(sk["cost"], f"[{sk['cost']}⚡]")
            skill_str += f"{bl} {te} **{sk['name']}**\n_{sk['desc']}_\n\n"
        if skill_str:
            embed.add_field(name="✨ Habilidades", value=skill_str.strip(), inline=False)

    if fig.get("image"):
        embed.set_image(url=fig["image"])

    embed.set_footer(text=f"Figura {page+1} de {len(unique_figs)}  •  Colección única")
    return embed

def make_fig_view_sync(orig_user_id, user, unique_figs, page, viewed_user_id=None):
    view = discord.ui.View(timeout=120)
    total = len(unique_figs)
    # viewed_user_id: si es None, se usa orig_user_id (viendo su propio inventario)
    target_uid = viewed_user_id or orig_user_id

    prev_btn = discord.ui.Button(label="◀ Anterior", style=discord.ButtonStyle.secondary,
                                  disabled=page==0, custom_id="fig_prev", row=0)
    counter_btn = discord.ui.Button(label=f"{page+1} / {total}", style=discord.ButtonStyle.primary,
                                     disabled=True, custom_id="fig_counter", row=0)
    next_btn = discord.ui.Button(label="Siguiente ▶", style=discord.ButtonStyle.secondary,
                                  disabled=page==total-1, custom_id="fig_next", row=0)

    def make_nav(new_page):
        async def callback(inter: discord.Interaction):
            if inter.user.id != orig_user_id:
                await inter.response.send_message("❌ Este menú no es tuyo.", ephemeral=True)
                return
            db2 = load_db()
            u2 = get_user(db2, target_uid)   # ← carga al dueño del inventario, no al que clickea
            if not u2:
                await inter.response.send_message("❌ Usuario no encontrado.", ephemeral=True)
                return
            uf2 = get_unique_figs(u2.get("figures", []))
            embed2 = build_figure_embed(u2, uf2, new_page, viewed_user_id=target_uid)
            view2  = make_fig_view_sync(orig_user_id, u2, uf2, new_page, viewed_user_id=target_uid)
            await inter.response.edit_message(embed=embed2, view=view2)
        return callback

    prev_btn.callback = make_nav(page - 1)
    next_btn.callback = make_nav(page + 1)
    view.add_item(prev_btn)
    view.add_item(counter_btn)
    view.add_item(next_btn)
    return view

async def show_figure_menu(interaction, user, figs, page: int, viewed_user_id=None):
    unique_figs = get_unique_figs(figs)
    if not unique_figs:
        await interaction.response.send_message("📭 No tienes figuras.", ephemeral=True)
        return
    page = min(page, len(unique_figs) - 1)
    target_uid = viewed_user_id or interaction.user.id
    embed = build_figure_embed(user, unique_figs, page, viewed_user_id=target_uid)
    view  = make_fig_view_sync(interaction.user.id, user, unique_figs, page, viewed_user_id=target_uid)
    if hasattr(interaction, 'response') and not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.edit_original_response(embed=embed, view=view)

# --- EQUIPAR ---
POS_NAMES  = ["🥇 Frontal", "🥈 Centro", "🥉 Trasero"]
POS_LABELS = ["Frontal (primer atacante)", "Centro (segundo)", "Trasero (reserva)"]


def _build_equip_embed(user: dict, step: int, temp_team: list) -> discord.Embed:
    """Genera el embed para el paso 'step' del menú de equipar."""
    figs     = user.get("figures", [])
    team     = temp_team

    embed = discord.Embed(
        title=f"⚔️ Equipar — Paso {step + 1}/3: {POS_LABELS[step]}",
        description=(
            "Elige la figura para esta posición del equipo.\n"
            "Tu equipo se muestra abajo conforme lo vas armando."
        ),
        color=0x3498db,
    )

    # Equipo actual (parcial)
    team_txt = ""
    for i in range(3):
        if i < step and team[i] is not None and team[i] < len(figs):
            fd  = figs[team[i]]
            fig = FIGURES.get(fd["key"], {})
            team_txt += f"{POS_NAMES[i]}: {fig.get('emoji','')} **{fig.get('name','?')}** (Nv.{fd.get('level',1)})\n"
        elif i == step:
            team_txt += f"{POS_NAMES[i]}: ← _eligiendo ahora_\n"
        else:
            team_txt += f"{POS_NAMES[i]}: _(pendiente)_\n"
    embed.add_field(name="🛡️ Tu equipo", value=team_txt, inline=False)
    embed.set_footer(text="Puedes elegir la misma figura en varias posiciones.")
    return embed


async def show_equip_menu(interaction: discord.Interaction, user: dict, step: int,
                           temp_team: list = None, edit: bool = False):
    """
    Muestra el selector de figura para la posición 'step' (0=frontal, 1=centro, 2=trasero).
    temp_team es la lista de índices ya elegidos para las posiciones anteriores.
    """
    if temp_team is None:
        # Heredar el equipo actual como base para que no se pierda lo ya equipado
        current = user.get("team", [None, None, None])
        temp_team = list(current) + [None] * (3 - len(current))
        temp_team = temp_team[:3]

    figs = user.get("figures", [])
    if not figs:
        msg = "❌ No tienes figuras. Usa `/tienda` para comprar."
        await interaction.response.send_message(msg, ephemeral=True)
        return

    uid   = interaction.user.id
    embed = _build_equip_embed(user, step, temp_team)

    # Build Select with all figures (max 25 shown, paginated via multiple selects if needed)
    # Group unique figures for cleaner display
    unique = {}
    for i, fd in enumerate(figs):
        k = fd["key"]
        if k not in unique or fd.get("level", 1) > unique[k]["level"]:
            unique[k] = {"idx": i, "level": fd.get("level", 1), "fd": fd}

    options = []
    for k, data in list(unique.items())[:25]:
        fig  = FIGURES.get(k, {})
        star = RARITY_STARS.get(fig.get("rarity", "común"), "⚪")
        options.append(discord.SelectOption(
            label=f"{fig.get('name', k)} (Nv.{data['level']})",
            value=str(data["idx"]),
            description=f"{fig.get('rarity','?').capitalize()} · HP:{fig.get('hp','?')} ATK:{fig.get('attack','?')} DEF:{fig.get('defense','?')}",
            emoji=star,
        ))

    view   = discord.ui.View(timeout=120)
    select = discord.ui.Select(
        placeholder=f"Elige para {POS_NAMES[step]}...",
        options=options,
        custom_id=f"equip_step_{step}",
        row=0,
    )

    def make_select_cb(current_step: int, current_temp: list):
        async def select_cb(inter: discord.Interaction):
            if inter.user.id != uid:
                await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return

            chosen_idx   = int(inter.data["values"][0])
            new_temp     = list(current_temp)
            new_temp[current_step] = chosen_idx

            if current_step < 2:
                # Reload user data and proceed to next step
                db2   = load_db()
                user2 = get_user(db2, inter.user.id)
                await show_equip_menu(inter, user2, current_step + 1, new_temp, edit=True)
            else:
                # Final step — save team
                db2   = load_db()
                user2 = get_user(db2, inter.user.id)
                figs2 = user2.get("figures", [])

                # Validate indices still exist
                valid_team = []
                for idx in new_temp:
                    if idx is not None and idx < len(figs2):
                        valid_team.append(idx)
                    else:
                        valid_team.append(None)

                user2["team"] = valid_team
                save_db(db2)

                # Build confirmation embed
                conf = discord.Embed(
                    title="✅ ¡Equipo guardado!",
                    description="Tu equipo de batalla ha sido actualizado.",
                    color=0x2ecc71,
                )
                team_txt = ""
                for i, idx in enumerate(valid_team):
                    if idx is not None and idx < len(figs2):
                        fd  = figs2[idx]
                        fig = FIGURES.get(fd["key"], {})
                        team_txt += f"{POS_NAMES[i]}: {fig.get('emoji','')} **{fig.get('name','?')}** (Nv.{fd.get('level',1)})\n"
                    else:
                        team_txt += f"{POS_NAMES[i]}: _(vacío)_\n"
                conf.add_field(name="⚔️ Tu nuevo equipo", value=team_txt, inline=False)
                conf.set_footer(text="Usa /perfil para ver tu equipo en cualquier momento.")

                await inter.response.edit_message(embed=conf, view=None)

        return select_cb

    select.callback = make_select_cb(step, temp_team)
    view.add_item(select)

    # Skip button — keep current figure in this slot
    if step > 0:
        skip_btn = discord.ui.Button(
            label=f"Mantener posición actual",
            style=discord.ButtonStyle.secondary,
            custom_id=f"equip_skip_{step}",
            row=1,
        )
        def make_skip_cb(current_step: int, current_temp: list):
            async def skip_cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                # Keep original team value for this slot
                db2   = load_db()
                user2 = get_user(db2, inter.user.id)
                # Don't change this slot
                if current_step < 2:
                    await show_equip_menu(inter, user2, current_step + 1, current_temp, edit=True)
                else:
                    # Save as-is
                    user2["team"] = list(current_temp)
                    save_db(db2)
                    await inter.response.edit_message(
                        embed=discord.Embed(
                            title="✅ ¡Equipo guardado!",
                            description="Se mantuvieron las posiciones sin cambios para los slots no elegidos.",
                            color=0x2ecc71
                        ),
                        view=None
                    )
            return skip_cb
        skip_btn.callback = make_skip_cb(step, temp_team)
        view.add_item(skip_btn)

    if edit:
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


def register_commands(bot):
    """Registra los comandos slash de este módulo. Llamar desde main.py."""

    @bot.tree.command(name="registrar", description="Regístrate en el Androide del PvP y obtén 1000 monedas!")
    async def registrar(interaction: discord.Interaction):
        db = load_db()
        user = get_user(db, interaction.user.id)
        if user:
            await interaction.response.send_message(
                f"⚠️ Ya estás registrado como **{user['name']}** con **{user['coins']}** monedas!",
                ephemeral=True
            )
            return

        modal = discord.ui.Modal(title="¡Bienvenido al Androide del PvP!")

        name_input = discord.ui.TextInput(
            label="¿Cómo quieres que te conozca el bot?",
            placeholder="Ej: El Destructor, MegaGamer, etc.",
            max_length=32
        )
        modal.add_item(name_input)

        async def on_submit(modal_interaction: discord.Interaction):
            display_name = name_input.value.strip()
            create_user(db, modal_interaction.user.id, display_name)
            embed = discord.Embed(
                title="🎉 ¡Registro exitoso!",
                description=f"¡Bienvenido, **{display_name}**!\nEres conocido en la arena como el gran **{display_name}**.",
                color=0x2ecc71
            )
            embed.add_field(name="💰 Monedas iniciales", value="1,000 monedas", inline=True)
            embed.add_field(name="🎮 Siguiente paso", value="Usa `/tienda` para comprar tu primera figura!", inline=True)
            embed.set_footer(text="¡Que comience la batalla!")
            await modal_interaction.response.send_message(embed=embed)

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)


    @bot.tree.command(name="perfil", description="Mira tu perfil o el de otro usuario")
    @app_commands.describe(usuario="Usuario cuyo perfil ver (opcional)")
    async def perfil(interaction: discord.Interaction, usuario: discord.Member = None):
        db = load_db()
        target_member = usuario or interaction.user
        user = get_user(db, target_member.id)
        if not user:
            msg = "❌ Ese usuario no está registrado." if usuario else "❌ No estás registrado. Usa `/registrar` primero."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"👤 Perfil de {user['name']}",
            color=0x3498db
        )
        embed.set_thumbnail(url=target_member.display_avatar.url)

        lvl    = user.get("level", 1)
        xp     = user.get("xp", 0)
        sp     = user.get("skill_points", 0)
        rb     = user.get("rebirth_count", 0)
        rc     = user.get("recipe_count", 0)

        rebirth_str = f"🔄 **×{rb}**" if rb > 0 else "—"
        embed.add_field(name="💰 Monedas",      value=f"{user['coins']:,}",               inline=True)
        embed.add_field(name="🏆 Nivel",         value=f"{lvl}",                           inline=True)
        embed.add_field(name="⚡ XP",            value=f"{xp}/{xp_to_level_up(lvl)}",      inline=True)
        embed.add_field(name="✨ Skill Points",  value=f"**{sp}** SP disponibles",         inline=True)
        embed.add_field(name="🔄 Rebirths",      value=rebirth_str,                        inline=True)
        embed.add_field(name="🧑‍🍳 Recetas",      value=f"{rc} descubiertas",               inline=True)
        embed.add_field(name="✅ Victorias",     value=user.get("wins", 0),                inline=True)
        embed.add_field(name="❌ Derrotas",      value=user.get("losses", 0),              inline=True)
        embed.add_field(name="🎭 Figuras",       value=len(user.get("figures", [])),        inline=True)

        # Nodos activos del árbol
        tree = user.get("learn_tree", {})
        active_nodes = [nid for nid, lvl in tree.items() if lvl > 0]
        if active_nodes:
            node_names = [LEARN_TREE.get(nid, {}).get("name", nid) for nid in active_nodes]
            embed.add_field(name="📚 Árbol de aprendizaje", value=", ".join(node_names), inline=False)

        active = user.get("active_figure")
        if active:
            fig = FIGURES.get(active)
            if fig:
                embed.add_field(name="🌟 Figura activa", value=f"{fig['emoji']} {fig['name']}", inline=False)

        await interaction.response.send_message(embed=embed)


    @bot.tree.command(name="misfiguras", description="Ver tu colección de figuras o la de otro usuario")
    @app_commands.describe(usuario="Usuario cuyas figuras ver (opcional)")
    async def misfiguras(interaction: discord.Interaction, usuario: discord.Member = None):
        db = load_db()
        target_member = usuario or interaction.user
        user = get_user(db, target_member.id)
        if not user:
            msg = "❌ Ese usuario no está registrado." if usuario else "❌ Usa `/registrar` primero."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        figs = user.get("figures", [])
        if not figs:
            msg = f"📭 **{user['name']}** no tiene figuras." if usuario else "📭 No tienes figuras. Usa `/tienda` para comprar."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await show_figure_menu(interaction, user, figs, page=0, viewed_user_id=target_member.id)


    @bot.tree.command(name="equipar", description="Arma tu equipo de 3 figuras (frontal, centro, trasero)")
    async def equipar(interaction: discord.Interaction):
        db = load_db()
        user = get_user(db, interaction.user.id)
        if not user or not user.get("figures"):
            await interaction.response.send_message("❌ No tienes figuras. Compra en `/tienda`.", ephemeral=True)
            return

        await show_equip_menu(interaction, user, step=0)

