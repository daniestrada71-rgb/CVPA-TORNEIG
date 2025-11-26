from flask import Blueprint, render_template, request, jsonify
import sqlite3
from db import (
    DB_FILE,
    calcular_classificacio,
    obtenir_grups_guardats,
    obtenir_fase_final_equips,    # ⬅ NECESSARI!!
    obtenir_config_fases_finals   # ⬅ NECESSARI!!
)
import os
import json
from flask import jsonify, request, send_from_directory
from .auth import require_admin

admin_fasefinal_bp = Blueprint('admin_fasefinal', __name__)

@admin_fasefinal_bp.route('/reset_classificacio_final')
def reset_classificacio_final():
    import sqlite3
    from db import DB_FILE

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Esborrem classificació final
    cur.execute("DELETE FROM classificacio_final")

    # Esborrem fase final
    cur.execute("DELETE FROM fase_final_equips")

    conn.commit()
    conn.close()

    return "Classificació final i fases finals reiniciades!"


# --- Assegurar taula d'eliminats existeix (executa a l'import)
_conn = sqlite3.connect(DB_FILE)
_cur = _conn.cursor()
_cur.execute("""
CREATE TABLE IF NOT EXISTS classificacio_eliminats (
    equip_nom TEXT PRIMARY KEY,
    punts INTEGER,
    dif_gol INTEGER,
    pos_grup INTEGER,
    grup INTEGER
)
""")
_conn.commit()
_conn.close()


# ---------------------------------------------------
# 🧮 CLASSIFICACIÓ ÚNICA (FASE FINAL)
# ---------------------------------------------------

