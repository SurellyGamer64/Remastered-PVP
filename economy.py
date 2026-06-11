"""
economy.py — Ingredientes, recetas, learn tree, logros, combine, rebirth, nivel de figuras.
"""
import random

INGREDIENTS = {
    "🦞": "Langosta",
    "🌶️": "Chile",
    "🧄": "Ajo",
    "🧅": "Cebolla",
    "🫙": "Salsa Secreta",
    "🍖": "Carne",
    "🌿": "Hierbas",
    "🥚": "Huevo",
    "🧀": "Queso",
    "🍫": "Chocolate",
    "🐮": "Santa Vaca",
    "🍝": "Spaghetti",
}

RECIPES = [
    {
        "name": "🦞🌶️🧄 Langosta Picante",
        "ingredients": ["🦞", "🌶️", "🧄"],
        "effect": "coins_boost",
        "value": 1.5,
        "desc": "¡+50% de monedas ganadas en batalla por 3 victorias!",
        "turns": 3,
    },
    {
        "name": "🦞🍖🧅 Estofado de Langosta",
        "ingredients": ["🦞", "🍖", "🧅"],
        "effect": "hp_boost",
        "value": 30,
        "desc": "¡+30 HP a todas las figuras de tu equipo en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🫙🌿 Langosta Gourmet",
        "ingredients": ["🦞", "🫙", "🌿"],
        "effect": "atk_boost",
        "value": 10,
        "desc": "¡+10 ATK a todas las figuras de tu equipo en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🥚🧀 Langosta con Queso",
        "ingredients": ["🦞", "🥚", "🧀"],
        "effect": "xp_boost",
        "value": 2.0,
        "desc": "¡XP x2 en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🍫🌿 Langosta Dulce",
        "ingredients": ["🦞", "🍫", "🌿"],
        "effect": "level_fig",
        "value": 1,
        "desc": "¡Sube 1 nivel a la figura frontal de tu equipo!",
        "turns": 1,
    },
    {
        "name": "🦞🧄🧅 Langosta Tradicional",
        "ingredients": ["🦞", "🧄", "🧅"],
        "effect": "coins_boost",
        "value": 1.3,
        "desc": "¡+30% de monedas por 2 victorias!",
        "turns": 2,
    },
    {
        "name": "🦞🍖🫙 Langosta a la Brasa",
        "ingredients": ["🦞", "🍖", "🫙"],
        "effect": "atk_boost",
        "value": 15,
        "desc": "¡+15 ATK a todas tus figuras en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🌶️🧀 Langosta Explosiva",
        "ingredients": ["🦞", "🌶️", "🧀"],
        "effect": "hp_boost",
        "value": 50,
        "desc": "¡+50 HP a todas las figuras de tu equipo en la próxima batalla!",
        "turns": 1,
    },
    # Recetas de 1 ingrediente
    {
        "name": "🦞🌶️ Langosta a la Brasa Rápida",
        "ingredients": ["🦞", "🌶️"],
        "effect": "atk_boost",
        "value": 5,
        "desc": "¡+5 ATK a tus figuras en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🍫 Langosta con Chocolate",
        "ingredients": ["🦞", "🍫"],
        "effect": "hp_boost",
        "value": 15,
        "desc": "¡+15 HP a tus figuras en la próxima batalla!",
        "turns": 1,
    },
    {
        "name": "🦞🌿 Langosta con Hierbas",
        "ingredients": ["🦞", "🌿"],
        "effect": "coins_boost",
        "value": 1.2,
        "desc": "¡+20% monedas en la próxima batalla!",
        "turns": 1,
    },
    # Receta épica (3 ingredientes específicos)
    {
        "name": "🦞🌶️🍖🧄 Langosta Suprema del Chef",
        "ingredients": ["🦞", "🌶️", "🍖", "🧄"],
        "effect": "all_boost",
        "value": 1,
        "desc": "¡+20 ATK, +30 HP y +50% monedas por 2 batallas! ¡La receta definitiva!",
        "turns": 2,
        "atk_bonus": 20,
        "hp_bonus": 30,
        "coins_mult": 1.5,
    },
    # Receta especial: Spaghetti de Langosta (requiere el ingrediente de Papyrus)
    {
        "name": "🦞🍝 Spaghetti de Langosta",
        "ingredients": ["🦞", "🍝"],
        "effect": "papyrus_special",
        "value": 1,
        "desc": (
            "¡La receta secreta de Papyrus! +25 ATK, +40 HP y +25 DEF a todas tus figuras "
            "en la próxima batalla. ¡NYEH HEH HEH!"
        ),
        "turns": 1,
        "atk_bonus": 25,
        "hp_bonus": 40,
        "def_bonus": 25,
    },
]

