# -*- coding: utf-8 -*-
"""
====================================================================================
 🛵 OVQAT YETKAZISH XIZMATI — YAGONA FAYL (delivery.py)

 Barcha Telegram botlar bitta faylda (jami 8 ta bot):
   1. Mijoz boti     @Botjon01_bot        — mijoz buyurtma beradi (restoran tanlaydi!)
   2. Kuryer boti    @Botxon01_bot        — kuryer topshiriq oladi, holat belgilaydi
   3. Operator boti  @Botbek01_bot        — siz boshqarasiz (buyurtmalar, kuryer, statistika)
   4-8. RESTORAN botlari (5 ta)           — har bir restoran o'z buyurtmalarini qabul qiladi:
          @AmirRestauran_bot, @fayzRestauran_bot, @VisolRestauran_bot,
          @MarjonaRestauran_bot, @MarakanaRestauran_bot

 Ishga tushirish:   python3 delivery.py   (Windows: py delivery.py)
 To'xtatish:        Ctrl+C
 Ma'lumotlar:       delivery.db  (shu papkada avtomatik yaratiladi)

 Bo'limlar:
   [1] SOZLAMALAR          — tokenlar, narxlar, telefon raqam
   [2] MA'LUMOTLAR BAZASI  — SQLite funksiyalari
   [3] UMUMIY YORDAMCHILAR — matn, tugmalar, bildirishnomalar
   [4] MIJOZ BOTI          — handlerlar
   [5] KURYER BOTI         — handlerlar
   [6] OPERATOR BOTI       — handlerlar
    [7] RESTORAN BOTLARI    — har bir restoran uchun handlerlar (5 ta bot)
    [8] VEB-SAYT            — mijozlar uchun sayt (buyurtma, holatni kuzatish)

   [8] ISHGA TUSHIRISH     — main
====================================================================================
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import html as _html
import json
import logging
import os
import re
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

logging.basicConfig(level=logging.INFO)

# ============================================================================
# [1] SOZLAMALAR
# ============================================================================

# --- Telegram bot tokenlari (BotFather'dan olingan) ---
CUSTOMER_BOT_TOKEN = "8726354054:AAEFFbCNBXsK6qXMwB5BQ-QDJ7M7AtxnnJ4"  # mijoz  @Botjon01_bot
COURIER_BOT_TOKEN = "8688742789:AAFMtlgALqjNSoytppdqpxj65ztCXr2npUk"    # kuryer @Botxon01_bot
OPERATOR_BOT_TOKEN = "8837451952:AAFweaaYEzrq393d4J8pGEroxGXLHSAuSFA"   # operator @Botbek01_bot

# --- 5 ta RESTORAN boti (har bir restoran shu botda buyurtma qabul qiladi) ---
# Restoran nomini shu yerda ham, bot ichida ham o'zgartirish mumkin.
RESTAURANT_BOTS = [
    {"id": 1, "token": "8266279696:AAGQYabjAy8cQAlE8K7RmGNEaS2fJgtgA0k", "name": "Amir Restoran"},
    {"id": 2, "token": "8955058655:AAHScrgYKYetyKJnbWgH0job10EkgmApS1s", "name": "Fayz Restoran"},
    {"id": 3, "token": "8465060827:AAGwcHANEE6f_xWOcbjomSrdAC1VgxISY9o", "name": "Visol Restoran"},
    {"id": 4, "token": "8921731130:AAGPuyaYvUqK7ydRXVKHozG5JKqXo9TE1wY", "name": "Marjona Restoran"},
    {"id": 5, "token": "8963091245:AAHP5lFYaxZ0gbYr1kwWgotVHnzH3CxWJHk", "name": "Marakana Restoran"},
]


def restaurant_token(restaurant_id):
    for r in RESTAURANT_BOTS:
        if r["id"] == restaurant_id:
            return r["token"]
    return None


# ======================= MENYU KATEGORIYALARI =======================
# Mijoz menyuni ochganda shu 3 ta tugma chiqadi
CAT_FOODS = "Ovqatlar"
CAT_SALADS = "Salatlar"
CAT_DRINKS = "Ichimliklar"

CATEGORIES = [
    ("foods", "🍲 Ovqatlar", CAT_FOODS),
    ("salads", "🥗 Salatlar", CAT_SALADS),
    ("drinks", "🥤 Ichimliklar", CAT_DRINKS),
]


def cat_label(code):
    """'foods' -> '🍲 Ovqatlar'"""
    for c, label, _name in CATEGORIES:
        if c == code:
            return label
    return code


def cat_name(code):
    """'foods' -> 'Ovqatlar'"""
    for c, _label, name in CATEGORIES:
        if c == code:
            return name
    return CAT_FOODS


def cat_code(name):
    """'Ovqatlar' -> 'foods'"""
    for c, _label, n in CATEGORIES:
        if n == name:
            return c
    return "foods"


# =======================================================================
# HAR BIR RESTORAN UCHUN ALOHIDA MENYU
# (restoran_id -> {kategoriya: [(nomi, narxi, izohi), ...]})
# =======================================================================
RESTAURANT_MENUS = {
    1: {
        CAT_FOODS: [
            ("Osh (to'y palovi)", 35000, "Qo'y go'shtli to'y oshi, 1 porsiya"),
            ("Qozon kabob", 45000, "Qo'y go'shti qozonda, 1 porsiya"),
            ("Manti (6 dona)", 28000, "Qo'l mantisi, qatiqli"),
            ("Lag'mon", 25000, "Uy lag'moni, 1 porsiya"),
            ("Shurpa", 30000, "Qo'y go'shtli shurpa"),
            ("Norin", 32000, "An'anaviy norin"),
            ("Somsa (3 dona)", 18000, "Tandir somsa"),
            ("Dolma", 30000, "Uzum bargi dolmasi"),
        ],
        CAT_SALADS: [
            ("Achichuk", 12000, "Pomidor, piyoz, ko'kat"),
            ("Sezar salati", 25000, "Tovuqli, parmezan bilan"),
            ("Olivye", 18000, "Klassik salat"),
            ("Ko'katlar to'plami", 10000, "Yashil ko'katlar"),
        ],
        CAT_DRINKS: [
            ("Ko'k choy (1 l)", 8000, "Choynakda"),
            ("Qora choy (1 l)", 8000, "Choynakda"),
            ("Ayron", 10000, "Uy ayroni, 0.5 l"),
            ("Kompot (1 l)", 12000, "Mevadan tayyorlangan"),
            ("Coca-Cola 0.5 l", 9000, "Sovutilgan"),
            ("Mineral suv 0.5 l", 7000, "Gazli"),
        ],
    },
    2: {
        CAT_FOODS: [
            ("Lavash (tovuqli)", 28000, "Tovuq go'shtli, katta"),
            ("Lavash (mol go'shtli)", 33000, "Mol go'shtli, katta"),
            ("Donar (katta)", 35000, "Turk donari"),
            ("Burger klassik", 30000, "Mol go'shtli kotlet"),
            ("Chizburger", 35000, "Ikki pishloqli"),
            ("Xot-dog", 18000, "Kolbasa bilan"),
            ("Frantsuz kartoshka", 15000, "Dudlangan kartoshka"),
            ("Nagets (6 dona)", 20000, "Sous bilan"),
            ("Pitsa Margarita", 55000, "30 sm, pishloqli"),
        ],
        CAT_SALADS: [
            ("Sezar salati", 26000, "Tovuqli"),
            ("Tovuqli salat", 22000, "Grill tovuq bilan"),
            ("Sabzavotli salat", 15000, "Yangi sabzavotlar"),
        ],
        CAT_DRINKS: [
            ("Coca-Cola 0.5 l", 9000, "Sovutilgan"),
            ("Fanta 0.5 l", 9000, "Sovutilgan"),
            ("Sprite 0.5 l", 9000, "Sovutilgan"),
            ("Milkshake", 20000, "Bananli/shakarlik"),
            ("Choy", 7000, "1 l"),
            ("Ayron", 10000, "0.5 l"),
        ],
    },
    3: {
        CAT_FOODS: [
            ("Mol go'shtli shashlik", 22000, "1 sixcha"),
            ("Qo'y go'shtli shashlik", 25000, "1 sixcha"),
            ("Tovuqli shashlik", 18000, "1 sixcha"),
            ("Lula kabob", 20000, "Qiyma kabob, 1 sixcha"),
            ("Jigar shashlik", 18000, "1 sixcha"),
            ("Baliq shashlik", 30000, "1 sixcha"),
            ("Osh", 32000, "1 porsiya"),
            ("Kabob bilan non", 15000, "Lavashda"),
        ],
        CAT_SALADS: [
            ("Achichuk", 12000, "Pomidor, piyoz"),
            ("Piyozli salat", 10000, "Sirka bilan"),
            ("Sabzavotli grill", 20000, "Grill sabzavotlar"),
            ("Ko'katlar", 8000, "Yashil ko'katlar"),
        ],
        CAT_DRINKS: [
            ("Ko'k choy (1 l)", 8000, "Choynakda"),
            ("Limonli choy", 10000, "1 l"),
            ("Ayron", 10000, "0.5 l"),
            ("Gazli suv", 6000, "0.5 l"),
            ("Kompot", 12000, "1 l"),
        ],
    },
    4: {
        CAT_FOODS: [
            ("Quritilgan tuxum (3 ta)", 18000, "Pomidor bilan"),
            ("Omelet", 20000, "Pishloqli"),
            ("Sirdagi qaymoq", 15000, "Tvorog, smetana"),
            ("Sutli bo'tqa", 16000, "Guruchli/tsennitsali"),
            ("Chuchvara", 25000, "Uy chuchvarasi"),
            ("Sho'rva", 22000, "Mol go'shtli"),
            ("Kartoshka qovurma", 20000, "Qo'ziqorinli"),
            ("Kotlet va pyure", 28000, "Tovuq kotlet"),
        ],
        CAT_SALADS: [
            ("Sabzavotli salat", 12000, "Yangi sabzavot"),
            ("Tvorogli salat", 16000, "Tvorog, ko'kat"),
            ("Mevali salat", 20000, "Mavsumiy mevalar"),
        ],
        CAT_DRINKS: [
            ("Sut 0.5 l", 10000, "Issiq/sovuq"),
            ("Kefir 0.5 l", 10000, "Yangi"),
            ("Choy", 7000, "1 l"),
            ("Kofe", 12000, "Qaynatilgan"),
            ("Kakao", 14000, "Sutli"),
            ("Sharbat", 15000, "0.5 l"),
        ],
    },
    5: {
        CAT_FOODS: [
            ("Pitsa Pepperoni", 60000, "32 sm"),
            ("Pitsa To'rt pishloq", 65000, "32 sm"),
            ("Pitsa Go'shtli", 70000, "32 sm"),
            ("Doner (turk)", 35000, "Katta"),
            ("Iskandar kabob", 55000, "Turkcha, non ustida"),
            ("Pide (qiymali)", 38000, "Turk pidesi"),
            ("Lahmajun", 25000, "Yupqa xamir"),
            ("Qanotlar (8 dona)", 40000, "Grill, sous bilan"),
        ],
        CAT_SALADS: [
            ("Turk salati", 22000, "Pomidor, bodring, feta"),
            ("Sezar salati", 26000, "Tovuqli"),
            ("Zaytunli salat", 24000, "Zaytun va sabzavot"),
        ],
        CAT_DRINKS: [
            ("Turk choyi", 8000, "Kichik stakanda"),
            ("Ayran", 10000, "Turk ayrani"),
            ("Coca-Cola 0.5 l", 9000, "Sovutilgan"),
            ("Mineral suv 0.5 l", 7000, "Gazli/gazsiz"),
            ("Limonad", 15000, "Uy limonadi, 0.5 l"),
        ],
    },
}

# --- Operator (siz) ---
# Telegram ID raqamingizni shu yerga yozing, masalan: OPERATOR_IDS = [123456789]
# Bo'sh qoldirilsa — operator botga birinchi bo'lib /start bosgan odam operator bo'ladi.
OPERATOR_IDS = [7897244775]

# Mijozlar "Yordam" bo'limida ko'radigan telefon raqamingiz
SUPPORT_PHONE = "+998 90 000 00 00"

# --- Narxlar ---
# Standart dostavka puli (so'm)
DELIVERY_FEE = 12000

# --- VEB-SAYT (mijozlar uchun) ---
# Sayt botlar bilan birga ishga tushadi.
# Kompyuterda:      http://127.0.0.1:8080
# Telefonda (Wi-Fi): http://<kompyuter-IP>:8080   (masalan http://192.168.1.5:8080)
WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.environ.get("PORT", 8080))
# Sayt nomi (sahifa sarlavhasida ko'rinadi)
SITE_NAME = "Ovqat Yetkazish"

# Ma'lumotlar bazasi fayli
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "delivery.db")


# ============================================================================
# [2] MA'LUMOTLAR BAZASI (SQLite)
# ============================================================================

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=10000")
    return c


def _q(sql, args=()):
    con = _conn()
    try:
        rows = con.execute(sql, args).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def _one(sql, args=()):
    rows = _q(sql, args)
    return rows[0] if rows else None


def _w(sql, args=()):
    con = _conn()
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


def _ensure_columns(con, table, cols):
    """Eski bazaga yetishmayotgan ustunlarni qo'shadi (migratsiya)."""
    have = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, ddl in cols.items():
        if name not in have:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db():
    con = _conn()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            tg_id      INTEGER PRIMARY KEY,
            role       TEXT NOT NULL,          -- customer | courier | operator | restaurant
            name       TEXT DEFAULT '',
            phone      TEXT DEFAULT '',
            status     TEXT DEFAULT 'active',  -- active | pending | rejected | blocked
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS restaurants (
            id           INTEGER PRIMARY KEY,
            name         TEXT DEFAULT '',
            owner_tg_id  INTEGER,
            contact_name TEXT DEFAULT '',
            phone        TEXT DEFAULT '',
            address      TEXT DEFAULT '',
            is_available INTEGER DEFAULT 1,
            created_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS menu (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER DEFAULT 1,
            name          TEXT NOT NULL,
            price         INTEGER NOT NULL,
            description   TEXT DEFAULT '',
            category      TEXT DEFAULT 'Ovqatlar',   -- Ovqatlar | Salatlar | Ichimliklar
            is_available  INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS carts (
            tg_id         INTEGER NOT NULL,
            item_id       INTEGER NOT NULL,
            restaurant_id INTEGER,
            qty           INTEGER NOT NULL,
            PRIMARY KEY (tg_id, item_id)
        );
        CREATE TABLE IF NOT EXISTS order_events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER NOT NULL,
            text       TEXT NOT NULL,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            source           TEXT NOT NULL,       -- bot | phone | site
            status           TEXT NOT NULL,       -- new|accepted|preparing|ready|with_courier|on_the_way|delivered|cancelled
            restaurant_id    INTEGER,
            customer_name    TEXT DEFAULT '',
            customer_phone   TEXT DEFAULT '',
            customer_tg_id   INTEGER,
            items            TEXT DEFAULT '[]',   -- json: [{name, price, qty}]
            food_cost        INTEGER DEFAULT 0,
            delivery_fee     INTEGER DEFAULT 0,
            collect_food     INTEGER DEFAULT 1,   -- 1=kuryer ovqatni sotib oladi, 0=mijoz restoranda to'lagan
            address_text     TEXT DEFAULT '',
            lat              REAL,
            lon              REAL,
            courier_tg_id    INTEGER,
            note             TEXT DEFAULT '',
            created_at       TEXT,
            updated_at       TEXT,
            delivered_at     TEXT,
            track_token      TEXT                 -- sayt buyurtmasini kuzatish uchun maxfiy kod
        );
        """
    )
    # Eski (avvalgi) bazalarga yangi ustunlarni qo'shish
    _ensure_columns(con, "menu", {"restaurant_id": "INTEGER DEFAULT 1",
                                  "category": "TEXT DEFAULT 'Ovqatlar'"})
    _ensure_columns(con, "carts", {"restaurant_id": "INTEGER"})
    _ensure_columns(con, "orders", {"restaurant_id": "INTEGER",
                                    "track_token": "TEXT"})
    con.commit()

    # 5 ta restoranni yaratish (agar yo'q bo'lsa)
    cnt = con.execute("SELECT COUNT(*) AS c FROM restaurants").fetchone()["c"]
    if cnt == 0:
        for r in RESTAURANT_BOTS:
            con.execute(
                "INSERT INTO restaurants (id, name, is_available, created_at) VALUES (?,?,1,?)",
                (r["id"], r["name"], _now()),
            )
        con.commit()

    # Har bir restoranga namuna menyu (o'sha restoranda taom bo'lmasa)
    sample = [
        ("Osh (palov)", 30000, "An'anaviy osh, 1 porsiya"),
        ("Somsa", 10000, "Go'shtli somsa, 1 dona"),
        ("Lag'mon", 22000, "Uy lag'moni, 1 porsiya"),
        ("Choy", 8000, "1 litr ko'k choy"),
    ]
    for r in RESTAURANT_BOTS:
        c2 = con.execute(
            "SELECT COUNT(*) AS c FROM menu WHERE restaurant_id=?", (r["id"],)
        ).fetchone()["c"]
        if c2 == 0:
            con.executemany(
                "INSERT INTO menu (restaurant_id, name, price, description) VALUES (?,?,?,?)",
                [(r["id"], n, p, d) for n, p, d in sample],
            )
    con.commit()

    # ===== YANGI: har bir restoranga o'ziga xos, katta menyu (kategoriyalar bilan) =====
    # Bir marta bajariladi (meta jadvalida belgilanadi), sizning qo'shgan taomlaringiz o'chmaydi.
    if not meta_get("menu_seed_v2"):
        old_defaults = {
            ("Osh (palov)", 30000), ("Somsa", 10000),
            ("Lag'mon", 22000), ("Choy", 8000),
        }
        for r in RESTAURANT_BOTS:
            rid = r["id"]
            # o'zgartirilmagan eski namuna taomlarni olib tashlaymiz
            for it in menu_items(rid, available_only=False):
                if (it["name"], it["price"]) in old_defaults:
                    del_menu_item(it["id"])
            have = {it["name"] for it in menu_items(rid, available_only=False)}
            new_rows = []
            for cat_name_, items_ in RESTAURANT_MENUS.get(rid, {}).items():
                for nm, pr, ds in items_:
                    if nm in have:
                        continue
                    new_rows.append((rid, nm, pr, ds, cat_name_))
            if new_rows:
                con3 = _conn()
                con3.executemany(
                    "INSERT INTO menu (restaurant_id, name, price, description, category) "
                    "VALUES (?,?,?,?,?)",
                    new_rows,
                )
                con3.commit()
                con3.close()
        meta_set("menu_seed_v2", "1")

    con.commit()
    con.close()


# ---------- Foydalanuvchilar ----------

def get_user(tg_id):
    return _one("SELECT * FROM users WHERE tg_id=?", (tg_id,))


def save_user(tg_id, role, name="", phone="", status="active"):
    _w(
        """INSERT INTO users (tg_id, role, name, phone, status, created_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(tg_id) DO UPDATE SET
             role=excluded.role, name=excluded.name,
             phone=excluded.phone, status=excluded.status""",
        (tg_id, role, name, phone, status, _now()),
    )


def set_user(tg_id, **kw):
    if not kw:
        return
    cols = ", ".join(f"{k}=?" for k in kw)
    _w(f"UPDATE users SET {cols} WHERE tg_id=?", (*kw.values(), tg_id))


def operator_tg_ids():
    """Operatorga xabar yuboriladigan Telegram ID lar.
    Agar OPERATOR_IDS to'ldirilgan bo'lsa — faqat o'shalar (boshqa akkauntlar
    tasodifan operator bo'lib qolgan bo'lsa ham, xabarlar faqat sizga keladi)."""
    if OPERATOR_IDS:
        return list(dict.fromkeys(OPERATOR_IDS))
    rows = _q("SELECT tg_id FROM users WHERE role='operator' AND status='active'")
    return [r["tg_id"] for r in rows]


def operator_count():
    return _one("SELECT COUNT(*) AS c FROM users WHERE role='operator' AND status='active'")["c"]


def couriers(active_only=False):
    if active_only:
        return _q(
            "SELECT * FROM users WHERE role='courier' AND status='active' ORDER BY name"
        )
    return _q("SELECT * FROM users WHERE role='courier' ORDER BY status, name")


def courier_name(tg_id):
    u = get_user(tg_id)
    return u["name"] if u else "—"


# ---------- Restoranlar ----------

def restaurants_list(available_only=False):
    if available_only:
        return _q("SELECT * FROM restaurants WHERE is_available=1 ORDER BY id")
    return _q("SELECT * FROM restaurants ORDER BY id")


def get_restaurant(restaurant_id):
    return _one("SELECT * FROM restaurants WHERE id=?", (restaurant_id,))


def set_restaurant(restaurant_id, **kw):
    if not kw:
        return
    cols = ", ".join(f"{k}=?" for k in kw)
    _w(f"UPDATE restaurants SET {cols} WHERE id=?", (*kw.values(), restaurant_id))


def restaurant_name(restaurant_id):
    r = get_restaurant(restaurant_id) if restaurant_id else None
    if r and r["name"]:
        return r["name"]
    return f"Restoran {restaurant_id}" if restaurant_id else "—"


# ---------- Menyu ----------

def menu_items(restaurant_id=None, available_only=True, category=None):
    """restaurant_id berilmasa — barcha taomlar. category berilsa — faqat shu kategoriya."""
    sql = "SELECT * FROM menu WHERE 1=1"
    args = []
    if restaurant_id is not None:
        sql += " AND restaurant_id=?"
        args.append(restaurant_id)
    if available_only:
        sql += " AND is_available=1"
    if category:
        sql += " AND IFNULL(category, 'Ovqatlar')=?"
        args.append(category)
    sql += " ORDER BY id"
    return _q(sql, tuple(args))


def menu_categories(restaurant_id):
    """Restoranda mavjud kategoriyalar va ulardagi taomlar soni:
    {'Ovqatlar': 8, 'Salatlar': 4, ...}"""
    rows = _q(
        "SELECT IFNULL(category,'Ovqatlar') AS cat, COUNT(*) AS c "
        "FROM menu WHERE restaurant_id=? AND is_available=1 GROUP BY cat",
        (restaurant_id,),
    )
    return {r["cat"]: r["c"] for r in rows}


# ---------- Meta (kichik sozlamalar/belgilar) ----------

def meta_get(key, default=None):
    row = _one("SELECT value FROM meta WHERE key=?", (key,))
    return row["value"] if row else default


def meta_set(key, value):
    _w("INSERT INTO meta (key, value) VALUES (?,?) "
       "ON CONFLICT(key) DO UPDATE SET value=?", (key, value, value))


def get_menu_item(item_id):
    return _one("SELECT * FROM menu WHERE id=?", (item_id,))


def add_menu_item(name, price, description="", restaurant_id=1, category="Ovqatlar"):
    _w("INSERT INTO menu (restaurant_id, name, price, description, category) "
       "VALUES (?,?,?,?,?)",
       (restaurant_id, name, price, description, category or "Ovqatlar"))


def set_menu_item(item_id, **kw):
    if not kw:
        return
    cols = ", ".join(f"{k}=?" for k in kw)
    _w(f"UPDATE menu SET {cols} WHERE id=?", (*kw.values(), item_id))


def del_menu_item(item_id):
    _w("DELETE FROM menu WHERE id=?", (item_id,))
    _w("DELETE FROM carts WHERE item_id=?", (item_id,))


# ---------- Savat ----------

def cart_list(tg_id):
    return _q(
        """SELECT c.item_id, m.name, m.price, m.restaurant_id, c.qty
           FROM carts c JOIN menu m ON m.id = c.item_id
           WHERE c.tg_id=? ORDER BY c.item_id""",
        (tg_id,),
    )


def cart_count(tg_id):
    return _one("SELECT COUNT(*) AS c FROM carts WHERE tg_id=?", (tg_id,))["c"]


def cart_restaurant(tg_id):
    """Savatdagi taomlar qaysi restoranga tegishli (bo'sh bo'lsa None)."""
    row = _one("SELECT restaurant_id FROM carts WHERE tg_id=? LIMIT 1", (tg_id,))
    return row["restaurant_id"] if row else None


def cart_add(tg_id, item_id, qty=1):
    """Savatga qo'shadi. Boshqa restoran taomi bo'lsa — savat tozalanadi."""
    it = get_menu_item(item_id)
    if not it:
        return
    rid = it["restaurant_id"] or 1
    other = cart_restaurant(tg_id)
    if other and other != rid:
        cart_clear(tg_id)
    _w(
        """INSERT INTO carts (tg_id, item_id, restaurant_id, qty) VALUES (?,?,?,?)
           ON CONFLICT(tg_id, item_id) DO UPDATE SET qty = qty + ?""",
        (tg_id, item_id, rid, qty, qty),
    )


def cart_dec(tg_id, item_id):
    row = _one("SELECT qty FROM carts WHERE tg_id=? AND item_id=?", (tg_id, item_id))
    if not row:
        return
    if row["qty"] <= 1:
        cart_remove(tg_id, item_id)
    else:
        _w("UPDATE carts SET qty = qty - 1 WHERE tg_id=? AND item_id=?",
           (tg_id, item_id))


def cart_remove(tg_id, item_id):
    _w("DELETE FROM carts WHERE tg_id=? AND item_id=?", (tg_id, item_id))


def cart_clear(tg_id):
    _w("DELETE FROM carts WHERE tg_id=?", (tg_id,))


# ---------- Buyurtmalar ----------

def create_order(source, customer_name, customer_phone, customer_tg_id,
                 items, food_cost, delivery_fee, collect_food,
                 address_text, lat=None, lon=None, note="", restaurant_id=None,
                 track_token=None):
    now = _now()
    con = _conn()
    try:
        cur = con.execute(
            """INSERT INTO orders (source, status, restaurant_id, customer_name, customer_phone,
               customer_tg_id, items, food_cost, delivery_fee, collect_food,
               address_text, lat, lon, note, created_at, updated_at, track_token)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (source, "new", restaurant_id, customer_name, customer_phone, customer_tg_id,
             json.dumps(items, ensure_ascii=False), food_cost, delivery_fee,
             1 if collect_food else 0, address_text, lat, lon, note, now, now,
             track_token),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


# ---------- Buyurtma voqealari (mijoz uchun xabarlar tarixi — saytda ko'rinadi) ----------

def add_event(order_id, text):
    _w("INSERT INTO order_events (order_id, text, created_at) VALUES (?,?,?)",
       (order_id, text, _now()))


def order_events_list(order_id, limit=50):
    return _q(
        "SELECT * FROM order_events WHERE order_id=? ORDER BY id DESC LIMIT ?",
        (order_id, limit),
    )


def get_order(order_id):
    return _one("SELECT * FROM orders WHERE id=?", (order_id,))


def set_order(order_id, **kw):
    if not kw:
        return
    kw.setdefault("updated_at", _now())
    cols = ", ".join(f"{k}=?" for k in kw)
    _w(f"UPDATE orders SET {cols} WHERE id=?", (*kw.values(), order_id))


def orders_by(kind, limit=30, restaurant_id=None):
    kinds = {
        "new": "status='new'",
        "active": "status IN ('accepted','preparing','ready','with_courier','on_the_way')",
        "delivered": "status='delivered'",
        "cancelled": "status='cancelled'",
        "all": "1=1",
    }
    where = kinds.get(kind, kinds["all"])
    if restaurant_id is not None:
        where += f" AND restaurant_id={int(restaurant_id)}"
    return _q(f"SELECT * FROM orders WHERE {where} ORDER BY id DESC LIMIT ?", (limit,))


def customer_orders(tg_id, limit=10):
    return _q(
        "SELECT * FROM orders WHERE customer_tg_id=? ORDER BY id DESC LIMIT ?",
        (tg_id, limit),
    )


def courier_active_orders(tg_id):
    return _q(
        """SELECT * FROM orders
           WHERE courier_tg_id=? AND status IN ('with_courier','on_the_way')
           ORDER BY id DESC""",
        (tg_id,),
    )


def courier_history(tg_id, limit=20):
    return _q(
        """SELECT * FROM orders
           WHERE courier_tg_id=? AND status IN ('delivered','cancelled')
           ORDER BY id DESC LIMIT ?""",
        (tg_id, limit),
    )


def courier_stats(tg_id, date=None):
    if date:
        rows = _q(
            """SELECT COUNT(*) AS c, COALESCE(SUM(delivery_fee),0) AS fee
               FROM orders
               WHERE courier_tg_id=? AND status='delivered'
                 AND substr(delivered_at,1,10)=?""",
            (tg_id, date),
        )
    else:
        rows = _q(
            """SELECT COUNT(*) AS c, COALESCE(SUM(delivery_fee),0) AS fee
               FROM orders WHERE courier_tg_id=? AND status='delivered'""",
            (tg_id,),
        )
    r = rows[0]
    return {"count": r["c"], "fee": r["fee"]}


# ---------- Hisobotlar ----------

def today_report():
    d = _today()
    all_rows = _q("SELECT * FROM orders WHERE substr(created_at,1,10)=?", (d,))
    delivered = [o for o in all_rows if o["status"] == "delivered"]
    cancelled = [o for o in all_rows if o["status"] == "cancelled"]
    active = [o for o in all_rows if o["status"] not in ("delivered", "cancelled", "new")]
    new = [o for o in all_rows if o["status"] == "new"]
    by_rest = []
    for r in restaurants_list():
        rows_r = [o for o in all_rows if (o["restaurant_id"] or 0) == r["id"]]
        del_r = [o for o in rows_r if o["status"] == "delivered"]
        by_rest.append({
            "id": r["id"],
            "name": r["name"],
            "count": len(rows_r),
            "delivered": len(del_r),
            "food_income": sum(o["food_cost"] or 0 for o in del_r),
        })
    return {
        "total": len(all_rows),
        "delivered": len(delivered),
        "cancelled": len(cancelled),
        "active": len(active),
        "new": len(new),
        "collected": sum((o["food_cost"] or 0) + (o["delivery_fee"] or 0) for o in delivered),
        "delivery_income": sum(o["delivery_fee"] for o in delivered),
        "by_restaurant": by_rest,
    }


def restaurant_today(restaurant_id):
    """Bitta restoran uchun bugungi ko'rsatkichlar."""
    d = _today()
    rows_r = _q(
        "SELECT * FROM orders WHERE substr(created_at,1,10)=? AND restaurant_id=?",
        (d, restaurant_id),
    )
    del_r = [o for o in rows_r if o["status"] == "delivered"]
    return {
        "count": len(rows_r),
        "new": len([o for o in rows_r if o["status"] == "new"]),
        "active": len([o for o in rows_r if o["status"] in ("accepted", "preparing", "ready", "with_courier", "on_the_way")]),
        "delivered": len(del_r),
        "food_income": sum(o["food_cost"] or 0 for o in del_r),
    }


def couriers_today():
    rows = couriers(active_only=True)
    out = []
    for c in rows:
        st = courier_stats(c["tg_id"], date=_today())
        out.append({"tg_id": c["tg_id"], "name": c["name"], **st})
    return out


# ============================================================================
# [3] UMUMIY YORDAMCHILAR
# ============================================================================

_bot_cache = {}


def get_bot(role):
    """role: 'customer' | 'courier' | 'operator' | 'restaurant_1'...'restaurant_5'"""
    if role not in _bot_cache:
        if role.startswith("restaurant_"):
            token = restaurant_token(int(role.split("_")[1]))
        else:
            token = {
                "customer": CUSTOMER_BOT_TOKEN,
                "courier": COURIER_BOT_TOKEN,
                "operator": OPERATOR_BOT_TOKEN,
            }[role]
        _bot_cache[role] = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot_cache[role]


async def send(bot, chat_id, text, kb=None):
    """Xabar yuboradi; xatolik yutiladi (foydalanuvchi botni to'xtatgan bo'lishi mumkin)."""
    try:
        await bot.send_message(chat_id, text, reply_markup=kb)
        return True
    except Exception:
        return False


async def notify_customer(tg_id, text, kb=None):
    if not tg_id:
        return False
    return await send(get_bot("customer"), tg_id, text, kb)


async def notify_customer_order(o, text, kb=None):
    """Mijozga xabar: Telegram buyurtma bo'lsa — Telegramga,
    sayt buyurtmasi bo'lsa — saytga (voqealar tarixiga) yoziladi.
    Ikkala holatda ham tarixga saqlanadi."""
    if not o:
        return False
    try:
        add_event(o["id"], text)
    except Exception:
        pass
    tg = o.get("customer_tg_id")
    if tg:
        return await notify_customer(tg, text, kb)
    return False   # sayt buyurtmasi — xabar saytda ko'rinadi


def source_label(o):
    s = (o or {}).get("source")
    if s == "site":
        return "🌐 Sayt"
    if s == "phone":
        return "☎️ Qo'ng'iroq"
    return "🤖 Telegram"


async def notify_courier(tg_id, text, kb=None):
    if not tg_id:
        return False
    return await send(get_bot("courier"), tg_id, text, kb)


async def notify_operators(text, kb=None):
    ok = False
    for op_id in operator_tg_ids():
        if await send(get_bot("operator"), op_id, text, kb):
            ok = True
    return ok


async def notify_restaurant(restaurant_id, text, kb=None):
    """Restoran boti orqali restoran egasiga xabar yuboradi."""
    if not restaurant_id:
        return False
    r = get_restaurant(restaurant_id)
    if not r or not r["owner_tg_id"]:
        return False
    return await send(get_bot(f"restaurant_{restaurant_id}"), r["owner_tg_id"], text, kb)


def esc(s):
    # Faqat &, <, > belgilarini almashtiramiz (apostrof va qo'shtirnoq matnda qoladi)
    return _html.escape(str(s or ""), quote=False)


def mone(n):
    """100000 -> '100 000 so'm'"""
    try:
        return f"{int(n):,}".replace(",", " ") + " so'm"
    except Exception:
        return "—"


def fmt_dt(s):
    """'2026-09-09 14:30:00' -> '09.09 14:30'"""
    try:
        return s[5:10] + "  " + s[11:16]
    except Exception:
        return s or ""


STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "✅ Qabul qilindi",
    "preparing": "🍳 Tayyorlanmoqda",
    "ready": "🛎 Tayyor (kuryer kutilmoqda)",
    "with_courier": "🛵 Kuryerga berildi",
    "on_the_way": "🏃 Yo'lda",
    "delivered": "✅ Yetkazildi",
    "cancelled": "❌ Bekor qilindi",
}


