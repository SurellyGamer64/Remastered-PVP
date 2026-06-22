"""
figures.py — Definición de todas las figuras, habilidades, constantes de rareza y helpers de stats.
"""
import random

# ============================================================
#  FIGURAS
# ============================================================
FIGURES = {
    "gamer64": {
        "name": "Gamer64",
        "emoji": "<:GamerNew:1511129412681076797>",
        "rarity": "raro",
        "price": 640,
        "hp": 142,
        "attack": 34,
        "defense": 38,
        "speed": 41,
        "image": "https://i.imgur.com/gl2UZZ3.png",  # Pon la URL pública de GamerNew.png aquí
    },
    "sonic": {
        "name": "Sonic",
        "emoji": "🦔",
        "rarity": "épico",
        "price": 1991,
        "hp": 200,
        "attack": 40,
        "defense": 42,
        "speed": 60,
        "image": "https://preview.redd.it/my-first-fanart-drew-the-sonic-adventure-pose-v0-ca4ogp5vra4c1.jpg?width=1080&crop=smart&auto=webp&s=34f3148da3adadf91ecfdfc4d2c218a137a0213f",
    },
    "alex": {
        "name": "Alex",
        "emoji": "<:Klin:1511129452036362372>",
        "rarity": "legendario",
        "price": 215,
        "hp": 250,
        "attack": 14,
        "defense": 30,
        "speed": 50,
        "image": "https://i.imgur.com/iJctAhj.png",  # Pon la URL aquí
    },
    "ringmaster": {
        "name": "Caine",
        "emoji": "🦷",
        "rarity": "legendario",
        "price": 1998,
        "hp": 230,
        "attack": 35,
        "defense": 40,
        "speed": 30,
        "image": "https://preview.redd.it/caine-villain-or-misunderstood-v0-covbmlxtsnqg1.png?width=860&format=png&auto=webp&s=8a3b7c21e6aa8adb851d88643994bd495064ca97",
        "passive": "torment",   # Pasiva: WHY DO YOU PEOPLE TORMENT ME
    },
    "michibug": {
        "name": "MichiBug",
        "emoji": "🦊",
        "rarity": "legendario",
        "price": 900,
        "hp": 170,
        "attack": 22,
        "defense": -2,
        "speed": 8,
        "image": "https://i.imgur.com/gPMrvOs.png",
    },
    "tails": {
        "name": "Tails",
        "emoji": "🦊",
        "rarity": "épico",
        "price": 1992,
        "hp": 140,
        "attack": 23,
        "defense": 20,
        "speed": 20,
        "image": "https://static.wikia.nocookie.net/sstp/images/6/6a/Tails.png/revision/latest?cb=20130319112956",
    },
    "hatred": {
        "name": "1x1x1x1",
        "emoji": "🤬",
        "rarity": "legendario",
        "price": 1250,
        "hp": 245,
        "attack": 30,
        "defense": 25,
        "speed": 25,
        "image": "https://pbs.twimg.com/media/Gxe4SOdWcAArEZN.jpg",
    },
    "chicken": {
        "name": "Shedletsky",
        "emoji": "🐔",
        "rarity": "mítico",
        "price": 2006,
        "hp": 210,
        "attack": 45,
        "defense": 30,
        "speed": 30,
        "image": "https://i.namu.wiki/i/uQrQ4Z8Ff1fNhIln9_uMjuG2-ehRjdvFjBoNQso5fohpP8WclZo-YF4QpQIfjqj6Y6hhYDmTlR-xatYm2PFNOg.webp",
    },
    "blackout": {
        "name": "Black Impostor",
        "emoji": "🔪",
        "rarity": "mítico",
        "price": 2021,
        "hp": 275,
        "attack": 52,
        "defense": 38,
        "speed": 35,
        "image": "https://static.wikia.nocookie.net/the-ultimate-evil/images/b/bc/Black_Impostor_FINALE_V4.png/revision/latest/scale-to-width/360?cb=20230309224128",
    },
    "homero": {
        "name": "Homero Simpson",
        "emoji": "🍩",
        "rarity": "mítico",
        "price": 2024,
        "hp": 100,
        "attack": 18,
        "defense": 10,
        "speed": 7,
        "image": "https://media.gq.com.mx/photos/5be9eeb284b96e68a794165c/master/pass/11_cosas_que_le_preguntariamos_a_homero_simpson_2494.jpg",
    },
    "jevil": {
        "name": "Jevil",
        "emoji": "🃏",
        "rarity": "mítico",
        "price": 2018,
        "hp": random.randint(270, 290),
        "attack": random.randint(21, 24),
        "defense": random.randint(20, 26),
        "speed": 30,
        "image": "https://images.steamusercontent.com/ugc/15345781204781413326/7D2F8F47C62958FAFD73E4B8528D601AE3D018E9/?imw=637&imh=358&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
        "passive": "true_god_of_chaos",
    },
    "annoying_dog": {
        "name": "Annoying Dog",
        "emoji": "🐶",
        "rarity": "mítico",
        "price": 1991,
        "hp": 290,
        "attack": random.randint(20, 25),
        "defense": random.randint(10, 20),
        "speed": random.randint(21, 32),
        "image": "https://i.scdn.co/image/ab6761610000e5ebcce32307d0f312e8faf01bae",
        "secret_misfiguras": True,
    },
    "santa_vaca": {
        "name": "SANTA VACA!",
        "emoji": "🐮",
        "rarity": "mítico",
        "price": 0,          # Solo con /holy
        "hp": 1234567890,
        "attack": 1234567890,
        "defense": 0,
        "speed": 1234567890,
        "image": "https://emblibrary.com/cdn/shop/files/M33422.jpg?v=1750188343&width=1214",
    },
    "lobster": {
        "name": "Lobster",
        "emoji": "🦞",
        "rarity": "común",
        "price": 0,        # Solo se obtiene con /lobster
        "hp": 1,
        "attack": 1,
        "defense": 1,
        "speed": 1,
        "image": "https://images.contentstack.io/v3/assets/bltcedd8dbd5891265b/blt6f01003267cbf97f/664cbd77d94e39430f4c7cd1/lobster-guide-hero.jpg?q=70&width=3840&auto=webp",
    },
    "agustoloco": {
        "name": "AgustoLoco",
        "emoji": "🚬",
        "rarity": "épico",
        "price": 110,
        "hp": 120,
        "attack": 20,
        "defense": 18,
        "speed": 16,
        "image": "https://i.imgur.com/ZEPFJmF.png",
    },
    "007n7": {
        "name": "007n7",
        "emoji": "🍔",
        "rarity": "epico",
        "price": 500,
        "hp": 210,
        "attack": 21,
        "defense": 32,
        "speed": 30,
        "image": "https://i.redd.it/b5tes4g0w75f1.jpeg",
    },
    "kidd": {
        "name": "c00lkidd",
        "emoji": "😎",
        "rarity": "legendario",
        "price": 900,
        "hp": 220,
        "attack": 40,
        "defense": 30,
        "speed": 52,
        "image": "https://media.printables.com/media/prints/42d1eb40-be5b-4dbe-aebf-e11a8c2538b9/images/11589036_18ec24f9-1577-4fac-94f1-e62f2d551df7_12dfa319-2d71-4dfc-a36b-85c25efc5e83/thumbs/inside/1280x960/jpg/artworks-ugygzb9kdqny96ww-9vz6cq-t1080x1080.webp",
    },
    "twotime": {
        "name": "Two Time",
        "emoji": "🗡️",
        "rarity": "epico",
        "price": 500,
        "hp": 170,
        "attack": 25,
        "defense": 25,
        "speed": 30,
        "image": "https://image-cdn-ak.spotifycdn.com/image/ab67706c0000da84d1891be46091133c6e496f49",
    },
    "noli": {
        "name": "Noli",
        "emoji": "✨",
        "rarity": "legendario",
        "price": 1100,
        "hp": 211,
        "attack": 25,
        "defense": 20,
        "speed": 30,
        "image": "https://static.wikia.nocookie.net/forsaken2024/images/2/26/NoliChangedRender.png/revision/latest?cb=20260423180748",
        "passive": "hallucinations",
    },
    "guest1337": {
        "name": "Guest1337",
        "emoji": "👊",
        "rarity": "epico",
        "price": 500,
        "hp": 215,
        "attack": 30,
        "defense": 25,
        "speed": 30,
        "image": "https://static.wikia.nocookie.net/forsaken2024/images/thumb/f/f2/Guest_1337_Render.png/220px-Guest_1337_Render.png",
    },
    "noob": {
        "name": "Noob",
        "emoji": "😃",
        "rarity": "raro",
        "price": 450,
        "hp": 200,
        "attack": 20,
        "defense": 20,
        "speed": 20,
        "image": "https://static.wikia.nocookie.net/forsaken2024/images/7/7c/Noobnewest.png/revision/latest?cb=20260417122231",
    },
    "chance": {
        "name": "Chance",
        "emoji": "🔫",
        "rarity": "legendario",
        "price": 777,
        "hp": 200,
        "attack": 27,
        "defense": 37,
        "speed": 37,
        "image": "https://static.wikia.nocookie.net/lgbt-characters/images/b/bd/Chance_%28Forsaken%29.png/revision/latest/thumbnail/width/360/height/450?cb=20260320010117",
    },
    "johndoe": {
        "name": "John Doe",
        "emoji": "💢",
        "rarity": "legendario",
        "price": 1120,
        "hp": 202,
        "attack": 30,
        "defense": 40,
        "speed": 30,
        "image": "https://i.redd.it/p5y051gk6mve1.jpeg",
    },
    "janedoe": {
        "name": "Jane Doe",
        "emoji": "🪓",
        "rarity": "epico",
        "price": 800,
        "hp": 170,
        "attack": 35,
        "defense": 30,
        "speed": 35,
        "image": "https://static.wikia.nocookie.net/forsaken2024/images/4/4e/JaneDoerender.png/revision/latest/smart/width/300/height/300?cb=20260308103449",
    },
    "donmanzanas": {
        "name": "Don Manzanas",
        "emoji": "🍎",
        "rarity": "común",
        "price": 400,
        "hp": 160,
        "attack": 19,
        "defense": 40,
        "speed": 41,
        "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQitxgXjvgIbadMnhQmNWfrG9uAdy7UC4Th_g&s",
    },
    "kirby": {
        "name": "Kirby",
        "emoji": "🌸",
        "rarity": "legendario",
        "price": 1992,
        "hp": 245,
        "attack": 35,
        "defense": 28,
        "speed": 45,
        "image": "https://upload.wikimedia.org/wikipedia/en/e/e5/Kirby_%28character%29.png",
        "passive": "kirby_transform",
    },
    "sans": {
        "name": "Sans",
        "emoji": "<:SANS:1511160523775807588>",
        "rarity": "mítico",
        "price": 2015,
        "hp": 1,
        "attack": 1,
        "defense": 1,
        "speed": 1,
        "image": "https://static.wikia.nocookie.net/undertale/images/1/1b/Sans_battle.png",
        "passive": "sans_miss",
    },
    "papyrus": {
        "name": "Papyrus",
        "emoji": "<:NYEH:1511554121482899616>",
        "rarity": "legendario",
        "price": 1154,
        "hp": 280,
        "attack": 18,
        "defense": 20,
        "speed": 30,
        "image": "https://preview.redd.it/my-3d-interpretation-of-papyrus-from-undertale-all-made-v0-nab5n5ucfwpa1.png?width=1080&crop=smart&auto=webp&s=56dc099ee82d768490b1579826f2684091f873ab",
    },
    "flowey": {
        "name": "Flowey",
        "emoji": "<:Flowey:1511554261996277830>",
        "rarity": "legendario",
        "price": 1500,
        "hp": 190,
        "attack": 19,
        "defense": 10,
        "speed": 35,
        "image": "https://cdn.displate.com/artwork/380x270/2024-11-05/1b25b88f-3cd6-4f28-a47c-4bcfe464fd11.jpg",
        "passive": "omega_evolution",
    },
    "omega_flowey": {
        "name": "OMEGA FLOWEY",
        "emoji": "<:OMEGA:1511553995578019910>",
        "rarity": "legendario",
        "price": 0,   # no comprable, solo se obtiene al evolucionar Flowey
        "hp": 299,
        "attack": 29,
        "defense": 25,
        "speed": 35,
        "image": "https://static.wikitide.net/atrociousgameplaywiki/f/f0/Omega_Flowey.png",
    },
    # ── FIGURAS SECRETAS (solo en /secret-store) ─────────────────
    "og_gamer64": {
        "name": "OG GAMER 64",
        "emoji": "<a:Parpadeo:1511129354745413695>",
        "rarity": "Mítico",
        "price": 99999,
        "hp": 235,
        "attack": 30,
        "defense": 40,
        "speed": 32,
        "phases": 4,
        "image": "https://i.postimg.cc/y8zY3Hyg/Normal.png",
        "passive": "og_gamer_phases",
    },
    "holy_cow": {
        "name": "Holy Cow",
        "emoji": "🐄",
        "rarity": "Mítico",
        "price": 88888,
        "hp": 500,
        "attack": 50,
        "defense": 50,
        "speed": 50,
        "image": "https://emblibrary.com/cdn/shop/files/M33422.jpg?v=1750188343&width=1214",
    },
    "ryu": {
        "name":    "Ryu",
        "emoji":   "<:Ryu:1518604002206416947>",
        "rarity":  "mítico",
        "price":   1987,
        "hp":      255,
        "attack":  50,
        "defense": 30,
        "speed":   32,
        "image":   "https://i.redd.it/bb2ik9eddzrc1.jpeg",
    },
}

