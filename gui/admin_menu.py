import tkinter as tk
from tkinter import messagebox

# Funció que es cridarà quan es premi el botó ADMIN
def open_admin():
    # Per ara no demanarem contrasenya, simplement obrim una finestra nova
    messagebox.showinfo("ADMIN", "Aquí s'obrirà el menú d'administració!")

# Crear la finestra principal
root = tk.Tk()
root.title("CVPA2x2 - Torneig Volei Platja")
root.geometry("600x500")  # Amplada x Alçada de la finestra
root.resizable(False, False)  # Evita que l'usuari redimensioni la finestra

# Afegir fons de color (opcional)
root.configure(bg="#f0f0f0")

# Títol de la portada
title_label = tk.Label(
    root,
    text="TORNEIG VOLEI PLATJA 2x2 / CVPA",
    font=("Arial", 22, "bold"),
    fg="#000000",
    bg="#f0f0f0"
)
title_label.pack(pady=50)  # Separació superior

# Espai per posar el logo
# Si tens un fitxer logo.png, es pot afegir així:
try:
    from PIL import Image, ImageTk
    logo_image = Image.open("assets/logo.png")
    logo_image = logo_image.resize((200, 200), Image.ANTIALIAS)
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = tk.Label(root, image=logo_photo, bg="#f0f0f0")
    logo_label.pack(pady=20)
except:
    logo_label = tk.Label(root, text="[LOGO]", font=("Arial", 16), bg="#f0f0f0")
    logo_label.pack(pady=20)

# Botó ADMIN granate amb text blanc
admin_button = tk.Button(
    root,
    text="ADMIN",
    bg="#800000",
    fg="white",
    font=("Arial", 16, "bold"),
    width=15,
    height=2,
    command=open_admin
)
admin_button.pack(pady=30)

# Indicació opcional a sota del botó
info_label = tk.Label(
    root,
    text="Prem ADMIN per accedir al menú de gestió del torneig",
    font=("Arial", 12),
    bg="#f0f0f0"
)
info_label.pack(pady=10)

# Inici del bucle principal de la finestra
root.mainloop()

