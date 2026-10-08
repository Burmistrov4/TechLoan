import tkinter as tk
from tkinter import ttk, messagebox

from app.gui.session import Session
from app.services.prestamo_equipo_service import PrestamoEquipoService
from app.services.equipo_service import EquipoService
from app.services.prestatario_service import PrestatarioService


class PrestamosWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Préstamos y Devoluciones")
        self.geometry("1120x680")
        self.minsize(980, 580)
        self.transient(master)

        self.equipos = []
        self.prestatarios = []
        self.selected_loan_id = None

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Préstamos y devoluciones",
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Actualizar", command=self.load_data).pack(side="right")

        form = ttk.LabelFrame(self, text="Registrar préstamo", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 10))

        self.vars = {key: tk.StringVar() for key in
                     ("equipo", "prestatario", "observaciones")}

        ttk.Label(form, text="Equipo disponible").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")
        self.equipo_combo = ttk.Combobox(
            form, textvariable=self.vars["equipo"],
            state="readonly", width=45)
        self.equipo_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(form, text="Prestatario").grid(
            row=0, column=2, padx=5, pady=5, sticky="w")
        self.prest_combo = ttk.Combobox(
            form, textvariable=self.vars["prestatario"],
            state="readonly", width=42)
        self.prest_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(form, text="Observaciones").grid(
            row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(form, textvariable=self.vars["observaciones"], width=90).grid(
            row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        ttk.Button(form, text="Registrar préstamo",
                   command=self.create_loan).grid(
            row=2, column=1, padx=5, pady=8, sticky="w")
        ttk.Button(form, text="Limpiar",
                   command=self.clear_form).grid(
            row=2, column=3, padx=5, pady=8, sticky="e")

        for column in range(4):
            form.columnconfigure(column, weight=1)

        table = ttk.LabelFrame(self, text="Historial de préstamos", padding=8)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        columns = ("id", "equipo", "prestatario", "fecha", "estado", "devolucion", "observaciones")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", selectmode="browse")
        headings = {
            "id": "ID", "equipo": "Equipo", "prestatario": "Prestatario",
            "fecha": "Fecha préstamo", "estado": "Estado",
            "devolucion": "Fecha devolución", "observaciones": "Observaciones"
        }
        widths = {
            "id": 45, "equipo": 190, "prestatario": 220,
            "fecha": 145, "estado": 90, "devolucion": 145, "observaciones": 230
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
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        actions = ttk.Frame(self, padding=(12, 0, 12, 12))
        actions.pack(fill="x")
        ttk.Button(actions, text="Devolver equipo seleccionado",
                   command=self.return_selected).pack(side="right")

        self.load_reference_data()
        self.load_data()

    def load_reference_data(self):
        self.equipos = EquipoService.list_all()
        equipment_values = [
            f'{r["id"]} — {r["codigo"]} — {r["nombre"]}'
            for r in self.equipos if r["estado"] == "DISPONIBLE"
        ]
        self.equipo_combo["values"] = equipment_values

        self.prestatarios = PrestatarioService.list_all()
        borrower_values = [
            f'{r["id"]} — {r["cedula"]} — {r["nombre"]} {r["apellido"]}'
            for r in self.prestatarios if r.get("estado", "ACTIVO") == "ACTIVO"
        ]
        self.prest_combo["values"] = borrower_values

        if equipment_values and not self.vars["equipo"].get():
            self.equipo_combo.current(0)
        if borrower_values and not self.vars["prestatario"].get():
            self.prest_combo.current(0)

    def _selected_id(self, value):
        try:
            return int(value.split(" — ", 1)[0])
        except (ValueError, IndexError):
            raise ValueError("Seleccione un equipo y un prestatario válidos.")

    def create_loan(self):
        if not Session.can("prestamos.write"):
            messagebox.showerror("Permiso",
                                 "No tiene permiso para registrar préstamos.",
                                 parent=self)
            return
        if not self.vars["equipo"].get() or not self.vars["prestatario"].get():
            messagebox.showwarning("Datos incompletos",
                                   "Seleccione el equipo y el prestatario.",
                                   parent=self)
            return
        try:
            equipment_id = self._selected_id(self.vars["equipo"].get())
            borrower_id = self._selected_id(self.vars["prestatario"].get())
            user_id = int(Session.current_user["id"])
            loan_id = PrestamoEquipoService.create(
                equipment_id, borrower_id, user_id,
                self.vars["observaciones"].get().strip()
            )
            messagebox.showinfo(
                "Préstamo registrado",
                f"Préstamo #{loan_id} registrado. El equipo pasó a estado PRESTADO.",
                parent=self
            )
            self.clear_form()
            self.load_reference_data()
            self.load_data()
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("No se puede registrar", str(exc), parent=self)

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            self.selected_loan_id = None
            return
        values = self.tree.item(selection[0], "values")
        self.selected_loan_id = int(values[0])

    def return_selected(self):
        if not Session.can("prestamos.return"):
            messagebox.showerror("Permiso",
                                 "No tiene permiso para registrar devoluciones.",
                                 parent=self)
            return
        if self.selected_loan_id is None:
            messagebox.showwarning("Seleccionar",
                                   "Seleccione un préstamo de la tabla.",
                                   parent=self)
            return

        loan = next(
            (r for r in PrestamoEquipoService.list_all()
             if r["id"] == self.selected_loan_id), None
        )
        if not loan:
            messagebox.showerror("Préstamo", "El préstamo ya no existe.", parent=self)
            return
        if loan["estado"] != "ACTIVO":
            messagebox.showwarning("Préstamo finalizado",
                                   "Este préstamo ya fue devuelto.",
                                   parent=self)
            return

        equipment = f'{loan["equipo_codigo"]}'
        borrower = f'{loan["prestatario_nombre"]} {loan["prestatario_apellido"]}'
        if not messagebox.askyesno(
            "Confirmar devolución",
            f"¿Registrar la devolución del equipo {equipment}?\nPrestatario: {borrower}",
            parent=self
        ):
            return

        try:
            PrestamoEquipoService.return_equipment(self.selected_loan_id)
            messagebox.showinfo(
                "Devolución registrada",
                "El equipo fue devuelto correctamente y volvió a DISPONIBLE.",
                parent=self
            )
            self.selected_loan_id = None
            self.load_reference_data()
            self.load_data()
        except ValueError as exc:
            messagebox.showerror("No se puede devolver", str(exc), parent=self)

    def clear_form(self):
        self.vars["equipo"].set("")
        self.vars["prestatario"].set("")
        self.vars["observaciones"].set("")
        self.selected_loan_id = None
        if hasattr(self, "tree"):
            self.tree.selection_remove(self.tree.selection())

    def load_data(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in PrestamoEquipoService.list_all():
            self.tree.insert("", "end", values=(
                row["id"],
                f'{row["equipo_codigo"]}',
                f'{row["prestatario_nombre"]} {row["prestatario_apellido"]}',
                row["fecha_prestamo"],
                row["estado"],
                row.get("fecha_devolucion") or "",
                row.get("observaciones") or ""
            ))