# Figuras exclusivas de la tienda secreta
SECRET_FIGURES = ["og_gamer64", "holy_cow"]
SECRET_CODE = "Th3-0g-G4m3R-64-I5-0P"
SECRET_OWNER_ID = 1236293193893412975
# Usuarios que han desbloqueado la tienda secreta (en memoria, se resetea al reiniciar)
secret_store_unlocked = set([SECRET_OWNER_ID])

# ============================================================
#  CONSTANTES DE RAREZA
# ============================================================
RARITY_COLOR = {
    "común": 0x95a5a6,
    "raro": 0x3498db,
    "épico": 0x9b59b6,
    "epico": 0x9b59b6,
    "legendario": 0xf1c40f,
    "Legendario": 0xf1c40f,
    "mítico": 0xff0000,
    "Mítico": 0xff0000,
}

RARITY_STARS = {
    "común": "⚪",
    "raro": "🔵",
    "épico": "🟣",
    "epico": "🟣",
    "legendario": "🌟",
    "Legendario": "🌟",
    "mítico": "🔱",
    "Mítico": "🔱",
}

# ============================================================
#  CONSTANTES DE PROGRESIÓN
# ============================================================
XP_PER_WIN  = 50
XP_PER_LOSS = 15
COINS_WIN   = 100
COINS_LOSS  = 20

