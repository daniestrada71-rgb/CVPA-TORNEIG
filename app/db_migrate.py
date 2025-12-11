import psycopg2
from psycopg2.extras import DictCursor
import os

def run_migration():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL no definit — no es poden fer migracions")
        return

    conn = psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=DictCursor)
    cur = conn.cursor()

    print("🔧 Executant migració de taules…")

    # -------------------------------------
    # Taula EQUIPS
    # -------------------------------------
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

    # -------------------------------------
    # PISTES
    # -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pistes_grup (
            grup INTEGER PRIMARY KEY,
            pista INTEGER
        );
    """)

    # -------------------------------------
    # PARTITS
    # -------------------------------------
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

    # -------------------------------------
    # CLASSIFICACIÓ FINAL
    # -------------------------------------
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

    # -------------------------------------
    # CLASSIFICACIÓ ELIMINATS
    # -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS classificacio_eliminats (
            equip_nom TEXT PRIMARY KEY,
            punts INTEGER,
            dif_gol INTEGER,
            pos_grup INTEGER,
            grup INTEGER
        );
    """)

    # -------------------------------------
    # CONFIG FASES FINALS
    # -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        );
    """)

    # -------------------------------------
    # FASE FINAL EQUIPS
    # -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fase_final_equips (
            id SERIAL PRIMARY KEY,
            fase TEXT,
            equip_nom TEXT,
            posicio INTEGER,
            punts INTEGER DEFAULT 0,
            dif_gol INTEGER DEFAULT 0,
            pos_grup INTEGER DEFAULT 0,
            grup INTEGER DEFAULT 0
        );
    """)

    # Per si existeix la taula però falten columnes
    columns = [
        ("punts", "INTEGER DEFAULT 0"),
        ("dif_gol", "INTEGER DEFAULT 0"),
        ("pos_grup", "INTEGER DEFAULT 0"),
        ("grup", "INTEGER DEFAULT 0"),
    ]

    for col, definition in columns:
        try:
            cur.execute(f"ALTER TABLE fase_final_equips ADD COLUMN {col} {definition};")
            print(f"  ➕ Afegida columna {col}")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()

    # -------------------------------------
    # GALERIA
    # -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS galeria_links (
            id SERIAL PRIMARY KEY,
            titol TEXT,
            url TEXT
        );
    """)

    conn.commit()
    conn.close()
    print("🎉 Migracions completades!")