def status_label(st):
    return STATUS_LABELS.get(st, st)


def items_lines(o):
    try:
        items = json.loads(o.get("items") or "[]")
    except Exception:
        items = []
    if not items:
        return "—"
    lines = []
    for i, it in enumerate(items, 1):
        nm = esc(it.get("name", "—"))
        pr = it.get("price", 0)
        q = it.get("qty", 1)
        if q > 1:
            lines.append(f"{i}) {nm} × {q} = {mone(pr * q)}")
        else:
            lines.append(f"{i}) {nm} — {mone(pr)}")
    return "\n".join(lines)


def collect_amount(o):
    """Kuryer mijozdan qancha pul olishi kerak."""
    total = (o.get("food_cost") or 0) + (o.get("delivery_fee") or 0)
    return total if o.get("collect_food") else (o.get("delivery_fee") or 0)


def map_links(lat, lon):
    if not lat or not lon:
        return ""
    g = f"https://maps.google.com/?q={lat},{lon}"
    ya = f"https://yandex.com/maps/?pt={lon}%2C{lat}&z=17"
    return f"🗺 Google: {g}\n🗺 Yandex: {ya}"


def order_card(o):
    """Buyurtmaning to'liq tavsifi."""
    oid = o["id"]
    st = status_label(o["status"])
    food = o.get("food_cost") or 0
    fee = o.get("delivery_fee") or 0
    total = food + fee
    amount = collect_amount(o)

    r = get_restaurant(o.get("restaurant_id")) if o.get("restaurant_id") else None
    lines = [f"🆔 Buyurtma №{oid}  |  {st}",
             f"🏪 Restoran: {esc(restaurant_name(o.get('restaurant_id')))}",
             f"📥 Manba: {source_label(o)}", ""]
    if r and (r["phone"] or r["address"]):
        if r["phone"]:
            lines.append(f"☎️ Restoran tel: {esc(r['phone'])}")
        if r["address"]:
            lines.append(f"📍 Restoran manzili: {esc(r['address'])}")
        lines.append("")
    lines.append("🛍 Mahsulot(lar):")
    lines.append(items_lines(o))
    lines.append("")
    lines.append(f"🍽 Ovqat narxi: {mone(food)}")
    lines.append(f"🛵 Dostavka: {mone(fee)}")
    lines.append(f"💰 Jami: {mone(total)}")
    if o.get("collect_food"):
        lines.append(f"💵 Mijozdan olinadi: {mone(amount)} (ovqat + dostavka)")
    else:
        lines.append(f"💵 Mijozdan olinadi: {mone(amount)} (faqat dostavka)")
    lines.append("")
    lines.append(f"👤 Mijoz: {esc(o.get('customer_name') or '—')}")
    ph = o.get("customer_phone") or "—"
    lines.append(f"📞 Telefon: {esc(ph)}")
    addr = o.get("address_text") or "—"
    lines.append(f"📍 Manzil: {esc(addr)}")
    ml = map_links(o.get("lat"), o.get("lon"))
    if ml:
        lines.append(ml)
    cname = courier_name(o.get("courier_tg_id")) if o.get("courier_tg_id") else "Tayinlanmagan"
    lines.append(f"🛵 Kuryer: {esc(cname)}")
    lines.append(f"📅 Yaratilgan: {fmt_dt(o.get('created_at'))}")
    if o.get("source") == "phone":
        lines.append("☎️ Manba: qo'ng'iroq orqali")
    return "\n".join(lines)


def simple_kb(rows):
    """[[('text', 'callback')], ...] -> InlineKeyboardMarkup"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
            for row in rows
        ]
    )
# ============================================================================
# [4] MIJOZ BOTI  (@Botjon01_bot)
# ============================================================================

dp_customer = Dispatcher()


class CustReg(StatesGroup):
    name = State()
    phone = State()


class Checkout(StatesGroup):
    way = State()        # joylashuv yoki matnli manzil tanlash
    addr_text = State()  # matnli manzil yozish
    confirm = State()    # tasdiqlash


BTN_MENU = "🍽 Menyu"
BTN_CART = "🛒 Savat"
BTN_MY_ORDERS = "📦 Buyurtmalarim"
BTN_HELP = "ℹ️ Yordam"
BTN_CANCEL = "❌ Bekor qilish"
BTN_TEXT_ADDR = "✍️ Manzilni matnda yozaman"
BTN_LOCATION = "📍 Joylashuvni yuborish"


def cust_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_CART)],
            [KeyboardButton(text=BTN_MY_ORDERS), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def cust_loc_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LOCATION, request_location=True)],
            [KeyboardButton(text=BTN_TEXT_ADDR)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def cust_phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamini yuborish", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def get_registered(message: Message):
    u = get_user(message.from_user.id)
    if u and u["role"] == "customer" and u["status"] == "active":
        return u
    return None


async def send_main(chat_id: int, text: str):
    await get_bot("customer").send_message(chat_id, text, reply_markup=cust_main_kb())


def restaurant_kb():
    """Mijozga restoranlar tanlovini ko'rsatadi."""
    rows = []
    for r in restaurants_list(available_only=True):
        rows.append([(f"🏪 {r['name']}", f"rest:{r['id']}")])
    rows.append([(BTN_CART, "to_cart"), ("🏠 Bosh sahifa", "home")])
    return simple_kb(rows)


def restaurant_text():
    if not restaurants_list(available_only=True):
        return "😔 Hozircha ochiq restoran yo'q. Keyinroq urinib ko'ring."
    return "🍽 <b>Qaysi restorandan buyurtma qilasiz?</b>\nRestoranni tanlang 👇"


def menu_kb(restaurant_id):
    """Kategoriyalar tanlovi: 🍲 Ovqatlar / 🥗 Salatlar / 🥤 Ichimliklar"""
    cats = menu_categories(restaurant_id)
    rows = []
    for code, label, name in CATEGORIES:
        if cats.get(name):
            rows.append([(label, f"cat:{restaurant_id}:{code}")])
    rows.append([(BTN_CART, "to_cart")])
    rows.append([("⬅️ Boshqa restoran", "to_menu")])
    rows.append([("🏠 Bosh sahifa", "home")])
    return simple_kb(rows)


def menu_text(restaurant_id):
    cats = menu_categories(restaurant_id)
    total = sum(cats.values())
    return (f"🏪 <b>{esc(restaurant_name(restaurant_id))}</b>\n"
            f"🍽 Menyu — {total} ta taom\n"
            "Kategoriyani tanlang 👇")


def cat_items_kb(restaurant_id, code):
    """Tanlangan kategoriyadagi taomlar ro'yxati (+ ⬅️ Orqaga)."""
    name = cat_name(code)
    rows = []
    for i, it in enumerate(menu_items(restaurant_id, category=name), 1):
        rows.append([(f"{i}. {it['name']} — {mone(it['price'])}  ➕", f"add:{it['id']}")])
    rows.append([("⬅️ Orqaga", f"cback:{restaurant_id}")])
    rows.append([(BTN_CART, "to_cart"), ("🏠 Bosh sahifa", "home")])
    return simple_kb(rows)


def cat_items_text(restaurant_id, code):
    return (f"🏪 <b>{esc(restaurant_name(restaurant_id))}</b>\n"
            f"{cat_label(code)} — taomni tanlang (savatga qo'shiladi):")


def build_cart(rows):
    rid = rows[0]["restaurant_id"] if rows else None
    lines = ["🛒 <b>Savatingiz:</b>", ""]
    if rid:
        lines.append(f"🏪 Restoran: <b>{esc(restaurant_name(rid))}</b>")
        lines.append("")
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}) {esc(r['name'])} × {r['qty']} = {mone(r['price'] * r['qty'])}")
    food = sum(r["price"] * r["qty"] for r in rows)
    lines.append("")
    lines.append(f"🍽 Jami (ovqat): {mone(food)}")
    lines.append(f"🛵 Dostavka: {mone(DELIVERY_FEE)}")
    lines.append(f"💰 <b>Jami: {mone(food + DELIVERY_FEE)}</b>")
    lines.append("")
    lines.append("💵 To'lov: yetkazilganda naqd pul (ovqat + dostavka)")
    return "\n".join(lines)


def cart_kb(rows):
    kb_rows = []
    for r in rows:
        kb_rows.append([
            ("➖", f"dec:{r['item_id']}"),
            ("➕", f"inc:{r['item_id']}"),
            ("🗑 O'chirish", f"rm:{r['item_id']}"),
        ])
    kb_rows.append([("✅ Buyurtma berish", "chk")])
    kb_rows.append([("⬅️ Menyuga qaytish", "to_menu")])
    return simple_kb(kb_rows)


@dp_customer.message(CommandStart())
async def cust_cmd_start(message: Message, state: FSMContext):
    await state.clear()
    u = get_user(message.from_user.id)
    if u and u["role"] == "customer" and u["status"] == "active":
        await send_main(
            message.chat.id,
            f"Assalomu alaykum, {esc(u['name'])}! 👋\n"
            "Menyudan taom tanlab buyurtma bering — kuryer yetkazib beradi.",
        )
        return
    await state.set_state(CustReg.name)
    await message.answer("👋 Xush kelibsiz!\nIsmingizni yozing:")


@dp_customer.message(CustReg.name, F.text)
async def cust_reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Iltimos, ismingizni to'g'ri yozing:")
        return
    await state.update_data(name=name)
    await state.set_state(CustReg.phone)
    await message.answer(
        f"Rahmat, {esc(name)}! 📱\nTelefon raqamingizni yuboring "
        "(tugma orqali yoki raqamni yozing):",
        reply_markup=cust_phone_kb(),
    )


@dp_customer.message(CustReg.phone, F.contact)
async def cust_reg_phone_contact(message: Message, state: FSMContext):
    await cust_finish_reg(message, state, message.contact.phone_number)