def xp_to_level_up(level: int) -> int:
    return 100 * level

def apply_level_bonus(base_stat: int, level: int) -> int:
    """Aplica un bonus de stats según el nivel de la figura (+5% por nivel)."""
    if base_stat < 0:
        return base_stat
    return int(base_stat * (1 + (level - 1) * 0.05))

def get_figure_level(figure_data: dict) -> int:
    return figure_data.get("level", 1)

def get_figure_xp(figure_data: dict) -> int:
    return figure_data.get("xp", 0)

FIGURE_SKILLS = {
    "gamer64": [
        {
            "name": "Heroic Pose",
            "cost": 30,
            "type": "team_atk_buff",
            "power": 0,
            "atk_buff": 10,            # +10 daño a todas las habilidades aliadas, acumulable
            "team_buff": True,
            "desc": "Gamer64 hace una pose heroica, dando +10 de daño a todas las habilidades de las figuras aliadas. ¡Acumulable!",
        },
        {
            "name": "Cannon Arm",
            "cost": 60,
            "type": "damage",
            "power": 15,
            "stun": True,
            "desc": "Transforma su brazo en un cañón y dispara un misil. Aturde al oponente 1 turno.",
        },
        {
            "name": "Regeneración",
            "cost": 100,
            "type": "heal",
            "power": 10,
            "team_heal": True,
            "team_heal_power": 12,
            "desc": "Cura a Gamer64 y a sus compañeros de batalla.",
        },
    ],
    "alex": [
        {
            "name": "Parry",
            "cost": 30,
            "type": "parry",        # Tipo especial: contraataca si el rival ataca este turno
            "power": 0,             # Sin daño directo
            "parry_flat_bonus": 10, # Contraataca con el daño del ataque + 10
            "desc": "Alex hace un parry. Si el rival ataca este turno, lo contraataca con su propio daño +10.",
        },
        {
            "name": "Carga Estelar",
            "cost": 60,
            "type": "buff",         # Tipo buff: potencia el siguiente ataque
            "power": 0,
            "atk_buff": 15,         # Suma 15 de ATK temporal al siguiente golpe
            "desc": "La estrella de Alex brilla y carga su poder. Su próximo golpe hará más daño.",
        },
        {
            "name": "Esfera Luminosa",
            "cost": 100,
            "type": "damage",
            "power": 14,
            "force_switch": True,
            "force_switch_turns": 2,  # Ciega al rival 2 turnos
            "desc": "Alex lanza una esfera de luz que explota, cegando al rival por 2 turnos y haciéndole daño.",
        },
    ],
    "ringmaster": [
        {
            "name": "Grab a Bite",
            "cost": 30,
            "type": "damage",
            "power": 10,
            "stun": True,
            "stun_turns": 2,           # stun extendido 2 turnos
            "self_heal": 5,            # Caine se cura 5 HP (mitad del daño)
            "desc": "Caine abre la boca, muerde al rival, se cura 5 HP y lo aturde 2 turnos.",
        },
        {
            "name": "Digital Hallucinations",
            "cost": 60,
            "type": "damage",
            "power": 25,
            "force_switch": True,
            "force_switch_turns": 3,   # fuerza cambio de figura
            "desc": "Caine finge que son alucinaciones digitales, daña al rival y lo fuerza a cambiar de figura.",
        },
        {
            "name": "Retributional Ringmaster",
            "cost": 100,
            "type": "retribution",     # contraataca con la mitad del daño recibido durante 1 turno
            "power": 0,
            "retrib_turns": 1,
            "desc": "Caine recibe el daño de una figura y luego libera su enfado devolviendo la mitad.",
        },
    ],
    "michibug": [
        {
            "name": "Counter",
            "cost": 30,
            "type": "michi_counter",   # parry especial: devuelve mitad del daño, 20% de que el rival no ataque
            "power": 0,
            "evade_chance": 20,        # 20% de que el rival pierda su turno
            "desc": "Michi se pone en pose defensiva. Si el rival ataca, devuelve la mitad del daño. 20% de que el rival ni ataque.",
        },
        {
            "name": "Glitch Manipulation",
            "cost": 60,
            "type": "glitch_dmg",      # daño aleatorio 2-45
            "power": 0,
            "min_dmg": 2,
            "max_dmg": 45,
            "desc": "Michi canaliza su poder glitch y lanza un objeto aleatorio al oponente. Daño: 2 a 45.",
        },
        {
            "name": "Corruption",
            "cost": 100,
            "type": "corruption",      # copia una habilidad aleatoria del juego y la ejecuta
            "power": 0,
            "desc": "Michi acumula poder glitch y ejecuta una habilidad aleatoria de cualquier figura del juego.",
        },
    ],
    "tails": [
        {
            "name": "Robot Buddy",
            "cost": 30,
            "type": "dot",
            "power": 10,
            "dot_turns": 3,
            "dot_stackable": True,
            "desc": "Tails lanza un robot al oponente. Hace 10 de daño cada turno por 3 turnos.",
        },
        {
            "name": "Intelectual",
            "cost": 60,
            "type": "team_atk_buff",
            "power": 0,
            "atk_buff": 10,
            "team_buff": True,
            "desc": "Tails usa su intelecto para dar +10 ATK a todas las figuras aliadas. ¡Acumulable!",
        },
        {
            "name": "Fly Away",
            "cost": 100,
            "type": "fly_away",        # Tails y el rival quedan bloqueados 3 turnos
            "power": 0,
            "fly_turns": 3,
            "desc": "Tails agarra al rival y lo lleva volando. Ambas figuras quedan bloqueadas 3 turnos.",
        },
    ],
    "hatred": [
        {
            "name": "Mass Infection",
            "cost": 30,
            "type": "damage",
            "power": 30,
            "dot": True,
            "dot_power": 8,
            "dot_turns": 4,
            "desc": "1x se acerca y aplica Mass Infection: daño normal + veneno por 4 turnos.",
        },
        {
            "name": "Entanglement",
            "cost": 60,
            "type": "damage",
            "power": 10,
            "stun": True,
            "stun_turns": 2,
            "entangle": True,      # el equipo aliado hace más daño a esta figura
            "desc": "1x lanza su Entanglement: atrae al enemigo, lo stunea 2 turnos y las figuras aliadas le hacen más daño.",
        },
        {
            "name": "Rejuvenate the Rotten",
            "cost": 100,
            "type": "revive_team",  # revive figuras aliadas muertas con stats fijos
            "power": 20,            # daño propio
            "revive_hp": 20,
            "revive_atk": 10,
            "revive_def": 15,
            "revive_poison": True,  # las figuras revividas envenenan al atacar
            "desc": "1x se clava sus espadas (-20 HP) y revive a todos los aliados caídos con 20HP/10ATK/15DEF. Los revividos envenenan al atacar.",
        },
    ],
    "chicken": [
        {
            "name": "Chicken Leg",
            "cost": 30,
            "type": "heal_self_small",  # cura solo a Shedletsky
            "power": 0,
            "heal_min": 20,
            "heal_max": 25,
            "desc": "Shedletsky saca una pierna de pollo a medio comer, y le pega un mordisco rápido, curándose rápidamente.",
        },
        {
            "name": "Slash",
            "cost": 60,
            "type": "slash",         # usa la espada activa y aplica su efecto
            "power": 50,
            "desc": "Shedletsky ataca aplicando el efecto de su espada actual.",
        },
        {
            "name": "Chicken Legs",
            "cost": 100,
            "type": "heal_team_self", # +25 aliados, +30 a sí mismo
            "power": 30,              # curación propia
            "team_heal_power": 25,
            "desc": "Shedletsky saca una cubeta de pollo y cura +30 HP propio y +25 a todos los aliados.",
        },
    ],
    "blackout": [
        {
            "name": "Chase Up",
            "cost": 30,
            "type": "drain",
            "power": 10,
            "bar_bonus": 60,
            "desc": "Black se acuchilla a sí mismo, para crear beneficio en el futuro... -10 HP al impostor, +60 de barra.",
        },
        {
            "name": "Fast Kill",
            "cost": 60,
            "type": "fast_kill",
            "power": 60,
            "charges_needed": 3,
            "desc": "Black agarra su cuchillo, apunta a una figura, se concentra y da un ataque fuerte... Úsalo 3 turnos seguidos para activarlo. 60 de daño.",
        },
        {
            "name": "Consumed By Fury",
            "cost": 100,
            "type": "consumed_fury",
            "power": 0,
            "splash_dmg": 40,
            "desc": "...Ya estoy harto de ustedes... Es hora de acabar esto... Mata a la figura activa enemiga, +40 de daño a las otras 2. Black muere directamente.",
        },
    ],
    "homero": [
        {
            "name": "Random Food",
            "cost": 30,
            "type": "random_food",
            "desc": (
                "Homero saca algo de su bolsillo y se lo come! Que hambre...\n"
                "🍩 Donut: Cura 20 HP. 🍺 Cerveza Duff: Cura 30 HP a Homero y 10 a aliados.\n"
                "🌶️ Chiles: 10 de daño a Homero, 5 a todos los rivales + burning + stun 1t.\n"
                "🦐 Mariscos: Cura 20 HP y +20 energía. 🍔 Krusty Burger: Cura 20 HP, -10 DEF por 2t.\n"
                "🥖 Submarino: Cura 100 HP y +40 HP máx, pero stunea 3 turnos.\n"
                "🍫 Barra de Comida: Cura entre 15 y 45 HP al azar."
            ),
            "foods": [
                {"key": "donut",    "label": "🍩 Donut",              "effect": "self_heal",    "power": 20},
                {"key": "duff",     "label": "🍺 Cerveza Duff",       "effect": "duff_heal",    "self_heal": 30, "ally_heal": 10},
                {"key": "chiles",   "label": "🌶️ Chiles Picantes",    "effect": "chiles",       "self_dmg": 10, "enemy_dmg": 5, "dot_power": 4, "dot_turns": 3, "stun_turns": 1},
                {"key": "mariscos", "label": "🦐 Mariscos",           "effect": "mariscos",     "self_heal": 20, "energy_bonus": 20},
                {"key": "burger",   "label": "🍔 Krusty Burger",      "effect": "krusty_burger","self_heal": 20, "def_nerf": 10, "nerf_turns": 2},
                {"key": "sub",      "label": "🥖 El Sandwich Submarino","effect": "submarine",  "self_heal": 100, "hp_bonus": 40, "stun_turns": 3},
                {"key": "bar",      "label": "🍫 Barra de Comida",    "effect": "random_heal",  "min": 15, "max": 45},
            ],
        },
        {
            "name": "Why, you little...!",
            "cost": 60,
            "type": "homer_choke",
            "power": 25,
            "dot_turns": 5,
            "self_block_turns": 5,
            "enemy_stun_turns": 5,
            "escape_minigame": True,
            "desc": (
                "Homero ahorca a la figura rival! 25 de daño por turno durante 5 turnos.\n"
                "Homero queda bloqueado y el rival stuneado por 5 turnos.\n"
                "El rival puede completar un minijuego para liberarse y stunear a Homero 2 turnos."
            ),
        },
        {
            "name": "Nuclear Missfunction",
            "cost": 100,
            "type": "nuclear_missfunction",
            "desc": (
                "Puede que haya presionado el botón incorrecto... D'OH!\n"
                "50%: Mata 2 figuras rivales y hace 100 de daño a la restante. ¡Woo-hoo!\n"
                "50%: Lo contrario... We tried our best and we failed miserably."
            ),
        },
    ],
    "jevil": [
        {
            "name": "CHAOS CHAOS",
            "cost": 30,
            "type": "chaos_chaos",
            "desc": (
                "THE CHAOS IS THE ONLY THING I'M HERE FOR!\n"
                "Aplica un efecto al azar al oponente: frozen, burning, stun 2t, "
                "forzar cambio, poisoning, o dizziness (-daño 3t)."
            ),
        },
        {
            "name": "THE MAP REVOLVING",
            "cost": 60,
            "type": "map_revolving",
            "dizziness_turns": 6,
            "stun_chance": 0.50,
            "desc": (
                "El mapa empieza a girar... ¡alguien tiene que pararlo!\n"
                "Aplica dizziness 6 turnos al oponente. Cada turno hay un 50% de que también lo stunee."
            ),
        },
        {
            "name": "METAMORPHOSIS!",
            "cost": 100,
            "type": "metamorphosis",
            "duration": 6,
            "desc": (
                "Jevil fuerza el cambio de figuras tanto de aliados como de oponentes!\n"
                "Cada turno, ocurre un cambio forzado de figura tras la jugada. Dura 6 turnos."
            ),
        },
    ],
    "annoying_dog": [
        {
            "name": "Code Consumer",
            "cost": 30,
            "type": "code_consumer",
            "desc": (
                "Toby se comió parte del código... OH NO!\n"
                "Obtiene un buff o debuff al azar y lo aplica también al enemigo."
            ),
        },
        {
            "name": "BARK!",
            "cost": 60,
            "type": "bark",
            "power": 15,
            "desc": "... ¿y eso qué hace?\n15 de daño al oponente + cualquier debuff al azar.",
        },
        {
            "name": "Strange Twirl",
            "cost": 100,
            "type": "strange_twirl",
            "desc": (
                "Este es solo el comienzo de algo más grande...\n"
                "Reemplaza a Toby y a la figura activa del oponente con figuras al azar del juego "
                "hasta el final de la batalla."
            ),
        },
    ],
    "santa_vaca": [
        {
            "name": "Holy!",
            "cost": 30,
            "type": "holy_buff",       # Evolución: +10B DEF y +1M ATK por 20 turnos
            "power": 0,
            "def_buff": 10000000000,
            "atk_buff_holy": 1000000,
            "holy_turns": 20,
            "desc": "¡LA VACA EVOLUCIONA! +10,000,000,000 DEF y +1,000,000 ATK por 20 turnos.",
        },
        {
            "name": "Steak",
            "cost": 60,
            "type": "holy_heal",       # +10T HP a todas las figuras aliadas
            "power": 0,
            "heal_all": 10000000000000,
            "desc": "La vaca saca un trozo de su torso (que se regenera) y cura 10,000,000,000,000 HP a todo el equipo.",
        },
        {
            "name": "GOD WHAT IS THAT-",
            "cost": 100,
            "type": "holy_nuke",       # Mata a TODAS las figuras enemigas de un golpe
            "power": 0,
            "desc": "La vaca mira fijamente al equipo rival. Todas sus figuras mueren instantáneamente.",
        },
    ],
    "lobster": [
        {
            "name": "LOBSTER",
            "cost": 30,
            "type": "lobster",     # No hace nada... o sí?
            "power": 0,
            "desc": "La langosta te mira fijamente. No pasa nada. O casi nada.",
        },
        {
            "name": "LOBSTER",
            "cost": 60,
            "type": "lobster",
            "power": 0,
            "desc": "La langosta te mira fijamente. No pasa nada. O casi nada.",
        },
        {
            "name": "LOBSTER",
            "cost": 100,
            "type": "lobster",
            "power": 0,
            "desc": "La langosta te mira fijamente. No pasa nada. O casi nada.",
        },
    ],
    "agustoloco": [
        {
            "name": "Fumada",
            "cost": 30,
            "type": "agus_fumada",
            "power": 0,
            "hp_min": 100,
            "hp_max": 200,
            "desc": "Augusto decide fumarse un porro... UFF que god. Cambia su HP a un valor aleatorio entre 100 y 200.",
        },
        {
            "name": "Mechero",
            "cost": 60,
            "type": "agus_mechero",
            "power": 0,
            "burn_dmg": 20,
            "burn_turns": 4,
            "desc": "40% daño al rival + burning 4t | 40% daño a Agus + burning 4t | 20% ambos.",
        },
        {
            "name": "Peso",
            "cost": 100,
            "type": "damage",
            "power": 35,
            "stun": True,
            "stun_turns": 2,
            "desc": "Agus saca un peso... y te lo lanza... y ya XD. 35 daño + stun 2 turnos.",
        },
    ],
    "sonic": [
        {
            "name": "Spindash",
            "cost": 30,
            "type": "damage",
            "power": 25,                 # daño al activo rival
            "aoe": True,                 # golpea a todo el equipo rival
            "aoe_secondary_power": 20,   # daño a los otros 2
            "desc": "Sonic agarra velocidad y hace un Spindash hacia el frente, dañando a todos los enemigos.",
        },
        {
            "name": "Homing Attack",
            "cost": 60,
            "type": "damage",
            "power": 30,
            "desc": "Sonic salta y se lanza directamente al enemigo, dándole un golpe fuerte y certero.",
        },
        {
            "name": "Speed Power",
            "cost": 100,
            "type": "damage",
            "power": 50,
            "force_switch": True,        # fuerza cambio de figura en el rival
            "force_switch_turns": 3,     # no puede volver a esa figura por 3 turnos
            "desc": "Sonic corre a máxima velocidad y golpea al rival, dejándolo fuera de combate por 3 turnos.",
        },
    ],
    # ─── NUEVAS FIGURAS ───────────────────────────────────────────
    "007n7": [
        {
            "name": "Switch Clone Type",
            "cost": 30,
            "type": "clone_switch",  # cambia entre def/atk/heal
            "power": 0,
            "desc": "007n7 cambia el tipo de clon que usará: DEF (bloquea 2 golpes), ATK (parry con mitad del daño), HEAL (cura según el daño recibido).",
        },
        {
            "name": "Clone",
            "cost": 60,
            "type": "clone_action",  # ejecuta según tipo activo
            "power": 0,
            "desc": "007n7 lanza un clon. Su comportamiento depende del tipo activo (def/atk/heal).",
        },
        {
            "name": "Teleport",
            "cost": 100,
            "type": "teleport_007",  # cede turno, se cura 10/turno, vuelve al tener HP lleno o si aliado muere
            "power": 0,
            "desc": "007n7 se teletransporta lejos, cede sus turnos y se cura 10HP por turno hasta tener vida llena.",
        },
    ],
    "kidd": [
        {
            "name": "Fling Brick",
            "cost": 30,
            "type": "fling_brick",   # daño + reduce ATK rival, 20% de forzar cambio
            "power": 10,
            "desc": "c00lkidd lanza un ladrillo. Reduce el ATK del rival. 20% de mandarlo a volar (fuerza cambio).",
        },
        {
            "name": "Walkspeed Override",
            "cost": 60,
            "type": "damage",
            "power": 40,
            "dot": True,
            "dot_power": 8,
            "dot_turns": 3,
            "desc": "c00lkidd carga hacia el oponente, haciéndole daño e inflingiéndole quemadura (8 daño/turno x3).",
        },
        {
            "name": "Minions",
            "cost": 100,
            "type": "minion_shield",  # escudo de 2 golpes; si atacan con minions activos, el rival recibe 10 + quemadura
            "power": 0,
            "desc": "c00lkidd invoca minions: escudo de 2 golpes. Si atacan con minions activos, el rival recibe 10 daño + quemadura.",
        },
    ],
    "twotime": [
        {
            "name": "Spawnpoint",
            "cost": 30,
            "type": "spawnpoint",    # coloca punto de respawn; pasiva: 4 backstabs = revive con 50% HP
            "power": 0,
            "desc": "Two Time coloca un punto de respawn. Si acumula 4 backstabs con barra llena, puede revivir con 50% HP.",
        },
        {
            "name": "Backstab",
            "cost": 60,
            "type": "backstab",      # 15 daño + stun 1 turno + recarga barra
            "power": 15,
            "stun": True,
            "bar_bonus": 20,
            "desc": "Two Time se acerca y da un backstab. Aturde al rival 1 turno y recarga su barra.",
        },
        {
            "name": "Crouch",
            "cost": 100,
            "type": "crouch",        # reduce daño recibido este turno, buff ATK 2 turnos
            "power": 0,
            "desc": "Two Time se agacha, reduciendo el daño recibido y aumentando su daño por 2 turnos.",
        },
    ],
    "noli": [
        {
            "name": "Voidstar",
            "cost": 30,
            "type": "voidstar",      # 10 daño + atrae (próximo ataque hace más daño)
            "power": 10,
            "desc": "Noli lanza su voidstar, dañando al rival y preparando el próximo ataque para hacer +15 daño.",
        },
        {
            "name": "Voidrush",
            "cost": 60,
            "type": "voidrush",      # 25 daño, +15 si rival tiene alucinaciones
            "power": 25,
            "desc": "Noli hace un Voidrush. Si el rival tiene alucinaciones, hace +15 daño extra.",
        },
        {
            "name": "Observant",
            "cost": 100,
            "type": "observant",     # desaparece 5 turnos, pone figura sustituta; al volver hace daño masivo
            "power": 0,
            "desc": "Noli desaparece 5 turnos generando alucinaciones. Al volver hace daño masivo al enemigo activo.",
        },
    ],
    "guest1337": [
        {
            "name": "Block",
            "cost": 30,
            "type": "guest_block",   # bloquea el siguiente ataque + gana carga para Punch
            "power": 0,
            "desc": "Guest bloquea el siguiente ataque y gana una carga para usar Punch.",
        },
        {
            "name": "Charge",
            "cost": 60,
            "type": "damage",
            "power": 25,
            "dot": True,
            "dot_power": 5,
            "dot_turns": 2,
            "desc": "Guest se lanza hacia el oponente, haciéndole daño y alejándolo (reduce su daño 2 turnos).",
        },
        {
            "name": "Punch",
            "cost": 100,
            "type": "guest_punch",   # requiere carga de Block; 55 daño + stun 2 turnos
            "power": 55,
            "stun": True,
            "stun_turns": 2,
            "desc": "Requiere una carga de Block. Guest lanza un golpe masivo que aturde al rival 2 turnos.",
        },
    ],
    "noob": [
        {
            "name": "Bloxy Cola",
            "cost": 30,
            "type": "bloxy_cola",    # incrementa la ganancia de energía por 2 turnos
            "power": 0,
            "desc": "Noob toma una Bloxy Cola. Gana +15 de energía extra por turno durante 2 turnos.",
        },
        {
            "name": "Slateskin",
            "cost": 60,
            "type": "slateskin",     # se vuelve de piedra: recibe mitad del daño y devuelve mitad
            "power": 0,
            "desc": "Noob toma poción de slateskin. El próximo ataque que reciba hace mitad de daño y devuelve mitad al rival.",
        },
        {
            "name": "GhostBurger",
            "cost": 100,
            "type": "ghostburger",   # evasión aumentada + cura 10 HP/turno por 4 turnos
            "power": 0,
            "desc": "Noob come una GhostBurger. Mayor evasión y se cura 10 HP por turno durante 4 turnos.",
        },
    ],
    "chance": [
        {
            "name": "Coin Flip",
            "cost": 30,
            "type": "coin_flip",     # cara = gana carga (max 3); sello = próximo ataque le hace más daño
            "power": 0,
            "desc": "Chance gira su moneda. Cara = gana una carga (máx 3). Sello = el siguiente ataque le hará más daño.",
        },
        {
            "name": "Gun Shot",
            "cost": 60,
            "type": "gun_shot",      # 1 carga=40% stun, 2=70%, 3=100%; resto puede explotar en la cara
            "power": 0,
            "desc": "Chance dispara su revólver. A más cargas, más probabilidad de stunear al rival.",
        },
        {
            "name": "Reload Stats",
            "cost": 100,
            "type": "reload_stats",  # cambia HP de Chance aleatoriamente entre 150-250
            "power": 0,
            "desc": "Chance recarga su revólver y cambia sus stats aleatoriamente: nueva vida entre 150 y 250.",
        },
    ],
    "johndoe": [
        {
            "name": "Spikes",
            "cost": 30,
            "type": "spikes",        # daño al rival + bloquea 2 ataques + John pierde 20 HP
            "power": 15,
            "desc": "John cubre el campo de espinas. Daña al rival, bloquea los siguientes 2 ataques, pero John pierde 20 HP.",
        },
        {
            "name": "Error 404",
            "cost": 60,
            "type": "error404",      # John pierde 10 HP, barra llena + buff ATK +20 por 4 turnos
            "power": 0,
            "desc": "John se arranca el ojo (-10 HP). Su barra de energía se llena y gana +20 ATK por 4 turnos.",
        },
        {
            "name": "Traps",
            "cost": 100,
            "type": "traps",         # 3 usos: al 3ro atrapa al rival con 20 daño/turno por 3 turnos
            "power": 0,
            "desc": "Úsala 3 veces para atrapar al rival en una trampa que hace 20 daño por turno durante 3 turnos.",
        },
    ],
    "janedoe": [
        {
            "name": "Crystal Type",
            "cost": 30,
            "type": "crystal_switch",  # cambia entre tipo daño y tipo curación
            "power": 0,
            "desc": "Jane cambia el tipo de cristal: DAÑO (stuned + 20 daño) o CURACIÓN (cura al aliado con menos HP + inmunidad).",
        },
        {
            "name": "Crystal Throw",
            "cost": 60,
            "type": "crystal_throw",   # ejecuta según tipo activo
            "power": 20,
            "desc": "Jane lanza un cristal. Si es de daño: 20 daño + stun 3 turnos. Si es curación: cura al aliado con menos HP + inmunidad 3 turnos.",
        },
        {
            "name": "Hatchet",
            "cost": 100,
            "type": "damage",
            "power": 45,
            "dot": True,
            "dot_power": 8,
            "dot_turns": 4,
            "desc": "Jane lanza su hacha hacia el enemigo, haciéndole daño y aplicando Resonancia (8 daño/turno x4).",
        },
    ],
    "donmanzanas": [
        {
            "name": "Apple Shot",
            "cost": 30,
            "type": "apple_shot",      # se concentra 3 turnos; al 3er uso dispara con daño máximo (max 33)
            "power": 25,
            "max_power": 33,
            "charges_needed": 3,
            "desc": "Don Manzanas se concentra por 3 turnos. Al estar lo suficientemente concentrado, ¡tira su manzana con toda su fuerza!",
        },
        {
            "name": "Apple Armor",
            "cost": 60,
            "type": "apple_armor",     # reduce daño recibido durante 2 turnos
            "power": 0,
            "armor_turns": 2,
            "armor_reduction": 0.5,    # recibe solo el 50% del daño
            "desc": "Don Manzanas construye una armadura de manzanas a toda velocidad. ¡Recibe menos daño por 2 turnos!",
        },
        {
            "name": "Golden Apple",
            "cost": 100,
            "type": "golden_apple",    # potencia el próximo ataque (acumulable)
            "power": 0,
            "atk_buff": 14,            # +14 ATK al próximo golpe (acumulable, hasta max 33 de ATK total)
            "desc": "Don Manzanas saca una Manzana Dorada. ¡Su próximo ataque será mucho más potente! (Acumulable)",
        },
    ],
}


