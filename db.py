import sqlite3
import os
from collections import defaultdict

DB_FILE = "/tmp/cvpa.db"
print("📌 Base de dades temporal:", DB_FILE)
print("📌 BASE DE DADES QUE SED UTILITZA:", DB_FILE)


# ----------------------------------------------------------------------
# 🔹 CREACIÓ BASE DE DADES
# ----------------------------------------------------------------------
def create_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

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
    c.execute("""
    CREATE TABLE IF NOT EXISTS pistes_grup (
        grup INTEGER PRIMARY KEY,
        pista INTEGER
    )
    """)


    conn.commit()
    conn.close()

# ----------------------------------------------------------------------
# 🔹 EQUIPS
# ----------------------------------------------------------------------
def obtenir_equips():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT id, nom_participants, nom_equip, valor, email, telefon, grup, ordre
        FROM equips ORDER BY id ASC
    """)
    equips = c.fetchall()
    conn.close()
    return equips

def obtenir_equip(id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nom_participants, nom_equip, valor, email, telefon, grup, ordre FROM equips WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()
    return row

def afegir_equip(nom_participants, nom_equip, valor, email, telefon):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO equips (nom_participants, nom_equip, valor, email, telefon)
        VALUES (?, ?, ?, ?, ?)
    """, (nom_participants, nom_equip, valor, email, telefon))
    conn.commit()
    conn.close()

def modificar_equip(id, nom_participants, nom_equip, valor, email, telefon):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE equips SET nom_participants=?, nom_equip=?, valor=?, email=?, telefon=?
        WHERE id=?
    """, (nom_participants, nom_equip, valor, email, telefon, id))
    conn.commit()
    conn.close()

def eliminar_equip(id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM equips WHERE id=?", (id,))
    conn.commit()
    conn.close()

def eliminar_tots_equips():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM equips")
    c.execute("DELETE FROM sqlite_sequence WHERE name='equips'")
    conn.commit()
    conn.close()

# ----------------------------------------------------------------------
# 🔹 GRUPS
# ----------------------------------------------------------------------
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
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT grup, ordre, nom_equip, id
        FROM equips
        WHERE grup IS NOT NULL
        ORDER BY grup ASC, ordre ASC
    """)
    files = cur.fetchall()
    conn.close()
    return files

# ----------------------------------------------------------------------
# 🔹 PARTITS
# ----------------------------------------------------------------------
def crear_taula_partits():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
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
    conn.commit()
    conn.close()

crear_taula_partits()

