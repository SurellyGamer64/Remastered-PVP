"""
bosses.py — BOT_ROSTER y figuras/habilidades exclusivas de jefes.
Importar después de figures.py para poder añadir entradas a FIGURES y FIGURE_SKILLS.
"""
from figures import FIGURES, FIGURE_SKILLS

BOT_ROSTER = [
    {
        "id": "facil",
        "name": "🪆 Maniquí de Combate",
        "desc": "Solo está ahí para recibir golpes. No te pongas nervioso.",
        "difficulty": 1,
        "team": ["agustoloco", "agustoloco", "agustoloco"],
        "level": 1,
        "hp_mult": 1.0, "atk_mult": 1.0, "energy_bonus": 0,
        "reward_coins": 80,
        "reward_xp": 30,
    },
    {
        "id": "medio",
        "name": "💼 Trabajador Ocupado",
        "desc": "Está peleando en su hora de almuerzo. Tiene algo de experiencia.",
        "difficulty": 2,
        "team": ["gamer64", "agustoloco", "agustoloco"],
        "level": 3,
        "hp_mult": 1.1, "atk_mult": 1.1, "energy_bonus": 0,
        "reward_coins": 150,
        "reward_xp": 60,
    },
    {
        "id": "dificil",
        "name": "🎮 Jugador Tryhard",
        "desc": "Lleva 14 horas jugando sin dormir. Un rival serio.",
        "difficulty": 3,
        "team": ["sonic", "gamer64", "agustoloco"],
        "level": 6,
        "hp_mult": 1.2, "atk_mult": 1.2, "energy_bonus": 5,
        "reward_coins": 250,
        "reward_xp": 100,
    },
    {
        "id": "experto",
        "name": "👾 Glitch",
        "desc": "Un OC malvado que rompe las reglas del juego. Muy pocos lo han derrotado.",
        "difficulty": 4,
        "team": ["sonic", "alex", "gamer64"],
        "level": 10,
        "hp_mult": 1.4, "atk_mult": 1.3, "energy_bonus": 8,
        "reward_coins": 400,
        "reward_xp": 150,
    },
    {
        "id": "nino_random",
        "name": "👦 Niño Random",
        "desc": "No sabes su nombre. No sabe el tuyo. Pero está MUY enojado.",
        "difficulty": 5,
        "team": ["boss_nino1", "boss_nino2", "boss_nino3"],
        "level": 13,
        "hp_mult": 1.5, "atk_mult": 1.4, "energy_bonus": 10,
        "reward_coins": 550,
        "reward_xp": 200,
        "is_boss": True,
    },
    {
        "id": "paper_mario",
        "name": "📄 Paper Mario",
        "desc": "Es delgado como papel pero golpea como un libro de texto.",
        "difficulty": 6,
        "team": ["boss_paper1", "boss_paper2", "boss_paper3"],
        "level": 15,
        "hp_mult": 1.6, "atk_mult": 1.5, "energy_bonus": 12,
        "reward_coins": 700,
        "reward_xp": 280,
        "is_boss": True,
    },
    {
        "id": "steve",
        "name": "⛏️ Steve",
        "desc": "Lleva sobreviviendo desde el 2011. Ha visto cosas que tú no puedes imaginar.",
        "difficulty": 7,
        "team": ["boss_steve1", "boss_steve2", "boss_steve3"],
        "level": 17,
        "hp_mult": 1.8, "atk_mult": 1.6, "energy_bonus": 15,
        "reward_coins": 850,
        "reward_xp": 350,
        "is_boss": True,
    },
    {
        "id": "impostor_negro",
        "name": "🔪 BLACK IMPOSTOR",
        "desc": "7 impostores. Tú y 3 figuras. ¿Puedes con todos?",
        "difficulty": 8,
        "team": ["boss_impostor_red","boss_impostor_green","boss_impostor_white",
                 "boss_impostor_maroon","boss_impostor_gray","boss_impostor_pink","blackout"],
        "level": 19,
        "hp_mult": 2.0, "atk_mult": 1.8, "energy_bonus": 18,
        "reward_coins": 4000,
        "reward_xp": 420,
        "is_boss": True,
        "special_7v3": True,
    },
    {
        "id": "jefe",
        "name": "💀 El Antifas Antifasado",
        "desc": "El jefe supremo. Nadie sabe de dónde vino. Sus figuras no se consiguen en la tienda.",
        "difficulty": 9,
        "team": ["antifas", "roblox_boss", "gamer64"],
        "level": 20,
        "hp_mult": 2.2, "atk_mult": 2.0, "energy_bonus": 20,
        "reward_coins": 1500,
        "reward_xp": 600,
        "is_boss": True,
    },
]

