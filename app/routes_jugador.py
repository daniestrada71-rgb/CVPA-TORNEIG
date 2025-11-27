import sqlite3
from flask import Blueprint, render_template, request, jsonify
from db import (
    obtenir_grups_guardats,
    obtenir_partits,
    calcular_classificacio,
    obtenir_config_fases_finals,
    obtenir_fase_final_equips
)

jugador_bp = Blueprint('jugador', __name__, url_prefix='/jugador')

# ========================================================
# 🏠 MENÚ PRINCIPAL JUGADOR
# ========================================================
@jugador_bp.route('/', methods=['GET'])
def menu_jugador():
    return render_template('jugador_menu.html')


# ========================================================
# 🟦 FASE DE GRUPS
# ========================================================
@jugador_bp.route('/fase-grups', methods=['GET'])
def fase_grups():
    grups_dict = obtenir_grups_guardats()
    grups = sorted(grups_dict.keys())
    return render_template('jugador_fase_grups.html', grups=grups)


@jugador_bp.route('/grup/<int:grup>', methods=['GET'])
def veure_grup(grup):
    partits = obtenir_partits(grup)
    classificacio = calcular_classificacio(grup)
    
    # Llegir pista assignada
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    row = c.execute("SELECT pista FROM pistes_grup WHERE grup=?", (grup,)).fetchone()
    conn.close()

    pista = row[0] if row and row[0] is not None else None

    return render_template(
        "jugador_grup.html",
        grup=grup,
        partits=partits,
        classificacio=classificacio,
        pista=pista
    )


@jugador_bp.route('/api/buscar_equip_grups')
def api_buscar_equip_grups():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({"ok": False, "resultats": []})

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    rows = c.execute("""
        SELECT nom_equip, grup
        FROM equips
        WHERE nom_equip IS NOT NULL
        AND grup IS NOT NULL
    """).fetchall()

    conn.close()

    resultats = []
    for nom, grup in rows:
        if q in nom.lower():
            resultats.append({
                "equip": nom,
                "grup": grup
            })

    return jsonify({"ok": True, "resultats": resultats})


# ========================================================
# 🟨 FASE FINAL
# ========================================================
@jugador_bp.route('/fase-final', methods=['GET'])
def fase_final_index():
    fases = obtenir_config_fases_finals() or {}

    fases_visibles = {
        k: v for k, v in fases.items()
        if k.upper() in ["OR", "PLATA", "BRONZE", "XOU"]
    }

    return render_template('jugador_fase_final.html', fases=fases_visibles)


# 🔍 API BUSCADOR FASE FINAL (CORREGIT)
@jugador_bp.route("/api/buscar_equip_fasefinal")
def buscar_equip_fasefinal():
    q = request.args.get("q", "").strip().lower()

    if not q:
        return jsonify({"ok": False, "resultats": []})

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT fase, equip_nom 
        FROM fase_final_equips
        WHERE LOWER(equip_nom) LIKE ?
        ORDER BY fase ASC
    """, (f"%{q}%",))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return jsonify({"ok": False, "resultats": []})

    resultats = [{"fase": r[0], "equip": r[1]} for r in rows]

    return jsonify({"ok": True, "resultats": resultats})


# ==========================
# 📋 Veure quadre (llista equips)
# ==========================
@jugador_bp.route('/fase-final/equips/<fase>')
def veure_equips_fase(fase):
    fase = fase.upper()

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    fases_cfg = dict(cur.fetchall())

    cur.execute("SELECT equip_nom, posicio FROM classificacio_final ORDER BY posicio ASC")
    tots = cur.fetchall()

    conn.close()

    if fase not in fases_cfg:
        return f"No existeix la fase {fase}"

    equips_fase = []
    pos = 0
    for f, n in fases_cfg.items():
        sub = tots[pos:pos+n]
        if f.upper() == fase:
            equips_fase = sub
            break
        pos += n

    return render_template(
        "jugador_fase_final_equips.html",
        fase=fase,
        equips=equips_fase
    )


# ==========================
# 🧩 Veure Bracket (jugador)
# ==========================
@jugador_bp.route('/fase-final/view/<fase>')
def veure_fase_final_jugador(fase):
    return render_template('jugador_fase_final_bracket.html', fase=fase.upper())