# ============================================================
#  SISTEMA DE BATALLAS NUEVO (3 figuras + barra de energía)
# ============================================================
active_battles = {}

# ── KIRBY ───────────────────────────────────────────────────────
KIRBY_DEFAULT_SKILLS = [
    {
        "name": "Absorb",
        "cost": 10,
        "type": "kirby_absorb",
        "power": 0,
        "desc": "Kirby absorbe a la figura del oponente. Desaparece 2 turnos y Kirby copia sus habilidades.",
    },
    {
        "name": "Sword Slash",
        "cost": 40,
        "type": "damage",
        "power": 20,
        "aoe": True,
        "aoe_secondary_power": 5,
        "desc": "Kirby vuela y se lanza al oponente. 20 de daño directo y 5 a las otras figuras enemigas.",
    },
    {
        "name": "Stone Crush",
        "cost": 60,
        "type": "damage",
        "power": 40,
        "desc": "Kirby se transforma en piedra y aplasta al oponente. 40 de daño.",
    },
    {
        "name": "Flamethrower",
        "cost": 100,
        "type": "kirby_flamethrower",
        "power": 20,
        "dot_turns": 8,
        "dot_power": 6,
        "desc": "Kirby escupe fuego sobre todos los enemigos. 20 de daño + burning 8 turnos a todos.",
    },
]
KIRBY_TRANSFORMED_SLOT0 = {
    "name": "Spit",
    "cost": 10,
    "type": "kirby_spit",
    "power": 0,
    "desc": "Kirby escupe la habilidad absorbida y regresa a sus habilidades por defecto.",
}
FIGURE_SKILLS["kirby"] = list(KIRBY_DEFAULT_SKILLS)