# ── Figuras exclusivas de los nuevos jefes ────────────────────────────────────

# Niño Random
FIGURES["boss_nino1"] = {"name":"Niño Enfadado","emoji":"😡","rarity":"legendario","price":0,"hp":200,"attack":38,"defense":20,"speed":40,"image":""}
FIGURES["boss_nino2"] = {"name":"Niño con Palo","emoji":"🏏","rarity":"legendario","price":0,"hp":180,"attack":45,"defense":15,"speed":35,"image":""}
FIGURES["boss_nino3"] = {"name":"Niño Llorón","emoji":"😭","rarity":"legendario","price":0,"hp":160,"attack":30,"defense":25,"speed":30,"image":""}
FIGURE_SKILLS["boss_nino1"] = [
    {"name":"Rabieta",       "cost":30, "type":"damage",       "power":25, "stun":True,  "desc":"El niño hace una rabieta y golpea al rival aturdido."},
    {"name":"QUIERO ESO YA","cost":60, "type":"team_atk_buff", "power":0,  "atk_buff":20,"desc":"Exige lo que quiere — todo el equipo gana +20 ATK."},
    {"name":"¡ME LO DICES A MÍ!","cost":100,"type":"damage",  "power":70, "aoe":True,"aoe_secondary_power":40,"desc":"Explota de furia y golpea a todo el equipo rival."},
]
FIGURE_SKILLS["boss_nino2"] = [
    {"name":"Palazo",        "cost":30, "type":"damage",  "power":30, "desc":"Un palazo directo sin contemplaciones."},
    {"name":"Palazo x2",     "cost":60, "type":"damage",  "power":55, "aoe":True,"aoe_secondary_power":25,"desc":"Gira el palo y golpea a todos los rivales."},
    {"name":"SUPER PALAZO",  "cost":100,"type":"damage",  "power":85, "stun":True,"stun_turns":2,"desc":"Un golpe devastador que aturde 2 turnos."},
]
FIGURE_SKILLS["boss_nino3"] = [
    {"name":"Llanto",        "cost":30, "type":"heal",         "power":40, "team_heal":True,"team_heal_power":20,"desc":"Sus lágrimas curan al equipo."},
    {"name":"Llamar a Mamá", "cost":60, "type":"team_atk_buff","power":0,  "atk_buff":15,  "desc":"Llama a mamá — el equipo se motiva con +15 ATK."},
    {"name":"Berrinche Total","cost":100,"type":"dot",         "power":15,"dot_turns":4,   "desc":"Berrinche imparable: 15 daño/turno x4 al rival."},
]

