"""
database.py — Carga, guarda y gestiona la base de datos JSON persistente.
"""
import json
import os

DB_PATH = "/etc/secrets/db.json" if os.path.exists("/etc/secrets") else "db.json"


def load_db() -> dict:
    """Carga la database desde el archivo persistente."""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    if os.path.exists("db.json"):
        with open("db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}


def save_db(db: dict):
    """Guarda la database en el archivo persistente."""
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error guardando en {DB_PATH}: {e} — intentando db.json local")
        with open("db.json", "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)


def save_user(uid: str, data: dict):
    """Guarda un solo usuario en la database."""
    db = load_db()
    db["users"][str(uid)] = data
    save_db(db)


def get_user(db: dict, user_id) -> dict | None:
    uid = str(user_id)
    return db["users"].get(uid)


def create_user(db: dict, user_id, display_name: str) -> dict:
    uid = str(user_id)
    db["users"][uid] = {
        "name": display_name,
        "coins": 1000,
        "figures": [],
        "team": [None, None, None],
        "wins": 0,
        "losses": 0,
        "level": 1,
        "xp": 0,
        "skill_points": 0,
        "learn_tree": {},
        "rebirth_count": 0,
        "recipe_count": 0,
        "combine_upgrades": {},
    }
    save_db(db)
    return db["users"][uid]