# ── SANS ─────────────────────────────────────────────────────────
FIGURE_SKILLS["sans"] = [
    {
        "name": "Bone Barrier",
        "cost": 30,
        "type": "bone_barrier",
        "power": 15,
        "desc": "Sans genera una barrera de huesos. Si el enemigo ataca, la barrera bloquea y hace 15 de daño al atacante.",
    },
    {
        "name": "Gaster Blaster",
        "cost": 60,
        "type": "damage",
        "power": 50,
        "desc": "Sans dispara un láser con su Gaster Blaster. 50 de daño.",
    },
    {
        "name": "Rest",
        "cost": 0,          # Gasta TODA la energía que tengas
        "type": "sans_rest",
        "power": 0,
        "desc": "Sans descansa un momento... Convierte toda su energía actual en Misses. Coste: toda tu barra de energía.",
    },
    {
        "name": "LOVE Check",
        "cost": 100,
        "type": "love_check",
        "power": 0,
        "dmg_per_kill": 20,
        "desc": "Sans mira todos tus pecados... El daño es igual al número de figuras matadas por el oponente ×20.",
    },
]

# ── PAPYRUS ──────────────────────────────────────────────────────
FIGURE_SKILLS["papyrus"] = [
    {
        "name": "Cool Pose!",
        "cost": 30,
        "type": "papyrus_pose",
        "power": 0,
        "atk_buff": 10,
        "def_buff": 10,
        "desc": "Papyrus hace una pose muy genial! +10 ATK y +10 DEF permanentes.",
    },
    {
        "name": "Spaghetti!",
        "cost": 60,
        "type": "damage",
        "power": 20,
        "stun": True,
        "stun_turns": 1,
        "def_debuff": 5,
        "desc": "Papyrus ofrece un plato de Spaghetti. 20 de daño, stun 1 turno y -5 DEF permanente al oponente.",
    },
    {
        "name": "Cool Laugh!",
        "cost": 100,
        "type": "papyrus_laugh",
        "power": 0,
        "self_heal": 35,
        "ally_heal": 20,
        "desc": "Papyrus motiva a todos. Cura 35 HP a sí mismo y 20 HP a los aliados.",
    },
]