# Paper Mario
FIGURES["boss_paper1"] = {"name":"Paper Mario","emoji":"📄","rarity":"legendario","price":0,"hp":220,"attack":42,"defense":35,"speed":38,"image":"","passive":"papelemental","passive2":"timing"}
FIGURES["boss_paper2"] = {"name":"Paper Bowser","emoji":"🐢","rarity":"legendario","price":0,"hp":280,"attack":50,"defense":45,"speed":20,"image":""}
FIGURES["boss_paper3"] = {"name":"Paper Peach","emoji":"👸","rarity":"legendario","price":0,"hp":190,"attack":35,"defense":30,"speed":42,"image":""}
FIGURE_SKILLS["boss_paper1"] = [
    {
        "name": "Paper Hammer",
        "cost": 30,
        "type": "damage",
        "power": 28,
        "desc": "Saca su martillo de papel y golpea. 28 de daño.",
    },
    {
        "name": "Object Menu",
        "cost": 60,
        "type": "object_menu",
        "desc": (
            "Paper Mario saca su menú de objetos. Elige uno:\n"
            "📄 Estrella de Papel — cura 50 HP al activo y 25 HP al equipo.\n"
            "🌸 Flor de Fuego — 28 de daño + burning 10 turnos.\n"
            "❄️ Flor de Hielo — 28 de daño + frozen 2 turnos (stun + 3 daño/turno).\n"
            "💥 Bloque POW — 15 de daño a todos los rivales + stun 2 turnos.\n"
            "🐢 Cola — 19 de daño + fuerza cambio de figura rival."
        ),
        "items": [
            {
                "key": "paper_star",
                "label": "📄 Estrella de Papel",
                "type": "heal",
                "power": 50,
                "team_heal": True,
                "team_heal_power": 25,
            },
            {
                "key": "fire_flower",
                "label": "🌸 Flor de Fuego",
                "type": "damage",
                "power": 28,
                "dot": True,
                "dot_power": 5,
                "dot_turns": 10,
            },
            {
                "key": "ice_flower",
                "label": "❄️ Flor de Hielo",
                "type": "damage",
                "power": 28,
                "frozen": True,
                "frozen_turns": 2,
                "frozen_dot": 3,
            },
            {
                "key": "pow_block",
                "label": "💥 Bloque POW",
                "type": "damage",
                "power": 15,
                "aoe": True,
                "aoe_secondary_power": 15,
                "stun": True,
                "stun_turns": 2,
            },
            {
                "key": "tail",
                "label": "🐢 Cola",
                "type": "damage",
                "power": 19,
                "force_switch": True,
                "force_switch_turns": 1,
            },
        ],
    },
    {
        "name": "Ally Help",
        "cost": 100,
        "type": "ally_help",
        "desc": (
            "¿Necesitas ayuda? ¡Presiona X para obtener un consejo!\n"
            "Elige un aliado:\n"
            "🧙 Kamek — 24 daño + stun 2t (17% fallo).\n"
            "🎪 Bowser Jr — 15 DOT x3t (18% fallo).\n"
            "🔬 Prof. Toad — 15 daño + 20 monedas (16% fallo).\n"
            "🐉 Bowser — 30 daño + burning 5t (15% fallo).\n"
            "💣 Bombi — 24 daño + 10 splash + stun 2t (16% fallo).\n"
            "🌸 Olivia — +40 HP a todos los aliados."
        ),
        "allies": [
            {
                "key": "kamek",
                "label": "🧙 Kamek",
                "type": "damage",
                "power": 24,
                "stun": True,
                "stun_turns": 2,
                "fail_chance": 0.17,
            },
            {
                "key": "bowser_jr",
                "label": "🎪 Bowser Jr",
                "type": "dot",
                "dot_power": 15,
                "dot_turns": 3,
                "fail_chance": 0.18,
            },
            {
                "key": "prof_toad",
                "label": "🔬 Professor Toad",
                "type": "damage",
                "power": 15,
                "coin_bonus": 20,
                "fail_chance": 0.16,
            },
            {
                "key": "bowser",
                "label": "🐉 Bowser",
                "type": "damage",
                "power": 30,
                "dot": True,
                "dot_power": 6,
                "dot_turns": 5,
                "fail_chance": 0.15,
            },
            {
                "key": "bombi",
                "label": "💣 Bombi",
                "type": "damage",
                "power": 24,
                "aoe_splash": 10,
                "stun": True,
                "stun_turns": 2,
                "fail_chance": 0.16,
            },
            {
                "key": "olivia",
                "label": "🌸 Olivia",
                "type": "team_heal",
                "power": 40,
                "fail_chance": 0.0,
            },
        ],
    },
]
FIGURE_SKILLS["boss_paper2"] = [
    {"name":"Lanzallamas",   "cost":30,"type":"damage","power":32,"aoe":True,"aoe_secondary_power":18,"desc":"Escupe fuego a todos los rivales."},
    {"name":"Koopa Shell",   "cost":60,"type":"damage","power":50,"force_switch":True,"force_switch_turns":2,"desc":"Lanza su caparazón que bloquea a una figura 2 turnos."},
    {"name":"BOWSER PAPER FURY","cost":100,"type":"damage","power":100,"desc":"La ira definitiva de Bowser en formato papel."},
]
FIGURE_SKILLS["boss_paper3"] = [
    {"name":"Bofetada Real", "cost":30,"type":"damage","power":22,"stun":True,"desc":"Una bofetada elegante que aturde al rival."},
    {"name":"Curación Real", "cost":60,"type":"heal",  "power":60,"team_heal":True,"team_heal_power":30,"desc":"Peach cura generosamente a todo el equipo."},
    {"name":"Parasol Real",  "cost":100,"type":"retribution","power":0,"desc":"El parasol devuelve la mitad del daño recibido."},
]