# Combinaciones fallidas (ingredientes sin sinergia)
FAILED_RECIPE_MSGS = [
    "💀 La langosta explotó. Mala idea mezclar eso.",
    "🤢 Eso huele horrible. Nadie en su sano juicio comería eso.",
    "😵 El plato resultante tiene vida propia. Lo tiraste.",
    "🔥 Se incendió la cocina. Ups.",
    "❓ Esto no es comida. Es algo más... ¿artístico?",
]

def find_recipe(selected_ings: list) -> dict | None:
    """Busca una receta que coincida con los ingredientes seleccionados."""
    selected_sorted = sorted(selected_ings)
    for recipe in RECIPES:
        recipe_sorted = sorted(recipe["ingredients"])
        if recipe_sorted == selected_sorted:
            return recipe
    # Buscar receta parcial (subset)
    for recipe in RECIPES:
        recipe_sorted = sorted(recipe["ingredients"])
        if all(i in selected_sorted for i in recipe_sorted) and len(recipe_sorted) <= len(selected_sorted):
            return recipe
    return None

TOTAL_RECIPES_FOR_EVENT = 40  # Recetas globales necesarias para Langosta Madre  # Recetas globales necesarias para Langosta Madre

# Contador global de recetas cocinadas
global_recipe_count = 0
lobster_madre_active = False

# Ingredientes que el jugador puede conseguir en batallas (se añaden a user["ingredients"])
BATTLE_INGREDIENT_DROP_CHANCE = 40  # 40% de probabilidad de conseguir ingrediente al ganar batalla

def give_battle_ingredient(user):
    """Da un ingrediente aleatorio al usuario (excepto langosta, que va por /lobster).
    Si Papyrus está en el equipo, 40% de probabilidad de obtener Spaghetti."""
    non_lobster = [k for k in INGREDIENTS if k != "🦞"]
    # Papyrus bonus: si está en el equipo, sube la prob de spaghetti
    team_keys = [user["figures"][i]["key"] for i in user.get("team", [])
                 if i is not None and i < len(user.get("figures", []))]
    if "papyrus" in team_keys and random.randint(1, 100) <= 40:
        ingredient = "🍝"
    else:
        ingredient = random.choice(non_lobster)
    if "ingredients" not in user:
        user["ingredients"] = {}
    user["ingredients"][ingredient] = user["ingredients"].get(ingredient, 0) + 1
    return ingredient

@bot.tree.command(name="ingredientes", description="Ve tus ingredientes de cocina actuales")
async def ingredientes_cmd(interaction: discord.Interaction):
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    ings = user.get("ingredients", {})
    # Langosta del inventario de figuras
    lobster_count = sum(1 for f in user.get("figures", []) if f["key"] == "lobster")
    embed = discord.Embed(title="🧑‍🍳 Tu despensa", color=0xe67e22)
    ing_str = ""
    if lobster_count:
        ing_str += f"🦞 Langosta x{lobster_count}\n"
    for emoji, amount in ings.items():
        name = INGREDIENTS.get(emoji, emoji)
        ing_str += f"{emoji} {name} x{amount}\n"
    embed.description = ing_str or "_Sin ingredientes. ¡Gana batallas o consigue una langosta!_"
    embed.set_footer(text=f"Recetas globales cocinadas: {global_recipe_count}/{TOTAL_RECIPES_FOR_EVENT}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cook", description="Cocina una receta combinando una langosta con hasta 3 ingredientes")