# ── FLOWEY ───────────────────────────────────────────────────────
FIGURE_SKILLS["flowey"] = [
    {
        "name": "Save And Reload",
        "cost": 30,
        "type": "flowey_save_reload",
        "power": 0,
        "desc": "1er uso: Flowey guarda el estado de la batalla. 2do uso: regresa al estado guardado.",
    },
    {
        "name": "Fake Help",
        "cost": 60,
        "type": "flowey_fake_help",
        "power": 40,
        "desc": "Los 2 primeros usos curan +5 HP al oponente. El 3er uso hace 40 de daño.",
    },
    {
        "name": "One more soul...",
        "cost": 100,
        "type": "flowey_soul",
        "power": 0,
        "hp_per_soul": 10,
        "souls_to_omega": 7,
        "desc": "Los primeros 6 usos dan +10 HP permanente a Flowey. Al 7mo, desbloquea la pasiva OMEGA.",
    },
]

# ── OMEGA FLOWEY ─────────────────────────────────────────────────
FIGURE_SKILLS["omega_flowey"] = [
    {
        "name": "MANIATIC LAUGH",
        "cost": 30,
        "type": "papyrus_laugh",   # reutiliza heal_team con distintos valores
        "power": 0,
        "self_heal": 20,
        "ally_heal": 10,
        "desc": '"ESTE ES MI MUNDO AHORA... JAJAJAJAAA!" Cura 20 HP a Flowey y 10 a los aliados.',
    },
    {
        "name": "BOMBS, FIRE AND ROOTS!",
        "cost": 60,
        "type": "damage",
        "power": 45,
        "aoe": True,
        "aoe_secondary_power": 10,
        "stun": True,
        "stun_turns": 1,
        "desc": '"ESTO ES UNA PESADILLA!" 45 de daño al activo, 10 a los otros 2 y stun 1 turno.',
    },
    {
        "name": "ITS THE END FOR YOU!",
        "cost": 100,
        "type": "omega_its_the_end",
        "power": 110,
        "desc": '"JAJAJAJA!" Mata al activo enemigo, 110 a los otros 2 enemigos. Flowey muere y 110 a sus propios aliados.',
    },
]