# Steve
FIGURES["boss_steve1"] = {"name":"Steve","emoji":"⛏️","rarity":"legendario","price":0,"hp":300,"attack":48,"defense":50,"speed":25,"image":""}
FIGURES["boss_steve2"] = {"name":"Creeper","emoji":"💚","rarity":"legendario","price":0,"hp":200,"attack":55,"defense":20,"speed":30,"image":""}
FIGURES["boss_steve3"] = {"name":"Enderman","emoji":"🌑","rarity":"legendario","price":0,"hp":250,"attack":45,"defense":35,"speed":45,"image":""}
FIGURE_SKILLS["boss_steve1"] = [
    {"name":"Picar con Pico", "cost":30,"type":"damage",       "power":30, "desc":"Steve pica con su pico de diamante."},
    {"name":"Crafting Rápido","cost":60,"type":"team_atk_buff","power":0,"atk_buff":20,"desc":"Steve craftea armas para todo el equipo: +20 ATK."},
    {"name":"TNT",            "cost":100,"type":"damage",      "power":80,"aoe":True,"aoe_secondary_power":50,"desc":"Steve coloca TNT y vuela a todo el equipo rival."},
]
FIGURE_SKILLS["boss_steve2"] = [
    {"name":"Sssss...",       "cost":30,"type":"dot",     "power":12,"dot_turns":3,"desc":"El Creeper empieza a sisear... 12 daño/turno x3."},
    {"name":"¡BOOM!",         "cost":60,"type":"damage",  "power":70,"aoe":True,"aoe_secondary_power":40,"desc":"EXPLOTA haciendo daño masivo a todo el equipo."},
    {"name":"Mega Explosión", "cost":100,"type":"consumed_fury","power":0,"splash_dmg":30,"desc":"La explosión más grande que has visto. Mata al activo + 30 splash."},
]
FIGURE_SKILLS["boss_steve3"] = [
    {"name":"Teletransporte", "cost":30,"type":"damage",  "power":25,"stun":True,"desc":"Aparece detrás del rival y golpea."},
    {"name":"Bloque de Ender","cost":60,"type":"parry",   "power":0,"parry_dmg_pct":35,"desc":"Bloquea el ataque y contraataca con el 35% del HP rival."},
    {"name":"Ojos de Ender",  "cost":100,"type":"damage", "power":90,"force_switch":True,"force_switch_turns":3,"desc":"Sus ojos lanzan un rayo que bloquea a la figura 3 turnos."},
]

# ── FNF VS IMPOSTOR BOSS FIGHT ──────────────────────────────────────────────

# RED IMPOSTOR
FIGURES["boss_impostor_red"] = {"name":"Red Impostor","emoji":"🔴","rarity":"legendario","price":0,"hp":240,"attack":50,"defense":30,"speed":35,"image":""}
FIGURE_SKILLS["boss_impostor_red"] = [
    {
        "name": "Impostor's Pose",
        "cost": 30,
        "type": "team_atk_buff",
        "power": 0,
        "atk_buff": 10,
        "team_buff": False,  # solo a sí mismo
        "desc": "Red hace una pose. Aunque parezca chistosa, da +10 ATK acumulable.",
    },
    {
        "name": "Knife Cut",
        "cost": 60,
        "type": "damage",
        "power": 20,
        "desc": "Red hace un corte certero directo. 20 de daño.",
    },
    {
        "name": "Gun Shot",
        "cost": 100,
        "type": "damage",
        "power": 50,
        "dot": True,
        "dot_turns": 2,
        "dot_power": 8,
        "dot_type": "bleeding",
        "desc": "Red dispara a la figura más cercana. 50 de daño + bleeding 2 turnos.",
    },
]

