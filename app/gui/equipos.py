import tkinter as tk
from tkinter import ttk, messagebox
from app.gui.session import Session
from app.services.equipo_service import EquipoService
from app.services.categoria_service import CategoriaService
from app.services.laboratorio_service import LaboratorioService

ESTADOS = ("DISPONIBLE", "PRESTADO", "MANTENIMIENTO", "DANADO", "INACTIVO")


class EquiposWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Equipos")
        self.geometry("1180x680")
        self.minsize(1000, 560)
        self.transient(master)
        self.selected_id = None
        self.category_map = {}
        self.lab_map = {}

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Equipos", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Nuevo", command=self.new_record).pack(side="right")
        ttk.Button(top, text="Actualizar datos", command=self.load_reference_data).pack(side="right", padx=8)

        form = ttk.LabelFrame(self, text="Datos del equipo", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 10))

        self.vars = {k: tk.StringVar() for k in
                     ("codigo", "nombre", "categoria", "marca", "modelo", "serial", "laboratorio", "estado")}

        fields = [("Código", "codigo"), ("Nombre", "nombre"), ("Marca", "marca"),
                  ("Modelo", "modelo"), ("Serial", "serial")]
        for i, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=i * 2, padx=5, pady=5, sticky="w")
            ttk.Entry(form, textvariable=self.vars[key], width=20).grid(
                row=0, column=i * 2 + 1, padx=5, pady=5, sticky="ew"
            )

        ttk.Label(form, text="Categoría").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.category_combo = ttk.Combobox(form, textvariable=self.vars["categoria"], state="readonly", width=25)
        self.category_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form, text="Laboratorio").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.lab_combo = ttk.Combobox(form, textvariable=self.vars["laboratorio"], state="readonly", width=25)
        self.lab_combo.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(form, text="Estado").grid(row=1, column=4, padx=5, pady=5, sticky="w")
        ttk.Combobox(form, textvariable=self.vars["estado"], values=ESTADOS,
                     state="readonly", width=20).grid(row=1, column=5, padx=5, pady=5)

        ttk.Button(form, text="Guardar", command=self.save).grid(row=1, column=8, padx=5, pady=5)
        ttk.Button(form, text="Eliminar seleccionado", command=self.delete_selected).grid(
            row=1, column=9, padx=5, pady=5
        )
        for c in range(10):
            form.columnconfigure(c, weight=1)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)
        columns = ("id", "codigo", "nombre", "categoria", "marca", "modelo", "serial", "laboratorio", "estado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "id": "ID", "codigo": "Código", "nombre": "Nombre", "categoria": "Categoría",
            "marca": "Marca", "modelo": "Modelo", "serial": "Serial",
            "laboratorio": "Laboratorio", "estado": "Estado"
        }
        widths = {"id": 45, "codigo": 90, "nombre": 150, "categoria": 120, "marca": 100,
                  "modelo": 100, "serial": 120, "laboratorio": 130, "estado": 115}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.load_reference_data()
        self.new_record()

    def load_reference_data(self):
        categories = CategoriaService.list_all()
        labs = LaboratorioService.list_all()
        self.category_map = {f"{r['id']} — {r['nombre']}": r["id"] for r in categories}
        self.lab_map = {f"{r['id']} — {r['codigo']} — {r['nombre']}": r["id"] for r in labs}
        self.category_combo["values"] = list(self.category_map)
        self.lab_combo["values"] = list(self.lab_map)
        self.load_data()

    def new_record(self):
        self.selected_id = None
        for var in self.vars.values():
            var.set("")
        self.vars["estado"].set("DISPONIBLE")
        self.tree.selection_remove(self.tree.selection())

    def load_data(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in EquipoService.list_all():
            self.tree.insert("", "end", values=(
                row["id"], row["codigo"], row["nombre"],
                row.get("categoria_nombre") or "Sin categoría",
                row.get("marca") or "", row.get("modelo") or "",
                row.get("serial") or "",
                row.get("laboratorio_nombre") or "Sin laboratorio",
                row["estado"]
            ))

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.selected_id = int(values[0])
        row = EquipoService.get(self.selected_id)
        if not row:
            return
        self.vars["codigo"].set(row["codigo"])
        self.vars["nombre"].set(row["nombre"])
        self.vars["marca"].set(row.get("marca") or "")
        self.vars["modelo"].set(row.get("modelo") or "")
        self.vars["serial"].set(row.get("serial") or "")
        self.vars["estado"].set(row["estado"])
        self.vars["categoria"].set(self._display_for_id(self.category_map, row.get("categoria_id")))
        self.vars["laboratorio"].set(self._display_for_id(self.lab_map, row.get("laboratorio_id")))

    @staticmethod
    def _display_for_id(mapping, value):
        for label, item_id in mapping.items():
            if item_id == value:
                return label
        return ""

    def _payload(self):
        category_id = self.category_map.get(self.vars["categoria"].get())
        lab_id = self.lab_map.get(self.vars["laboratorio"].get())
        return {
            "codigo": self.vars["codigo"].get().strip(),
            "nombre": self.vars["nombre"].get().strip(),
            "categoria_id": category_id,
            "marca": self.vars["marca"].get().strip(),
            "modelo": self.vars["modelo"].get().strip(),
            "serial": self.vars["serial"].get().strip(),
            "laboratorio_id": lab_id,
            "estado": self.vars["estado"].get()
        }

    def save(self):
        if not Session.can("equipos.write"):
            messagebox.showerror("Permiso", "No tiene permiso para modificar equipos.", parent=self)
            return
        try:
            data = self._payload()
            if self.selected_id is None:
                EquipoService.create(data)
                messagebox.showinfo("Guardado", "Equipo registrado correctamente.", parent=self)
            else:
                EquipoService.update(self.selected_id, data)
                messagebox.showinfo("Actualizado", "Equipo actualizado correctamente.", parent=self)
            self.load_data()
            self.new_record()
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)

    def delete_selected(self):
        if not Session.can("equipos.delete"):
            messagebox.showerror("Permiso", "No tiene permiso para eliminar equipos.", parent=self)
            return
        if self.selected_id is None:
            messagebox.showwarning("Seleccionar", "Seleccione un equipo.", parent=self)
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar el equipo seleccionado?", parent=self):
            return
        try:
            EquipoService.delete(self.selected_id)
            self.load_data()
            self.new_record()
            messagebox.showinfo("Eliminado", "Equipo eliminado correctamente.", parent=self)
        except ValueError as exc:
            messagebox.showerror("No se puede eliminar", str(exc), parent=self)
