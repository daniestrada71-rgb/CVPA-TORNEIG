import os
import psycopg2
from psycopg2.extras import DictCursor

# --------------------------------------------------------
# 🔧 CONFIGURACIÓ
# --------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ ERROR: No s'ha trobat DATABASE_URL a l'entorn!")

print("📌 Base de dades utilitzada: PostgreSQL (Neon)")


# --------------------------------------------------------
# 🔌 CONNEXIÓ A POSTGRES
# --------------------------------------------------------
def get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        cursor_factory=DictCursor
    )


# --------------------------------------------------------
# 🏗 CREACIÓ DE TOTES LES TAULES
# --------------------------------------------------------
def ensure_db_exists():
    conn = get_conn()
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
        );
    """)

    # Taula pistes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pistes_grup (
            grup INTEGER PRIMARY KEY,
            pista INTEGER
        );
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
        );
    """)

    # Classificació final
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

    # Eliminats
    cur.execute("""
        CREATE TABLE IF NOT EXISTS classificacio_eliminats (
            equip_nom TEXT PRIMARY KEY,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        );
    """)

    # Config fases finals
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        );
    """)

    # Fase final equips
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


# --------------------------------------------------------
# EXECUTE / FETCH HELPERS
# --------------------------------------------------------
def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()


def executemany(query, params_list):
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(query, params_list)
    conn.commit()
    conn.close()


def fetchall(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# --------------------------------------------------------
# 🔹 EQUIPS
# --------------------------------------------------------
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
    execute("DELETE FROM equips WHERE id=%s", (id,))


def eliminar_tots_equips():
    execute("DELETE FROM equips")


# --------------------------------------------------------
# 🔹 GRUPS
# --------------------------------------------------------
def obtenir_grups_guardats():
    equips = obtenir_equips()
    grups = {}
    for e in equips:
        grup = e["grup"]
        if grup is None:
            continue
        grups.setdefault(grup, []).append(e)
    for g in grups:
        grups[g] = sorted(grups[g], key=lambda x: x["ordre"] or 0)
    return grups


def obtenir_grups():
    return fetchall("""
        SELECT grup, ordre, nom_equip, id
        FROM equips
        WHERE grup IS NOT NULL
        ORDER BY grup ASC, ordre ASC
    """)


# --------------------------------------------------------
# 🔹 PARTITS
# --------------------------------------------------------
def generar_partits(grup_id):
    files = fetchall("""
        SELECT nom_equip
        FROM equips
        WHERE grup=%s
        ORDER BY ordre
    """, (grup_id,))
    equips = [row[0] for row in files]
    N = len(equips)

    execute("DELETE FROM partits WHERE grup=%s", (grup_id,))

    patrons = {
        4: [(1,3,2),(0,2,3),(1,2,0),(0,3,2),(2,3,1),(0,1,3)],
        5: [(1,3,2),(2,0,4),(4,1,3),(2,3,0),(0,4,1),(2,1,3),(3,4,0),(1,0,4),(2,4,1),(3,0,2)],
        6: [(3,2,1),(0,5,4),(1,4,2),(2,0,3),(3,4,5),(1,5,4),(2,4,3),(3,5,1),(0,1,2),
            (2,5,0),(4,0,1),(1,3,4),(5,4,0),(3,0,5),(1,2,3)]
    }

    if N not in patrons:
        return 0

    inserts = [
        (grup_id, equips[a], equips[b], equips[c])
        for a, b, c in patrons[N]
    ]

    executemany("""
        INSERT INTO partits (grup, equip1, equip2, arbitre)
        VALUES (%s, %s, %s, %s)
    """, inserts)

    return len(inserts)


def obtenir_partits(grup_id):
    return fetchall("""
        SELECT id, equip1, equip2, arbitre, punts1, punts2, jugat
        FROM partits
        WHERE grup=%s
        ORDER BY id
    """, (grup_id,))


def actualitzar_resultat(partit_id, punts1, punts2):
    execute("""
        UPDATE partits
        SET punts1=%s, punts2=%s, jugat=1
        WHERE id=%s
    """, (punts1, punts2, partit_id))

# --------------------------------------------------------
# 🔹 CLASSIFICACIÓ
# --------------------------------------------------------
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
                "pj": 0,
                "pg": 0,
                "pp": 0
            }

    for row in partits:
        e1 = row[1]
        e2 = row[2]
        p1 = row[4]
        p2 = row[5]
        jugat = row[6]

        ensure(e1)
        ensure(e2)

        # Si el partit no s’ha jugat, o és 0-0, no el comptem
        if jugat != 1 or (p1 == 0 and p2 == 0):
            continue

        stats[e1]["pj"] += 1
        stats[e2]["pj"] += 1

        stats[e1]["favor"] += p1
        stats[e1]["contra"] += p2

        stats[e2]["favor"] += p2
        stats[e2]["contra"] += p1

        # Partit guanyat / perdut
        if p1 > p2:
            stats[e1]["pg"] += 1
            stats[e2]["pp"] += 1
            stats[e1]["punts"] += 3
        elif p2 > p1:
            stats[e2]["pg"] += 1
            stats[e1]["pp"] += 1
            stats[e2]["punts"] += 3

    # Diferència
    for e in stats:
        stats[e]["diferencia"] = stats[e]["favor"] - stats[e]["contra"]

    # Ordenar igual que abans
    return sorted(
        stats.items(),
        key=lambda x: (x[1]["punts"], x[1]["diferencia"], x[1]["favor"]),
        reverse=True
    )

# --------------------------------------------------------
# 🔹 FASE FINAL
# --------------------------------------------------------
def obtenir_config_fases_finals():
    files = fetchall("SELECT fase, num_equips FROM config_fases_finals")

    ordre = ["OR","PLATA","BRONZE","SHOW","XOU"]

    return {
        fase.upper() : num
        for fase, num in sorted(files, key=lambda x: ordre.index(x[0].upper()))
    }

def generar_fase_final_equips():
    """
    Llegeix 'classificacio_final' i crea la taula fase_final_equips
    amb els equips classificats, ordenats i assignats a fases.
    Compatible 100% amb PostgreSQL.
    """

    conn = get_conn()
    cur = conn.cursor()

    # Crear taula si no existeix (PostgreSQL)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id SERIAL PRIMARY KEY,
            fase TEXT,
            posicio INTEGER,
            equip_nom TEXT,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        )
    """)

    # Buidar contingut antic
    cur.execute("DELETE FROM fase_final_equips")

    # Llegir configuració de fases
    cur.execute("SELECT fase, num_equips FROM config_fases_finals ORDER BY fase ASC")
    fases = cur.fetchall()

    # Llegir classificació final
    cur.execute("""
        SELECT equip_nom, punts, dif_gol, pos_grup, grup
        FROM classificacio_final
        ORDER BY posicio ASC
    """)
    classificats = cur.fetchall()

    index = 0
    for fase, n_equips in fases:
        sublist = classificats[index:index + n_equips]

        pos = 1
        for eq_nom, punts, dif, pos_g, grup in sublist:
            cur.execute("""
                INSERT INTO fase_final_equips
                (fase, posicio, equip_nom, punts, dif_gol, pos_grup, grup)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (fase, pos, eq_nom, punts, dif, pos_g, grup))
            pos += 1

        index += n_equips

    conn.commit()
    conn.close()

def obtenir_fase_final_equips(fase):
    fase = fase.upper()
    return fetchall("""
        SELECT equip_nom, posicio
        FROM fase_final_equips
        WHERE fase=%s
        ORDER BY posicio
    """, (fase,))