# ── OG GAMER 64 — habilidades por fase ─────────────────────────
# Las habilidades cambian según la fase activa (1-4).
# La pasiva "og_gamer_phases" controla la revivificación con cambio de fase.
FIGURE_SKILLS["og_gamer64"] = [
    {
        "name": "Heroic Pose",
        "cost": 30,
        "type": "team_atk_buff",
        "power": 0,
        "atk_buff": 10,
        "team_buff": True,
        "phase": 1,
        "desc": "Gamer hace una pose que incrementa el daño de todos los aliados. +10 de daño a todos los aliados hasta hacer un ataque. ¡Acumulable!",
    },
    {
        "name": "Cannon Arm",
        "cost": 60,
        "type": "damage",
        "power": 45,
        "stun": True,
        "stun_turns": 3,
        "bar_drain": 50,
        "phase": 1,
        "desc": "Gamer dispara su cañón. 45 de daño, -50 de carga en la barra del oponente y stun por 3 turnos.",
    },
    {
        "name": "Childish Android",
        "cost": 100,
        "type": "damage",
        "power": 150,
        "phase": 1,
        "desc": "Gamer se enfada. No puede ser que alguien sea más fuerte que él. 150 de daño masivo al oponente.",
    },
    # ── FASE 2 ──────────────────────────────────────────────────
    {
        "name": "Glitched Arm",
        "cost": 30,
        "type": "damage",
        "power": 30,
        "force_switch": True,
        "force_switch_turns": 3,
        "phase": 2,
        "desc": "Gamer golpea el suelo con su brazo corrupto. 30 de daño y la figura actual del oponente queda bloqueada por 3 turnos.",
    },
    {
        "name": "Corrupted Spikes",
        "cost": 60,
        "type": "dot",
        "power": 0,
        "dot_turns": 10,
        "dot_power": 8,
        "stun": True,
        "stun_turns": 3,
        "phase": 2,
        "desc": "Gamer atrapa al oponente en espinas corruptas. Veneno por 10 turnos y stun de 3 turnos.",
    },
    {
        "name": "[[TEXT NOT FOUND]]",
        "cost": 100,
        "type": "charge_delete",
        "power": 0,
        "charge_turns": 2,
        "phase": 2,
        "desc": "Gamer empieza a recargar un ataque. Si usas esta habilidad 2 veces seguidas, la figura actual del oponente desaparece.",
    },
    # ── FASE 3 ──────────────────────────────────────────────────
    {
        "name": "Ki Charge",
        "cost": 30,
        "type": "og_ki_charge",
        "power": 0,
        "ki_hp": 100,
        "ki_stat": 20,
        "phase": 3,
        "desc": "Gamer carga su ki. +100 de vida, +20 de ataque, defensa y velocidad. ¡Acumulable hasta el final de la batalla!",
    },
    {
        "name": "Kamehameha!",
        "cost": 60,
        "type": "damage",
        "power": 60,
        "stun": True,
        "stun_turns": 3,
        "phase": 3,
        "desc": "Gamer lanza un láser de energía. 60 de daño y 3 turnos de stun al oponente.",
    },
    {
        "name": "Godlike",
        "cost": 100,
        "type": "instakill_random",
        "power": 0,
        "phase": 3,
        "desc": "Gamer flota, agarra una figura del oponente y la aplasta. Instakill a una figura aleatoria del oponente.",
    },
    # ── FASE 4 ──────────────────────────────────────────────────
    {
        "name": "Prismatic Energy",
        "cost": 30,
        "type": "og_reset_phase",
        "power": 0,
        "phase": 4,
        "desc": "Gamer regresa el tiempo para repetir el ciclo. Regresa a la Fase 1 con vida completa.",
    },
    {
        "name": "Chaos Control!",
        "cost": 60,
        "type": "damage",
        "power": 0,
        "stun": True,
        "stun_turns": 10,
        "team_atk_buff": 20,
        "phase": 4,
        "desc": "Gamer congela el tiempo. Stun de 10 turnos al oponente y +20 de daño a todas las figuras aliadas.",
    },
    {
        "name": "ITS OVER!",
        "cost": 100,
        "type": "og_its_over",
        "power": 20,
        "self_destruct": True,
        "phase": 4,
        "desc": "Gamer explota acabando con todo. Mata a todas las figuras del oponente y a sí mismo. 20 de daño a las figuras aliadas por la explosión.",
    },
]