@admin_fasefinal_bp.route('/admin/fasefinal', methods=['GET'])
@require_admin
def fase_final_classificacio():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # 🔧 Crear taula si no existeix
    cur.execute("""
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
    conn.commit()

    # Ara ja és segur fer SELECT
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
    """Genera una classificació única automàtica a partir dels grups guardats."""
    grups = sorted(obtenir_grups_guardats().keys())
    classificacio = []

    for pos in range(1, 9):  # fins al 8è classificat per grup com a màxim
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


@admin_fasefinal_bp.route('/admin/fasefinal/guardar', methods=['POST'])
def guardar_classificacio_final():
    """Guarda la classificació única després del drag & drop."""
    data = request.get_json()
    if not data or "ordre" not in data:
        return jsonify({"ok": False, "msg": "Dades incorrectes"})

    ordre = data["ordre"]

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS classificacio_final")
    cur.execute("""
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

    for pos, item in enumerate(ordre, start=1):
        cur.execute("""
            INSERT INTO classificacio_final (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pos, item["equip"], item["punts"], item["dif"], item["pos"], item["grup"]))

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "msg": "Classificació guardada correctament!"})

@admin_fasefinal_bp.route('/admin/fasefinal/recalcular', methods=['POST'])
def fase_final_recalcular():
    """Buida la classificació final i la torna a generar segons els resultats actuals."""
    try:
        
        import sqlite3

        # Generem la nova classificació
        classificacio_unica = generar_classificacio_unica()
        if not classificacio_unica:
            return jsonify({"ok": False, "msg": "No hi ha dades per generar la classificació."}), 400

        # Connectem a la base de dades
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        # Esborrem la taula i la tornem a crear si cal
        cur.execute("""
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
        cur.execute("DELETE FROM classificacio_final")

        # Inserim la nova classificació
        for pos, item in enumerate(classificacio_unica, start=1):
            cur.execute("""
                INSERT INTO classificacio_final (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pos, item["equip"], item["punts"], item["dif"], item["pos"], item["grup"]))


        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": "Classificació regenerada correctament."}), 200

    except Exception as e:
        print("⚠️ Error en recalcular:", e)
        return jsonify({"ok": False, "msg": str(e)}), 500

@admin_fasefinal_bp.route('/admin/fasefinal/configurar', methods=['GET', 'POST'])
def configurar_fases():
    """Permet definir quants equips van a cada fase (Or, Plata, Bronze, Xou)."""

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Assegurem que existeixi la taula
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_fases_finals (
            fase TEXT PRIMARY KEY,
            num_equips INTEGER
        )
    """)

    # ============================
    # 🔹 POST → Guardar i passar a quadres
    # ============================
    if request.method == 'POST':
        dades = request.form

        for fase, num in dades.items():
            cur.execute("""
                INSERT INTO config_fases_finals (fase, num_equips)
                VALUES (?, ?)
                ON CONFLICT(fase) DO UPDATE SET num_equips=excluded.num_equips
            """, (fase, num))

        conn.commit()
        conn.close()

        # Generem equips per fase
        from db import generar_fase_final_equips
        generar_fase_final_equips()

        # REDIRIGIM a quadres
        from flask import redirect, url_for
        return redirect(url_for('admin_fasefinal.mostrar_quadres_finals'))

    # ============================
    # 🔹 GET → Mostrar pàgina de configuració
    # ============================

    # Comprovar si hi ha classificació
    cur.execute("SELECT COUNT(*) FROM classificacio_final")
    total_equips = cur.fetchone()[0] or 0

    # Carregar dades actuals
    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    dades = dict(cur.fetchall())

    conn.close()

    return render_template(
        "admin_config_fases.html",
        dades=dades,
        total_equips=total_equips
    )

@admin_fasefinal_bp.route('/admin/fasefinal/quadres', methods=['GET', 'POST'])
def mostrar_quadres_finals():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Carreguem configuració de fases
    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    fases = dict(cur.fetchall())

    # Llista completa de classificació
    cur.execute("SELECT equip_nom, posicio FROM classificacio_final ORDER BY posicio ASC")
    tots_equips = cur.fetchall()
    conn.close()

    # 🟢 NOVA LÒGICA
    if request.method == "POST":
        fase_sel = request.form.get("fase", "OR")
    else:
        fase_sel = request.args.get("fase", "OR")  # <-- ACCEPTAR GET

    # Calcular equips de cada fase
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

@admin_fasefinal_bp.route('/admin/fasefinal/eliminar_equip', methods=['POST'])
def eliminar_equip_classificacio():
    """Mou un equip a la taula d'eliminats i recalcula la classificació."""
    data = request.get_json()
    equip_nom = data.get('equip')

    if not equip_nom:
        return jsonify({"ok": False, "msg": "Equip no especificat"}), 400

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        # Assegurem que la taula d'eliminats existeixi (defensiu)
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

        # Agafem les dades actuals de l'equip
        cur.execute("""
            SELECT punts, dif_gol, pos_grup, grup
            FROM classificacio_final
            WHERE equip_nom = ?
        """, (equip_nom,))
        fila = cur.fetchone()

        if not fila:
            conn.close()
            return jsonify({"ok": False, "msg": "No trobat a la classificació"}), 400

        punts, dif, pos_grup, grup = fila

        # Guardem a la taula d'eliminats
        cur.execute("""
            INSERT OR REPLACE INTO classificacio_eliminats
            (equip_nom, punts, dif_gol, pos_grup, grup)
            VALUES (?, ?, ?, ?, ?)
        """, (equip_nom, punts, dif, pos_grup, grup))

        # Eliminem de la classificació final
        cur.execute("DELETE FROM classificacio_final WHERE equip_nom = ?", (equip_nom,))

        # Recuperem resta i reassignem posicions
        cur.execute("""
            SELECT equip_nom, punts, dif_gol, pos_grup, grup
            FROM classificacio_final
            ORDER BY posicio ASC
        """)
        restants = cur.fetchall()

        cur.execute("DELETE FROM classificacio_final")

        for nova_pos, (eq, p, d, pg, g) in enumerate(restants, start=1):
            cur.execute("""
                INSERT INTO classificacio_final
                (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nova_pos, eq, p, d, pg, g))

        conn.commit()
        conn.close()

        return jsonify({"ok": True, "msg": f"L’equip '{equip_nom}' ha estat eliminat correctament i guardat a Eliminats."})

    except Exception as e:
        # imprimeix al log del servidor per debugging
        print("⚠️ Error eliminant equip:", repr(e))
        try:
            conn.close()
        except:
            pass
        return jsonify({"ok": False, "msg": "Error intern: " + str(e)}), 500

@admin_fasefinal_bp.route('/admin/fasefinal/generar/<fase>')
def generar_quadre_fase(fase):
    """Redirigeix directament al quadre HTML (nova versió web)."""
    from flask import redirect, url_for
    return redirect(url_for('admin_fasefinal.visualitzar_quadre_fase', fase=fase.upper()))

    def run_window():
        # ✔ Root no visible, no parpelleig
        root = tk.Tk()
        root.overrideredirect(True)    # Amaga el marc
        root.geometry("0x0+9999+9999") # Amaga completament
        root.withdraw()

        # --- Finestra elegant ---
        elegant = tk.Toplevel(root)
        elegant.title(f"🏆 Quadre Fase {fase.upper()}")
        elegant.configure(bg="#f0f0f0")

        # ✔ Efecte d'aparició elegant
        elegant.attributes("-alpha", 0.0)
        elegant.update_idletasks()

        # ✓ Centrar finestra abans de mostrar-la
        w, h = 1300, 900
        sw = elegant.winfo_screenwidth()
        sh = elegant.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2

        elegant.geometry(f"{w}x{h}+{x}+{y}")

        # Animació d'aparició suau
        for i in range(1, 11):
            elegant.after(i * 15, lambda a=i: elegant.attributes("-alpha", a / 10.0))

        # Carreguem el quadre dins la finestra elegant
        open_quadrefase(elegant, fase.upper(), mode="admin")

        root.mainloop()

    # Obrim en un fil separat, sense bloquear Flask
    threading.Thread(target=run_window).start()

    return jsonify({"ok": True})

@admin_fasefinal_bp.route('/admin/fasefinal/eliminats', methods=['GET'])
def llistar_eliminats():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT equip_nom FROM classificacio_eliminats ORDER BY equip_nom ASC")
    equips = [{"equip": e[0]} for e in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "equips": equips})

@admin_fasefinal_bp.route('/admin/fasefinal/recuperar_equip', methods=['POST'])
def recuperar_equip():
    data = request.get_json()
    equip = data.get("equip")

    if not equip:
        return jsonify({"ok": False, "msg": "Equip no especificat"})

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Obtenim des d’eliminats
    cur.execute("""
        SELECT equip_nom, punts, dif_gol, pos_grup, grup
        FROM classificacio_eliminats
        WHERE equip_nom = ?
    """, (equip,))
    fila = cur.fetchone()

    if not fila:
        return jsonify({"ok": False, "msg": "Aquest equip no és a Eliminats"})

    equip_nom, punts, dif, pos_grup, grup = fila

    # Calcular nova posició
    cur.execute("SELECT COUNT(*) FROM classificacio_final")
    nova_pos = cur.fetchone()[0] + 1

    # Insertar-lo al final
    cur.execute("""
        INSERT INTO classificacio_final
        (posicio, equip_nom, punts, dif_gol, pos_grup, grup)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nova_pos, equip_nom, punts, dif, pos_grup, grup))

    # Esborrar d’eliminats
    cur.execute("DELETE FROM classificacio_eliminats WHERE equip_nom = ?", (equip,))

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "msg": f"Equip '{equip}' recuperat correctament!"})