async def cook_cmd(interaction: discord.Interaction):
    global global_recipe_count, lobster_madre_active
    db = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return
    lobster_idx = next((i for i, f in enumerate(user.get("figures", [])) if f["key"] == "lobster"), None)
    if lobster_idx is None:
        await interaction.response.send_message("❌ Necesitas al menos una 🦞 Langosta. Consíguela con `/lobster`.", ephemeral=True)
        return
    ings = user.get("ingredients", {})
    available = {k: v for k, v in ings.items() if v > 0}
    if not available:
        await interaction.response.send_message("❌ No tienes ingredientes. ¡Gana batallas para conseguir algunos!", ephemeral=True)
        return

    ing_options = [
        discord.SelectOption(label=f"{INGREDIENTS.get(emoji, emoji)} x{amt}", value=emoji)
        for emoji, amt in available.items()
    ]
    state = {"selected": [], "user_id": interaction.user.id}

    def make_embed():
        selected_str = " + ".join(state["selected"]) if state["selected"] else "_Ninguno aún_"
        return discord.Embed(
            title="🧑‍🍳 ¡Hora de cocinar!",
            description=f"🦞 Langosta + **{selected_str}**\n\nElige hasta 3 ingredientes y luego **Cocinar**:",
            color=0xe67e22
        )

    def make_view():
        view = discord.ui.View(timeout=60)

        if len(state["selected"]) < 3:
            sel = discord.ui.Select(placeholder="Añadir ingrediente...", options=ing_options, max_values=1)
            async def add_ingredient(si: discord.Interaction):
                if si.user.id != state["user_id"]:
                    await si.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                state["selected"].append(sel.values[0])
                await si.response.edit_message(embed=make_embed(), view=make_view())
            sel.callback = add_ingredient
            view.add_item(sel)

        if len(state["selected"]) > 0:
            undo_btn = discord.ui.Button(label="↩️ Quitar último", style=discord.ButtonStyle.secondary)
            async def undo(ui: discord.Interaction):
                if ui.user.id != state["user_id"]:
                    await ui.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                state["selected"].pop()
                await ui.response.edit_message(embed=make_embed(), view=make_view())
            undo_btn.callback = undo
            view.add_item(undo_btn)

            cook_btn = discord.ui.Button(label="🍳 ¡Cocinar!", style=discord.ButtonStyle.success)
            async def do_cook(ci: discord.Interaction):
                if ci.user.id != state["user_id"]:
                    await ci.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                global global_recipe_count, lobster_madre_active
                db2 = load_db()
                user2 = get_user(db2, ci.user.id)
                lb_idx = next((i for i, f in enumerate(user2.get("figures", [])) if f["key"] == "lobster"), None)
                if lb_idx is None:
                    await ci.response.edit_message(content="❌ Ya no tienes langosta.", embed=None, view=None)
                    return
                ings2 = user2.get("ingredients", {})
                for ing in state["selected"]:
                    if ings2.get(ing, 0) <= 0:
                        await ci.response.edit_message(content=f"❌ Ya no tienes {ing}.", embed=None, view=None)
                        return
                # Consumir langosta e ingredientes
                user2["figures"].pop(lb_idx)
                for ing in state["selected"]:
                    ings2[ing] -= 1
                user2["ingredients"] = ings2
                # Buscar receta
                matched = None
                for recipe in RECIPES:
                    if set(recipe["ingredients"]) == set(["🦞"] + state["selected"]):
                        matched = recipe
                        break
                # Verificar hojas de receta conocidas
                if not matched:
                    for idx in user2.get("recipe_sheets", []):
                        if idx < len(RECIPES):
                            recipe = RECIPES[idx]
                            if set(recipe["ingredients"]) == set(["🦞"] + state["selected"]):
                                matched = recipe
                                break
                global_recipe_count += 1
                user2["recipe_count"] = user2.get("recipe_count", 0) + 1
                # Logros de receta
                new_achs = check_achievements(user2, {"action": "cook"})
                if new_achs:
                    ach_names = [ACHIEVEMENTS[a]["name"] for a in new_achs]
                    await interaction.followup.send(f"🏅 ¡Logro desbloqueado! {' · '.join(ach_names)}", ephemeral=True)
                # XP al jugador por cocinar
                user2["xp"] = user2.get("xp", 0) + 20
                _check_player_levelup(user2)
                if matched:
                    if "buffs" not in user2:
                        user2["buffs"] = []
                    user2["buffs"].append({"effect": matched["effect"], "value": matched["value"], "turns": matched["turns"]})
                    if matched["effect"] == "level_fig":
                        team = user2.get("team", [])
                        if team and team[0] is not None and team[0] < len(user2.get("figures", [])):
                            fig = user2["figures"][team[0]]
                            if fig.get("level", 1) < FIGURE_LEVEL_MAX:
                                fig["level"] = fig.get("level", 1) + 1
                    recipe_name = matched["name"]
                    result_desc = matched["desc"]
                    color = 0x2ecc71
                else:
                    recipe_name = "💀 Receta Fallida"
                    result_desc = "Los ingredientes no tienen sinergia entre sí... Se arruinó la comida. No obtienes ningún beneficio.\n\n💡 _Tip: explora para encontrar Hojas de Receta._"
                    color = 0xe74c3c
                save_db(db2)
                embed2 = discord.Embed(title=f"{'✅' if matched else '❌'} {recipe_name}", description=result_desc, color=color)
                embed2.set_footer(text=f"Recetas globales: {global_recipe_count}/{TOTAL_RECIPES_FOR_EVENT}")
                await ci.response.edit_message(embed=embed2, view=None)
                if global_recipe_count >= TOTAL_RECIPES_FOR_EVENT and not lobster_madre_active:
                    lobster_madre_active = True
                    await trigger_lobster_madre(ci.channel)
            cook_btn.callback = do_cook
            view.add_item(cook_btn)

        return view

    await interaction.response.send_message(embed=make_embed(), view=make_view(), ephemeral=True)

