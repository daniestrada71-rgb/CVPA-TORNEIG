        # app/routes.py

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    session,
    current_app,
    make_response,
)
from db import (
    afegir_equip,
    obtenir_equips,
    obtenir_equip,
    modificar_equip,
    eliminar_equip,
    eliminar_tots_equips,
    obtenir_grups_guardats,
    generar_partits,
    obtenir_partits,
    actualitzar_resultat,
    calcular_classificacio,
    execute,
    fetchall,
)
import pandas as pd
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO
from functools import wraps


# ----------------------------------------------------------------------
# 🔹 Decorador require_admin (control de sessió admin)
# ----------------------------------------------------------------------
def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("main.admin_login"))
        return f(*args, **kwargs)

    return wrapper


main_bp = Blueprint("main", __name__)
admin_bd_bp = Blueprint("admin_bd", __name__)


# ----------------------------------------------------------------------
# 🔹 MENÚ PRINCIPAL
# ----------------------------------------------------------------------
@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/admin")
@require_admin
def admin_menu():
    return render_template("admin_menu.html")


@main_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return redirect("/admin")
        else:
            error = "Contrasenya incorrecta"

    return render_template("admin_login.html", error=error)


@main_bp.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("main.admin_login"))


# ----------------------------------------------------------------------
# 🔹 GESTIÓ DE BASE DE DADES D’EQUIPS
# ----------------------------------------------------------------------
@admin_bd_bp.route("/admin/basedades", methods=["GET", "POST"])
def admin_base_dades():
    equips = obtenir_equips()
    equip_editant = None

    if request.method == "POST":
        # === Carregar equip per editar ===
        if "carregar" in request.form:
            try:
                equip_id = int(request.form.get("id", 0))
                equip_editant = obtenir_equip(equip_id)
            except Exception:
                equip_editant = None
            return render_template("bd.html", equips=equips, equip_editant=equip_editant)

        # === Afegir nou equip ===
        if "afegir" in request.form:
            nom_participants = request.form.get("nom_participants", "").strip()
            nom_equip = request.form.get("nom_equip", "").strip()
            try:
                valor = int(request.form.get("valor", 0))
            except ValueError:
                valor = 0
            email = request.form.get("email", "").strip()
            telefon = request.form.get("telefon", "").strip()
            afegir_equip(nom_participants, nom_equip, valor, email, telefon)
            return redirect(url_for("admin_bd.admin_base_dades"))

        # === Modificar equip existent ===
        if "modificar" in request.form:
            try:
                equip_id = int(request.form.get("id", 0))
            except ValueError:
                return redirect(url_for("admin_bd.admin_base_dades"))
            nom_participants = request.form.get("nom_participants", "").strip()
            nom_equip = request.form.get("nom_equip", "").strip()
            try:
                valor = int(request.form.get("valor", 0))
            except ValueError:
                valor = 0
            email = request.form.get("email", "").strip()
            telefon = request.form.get("telefon", "").strip()
            modificar_equip(equip_id, nom_participants, nom_equip, valor, email, telefon)
            return redirect(url_for("admin_bd.admin_base_dades"))

        # === Eliminar equip ===
        if "eliminar" in request.form:
            try:
                equip_id = int(request.form.get("id", 0))
                eliminar_equip(equip_id)
            except Exception:
                pass
            return redirect(url_for("admin_bd.admin_base_dades"))

        # === Eliminar tots els equips ===
        if "eliminar_tot" in request.form:
            eliminar_tots_equips()
            return redirect(url_for("admin_bd.admin_base_dades"))

    # GET
    return render_template("bd.html", equips=equips, equip_editant=equip_editant)


# ----------------------------------------------------------------------
# 🔹 EXPORTAR / IMPORTAR EXCEL
# ----------------------------------------------------------------------
@admin_bd_bp.route("/admin/basedades/export", methods=["GET"])
def export_excel():
    equips = obtenir_equips()
    df = pd.DataFrame(
        equips,
        columns=["id", "jugadors", "equip", "valor", "email", "telefon", "grup", "ordre"],
    )
    df = df[["jugadors", "equip", "valor", "email", "telefon"]]
    ruta = os.path.join(os.getcwd(), "export_equips.xlsx")
    df.to_excel(ruta, index=False)
    return send_file(ruta, as_attachment=True)


