import tkinter as tk
from tkinter import ttk, messagebox

from app.gui.session import Session
from app.services.laboratorio_service import LaboratorioService


ESTADOS = ("DISPONIBLE", "MANTENIMIENTO", "INACTIVO")


class LaboratoriosWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Laboratorios")
        self.geometry("1050x650")
        self.minsize(900, 560)
        self.transient(master)
        self.selected_id = None

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Laboratorios", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Nuevo", command=self.new_record).pack(side="right")

        form = ttk.LabelFrame(self, text="Datos del laboratorio", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 10))

        self.vars = {k: tk.StringVar() for k in (
            "codigo", "nombre", "ubicacion", "capacidad",
            "duracion_estandar_minutos", "estado"
        )}

        fields = [
            ("Código", "codigo"), ("Nombre", "nombre"), ("Ubicación", "ubicacion"),
            ("Capacidad", "capacidad"), ("Duración estándar (min)", "duracion_estandar_minutos")
        ]
        for i, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=i * 2, padx=5, pady=5, sticky="w")
            ttk.Entry(form, textvariable=self.vars[key], width=22).grid(
                row=0, column=i * 2 + 1, padx=5, pady=5, sticky="ew"
            )

        ttk.Label(form, text="Estado").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Combobox(
            form, textvariable=self.vars["estado"], values=ESTADOS,
            state="readonly", width=20
        ).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(
            form, text="La duración estándar por defecto es 70 minutos (1 h 10 min)."
        ).grid(row=1, column=2, columnspan=5, padx=8, pady=5, sticky="w")

        ttk.Button(form, text="Guardar", command=self.save).grid(
            row=1, column=7, padx=5, pady=5
        )
        ttk.Button(form, text="Eliminar seleccionado", command=self.delete_selected).grid(
            row=1, column=8, padx=5, pady=5
        )

        for c in range(10):
            form.columnconfigure(c, weight=1)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "codigo", "nombre", "ubicacion", "capacidad", "duracion", "estado")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "id": "ID", "codigo": "Código", "nombre": "Nombre",
            "ubicacion": "Ubicación", "capacidad": "Capacidad",
            "duracion": "Duración estándar", "estado": "Estado"
        }
        widths = {
            "id": 45, "codigo": 100, "nombre": 180, "ubicacion": 180,
            "capacidad": 90, "duracion": 150, "estado": 130
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.load_data()
        self.new_record()

    def new_record(self):
        self.selected_id = None
        for var in self.vars.values():
            var.set("")
        self.vars["duracion_estandar_minutos"].set("70")
        self.vars["estado"].set("DISPONIBLE")
        self.tree.selection_remove(self.tree.selection())

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in LaboratorioService.list_all():
            self.tree.insert("", "end", values=(
                row["id"], row["codigo"], row["nombre"], row["ubicacion"],
                row["capacidad"], f'{row["duracion_estandar_minutos"]} min',
                row["estado"]
            ))

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.selected_id = int(values[0])
        row = LaboratorioService.get(self.selected_id)
        if not row:
            return
        for key in self.vars:
            self.vars[key].set(str(row[key]))
    
    def _payload(self):
        return {
            "codigo": self.vars["codigo"].get().strip(),
            "nombre": self.vars["nombre"].get().strip(),
            "ubicacion": self.vars["ubicacion"].get().strip(),
            "capacidad": self.vars["capacidad"].get().strip(),
            "duracion_estandar_minutos": self.vars["duracion_estandar_minutos"].get().strip(),
            "estado": self.vars["estado"].get()
        }

    def save(self):
        if not Session.can("laboratorios.write"):
            messagebox.showerror(
                "Permiso", "No tiene permiso para modificar laboratorios.", parent=self
            )
            return
        try:
            data = self._payload()
            if self.selected_id is None:
                LaboratorioService.create(data)
                messagebox.showinfo("Guardado", "Laboratorio registrado correctamente.", parent=self)
            else:
                LaboratorioService.update(self.selected_id, data)
                messagebox.showinfo("Actualizado", "Laboratorio actualizado correctamente.", parent=self)
            self.load_data()
            self.new_record()
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)

    def delete_selected(self):
        if not Session.can("laboratorios.delete"):
            messagebox.showerror(
                "Permiso", "No tiene permiso para eliminar laboratorios.", parent=self
            )
            return
        if self.selected_id is None:
            messagebox.showwarning("Seleccionar", "Seleccione un laboratorio.", parent=self)
            return
        if not messagebox.askyesno(
            "Confirmar", "¿Eliminar el laboratorio seleccionado?", parent=self
        ):
            return
        try:
            LaboratorioService.delete(self.selected_id)
            self.load_data()
            self.new_record()
            messagebox.showinfo("Eliminado", "Laboratorio eliminado correctamente.", parent=self)
        except ValueError as exc:
            messagebox.showerror("No se puede eliminar", str(exc), parent=self)