# ─── LANGOSTA MADRE (evento global) ───────────────────────────────────────────
LOBSTER_MADRE_HP = 300000
lobster_madre_state = {}

async def trigger_lobster_madre(channel):
    """Inicia el evento global de la Langosta Madre."""
    global lobster_madre_state
    lobster_madre_state = {
        "hp": LOBSTER_MADRE_HP,
        "max_hp": LOBSTER_MADRE_HP,
        "participants": {},  # user_id -> damage dealt
        "active": True,
    }
    embed = discord.Embed(
        title="🦞🦞🦞 ¡APARECE LA LANGOSTA MADRE! 🦞🦞🦞",
        description=(
            "¡40 recetas han sido cocinadas! ¡La **LANGOSTA MADRE** ha despertado!\n\n"
            "❤️ **HP:** 300,000\n⚔️ **ATK:** 70 | 🛡️ **DEF:** 30\n\n"
            "**¡Tienes 60 segundos para unirte!** Todos los jugadores que se unan atacarán juntos."
        ),
        color=0xe74c3c
    )
    view = discord.ui.View(timeout=60)
    join_btn = discord.ui.Button(label="⚔️ ¡UNIRME AL ATAQUE!", style=discord.ButtonStyle.danger, custom_id="join_lobster")
    async def join_cb(inter: discord.Interaction):
        uid = inter.user.id
        if not lobster_madre_state.get("active"):
            await inter.response.send_message("❌ El evento ya terminó.", ephemeral=True)
            return
        if uid in lobster_madre_state["participants"]:
            await inter.response.send_message("✅ Ya estás en el ataque!", ephemeral=True)
            return
        lobster_madre_state["participants"][uid] = 0
        await inter.response.send_message(f"⚔️ ¡<@{uid}> se unió al ataque! Ya somos **{len(lobster_madre_state['participants'])}** guerreros!", ephemeral=False)
    join_btn.callback = join_cb
    view.add_item(join_btn)
    msg = await channel.send(embed=embed, view=view)
    await asyncio.sleep(60)
    # ¡A pelear!
    await run_lobster_madre_battle(channel, msg)