# GREEN IMPOSTOR — Forma 1 (pre-Ejected)
FIGURES["boss_impostor_green"] = {"name":"Green Impostor","emoji":"🟢","rarity":"legendario","price":0,"hp":241,"attack":51,"defense":31,"speed":36,"image":"","passive":"green_new_form"}
FIGURE_SKILLS["boss_impostor_green"] = [
    {
        "name": "Keep the Act",
        "cost": 30,
        "type": "keep_the_act",
        "power": 0,
        "bar_bonus": 50,
        "cant_attack_turns": 2,
        "desc": "Green finge ser tripulante. +50 barra, pero no puede atacar por 2 turnos.",
    },
    {
        "name": "Lights Out",
        "cost": 60,
        "type": "lights_out",
        "power": 0,
        "stun_turns": 3,
        "self_atk_buff": 10,
        "self_atk_buff_turns": 2,
        "desc": "Green apaga las luces. Stun 3T a amigos Y enemigos. Green recibe +10 ATK 2 turnos.",
    },
    {
        "name": "Ejected",
        "cost": 100,
        "type": "ejected",
        "power": 0,
        "return_turns": 18,
        "desc": "Green y la figura activa enemiga 'mueren'. Si en 18 turnos no acabas con el resto, ambos vuelven... Green con nueva forma.",
    },
]
# GREEN IMPOSTOR — Forma 2 (post-Ejected)
FIGURES["boss_impostor_green2"] = {"name":"Green Impostor II","emoji":"🟢","rarity":"mítico","price":0,"hp":241,"attack":51,"defense":31,"speed":36,"image":""}
FIGURE_SKILLS["boss_impostor_green2"] = [
    {
        "name": "Sky Throw",
        "cost": 30,
        "type": "damage",
        "power": 20,
        "aoe": True,
        "aoe_secondary_power": 10,
        "desc": "Green sube al aire y se lanza en picada. 20 dmg al activo + 10 a sus aliados.",
    },
    {
        "name": "Flying Monstrosity",
        "cost": 60,
        "type": "flying_monstrosity",
        "power": 0,
        "hold_turns": 5,
        "desc": "Green agarra una figura enemiga. Ambos quedan bloqueados 5 turnos. Si sobrevive, la figura muere.",
    },
    {
        "name": "Final Act",
        "cost": 100,
        "type": "consumed_fury",
        "power": 0,
        "splash_dmg": 40,
        "desc": "Green agarra a todas las figuras enemigas y termina con todo. Mata al activo + 40 a los otros 2. Green muere.",
    },
]

# WHITE IMPOSTOR
FIGURES["boss_impostor_white"] = {"name":"White Impostor","emoji":"⚪","rarity":"legendario","price":0,"hp":260,"attack":42,"defense":52,"speed":59,"image":""}
FIGURE_SKILLS["boss_impostor_white"] = [
    {
        "name": "Hide and Seek",
        "cost": 30,
        "type": "hide_and_seek",
        "power": 30,
        "hide_turns": 2,
        "desc": "White se esconde. Fuerza cambio de figura aliada. En 2 turnos vuelve con 30 de daño a un enemigo.",
    },
    {
        "name": "Fast Kill",
        "cost": 60,
        "type": "fast_kill",
        "power": 60,
        "charges_needed": 3,
        "desc": "Igual que Black. Aprendió bien de su compañero. 3 usos seguidos, 60 de daño.",
    },
    {
        "name": "TroubleMaker",
        "cost": 100,
        "type": "damage",
        "power": 40,
        "aoe": True,
        "aoe_secondary_power": 20,
        "dot": True,
        "dot_turns": 20,
        "dot_power": 5,
        "dot_type": "bleeding",
        "desc": "White ataca a todos. 40 al activo + 20 a los secundarios + bleeding 20 turnos a todos.",
    },
]