# ---------------------------
# Visualitzar bracket en web
# ---------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/visualitzar/<fase>', methods=['GET'])
def visualitzar_quadre_fase(fase):
    """Renderitza la pàgina del quadre final (HTML) per la fase indicada."""
    return render_template('admin_fasefinal_bracket.html', fase=fase.upper())

@admin_fasefinal_bp.route('/admin/fasefinal/api/equips/<fase>', methods=['GET'])
def api_equips_fase(fase):
    """Retorna JSON amb els equips assignats a la fase (posició i nom)."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Agafem la configuració de fases guardada
    cur.execute("SELECT fase, num_equips FROM config_fases_finals")
    fases = dict(cur.fetchall())

    # Recollim la classificació global ordenada
    cur.execute("SELECT equip_nom, posicio FROM classificacio_final ORDER BY posicio ASC")
    tots_equips = cur.fetchall()
    conn.close()

    # si la config no existeix, retornem buit
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

    # format JSON
    equips_json = [{"pos": pos, "equip": eq} for eq, pos in equips_fase]
    return jsonify({"ok": True, "equips": equips_json})

# ---------------------------
# Guardar estat del bracket (JSON)
# ---------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/api/save/<fase>', methods=['POST'])
def api_save_bracket(fase):
    """Rep un JSON amb l'estat dels partits i el desa en un fitxer."""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "msg": "No data received"}), 400

    save_dir = os.path.join(os.getcwd(), 'brackets_data')
    os.makedirs(save_dir, exist_ok=True)
    save_file = os.path.join(save_dir, f"fase_final_{fase.lower()}_data.json")

    try:
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True, "msg": "Guardat correctament"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

# ---------------------------
# Carregar estat del bracket (JSON)
# ---------------------------
@admin_fasefinal_bp.route('/admin/fasefinal/api/load/<fase>', methods=['GET'])
def api_load_bracket(fase):
    save_dir = os.path.join(os.getcwd(), 'brackets_data')
    save_file = os.path.join(save_dir, f"fase_final_{fase.lower()}_data.json")
    if not os.path.exists(save_file):
        return jsonify({"ok": False, "msg": "No saved state", "data": {}})

    try:
        with open(save_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500




