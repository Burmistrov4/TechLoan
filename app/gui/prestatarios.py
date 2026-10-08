import tkinter as tk
from tkinter import ttk, messagebox
from app.gui.session import Session
from app.services.prestatario_service import PrestatarioService

TIPOS = ("ESTUDIANTE", "PROFESOR", "EMPLEADO", "OTRO")
ESTADOS = ("ACTIVO", "INACTIVO")


class PrestatariosWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Prestatarios")
        self.geometry("1050x620")
        self.minsize(900, 520)
        self.transient(master)
        self.selected_id = None

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Prestatarios", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Nuevo", command=self.new_record).pack(side="right")
        ttk.Button(top, text="Actualizar lista", command=self.load_data).pack(side="right", padx=8)

        form = ttk.LabelFrame(self, text="Datos del prestatario", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 10))

        self.vars = {k: tk.StringVar() for k in
                     ("cedula", "nombre", "apellido", "tipo", "telefono", "email", "estado")}
        fields = [
            ("Cédula", "cedula"), ("Nombre", "nombre"), ("Apellido", "apellido"),
            ("Teléfono", "telefono"), ("Correo", "email")
        ]
        for i, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=i * 2, padx=5, pady=5, sticky="w")
            ttk.Entry(form, textvariable=self.vars[key], width=22).grid(
                row=0, column=i * 2 + 1, padx=5, pady=5, sticky="ew"
            )

        ttk.Label(form, text="Tipo").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Combobox(form, textvariable=self.vars["tipo"], values=TIPOS,
                     state="readonly", width=19).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form, text="Estado").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Combobox(form, textvariable=self.vars["estado"], values=ESTADOS,
                     state="readonly", width=19).grid(row=1, column=3, padx=5, pady=5)
        ttk.Button(form, text="Guardar", command=self.save).grid(row=1, column=8, padx=5, pady=5)
        ttk.Button(form, text="Eliminar seleccionado", command=self.delete_selected).grid(
            row=1, column=9, padx=5, pady=5
        )
        for c in range(10):
            form.columnconfigure(c, weight=1)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)
        columns = ("id", "cedula", "nombre", "apellido", "tipo", "telefono", "email", "estado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "id": "ID", "cedula": "Cédula", "nombre": "Nombre", "apellido": "Apellido",
            "tipo": "Tipo", "telefono": "Teléfono", "email": "Correo", "estado": "Estado"
        }
        widths = {"id": 45, "cedula": 100, "nombre": 120, "apellido": 120,
                  "tipo": 105, "telefono": 105, "email": 190, "estado": 90}
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
        self.vars["tipo"].set("ESTUDIANTE")
        self.vars["estado"].set("ACTIVO")
        self.tree.selection_remove(self.tree.selection())

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in PrestatarioService.list_all():
            values = tuple(row.get(col) or "" for col in self.tree["columns"])
            self.tree.insert("", "end", values=values)

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.selected_id = int(values[0])
        for key, value in zip(self.tree["columns"][1:], values[1:]):
            if key in self.vars:
                self.vars[key].set(value)

    def _payload(self):
        return {key: var.get().strip() for key, var in self.vars.items()}

    def save(self):
        if not Session.can("prestatarios.write"):
            messagebox.showerror("Permiso", "No tiene permiso para modificar prestatarios.", parent=self)
            return
        try:
            data = self._payload()
            if self.selected_id is None:
                PrestatarioService.create(data)
                messagebox.showinfo("Guardado", "Prestatario registrado correctamente.", parent=self)
            else:
                PrestatarioService.update(self.selected_id, data)
                messagebox.showinfo("Actualizado", "Prestatario actualizado correctamente.", parent=self)
            self.load_data()
            self.new_record()
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)

    def delete_selected(self):
        if not Session.can("prestatarios.delete"):
            messagebox.showerror("Permiso", "No tiene permiso para eliminar prestatarios.", parent=self)
            return
        if self.selected_id is None:
            messagebox.showwarning("Seleccionar", "Seleccione un prestatario.", parent=self)
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar el prestatario seleccionado?", parent=self):
            return
        try:
            PrestatarioService.delete(self.selected_id)
            self.load_data()
            self.new_record()
            messagebox.showinfo("Eliminado", "Prestatario eliminado correctamente.", parent=self)
        except ValueError as exc:
            messagebox.showerror("No se puede eliminar", str(exc), parent=self)