# MAROON IMPOSTOR — Forma 1
FIGURES["boss_impostor_maroon"] = {"name":"Maroon Impostor","emoji":"🟤","rarity":"legendario","price":0,"hp":250,"attack":40,"defense":50,"speed":45,"image":"","passive":"maroon_lol_you_thought"}
FIGURE_SKILLS["boss_impostor_maroon"] = [
    {
        "name": "Rage Baiting",
        "cost": 30,
        "type": "rage_baiting",
        "power": 0,
        "chance": 50,
        "atk_debuff_turns": 3,
        "atk_debuff": 10,
        "stun_turns": 3,
        "desc": "50%: el oponente hace -10 ATK 3T. 50%: Maroon stun al oponente 3T.",
    },
    {
        "name": "Bait Knife",
        "cost": 60,
        "type": "damage",
        "power": 50,
        "dot": True,
        "dot_turns": 4,
        "dot_power": 8,
        "dot_type": "bleeding",
        "desc": "Un cuchillo... no, una pistola. 50 de daño + bleeding 4 turnos.",
    },
    {
        "name": "Volcano Comeback",
        "cost": 100,
        "type": "ejected",
        "power": 0,
        "return_turns": 18,
        "second_form_key": "boss_impostor_maroon2",
        "desc": "Maroon y la figura activa enemiga 'mueren'. Si en 18 turnos no acabas, vuelven. Maroon con nueva forma.",
    },
]
# MAROON IMPOSTOR — Forma 2
FIGURES["boss_impostor_maroon2"] = {"name":"Maroon Impostor II","emoji":"🟤","rarity":"mítico","price":0,"hp":250,"attack":40,"defense":50,"speed":45,"image":""}
FIGURE_SKILLS["boss_impostor_maroon2"] = [
    {
        "name": "No more Games",
        "cost": 30,
        "type": "damage",
        "power": 25,
        "stun": True,
        "stun_turns": 3,
        "desc": "Maroon se lanza y remata con una tackleada voladora. 25 dmg + stun 3T.",
    },
    {
        "name": "Nah Just Kidding...",
        "cost": 60,
        "type": "damage",
        "power": 30,
        "stun": True,
        "stun_turns": 5,
        "desc": "Finge 5 ataques en distintas direcciones, luego ataca de verdad. 30 dmg + stun 5T.",
    },
    {
        "name": "LULZ GIT GUT XD",
        "cost": 100,
        "type": "lulz_git_gut",
        "power": 30,
        "hp_drain_pct": 80,
        "self_dmg": 30,
        "desc": "Ataca a una figura bajándole el 80% de su vida. Pero Maroon pierde 30 HP.",
    },
]

# GRAY IMPOSTOR
FIGURES["boss_impostor_gray"] = {"name":"Gray Impostor","emoji":"🩶","rarity":"legendario","price":0,"hp":275,"attack":54,"defense":39,"speed":42,"image":""}
FIGURE_SKILLS["boss_impostor_gray"] = [
    {
        "name": "Childhood Trauma",
        "cost": 30,
        "type": "damage",
        "power": 35,
        "bar_drain": -20,   # negativo = recarga barra propia
        "desc": "Gray no mira atrás. 35 de daño + +20 a su barra de carga.",
    },
    {
        "name": "Maniatic Laugh",
        "cost": 60,
        "type": "revive_team",
        "power": 20,
        "revive_hp_pct": 50,
        "heal_alive": 20,
        "desc": "Gray se ríe malvadamente. Revive figuras muertas con 50% HP y cura 20 a las vivas.",
    },
    {
        "name": "Consumed By Fury",
        "cost": 100,
        "type": "consumed_fury",
        "power": 0,
        "splash_dmg": 40,
        "desc": "Aprendió de su padre muy bien. Mata al activo enemigo + 40 a los otros 2. Gray muere.",
    },
]

# PINK IMPOSTOR
FIGURES["boss_impostor_pink"] = {"name":"Pink Impostor","emoji":"🩷","rarity":"legendario","price":0,"hp":250,"attack":15,"defense":40,"speed":40,"image":""}
FIGURE_SKILLS["boss_impostor_pink"] = [
    {
        "name": "Friendship",
        "cost": 30,
        "type": "heal_team_self",
        "power": 20,
        "desc": "Pink cura a todas las figuras aliadas +20 HP.",
    },
    {
        "name": "Convincment",
        "cost": 60,
        "type": "convincment",
        "power": 0,
        "desc": "Pink y una figura enemiga 'llegan a un acuerdo'. Ambas mueren instantáneamente.",
    },
    {
        "name": "Friendship Shield",
        "cost": 100,
        "type": "friendship_shield",
        "power": 0,
        "shield_turns": 10,
        "shield_hits": 5,
        "desc": "Pink genera un escudo que dura 10 turnos y absorbe 5 ataques.",
    },
]

