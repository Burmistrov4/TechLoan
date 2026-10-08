import tkinter as tk
from tkinter import messagebox
from app.gui.session import Session
from app.gui.prestatarios import PrestatariosWindow
from app.gui.equipos import EquiposWindow
from app.gui.laboratorios import LaboratoriosWindow
from app.gui.categorias import CategoriasWindow
from app.gui.reservas import ReservasWindow
from app.gui.prestamos import PrestamosWindow
from app.gui.historial import HistorialWindow


class DashboardWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Dashboard")
        self.geometry("900x600")
        self.minsize(800, 500)
        self.protocol("WM_DELETE_WINDOW", self._logout)

        user = Session.current_user
        header = tk.Frame(self, padx=20, pady=15)
        header.pack(fill="x")
        tk.Label(header, text="TECHLOAN", font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(header, text=f"{user['nombre']} {user['apellido']} · {user['rol']}").pack(side="right")

        body = tk.Frame(self, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        modules = [
            ("Prestatarios", "prestatarios.read", self.open_prestatarios),
            ("Equipos", "equipos.read", self.open_equipos),
            ("Laboratorios", "laboratorios.read", self.open_laboratorios),
            ("Categorías", "categorias.read", self.open_categorias),
            ("Reservas", "reservas.read", self.open_reservas),
            ("Préstamos", "prestamos.read", self.open_prestamos),
            ("Devoluciones", "prestamos.return", self.open_prestamos),
            ("Historial", "historial.read", self.open_historial),
            ("Usuarios", "usuarios.read", self.not_ready),
        ]
        for index, (name, permission, command) in enumerate(modules):
            if Session.can(permission):
                tk.Button(
                    body, text=name, width=22, height=3,
                    command=command
                ).grid(row=index // 3, column=index % 3, padx=10, pady=10, sticky="nsew")

        for c in range(3):
            body.grid_columnconfigure(c, weight=1)
        for r in range(3):
            body.grid_rowconfigure(r, weight=1)

    def open_prestatarios(self):
        PrestatariosWindow(self)

    def open_equipos(self):
        EquiposWindow(self)

    def open_laboratorios(self):
        LaboratoriosWindow(self)

    def open_categorias(self):
        CategoriasWindow(self)

    def open_reservas(self):
        ReservasWindow(self)

    def open_prestamos(self):
        PrestamosWindow(self)

    def open_historial(self):
        HistorialWindow(self)

    def not_ready(self):
        messagebox.showinfo(
            "Módulo",
            "Este módulo se implementará en la siguiente etapa de la Fase 4.",
            parent=self
        )

    def _logout(self):
        Session.end()
        self.destroy()