@admin_bd_bp.route("/admin/basedades/import", methods=["POST"])
def import_excel():
    arxiu = request.files.get("fitxer_excel")

    if not arxiu or arxiu.filename == "":
        return redirect(url_for("admin_bd.admin_base_dades"))

    df = pd.read_excel(arxiu)
    eliminar_tots_equips()

    for _, row in df.iterrows():
        afegir_equip(
            row["jugadors"],
            row["equip"],
            int(row["valor"]),
            row.get("email", ""),
            row.get("telefon", ""),
        )

    return redirect(url_for("admin_bd.admin_base_dades"))


# ----------------------------------------------------------------------
# 🔹 CONFECCIÓ DE GRUPS (amb pistes)
# ----------------------------------------------------------------------
@admin_bd_bp.route("/admin/confecciogrups", methods=["GET", "POST"])
def confeccio_grups():
    from db import obtenir_grups_guardats

    equips = obtenir_equips()
    total_equips = len(equips)
    max_grups = max(1, total_equips // 4)
    num_grups = request.form.get("num_grups", type=int, default=2)

    msg = None
    error = None
    grups = {}

    # ---------- LLEGIR PISTES GUARDADES (via db.fetchall) ---------- #
    try:
        rows = fetchall("SELECT grup, pista FROM pistes_grup")
    except Exception:
        rows = []

    pistes = {r[0]: r[1] for r in rows if r[1] is not None}
    num_pistes = max(pistes.values()) if pistes else 4

    # 🔁 SI ÉS POST, SOBREESCRIEM num_pistes AMB EL DEL FORMULARI
    if request.method == "POST":
        num_pistes_form = request.form.get("num_pistes", type=int)
        if num_pistes_form:
            num_pistes = num_pistes_form

    # ---------- GET ---------- #
    if request.method == "GET":
        guardats = obtenir_grups_guardats()
        if guardats:
            return render_template(
                "admin_confecciogrups.html",
                total_equips=total_equips,
                max_grups=max_grups,
                num_grups=len(guardats),
                grups=guardats,
                msg=None,
                error=None,
                num_pistes=num_pistes,
                pistes=pistes,
            )
        return render_template(
            "admin_confecciogrups.html",
            total_equips=total_equips,
            max_grups=max_grups,
            num_grups=num_grups,
            grups={},
            msg=None,
            error=None,
            num_pistes=num_pistes,
            pistes=pistes,
        )

    # ---------- POST ---------- #

    # Recarregar des de BD
    if "recarregar" in request.form:
        guardats = obtenir_grups_guardats()
        return render_template(
            "admin_confecciogrups.html",
            total_equips=total_equips,
            max_grups=max_grups,
            num_grups=len(guardats),
            grups=guardats,
            msg="🔄 Grups recarregats correctament",
            error=None,
            num_pistes=num_pistes,
            pistes=pistes,
        )

    # Capacitat manual per grup
    capacitat_grups = [
        request.form.get(f"grup_{i}", type=int, default=0)
        for i in range(1, num_grups + 1)
    ]
    suma = sum(capacitat_grups)

    # Capacitat suggerida
    capacitat_suggerida = []
    if num_grups > 0:
        base = total_equips // num_grups
        extra = total_equips % num_grups
        capacitat_suggerida = [
            base + (1 if i < extra else 0) for i in range(num_grups)
        ]

    # ---------- GUARDAR (sense redistribuir) ---------- #
    if "guardar" in request.form:
        ordre_json = request.form.get("ordre_json")

        # Guardar ordre dels equips
        if ordre_json:
            try:
                ordre = json.loads(ordre_json)
            except Exception:
                ordre = {}

            for grup_id, equips_ordre in ordre.items():
                for e_id, posicio in equips_ordre:
                    execute(
                        """
                        UPDATE equips SET grup=%s, ordre=%s WHERE id=%s
                    """,
                        (int(grup_id), int(posicio), int(e_id)),
                    )
        else:
            # si no arriba ordre_json, fem servir els grups guardats actuals
            grups_guardats = obtenir_grups_guardats()
            pos = 1
            for grup_id, llista in grups_guardats.items():
                for e in llista:
                    execute(
                        """
                        UPDATE equips SET grup=%s, ordre=%s WHERE id=%s
                    """,
                        (int(grup_id), pos, int(e[0])),
                    )
                    pos += 1

        # ----- GUARDAR PISTES -----
        num_pistes_form = request.form.get("num_pistes", type=int, default=num_pistes)
        num_pistes = num_pistes_form or num_pistes

        # 🔥 ESBORRAR PISTES ANTIGUES
        execute("DELETE FROM pistes_grup")

        # Tornar a inserir només les noves
        for i in range(1, num_grups + 1):
            pista_val = request.form.get(f"pista_{i}", None)
            if not pista_val:
                execute(
                    """
                    INSERT INTO pistes_grup (grup, pista) VALUES (%s, NULL)
                """,
                    (i,),
                )
            else:
                execute(
                    """
                    INSERT INTO pistes_grup (grup, pista) VALUES (%s, %s)
                """,
                    (i, int(pista_val)),
                )

        # Recarreguem grups i pistes des de BD per mostrar
        grups_guardats = obtenir_grups_guardats()

        try:
            rows = fetchall("SELECT grup, pista FROM pistes_grup")
        except Exception:
            rows = []
        pistes = {r[0]: r[1] for r in rows if r[1] is not None}

        msg = "💾 Dades guardades correctament!"
        return render_template(
            "admin_confecciogrups.html",
            total_equips=total_equips,
            max_grups=max_grups,
            num_grups=len(grups_guardats),
            grups=grups_guardats,
            msg=msg,
            error=None,
            num_pistes=num_pistes,
            pistes=pistes,
        )

    # ---------- Si no és “Guardar”, generem distribució ---------- #

    # 🔥 RESET COMPLET DEL TORNEIG QUAN ES GENEREN GRUPS NOUS
    from db import reset_competicio
    reset_competicio()

    equips_ordenats = sorted(equips, key=lambda e: e[3])
    grups = {i + 1: [] for i in range(num_grups)}


    from collections import defaultdict

    nivells = defaultdict(list)
    for e in equips_ordenats:
        nivells[e[3]].append(e)

    idx = 0
    direccio = 1

    if suma == total_equips and suma > 0:
        # Mode manual (respectant capacitats)
        for valor in sorted(nivells.keys()):
            for equip in nivells[valor]:
                assignat = False
                intents = 0
                while not assignat and intents < num_grups:
                    if capacitat_grups[idx] > 0:
                        grups[idx + 1].append(equip)
                        capacitat_grups[idx] -= 1
                        assignat = True
                    else:
                        idx += direccio
                        if idx >= num_grups:
                            direccio = -1
                            idx = num_grups - 1
                        elif idx < 0:
                            direccio = 1
                            idx = 0
                    intents += 1
                idx += direccio
                if idx >= num_grups:
                    direccio = -1
                    idx = num_grups - 1
                elif idx < 0:
                    direccio = 1
                    idx = 0
        msg = "✅ Grups generats segons capacitat manual."
    else:
        # Mode automàtic si no quadra
        capacitat_grups = capacitat_suggerida.copy()
        for equip in equips_ordenats:
            buscats = 0
            while capacitat_grups[idx] == 0 and buscats < num_grups:
                idx = (idx + direccio) % num_grups
                buscats += 1
            if capacitat_grups[idx] == 0:
                break
            grups[idx + 1].append(equip)
            capacitat_grups[idx] -= 1
            if direccio == 1:
                idx += 1
                if idx >= num_grups:
                    direccio = -1
                    idx = num_grups - 1
            else:
                idx -= 1
                if idx < 0:
                    direccio = 1
                    idx = 0
        msg = "✅ Grups generats automàticament."

    # ---------- Guardar automàtic després de generar ---------- #
    try:
        pos = 1
        for grup_id, llista in grups.items():
            for e in llista:
                execute(
                    """
                    UPDATE equips SET grup=%s, ordre=%s WHERE id=%s
                """,
                    (int(grup_id), pos, int(e[0])),
                )
                pos += 1
        msg = (msg or "") + " (💾 Generat i guardat automàticament!)"
    except Exception as e:
        print("Error desant automàticament:", e)

    # Recupera de BD per mantenir l'ordre correcte
    grups_guardats = obtenir_grups_guardats()

    # Recarreguem pistes per coherència
    try:
        rows = fetchall("SELECT grup, pista FROM pistes_grup")
    except Exception:
        rows = []
    pistes = {r[0]: r[1] for r in rows if r[1] is not None}

    return render_template(
        "admin_confecciogrups.html",
        total_equips=total_equips,
        max_grups=max_grups,
        num_grups=len(grups_guardats),
        grups=grups_guardats,
        msg=msg,
        error=None,
        num_pistes=num_pistes,
        pistes=pistes,
    )


# ----------------------------------------------------------------------
# 🔹 FASE DE GRUPS
# ----------------------------------------------------------------------
@admin_bd_bp.route("/admin/fasegrups", methods=["GET", "POST"])
def fase_grups():
    from db import (
        obtenir_grups_guardats,
        generar_partits,
        obtenir_partits,
        actualitzar_resultat,
        calcular_classificacio,
    )

    grups_guardats = obtenir_grups_guardats()
    grups_disponibles = sorted(grups_guardats.keys()) if grups_guardats else [1]
    grup_id = request.form.get("grup", type=int, default=grups_disponibles[0])

    msg = None
    error = None

    # -------------------------------------------------------------------
    # 🔥 GENERAR PARTITS DE TOTS ELS GRUPS
    # -------------------------------------------------------------------
    if "generar" in request.form:
        total = 0
        detalls = []

        for g in grups_disponibles:
            num = generar_partits(g)
            total += num
            detalls.append(f"Grup {g}: {num} partits")

        msg = f"✅ S'han generat {total} partits en total — {', '.join(detalls)}"

    # -------------------------------------------------------------------
    # 💾 GUARDAR RESULTATS DEL GRUP ACTUAL
    # -------------------------------------------------------------------
    if "guardar" in request.form:
        try:
            for p in obtenir_partits(grup_id):
                pid = p[0]

                p1 = request.form.get(f"p1_{pid}", "").strip()
                p2 = request.form.get(f"p2_{pid}", "").strip()

                if p1.isdigit() and p2.isdigit():
                    actualitzar_resultat(pid, int(p1), int(p2))

            msg = "💾 Resultats guardats correctament!"
        except Exception as e:
            error = f"❌ Error guardant resultats: {e}"

    # -------------------------------------------------------------------
    # 🔄 DESPRÉS DE GENERAR / GUARDAR / GET → CARREGAR DADES DEL GRUP
    # -------------------------------------------------------------------
    partits = obtenir_partits(grup_id)
    classificacio = calcular_classificacio(grup_id)

    # -------------------------------------------------------------------
    # 🏐 Carregar pista assignada (via db.fetchall)
    # -------------------------------------------------------------------
    try:
        rows = fetchall("SELECT pista FROM pistes_grup WHERE grup=%s", (grup_id,))
        row = rows[0] if rows else None
    except Exception:
        row = None

    pista_assignada = row[0] if row else None

    return render_template(
        "admin_fasegrups.html",
        grups=grups_disponibles,
        grup_id=grup_id,
        partits=partits,
        classificacio=classificacio,
        msg=msg,
        error=error,
        pista=pista_assignada,
    )


# ----------------------------------------------------------------------
# 🔹 PDF FASE DE GRUPS
# ----------------------------------------------------------------------
@admin_bd_bp.route("/admin/fasegrups/pdf/<int:grup_id>", methods=["GET"])
def descarregar_pdf_grup(grup_id):
    import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from io import BytesIO
    from flask import make_response

    from db import obtenir_partits

    partits = obtenir_partits(grup_id)
    if not partits:
        return "⚠️ No hi ha partits per aquest grup."

    # ------ CAPTURAR PÀGINES EN MEMÒRIA ------
    packet = BytesIO()
    pdf = canvas.Canvas(packet, pagesize=A4)
    width, height = A4

    # ------ LOCALITZAR LOGO ------
    possible_paths = [
        os.path.join(os.getcwd(), "app", "static", "logo1.png"),
        os.path.join(os.getcwd(), "app", "static", "img", "logo1.png"),
        os.path.join(os.getcwd(), "static", "logo1.png"),
        os.path.join(os.getcwd(), "static", "img", "logo1.png"),
    ]

    logo_path = next((p for p in possible_paths if os.path.exists(p)), None)

    # ------ FUNCIONS PER CAPÇALERA ------
    def draw_header(c):
        header_margin_top = 18
        display_w = 90
        if logo_path:
            try:
                img = ImageReader(logo_path)
                ow, oh = img.getSize()
                scale = display_w / ow
                display_h = oh * scale
            except Exception:
                display_h = 40
        else:
            display_h = 40

        # posició vertical del logo
        y = height - header_margin_top - display_h

        if logo_path:
            c.drawImage(
                logo_path,
                40,
                y,
                width=display_w,
                height=display_h,
                preserveAspectRatio=True,
                mask="auto",
            )

        # Títol
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(
            width / 2,
            height - header_margin_top - (display_h / 2),
            f"GRUP {grup_id}",
        )

        # Data
        c.setFont("Helvetica", 9)
        pdf.drawRightString(
            width - 40, height - 60, datetime.datetime.now().strftime("%d/%m/%Y")
        )

        # Línia separació
        c.line(40, y - 12, width - 40, y - 12)

        # marca d'aigua (opcional, baixa opacitat)
        if logo_path:
            try:
                c.saveState()
                try:
                    c.setFillAlpha(0.04)
                except Exception:
                    pass
                wm_w = 260
                wm_h = 260
                c.drawImage(
                    logo_path,
                    (width - wm_w) / 2,
                    (height - wm_h) / 2,
                    width=wm_w,
                    height=wm_h,
                    mask="auto",
                )
                c.restoreState()
            except Exception as e:
                print("⚠️ Error dibuixant marca d'aigua:", e)

        # tornem la Y inicial pels partits
        return y - 30

    # ------ DIBUIXAR CONTINGUT ------
    y = draw_header(pdf)
    pdf.setFont("Helvetica", 12)

    for idx, (pid, equip1, equip2, arbit, punts1, punts2, jugat) in enumerate(
        partits, start=1
    ):
        # si no hi ha espai, nova pàgina
        if y < 140:
            pdf.showPage()
            y = draw_header(pdf)
            pdf.setFont("Helvetica", 12)

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(60, y, f"Partit {idx}.{grup_id}")
        pdf.setFont("Helvetica", 10)
        pdf.drawRightString(width - 60, y, f"Àrbitre: {arbit}")
        y -= 18

        # --- GRAELLES ---
        cell_w, cell_h = 16, 12
        top_row = list(range(1, 14))
        bottom_row = list(range(14, 26))
        total_w = len(top_row) * cell_w
        x1 = 60
        x2 = width - (60 + total_w)

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(x1 + total_w / 2, y, equip1)
        pdf.drawCentredString(x2 + total_w / 2, y, equip2)
        y -= 22

        pdf.setFont("Helvetica", 6)
        start_y = y

        for fila, nums in enumerate([top_row, bottom_row]):
            for i, num in enumerate(nums):
                y_pos = start_y - fila * cell_h

                pdf.rect(x1 + i * cell_w, y_pos, cell_w, cell_h)
                pdf.drawCentredString(
                    x1 + i * cell_w + cell_w / 2, y_pos + 3, str(num)
                )

                pdf.rect(x2 + i * cell_w, y_pos, cell_w, cell_h)
                pdf.drawCentredString(
                    x2 + i * cell_w + cell_w / 2, y_pos + 3, str(num)
                )

        y = start_y - (2 * cell_h) - 25
        pdf.line(40, y, width - 40, y)
        y -= 20

    # -------- Finalitzar primer PDF (sense numeració) --------
    pdf.save()

    # -------- SEGONA PASSADA: AFEGIR NUMERACIÓ --------
    from PyPDF2 import PdfReader, PdfWriter

    packet.seek(0)
    reader = PdfReader(packet)
    writer = PdfWriter()

    total_pages = len(reader.pages)

    for i, page in enumerate(reader.pages):
        num_packet = BytesIO()
        num_canvas = canvas.Canvas(num_packet, pagesize=A4)

        num_canvas.setFont("Helvetica", 9)
        num_canvas.drawCentredString(
            width / 2, 25, f"Pàgina {i + 1} de {total_pages}"
        )

        num_canvas.save()
        num_packet.seek(0)

        footer_pdf = PdfReader(num_packet)
        page.merge_page(footer_pdf.pages[0])
        writer.add_page(page)

    out_buffer = BytesIO()
    writer.write(out_buffer)
    out_buffer.seek(0)

    response = make_response(out_buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=grup_{grup_id}.pdf"
    return response