# Actualizar boss fight del Impostor Negro con el elenco completo
# (se usa en BOT_BATTLES, se actualiza abajo)

# ── FIGURAS EXCLUSIVAS DEL JEFE (versiones potenciadas) ─────────────────────
FIGURES["antifas"] = {
    "name": "Antifas Antifasado",
    "emoji": "🦝",
    "rarity": "legendario",
    "price": 0,
    "hp": 235,
    "attack": 40,
    "defense": 38,
    "speed": 39,
    "image": "",
}
FIGURE_SKILLS["antifas"] = [
    {
        "name": "Heroic Pose",
        "cost": 30,
        "type": "team_atk_buff",   # buff de ATK acumulable al equipo
        "power": 0,
        "atk_buff": 15,            # +15 ATK acumulable, se consume al atacar
        "team_buff": True,
        "desc": "Pose heroica: +15 ATK a todas las figuras aliadas. Acumulable. Se consume al atacar.",
    },
    {
        "name": "Throwable Bomb",
        "cost": 60,
        "type": "dot",             # daño por turnos
        "power": 10,
        "dot_turns": 3,            # dura 3 turnos
        "dot_stackable": True,     # acumulable
        "desc": "Lanza una bomba venenosa. 10 de daño cada turno por 3 turnos. ¡Acumulable!",
    },
    {
        "name": "Dark Hole",
        "cost": 100,
        "type": "damage",
        "power": 15,
        "force_switch": True,
        "force_switch_turns": 3,
        "desc": "Invoca un agujero negro que manda a una figura enemiga al vacío por 3 turnos.",
    },
]

# --- Roblox (disponible en tienda Y usado por el jefe con stats superiores) ---
FIGURES["roblox"] = {
    "name": "Roblox",
    "emoji": "🔳",
    "rarity": "mítico",
    "price": 2003,
    "hp": 230,           # stats de tienda
    "attack": 35,
    "defense": 45,
    "speed": 35,
    "image": "https://tr.rbxcdn.com/30DAY-Avatar-310966282D3529E36976BF6B07B1DC90-Png/720/720/Avatar/Webp/noFilter",
}
FIGURES["roblox_boss"] = {
    "name": "Roblox",
    "emoji": "🔳",
    "rarity": "mítico",
    "price": 0,          # no aparece en tienda
    "hp": 270,           # stats del jefe
    "attack": 50,
    "defense": 45,
    "speed": 35,
    "image": "https://tr.rbxcdn.com/30DAY-Avatar-310966282D3529E36976BF6B07B1DC90-Png/720/720/Avatar/Webp/noFilter",
}
_roblox_skills = [
    {
        "name": "Bad Update",
        "cost": 30,
        "type": "bad_update",      # daño aleatorio a enemigos + cura aliados
        "power": 0,
        "desc": "Mala actualización: daña 4/6/8 a cada enemigo y cura la mitad a cada aliado.",
    },
    {
        "name": "Shut Down",
        "cost": 60,
        "type": "damage",
        "power": 20,
        "stun": True,
        "stun_turns": 3,           # stun extendido 3 turnos
        "desc": "Apaga los servidores. Aturde a la figura enemiga activa por 3 turnos.",
    },
    {
        "name": "Ban Hammer",
        "cost": 100,
        "type": "ban_hammer",      # 50/50: mata al enemigo O a un aliado
        "power": 0,
        "desc": "50% de chances de eliminar a la figura enemiga activa. El otro 50%... mata a una aliada.",
    },
]
FIGURE_SKILLS["roblox"] = _roblox_skills
FIGURE_SKILLS["roblox_boss"] = _roblox_skills

IMPOSTOR_REWARDS = {
    3: {"coins": 4000, "recipe_sheets": 2, "auto_levels": 2,  "xp": 600,  "achievement": True},
    4: {"coins": 2500, "recipe_sheets": 1, "auto_levels": 1,  "xp": 450,  "achievement": False},
    5: {"coins": 1500, "recipe_sheets": 0, "auto_levels": 0,  "xp": 300,  "achievement": False},
    6: {"coins": 500,  "recipe_sheets": 0, "auto_levels": 0,  "xp": 100,  "achievement": False},
    7: {"coins": 0,    "recipe_sheets": 0, "auto_levels": 0,  "xp": 0,    "achievement": False},
}