@dp_customer.message(CustReg.phone, F.text)
async def cust_reg_phone_text(message: Message, state: FSMContext):
    if message.text.strip() == BTN_CANCEL:
        await state.clear()
        await message.answer("Ro'yxatdan o'tish bekor qilindi.")
        return
    digits = re.sub(r"\D", "", message.text or "")
    if not (9 <= len(digits) <= 15):
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567 ko'rinishida yozing:")
        return
    t = message.text.strip()
    phone = t if t.startswith("+") else "+" + digits
    await cust_finish_reg(message, state, phone)


async def cust_finish_reg(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    save_user(message.from_user.id, "customer", data.get("name", ""), phone, "active")
    await state.clear()
    await send_main(
        message.chat.id,
        "✅ Ro'yxatdan o'tdingiz!\n\n🍽 Taom tanlash uchun menyuni oching. "
        "Buyurtma holati haqida bu yerda xabar beramiz.",
    )


@dp_customer.message(F.text == BTN_MENU)
async def cust_on_menu(message: Message):
    if not get_registered(message):
        await message.answer("Avval /start bosing va ro'yxatdan o'ting.")
        return
    await message.answer(restaurant_text(), reply_markup=restaurant_kb())


@dp_customer.message(F.text == BTN_CART)
async def cust_on_cart(message: Message):
    if not get_registered(message):
        await message.answer("Avval /start bosing va ro'yxatdan o'ting.")
        return
    rows = cart_list(message.from_user.id)
    if not rows:
        await message.answer("🛒 Savatingiz bo'sh. 🍽 Menyudan taom tanlang.",
                             reply_markup=cust_main_kb())
        return
    await message.answer(build_cart(rows), reply_markup=cart_kb(rows))


@dp_customer.message(F.text == BTN_MY_ORDERS)
async def cust_on_my_orders(message: Message):
    if not get_registered(message):
        await message.answer("Avval /start bosing va ro'yxatdan o'ting.")
        return
    rows = customer_orders(message.from_user.id)
    if not rows:
        await message.answer("📦 Sizda hali buyurtma yo'q.", reply_markup=cust_main_kb())
        return
    kb_rows = []
    for o in rows:
        kb_rows.append([(f"№{o['id']} — {status_label(o['status'])}", f"own:{o['id']}")])
    await message.answer("📦 <b>Sizning buyurtmalaringiz:</b>", reply_markup=simple_kb(kb_rows))


@dp_customer.message(F.text == BTN_HELP)
async def cust_on_help(message: Message):
    if not get_registered(message):
        await message.answer("Avval /start bosing va ro'yxatdan o'ting.")
        return
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "1️⃣ Menyudan taom tanlang\n"
        "2️⃣ Buyurtma bering, manzilni yuboring\n"
        "3️⃣ Kuryer yetkazib beradi — pulni naqd to'laysiz\n\n"
        f"☎️ Operator: <code>{esc(SUPPORT_PHONE)}</code>\n"
        "Qo'ng'iroq qilib ham buyurtma berishingiz mumkin — operator yozib oladi.",
        reply_markup=cust_main_kb(),
    )


async def edit_or_send(cq: CallbackQuery, text: str, kb):
    try:
        await cq.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cq.message.answer(text, reply_markup=kb)


@dp_customer.callback_query(F.data == "to_menu")
async def cust_cb_to_menu(cq: CallbackQuery):
    await cq.answer()
    await edit_or_send(cq, restaurant_text(), restaurant_kb())


@dp_customer.callback_query(F.data.startswith("rest:"))
async def cust_cb_restaurant(cq: CallbackQuery):
    """Mijoz restoranni tanladi — o'sha restoran menyusini ko'rsatamiz."""
    rid = int(cq.data.split(":")[1])
    if not get_menu_item_any(rid):
        await cq.answer("Bu restoranda hozircha menyu yo'q.")
        return
    await cq.answer()
    await edit_or_send(cq, menu_text(rid), menu_kb(rid))


def get_menu_item_any(restaurant_id):
    """Restoranda kamida bitta taom bormi?"""
    return menu_items(restaurant_id, available_only=True)


@dp_customer.callback_query(F.data.startswith("cat:"))
async def cust_cb_category(cq: CallbackQuery):
    """Mijoz kategoriyani tanladi (🥤 Ichimliklar / 🥗 Salatlar / 🍲 Ovqatlar)."""
    parts = cq.data.split(":")
    if len(parts) != 3:
        await cq.answer("Eski tugma — menyuni qaytadan oching.")
        return
    rid, code = int(parts[1]), parts[2]
    if not menu_items(rid, category=cat_name(code)):
        await cq.answer("Bu bo'limda hozircha taom yo'q.")
        return
    await cq.answer()
    await edit_or_send(cq, cat_items_text(rid, code), cat_items_kb(rid, code))


@dp_customer.callback_query(F.data.startswith("cback:"))
async def cust_cb_category_back(cq: CallbackQuery):
    """⬅️ Orqaga — o'sha 3 ta kategoriya tugmasiga qaytadi."""
    rid = int(cq.data.split(":")[1])
    await cq.answer()
    await edit_or_send(cq, menu_text(rid), menu_kb(rid))


@dp_customer.callback_query(F.data == "to_cart")
async def cust_cb_to_cart(cq: CallbackQuery):
    await cq.answer()
    rows = cart_list(cq.from_user.id)
    if not rows:
        await edit_or_send(cq, "🛒 Savatingiz bo'sh. 🍽 Menyudan taom tanlang.", None)
        return
    await edit_or_send(cq, build_cart(rows), cart_kb(rows))


@dp_customer.callback_query(F.data == "home")
async def cust_cb_home(cq: CallbackQuery):
    await cq.answer()
    try:
        await cq.message.delete()
    except Exception:
        pass
    await send_main(cq.message.chat.id, "🏠 Bosh sahifa. Kerakli bo'limni tanlang:")


@dp_customer.callback_query(F.data.startswith("add:"))
async def cust_cb_add(cq: CallbackQuery):
    iid = int(cq.data.split(":")[1])
    it = get_menu_item(iid)
    if not it or not it["is_available"]:
        await cq.answer("Bu taom hozircha mavjud emas.")
        return
    prev = cart_restaurant(cq.from_user.id)
    cart_add(cq.from_user.id, iid)
    if prev and prev != (it["restaurant_id"] or 1):
        await cq.answer(f"✅ Qo'shildi: {it['name']}\n(Eski savat boshqa restorandan edi — tozalandi)")
    else:
        await cq.answer(f"✅ Savatga qo'shildi: {it['name']}")


@dp_customer.callback_query(F.data.startswith(("dec:", "inc:", "rm:")))
async def cust_cb_cart_edit(cq: CallbackQuery):
    action, iid_s = cq.data.split(":")
    iid = int(iid_s)
    if action == "dec":
        cart_dec(cq.from_user.id, iid)
    elif action == "inc":
        cart_add(cq.from_user.id, iid)
    elif action == "rm":
        cart_remove(cq.from_user.id, iid)
    await cq.answer()
    rows = cart_list(cq.from_user.id)
    if not rows:
        await edit_or_send(cq, "🛒 Savatingiz bo'sh. 🍽 Menyudan taom tanlang.", None)
        await cq.message.answer("Kerakli bo'limni tanlang:", reply_markup=cust_main_kb())
        return
    await edit_or_send(cq, build_cart(rows), cart_kb(rows))


# ---------- Buyurtma berish oqimi ----------

@dp_customer.callback_query(F.data == "chk")
async def cust_cb_checkout(cq: CallbackQuery, state: FSMContext):
    rows = cart_list(cq.from_user.id)
    if not rows:
        await cq.answer("Savatingiz bo'sh!")
        return
    await cq.answer()
    await state.set_state(Checkout.way)
    await cq.message.answer(
        "📍 <b>Yetkazib berish manzili</b>\n\n"
        "Quyidagi tugmani bosing — joylashuvingiz avtomatik yuboriladi.\n"
        "Yoki manzilni matnda yozing:",
        reply_markup=cust_loc_kb(),
    )


async def go_confirm(chat_id: int, state: FSMContext, address_text: str, lat=None, lon=None):
    await state.update_data(address_text=address_text, lat=lat, lon=lon)
    rows = cart_list(chat_id)
    if not rows:
        await state.clear()
        return
    food = sum(r["price"] * r["qty"] for r in rows)
    rid = rows[0]["restaurant_id"] or 1
    lines = ["📝 <b>Buyurtmani tekshiring:</b>",
             f"🏪 Restoran: {esc(restaurant_name(rid))}", ""]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}) {esc(r['name'])} × {r['qty']} = {mone(r['price'] * r['qty'])}")
    lines += [
        "",
        f"🍽 Ovqat: {mone(food)}",
        f"🛵 Dostavka: {mone(DELIVERY_FEE)}",
        f"💰 <b>Jami: {mone(food + DELIVERY_FEE)}</b>",
        "",
        f"📍 Manzil: {esc(address_text)}",
    ]
    await state.set_state(Checkout.confirm)
    kb = simple_kb([[("✅ Tasdiqlash", "cfm_ok"), (BTN_CANCEL, "cfm_no")]])
    await get_bot("customer").send_message(chat_id, "\n".join(lines), reply_markup=kb)


@dp_customer.message(F.location, Checkout.way)
async def cust_on_loc_way(message: Message, state: FSMContext):
    loc = message.location
    await go_confirm(message.chat.id, state, "📍 Telegram lokatsiyasi",
                     loc.latitude, loc.longitude)


@dp_customer.message(F.location, Checkout.addr_text)
async def cust_on_loc_addr(message: Message, state: FSMContext):
    loc = message.location
    await go_confirm(message.chat.id, state, "📍 Telegram lokatsiyasi",
                     loc.latitude, loc.longitude)


@dp_customer.message(Checkout.way, F.text == BTN_TEXT_ADDR)
async def cust_on_choose_text_addr(message: Message, state: FSMContext):
    await state.set_state(Checkout.addr_text)
    await message.answer(
        "✍️ Manzilingizni yozing.\n"
        "Masalan: <i>Bobur ko'chasi 12, 3-uy, ko'k darvoza</i>\n\n"
        "Yoki pastdagi 📍 tugma orqali lokatsiya yuborishingiz mumkin.",
        reply_markup=cust_loc_kb(),
    )


@dp_customer.message(Checkout.way, F.text == BTN_CANCEL)
async def cust_on_cancel_way(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Buyurtma bekor qilindi.", reply_markup=cust_main_kb())


@dp_customer.message(Checkout.addr_text, F.text)
async def cust_on_addr_text(message: Message, state: FSMContext):
    if message.text.strip() == BTN_CANCEL:
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=cust_main_kb())
        return
    if len(message.text.strip()) < 3:
        await message.answer("Manzil juda qisqa. Batafsilroq yozing:")
        return
    await go_confirm(message.chat.id, state, message.text.strip())


