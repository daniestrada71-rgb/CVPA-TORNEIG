import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor

# -----------------------------
# Detectar si usem PostgreSQL
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    print("📌 Base de dades utilitzada: PostgreSQL (Neon)")
else:
    print("📌 Base de dades utilitzada: SQLite local")


# -----------------------------
# Connexió PostgreSQL
# -----------------------------
def pg_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -----------------------------
# CREACIÓ DE TAULES (POSTGRES o SQLITE)
# -----------------------------

def create_tables_pg():
    """Crea totes les taules a PostgreSQL si no existeixen."""
    conn = pg_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS equips (
            id SERIAL PRIMARY KEY,
            nom_participants TEXT,
            nom_equip TEXT,
            valor INTEGER,
            email TEXT,
            telefon TEXT,
            grup INTEGER,
            ordre INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pistes_grup (
            grup INTEGER PRIMARY KEY,
            pista INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS partits (
            id SERIAL PRIMARY KEY,
            grup INTEGER,
            equip1 TEXT,
            equip2 TEXT,
            arbitre TEXT,
            punts1 INTEGER DEFAULT 0,
            punts2 INTEGER DEFAULT 0,
            jugat INTEGER DEFAULT 0
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classificacio_final (
            id SERIAL PRIMARY KEY,
            posicio INTEGER,
            equip_nom TEXT,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classificacio_eliminats (
            equip_nom TEXT PRIMARY KEY,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id SERIAL PRIMARY KEY,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        );
    """)

    conn.commit()
    conn.close()


def create_tables_sqlite(DB_FILE):
    """Crea totes les taules per SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS equips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_participants TEXT,
            nom_equip TEXT,
            valor INTEGER,
            email TEXT,
            telefon TEXT,
            grup INTEGER,
            ordre INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pistes_grup (
            grup INTEGER PRIMARY KEY,
            pista INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS partits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup INTEGER,
            equip1 TEXT,
            equip2 TEXT,
            arbitre TEXT,
            punts1 INTEGER DEFAULT 0,
            punts2 INTEGER DEFAULT 0,
            jugat INTEGER DEFAULT 0
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classificacio_final (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posicio INTEGER,
            equip_nom TEXT,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classificacio_eliminats (
            equip_nom TEXT PRIMARY KEY,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        );
    """)

    conn.commit()
    conn.close()


# -----------------------------
# FUNCIÓ PRINCIPAL
# -----------------------------

def ensure_db_exists():
    """Assegura que totes les taules existeixin a PostgreSQL o SQLite."""
    if USE_POSTGRES:
        print("📌 PostgreSQL detectat — creant/validant taules…")
        create_tables_pg()
    else:
        DB_FILE = os.path.join(os.path.dirname(__file__), "cvpa.db")
        print("📌 SQLite — creant/validant taules…")
        create_tables_sqlite(DB_FILE)
        
def execute(query, params=()):
    if USING_POSTGRES:
        conn = _get_pg_conn()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        conn.close()
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute(_adapt_query(query), params)
        conn.commit()
        conn.close()


def executemany(query, params_list):
    if USING_POSTGRES:
        conn = _get_pg_conn()
        cur = conn.cursor()
        cur.executemany(query, params_list)
        conn.commit()
        conn.close()
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.executemany(_adapt_query(query), params_list)
        conn.commit()
        conn.close()


# --------------------------------------------------
#  CREACIÓ / INICIALITZACIÓ BD
# --------------------------------------------------
def create_db():
    """
    Crea totes les taules necessàries tant a SQLite com a PostgreSQL.
    Es crida des de app/__init__.py → create_app()
    """
    if USING_POSTGRES:
        conn = _get_pg_conn()
        cur = conn.cursor()

        # Taula equips
        cur.execute("""
            CREATE TABLE IF NOT EXISTS equips (
                id SERIAL PRIMARY KEY,
                nom_participants TEXT,
                nom_equip TEXT,
                valor INTEGER,
                email TEXT,
                telefon TEXT,
                grup INTEGER,
                ordre INTEGER
            )
        """)

        # Taula pistes_grup
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pistes_grup (
                grup INTEGER PRIMARY KEY,
                pista INTEGER
            )
        """)

        # Taula partits
        cur.execute("""
            CREATE TABLE IF NOT EXISTS partits (
                id SERIAL PRIMARY KEY,
                grup INTEGER,
                equip1 TEXT,
                equip2 TEXT,
                arbitre TEXT,
                punts1 INTEGER DEFAULT 0,
                punts2 INTEGER DEFAULT 0,
                jugat INTEGER DEFAULT 0
            )
        """)

        # Taula classificacio_final
        cur.execute("""
            CREATE TABLE IF NOT EXISTS classificacio_final (
                id SERIAL PRIMARY KEY,
                posicio INTEGER,
                equip_nom TEXT,
                punts INTEGER,
                dif_gol INTEGER,
                pos_grup INTEGER,
                grup INTEGER
            )
        """)

        # Config fases finals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config_fases_finals (
                fase TEXT PRIMARY KEY,
                num_equips INTEGER
            )
        """)

        # Fase final equips
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fase_final_equips (
                id SERIAL PRIMARY KEY,
                fase TEXT,
                equip_nom TEXT,
                posicio INTEGER
            )
        """)

        # Eliminats
        cur.execute("""
            CREATE TABLE IF NOT EXISTS classificacio_eliminats (
                equip_nom TEXT PRIMARY KEY,
                punts INTEGER,
                dif_gol INTEGER,
                pos_grup INTEGER,
                grup INTEGER
            )
        """)

        conn.commit()
        conn.close()

    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()

        # Taula equips
        c.execute("""
            CREATE TABLE IF NOT EXISTS equips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_participants TEXT,
                nom_equip TEXT,
                valor INTEGER,
                email TEXT,
                telefon TEXT,
                grup INTEGER,
                ordre INTEGER
            )
        """)

        # Taula pistes_grup
        c.execute("""
            CREATE TABLE IF NOT EXISTS pistes_grup (
                grup INTEGER PRIMARY KEY,
                pista INTEGER
            )
        """)

        # Taula partits
        c.execute("""
            CREATE TABLE IF NOT EXISTS partits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grup INTEGER,
                equip1 TEXT,
                equip2 TEXT,
                arbitre TEXT,
                punts1 INTEGER DEFAULT 0,
                punts2 INTEGER DEFAULT 0,
                jugat INTEGER DEFAULT 0
            )
        """)

        # Taula classificacio_final
        c.execute("""
            CREATE TABLE IF NOT EXISTS classificacio_final (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                posicio INTEGER,
                equip_nom TEXT,
                punts INTEGER,
                dif_gol INTEGER,
                pos_grup INTEGER,
                grup INTEGER
            )
        """)

        # Config fases finals
        c.execute("""
            CREATE TABLE IF NOT EXISTS config_fases_finals (
                fase TEXT PRIMARY KEY,
                num_equips INTEGER
            )
        """)

        # Fase final equips
        c.execute("""
            CREATE TABLE IF NOT EXISTS fase_final_equips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fase TEXT,
                equip_nom TEXT,
                posicio INTEGER
            )
        """)

        # Eliminats
        c.execute("""
            CREATE TABLE IF NOT EXISTS classificacio_eliminats (
                equip_nom TEXT PRIMARY KEY,
                punts INTEGER,
                dif_gol INTEGER,
                pos_grup INTEGER,
                grup INTEGER
            )
        """)

        conn.commit()
        conn.close()


# --------------------------------------------------
# 🔹 EQUIPS
# --------------------------------------------------
def obtenir_equips():
    return fetchall("""
        SELECT id, nom_participants, nom_equip, valor, email, telefon, grup, ordre
        FROM equips ORDER BY id ASC
    """)


def obtenir_equip(id):
    rows = fetchall("""
        SELECT id, nom_participants, nom_equip, valor, email, telefon, grup, ordre
        FROM equips
        WHERE id=%s
    """, (id,))
    return rows[0] if rows else None


def afegir_equip(nom_participants, nom_equip, valor, email, telefon):
    execute("""
        INSERT INTO equips (nom_participants, nom_equip, valor, email, telefon)
        VALUES (%s, %s, %s, %s, %s)
    """, (nom_participants, nom_equip, valor, email, telefon))


def modificar_equip(id, nom_participants, nom_equip, valor, email, telefon):
    execute("""
        UPDATE equips
        SET nom_participants=%s, nom_equip=%s, valor=%s, email=%s, telefon=%s
        WHERE id=%s
    """, (nom_participants, nom_equip, valor, email, telefon, id))


def eliminar_equip(id):
    execute("""
        DELETE FROM equips WHERE id=%s
    """, (id,))


def eliminar_tots_equips():
    execute("DELETE FROM equips")
    # Reset id només a SQLite
    if not USING_POSTGRES:
        execute("DELETE FROM sqlite_sequence WHERE name='equips'")


# --------------------------------------------------
# 🔹 GRUPS
# --------------------------------------------------
def obtenir_grups_guardats():
    equips = obtenir_equips()
    grups = {}
    for e in equips:
        grup = e[6]
        if grup is None:
            continue
        if grup not in grups:
            grups[grup] = []
        grups[grup].append(e)

    for g in grups:
        grups[g] = sorted(grups[g], key=lambda x: x[7] if x[7] is not None else 0)

    return grups


def obtenir_grups():
    files = fetchall("""
        SELECT grup, ordre, nom_equip, id
        FROM equips
        WHERE grup IS NOT NULL
        ORDER BY grup ASC, ordre ASC
    """)
    return files


# --------------------------------------------------
# 🔹 PARTITS
# --------------------------------------------------
def generar_partits(grup_id):
    # Agafem equips del grup ordenats
    files = fetchall("""
        SELECT nom_equip
        FROM equips
        WHERE grup=%s
        ORDER BY ordre
    """, (grup_id,))
    equips = [row[0] for row in files]
    N = len(equips)

    # Esborrem antics partits del grup
    execute("DELETE FROM partits WHERE grup=%s", (grup_id,))

    # Patrons segons N
    patrons = {
        4: [(1, 3, 2), (0, 2, 3), (1, 2, 0), (0, 3, 2), (2, 3, 1), (0, 1, 3)],
        5: [(1, 3, 2), (2, 0, 4), (4, 1, 3), (2, 3, 0), (0, 4, 1),
            (2, 1, 3), (3, 4, 0), (1, 0, 4), (2, 4, 1), (3, 0, 2)],
        6: [(3, 2, 1), (0, 5, 4), (1, 4, 2), (2, 0, 3), (3, 4, 5),
            (1, 5, 4), (2, 4, 3), (3, 5, 1), (0, 1, 2), (2, 5, 0),
            (4, 0, 1), (1, 3, 4), (5, 4, 0), (3, 0, 5), (1, 2, 3)]
    }

    if N not in patrons:
        return 0

    inserts = []
    for eq1, eq2, arb in patrons[N]:
        if eq1 < N and eq2 < N and arb < N:
            inserts.append((grup_id, equips[eq1], equips[eq2], equips[arb]))

    if inserts:
        executemany("""
            INSERT INTO partits (grup, equip1, equip2, arbitre)
            VALUES (%s, %s, %s, %s)
        """, inserts)

    return len(inserts)


def obtenir_partits(grup_id):
    partits = fetchall("""
        SELECT id, equip1, equip2, arbitre, punts1, punts2, jugat
        FROM partits
        WHERE grup=%s
        ORDER BY id
    """, (grup_id,))
    return partits


def actualitzar_resultat(partit_id, punts1, punts2):
    execute("""
        UPDATE partits
        SET punts1=%s, punts2=%s, jugat=1
        WHERE id=%s
    """, (punts1, punts2, partit_id))


def calcular_classificacio(grup):
    partits = obtenir_partits(grup)

    stats = {}

    def ensure(e):
        if e not in stats:
            stats[e] = {
                "punts": 0,
                "favor": 0,
                "contra": 0,
                "diferencia": 0,
                "pj": 0
            }

    for row in partits:
        # (id, equip1, equip2, arbitre, p1, p2, jugat)
        e1 = row[1]
        e2 = row[2]
        p1 = row[4]
        p2 = row[5]
        jugat = row[6]

        if not e1 or not e2:
            continue

        ensure(e1)
        ensure(e2)

        # Només si està marcat jugat
        if jugat != 1:
            continue

        p1n = int(p1) if p1 is not None else 0
        p2n = int(p2) if p2 is not None else 0

        stats[e1]["pj"] += 1
        stats[e2]["pj"] += 1

        stats[e1]["favor"] += p1n
        stats[e1]["contra"] += p2n

        stats[e2]["favor"] += p2n
        stats[e2]["contra"] += p1n

        if p1n > p2n:
            stats[e1]["punts"] += 3
        elif p2n > p1n:
            stats[e2]["punts"] += 3
        else:
            # empat
            stats[e1]["punts"] += 0
            stats[e2]["punts"] += 0

    for e, s in stats.items():
        s["diferencia"] = s["favor"] - s["contra"]

    classificacio = sorted(
        stats.items(),
        key=lambda x: (x[1]["punts"], x[1]["diferencia"], x[1]["favor"]),
        reverse=True
    )

    return classificacio


# --------------------------------------------------
# 🔹 FASE FINAL
# --------------------------------------------------
def obtenir_config_fases_finals():
    files = fetchall("""
        SELECT fase, num_equips
        FROM config_fases_finals
        ORDER BY fase ASC
    """)
    ordre = ["OR", "PLATA", "BRONZE", "XOU"]
    return {
        fase.upper(): num
        for fase, num in sorted(files, key=lambda x: ordre.index(x[0].upper()) if x[0].upper() in ordre else 999)
    }


def generar_fase_final_equips():
    conn = _get_pg_conn() if USING_POSTGRES else _get_sqlite_conn()
    cur = conn.cursor()

    # Ens assegurem que taula existeix
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id {} PRIMARY KEY,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        )
    """.format("SERIAL" if USING_POSTGRES else "INTEGER AUTOINCREMENT"))

    # Buidem
    cur.execute("DELETE FROM fase_final_equips")

    # Ordre de fases
    ordre = ["OR", "PLATA", "BRONZE", "XOU"]

    # Config
    cfg = obtenir_config_fases_finals()
    fases = [(fase, cfg[fase]) for fase in ordre if fase in cfg]

    # Classificació global
    cur.execute("SELECT equip_nom FROM classificacio_final ORDER BY posicio ASC")
    equips = [e[0] for e in cur.fetchall()]

    pos = 0
    for fase, n in fases:
        sub = equips[pos:pos + n]
        for i, nom in enumerate(sub, start=1):
            cur.execute("""
                INSERT INTO fase_final_equips (fase, equip_nom, posicio)
                VALUES (%s, %s, %s)
            """.replace("%s", "%s" if USING_POSTGRES else "?"),
                        (fase, nom, i))
        pos += n

    conn.commit()
    conn.close()


def obtenir_fase_final_equips(fase):
    fase = fase.upper()
    # Assegurem que hi ha dades correctes
    fases_cfg = obtenir_config_fases_finals()
    necessaris = fases_cfg.get(fase, 0)

    conn = _get_pg_conn() if USING_POSTGRES else _get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id {} PRIMARY KEY,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        )
    """.format("SERIAL" if USING_POSTGRES else "INTEGER AUTOINCREMENT"))

    cur.execute("""
        SELECT equip_nom, posicio
        FROM fase_final_equips
        WHERE fase=%s
        ORDER BY posicio ASC
    """.replace("%s", "%s" if USING_POSTGRES else "?"), (fase,))
    equips = cur.fetchall()

    if len(equips) != necessaris and necessaris > 0:
        conn.close()
        # regenerem
        generar_fase_final_equips()
        conn = _get_pg_conn() if USING_POSTGRES else _get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT equip_nom, posicio
            FROM fase_final_equips
            WHERE fase=%s
            ORDER BY posicio ASC
        """.replace("%s", "%s" if USING_POSTGRES else "?"), (fase,))
        equips = cur.fetchall()

    conn.close()
    return equips



