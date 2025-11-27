from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from db import (
    get_conn,
    calcular_classificacio,
    obtenir_grups_guardats,
)
from .auth import require_admin
import os
import json

admin_fasefinal_bp = Blueprint('admin_fasefinal', __name__)

# ---------------------------------------------------------
# 🧹 RESET CLASSIFICACIÓ FINAL + FASE FINAL
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/reset_classificacio_final')
def reset_classificacio_final():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM classificacio_final")
    cur.execute("DELETE FROM fase_final_equips")
    cur.execute("DELETE FROM classificacio_eliminats")

    conn.commit()
    conn.close()
    return "Classificació final i fases finals reiniciades!"


# ---------------------------------------------------------
# Ens assegurem que la taula d'eliminats existeix (PostgreSQL)
# ---------------------------------------------------------
conn = get_conn()
cur = conn.cursor()
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


# ---------------------------------------------------------
# 🧮 CLASSIFICACIÓ ÚNICA (FASE FINAL)
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal', methods=['GET'])
@require_admin
def fase_final_classificacio():
    conn = get_conn()
    cur = conn.cursor()

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

    cur.execute("SELECT equip_nom, punts, dif_gol, pos_grup, grup FROM classificacio_final ORDER BY posicio")
    guardada = cur.fetchall()

    conn.close()

    if guardada:
        classificacio = [
            {"equip": e, "punts": p, "dif": d, "pos": pg, "grup": g}
            for e, p, d, pg, g in guardada
        ]
    else:
        classificacio = generar_classificacio_unica()

    return render_template("admin_fasefinal_classificacio.html", classificacio=classificacio)


def generar_classificacio_unica():
    """Genera classificació automàtica segons els grups."""
    grups = sorted(obtenir_grups_guardats().keys())
    classificacio = []

    for pos in range(1, 9):  # màxim 8 posicions
        candidats = []

        for g in grups:
            class_grup = calcular_classificacio(g)
            if pos <= len(class_grup):
                eq, stats = class_grup[pos - 1]
                candidats.append({
                    "equip": eq,
                    "punts": stats["punts"],
                    "dif": stats["diferencia"],
                    "pf": stats["favor"],
                    "pc": stats["contra"],
                    "pos": pos,
                    "grup": g
                })

        candidats.sort(key=lambda x: (x["punts"], x["dif"], x["pf"]), reverse=True)
        classificacio.extend(candidats)

    return classificacio


