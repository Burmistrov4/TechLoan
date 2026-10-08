import tkinter as tk
from tkinter import ttk, messagebox

from app.gui.session import Session
from app.services.categoria_service import CategoriaService


class CategoriasWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Categorías")
        self.geometry("850x600")
        self.minsize(760, 520)
        self.transient(master)
        self.selected_id = None

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Categorías", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Nuevo", command=self.new_record).pack(side="right")

        form = ttk.LabelFrame(self, text="Datos de la categoría", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 10))

        self.nombre_var = tk.StringVar()
        ttk.Label(form, text="Nombre").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(form, textvariable=self.nombre_var, width=35).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )

        ttk.Label(form, text="Descripción").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.descripcion_text = tk.Text(form, height=4, width=55, wrap="word")
        self.descripcion_text.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(form, text="Guardar", command=self.save).grid(
            row=0, column=2, padx=8, pady=5
        )
        ttk.Button(form, text="Eliminar seleccionado", command=self.delete_selected).grid(
            row=1, column=2, padx=8, pady=5
        )
        form.columnconfigure(1, weight=1)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "nombre", "descripcion")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {"id": "ID", "nombre": "Nombre", "descripcion": "Descripción"}
        widths = {"id": 55, "nombre": 220, "descripcion": 480}
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
        self.nombre_var.set("")
        self.descripcion_text.delete("1.0", "end")
        self.tree.selection_remove(self.tree.selection())

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in CategoriaService.list_all():
            self.tree.insert("", "end", values=(
                row["id"], row["nombre"], row.get("descripcion") or ""
            ))

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.selected_id = int(values[0])
        row = CategoriaService.get(self.selected_id)
        if not row:
            return
        self.nombre_var.set(row["nombre"])
        self.descripcion_text.delete("1.0", "end")
        self.descripcion_text.insert("1.0", row.get("descripcion") or "")

    def _payload(self):
        return {
            "nombre": self.nombre_var.get().strip(),
            "descripcion": self.descripcion_text.get("1.0", "end-1c").strip()
        }

    def save(self):
        if not Session.can("categorias.write"):
            messagebox.showerror(
                "Permiso", "No tiene permiso para modificar categorías.", parent=self
            )
            return
        try:
            data = self._payload()
            if self.selected_id is None:
                CategoriaService.create(data)
                messagebox.showinfo("Guardado", "Categoría registrada correctamente.", parent=self)
            else:
                CategoriaService.update(self.selected_id, data)
                messagebox.showinfo("Actualizado", "Categoría actualizada correctamente.", parent=self)
            self.load_data()
            self.new_record()
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)

    def delete_selected(self):
        if not Session.can("categorias.delete"):
            messagebox.showerror(
                "Permiso", "No tiene permiso para eliminar categorías.", parent=self
            )
            return
        if self.selected_id is None:
            messagebox.showwarning("Seleccionar", "Seleccione una categoría.", parent=self)
            return
        if not messagebox.askyesno(
            "Confirmar", "¿Eliminar la categoría seleccionada?", parent=self
        ):
            return
        try:
            CategoriaService.delete(self.selected_id)
            self.load_data()
            self.new_record()
            messagebox.showinfo("Eliminado", "Categoría eliminada correctamente.", parent=self)
        except ValueError as exc:
            messagebox.showerror("No se puede eliminar", str(exc), parent=self)