@dp_customer.callback_query(F.data == "cfm_no")
async def cust_cb_cfm_no(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.answer("Bekor qilindi")
    try:
        await cq.message.edit_text("❌ Buyurtma bekor qilindi.")
    except Exception:
        pass
    await send_main(cq.message.chat.id, "Bosh sahifa. Kerakli bo'limni tanlang:")


@dp_customer.callback_query(F.data == "cfm_ok")
async def cust_cb_cfm_ok(cq: CallbackQuery, state: FSMContext):
    u = get_user(cq.from_user.id)
    if not u:
        await cq.answer("Avval /start orqali ro'yxatdan o'ting.")
        await state.clear()
        return
    data = await state.get_data()
    rows = cart_list(cq.from_user.id)
    if not rows:
        await state.clear()
        await cq.answer("Savatingiz bo'sh!")
        return
    rid = cart_restaurant(cq.from_user.id) or rows[0]["restaurant_id"] or 1
    items = [{"name": r["name"], "price": r["price"], "qty": r["qty"]} for r in rows]
    food = sum(r["price"] * r["qty"] for r in rows)
    oid = create_order(
        source="bot",
        customer_name=u["name"],
        customer_phone=u["phone"],
        customer_tg_id=cq.from_user.id,
        items=items,
        food_cost=food,
        delivery_fee=DELIVERY_FEE,
        collect_food=1,
        address_text=data.get("address_text", ""),
        lat=data.get("lat"),
        lon=data.get("lon"),
        restaurant_id=rid,
    )
    cart_clear(cq.from_user.id)
    await state.clear()
    await cq.answer("✅ Buyurtma yaratildi!")
    o = get_order(oid)
    try:
        await cq.message.edit_text(
            f"✅ <b>Buyurtma yuborildi!</b>\n\n{order_card(o)}",
            reply_markup=simple_kb([[("🔄 Holatni yangilash", f"own:{oid}")]]),
        )
    except Exception:
        pass

    # MUHIM: buyurtma avval OPERATORGA keladi. Operator "Ruxsat berish" bosgach,
    # shundan keyingina restoranga yuboriladi.
    await add_event(oid, "✅ Buyurtmangiz qabul qilindi. Operator tasdiqlashini kuting.")
    kb = simple_kb([
        [("✅ Ruxsat berish", f"acc:{oid}")],
        [("❌ Bekor qilish", f"rej:{oid}")],
    ])
    await notify_operators(
        f"🔔 <b>YANGI BUYURTMA №{oid}</b> — tasdiqlash kerak!\n\n{order_card(o)}\n\n"
        f"➡️ «✅ Ruxsat berish» bosilgach buyurtma <b>{esc(restaurant_name(rid))}</b> "
        f"restoraniga yuboriladi.",
        kb,
    )


@dp_customer.callback_query(F.data.startswith("own:"))
async def cust_cb_own_order(cq: CallbackQuery):
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["customer_tg_id"] != cq.from_user.id:
        await cq.answer("Buyurtma topilmadi.")
        return
    await cq.answer()
    lines = [
        f"🆔 <b>Buyurtma №{oid}</b> — {status_label(o['status'])}",
        "",
    ]
    lines.append(items_lines(o))
    lines.append("")
    lines.append(f"🍽 Ovqat: {mone(o['food_cost'] or 0)}")
    lines.append(f"🛵 Dostavka: {mone(o['delivery_fee'] or 0)}")
    total = (o["food_cost"] or 0) + (o["delivery_fee"] or 0)
    lines.append(f"💰 Jami: {mone(total)}")
    lines.append(f"📍 Manzil: {esc(o.get('address_text') or '—')}")
    ml = map_links(o.get("lat"), o.get("lon"))
    if ml and o["status"] in ("on_the_way", "with_courier", "delivered"):
        lines.append(ml)
    lines.append(f"📅 Vaqt: {fmt_dt(o.get('created_at'))}")
    if o["status"] == "on_the_way":
        lines.append("\n🏃 Kuryer yo'lda — yaqinda yetib boradi!")
    if o["status"] == "delivered":
        lines.append("\n✅ Yetkazildi. Xizmatimizdan foydalanganingiz uchun rahmat!")
    kb = simple_kb([[("🔄 Yangilash", f"own:{oid}")]])
    await edit_or_send(cq, "\n".join(lines), kb)
# ============================================================================
# [5] KURYER BOTI  (@Botxon01_bot)
# ============================================================================

dp_courier = Dispatcher()


class CourReg(StatesGroup):
    name = State()
    phone = State()


BTN_TASKS = "📦 Topshiriqlar"
BTN_INCOME = "💰 Mening daromad"
BTN_HISTORY = "📜 Tarix"


def cour_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TASKS), KeyboardButton(text=BTN_INCOME)],
            [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def cour_phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamini yuborish", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def active_courier(message: Message):
    u = get_user(message.from_user.id)
    if u and u["role"] == "courier" and u["status"] == "active":
        return u
    return None


@dp_courier.message(CommandStart())
async def cour_cmd_start(message: Message, state: FSMContext):
    await state.clear()
    u = get_user(message.from_user.id)
    if u and u["role"] == "courier":
        if u["status"] == "active":
            await message.answer(
                f"Assalomu alaykum, {esc(u['name'])}! 🛵\n"
                "Yangi topshiriq kelganda shu botga xabar keladi.",
                reply_markup=cour_main_kb(),
            )
        elif u["status"] == "pending":
            await message.answer("⏳ So'rovingiz ko'rib chiqilmoqda. Operator tasdiqlashini kuting.")
        else:
            await message.answer("❌ Siz tasdiqlanmadingiz. Operator bilan bog'laning.")
        return
    await state.set_state(CourReg.name)
    await message.answer("🛵 Kuryer bo'lib ishlash uchun ro'yxatdan o'ting.\nIsmingizni yozing:")


@dp_courier.message(CourReg.name, F.text)
async def cour_reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Iltimos, ismingizni to'g'ri yozing:")
        return
    await state.update_data(name=name)
    await state.set_state(CourReg.phone)
    await message.answer(f"Rahmat, {esc(name)}! 📱\nTelefon raqamingizni yuboring:",
                         reply_markup=cour_phone_kb())


@dp_courier.message(CourReg.phone, F.contact)
async def cour_reg_phone_contact(message: Message, state: FSMContext):
    await cour_finish_reg(message, state, message.contact.phone_number)


@dp_courier.message(CourReg.phone, F.text)
async def cour_reg_phone_text(message: Message, state: FSMContext):
    t = (message.text or "").strip()
    if t == BTN_CANCEL:
        await state.clear()
        await message.answer("Ro'yxatdan o'tish bekor qilindi.")
        return
    digits = re.sub(r"\D", "", t)
    if not (9 <= len(digits) <= 15):
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567 ko'rinishida yozing:")
        return
    phone = t if t.startswith("+") else "+" + digits
    await cour_finish_reg(message, state, phone)


async def cour_finish_reg(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    name = data.get("name", "")
    save_user(message.from_user.id, "courier", name, phone, "pending")
    await state.clear()
    await message.answer(
        "✅ So'rovingiz yuborildi. Operator tasdiqlagach, bu yerda xabar beramiz.",
        reply_markup=cour_main_kb(),
    )
    kb = simple_kb([
        [("✅ Tasdiqlash", f"appr:{message.from_user.id}")],
        [("❌ Rad etish", f"rejr:{message.from_user.id}")],
    ])
    await notify_operators(
        f"🛵 <b>Yangi kuryer so'rovi</b>\n\n"
        f"👤 Ism: {esc(name)}\n"
        f"📞 Tel: {esc(phone)}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"👤 Username: @{message.from_user.username or '—'}",
        kb,
    )


def task_kb(orders):
    kb_rows = []
    for o in orders:
        kb_rows.append([(f"№{o['id']} — {status_label(o['status'])}", f"act:{o['id']}")])
    return simple_kb(kb_rows)


@dp_courier.message(F.text == BTN_TASKS)
async def cour_on_tasks(message: Message):
    if not active_courier(message):
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return
    orders = courier_active_orders(message.from_user.id)
    if not orders:
        await message.answer("✅ Hozircha topshiriq yo'q. Yangisi kelganda xabar beramiz.",
                             reply_markup=cour_main_kb())
        return
    await message.answer("📦 <b>Faol topshiriqlaringiz:</b>", reply_markup=task_kb(orders))


def cour_order_kb(o):
    rows = []
    if o["status"] == "with_courier":
        rows.append([("🏃 Yo'lda (ovqatni oldim)", f"croute:{o['id']}")])
        rows.append([("❌ Rad etish", f"cref:{o['id']}")])
    elif o["status"] == "on_the_way":
        rows.append([("✅ Yetkazildi (pulni oldim)", f"cdone:{o['id']}")])
    return simple_kb(rows)


@dp_courier.callback_query(F.data.startswith("act:"))
async def cour_cb_act(cq: CallbackQuery):
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["courier_tg_id"] != cq.from_user.id:
        await cq.answer("Topshiriq topilmadi.")
        return
    await cq.answer()
    text = f"📋 <b>Topshiriq</b>\n\n{order_card(o)}"
    kb = cour_order_kb(o)
    try:
        await cq.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cq.message.answer(text, reply_markup=kb)


@dp_courier.callback_query(F.data.startswith("croute:"))
async def cour_cb_croute(cq: CallbackQuery):
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["courier_tg_id"] != cq.from_user.id:
        await cq.answer("Topshiriq topilmadi.")
        return
    if o["status"] != "with_courier":
        await cq.answer("Holat allaqachon o'zgargan.")
        return
    set_order(oid, status="on_the_way")
    o = get_order(oid)
    await cq.answer("✅ Belgilandi: Yo'lda")
    try:
        await cq.message.edit_text(f"📋 <b>Topshiriq</b>\n\n{order_card(o)}",
                                   reply_markup=cour_order_kb(o))
    except Exception:
        pass
    await notify_customer_order(
        o,
        f"🏃 <b>Buyurtma №{oid}</b> — kuryer yo'lda!\n"
        "Ovqatni yaqinda yetkazib beradi. Kutib turing 😊",
    )
    await notify_operators(f"🏃 Buyurtma №{oid}: kuryer mijoz tomon yo'lda.")


@dp_courier.callback_query(F.data.startswith("cdone:"))
async def cour_cb_cdone(cq: CallbackQuery):
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["courier_tg_id"] != cq.from_user.id:
        await cq.answer("Topshiriq topilmadi.")
        return
    if o["status"] not in ("with_courier", "on_the_way"):
        await cq.answer("Holat allaqachon o'zgargan.")
        return
    set_order(oid, status="delivered",
              delivered_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    o = get_order(oid)
    amount = collect_amount(o)
    fee = o["delivery_fee"] or 0
    await cq.answer("✅ Yetkazildi!")
    try:
        await cq.message.edit_text(
            f"✅ <b>Topshiriq №{oid} bajarildi!</b>\n\n"
            f"Mijozdan olindi: {mone(amount)}\n"
            f"Sizning daromadingiz (dostavka): {mone(fee)}",
        )
    except Exception:
        pass
    await notify_customer_order(
        o,
        f"✅ <b>Buyurtma №{oid} yetkazildi!</b>\n"
        f"To'lov: {mone(amount)} (naqd).\nXizmatimizdan foydalanganingiz uchun rahmat! 🎉",
    )
    cname = courier_name(cq.from_user.id)
    await notify_operators(
        f"✅ <b>Buyurtma №{oid} yetkazildi</b> (kuryer: {esc(cname)})\n"
        f"Mijozdan olindi: {mone(amount)}  |  Kuryer haqi: {mone(fee)}"
    )


@dp_courier.callback_query(F.data.startswith("cref:"))
async def cour_cb_cref(cq: CallbackQuery):
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["courier_tg_id"] != cq.from_user.id:
        await cq.answer("Topshiriq topilmadi.")
        return
    if o["status"] != "with_courier":
        await cq.answer("Holat allaqachon o'zgargan.")
        return
    set_order(oid, status="preparing", courier_tg_id=None)
    await cq.answer("Rad etildi")
    try:
        await cq.message.edit_text(f"❌ Siz №{oid} topshiriqni rad etdingiz.")
    except Exception:
        pass
    kb = simple_kb([[("🛵 Kuryer tayinlash", f"asg:{oid}")]])
    await notify_operators(
        f"⚠️ Kuryer №{oid} topshiriqni <b>rad etdi</b>. Buyurtma yana kuryer kutmoqda.\n\n"
        f"{order_card(o)}",
        kb,
    )


@dp_courier.message(F.text == BTN_INCOME)
async def cour_on_income(message: Message):
    if not active_courier(message):
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    st_all = courier_stats(message.from_user.id)
    st_today = courier_stats(message.from_user.id, date=today)
    await message.answer(
        "💰 <b>Mening daromadim</b>\n\n"
        f"📅 Bugun ({today[5:]}.{today[:4]}):\n"
        f"   Yetkazilgan: {st_today['count']} ta\n"
        f"   Daromad: <b>{mone(st_today['fee'])}</b>\n\n"
        f"📊 Jami:\n"
        f"   Yetkazilgan: {st_all['count']} ta\n"
        f"   Daromad: <b>{mone(st_all['fee'])}</b>\n\n"
        "ℹ️ Kuryer haqi = har bir yetkazilgan buyurtma uchun dostavka puli.",
        reply_markup=cour_main_kb(),
    )


@dp_courier.message(F.text == BTN_HISTORY)
async def cour_on_history(message: Message):
    if not active_courier(message):
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return
    orders = courier_history(message.from_user.id)
    if not orders:
        await message.answer("📜 Tarix hozircha bo'sh.", reply_markup=cour_main_kb())
        return
    lines = ["📜 <b>Topshiriqlar tarixi:</b>", ""]
    for o in orders[:15]:
        mark = "✅" if o["status"] == "delivered" else "❌"
        lines.append(
            f"{mark} №{o['id']} — {fmt_dt(o.get('created_at'))} — "
            f"{status_label(o['status'])} — dostavka {mone(o['delivery_fee'] or 0)}"
        )
    await message.answer("\n".join(lines), reply_markup=cour_main_kb())


@dp_courier.message(F.text == BTN_HELP)
async def cour_on_help(message: Message):
    if not active_courier(message):
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return
    await message.answer(
        "ℹ️ <b>Kuryer uchun yo'riqnoma</b>\n\n"
        "1️⃣ Topshiriq kelganda manzil va summani ko'ring\n"
        "2️⃣ Ovqatni olgach «🏃 Yo'lda» tugmasini bosing\n"
        "3️⃣ Mijozga yetkazib, pulni olgach «✅ Yetkazildi» tugmasini bosing\n\n"
        f"☎️ Operator: <code>{esc(SUPPORT_PHONE)}</code>\n"
        "Manzilni topa olmasangiz — mijozga qo'ng'iroq qiling.",
        reply_markup=cour_main_kb(),
    )
# ============================================================================
# [6] OPERATOR BOTI  (@Botbek01_bot)
# ============================================================================

dp_operator = Dispatcher()

OP_ORDERS = "📋 Buyurtmalar"
OP_PHONE = "➕ Telefon buyurtma"
OP_MENU = "🍽 Menyu boshqaruvi"
OP_COURIERS = "🛵 Kuryerlar"
OP_STATS = "📊 Statistika"


def op_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=OP_ORDERS), KeyboardButton(text=OP_PHONE)],
            [KeyboardButton(text=OP_MENU), KeyboardButton(text=OP_COURIERS)],
            [KeyboardButton(text=OP_STATS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def is_allowed(tg_id):
    """Operator huquqi: OPERATOR_IDS to'ldirilgan bo'lsa — faqat o'shalar,
    aks holda bazadagi operatorlar."""
    if OPERATOR_IDS:
        return tg_id in OPERATOR_IDS
    u = get_user(tg_id)
    return bool(u and u["role"] == "operator" and u["status"] == "active")


class OReg(StatesGroup):
    name = State()


class PhoneO(StatesGroup):
    name = State()
    phone = State()
    rest = State()   # qaysi restoran
    desc = State()
    cost = State()
    mode = State()
    addr = State()
    fee = State()
    confirm = State()


class MAdd(StatesGroup):
    name = State()
    price = State()
    cat = State()    # kategoriya tanlash (Ovqatlar/Salatlar/Ichimliklar)


class MRename(StatesGroup):
    wait = State()


class MPrice(StatesGroup):
    wait = State()


@dp_operator.message(CommandStart())
async def op_cmd_start(message: Message, state: FSMContext):
    await state.clear()
    tg_id = message.from_user.id
    if is_allowed(tg_id):
        if not get_user(tg_id):
            save_user(tg_id, "operator", message.from_user.full_name or "Operator", "", "active")
        await message.answer(
            "👋 Operator paneliga xush kelibsiz!\n"
            "Buyurtmalarni qabul qiling, kuryer tayinlang va nazorat qiling.",
            reply_markup=op_main_kb(),
        )
        return
    has_op = operator_count() > 0 or bool(OPERATOR_IDS)
    if has_op:
        await message.answer("❌ Siz operator emassiz. Ruxsat yo'q.")
        return
    await state.set_state(OReg.name)
    await message.answer(
        "👋 Bu operator boshqaruv boti.\n"
        "Siz birinchi bo'lib ochdingiz — siz operator bo'lasiz.\nIsmingizni yozing:"
    )


@dp_operator.message(OReg.name, F.text)
async def op_oreg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Ismingizni to'g'ri yozing:")
        return
    save_user(message.from_user.id, "operator", name, "", "active")
    await state.clear()
    await message.answer(
        f"✅ Tabriklaymiz, {esc(name)}! Endi siz operatorsiz.\n"
        "Buyurtmalarni qabul qilishni boshlang.",
        reply_markup=op_main_kb(),
    )


# ---------- Buyurtmalar ro'yxati ----------

FILTER_LABELS = {
    "new": "🆕 Yangi",
    "active": "🔵 Faolda",
    "delivered": "✅ Yetkazilgan",
    "cancelled": "❌ Bekor qilingan",
    "all": "📜 Barchasi",
}


def orders_filter_kb():
    rows = []
    for k, label in FILTER_LABELS.items():
        rows.append([(label, f"lst:{k}")])
    return simple_kb(rows)


@dp_operator.message(F.text == OP_ORDERS)
async def op_on_orders(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    await message.answer("📋 <b>Buyurtmalar bo'limi</b> — filterni tanlang:",
                         reply_markup=orders_filter_kb())


@dp_operator.callback_query(F.data.startswith("lst:"))
async def op_cb_lst(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    kind = cq.data.split(":")[1]
    orders = orders_by(kind, limit=20)
    if not orders:
        text = f"{FILTER_LABELS.get(kind, kind)}: hozircha buyurtma yo'q."
        kb = simple_kb([[("⬅️ Orqaga", "lst_back")]])
    else:
        lines = [f"{FILTER_LABELS.get(kind, kind)} — {len(orders)} ta:", ""]
        kb_rows = []
        for o in orders:
            who = esc(o["customer_name"]) or "—"
            lines.append(f"№{o['id']} — {who} — {status_label(o['status'])}")
            kb_rows.append([(f"№{o['id']} — {who[:20]} — {status_label(o['status'])}",
                             f"ov:{o['id']}")])
        text = "\n".join(lines)
        kb_rows.append([("⬅️ Orqaga", "lst_back")])
        kb = simple_kb(kb_rows)
    try:
        await cq.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cq.message.answer(text, reply_markup=kb)


@dp_operator.callback_query(F.data == "lst_back")
async def op_cb_lst_back(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    await cq.answer()
    await cq.message.edit_text("📋 <b>Buyurtmalar bo'limi</b> — filterni tanlang:",
                               reply_markup=orders_filter_kb())


# ---------- Bitta buyurtma: ko'rish + amallar ----------

def op_order_kb(o):
    rows = []
    if o["status"] == "new":
        rows.append([("✅ Qabul qilish", f"acc:{o['id']}")])
        rows.append([("❌ Bekor qilish", f"rej:{o['id']}")])
    elif o["status"] == "accepted":
        rows.append([("🍳 Tayyorlanmoqda", f"prep:{o['id']}")])
        rows.append([("❌ Bekor qilish", f"rej:{o['id']}")])
    elif o["status"] == "preparing":
        rows.append([("🛎 Tayyor deb belgilash", f"rdy:{o['id']}")])
        rows.append([("🛵 Kuryer tayinlash", f"asg:{o['id']}")])
        rows.append([("❌ Bekor qilish", f"rej:{o['id']}")])
    elif o["status"] == "ready":
        rows.append([("🛵 Kuryer tayinlash", f"asg:{o['id']}")])
        rows.append([("❌ Bekor qilish", f"rej:{o['id']}")])
    elif o["status"] == "with_courier":
        rows.append([("✅ Yetkazildi deb belgilash", f"fin:{o['id']}")])
        rows.append([("📨 Topshiriqni qayta yuborish", f"resend:{o['id']}")])
    elif o["status"] == "on_the_way":
        rows.append([("✅ Yetkazildi deb belgilash", f"fin:{o['id']}")])
    return simple_kb(rows)


@dp_operator.callback_query(F.data.startswith("ov:"))
async def op_cb_ov(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o:
        await cq.answer("Buyurtma topilmadi.")
        return
    await cq.answer()
    text = f"📋 <b>Buyurtma</b>\n\n{order_card(o)}"
    kb = op_order_kb(o)
    try:
        await cq.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cq.message.answer(text, reply_markup=kb)


@dp_operator.callback_query(F.data.startswith("acc:"))
async def op_cb_acc(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o:
        await cq.answer("Topilmadi.")
        return
    if o["status"] != "new":
        await cq.answer("Bu buyurtma allaqachon qabul qilingan/bekor qilingan.")
        return
    # RUXSAT BERISH: endi buyurtma RESTORANGA yuboriladi
    set_order(oid, status="accepted")
    o = get_order(oid)
    rkb = simple_kb([
        [("🍳 Tayyorlanmoqda", f"rprep:{oid}")],
        [("🛎 Tayyor", f"rrdy:{oid}")],
        [("❌ Rad etish", f"rrej:{oid}")],
    ])
    sent = await notify_restaurant(
        o.get("restaurant_id"),
        f"🔔 <b>YANGI BUYURTMA №{oid}</b> (operator ruxsat berdi)\n\n{order_card(o)}\n\n"
        "Ovqatni tayyorlang va holatni belgilang 👇",
        rkb,
    )
    await cq.answer(
        "✅ Ruxsat berildi — restoranga yuborildi." if sent else
        "✅ Ruxsat berildi, lekin restoran botiga hali hech kim kirmagan!",
        show_alert=not sent,
    )
    await notify_customer_order(
        o,
        f"✅ <b>Buyurtma №{oid} tasdiqlandi!</b>\n"
        f"Restoran: {esc(restaurant_name(o.get('restaurant_id')))}\n"
        "Ovqat tayyorlanadi, holatni kuzatib turing.",
    )
    if not sent:
        await cq.message.answer(
            f"⚠️ <b>Diqqat!</b> «{esc(restaurant_name(o.get('restaurant_id')))}» botiga "
            f"hali hech kim kirmagan — restoranga qo'ng'iroq qilish kerak "
            f"(tel: {esc((get_restaurant(o.get('restaurant_id')) or {}).get('phone') or '—')})."
        )
    try:
        await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                   reply_markup=op_order_kb(o))
    except Exception:
        pass


@dp_operator.callback_query(F.data.startswith("prep:"))
async def op_cb_prep(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["status"] != "accepted":
        await cq.answer("Avval buyurtmani qabul qilishingiz kerak.")
        return
    set_order(oid, status="preparing")
    o = get_order(oid)
    await cq.answer("🍳 Tayyorlanmoqda")
    await notify_customer_order(o, f"🍳 <b>Buyurtma №{oid}</b>: ovqat tayyorlanmoqda.")
    await notify_restaurant(
        o.get("restaurant_id"),
        f"🍳 <b>Buyurtma №{oid}</b>: operator «Tayyorlanmoqda» deb belgiladi.",
    )
    try:
        await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                   reply_markup=op_order_kb(o))
    except Exception:
        pass


@dp_operator.callback_query(F.data.startswith("rdy:"))
async def op_cb_rdy(cq: CallbackQuery):
    """Buyurtma tayyor — kuryer tayinlash uchun tayyor holatga o'tadi."""
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["status"] not in ("preparing", "accepted"):
        await cq.answer("Bu buyurtmani «Tayyor» deb belgilab bo'lmaydi.")
        return
    set_order(oid, status="ready")
    o = get_order(oid)
    await cq.answer("🛎 Tayyor")
    await notify_customer_order(o,
                                f"🛎 <b>Buyurtma №{oid}</b>: ovqat tayyor! Kuryer kutilmoqda.")
    await notify_restaurant(
        o.get("restaurant_id"),
        f"🛎 <b>Buyurtma №{oid}</b>: operator «Tayyor» deb belgiladi.",
    )
    try:
        await cq.message.edit_text(
            f"📋 <b>Buyurtma</b>\n\n{order_card(o)}\n\n🛵 Endi kuryer tayinlang.",
            reply_markup=op_order_kb(o))
    except Exception:
        pass


@dp_operator.callback_query(F.data.startswith("rej:"))
async def op_cb_rej(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["status"] in ("delivered", "cancelled"):
        await cq.answer("Bu buyurtmani bekor qilib bo'lmaydi.")
        return
    set_order(oid, status="cancelled", courier_tg_id=None)
    o = get_order(oid)
    await cq.answer("❌ Bekor qilindi")
    await notify_customer_order(
        o,
        f"❌ <b>Buyurtma №{oid} bekor qilindi.</b>\n"
        f"Sabab: operator bekor qildi. Agar xato bo'lsa operatorga qo'ng'iroq qiling: {SUPPORT_PHONE}",
    )
    await notify_restaurant(
        o.get("restaurant_id"),
        f"❌ <b>Buyurtma №{oid} bekor qilindi</b> (operator). Tayyorlamang.",
    )
    try:
        await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                   reply_markup=op_order_kb(o))
    except Exception:
        pass


# ---------- Kuryer tayinlash ----------

@dp_operator.callback_query(F.data.startswith("asg:"))
async def op_cb_asg(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["status"] not in ("preparing", "ready", "with_courier"):
        await cq.answer("Avval buyurtmani qabul qiling (holat: Tayyor yoki Tayyorlanmoqda).")
        return
    cs = couriers(active_only=True)
    if not cs:
        await cq.answer("Hozircha faol kuryer yo'q! Kuryer bot orqali ro'yxatdan o'tishi kerak.")
        return
    await cq.answer()
    rows = []
    for c in cs:
        st_today = courier_stats(c["tg_id"], date=datetime.now().strftime("%Y-%m-%d"))
        rows.append([(f"🛵 {c['name']} ({st_today['count']} ta bugun)",
                      f"asg2:{oid}:{c['tg_id']}")])
    rows.append([("⬅️ Orqaga", f"ov:{oid}")])
    await cq.message.edit_text(
        f"🛵 <b>№{oid} buyurtma uchun kuryer tanlang:</b>",
        reply_markup=simple_kb(rows),
    )


@dp_operator.callback_query(F.data.startswith("asg2:"))
async def op_cb_asg2(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    _, oid_s, tg_s = cq.data.split(":")
    oid, ctg = int(oid_s), int(tg_s)
    o = get_order(oid)
    cu = get_user(ctg)
    if not o or not cu:
        await cq.answer("Xatolik. Buyurtma yoki kuryer topilmadi.")
        return
    if o["status"] not in ("preparing", "ready", "with_courier") or cu["status"] != "active":
        await cq.answer("Holat o'zgargan — buyurtmani qaytadan oching.")
        return
    set_order(oid, status="with_courier", courier_tg_id=ctg)
    o = get_order(oid)
    await cq.answer("✅ Kuryer tayinlandi")
    kb = simple_kb([
        [("🏃 Yo'lda (ovqatni oldim)", f"croute:{oid}")],
        [("❌ Rad etish", f"cref:{oid}")],
    ])
    await notify_courier(
        ctg,
        f"🛵 <b>Yangi topshiriq — buyurtma №{oid}!</b>\n\n{order_card(o)}\n\n"
        "👇 Ovqatni olgach «Yo'lda», yetkazgach «Yetkazildi» tugmasini bosing.",
        kb,
    )
    await notify_customer_order(
        o,
        f"🛵 <b>Buyurtma №{oid}</b>: kuryer biriktirildi ({esc(cu['name'])}). Tez orada yetkaziladi!",
    )
    await notify_restaurant(
        o.get("restaurant_id"),
        f"🛵 <b>Buyurtma №{oid}</b>: kuryer <b>{esc(cu['name'])}</b> ovqatni olib ketishga keladi.",
    )
    try:
        await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                   reply_markup=op_order_kb(o))
    except Exception:
        pass


@dp_operator.callback_query(F.data.startswith("resend:"))
async def op_cb_resend(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or not o.get("courier_tg_id"):
        await cq.answer("Kuryer tayinlanmagan.")
        return
    kb = simple_kb([
        [("🏃 Yo'lda (ovqatni oldim)", f"croute:{oid}")],
        [("❌ Rad etish", f"cref:{oid}")],
    ])
    await notify_courier(
        o["courier_tg_id"],
        f"🔔 <b>Eslatma — buyurtma №{oid} sizga biriktirilgan!</b>\n\n{order_card(o)}\n\n"
        "Iltimos, topshiriqni ko'ring.",
        kb,
    )
    await cq.answer("📨 Qayta yuborildi")


@dp_operator.callback_query(F.data.startswith("fin:"))
async def op_cb_fin(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    oid = int(cq.data.split(":")[1])
    o = get_order(oid)
    if not o or o["status"] not in ("with_courier", "on_the_way"):
        await cq.answer("Bu buyurtmani yetkazildi deb belgilab bo'lmaydi.")
        return
    set_order(oid, status="delivered",
              delivered_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    o = get_order(oid)
    amount = collect_amount(o)
    await cq.answer("✅ Yetkazildi")
    await notify_customer_order(
        o,
        f"✅ <b>Buyurtma №{oid} yetkazildi!</b>\nTo'lov: {mone(amount)}.\n"
        "Xizmatimizdan foydalanganingiz uchun rahmat! 🎉",
    )
    if o.get("courier_tg_id"):
        await notify_courier(
            o["courier_tg_id"],
            f"✅ Buyurtma №{oid} yetkazildi deb belgilandi. "
            f"Daromadingiz: {mone(o['delivery_fee'] or 0)}",
        )
    await notify_restaurant(
        o.get("restaurant_id"),
        f"✅ <b>Buyurtma №{oid}</b> mijozga yetkazildi. Rahmat!",
    )
    try:
        await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                   reply_markup=op_order_kb(o))
    except Exception:
        pass


# ---------- Kuryerlarni tasdiqlash ----------

@dp_operator.callback_query(F.data.startswith("appr:"))
async def op_cb_appr(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    ctg = int(cq.data.split(":")[1])
    cu = get_user(ctg)
    if not cu:
        await cq.answer("Kuryer topilmadi.")
        return
    set_user(ctg, status="active")
    await cq.answer("✅ Tasdiqlandi")
    await notify_courier(
        ctg,
        f"✅ <b>Tabriklaymiz, {esc(cu['name'])}!</b> Siz kuryer sifatida tasdiqlandingiz. "
        "Endi topshiriqlar kela boshlaydi! 🛵",
    )
    try:
        await cq.message.edit_text(f"✅ Kuryer tasdiqlandi: {esc(cu['name'])}")
    except Exception:
        pass


@dp_operator.callback_query(F.data.startswith("rejr:"))
async def op_cb_rejr(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    ctg = int(cq.data.split(":")[1])
    cu = get_user(ctg)
    if not cu:
        await cq.answer("Kuryer topilmadi.")
        return
    set_user(ctg, status="rejected")
    await cq.answer("❌ Rad etildi")
    await notify_courier(ctg, "❌ Afsuski, sizning so'rovingiz rad etildi.")
    try:
        await cq.message.edit_text(f"❌ Kuryer rad etildi: {esc(cu['name'])}")
    except Exception:
        pass


@dp_operator.message(F.text == OP_COURIERS)
async def op_on_couriers(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    await op_show_couriers(message)


async def op_show_couriers(message: Message):
    today = datetime.now().strftime("%Y-%m-%d")
    cs = couriers()
    if not cs:
        await message.answer("Hozircha kuryerlar yo'q. Kuryerlar o'z boti orqali ro'yxatdan o'tadi.",
                             reply_markup=op_main_kb())
        return
    lines = ["🛵 <b>Kuryerlar:</b>", ""]
    kb_rows = []
    for c in cs:
        if c["status"] == "active":
            st = courier_stats(c["tg_id"], date=today)
            lines.append(
                f"✅ {esc(c['name'])} — {esc(c['phone'])} — bugun {st['count']} ta, {mone(st['fee'])}"
            )
        elif c["status"] == "pending":
            lines.append(f"⏳ {esc(c['name'])} — {esc(c['phone'])} (tasdiqlash kutilmoqda)")
            kb_rows.append([(f"✅ {c['name']}", f"appr:{c['tg_id']}"),
                            (f"❌ {c['name']}", f"rejr:{c['tg_id']}")])
        else:
            lines.append(f"❌ {esc(c['name'])} — {esc(c['phone'])} (rad etilgan)")
    text = "\n".join(lines)
    kb = simple_kb(kb_rows) if kb_rows else None
    await message.answer(text, reply_markup=kb or op_main_kb())


@dp_operator.message(F.text == OP_STATS)
async def op_on_stats(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    r = today_report()
    lines = [
        "📊 <b>Bugungi statistika</b>", "",
        f"🆕 Yangi: {r['new']}",
        f"🔵 Faolda: {r['active']}",
        f"✅ Yetkazilgan: {r['delivered']}",
        f"❌ Bekor qilingan: {r['cancelled']}",
        f"📦 Jami buyurtma: {r['total']}",
        "",
        f"💰 Yig'ilgan (ovqat + dostavka): {mone(r['collected'])}",
        f"🛵 Dostavka daromadi: {mone(r['delivery_income'])}",
        "",
        "🛵 <b>Kuryerlar (bugun):</b>",
    ]
    ct = couriers_today()
    if ct:
        for c in ct:
            lines.append(f"• {esc(c['name'])}: {c['count']} ta — {mone(c['fee'])}")
    else:
        lines.append("• Hozircha kuryer yo'q")

    lines.append("")
    lines.append("🏪 <b>Restoranlar (bugun):</b>")
    by = r.get("by_restaurant", [])
    has_rest = False
    for b in by:
        if b["count"] == 0:
            continue
        has_rest = True
        lines.append(f"• {esc(b['name'])}: {b['count']} ta buyurtma, "
                     f"{b['delivered']} yetkazilgan — {mone(b['food_income'])}")
    if not has_rest:
        lines.append("• Bugun restoranlardan buyurtma yo'q")
    await message.answer("\n".join(lines), reply_markup=op_main_kb())

# ---------- Menyu boshqaruvi ----------

def _split3(data):
    """'mtog:3:12' -> ('mtog', 3, 12); eski format bo'lsa (None, None, None)."""
    parts = data.split(":")
    if len(parts) != 3:
        return None, None, None
    try:
        return parts[0], int(parts[1]), int(parts[2])
    except ValueError:
        return None, None, None


def op_restaurants_kb():
    rows = []
    for r in restaurants_list():
        mark = "✅" if r["is_available"] else "🚫"
        owner = "✅ bor" if r["owner_tg_id"] else "⚠️ yo'q"
        rows.append([(f"{mark} {r['name']} (ega: {owner})", f"omr:{r['id']}")])
    return simple_kb(rows)


def op_menu_text(rid):
    items = menu_items(rid, available_only=False)
    lines = [f"🍽 <b>{esc(restaurant_name(rid))} — menyu boshqaruvi:</b>", ""]
    for code, label, name in CATEGORIES:
        cat_items = [it for it in items if (it.get("category") or CAT_FOODS) == name]
        if not cat_items:
            continue
        lines.append(f"<b>{label}</b>")
        for it in cat_items:
            mark = "✅" if it["is_available"] else "🚫"
            lines.append(f"  {mark} {esc(it['name'])} — {mone(it['price'])}")
        lines.append("")
    if not items:
        lines.append("(menyu bo'sh)")
    return "\n".join(lines)


def op_menu_kb(rid):
    rows = []
    for code, label, name in CATEGORIES:
        cat_items = [it for it in menu_items(rid, available_only=False)
                     if (it.get("category") or CAT_FOODS) == name]
        for it in cat_items:
            rows.append([(f"{'✅' if it['is_available'] else '🚫'} {it['name']} — {mone(it['price'])}",
                          f"mtog:{rid}:{it['id']}")])
            rows.append([("✏️ Nomi", f"mnm:{rid}:{it['id']}"),
                         ("💰 Narxi", f"mpr:{rid}:{it['id']}"),
                         ("🗂 Kategoriya", f"mcat:{rid}:{it['id']}"),
                         ("🗑 O'chirish", f"mdel:{rid}:{it['id']}")])
    rows.append([("➕ Yangi taom qo'shish", f"madd:{rid}")])
    rows.append([("⬅️ Restoranlar", "omr_back")])
    return simple_kb(rows)


@dp_operator.callback_query(F.data.startswith("mcat:"))
async def op_cb_mcat(cq: CallbackQuery):
    """Taom kategoriyasini o'zgartirish (Ovqatlar/Salatlar/Ichimliklar)."""
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    _, rid, iid = _split3(cq.data)
    if rid is None:
        await cq.answer("Eski tugma — menyuni qaytadan oching.")
        return
    it = get_menu_item(iid)
    if not it:
        await cq.answer("Topilmadi.")
        return
    rows = [[(label, f"mset:{rid}:{iid}:{code}")] for code, label, _n in CATEGORIES]
    await cq.answer()
    await cq.message.answer(
        f"«{esc(it['name'])}» uchun kategoriyani tanlang "
        f"(hozir: {cat_label(cat_code(it.get('category') or CAT_FOODS))}):",
        reply_markup=simple_kb(rows),
    )


@dp_operator.callback_query(F.data.startswith("mset:"))
async def op_cb_mset(cq: CallbackQuery):
    parts = cq.data.split(":")
    if len(parts) != 4:
        await cq.answer("Eski tugma.")
        return
    _, rid_s, iid_s, code = parts
    rid, iid = int(rid_s), int(iid_s)
    set_menu_item(iid, category=cat_name(code))
    await cq.answer(f"🗂 {cat_label(code)}")
    await edit_menu_show(cq, rid)


@dp_operator.message(F.text == OP_MENU)
async def op_on_menu_admin(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    await message.answer(
        "🍽 <b>Qaysi restoran menyusini boshqarasiz?</b>\nRestoranni tanlang 👇",
        reply_markup=op_restaurants_kb(),
    )


async def edit_menu_show(cq: CallbackQuery, rid):
    try:
        await cq.message.edit_text(op_menu_text(rid), reply_markup=op_menu_kb(rid))
    except Exception:
        await cq.message.answer(op_menu_text(rid), reply_markup=op_menu_kb(rid))


@dp_operator.callback_query(F.data.startswith("omr:"))
async def op_cb_omr(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    rid = int(cq.data.split(":")[1])
    await cq.answer()
    await edit_menu_show(cq, rid)


@dp_operator.callback_query(F.data == "omr_back")
async def op_cb_omr_back(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    await cq.answer()
    text = "🍽 <b>Qaysi restoran menyusini boshqarasiz?</b>\nRestoranni tanlang 👇"
    try:
        await cq.message.edit_text(text, reply_markup=op_restaurants_kb())
    except Exception:
        await cq.message.answer(text, reply_markup=op_restaurants_kb())


@dp_operator.callback_query(F.data.startswith("madd:"))
async def op_cb_madd(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    rid = int(cq.data.split(":")[1])
    await state.update_data(rid=rid)
    await state.set_state(MAdd.name)
    await cq.answer()
    await cq.message.answer(
        f"🍽 «{esc(restaurant_name(rid))}» uchun yangi taom nomini yozing:"
    )


@dp_operator.message(MAdd.name, F.text)
async def op_madd_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Nom noto'g'ri, qayta yozing:")
        return
    await state.update_data(name=name)
    await state.set_state(MAdd.price)
    await message.answer(f"«{esc(name)}» narxini so'mda yozing (masalan: 30000):")


@dp_operator.message(MAdd.price, F.text)
async def op_madd_price(message: Message, state: FSMContext):
    digits = re.sub(r"\D", "", message.text or "")
    if not digits:
        await message.answer("Narxni raqamda yozing (masalan: 30000):")
        return
    data = await state.get_data()
    rid = data.get("rid", 1)
    await state.update_data(price=int(digits))
    await state.set_state(MAdd.cat)
    rows = [[(label, f"maddcat:{code}")] for code, label, _n in CATEGORIES]
    await message.answer(
        f"🗂 «{esc(data['name'])}» qaysi kategoriyaga qo'shilsin?",
        reply_markup=simple_kb(rows),
    )


@dp_operator.callback_query(F.data.startswith("maddcat:"))
async def op_cb_maddcat(cq: CallbackQuery, state: FSMContext):
    code = cq.data.split(":")[1]
    data = await state.get_data()
    rid = data.get("rid", 1)
    if not data.get("name") or not data.get("price"):
        await cq.answer("Ma'lumot yo'qolgan — qaytadan boshlang.")
        return
    add_menu_item(data["name"], int(data["price"]), restaurant_id=rid, category=cat_name(code))
    await state.clear()
    await cq.answer("✅ Qo'shildi")
    try:
        await cq.message.edit_text(
            f"✅ Taom qo'shildi: {esc(data['name'])} — {mone(int(data['price']))}\n"
            f"🗂 {cat_label(code)}")
    except Exception:
        pass
    await cq.message.answer(op_menu_text(rid), reply_markup=op_menu_kb(rid))


@dp_operator.callback_query(F.data.startswith("mtog:"))
async def op_cb_mtog(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    _, rid, iid = _split3(cq.data)
    if rid is None:
        await cq.answer("Eski tugma — menyuni qaytadan oching.")
        return
    it = get_menu_item(iid)
    if not it:
        await cq.answer("Topilmadi.")
        return
    set_menu_item(iid, is_available=0 if it["is_available"] else 1)
    await cq.answer("✅" if not it["is_available"] else "🚫")
    await edit_menu_show(cq, rid)


@dp_operator.callback_query(F.data.startswith("mnm:"))
async def op_cb_mnm(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    _, rid, iid = _split3(cq.data)
    if rid is None:
        await cq.answer("Eski tugma — menyuni qaytadan oching.")
        return
    it = get_menu_item(iid)
    if not it:
        await cq.answer("Topilmadi.")
        return
    await state.update_data(iid=iid, rid=rid)
    await state.set_state(MRename.wait)
    await cq.answer()
    await cq.message.answer(f"Hozirgi nom: {esc(it['name'])}. Yangi nomni yozing:")


@dp_operator.message(MRename.wait, F.text)
async def op_mrename_wait(message: Message, state: FSMContext):
    data = await state.get_data()
    set_menu_item(data["iid"], name=message.text.strip())
    rid = data.get("rid", 1)
    await state.clear()
    await message.answer("✅ Nom yangilandi.", reply_markup=op_main_kb())
    await message.answer(op_menu_text(rid), reply_markup=op_menu_kb(rid))


@dp_operator.callback_query(F.data.startswith("mpr:"))
async def op_cb_mpr(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    _, rid, iid = _split3(cq.data)
    if rid is None:
        await cq.answer("Eski tugma — menyuni qaytadan oching.")
        return
    it = get_menu_item(iid)
    if not it:
        await cq.answer("Topilmadi.")
        return
    await state.update_data(iid=iid, rid=rid)
    await state.set_state(MPrice.wait)
    await cq.answer()
    await cq.message.answer(f"Hozirgi narx: {mone(it['price'])}. Yangi narxni so'mda yozing:")


@dp_operator.message(MPrice.wait, F.text)
async def op_mprice_wait(message: Message, state: FSMContext):
    digits = re.sub(r"\D", "", message.text or "")
    if not digits:
        await message.answer("Narxni raqamda yozing:")
        return
    data = await state.get_data()
    set_menu_item(data["iid"], price=int(digits))
    rid = data.get("rid", 1)
    await state.clear()
    await message.answer("✅ Narx yangilandi.", reply_markup=op_main_kb())
    await message.answer(op_menu_text(rid), reply_markup=op_menu_kb(rid))


@dp_operator.callback_query(F.data.startswith("mdel:"))
async def op_cb_mdel(cq: CallbackQuery):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    _, rid, iid = _split3(cq.data)
    if rid is None:
        await cq.answer("Eski tugma — menyuni qaytadan oching.")
        return
    del_menu_item(iid)
    await cq.answer("🗑 O'chirildi")
    await edit_menu_show(cq, rid)


# ---------- Telefon orqali buyurtma ----------

@dp_operator.message(F.text == OP_PHONE)
async def op_on_phone_order(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    await state.set_state(PhoneO.name)
    await message.answer(
        "☎️ <b>Qo'ng'iroq orqali buyurtma</b>\n\n"
        "Mijozdan so'rang va quyidagilarni yozing.\n"
        "1️⃣ Mijozning ismi:",
        reply_markup=op_main_kb(),
    )


@dp_operator.message(PhoneO.name, F.text)
async def op_po_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PhoneO.phone)
    await message.answer("2️⃣ Mijozning telefon raqami (masalan: +998901234567):")


@dp_operator.message(PhoneO.phone, F.text)
async def op_po_phone(message: Message, state: FSMContext):
    digits = re.sub(r"\D", "", message.text or "")
    if not (9 <= len(digits) <= 15):
        await message.answer("Raqam noto'g'ri. Masalan: +998901234567 ko'rinishida yozing:")
        return
    phone = message.text.strip() if message.text.strip().startswith("+") else "+" + digits
    await state.update_data(phone=phone)
    await state.set_state(PhoneO.rest)
    kb = simple_kb([[("🏪 " + r["name"], f"po_rest:{r['id']}")] for r in restaurants_list(available_only=True)])
    await message.answer("3️⃣ Mijoz qaysi restorandan buyurtma qiladi?", reply_markup=kb)


@dp_operator.callback_query(F.data.startswith("po_rest:"))
async def op_cb_po_rest(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    rid = int(cq.data.split(":")[1])
    await state.update_data(rid=rid)
    await state.set_state(PhoneO.desc)
    await cq.answer()
    await cq.message.edit_text(
        f"✅ Restoran: <b>{esc(restaurant_name(rid))}</b>\n\n"
        "4️⃣ Nima olib kelish kerak? (masalan: 100 minglik osh):"
    )


@dp_operator.message(PhoneO.desc, F.text)
async def op_po_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text.strip())
    await state.set_state(PhoneO.cost)
    await message.answer(
        "5️⃣ Ovqatning summasi (so'm) — kuryer qancha pulga sotib oladi?\n"
        "Masalan: 100000. Agar mijoz restoranda to'lagan bo'lsa 0 deb yozing:"
    )


@dp_operator.message(PhoneO.cost, F.text)
async def op_po_cost(message: Message, state: FSMContext):
    digits = re.sub(r"\D", "", message.text or "")
    if not digits:
        await message.answer("Summani raqamda yozing (masalan: 100000):")
        return
    await state.update_data(cost=int(digits))
    await state.set_state(PhoneO.mode)
    kb = simple_kb([
        [("🛒 Kuryer o'zi sotib oladi (B)", "po_mode:1")],
        [("🚚 Mijoz restoranda to'lagan (A)", "po_mode:0")],
    ])
    await message.answer(
        "6️⃣ Ovqat pulini kim to'laydi?\n\n"
        "<b>A</b>) Mijoz restoranda o'zi to'lagan — kuryer faqat yetkazadi (dostavka puli olinadi).\n"
        "<b>B</b>) Kuryer ovqatni o'z puliga/kassa puliga sotib oladi — "
        "yetkazganda ovqat + dostavka olinadi.",
        reply_markup=kb,
    )


@dp_operator.callback_query(F.data.startswith("po_mode:"))
async def op_cb_po_mode(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    collect = int(cq.data.split(":")[1])
    await state.update_data(collect=collect)
    await state.set_state(PhoneO.addr)
    await cq.answer()
    await cq.message.edit_text(
        "7️⃣ Manzilni yozing yoki 📍 lokatsiya yuboring.\n"
        "Masalan: <i>Bobur ko'chasi 12, ko'k darvoza, 3-uy</i>"
    )


@dp_operator.message(PhoneO.addr, F.text)
async def op_po_addr_text(message: Message, state: FSMContext):
    await state.update_data(addr=message.text.strip())
    await op_ask_fee(message, state)


@dp_operator.message(PhoneO.addr, F.location)
async def op_po_addr_loc(message: Message, state: FSMContext):
    loc = message.location
    await state.update_data(addr="📍 Telegram lokatsiyasi", lat=loc.latitude, lon=loc.longitude)
    await op_ask_fee(message, state)


async def op_ask_fee(message: Message, state: FSMContext):
    await state.set_state(PhoneO.fee)
    kb = simple_kb([[("✅ Standart — " + mone(DELIVERY_FEE), "po_fee")]])
    await message.answer(
        f"8️⃣ Dostavka puli?\nStandart: {mone(DELIVERY_FEE)}.\n"
        "Standartni tanlang yoki boshqa summani yozing:",
        reply_markup=kb,
    )


@dp_operator.callback_query(F.data == "po_fee")
async def op_cb_po_fee(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    await state.update_data(fee=DELIVERY_FEE)
    await cq.answer()
    await op_show_po_summary(cq.message, state)


@dp_operator.message(PhoneO.fee, F.text)
async def op_po_fee_text(message: Message, state: FSMContext):
    digits = re.sub(r"\D", "", message.text or "")
    if not digits:
        await message.answer("Summani raqamda yozing yoki standart tugmani bosing:")
        return
    await state.update_data(fee=int(digits))
    await op_show_po_summary(message, state)


async def op_show_po_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    food = data.get("cost", 0)
    fee = data.get("fee", 0)
    total = food + fee
    collect_mode = "B) kuryer sotib oladi" if data.get("collect") else "A) mijoz restoranda to'lagan"
    lines = [
        "📝 <b>Buyurtmani tekshiring:</b>", "",
        f"👤 Mijoz: {esc(data.get('name', ''))}",
        f"📞 Tel: {esc(data.get('phone', ''))}",
        f"🏪 Restoran: {esc(restaurant_name(data.get('rid')))}",
        f"🛍 Tavsif: {esc(data.get('desc', ''))}",
        f"🍽 Ovqat summasi: {mone(food)}",
        f"🛵 Dostavka: {mone(fee)}",
        f"💰 Jami: {mone(total)}",
        f"💳 Holat: {collect_mode}",
        f"📍 Manzil: {esc(data.get('addr', ''))}",
    ]
    if data.get("lat"):
        lines.append(map_links(data["lat"], data["lon"]))
    kb = simple_kb([[("✅ Yaratish", "po_ok"), (BTN_CANCEL, "po_no")]])
    await state.set_state(PhoneO.confirm)
    await message.answer("\n".join(lines), reply_markup=kb)


@dp_operator.callback_query(F.data == "po_no")
async def op_cb_po_no(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    await state.clear()
    await cq.answer("Bekor qilindi")
    try:
        await cq.message.edit_text("❌ Qo'ng'iroq buyurtmasi bekor qilindi.")
    except Exception:
        pass


@dp_operator.callback_query(F.data == "po_ok")
async def op_cb_po_ok(cq: CallbackQuery, state: FSMContext):
    if not is_allowed(cq.from_user.id):
        await cq.answer("Ruxsat yo'q.")
        return
    data = await state.get_data()
    collect = data.get("collect", 1)
    oid = create_order(
        source="phone",
        customer_name=data.get("name", "—"),
        customer_phone=data.get("phone", ""),
        customer_tg_id=None,
        items=[{"name": data.get("desc", "Buyurtma"), "price": data.get("cost", 0), "qty": 1}],
        food_cost=data.get("cost", 0),
        delivery_fee=data.get("fee", DELIVERY_FEE),
        collect_food=collect,
        address_text=data.get("addr", ""),
        lat=data.get("lat"),
        lon=data.get("lon"),
        note="Qo'ng'iroq orqali qabul qilindi",
        restaurant_id=data.get("rid"),
    )
    await state.clear()
    await cq.answer("✅ Buyurtma yaratildi")
    o = get_order(oid)
    text = f"✅ <b>Buyurtma №{oid} yaratildi</b>\n\n{order_card(o)}"
    try:
        await cq.message.edit_text(text, reply_markup=op_order_kb(o))
    except Exception:
        await cq.message.answer(text, reply_markup=op_order_kb(o))


# ============================================================================
# [7] RESTORAN BOTLARI (5 ta bot — har bir restoran o'z buyurtmasini qabul qiladi)
# ============================================================================

R_ORDERS = "📋 Buyurtmalar"
R_MENU = "🍽 Menyu"
R_INFO = "🏪 Ma'lumotlar"
R_HELP = "ℹ️ Yordam"


class RReg(StatesGroup):
    rest_name = State()
    contact = State()
    phone = State()
    address = State()


class REdit(StatesGroup):
    wait = State()


class RMenuAdd(StatesGroup):
    name = State()
    price = State()
    cat = State()    # kategoriya tanlash


class RMenuRename(StatesGroup):
    wait = State()


class RMenuPrice(StatesGroup):
    wait = State()


R_FILTERS = {
    "new": "🆕 Yangi",
    "active": "🟠 Faolda",
    "delivered": "✅ Yetkazilgan",
    "cancelled": "❌ Bekor qilingan",
    "all": "📜 Barchasi",
}


def build_restaurant_dispatcher(rid: int) -> Dispatcher:
    """Har bir restoran uchun alohida dispatcher yaratadi."""
    dp = Dispatcher()

    # ---------- yordamchi ----------

    def r_main_kb():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=R_ORDERS), KeyboardButton(text=R_MENU)],
                [KeyboardButton(text=R_INFO), KeyboardButton(text=R_HELP)],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )

    def r_phone_kb():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Telefon raqamini yuborish", request_contact=True)],
                [KeyboardButton(text=BTN_CANCEL)],
            ],
            resize_keyboard=True,
        )

    def is_owner(tg_id):
        r = get_restaurant(rid)
        return bool(r and r["owner_tg_id"] == tg_id)

    def owns_order(o):
        return bool(o and (o.get("restaurant_id") or 0) == rid)

    def r_order_kb(o):
        rows = []
        if o["status"] == "new":
            # Operator tasdiqlamagan buyurtma — restoran hech narsa qilmaydi
            rows.append([("⏳ Operator tasdiqlashini kuting", f"rwait:{o['id']}")])
        elif o["status"] == "accepted":
            # operator ruxsat bergan — restoran tayyorlashni boshlaydi
            rows.append([("🍳 Tayyorlanmoqda", f"rprep:{o['id']}")])
            rows.append([("🛎 Tayyor (kuryerga)", f"rrdy:{o['id']}")])
            rows.append([("❌ Rad etish", f"rrej:{o['id']}")])
        elif o["status"] == "preparing":
            rows.append([("🛎 Tayyor (kuryerga tayyor)", f"rrdy:{o['id']}")])
        return simple_kb(rows)

    def r_menu_text():
        items = menu_items(rid, available_only=False)
        lines = [f"🍽 <b>{esc(restaurant_name(rid))} — menyu:</b>", ""]
        for code, label, name in CATEGORIES:
            cat_items = [it for it in items if (it.get("category") or CAT_FOODS) == name]
            if not cat_items:
                continue
            lines.append(f"<b>{label}</b>")
            for it in cat_items:
                lines.append(
                    f"  {'✅' if it['is_available'] else '🚫'} {esc(it['name'])} — {mone(it['price'])}"
                )
            lines.append("")
        if not items:
            lines.append("(menyu bo'sh — ➕ Yangi taom qo'shing)")
        return "\n".join(lines)

    def r_menu_kb():
        rows = []
        for code, label, name in CATEGORIES:
            cat_items = [it for it in menu_items(rid, available_only=False)
                         if (it.get("category") or CAT_FOODS) == name]
            for it in cat_items:
                rows.append([(f"{'✅' if it['is_available'] else '🚫'} {it['name']} — {mone(it['price'])}",
                              f"rmtog:{it['id']}")])
                rows.append([("✏️ Nomi", f"rmnm:{it['id']}"),
                             ("💰 Narxi", f"rmpr:{it['id']}"),
                             ("🗂 Kategoriya", f"rcat:{it['id']}"),
                             ("🗑 O'chirish", f"rmdel:{it['id']}")])
        rows.append([("➕ Yangi taom qo'shish", "rmadd")])
        return simple_kb(rows)

    async def r_send_menu(target, edit=False):
        text, kb = r_menu_text(), r_menu_kb()
        if edit:
            try:
                await target.edit_text(text, reply_markup=kb)
                return
            except Exception:
                pass
        await target.answer(text, reply_markup=kb)

    async def r_send_info(message):
        r = get_restaurant(rid)
        status = "🟢 Ochiq" if r["is_available"] else "🔴 Yopiq"
        text = (
            f"🏪 <b>{esc(r['name'])}</b>\n\n"
            f"👤 Mas'ul: {esc(r['contact_name'] or '—')}\n"
            f"📞 Telefon: {esc(r['phone'] or '—')}\n"
            f"📍 Manzil: {esc(r['address'] or '—')}\n"
            f"🚦 Holat: {status}\n\n"
            "O'zgartirish uchun tugmani bosing 👇"
        )
        kb = simple_kb([
            [("📝 Nomini o'zgartirish", "redit:name")],
            [("👤 Mas'ul shaxs", "redit:contact")],
            [("📞 Telefon", "redit:phone")],
            [("📍 Manzil", "redit:address")],
            [("🔴 Yopish" if r["is_available"] else "🟢 Ochish", "rtoggle")],
        ])
        await message.answer(text, reply_markup=kb)

    # ---------- start / ro'yxatdan o'tish ----------

    @dp.message(CommandStart())
    async def r_start(message: Message, state: FSMContext):
        await state.clear()
        r = get_restaurant(rid)
        if r and r["owner_tg_id"]:
            if r["owner_tg_id"] == message.from_user.id:
                await message.answer(
                    f"🏪 <b>{esc(r['name'])}</b> boshqaruv paneli.\n"
                    "Mijozlardan buyurtmalar shu botga keladi.",
                    reply_markup=r_main_kb(),
                )
            else:
                await message.answer(
                    f"❌ Bu bot «{esc(r['name'])}» restoraniga tegishli.\n"
                    "Agar siz restoran egasi bo'lsangiz, operator bilan bog'laning."
                )
            return
        await state.set_state(RReg.rest_name)
        await message.answer(
            "🏪 Xush kelibsiz! Bu restoran boti — ro'yxatdan o'tamiz.\n\n"
            "1️⃣ Restoran nomini yozing:"
        )

    @dp.message(RReg.rest_name, F.text)
    async def r_reg_name(message: Message, state: FSMContext):
        name = message.text.strip()
        if len(name) < 2:
            await message.answer("Nomni to'g'ri yozing:")
            return
        await state.update_data(rest_name=name)
        await state.set_state(RReg.contact)
        await message.answer(f"2️⃣ «{esc(name)}» mas'ul shaxsining ismini yozing:")

    @dp.message(RReg.contact, F.text)
    async def r_reg_contact(message: Message, state: FSMContext):
        await state.update_data(contact=message.text.strip())
        await state.set_state(RReg.phone)
        await message.answer("3️⃣ Restoran telefon raqamini yuboring:", reply_markup=r_phone_kb())

    @dp.message(RReg.phone, F.contact)
    async def r_reg_phone_contact(message: Message, state: FSMContext):
        await state.update_data(phone=message.contact.phone_number)
        await state.set_state(RReg.address)
        await message.answer("4️⃣ Restoran manzilini yozing (kuryer ovqatni shu yerdan oladi):")

    @dp.message(RReg.phone, F.text)
    async def r_reg_phone_text(message: Message, state: FSMContext):
        t = (message.text or "").strip()
        if t == BTN_CANCEL:
            await state.clear()
            await message.answer("Ro'yxatdan o'tish bekor qilindi.")
            return
        digits = re.sub(r"\D", "", t)
        if not (9 <= len(digits) <= 15):
            await message.answer("Raqam noto'g'ri. Masalan: +998901234567:")
            return
        await state.update_data(phone=t if t.startswith("+") else "+" + digits)
        await state.set_state(RReg.address)
        await message.answer("4️⃣ Restoran manzilini yozing (kuryer ovqatni shu yerdan oladi):")

    @dp.message(RReg.address, F.text)
    async def r_reg_address(message: Message, state: FSMContext):
        data = await state.get_data()
        set_restaurant(
            rid,
            name=data.get("rest_name") or restaurant_name(rid),
            contact_name=data.get("contact", ""),
            phone=data.get("phone", ""),
            address=message.text.strip(),
            owner_tg_id=message.from_user.id,
        )
        await state.clear()
        await message.answer(
            f"✅ Tabriklaymiz! «{esc(restaurant_name(rid))}» ro'yxatdan o'tdi.\n"
            "Endi mijozlardan buyurtmalar shu botga keladi.",
            reply_markup=r_main_kb(),
        )
        await notify_operators(
            "🏪 <b>Yangi restoran ro'yxatdan o'tdi</b>\n\n"
            f"Nomi: {esc(restaurant_name(rid))}\n"
            f"Mas'ul: {esc(data.get('contact', ''))}\n"
            f"Tel: {esc(data.get('phone', ''))}\n"
            f"Manzil: {esc(message.text.strip())}"
        )

    # ---------- buyurtmalar ----------

    @dp.message(F.text == R_ORDERS)
    async def r_on_orders(message: Message):
        if not is_owner(message.from_user.id):
            await message.answer("Avval /start orqali ro'yxatdan o'ting.")
            return
        rows = [[(label, f"rlst:{k}")] for k, label in R_FILTERS.items()]
        rows.append([("📊 Bugungi hisobot", "rtoday")])
        await message.answer(
            f"📋 <b>{esc(restaurant_name(rid))} — buyurtmalar</b>",
            reply_markup=simple_kb(rows),
        )

    @dp.callback_query(F.data.startswith("rlst:"))
    async def r_cb_lst(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        kind = cq.data.split(":")[1]
        orders = orders_by(kind, limit=20, restaurant_id=rid)
        if not orders:
            await cq.answer(f"{R_FILTERS.get(kind, kind)}: buyurtma yo'q.")
            return
        kb_rows = []
        for o in orders:
            kb_rows.append([(f"№{o['id']} — {status_label(o['status'])}", f"rov:{o['id']}")])
        kb_rows.append([("⬅️ Orqaga", "rback")])
        await cq.answer()
        text = f"{R_FILTERS.get(kind, kind)} — {len(orders)} ta:"
        try:
            await cq.message.edit_text(text, reply_markup=simple_kb(kb_rows))
        except Exception:
            await cq.message.answer(text, reply_markup=simple_kb(kb_rows))

    @dp.callback_query(F.data == "rback")
    async def r_cb_back(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        await cq.answer()
        rows = [[(label, f"rlst:{k}")] for k, label in R_FILTERS.items()]
        rows.append([("📊 Bugungi hisobot", "rtoday")])
        await cq.message.edit_text(
            f"📋 <b>{esc(restaurant_name(rid))} — buyurtmalar</b>",
            reply_markup=simple_kb(rows),
        )

    @dp.callback_query(F.data == "rtoday")
    async def r_cb_today(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        st = restaurant_today(rid)
        await cq.answer()
        await cq.message.answer(
            f"📊 <b>{esc(restaurant_name(rid))} — bugun</b>\n\n"
            f"🆕 Yangi: {st['new']}\n"
            f"🟠 Faolda: {st['active']}\n"
            f"✅ Yetkazilgan: {st['delivered']}\n"
            f"🍽 Ovqat summasi (yetkazilganlarga): {mone(st['food_income'])}"
        )

    @dp.callback_query(F.data.startswith("rov:"))
    async def r_cb_rov(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        oid = int(cq.data.split(":")[1])
        o = get_order(oid)
        if not owns_order(o):
            await cq.answer("Bu buyurtma sizga tegishli emas.")
            return
        await cq.answer()
        text = f"📋 <b>Buyurtma</b>\n\n{order_card(o)}"
        kb = r_order_kb(o)
        try:
            await cq.message.edit_text(text, reply_markup=kb)
        except Exception:
            await cq.message.answer(text, reply_markup=kb)

    @dp.callback_query(F.data.startswith("racc:"))
    async def r_cb_acc(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        oid = int(cq.data.split(":")[1])
        o = get_order(oid)
        if not owns_order(o):
            await cq.answer("Bu buyurtma sizga tegishli emas.")
            return
        # MUHIM: operator tasdiqlamagan buyurtmani restoran o'zi qabul qila olmaydi
        if o["status"] == "new":
            await cq.answer("⏳ Bu buyurtma hali operator tomonidan tasdiqlanmagan.",
                            show_alert=True)
            return
        if o["status"] != "accepted":
            await cq.answer("Bu buyurtmani qabul qilib bo'lmaydi (holat o'zgargan).")
            return
        set_order(oid, status="preparing")
        o = get_order(oid)
        await cq.answer("✅ Qabul qilindi")
        await notify_customer_order(
            o,
            f"✅ <b>Buyurtma №{oid} qabul qilindi!</b>\n"
            f"«{esc(restaurant_name(rid))}» ovqatni tayyorlashni boshladi.",
        )
        await notify_operators(
            f"✅ №{oid} buyurtma «{esc(restaurant_name(rid))}» tomonidan qabul qilindi."
        )
        try:
            await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                       reply_markup=r_order_kb(o))
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("rwait:"))
    async def r_cb_wait(cq: CallbackQuery):
        await cq.answer(
            "⏳ Operator tasdiqlashini kuting. Tasdiqlangach buyurtma shu botga keladi.",
            show_alert=True,
        )

    @dp.callback_query(F.data.startswith("rprep:"))
    async def r_cb_prep(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        oid = int(cq.data.split(":")[1])
        o = get_order(oid)
        if not owns_order(o) or o["status"] != "accepted":
            await cq.answer("Avval buyurtmani qabul qiling.")
            return
        set_order(oid, status="preparing")
        o = get_order(oid)
        await cq.answer("🍳 Tayyorlanmoqda")
        await notify_customer_order(o, f"🍳 <b>Buyurtma №{oid}</b>: ovqat tayyorlanmoqda.")
        try:
            await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                       reply_markup=r_order_kb(o))
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("rrdy:"))
    async def r_cb_ready(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        oid = int(cq.data.split(":")[1])
        o = get_order(oid)
        if not owns_order(o) or o["status"] not in ("preparing", "accepted"):
            await cq.answer("Bu buyurtmani «Tayyor» deb belgilab bo'lmaydi.")
            return
        set_order(oid, status="ready")
        o = get_order(oid)
        await cq.answer("🛎 Tayyor")
        await notify_customer_order(
            o,
            f"🛎 <b>Buyurtma №{oid}</b>: ovqat tayyor! Kuryer olib kelish uchun yo'lda.",
        )
        await notify_operators(
            f"🛎 <b>№{oid} buyurtma tayyor</b> — {esc(restaurant_name(rid))}.\n"
            "Kuryer tayinlang 👇",
            simple_kb([[("🛵 Kuryer tayinlash", f"asg:{oid}")]]),
        )
        try:
            await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                       reply_markup=r_order_kb(o))
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("rrej:"))
    async def r_cb_rej(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        oid = int(cq.data.split(":")[1])
        o = get_order(oid)
        if not owns_order(o) or o["status"] not in ("new", "accepted", "preparing", "ready"):
            await cq.answer("Bu buyurtmani rad etib bo'lmaydi.")
            return
        set_order(oid, status="cancelled", courier_tg_id=None)
        o = get_order(oid)
        await cq.answer("❌ Rad etildi")
        await notify_customer_order(
            o,
            f"❌ <b>Buyurtma №{oid} rad etildi.</b>\n"
            f"«{esc(restaurant_name(rid))}» hozir bu buyurtmani qabul qila olmadi.\n"
            "Boshqa restorandan buyurtma berishingiz mumkin.",
        )
        await notify_operators(
            f"⚠️ №{oid} buyurtma «{esc(restaurant_name(rid))}» tomonidan rad etildi."
        )
        try:
            await cq.message.edit_text(f"📋 <b>Buyurtma</b>\n\n{order_card(o)}",
                                       reply_markup=r_order_kb(o))
        except Exception:
            pass

    # ---------- menyu boshqaruvi ----------

    @dp.message(F.text == R_MENU)
    async def r_on_menu(message: Message):
        if not is_owner(message.from_user.id):
            await message.answer("Avval /start orqali ro'yxatdan o'ting.")
            return
        await r_send_menu(message)

    @dp.callback_query(F.data == "rmadd")
    async def r_cb_add(cq: CallbackQuery, state: FSMContext):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        await state.set_state(RMenuAdd.name)
        await cq.answer()
        await cq.message.answer("🍽 Yangi taom nomini yozing:")

    @dp.message(RMenuAdd.name, F.text)
    async def r_add_name(message: Message, state: FSMContext):
        if not is_owner(message.from_user.id):
            return
        name = message.text.strip()
        if len(name) < 2:
            await message.answer("Nom noto'g'ri, qayta yozing:")
            return
        await state.update_data(name=name)
        await state.set_state(RMenuAdd.price)
        await message.answer(f"«{esc(name)}» narxini so'mda yozing (masalan: 30000):")

    @dp.message(RMenuAdd.price, F.text)
    async def r_add_price(message: Message, state: FSMContext):
        if not is_owner(message.from_user.id):
            return
        digits = re.sub(r"\D", "", message.text or "")
        if not digits:
            await message.answer("Narxni raqamda yozing (masalan: 30000):")
            return
        data = await state.get_data()
        await state.update_data(price=int(digits))
        await state.set_state(RMenuAdd.cat)
        rows = [[(label, f"raddcat:{code}")] for code, label, _n in CATEGORIES]
        await message.answer(
            f"🗂 «{esc(data['name'])}» qaysi kategoriyaga qo'shilsin?",
            reply_markup=simple_kb(rows),
        )

    @dp.callback_query(F.data.startswith("raddcat:"))
    async def r_addcat(cq: CallbackQuery, state: FSMContext):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        code = cq.data.split(":")[1]
        data = await state.get_data()
        if not data.get("name") or not data.get("price"):
            await cq.answer("Ma'lumot yo'qolgan — qaytadan boshlang.")
            return
        add_menu_item(data["name"], int(data["price"]), restaurant_id=rid,
                      category=cat_name(code))
        await state.clear()
        await cq.answer("✅ Qo'shildi")
        try:
            await cq.message.edit_text(
                f"✅ Taom qo'shildi: {esc(data['name'])} — {mone(int(data['price']))}\n"
                f"🗂 {cat_label(code)}")
        except Exception:
            pass
        await r_send_menu(cq.message)

    @dp.callback_query(F.data.startswith("rcat:"))
    async def r_change_cat(cq: CallbackQuery):
        """Taom kategoriyasini o'zgartirish."""
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        iid = int(cq.data.split(":")[1])
        it = get_menu_item(iid)
        if not it or (it["restaurant_id"] or 0) != rid:
            await cq.answer("Topilmadi.")
            return
        rows = [[(label, f"rset:{iid}:{code}")] for code, label, _n in CATEGORIES]
        await cq.answer()
        await cq.message.answer(
            f"«{esc(it['name'])}» uchun kategoriyani tanlang "
            f"(hozir: {cat_label(cat_code(it.get('category') or CAT_FOODS))}):",
            reply_markup=simple_kb(rows),
        )

    @dp.callback_query(F.data.startswith("rset:"))
    async def r_set_cat(cq: CallbackQuery):
        parts = cq.data.split(":")
        if len(parts) != 3:
            await cq.answer("Eski tugma.")
            return
        _, iid_s, code = parts
        iid = int(iid_s)
        it = get_menu_item(iid)
        if not it or (it["restaurant_id"] or 0) != rid:
            await cq.answer("Topilmadi.")
            return
        set_menu_item(iid, category=cat_name(code))
        await cq.answer(f"🗂 {cat_label(code)}")
        await r_send_menu(cq.message, edit=True)

    @dp.callback_query(F.data.startswith("rmtog:"))
    async def r_cb_tog(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        iid = int(cq.data.split(":")[1])
        it = get_menu_item(iid)
        if not it or (it["restaurant_id"] or 0) != rid:
            await cq.answer("Topilmadi.")
            return
        set_menu_item(iid, is_available=0 if it["is_available"] else 1)
        await cq.answer("✅" if not it["is_available"] else "🚫")
        await r_send_menu(cq.message, edit=True)

    @dp.callback_query(F.data.startswith("rmnm:"))
    async def r_cb_ren(cq: CallbackQuery, state: FSMContext):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        iid = int(cq.data.split(":")[1])
        it = get_menu_item(iid)
        if not it or (it["restaurant_id"] or 0) != rid:
            await cq.answer("Topilmadi.")
            return
        await state.update_data(iid=iid)
        await state.set_state(RMenuRename.wait)
        await cq.answer()
        await cq.message.answer(f"Hozirgi nom: {esc(it['name'])}. Yangi nomni yozing:")

    @dp.message(RMenuRename.wait, F.text)
    async def r_ren_wait(message: Message, state: FSMContext):
        if not is_owner(message.from_user.id):
            return
        data = await state.get_data()
        set_menu_item(data["iid"], name=message.text.strip())
        await state.clear()
        await message.answer("✅ Nom yangilandi.", reply_markup=r_main_kb())
        await r_send_menu(message)

    @dp.callback_query(F.data.startswith("rmpr:"))
    async def r_cb_price(cq: CallbackQuery, state: FSMContext):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        iid = int(cq.data.split(":")[1])
        it = get_menu_item(iid)
        if not it or (it["restaurant_id"] or 0) != rid:
            await cq.answer("Topilmadi.")
            return
        await state.update_data(iid=iid)
        await state.set_state(RMenuPrice.wait)
        await cq.answer()
        await cq.message.answer(f"Hozirgi narx: {mone(it['price'])}. Yangi narxni so'mda yozing:")

    @dp.message(RMenuPrice.wait, F.text)
    async def r_price_wait(message: Message, state: FSMContext):
        if not is_owner(message.from_user.id):
            return
        digits = re.sub(r"\D", "", message.text or "")
        if not digits:
            await message.answer("Narxni raqamda yozing:")
            return
        data = await state.get_data()
        set_menu_item(data["iid"], price=int(digits))
        await state.clear()
        await message.answer("✅ Narx yangilandi.", reply_markup=r_main_kb())
        await r_send_menu(message)

    @dp.callback_query(F.data.startswith("rmdel:"))
    async def r_cb_del(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        iid = int(cq.data.split(":")[1])
        it = get_menu_item(iid)
        if not it or (it["restaurant_id"] or 0) != rid:
            await cq.answer("Topilmadi.")
            return
        del_menu_item(iid)
        await cq.answer("🗑 O'chirildi")
        await r_send_menu(cq.message, edit=True)

    # ---------- ma'lumotlar / yordam ----------

    @dp.message(F.text == R_INFO)
    async def r_on_info(message: Message):
        if not is_owner(message.from_user.id):
            await message.answer("Avval /start orqali ro'yxatdan o'ting.")
            return
        await r_send_info(message)

    @dp.callback_query(F.data.startswith("redit:"))
    async def r_cb_edit(cq: CallbackQuery, state: FSMContext):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        field = cq.data.split(":")[1]
        await state.update_data(field=field)
        await state.set_state(REdit.wait)
        await cq.answer()
        prompts = {
            "name": "Yangi restoran nomini yozing:",
            "contact": "Mas'ul shaxsning ismini yozing:",
            "phone": "Yangi telefon raqamni yozing (masalan: +998901234567):",
            "address": "Yangi manzilni yozing:",
        }
        await cq.message.answer(prompts.get(field, "Yangi qiymatni yozing:"))

    @dp.message(REdit.wait, F.text)
    async def r_edit_wait(message: Message, state: FSMContext):
        if not is_owner(message.from_user.id):
            return
        data = await state.get_data()
        field = data.get("field")
        val = message.text.strip()
        if field in ("name", "contact", "phone", "address"):
            set_restaurant(rid, **{field if field != "contact" else "contact_name": val})
        await state.clear()
        await message.answer("✅ Saqlandi.", reply_markup=r_main_kb())
        await r_send_info(message)

    @dp.callback_query(F.data == "rtoggle")
    async def r_cb_toggle(cq: CallbackQuery):
        if not is_owner(cq.from_user.id):
            await cq.answer("Ruxsat yo'q.")
            return
        r = get_restaurant(rid)
        set_restaurant(rid, is_available=0 if r["is_available"] else 1)
        await cq.answer("🔴 Yopildi" if r["is_available"] else "🟢 Ochildi")
        try:
            await cq.message.delete()
        except Exception:
            pass
        await r_send_info(cq.message)

    @dp.message(F.text == R_HELP)
    async def r_on_help(message: Message):
        if not is_owner(message.from_user.id):
            await message.answer("Avval /start orqali ro'yxatdan o'ting.")
            return
        await message.answer(
            "ℹ️ <b>Restoran uchun yo'riqnoma</b>\n\n"
            "1️⃣ Yangi buyurtma kelganda «✅ Qabul qilish» bosing\n"
            "2️⃣ Tayyorlashni boshlagach «🍳 Tayyorlanmoqda»\n"
            "3️⃣ Ovqat tayyor bo'lgach «🛎 Tayyor» — kuryer tayinlanadi\n"
            "4️⃣ Kuryer kelib ovqatni olib ketadi\n\n"
            f"☎️ Operator: <code>{esc(SUPPORT_PHONE)}</code>\n"
            "Menyu, narx va ma'lumotlaringizni shu botda o'zingiz boshqarasiz.",
            reply_markup=r_main_kb(),
        )

    return dp


# ============================================================================
# [8] VEB-SAYT (mijozlar uchun) — botlar bilan birga ishlaydi
# ============================================================================
# Sayt: restoran tanlash -> kategoriyali menyu -> savat -> buyurtma
# Buyurtma Telegramda OPERATORGA keladi -> operator "Ruxsat berish" bosadi ->
# shundan keyin restoranga yuboriladi. Saytdan buyurtma bergan mijozning
# xabarlari saytda (kuzatuv sahifasida) ko'rinadi.

import secrets

from aiohttp import web

WEB_HTML = r'''<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#FF6B35">
<title>Ovqat Yetkazish</title>
<style>
:root{
  --brand:#FF6B35; --brand2:#FF9F1C; --brand3:#FF3D71;
  --ink:#101319; --ink2:#3A4150; --muted:#7A8494; --line:#EEF0F5;
  --card:#FFFFFF; --bg1:#FFF6F0; --bg2:#F4F6FC;
  --ok:#12B76A; --warn:#F79009; --bad:#F04438; --info:#2E90FA;
  --r:20px; --r-sm:14px; --sh:0 6px 24px rgba(16,19,25,.07); --sh2:0 12px 34px rgba(255,107,53,.28);
}
*{box-sizing:border-box; -webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0}
body{
  font-family:'Inter',-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
  color:var(--ink); background:linear-gradient(180deg,var(--bg1) 0%,var(--bg2) 38%,var(--bg2) 100%);
  min-height:100vh; padding-bottom:104px; -webkit-font-smoothing:antialiased;
}
a{color:var(--brand); text-decoration:none}
.wrap{max-width:760px;margin:0 auto;padding:0 0 18px}
.hidden{display:none!important}

/* ---------- HERO ---------- */
.hero{
  position:relative; overflow:hidden; padding:22px 18px 58px;
  background:linear-gradient(135deg,#FF6B35 0%,#FF8A3D 45%,#FFB03A 100%);
  border-radius:0 0 34px 34px; box-shadow:0 10px 30px rgba(255,107,53,.28);
}
.hero:before,.hero:after{content:'';position:absolute;border-radius:50%;background:rgba(255,255,255,.16)}
.hero:before{width:190px;height:190px;top:-70px;right:-50px}
.hero:after{width:120px;height:120px;bottom:-60px;left:-30px;background:rgba(255,255,255,.12)}
.hero .brand{position:relative;display:flex;align-items:center;gap:11px}
.hero .logo{
  width:46px;height:46px;border-radius:15px;display:grid;place-items:center;font-size:24px;
  background:rgba(255,255,255,.22);border:1px solid rgba(255,255,255,.35);backdrop-filter:blur(4px);
}
.hero h1{position:relative;margin:0;font-size:21px;color:#fff;font-weight:800;letter-spacing:-.3px}
.hero p{position:relative;margin:5px 0 0;color:rgba(255,255,255,.92);font-size:12.5px;font-weight:500}
.hero .stats{position:relative;display:flex;gap:8px;margin-top:15px}
.chip{
  background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.32);color:#fff;
  padding:7px 12px;border-radius:999px;font-size:12px;font-weight:600;display:flex;align-items:center;gap:6px;
}

/* ---------- BODY / CARDS ---------- */
.body{padding:0 14px;margin-top:-40px;position:relative;z-index:2}
.card{
  background:var(--card);border-radius:var(--r);padding:16px;margin-bottom:13px;
  box-shadow:var(--sh);border:1px solid rgba(16,19,25,.04);animation:up .45s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes up{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.card h2{margin:0 0 12px;font-size:16.5px;font-weight:800;letter-spacing:-.2px}
.sec-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.sec-title h2{margin:0}
.link{font-size:13px;font-weight:700;color:var(--brand)}

/* ---------- RESTORANT KARTALARI ---------- */
.rest{
  display:flex;align-items:center;gap:14px; padding:13px; border-radius:16px;
  background:linear-gradient(180deg,#FFFFFF,#FDFDFF); border:1px solid var(--line);
  margin-bottom:10px; cursor:pointer; transition:transform .18s, box-shadow .18s, border-color .18s;
}
.rest:active{transform:scale(.985)}
.rest:hover{border-color:#FFD9C6; box-shadow:0 8px 22px rgba(255,107,53,.12)}
.rest .av{
  width:52px;height:52px;border-radius:16px;display:grid;place-items:center;font-size:26px;flex:0 0 52px;
  background:linear-gradient(135deg,#FFF1E8,#FFE3D2);border:1px solid #FFE0CE;
}
.rest .info{flex:1;min-width:0}
.rest .info b{display:block;font-size:15.5px;font-weight:750;letter-spacing:-.2px}
.rest .info span{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:12.5px;margin-top:3px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 3px rgba(18,183,106,.14)}
.go{
  width:36px;height:36px;border-radius:12px;display:grid;place-items:center;flex:0 0 36px;
  background:#FFF3EC;color:var(--brand);font-size:16px;font-weight:800;
}

/* ---------- KATEGORIYA PILLS ---------- */
.tabs{display:flex;gap:9px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{
  white-space:nowrap;padding:10px 15px;border-radius:999px;font-size:13.5px;font-weight:700;
  background:#fff;border:1px solid var(--line);color:var(--ink2);cursor:pointer;transition:.18s;
}
.tab.on{background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;border-color:transparent;box-shadow:var(--sh2)}

/* ---------- TAOM QATORI ---------- */
.item{display:flex;gap:12px;align-items:center;padding:12px 0;border-bottom:1px dashed var(--line)}
.item:last-child{border-bottom:0}
.item .em{
  width:46px;height:46px;border-radius:14px;display:grid;place-items:center;font-size:23px;flex:0 0 46px;
  background:linear-gradient(135deg,#F7F8FD,#EFF2FA);border:1px solid var(--line);
}
.item .txt{flex:1;min-width:0}
.item .txt b{font-size:14.5px;font-weight:750;display:block;letter-spacing:-.1px}
.item .txt small{color:var(--muted);font-size:12px;display:block;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.price{color:var(--brand);font-weight:800;font-size:14px;white-space:nowrap}

/* ---------- SONI (qty) ---------- */
.qty{display:flex;align-items:center;gap:9px}
.qbtn{
  width:34px;height:34px;border-radius:12px;border:1px solid var(--line);background:#fff;color:var(--ink);
  font-size:18px;font-weight:700;cursor:pointer;display:grid;place-items:center;transition:.15s;
}
.qbtn:active{transform:scale(.9)}
.qbtn.plus{background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;border-color:transparent;box-shadow:0 6px 16px rgba(255,107,53,.35)}
.qnum{min-width:16px;text-align:center;font-weight:800}

/* ---------- TUGMALAR ---------- */
.btn{
  display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:15px;border:0;
  border-radius:16px;background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;
  font-size:16px;font-weight:800;cursor:pointer;margin-top:12px;letter-spacing:-.2px;
  box-shadow:var(--sh2);transition:transform .16s, box-shadow .16s;
}
.btn:active{transform:scale(.98);box-shadow:0 6px 18px rgba(255,107,53,.3)}
.btn.sec{background:#F1F3F9;color:var(--ink2);box-shadow:none;border:1px solid var(--line)}
.btn.ghost{background:transparent;color:var(--brand);box-shadow:none;border:1.5px dashed #FFC9AE}
.btn:disabled{opacity:.55;box-shadow:none}

/* ---------- SAVAT PANELI ---------- */
.bar{
  position:fixed;left:0;right:0;bottom:0;z-index:20;padding:12px 14px calc(12px + env(safe-area-inset-bottom));
  background:rgba(255,255,255,.92);backdrop-filter:blur(14px);border-top:1px solid var(--line);
  display:flex;align-items:center;gap:12px;animation:up .3s both;
}
.bar .basket{position:relative;width:48px;height:48px;border-radius:16px;display:grid;place-items:center;
  background:linear-gradient(135deg,#FFF1E8,#FFE3D2);font-size:22px;flex:0 0 48px;border:1px solid #FFE0CE}
.bar .basket .badge{
  position:absolute;top:-6px;right:-6px;min-width:22px;height:22px;border-radius:999px;background:var(--brand3);
  color:#fff;font-size:11.5px;font-weight:800;display:grid;place-items:center;padding:0 5px;
  box-shadow:0 4px 10px rgba(255,61,113,.4);animation:pop .3s both;
}
@keyframes pop{from{transform:scale(.4)}to{transform:scale(1)}}
.bar .sums{flex:1;min-width:0}
.bar .sums small{color:var(--muted);font-size:11.5px;font-weight:600;display:block}
.bar .sums b{font-size:18px;font-weight:850;letter-spacing:-.3px}
.bar .btn{width:auto;padding:13px 18px;margin:0;font-size:14.5px}

/* ---------- FORMA ---------- */
label{display:block;font-size:12.5px;font-weight:700;color:var(--ink2);margin:13px 0 0}
input,textarea{
  width:100%;padding:13px 14px;border:1.5px solid var(--line);border-radius:15px;font-size:15px;
  font-family:inherit;background:#FCFCFE;margin-top:6px;transition:.18s;color:var(--ink);
}
input:focus,textarea:focus{outline:none;border-color:var(--brand);background:#fff;box-shadow:0 0 0 4px rgba(255,107,53,.12)}
textarea{resize:vertical;min-height:74px}
.err{background:#FFF1F0;border:1px solid #FFD6D2;color:#B42318;padding:12px;border-radius:14px;font-size:13.5px;font-weight:600;margin-top:10px}
.hint{font-size:12px;color:var(--muted);text-align:center;margin-top:9px}

/* ---------- SUMMAR ---------- */
.rows{border:1px dashed var(--line);border-radius:16px;padding:12px;margin-top:10px;background:#FCFCFE}
.row{display:flex;justify-content:space-between;gap:10px;font-size:13.5px;padding:7px 0;color:var(--ink2)}
.row b{font-weight:750;color:var(--ink)}
.row.total{border-top:1px dashed var(--line);margin-top:6px;padding-top:11px;font-size:15.5px}
.row.total b{font-size:19px;color:var(--brand);font-weight:850}

/* ---------- STATUS / STEPPER ---------- */
.status-hero{text-align:center;background:linear-gradient(135deg,#FFFFFF,#FFF9F5);border:1px solid #FFE8DB}
.status-ico{
  width:70px;height:70px;border-radius:24px;margin:2px auto 12px;display:grid;place-items:center;font-size:34px;
  background:linear-gradient(135deg,#FFF1E8,#FFE3D2);border:1px solid #FFE0CE;animation:pulse 2.4s infinite;
}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,107,53,.25)}50%{box-shadow:0 0 0 14px rgba(255,107,53,0)}}
.status-hero h2{margin:0;font-size:19px;font-weight:850;letter-spacing:-.3px}
.status-hero p{margin:7px 0 0;color:var(--muted);font-size:13px}
.stepper{display:flex;align-items:flex-start;margin:18px 2px 4px}
.step{flex:1;text-align:center;position:relative}
.step .bubble{
  width:34px;height:34px;border-radius:999px;margin:0 auto 7px;display:grid;place-items:center;font-size:15px;
  background:#F4F5F9;border:1.5px solid var(--line);color:var(--muted);transition:.3s;position:relative;z-index:2;
}
.step .lbl{font-size:10.5px;font-weight:700;color:var(--muted);line-height:1.25}
.step:after{content:'';position:absolute;top:17px;left:50%;width:100%;height:2.5px;background:var(--line);z-index:1}
.step:last-child:after{display:none}
.step.on .bubble{background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;border-color:transparent;box-shadow:0 6px 16px rgba(255,107,53,.35)}
.step.on .lbl{color:var(--brand)}
.step.on:after{background:linear-gradient(90deg,var(--brand),var(--brand2))}
.step.done .bubble{background:#E9FBF1;border-color:#C6F0D9;color:var(--ok)}
.step.done:after{background:#C6F0D9}

/* ---------- XABARLAR (timeline) ---------- */
.chat{display:flex;flex-direction:column;gap:10px;max-height:430px;overflow-y:auto;padding:4px 2px 2px}
.msg{display:flex;gap:10px;align-items:flex-start;animation:slide .4s cubic-bezier(.2,.8,.2,1) both}
@keyframes slide{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
.msg .ic{
  width:36px;height:36px;border-radius:13px;display:grid;place-items:center;font-size:17px;flex:0 0 36px;
  background:#EEF2FF;border:1px solid #E0E7FF;
}
.msg .bubble{
  flex:1;background:#FBFBFE;border:1px solid var(--line);border-radius:4px 16px 16px 16px;
  padding:10px 12px;position:relative;
}
.msg .bubble .t{font-size:13.5px;font-weight:600;line-height:1.45;color:var(--ink)}
.msg .bubble .tm{font-size:10.5px;color:var(--muted);margin-top:4px;font-weight:600}
.msg.ok .ic{background:#E9FBF1;border-color:#C6F0D9;color:var(--ok)}
.msg.ok .bubble{background:#F3FDF8;border-color:#D6F5E4}
.msg.bad .ic{background:#FFF1F0;border-color:#FFD6D2}
.msg.bad .bubble{background:#FFF8F7;border-color:#FFE3E0}
.msg.warn .ic{background:#FFF8EC;border-color:#FDE3B8}
.msg.warn .bubble{background:#FFFCF5;border-color:#FBEBCB}
.msg.info .ic{background:#EFF6FF;border-color:#D6E8FF}
.msg.info .bubble{background:#F7FBFF;border-color:#E1EEFF}
.msg.new .bubble:after{
  content:'yangi';position:absolute;top:-9px;right:10px;font-size:9.5px;font-weight:800;color:#fff;
  background:var(--brand3);padding:2px 7px;border-radius:999px;letter-spacing:.3px;
}

/* ---------- KURYER ---------- */
.courier{display:flex;align-items:center;gap:12px;background:#F8FAFF;border:1px solid #E4EDFF;border-radius:16px;padding:12px}
.courier .av{width:44px;height:44px;border-radius:14px;display:grid;place-items:center;font-size:22px;background:#fff;border:1px solid #E4EDFF}
.call{margin-left:auto;background:#12B76A;color:#fff;border-radius:12px;padding:10px 13px;font-size:13px;font-weight:800;display:flex;gap:6px;align-items:center;box-shadow:0 6px 16px rgba(18,183,106,.3)}

/* ---------- BO'SH HOLAT / SPINNER ---------- */
.empty{text-align:center;padding:30px 12px;color:var(--muted)}
.empty .em{font-size:44px;display:block;margin-bottom:10px;opacity:.85}
.spinner{width:34px;height:34px;border-radius:50%;border:3px solid #FFE3D2;border-top-color:var(--brand);margin:26px auto;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.skel{height:68px;border-radius:16px;background:linear-gradient(90deg,#F4F5F9,#EDEFF6,#F4F5F9);background-size:200% 100%;animation:sh 1.2s infinite;margin-bottom:10px}
@keyframes sh{to{background-position:-200% 0}}

/* ---------- TOAST ---------- */
#toast{position:fixed;left:50%;bottom:112px;transform:translateX(-50%) translateY(20px);z-index:40;
  background:#101319;color:#fff;padding:11px 16px;border-radius:999px;font-size:13px;font-weight:700;
  opacity:0;pointer-events:none;transition:.28s;box-shadow:0 10px 26px rgba(0,0,0,.28)}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
#toast.ok{background:linear-gradient(135deg,#12B76A,#059669)}
#toast.bad{background:linear-gradient(135deg,#F04438,#D92D20)}
.success-ico{width:84px;height:84px;border-radius:28px;margin:6px auto 14px;display:grid;place-items:center;font-size:42px;
  background:linear-gradient(135deg,#E9FBF1,#D3F7E4);border:1px solid #BFEFD6;animation:pop .5s both}
.code{font-family:ui-monospace,Menlo,Consolas,monospace;background:#F4F5F9;border:1px solid var(--line);
  padding:3px 7px;border-radius:8px;font-size:12.5px;font-weight:700}
@media(max-width:360px){.step .lbl{font-size:9.5px}.hero h1{font-size:19px}}
</style>
</head>
<body>
<div class="hero">
  <div class="brand">
    <div class="logo">&#128757;</div>
    <div>
      <h1 id="siteName">Ovqat Yetkazish</h1>
      <p>Issiq ovqat &mdash; tez yetkazib berish</p>
    </div>
  </div>
  <div class="stats">
    <div class="chip"><span class="dot"></span> <span id="chipOpen">Restoranlar</span></div>
    <div class="chip">&#128663; <span id="chipFee">Dostavka</span></div>
  </div>
</div>
<div class="wrap"><div class="body" id="view"></div></div>
<div class="bar hidden" id="bar">
  <div class="basket">&#128722;<span class="badge" id="barCount">0</span></div>
  <div class="sums"><small>Savat summasi</small><b id="barSum">0 so'm</b></div>
  <button class="btn" onclick="checkout()">Buyurtma berish &rarr;</button>
</div>
<div id="toast"></div>
<script>
var EMO={"foods":"\uD83C\uDF72","salads":"\uD83E\uDD57","drinks":"\uD83E\uDD64"};
var EMO_ITEM={
 "osh":"\uD83C\uDF5B","palov":"\uD83C\uDF5B","somsa":"\uD83E\uDD6E","lag":"\uD83C\uDF5C","shurpa":"\uD83C\uDF72",
 "norin":"\uD83C\uDF5D","manti":"\uD83E\uDD5F","kabob":"\uD83C\uDF56","shashlik":"\uD83C\uDF56","lula":"\uD83C\uDF56",
 "jigar":"\uD83C\uDF56","baliq":"\uD83D\uDC1F","lavash":"\uD83C\uDF2F","donar":"\uD83E\uDD59","burger":"\uD83C\uDF54",
 "chizburger":"\uD83C\uDF54","xot-dog":"\uD83C\uDF2D","kartoshka":"\uD83C\uDF5F","nagets":"\uD83C\uDF57","pitsa":"\uD83C\uDF55",
 "pide":"\uD83E\uDD67","lahmajun":"\uD83E\uDD67","tuxum":"\uD83C\uDF73","omelet":"\uD83C\uDF73","bo'tqa":"\uD83E\uDD63",
 "chuchvara":"\uD83E\uDD5F","kotlet":"\uD83C\uDF56","salat":"\uD83E\uDD57","achichuk":"\uD83E\uDD52","sezar":"\uD83E\uDD57",
 "olivye":"\uD83E\uDD57","sabzavot":"\uD83E\uDD66","meva":"\uD83C\uDF4E","choy":"\uD83C\uDF75","ayron":"\uD83E\uDD5B",
 "kompot":"\uD83E\uDDC3","cola":"\uD83E\uDD64","fanta":"\uD83E\uDD64","sprite":"\uD83E\uDD64","suv":"\uD83D\uDCA7",
 "limonad":"\uD83C\uDF79","kofe":"\u2615","kakao":"\u2615","sut":"\uD83E\uDD5B","kefir":"\uD83E\uDD5B",
 "sharbat":"\uD83E\uDDC3","milkshake":"\uD83E\uDD5B","non":"\uD83C\uDF5E","turk":"\uD83C\uDF75","mineral":"\uD83D\uDCA7"
};
function emo(name){var n=String(name||'').toLowerCase();for(var k in EMO_ITEM){if(n.indexOf(k)>=0)return EMO_ITEM[k];}return "\uD83C\uDF7D";}
var STEPS=[["new","\uD83C\uDFE2","Tasdiqlash"],["accepted","\u2705","Qabul"],["preparing","\uD83C\uDF73","Tayyorlash"],["ready","\uD83D\uDED2","Tayyor"],["with_courier","\uD83D\uDEF5","Kuryer"],["on_the_way","\uD83C\uDFC3","Yo\u2018lda"],["delivered","\u2705","Yetkazildi"]];
var S={restaurants:[],rid:null,rname:'',cats:[],cart:{},delivery_fee:0,order:null,timer:null,
       name:'',phone:'',address:'',lat:null,lon:null,note:'',saved:[],activeCat:0,token:'',loading:false};
function el(i){return document.getElementById(i);}
function money(n){return Number(n||0).toLocaleString('ru-RU').replace(/,/g,' ')+" so'm";}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function q(s){return String(s||'').replace(/'/g,"\\'");}
function toast(t,kind){var e=el('toast');e.textContent=t;e.className='show '+(kind||'');clearTimeout(e._t);e._t=setTimeout(function(){e.className='';},2200);}
async function api(p,o){var r=await fetch(p,o);return await r.json();}
function show(h){el('view').innerHTML=h;}
function loading(){show('<div class="card"><div class="skel"></div><div class="skel"></div><div class="skel"></div></div>');}
function hero(){el('siteName').textContent=S.site_name||'Ovqat Yetkazish';
  el('chipOpen').textContent=(S.restaurants.length||0)+' ta restoran';
  el('chipFee').textContent='Dostavka '+money(S.delivery_fee);}
function setBar(){
  var c=0,s=0;for(var k in S.cart){c+=S.cart[k].qty;s+=S.cart[k].qty*S.cart[k].price;}
  el('bar').classList.toggle('hidden',c===0);
  if(c){el('barCount').textContent=c;el('barSum').textContent=money(s);}
}

/* ---------- XABARLARNI TURLARGA AJRATISH ---------- */
function msgKind(t){
  var s=String(t||'');
  if(s.indexOf('\u274C')>=0||s.indexOf('rad et')>=0||s.indexOf('bekor')>=0)return 'bad';
  if(s.indexOf('\u2705')>=0||s.indexOf('yetkazildi')>=0||s.indexOf('tasdiqlandi')>=0||s.indexOf('tayyor!')>=0)return 'ok';
  if(s.indexOf('\uD83C\uDF73')>=0||s.indexOf('\uD83D\uDED2')>=0||s.indexOf('tayyorlan')>=0||s.indexOf('kutil')>=0)return 'warn';
  if(s.indexOf('\uD83D\uDEF5')>=0||s.indexOf('\uD83C\uDFC3')>=0||s.indexOf('kuryer')>=0||s.indexOf('yo\u2018lda')>=0)return 'info';
  return 'info';
}
function msgIcon(t){
  /* Xabar boshidagi emoji (yoki birinchi so'z) ni ikonka qilib olamiz */
  var m=String(t||'').trim().match(/^(\S+)/);
  return m?m[1]:'\uD83D\uDCAC';
}

/* ---------- RESTORANLAR ---------- */
async function boot(){
  loading();
  var d=await api('/api/restaurants');
  S.restaurants=d.restaurants||[];S.delivery_fee=d.delivery_fee||0;S.site_name=d.site_name;
  hero();renderRestaurants();
}
function renderRestaurants(){
  var h='<div class="card"><div class="sec-title"><h2>Kimdan buyurtma qilamiz?</h2><span class="link" onclick="renderSaved()">Buyurtmalarim</span></div>';
  if(!S.restaurants.length){h+='<div class="empty"><span class="em">\uD83C\uDFEA</span>Hozircha ochiq restoran yo\u2018q</div>';}
  S.restaurants.forEach(function(r){
    h+='<div class="rest" onclick="openRest('+r.id+',\''+q(r.name)+'\')">'
     + '<div class="av">\uD83C\uDFEA</div>'
     + '<div class="info"><b>'+esc(r.name)+'</b><span><i class="dot"></i>Ochiq \u2022 menyuni ko\u2018rish</span></div>'
     + '<div class="go">\u203A</div></div>';
  });
  h+='</div>';
  show(h);setBar();
}
function renderSaved(){
  if(!S.saved.length){show('<div class="card"><div class="sec-title"><h2>Buyurtmalarim</h2><span class="link" onclick="renderRestaurants()">\u2190 Orqaga</span></div>'
    +'<div class="empty"><span class="em">\uD83D\uDCE6</span>Hali buyurtma bermadingiz</div></div>');return;}
  var h='<div class="card"><div class="sec-title"><h2>Buyurtmalarim</h2><span class="link" onclick="renderRestaurants()">\u2190 Orqaga</span></div>';
  S.saved.forEach(function(o){
    h+='<div class="rest" onclick="openOrder('+o.id+',\''+o.token+'\')"><div class="av">\uD83E\uDDFE</div>'
     + '<div class="info"><b>Buyurtma \u2116'+o.id+'</b><span>'+esc(o.rname||'')+' \u2022 '+esc(o.at||'')+'</span></div>'
     + '<div class="go">\u203A</div></div>';
  });
  h+='</div>';show(h);setBar();
}

/* ---------- MENYU ---------- */
async function openRest(rid,name){
  S.rid=rid;S.rname=name;S.activeCat=0;loading();
  var d=await api('/api/menu?restaurant='+rid);
  S.cats=d.categories||[];renderMenu();
}
function renderMenu(){
  var h='<div class="card"><div class="sec-title"><h2>'+esc(S.rname)+'</h2><span class="link" onclick="renderRestaurants()">\u2190 Restoranlar</span></div>';
  if(!S.cats.length){h+='<div class="empty"><span class="em">\uD83D\uDDD2</span>Bu restoranda menyu yo\u2018q</div></div>';show(h);setBar();return;}
  if(S.activeCat>=S.cats.length)S.activeCat=0;
  h+='<div class="tabs">';
  S.cats.forEach(function(c,i){
    var em=EMO[c.code]||'\uD83C\uDF7D';
    h+='<div class="tab '+(i===S.activeCat?'on':'')+'" onclick="selectCat('+i+')">'+em+' '+esc(c.label)+'</div>';
  });
  h+='</div>';
  var cat=S.cats[S.activeCat];
  cat.items.forEach(function(it){
    var n=(S.cart[it.id]||{}).qty||0;
    h+='<div class="item"><div class="em">'+emo(it.name)+'</div>'
     + '<div class="txt"><b>'+esc(it.name)+'</b><small>'+(it.desc?esc(it.desc)+' \u2022 ':'')+'<span class="price">'+money(it.price)+'</span></small></div>'
     + '<div class="qty">'
     + (n>0?'<button class="qbtn" onclick="dec('+it.id+')">\u2212</button><span class="qnum">'+n+'</span>':'')
     + '<button class="qbtn plus" onclick="add('+it.id+',\''+q(it.name)+'\','+it.price+')">+</button></div></div>';
  });
  h+='</div>';show(h);setBar();
}
function selectCat(i){S.activeCat=i;renderMenu();}
function add(id,name,price){var c=S.cart[id]||{qty:0,name:name,price:price};c.qty++;S.cart[id]=c;renderMenu();toast('\u2705 '+name+' qo\u2018shildi','ok');}
function dec(id){var c=S.cart[id];if(!c)return;c.qty--;if(c.qty<=0)delete S.cart[id];renderMenu();}

/* ---------- BUYURTMA BERISH ---------- */
function checkout(){
  if(!Object.keys(S.cart).length){toast('Savat bo\u2018sh','bad');return;}
  var food=0,h='<div class="card"><div class="sec-title"><h2>Buyurtmani tasdiqlash</h2><span class="link" onclick="renderMenu()">\u2190 Menyu</span></div>';
  h+='<div class="rows">';
  for(var k in S.cart){var c=S.cart[k];food+=c.qty*c.price;
    h+='<div class="row"><span>'+esc(c.name)+' \u00D7 '+c.qty+'</span><b>'+money(c.qty*c.price)+'</b></div>';}
  h+='<div class="row"><span>Ovqat</span><b>'+money(food)+'</b></div>';
  h+='<div class="row"><span>Dostavka</span><b>'+money(S.delivery_fee)+'</b></div>';
  h+='<div class="row total"><span>Jami</span><b>'+money(food+S.delivery_fee)+'</b></div></div>';
  h+='<p class="hint">\uD83D\uDCB5 To\u2018lov: yetkazilganda naqd (ovqat + dostavka)</p>';
  h+='<label>Ismingiz</label><input id="f_name" value="'+esc(S.name)+'" placeholder="Masalan: Ali Valiyev">';
  h+='<label>Telefon raqamingiz</label><input id="f_phone" value="'+esc(S.phone)+'" inputmode="tel" placeholder="+998 90 123 45 67">';
  h+='<label>Manzil (ko\u2018cha, uy, mo\u2018ljal)</label><textarea id="f_addr" placeholder="Masalan: Bobur ko\u2018chasi 12, ko\u2018k darvoza, 3-uy">'+esc(S.address)+'</textarea>';
  h+='<button class="btn ghost" onclick="geo()">\uD83D\uDCCD Joylashuvimni aniqlash</button>';
  h+='<div class="hint" id="geoInfo">'+(S.lat?'\u2705 Joylashuv olindi':'Lokatsiya ixtiyoriy \u2014 kuryer uchun foydali')+'</div>';
  h+='<label>Izoh (ixtiyoriy)</label><input id="f_note" value="'+esc(S.note)+'" placeholder="Masalan: achchiq qilmang">';
  h+='<div id="err"></div>';
  h+='<button class="btn" onclick="submitOrder()">\u2705 Buyurtmani yuborish</button></div>';
  show(h);window.scrollTo({top:0,behavior:'smooth'});
}
function geo(){
  if(!navigator.geolocation){el('geoInfo').textContent='Brauzer joylashuvni qo\u2018llamaydi';return;}
  el('geoInfo').textContent='\u23F3 Aniqlanmoqda...';
  navigator.geolocation.getCurrentPosition(function(p){
    S.lat=p.coords.latitude;S.lon=p.coords.longitude;
    el('geoInfo').textContent='\u2705 Joylashuv olindi';toast('Joylashuv olindi','ok');
  },function(){el('geoInfo').textContent='\u26A0\uFE0F Olib bo\u2018lmadi (manzil matni yetarli)';});
}
async function submitOrder(){
  S.name=el('f_name').value.trim();S.phone=el('f_phone').value.trim();
  S.address=el('f_addr').value.trim();S.note=el('f_note').value.trim();
  var items=[];for(var k in S.cart){items.push({id:Number(k),qty:S.cart[k].qty});}
  el('err').innerHTML='';
  var sendBtn=document.querySelector('#view .btn:last-child');if(sendBtn)sendBtn.disabled=true;
  var d=await api('/api/order',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({restaurant_id:S.rid,items:items,name:S.name,phone:S.phone,
      address:S.address,note:S.note,lat:S.lat,lon:S.lon})});
  if(d.error){
    el('err').innerHTML='<div class="err">\u26A0\uFE0F '+esc(d.error)+'</div>';
    toast(d.error,'bad');if(sendBtn)sendBtn.disabled=false;return;
  }
  S.cart={};setBar();
  var rec={id:d.order_id,token:d.token,rname:S.rname,at:new Date().toLocaleString('ru-RU')};
  S.saved.unshift(rec);S.saved=S.saved.slice(0,20);
  try{localStorage.setItem('site_orders',JSON.stringify(S.saved));}catch(e){}
  toast('Buyurtma yuborildi!','ok');
  openOrder(d.order_id,d.token,true);
}

/* ---------- HOLATNI KUZATISH ---------- */
async function openOrder(id,token,fresh){
  if(S.timer)clearInterval(S.timer);
  if(fresh){show('<div class="card"><div class="success-ico">\uD83C\uDF89</div>'
    +'<h2 style="text-align:center;margin:0">Buyurtma qabul qilindi!</h2>'
    +'<p class="hint">Operator tasdiqlashini kutmoqda \u2014 holat avtomatik yangilanadi</p></div><div class="card"><div class="spinner"></div></div>');}
  var d=await api('/api/order/'+id+'?t='+encodeURIComponent(token||''));
  if(d.error){show('<div class="card"><div class="empty"><span class="em">\uD83D\uDD0D</span>Buyurtma topilmadi</div></div>');return;}
  S.order=d;S.token=token;renderOrder();
  S.timer=setInterval(async function(){
    var n=await api('/api/order/'+id+'?t='+encodeURIComponent(token||''));
    if(!n.error){var grew=(n.events||[]).length>(S.order.events||[]).length;S.order=n;renderOrder(grew);}
  },7000);
}
function renderOrder(isNew){
  var o=S.order;if(!o)return;
  var idx=-1;for(var i=0;i<STEPS.length;i++){if(STEPS[i][0]===o.status)idx=i;}
  if(o.status==='cancelled')idx=-1;
  var icon=(idx>=0?STEPS[idx][1]:'\u274C');
  var h='<div class="card status-hero"><div class="status-ico">'+icon+'</div>'
    + '<h2>'+esc(o.status_label)+'</h2>'
    + '<p>Buyurtma \u2116'+o.id+' \u2022 <b>'+esc(o.restaurant)+'</b></p>';
  if(idx>=0){
    h+='<div class="stepper">';
    STEPS.forEach(function(s,i){
      var cls=(i<idx?'done':(i===idx?'on':''));
      h+='<div class="step '+cls+'"><div class="bubble">'+(i<idx?'\u2713':s[1])+'</div><div class="lbl">'+s[2]+'</div></div>';
    });
    h+='</div>';
  }
  h+='</div>';

  h+='<div class="card"><div class="sec-title"><h2>Tarkibi</h2><span class="link" onclick="renderRestaurants()">\uD83C\uDFE0 Bosh sahifa</span></div>';
  (o.items||[]).forEach(function(it){
    h+='<div class="item"><div class="em">'+emo(it.name)+'</div><div class="txt"><b>'+esc(it.name)+'</b><small>'+it.qty+' \u00D7 '+money(it.price)+'</small></div>'
     + '<span class="price">'+money(it.qty*it.price)+'</span></div>';
  });
  h+='<div class="rows"><div class="row"><span>Ovqat</span><b>'+money(o.food_cost)+'</b></div>'
   + '<div class="row"><span>Dostavka</span><b>'+money(o.delivery_fee)+'</b></div>'
   + '<div class="row total"><span>Jami</span><b>'+money(o.total)+'</b></div></div>';
  h+='<p class="hint">\uD83D\uDCCD '+esc(o.address)+'</p>'
   + '<p class="hint">\uD83D\uDD52 '+esc(o.created_at)+'</p></div>';

  if(o.courier){
    h+='<div class="card"><h2>Kuryer</h2><div class="courier"><div class="av">\uD83D\uDEF5</div>'
     + '<div><b>'+esc(o.courier.name)+'</b><div class="hint" style="margin:2px 0 0;text-align:left">'+esc(o.courier.phone||'')+'</div></div>'
     + (o.courier.phone?'<a class="call" href="tel:'+esc(o.courier.phone)+'">\uD83D\uDCDE Qo\u2018ng\u2018iroq</a>':'')
     + '</div></div>';
  }

  h+='<div class="card"><h2>Xabarlar</h2><div class="chat">';
  var ev=(o.events||[]);
  if(!ev.length)h+='<div class="empty"><span class="em">\uD83D\uDCAC</span>Hozircha xabar yo\u2018q</div>';
  ev.forEach(function(e,i){
    var k=msgKind(e.text);
    h+='<div class="msg '+k+((isNew&&i===0)?' new':'')+'"><div class="ic">'+msgIcon(e.text)+'</div>'
     + '<div class="bubble"><div class="t">'+esc(e.text)+'</div><div class="tm">'+esc(e.at)+'</div></div></div>';
  });
  h+='</div><p class="hint">\uD83D\uDD04 Sahifa har 7 sekundda yangilanadi</p></div>';
  show(h);
  var c=document.querySelector('.chat');if(c)c.scrollTop=0;
}
boot();
</script>
</body>
</html>
'''


async def web_index(request):
    return web.Response(text=WEB_HTML, content_type="text/html", charset="utf-8")


async def api_restaurants(request):
    data = [{"id": r["id"], "name": r["name"]} for r in restaurants_list(available_only=True)]
    return web.json_response({"restaurants": data, "site_name": SITE_NAME,
                              "delivery_fee": DELIVERY_FEE})


async def api_menu(request):
    try:
        rid = int(request.query.get("restaurant", 0))
    except Exception:
        rid = 0
    r = get_restaurant(rid)
    if not r or not r["is_available"]:
        return web.json_response({"error": "Restoran topilmadi"}, status=404)
    cats = []
    for code, label, name in CATEGORIES:
        items = menu_items(rid, category=name)
        if not items:
            continue
        cats.append({
            "code": code,
            "label": label,
            "items": [{"id": i["id"], "name": i["name"], "price": i["price"],
                       "desc": i.get("description") or ""} for i in items],
        })
    return web.json_response({"restaurant": {"id": r["id"], "name": r["name"]},
                              "categories": cats, "delivery_fee": DELIVERY_FEE})


async def api_create_order(request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri so'rov"}, status=400)

    try:
        rid = int(body.get("restaurant_id") or 0)
    except Exception:
        rid = 0
    name = (body.get("name") or "").strip()
    phone = (body.get("phone") or "").strip()
    address = (body.get("address") or "").strip()
    note = (body.get("note") or "").strip()
    lat = body.get("lat")
    lon = body.get("lon")
    items_in = body.get("items") or []

    r = get_restaurant(rid)
    if not r or not r["is_available"]:
        return web.json_response({"error": "Restoran topilmadi"}, status=400)
    if len(name) < 2:
        return web.json_response({"error": "Ismingizni kiriting"}, status=400)
    if len(re.sub(r"\D", "", phone)) < 9:
        return web.json_response({"error": "Telefon raqam noto'g'ri"}, status=400)
    if len(address) < 5:
        return web.json_response({"error": "Manzilni to'liq kiriting"}, status=400)

    # Narxlarni bazadan olamiz (mijoz yuborgan narxga ishonmaymiz)
    items, food = [], 0
    for it in items_in:
        try:
            iid = int(it.get("id"))
            qty = int(it.get("qty") or 1)
        except Exception:
            continue
        if qty < 1 or qty > 50:
            continue
        mi = get_menu_item(iid)
        if not mi or not mi["is_available"] or (mi["restaurant_id"] or 1) != rid:
            continue
        items.append({"name": mi["name"], "price": mi["price"], "qty": qty})
        food += mi["price"] * qty
    if not items:
        return web.json_response({"error": "Savat bo'sh — taom tanlang"}, status=400)

    token = secrets.token_hex(8)
    oid = create_order(
        source="site",
        customer_name=name,
        customer_phone=phone,
        customer_tg_id=None,
        items=items,
        food_cost=food,
        delivery_fee=DELIVERY_FEE,
        collect_food=1,
        address_text=address,
        lat=lat,
        lon=lon,
        note=note,
        restaurant_id=rid,
        track_token=token,
    )
    o = get_order(oid)
    add_event(oid, "✅ Buyurtmangiz qabul qilindi. Operator tasdiqlashini kuting.")

    kb = simple_kb([
        [("✅ Ruxsat berish", f"acc:{oid}")],
        [("❌ Bekor qilish", f"rej:{oid}")],
    ])
    sent = await notify_operators(
        f"🔔 <b>YANGI BUYURTMA №{oid}</b> (🌐 saytdan) — tasdiqlash kerak!\n\n"
        f"{order_card(o)}\n\n"
        f"➡️ «✅ Ruxsat berish» bosilgach buyurtma "
        f"<b>{esc(restaurant_name(rid))}</b> restoraniga yuboriladi.",
        kb,
    )
    if not sent:
        logging.warning(f"Sayt buyurtmasi №{oid}: operatorga xabar yuborilmadi (operator ro'yxatdan o'tmagan?)")

    return web.json_response({
        "ok": True, "order_id": oid, "token": token,
        "food_cost": food, "delivery_fee": DELIVERY_FEE, "total": food + DELIVERY_FEE,
    })


async def api_order_status(request):
    try:
        oid = int(request.match_info.get("oid", 0))
    except Exception:
        oid = 0
    o = get_order(oid)
    if not o:
        return web.json_response({"error": "Buyurtma topilmadi"}, status=404)
    t = request.query.get("t") or ""
    if o.get("track_token") and t != o["track_token"]:
        return web.json_response({"error": "Ruxsat yo'q"}, status=403)
    events = [{"text": e["text"], "at": fmt_dt(e["created_at"])}
              for e in order_events_list(oid, 30)]
    courier = None
    if o.get("courier_tg_id"):
        cu = get_user(o["courier_tg_id"])
        if cu:
            courier = {"name": cu["name"], "phone": cu["phone"]}
    try:
        items = json.loads(o.get("items") or "[]")
    except Exception:
        items = []
    return web.json_response({
        "id": o["id"],
        "status": o["status"],
        "status_label": status_label(o["status"]),
        "restaurant": restaurant_name(o.get("restaurant_id")),
        "items": items,
        "food_cost": o["food_cost"] or 0,
        "delivery_fee": o["delivery_fee"] or 0,
        "total": (o["food_cost"] or 0) + (o["delivery_fee"] or 0),
        "collect": collect_amount(o),
        "address": o["address_text"] or "",
        "created_at": fmt_dt(o["created_at"]),
        "courier": courier,
        "events": events,
    })


def local_ip_list():
    """Kompyuterning Wi-Fi/LAN IP manzillari (telefonda saytni ochish uchun)."""
    import socket
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            ips.append(ip)
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def build_web_app():
    app = web.Application()
    app.router.add_get("/", web_index)
    app.router.add_get("/api/restaurants", api_restaurants)
    app.router.add_get("/api/menu", api_menu)
    app.router.add_post("/api/order", api_create_order)
    app.router.add_get("/api/order/{oid}", api_order_status)
    return app


async def run_web():
    """Veb-saytni botlar bilan bir vaqtda ishga tushiradi.
    Sayt ishga tushmasa ham BOTLAR ishlashda davom etadi."""
    try:
        runner = web.AppRunner(build_web_app())
        await runner.setup()
        site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
        await site.start()
        logging.info(f"Veb-sayt ishga tushdi: http://127.0.0.1:{WEB_PORT}")
        print(f"  ✅ Veb-sayt tayyor: http://127.0.0.1:{WEB_PORT}")
    except OSError as e:
        logging.error(f"Veb-sayt ishga tushmadi (port {WEB_PORT} band bo'lishi mumkin): {e}")
        print(f"  ⚠️ Veb-sayt ishga tushmadi: port {WEB_PORT} band. Botlar ishlashda davom etadi.")
        print(f"     Yechim: delivery.py da WEB_PORT = {WEB_PORT + 1} qilib o'zgartiring.")
        return
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await runner.cleanup()
        raise


# ============================================================================
# [9] ISHGA TUSHIRISH
# ============================================================================

BOT_LABELS = {
    "customer": "Mijoz boti",
    "courier": "Kuryer boti",
    "operator": "Operator boti",
}


async def _run_bot(role: str, dp: Dispatcher):
    if role.startswith("restaurant_"):
        rid = int(role.split("_")[1])
        token = restaurant_token(rid)
        label = f"Restoran boti #{rid} ({restaurant_name(rid)})"
    else:
        token = {
            "customer": CUSTOMER_BOT_TOKEN,
            "courier": COURIER_BOT_TOKEN,
            "operator": OPERATOR_BOT_TOKEN,
        }[role]
        label = BOT_LABELS.get(role, role)
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logging.info(f"{label} ishga tushdi")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def main():
    init_db()
    print("=" * 56)
    print("  🛵 OVQAT YETKAZISH XIZMATI — 8 TA BOT + VEB-SAYT")
    print(f"  Mijoz    bot: https://t.me/Botjon01_bot")
    print(f"  Kuryer   bot: https://t.me/Botxon01_bot")
    print(f"  Operator bot: https://t.me/Botbek01_bot")
    print("  --- Restoran botlari ---")
    for r in RESTAURANT_BOTS:
        print(f"  {r['id']}) {r['name']:18s} bot ishga tushmoqda")
    print("  --- Veb-sayt (mijozlar uchun) ---")
    print(f"  Kompyuterda:   http://127.0.0.1:{WEB_PORT}")
    for ip in local_ip_list():
        print(f"  Telefonda:     http://{ip}:{WEB_PORT}   (bir Wi-Fi tarmog'ida)")
    print("  To'xtatish: Ctrl+C")
    print("=" * 56)

    tasks = [
        _run_bot("customer", dp_customer),
        _run_bot("courier", dp_courier),
        _run_bot("operator", dp_operator),
        run_web(),
    ]
    # Har bir restoran uchun alohida bot
    for r in RESTAURANT_BOTS:
        tasks.append(_run_bot(f"restaurant_{r['id']}", build_restaurant_dispatcher(r["id"])))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBotlar to'xtatildi.")
