import tkinter as tk
from tkinter import ttk, messagebox

from app.gui.session import Session
from app.services.historial_service import HistorialService
from app.services.prestatario_service import PrestatarioService


class HistorialWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Historial")
        self.geometry("1250x700")
        self.minsize(1050, 600)
        self.transient(master)

        self.prestatarios = []

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Historial de operaciones",
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Actualizar", command=self.load_data).pack(side="right")

        filters = ttk.LabelFrame(self, text="Filtros", padding=10)
        filters.pack(fill="x", padx=12, pady=(0, 10))

        self.vars = {
            "tipo": tk.StringVar(value="TODOS"),
            "prestatario": tk.StringVar(value="TODOS"),
            "recurso": tk.StringVar(),
            "estado": tk.StringVar(value="TODOS"),
            "desde": tk.StringVar(),
            "hasta": tk.StringVar(),
        }

        ttk.Label(filters, text="Tipo").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Combobox(filters, textvariable=self.vars["tipo"], state="readonly",
                     values=("TODOS", "RESERVA", "PRESTAMO", "DEVOLUCION"),
                     width=16).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(filters, text="Prestatario").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.prest_combo = ttk.Combobox(filters, textvariable=self.vars["prestatario"],
                                         state="readonly", width=34)
        self.prest_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(filters, text="Equipo/Laboratorio").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        ttk.Entry(filters, textvariable=self.vars["recurso"], width=28).grid(
            row=0, column=5, padx=5, pady=5, sticky="ew")

        ttk.Label(filters, text="Estado").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Combobox(filters, textvariable=self.vars["estado"], state="readonly",
                     values=("TODOS", "CONFIRMADA", "ACTIVA", "FINALIZADA",
                             "CANCELADA", "DEVUELTO", "ACTIVO"),
                     width=16).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(filters, text="Desde").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(filters, textvariable=self.vars["desde"], width=14).grid(
            row=1, column=3, padx=5, pady=5, sticky="w")
        ttk.Label(filters, text="Hasta").grid(row=1, column=4, padx=5, pady=5, sticky="w")
        ttk.Entry(filters, textvariable=self.vars["hasta"], width=14).grid(
            row=1, column=5, padx=5, pady=5, sticky="w")

        ttk.Button(filters, text="Aplicar filtros", command=self.load_data).grid(
            row=2, column=3, padx=5, pady=8, sticky="e")
        ttk.Button(filters, text="Limpiar filtros", command=self.clear_filters).grid(
            row=2, column=4, padx=5, pady=8, sticky="w")

        for column in range(6):
            filters.columnconfigure(column, weight=1)

        table = ttk.LabelFrame(self, text="Registro de actividad", padding=8)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        columns = ("tipo", "referencia", "fecha", "prestatario", "recurso",
                   "estado", "usuario", "observaciones")
        self.tree = ttk.Treeview(table, columns=columns, show="headings")
        headings = {
            "tipo": "Operación", "referencia": "ID", "fecha": "Fecha / hora",
            "prestatario": "Prestatario", "recurso": "Recurso",
            "estado": "Estado", "usuario": "Operador", "observaciones": "Observaciones"
        }
        widths = {
            "tipo": 105, "referencia": 55, "fecha": 145, "prestatario": 205,
            "recurso": 235, "estado": 105, "usuario": 110, "observaciones": 250
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        sy = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.pack(side="top", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        self.status_label = ttk.Label(self, text="0 operaciones")
        self.status_label.pack(anchor="w", padx=15, pady=(0, 8))

        self.load_reference_data()
        self.load_data()

    def load_reference_data(self):
        self.prestatarios = PrestatarioService.list_all()
        values = ["TODOS"] + [
            f'{r["id"]} — {r["cedula"]} — {r["nombre"]} {r["apellido"]}'
            for r in self.prestatarios
        ]
        self.prest_combo["values"] = values
        if not self.vars["prestatario"].get():
            self.prest_combo.current(0)

    def _selected_borrower_id(self):
        value = self.vars["prestatario"].get()
        if not value or value == "TODOS":
            return None
        try:
            return int(value.split(" — ", 1)[0])
        except (ValueError, IndexError) as exc:
            raise ValueError("Prestatario inválido.") from exc

    def load_data(self):
        try:
            rows = HistorialService.list_all(
                tipo=self.vars["tipo"].get(),
                prestatario_id=self._selected_borrower_id(),
                recurso=self.vars["recurso"].get(),
                estado=self.vars["estado"].get(),
                fecha_desde=self.vars["desde"].get().strip(),
                fecha_hasta=self.vars["hasta"].get().strip(),
            )
        except ValueError as exc:
            messagebox.showerror("Filtros inválidos", str(exc), parent=self)
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            recurso = f'{row["recurso_tipo"]}: {row["recurso_codigo"]} — {row["recurso_nombre"]}'
            self.tree.insert("", "end", values=(
                row["tipo"],
                row["referencia_id"],
                row["fecha_operacion"],
                row["prestatario"],
                recurso,
                row["estado"],
                row["usuario"],
                row.get("observaciones") or "",
            ))
        self.status_label.config(text=f"{len(rows)} operación(es) encontradas")

    def clear_filters(self):
        self.vars["tipo"].set("TODOS")
        self.vars["prestatario"].set("TODOS")
        self.vars["recurso"].set("")
        self.vars["estado"].set("TODOS")
        self.vars["desde"].set("")
        self.vars["hasta"].set("")
        self.load_data()