async def run_lobster_madre_battle(channel, msg):
    """Ejecuta la batalla contra la Langosta Madre con todos los participantes."""
    global lobster_madre_active
    participants = list(lobster_madre_state.get("participants", {}).keys())
    if not participants:
        await channel.send("🦞 Nadie se unió al ataque... La Langosta Madre se retira victoriosa.")
        lobster_madre_active = False
        return

    lm_hp = lobster_madre_state["hp"]
    lm_max = lobster_madre_state["max_hp"]
    lm_atk = 70
    all_skills_pool = [sk for skills in FIGURE_SKILLS.values() for sk in skills
                       if sk["type"] not in ("consumed_fury", "revive_team", "ban_hammer", "drain_fill", "lobster")]
    round_num = 0

    while lm_hp > 0 and participants:
        round_num += 1
        log = [f"**Ronda {round_num}**"]

        # Jugadores atacan
        db = load_db()
        total_dmg = 0
        for uid in participants[:]:
            user = get_user(db, uid)
            if not user:
                participants.remove(uid)
                continue
            # Ataque básico del jugador
            atk = random.randint(15, 40)
            lm_hp = max(0, lm_hp - atk)
            total_dmg += atk
            lobster_madre_state["participants"][uid] = lobster_madre_state["participants"].get(uid, 0) + atk
        log.append(f"⚔️ Los {len(participants)} guerreros hacen **{total_dmg}** daño total! (🦞 HP: {lm_hp:,}/{lm_max:,})")

        if lm_hp <= 0:
            break

        # Langosta Madre ataca con habilidad aleatoria
        skill_used = random.choice(all_skills_pool)
        dmg_to_all = random.randint(20, lm_atk)
        log.append(f"🦞 **¡LANGOSTA MADRE** usa **{skill_used['name']}**! ¡{dmg_to_all} daño a todos!")

        bar_len = 20
        filled = int((lm_hp / lm_max) * bar_len)
        hp_bar = "🟥" * filled + "⬛" * (bar_len - filled)

        embed = discord.Embed(
            title="🦞 LANGOSTA MADRE",
            description=f"{hp_bar}\n❤️ **{lm_hp:,}/{lm_max:,} HP**\n\n" + "\n".join(log),
            color=0xe74c3c if lm_hp > lm_max * 0.5 else 0x95a5a6
        )
        await msg.edit(embed=embed)
        await asyncio.sleep(3)

        if lm_hp <= 0:
            break

    # Resultado
    lobster_madre_active = False
    if lm_hp <= 0:
        db = load_db()
        rewards_text = []
        for uid, dmg in lobster_madre_state["participants"].items():
            user = get_user(db, uid)
            if user:
                coins_reward = 500 + (dmg // 10)
                user["coins"] = user.get("coins", 0) + coins_reward
                rewards_text.append(f"<@{uid}>: +{coins_reward}🪙 ({dmg} daño total)")
        save_db(db)
        embed = discord.Embed(
            title="🏆 ¡LANGOSTA MADRE DERROTADA!",
            description="¡Increíble! ¡Los guerreros lograron derrotar a la Langosta Madre!\n\n" + "\n".join(rewards_text[:10]),
            color=0x2ecc71
        )
    else:
        embed = discord.Embed(
            title="💀 La Langosta Madre sobrevivió...",
            description=f"¡La LANGOSTA MADRE sobrevivió con **{lm_hp:,} HP** restantes! ¡Mejor suerte la próxima vez!",
            color=0xe74c3c
        )
    await channel.send(embed=embed)


def _make_stat_up_view(fig_data: dict, fig_key: str, user_data: dict, user_id: int, db) -> discord.ui.View:
    """Crea la view de selección de stat para el level up. Sin async."""
    view = discord.ui.View(timeout=60)
    stats = [("hp","❤️ HP"),("attack","⚔️ ATK"),("defense","🛡️ DEF"),("speed","⚡ VEL")]
    for stat_key, stat_label in stats:
        btn = discord.ui.Button(label=f"{stat_label} +2", style=discord.ButtonStyle.primary, custom_id=f"su_{stat_key}_{fig_key}")
        async def cb(inter: discord.Interaction, sk=stat_key, fk=fig_key, uid=user_id):
            if inter.user.id != uid:
                await inter.response.send_message("❌ No es tu elección.", ephemeral=True)
                return
            db2 = load_db()
            u2 = get_user(db2, uid)
            target = next((f for f in u2.get("figures",[]) if f.get("key")==fk and f.get("pending_stat_up",0)>0), None)
            if not target:
                await inter.response.edit_message(content="✅ Ya procesado.", embed=None, view=None)
                return
            if "stat_ups" not in target: target["stat_ups"] = {}
            target["stat_ups"][sk] = target["stat_ups"].get(sk,0) + 2
            target["pending_stat_up"] = target.get("pending_stat_up",0) - 1
            save_db(db2)
            fig_base = FIGURES.get(fk,{})
            ok_embed = discord.Embed(
                title=f"✅ ¡+2 {sk.upper()} a {fig_base.get('name',fk)}!",
                description=f"Tu figura ahora tiene **+{target['stat_ups'].get(sk,0)}** de bonus en {sk}.",
                color=0x2ecc71
            )
            await inter.response.edit_message(embed=ok_embed, view=None)
            # Si quedan más pendientes, mostrar otro menú
            if target.get("pending_stat_up",0) > 0:
                db3 = load_db()
                u3 = get_user(db3, uid)
                t2 = next((f for f in u3.get("figures",[]) if f.get("key")==fk and f.get("pending_stat_up",0)>0), None)
                if t2:
                    v2 = _make_stat_up_view(t2, fk, u3, uid, db3)
                    again_embed = discord.Embed(
                        title=f"⬆️ ¡{fig_base.get('emoji','')} {fig_base.get('name',fk)} subió otro nivel!",
                        description="Elige otro stat:",
                        color=0xf1c40f
                    )
                    await inter.followup.send(embed=again_embed, view=v2)
        btn.callback = cb
        view.add_item(btn)
    return view

# ============================================================
#  SISTEMA DE LEVEL UP CON ELECCIÓN DE STAT (figuras)
# ============================================================
FIGURE_LEVEL_MAX = 30
FIGURE_LEVEL_MAX = 30

def check_figure_levelup(fig_data, interaction_hook=None):
    """
    Verifica si una figura subió de nivel y devuelve (leveled_up, new_level).
    fig_data es el dict de la figura del usuario (con key, level, xp, stat_ups).
    """
    leveled = False
    while fig_data.get("level", 1) < FIGURE_LEVEL_MAX:
        needed = xp_to_level_up(fig_data.get("level", 1))
        if fig_data.get("xp", 0) >= needed:
            fig_data["xp"] -= needed
            fig_data["level"] = fig_data.get("level", 1) + 1
            fig_data["pending_stat_up"] = fig_data.get("pending_stat_up", 0) + 1
            leveled = True
        else:
            break
    return leveled

async def prompt_stat_up(interaction: discord.Interaction, fig_data: dict, fig_key: str, db):
    """Muestra un menú para elegir qué stat subir al subir de nivel."""
    pending = fig_data.get("pending_stat_up", 0)
    if pending <= 0:
        return
    fig_base  = FIGURES.get(fig_key, {})
    fig_name  = fig_base.get("name", fig_key)
    fig_emoji = fig_base.get("emoji", "🎭")
    lvl = fig_data.get("level", 1)

    embed = discord.Embed(
        title=f"⬆️ ¡{fig_emoji} {fig_name} subió al nivel {lvl}!",
        description="Elige **una mejora permanente**:",
        color=0xf1c40f
    )

    # Opciones: +10 HP | +5 ATK | +5 VEL | +10 Barra de carga
    STAT_OPTIONS = [
        ("hp",         "❤️ +10 Vida",          "hp",      10),
        ("attack",     "⚔️ +5 Ataque",          "attack",  5),
        ("speed",      "⚡ +5 Velocidad",        "speed",   5),
        ("energy_cap", "🔋 +10 Barra de carga", "energy_cap", 10),
    ]

    view = discord.ui.View(timeout=60)
    user_id = interaction.user.id

    def make_callback(stat_key, stat_label, stat_field, stat_amt):
        async def callback(inter: discord.Interaction):
            if inter.user.id != user_id:
                await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                return
            db2 = load_db()
            u2 = get_user(db2, user_id)
            if not u2:
                await inter.response.send_message("❌ Error al cargar tu perfil.", ephemeral=True)
                return
            target = next((f for f in u2.get("figures", []) if f.get("key") == fig_key and f.get("pending_stat_up", 0) > 0), None)
            if not target:
                await inter.response.edit_message(content="✅ Ya fue procesado.", embed=None, view=None)
                return
            if "stat_ups" not in target:
                target["stat_ups"] = {}
            target["stat_ups"][stat_field] = target["stat_ups"].get(stat_field, 0) + stat_amt
            target["pending_stat_up"] = target.get("pending_stat_up", 0) - 1
            save_db(db2)
            result_embed = discord.Embed(
                title=f"✅ {fig_emoji} {fig_name} — ¡Mejora aplicada!",
                description=f"**{stat_label}** permanente! (Nv.{target.get('level',1)})\nTotal bonus {stat_field}: **+{target['stat_ups'].get(stat_field,0)}**",
                color=0x2ecc71
            )
            await inter.response.edit_message(embed=result_embed, view=None)
            if target.get("pending_stat_up", 0) > 0:
                await asyncio.sleep(1)
                await prompt_stat_up(inter, target, fig_key, db2)
        return callback

    for stat_key, stat_label, stat_field, stat_amt in STAT_OPTIONS:
        btn = discord.ui.Button(label=stat_label, style=discord.ButtonStyle.primary)
        btn.callback = make_callback(stat_key, stat_label, stat_field, stat_amt)
        view.add_item(btn)

    try:
        if hasattr(interaction, 'followup'):
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.channel.send(embed=embed, view=view)
    except Exception:
        pass

# ============================================================
#  LEADERBOARDS EXPANDIDOS
# ============================================================
@bot.tree.command(name="leaderboard", description="Ver los rankings del servidor")
async def leaderboard_cmd(interaction: discord.Interaction):
    view = discord.ui.View(timeout=60)

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
@bot.tree.command(name="logros", description="Ver tus logros conseguidos y los que faltan")
async def logros_cmd(interaction: discord.Interaction):
    db   = load_db()
    user = get_user(db, interaction.user.id)
    if not user:
        await interaction.response.send_message("❌ Usa `/registrar` primero.", ephemeral=True)
        return

    uid    = interaction.user.id
    earned = set(user.get("achievements", []))
    total  = len(ACHIEVEMENTS)
    done   = len(earned)

    # Construir lista completa: conseguidos primero, luego pendientes
    items = []
    for aid, ach in ACHIEVEMENTS.items():
        if aid in earned:
            items.append(("done", aid, ach))
    for aid, ach in ACHIEVEMENTS.items():
        if aid not in earned:
            items.append(("pending", aid, ach))

    PAGE_SIZE = 8  # fields por página (bien dentro del límite de 25)
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)

    def build_logros_embed(page: int) -> discord.Embed:
        embed = discord.Embed(
            title=f"🏅 Logros — {user['name']}",
            description=f"**{done}/{total}** conseguidos  |  Página {page+1}/{total_pages}",
            color=0xf1c40f
        )
        start = page * PAGE_SIZE
        for status, aid, ach in items[start:start + PAGE_SIZE]:
            if status == "done":
                embed.add_field(name=f"✅ {ach['name']}", value=ach["desc"], inline=True)
            else:
                if ach.get("secret"):
                    embed.add_field(name="🔒 ???", value="*Logro secreto*", inline=True)
                else:
                    embed.add_field(name=f"⬜ {ach['name']}", value=ach["desc"], inline=True)
        embed.set_footer(text="✅ Conseguido  ·  ⬜ Pendiente  ·  🔒 Secreto")
        return embed

    def build_logros_view(page: int) -> discord.ui.View:
        view = discord.ui.View(timeout=120)
        prev_btn = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary, disabled=page == 0)
        next_btn = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary, disabled=page >= total_pages - 1)

        def make_nav(new_page):
            async def cb(inter: discord.Interaction):
                if inter.user.id != uid:
                    await inter.response.send_message("❌ No es tu menú.", ephemeral=True)
                    return
                await inter.response.edit_message(
                    embed=build_logros_embed(new_page),
                    view=build_logros_view(new_page)
                )
            return cb

        prev_btn.callback = make_nav(page - 1)
        next_btn.callback = make_nav(page + 1)
        view.add_item(prev_btn)
        view.add_item(next_btn)
        return view

    await interaction.response.send_message(
        embed=build_logros_embed(0),
        view=build_logros_view(0),
        ephemeral=True
    )