def generar_partits(grup_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nom_equip FROM equips WHERE grup=? ORDER BY ordre", (grup_id,))
    equips = [row[0] for row in c.fetchall()]
    N = len(equips)

    c.execute("DELETE FROM partits WHERE grup=?", (grup_id,))

    # Patrons
    patrons = {
        4: [(1,3,2),(0,2,3),(1,2,0),(0,3,2),(2,3,1),(0,1,3)],
        5: [(1,3,2),(2,0,4),(4,1,3),(2,3,0),(0,4,1),(2,1,3),(3,4,0),(1,0,4),(2,4,1),(3,0,2)],
        6: [(3,2,1),(0,5,4),(1,4,2),(2,0,3),(3,4,5),(1,5,4),(2,4,3),(3,5,1),(0,1,2),(2,5,0),
            (4,0,1),(1,3,4),(5,4,0),(3,0,5),(1,2,3)]
    }

    if N not in patrons:
        conn.close()
        return 0

    inserts = []
    for eq1, eq2, arb in patrons[N]:
        if eq1 < N and eq2 < N and arb < N:
            inserts.append((grup_id, equips[eq1], equips[eq2], equips[arb]))

    c.executemany("""
        INSERT INTO partits (grup, equip1, equip2, arbitre)
        VALUES (?, ?, ?, ?)
    """, inserts)

    conn.commit()
    conn.close()
    return len(inserts)

def obtenir_partits(grup_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT id, equip1, equip2, arbitre, punts1, punts2, jugat
        FROM partits
        WHERE grup=?
        ORDER BY id
    """, (grup_id,))
    partits = c.fetchall()
    conn.close()
    return partits

def actualitzar_resultat(partit_id, punts1, punts2):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE partits
        SET punts1=?, punts2=?, jugat=1
        WHERE id=?
    """, (punts1, punts2, partit_id))
    conn.commit()
    conn.close()

def calcular_classificacio(grup):
    partits = obtenir_partits(grup)

    stats = {}

    # inicialitzar
    def ensure(e):
        if e not in stats:
            stats[e] = {
                "punts": 0,
                "favor": 0,
                "contra": 0,
                "diferencia": 0,
                "pj": 0   # <<--- AFEGIT
            }

    for row in partits:
        # Format partit:
        # (id, equip1, equip2, arbit, p1, p2, jugat)
        e1 = row[1]
        e2 = row[2]
        p1 = row[4]
        p2 = row[5]

        if not e1 or not e2:
            continue

        ensure(e1)
        ensure(e2)

        # Només comptem com a jugat si tenim números correctes
        try:
            p1n = int(p1)
            p2n = int(p2)
        except:
            continue

        # Sumem PARTIT JUGAT aquí
        stats[e1]["pj"] += 1
        stats[e2]["pj"] += 1

        # Favor / contra
        stats[e1]["favor"] += p1n
        stats[e1]["contra"] += p2n

        stats[e2]["favor"] += p2n
        stats[e2]["contra"] += p1n

        # Punts (victòria = 3)
        if p1n > p2n:
            stats[e1]["punts"] += 3
        elif p2n > p1n:
            stats[e2]["punts"] += 3
        else:
            # Empat (per si mai es dona)
            stats[e1]["punts"] += 0
            stats[e2]["punts"] += 0

    # Diferència
    for e, s in stats.items():
        s["diferencia"] = s["favor"] - s["contra"]

    # Ordenar classificació
    classificacio = sorted(
        stats.items(),
        key=lambda x: (x[1]["punts"], x[1]["diferencia"], x[1]["favor"]),
        reverse=True
    )

    return classificacio

# ----------------------------------------------------------------------
# 🔹 FASE FINAL
# ----------------------------------------------------------------------
def obtenir_config_fases_finals():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        )
    """)
    cur.execute("SELECT fase, num_equips FROM config_fases_finals ORDER BY fase ASC")
    files = cur.fetchall()
    conn.close()

    ordre = ["OR", "PLATA", "BRONZE", "XOU"]
    return {fase.upper(): num for fase, num in sorted(files, key=lambda x: ordre.index(x[0].upper()))}

def generar_fase_final_equips():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        )
    """)

    cur.execute("DELETE FROM fase_final_equips")

    cur.execute("SELECT fase, num_equips FROM config_fases_finals ORDER BY fase ASC")
    fases = cur.fetchall()

    cur.execute("SELECT equip_nom FROM classificacio_final ORDER BY posicio ASC")
    equips = [e[0] for e in cur.fetchall()]

    pos = 0
    for fase, n in fases:
        for i, nom in enumerate(equips[pos:pos+n], start=1):
            cur.execute("""
                INSERT INTO fase_final_equips (fase, equip_nom, posicio)
                VALUES (?, ?, ?)
            """, (fase.upper(), nom, i))
        pos += n

    conn.commit()
    conn.close()

def generar_fase_final_equips():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        )
    """)

    cur.execute("DELETE FROM fase_final_equips")

    # ORDRE CORRECTE DE LES FASES
    ordre = ["OR", "PLATA", "BRONZE", "XOU"]

    # Carreguem configuració i la reordenem manualment
    cfg = obtenir_config_fases_finals()
    fases = [(fase, cfg[fase]) for fase in ordre if fase in cfg]

    # ordre correcte segons classificació
    cur.execute("SELECT equip_nom FROM classificacio_final ORDER BY posicio ASC")
    equips = [e[0] for e in cur.fetchall()]

    pos = 0
    for fase, n in fases:
        sub = equips[pos:pos+n]
        for i, nom in enumerate(sub, start=1):
            cur.execute("""
                INSERT INTO fase_final_equips (fase, equip_nom, posicio)
                VALUES (?, ?, ?)
            """, (fase, nom, i))
        pos += n

    conn.commit()
    conn.close()

def obtenir_fase_final_equips(fase):
    fase = fase.upper()

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER
        )
    """)

    cur.execute("""
        SELECT equip_nom, posicio
        FROM fase_final_equips
        WHERE fase=?
        ORDER BY posicio ASC
    """, (fase,))
    equips = cur.fetchall()
    conn.close()

    fases_cfg = obtenir_config_fases_finals()
    necessaris = fases_cfg.get(fase, 0)

    if len(equips) != necessaris:
        generar_fase_final_equips()

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT equip_nom, posicio
            FROM fase_final_equips
            WHERE fase=?
            ORDER BY posicio ASC
        """, (fase,))
        equips = cur.fetchall()
        conn.close()

    return equips

