def open_confeccio_grups():
    grups_window = tk.Toplevel(root)
    grups_window.title("Confecció de grups")
    grups_window.geometry("900x600")

    # Obtenir equips de la DB
    equips = obtenir_equips()
    total_equips = len(equips)

    # Mostrar quants equips hi ha
    info_label = tk.Label(
        grups_window,
        text=f"Equips registrats: {total_equips}",
        font=("Arial", 14, "bold")
    )
    info_label.pack(pady=10)

    # Formulari per definir nombre de grups i equips per grup
    form_frame = tk.Frame(grups_window)
    form_frame.pack(pady=10)

    tk.Label(form_frame, text="Nombre de grups:").grid(row=0, column=0, padx=5, pady=5)
    entry_num_grups = tk.Entry(form_frame, width=5)
    entry_num_grups.grid(row=0, column=1, padx=5)

    tk.Label(form_frame, text="Equips per grup:").grid(row=0, column=2, padx=5, pady=5)
    entry_equips_grup = tk.Entry(form_frame, width=5)
    entry_equips_grup.grid(row=0, column=3, padx=5)

    grups_frame = tk.Frame(grups_window)
    grups_frame.pack(fill="both", expand=True, padx=10, pady=10)

    grups_widgets = []

    def generar_grups():
        for widget in grups_frame.winfo_children():
            widget.destroy()
        grups_widgets.clear()

        try:
            num_grups = int(entry_num_grups.get())
            equips_per_grup = int(entry_equips_grup.get())

            if num_grups * equips_per_grup != total_equips:
                messagebox.showwarning(
                    "Atenció",
                    "El nombre total d’equips no coincideix amb grups x equips per grup"
                )
                return

            # Ordenar equips per valor
            equips_sorted = sorted(equips, key=lambda x: x[3])  # columna valor

            # Distribució equilibrada
            grups = [[] for _ in range(num_grups)]
            for i, equip in enumerate(equips_sorted):
                grups[i % num_grups].append(equip)

            # Mostrar grups en taules
            for idx, grup in enumerate(grups, start=1):
                frame = tk.LabelFrame(grups_frame, text=f"Grup {idx}", padx=10, pady=10)
                frame.pack(side="left", fill="y", expand=True, padx=5)

                cols = ("ID", "Nom equip", "Valor")
                tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
                for col in cols:
                    tree.heading(col, text=col)
                    tree.column(col, width=100)
                tree.pack()

                for eq in grup:
                    tree.insert("", "end", values=(eq[0], eq[2], eq[3]))  # ID, Nom, Valor

                grups_widgets.append(tree)

        except ValueError:
            messagebox.showerror("Error", "Introdueix números vàlids")

    # Botó per generar grups
    tk.Button(
        grups_window,
        text="Generar grups automàticament",
        bg="#800000",
        fg="white",
        font=("Arial", 12, "bold"),
        command=generar_grups
    ).pack(pady=10)

    # Espai per botons de modificació manual
    mod_frame = tk.Frame(grups_window)
    mod_frame.pack(fill="x", pady=10)

    def moure_equip():
        if len(grups_widgets) < 2:
            messagebox.showwarning("Atenció", "Primer genera els grups!")
            return

        # Comprovar selecció
        origen = None
        sel_item = None
        for tree in grups_widgets:
            sel = tree.selection()
            if sel:
                origen = tree
                sel_item = sel[0]
                break

        if not origen:
            messagebox.showwarning("Atenció", "Selecciona un equip per moure!")
            return

        equip_data = origen.item(sel_item)["values"]

        # Diàleg per escollir a quin grup moure
        dest_idx = tk.simpledialog.askinteger("Moure", f"A quin grup vols moure l’equip {equip_data[1]}?")
        if not dest_idx or dest_idx < 1 or dest_idx > len(grups_widgets):
            return

        dest_tree = grups_widgets[dest_idx - 1]

        # Afegir al nou grup
        dest_tree.insert("", "end", values=equip_data)

        # Eliminar del grup original
        origen.delete(sel_item)

    tk.Button(mod_frame, text="Moure equip seleccionat", command=moure_equip).pack(side="left", padx=10)