# ── RECOMPENSAS VARIABLES DEL IMPOSTOR NEGRO (7v3) ──────────────────────────
IMPOSTOR_REWARDS = {
    3: {"coins": 4000, "recipe_sheets": 2, "auto_levels": 2,  "xp": 600,  "achievement": True},
    4: {"coins": 2500, "recipe_sheets": 1, "auto_levels": 1,  "xp": 450,  "achievement": False},
def _register_kill_for_love(owner_id, battle=None):
    """Registra un kill en la DB del jugador para el LOVE Check de Sans (permanente)."""
    if not owner_id:
        return
    try:
        db = load_db()
        user = get_user(db, owner_id)
        if user:
            user["total_kills"] = user.get("total_kills", 0) + 1
            save_db(db)
    except Exception:
        pass

def _get_love_kills(battle, attacker) -> int:
    """Devuelve el total de kills del atacante: kills en batalla + kills globales en DB."""
    battle_kills = attacker.get("total_kills", 0)
    # Intentar leer kills globales si hay owner_id
    owner_id = attacker.get("owner_id")
    if owner_id:
        try:
            db = load_db()
            user = get_user(db, owner_id)
            if user:
                return user.get("total_kills", 0)
        except Exception:
            pass
    return battle_kills

def _apply_recipe_buffs(user_data: dict, team: list, db) -> str | None:
    """Aplica los buffs de receta activos del usuario a su equipo y los consume.
    Devuelve 'good'/'bad' si había receta papyrus_special, None si no."""
    buffs = user_data.get("buffs", [])
    if not buffs:
        return None
    remaining = []
    papyrus_result = None
    # El resultado de papyrus se tira UNA sola vez para todo el equipo
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
                fig["hp"]     = fig["hp"] + val
                fig["max_hp"] = fig["max_hp"] + val
            elif effect == "atk_boost":
                fig["atk"] = fig.get("atk", 0) + val
            elif effect in ("all_boost",):
                fig["atk"]    = fig.get("atk", 0) + b.get("atk_bonus", 0)
                hp_b          = b.get("hp_bonus", 0)
                fig["hp"]     = fig["hp"] + hp_b
                fig["max_hp"] = fig["max_hp"] + hp_b
            elif effect == "papyrus_special":
                sign = 1 if papyrus_good else -1
                fig["atk"]    = max(1, fig.get("atk", 0) + sign * b.get("atk_bonus", 25))
                hp_b          = b.get("hp_bonus", 40)
                def_b         = b.get("def_bonus", 25)
                fig["hp"]     = max(1, fig["hp"] + sign * hp_b)
                fig["max_hp"] = max(1, fig["max_hp"] + sign * hp_b)
                fig["defense"]= max(0, fig.get("defense", 0) + sign * def_b)
        if effect in ("coins_boost", "xp_boost"):
            remaining.append(b)
        elif turns > 1:
            remaining.append({**b, "turns": turns - 1})
    user_data["buffs"] = remaining
    return papyrus_result

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