# ---------------------------------------------------------
# 💾 GUARDAR CLASSIFICACIÓ ÚNICA
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/guardar', methods=['POST'])
def guardar_classificacio_final():
    data = request.get_json()
    if not data or "ordre" not in data:
        return jsonify({"ok": False, "msg": "Dades incorrectes"})

    ordre = data["ordre"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS classificacio_final")
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

    for pos, item in enumerate(ordre, start=1):
        cur.execute("""
            INSERT INTO classificacio_final (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (pos, item["equip"], item["punts"], item["dif"], item["pos"], item["grup"]))

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "msg": "Classificació guardada correctament!"})


# ---------------------------------------------------------
# 🔄 RECALCULAR CLASSIFICACIÓ
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/recalcular', methods=['POST'])
def fase_final_recalcular():
    try:
        classificacio_unica = generar_classificacio_unica()
        if not classificacio_unica:
            return jsonify({"ok": False, "msg": "No hi ha dades per generar la classificació."}), 400

        conn = get_conn()
        cur = conn.cursor()

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
        cur.execute("DELETE FROM classificacio_final")

        for pos, item in enumerate(classificacio_unica, start=1):
            cur.execute("""
                INSERT INTO classificacio_final (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (pos, item["equip"], item["punts"], item["dif"], item["pos"], item["grup"]))

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": "Classificació regenerada correctament."})

    except Exception as e:
        print("⚠️ Error recalculant:", e)
        return jsonify({"ok": False, "msg": str(e)}), 500


# ---------------------------------------------------------
# ⚙️ CONFIGURAR FASES FINALS
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/configurar', methods=['GET', 'POST'])
def configurar_fases():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        )
    """)

    if request.method == 'POST':
        dades = request.form

        for fase, num in dades.items():
            cur.execute("""
                INSERT INTO config_fases_finals (fase, num_equips)
                VALUES (%s, %s)
                ON CONFLICT (fase)
                DO UPDATE SET num_equips = EXCLUDED.num_equips
            """, (fase, num))

        conn.commit()
        conn.close()

        from db import generar_fase_final_equips
        generar_fase_final_equips()

        return redirect(url_for('admin_fasefinal.mostrar_quadres_finals'))

    cur.execute("SELECT COUNT(*) FROM classificacio_final")
    total_equips = cur.fetchone()[0]

    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    dades = dict(cur.fetchall())

    conn.close()

    return render_template(
        "admin_config_fases.html",
        dades=dades,
        total_equips=total_equips
    )


# ---------------------------------------------------------
# 🏆 MOSTRAR QUADRES FINALS
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/quadres', methods=['GET', 'POST'])
def mostrar_quadres_finals():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    fases = dict(cur.fetchall())

    cur.execute("SELECT equip_nom, posicio FROM classificacio_final ORDER BY posicio ASC")
    tots_equips = cur.fetchall()

    conn.close()

    fase_sel = (
        request.form.get("fase")
        if request.method == "POST"
        else request.args.get("fase", "OR")
    )

    fases_ordenades = list(fases.keys())
    posicio_inici = 0
    equips_fase = []

    for fase in fases_ordenades:
        n = fases[fase]
        sublist = tots_equips[posicio_inici:posicio_inici + n]

        if fase.upper() == fase_sel.upper():
            equips_fase = sublist

        posicio_inici += n

    return render_template(
        "admin_fasefinal_quadres.html",
        fases=fases,
        fase_sel=fase_sel,
        equips=equips_fase
    )


# ---------------------------------------------------------
# ❌ ELIMINAR UN EQUIP DE LA CLASSIFICACIÓ
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/eliminar_equip', methods=['POST'])
def eliminar_equip_classificacio():
    data = request.get_json()
    equip_nom = data.get('equip')

    if not equip_nom:
        return jsonify({"ok": False, "msg": "Equip no especificat"}), 400

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT punts, dif_gol, pos_grup, grup
        FROM classificacio_final
        WHERE equip_nom = %s
    """, (equip_nom,))
    fila = cur.fetchone()

    if not fila:
        conn.close()
        return jsonify({"ok": False, "msg": "Aquest equip no existeix"}), 400

    punts, dif, pos_grup, grup = fila

    cur.execute("""
        INSERT INTO classificacio_eliminats (equip_nom, punts, dif_gol, pos_grup, grup)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (equip_nom)
        DO UPDATE SET punts = EXCLUDED.punts
    """, (equip_nom, punts, dif, pos_grup, grup))

    cur.execute("DELETE FROM classificacio_final WHERE equip_nom = %s", (equip_nom,))

    cur.execute("""
        SELECT equip_nom, punts, dif_gol, pos_grup, grup
        FROM classificacio_final
        ORDER BY posicio ASC
    """)
    restants = cur.fetchall()

    cur.execute("DELETE FROM classificacio_final")

    for nova_pos, (eq, p, d, pg, g) in enumerate(restants, start=1):
        cur.execute("""
            INSERT INTO classificacio_final (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nova_pos, eq, p, d, pg, g))

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "msg": f"L’equip '{equip_nom}' ha estat eliminat."})


# ---------------------------------------------------------
# 🔙 RECUPERAR UN EQUIP ELIMINAT
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/recuperar_equip', methods=['POST'])
def recuperar_equip():
    data = request.get_json()
    equip = data.get("equip")

    if not equip:
        return jsonify({"ok": False, "msg": "Equip no especificat"})

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT equip_nom, punts, dif_gol, pos_grup, grup
        FROM classificacio_eliminats
        WHERE equip_nom = %s
    """, (equip,))
    fila = cur.fetchone()

    if not fila:
        return jsonify({"ok": False, "msg": "Aquest equip no és a Eliminats"})

    equip_nom, punts, dif, pos_grup, grup = fila

    cur.execute("SELECT COUNT(*) FROM classificacio_final")
    nova_pos = cur.fetchone()[0] + 1

    cur.execute("""
        INSERT INTO classificacio_final (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nova_pos, equip_nom, punts, dif, pos_grup, grup))

    cur.execute("DELETE FROM classificacio_eliminats WHERE equip_nom = %s", (equip,))

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "msg": f"Equip '{equip}' recuperat correctament!"})


# ---------------------------------------------------------
# 📦 API — OBTENIR EQUIPS D'UNA FASE
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/api/equips/<fase>', methods=['GET'])
def api_equips_fase(fase):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    fases = dict(cur.fetchall())

    cur.execute("SELECT equip_nom, posicio FROM classificacio_final ORDER BY posicio ASC")
    tots_equips = cur.fetchall()

    conn.close()

    if not fases:
        return jsonify({"ok": True, "equips": []})

    fases_ordenades = list(fases.keys())
    posicio_inici = 0
    equips_fase = []

    for fase_key in fases_ordenades:
        n = fases[fase_key]
        sublist = tots_equips[posicio_inici:posicio_inici + n]

        if fase_key.upper() == fase.upper():
            equips_fase = sublist
            break

        posicio_inici += n

    equips_json = [{"pos": pos, "equip": eq} for eq, pos in equips_fase]
    return jsonify({"ok": True, "equips": equips_json})


# ---------------------------------------------------------
# 💾 Guardar bracket (JSON)
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/api/save/<fase>', methods=['POST'])
def api_save_bracket(fase):
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "msg": "No data received"}), 400

    save_dir = os.path.join(os.getcwd(), 'brackets_data')
    os.makedirs(save_dir, exist_ok=True)
    save_file = os.path.join(save_dir, f"fase_final_{fase.lower()}_data.json")

    with open(save_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "msg": "Guardat correctament"})


# ---------------------------------------------------------
# 📥 Carregar bracket
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/api/load/<fase>', methods=['GET'])
def api_load_bracket(fase):
    save_dir = os.path.join(os.getcwd(), 'brackets_data')
    save_file = os.path.join(save_dir, f"fase_final_{fase.lower()}_data.json")

    if not os.path.exists(save_file):
        return jsonify({"ok": False, "msg": "No saved state", "data": {}})

    with open(save_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return jsonify({"ok": True, "data": data})


# ---------------------------------------------------------
# 🔄 Reiniciar bracket
# ---------------------------------------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/api/reset/<fase>', methods=['POST'])
def reset_bracket(fase):
    save_dir = os.path.join(os.getcwd(), 'brackets_data')
    save_file = os.path.join(save_dir, f"fase_final_{fase.lower()}_data.json")

    if os.path.exists(save_file):
        os.remove(save_file)
        return jsonify({"ok": True, "msg": "Quadrant reiniciat correctament!"})

    return jsonify({"ok": False, "msg": "No hi havia cap quadre guardat."})