# ── RYU ─────────────────────────────────────────────────────────────────────
FIGURE_SKILLS["ryu"] = [
    {
        "name":  "Hadouken",
        "cost":  30,
        "type":  "hadouken",        # special: activates timing minigame
        "power": 30,
        "fire_power": 40,           # power if timing hits (Fire Hadouken)
        "desc":  (
            "Ryu lanza una bola de energía! "
            "Si atinas el timing → Fire Hadouken: 40 daño + burning 2T. "
            "Sin timing → Hadouken normal: 30 daño."
        ),
    },
    {
        "name":       "Shoryuken",
        "cost":       40,
        "type":       "damage",
        "power":      20,
        "stun":       True,
        "stun_turns": 2,
        "desc":       "Ryu hace un gancho. 20 daño y stun 2 turnos al oponente.",
    },
    {
        "name":     "Tatsumaki Senpuu Kyaku",
        "cost":     50,
        "type":     "tatsumaki",    # special: activates opponent memory minigame
        "power":    30,
        "dot_turns": 3,
        "desc":     (
            "Ryu hace una patada voladora. DOT 30/turno × 3T. "
            "Pero el oponente tiene un minijuego de memoria: si lo completa, "
            "cancela el ataque y Ryu recibe stun 3T."
        ),
    },
    {
        "name":     "Shin-Hadoken",
        "cost":     100,            # costs all SUPER bar (treated as energy gate)
        "type":     "shin_hadoken",
        "power":    150,
        "aoe_secondary_power": 40,
        "stun":     True,
        "stun_turns": 2,
        "super_move": True,         # only available when super_bar >= 100
        "desc":     (
            "ESTO SE ACABA AHORA! — 150 daño a la figura activa, "
            "40 daño a las demás figuras del oponente. Ryu queda stunned 2T."
        ),
    },
]

