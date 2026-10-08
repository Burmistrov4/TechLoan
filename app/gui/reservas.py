import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from app.gui.session import Session
from app.services.reservation_service import ReservationService
from app.services.laboratorio_service import LaboratorioService
from app.services.prestatario_service import PrestatarioService


class ReservasWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("TechLoan — Reservas")
        self.geometry("1150x700")
        self.minsize(980, 600)
        self.transient(master)

        self.laboratorios = []
        self.prestatarios = []

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Reservas de laboratorios",
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Actualizar lista",
                   command=self.load_data).pack(side="right")

        form = ttk.LabelFrame(self, text="Nueva reserva", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 10))

        self.vars = {key: tk.StringVar() for key in (
            "laboratorio", "prestatario", "fecha", "hora_inicio",
            "duracion", "hora_fin", "observaciones"
        )}

        ttk.Label(form, text="Laboratorio").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.lab_combo = ttk.Combobox(
            form, textvariable=self.vars["laboratorio"], state="readonly", width=38
        )
        self.lab_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.lab_combo.bind("<<ComboboxSelected>>", self.on_lab_selected)

        ttk.Label(form, text="Prestatario").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.prest_combo = ttk.Combobox(
            form, textvariable=self.vars["prestatario"], state="readonly", width=38
        )
        self.prest_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(form, text="Fecha (AAAA-MM-DD)").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(form, textvariable=self.vars["fecha"], width=20).grid(
            row=1, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(form, text="Hora inicio (HH:MM)").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(form, textvariable=self.vars["hora_inicio"], width=20).grid(
            row=1, column=3, padx=5, pady=5, sticky="w"
        )

        ttk.Label(form, text="Duración (min)").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        duration_frame = ttk.Frame(form)
        duration_frame.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ttk.Entry(duration_frame, textvariable=self.vars["duracion"], width=12).pack(side="left")
        ttk.Label(duration_frame, text="  Estándar: 70 min").pack(side="left")

        ttk.Label(form, text="Hora fin").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        ttk.Label(form, textvariable=self.vars["hora_fin"],
                  font=("Segoe UI", 10, "bold")).grid(
            row=2, column=3, padx=5, pady=5, sticky="w"
        )

        ttk.Label(form, text="Observaciones").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(form, textvariable=self.vars["observaciones"], width=85).grid(
            row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        ttk.Button(form, text="Calcular hora fin",
                   command=self.calculate_end).grid(row=4, column=1, padx=5, pady=8, sticky="w")
        ttk.Button(form, text="Crear reserva",
                   command=self.create).grid(row=4, column=3, padx=5, pady=8, sticky="e")

        for column in range(4):
            form.columnconfigure(column, weight=1)

        self.vars["fecha"].set(datetime.now().strftime("%Y-%m-%d"))
        self.vars["hora_inicio"].set("08:00")
        self.vars["duracion"].set("70")

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id", "fecha", "hora_inicio", "hora_fin", "duracion",
            "laboratorio", "prestatario", "estado", "observaciones"
        )
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "id": "ID", "fecha": "Fecha", "hora_inicio": "Inicio",
            "hora_fin": "Fin", "duracion": "Duración", "laboratorio": "Laboratorio",
            "prestatario": "Prestatario", "estado": "Estado",
            "observaciones": "Observaciones"
        }
        widths = {
            "id": 45, "fecha": 95, "hora_inicio": 70, "hora_fin": 70,
            "duracion": 75, "laboratorio": 190, "prestatario": 190,
            "estado": 100, "observaciones": 220
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(side="top", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.load_reference_data()
        self.load_data()

    def load_reference_data(self):
        self.laboratorios = LaboratorioService.list_all()
        lab_values = [
            f'{row["id"]} — {row["codigo"]} — {row["nombre"]} '
            f'({row["capacidad"]} puestos)'
            for row in self.laboratorios
            if row["estado"] == "DISPONIBLE"
        ]
        self.lab_combo["values"] = lab_values

        self.prestatarios = PrestatarioService.list_all()
        prest_values = [
            f'{row["id"]} — {row["cedula"]} — {row["nombre"]} {row["apellido"]}'
            for row in self.prestatarios
            if row.get("estado", "ACTIVO") == "ACTIVO"
        ]
        self.prest_combo["values"] = prest_values

        if not self.vars["laboratorio"].get() and lab_values:
            self.lab_combo.current(0)
            self.on_lab_selected()

        if not self.vars["prestatario"].get() and prest_values:
            self.prest_combo.current(0)

    def on_lab_selected(self, _event=None):
        value = self.vars["laboratorio"].get()
        if not value:
            return
        try:
            lab_id = int(value.split(" — ", 1)[0])
        except (ValueError, IndexError):
            return
        lab = LaboratorioService.get(lab_id)
        if lab:
            self.vars["duracion"].set(str(lab["duracion_estandar_minutos"]))
            self.calculate_end()

    def calculate_end(self):
        try:
            self.vars["hora_fin"].set(
                ReservationService.calculate_end_time(
                    self.vars["hora_inicio"].get().strip(),
                    int(self.vars["duracion"].get().strip())
                )
            )
        except (ValueError, TypeError) as exc:
            self.vars["hora_fin"].set("")
            messagebox.showerror("Horario inválido", str(exc), parent=self)

    def _selected_id(self, value):
        try:
            return int(value.split(" — ", 1)[0])
        except (ValueError, IndexError):
            raise ValueError("Seleccione un laboratorio y un prestatario válidos.")

    def create(self):
        if not Session.can("reservas.write"):
            messagebox.showerror(
                "Permiso", "No tiene permiso para crear reservas.", parent=self
            )
            return

        if not self.vars["laboratorio"].get() or not self.vars["prestatario"].get():
            messagebox.showwarning(
                "Datos incompletos",
                "Seleccione el laboratorio y el prestatario.",
                parent=self
            )
            return

        try:
            laboratorio_id = self._selected_id(self.vars["laboratorio"].get())
            prestatario_id = self._selected_id(self.vars["prestatario"].get())
            usuario_id = int(Session.current_user["id"])
            fecha = self.vars["fecha"].get().strip()
            hora_inicio = self.vars["hora_inicio"].get().strip()
            duracion = int(self.vars["duracion"].get().strip())

            ReservationService.create_reservation(
                laboratorio_id,
                prestatario_id,
                usuario_id,
                fecha,
                hora_inicio,
                duracion,
                self.vars["observaciones"].get().strip()
            )
            hora_fin = ReservationService.calculate_end_time(hora_inicio, duracion)
            messagebox.showinfo(
                "Reserva creada",
                f"Reserva registrada correctamente.\nHorario: {hora_inicio} - {hora_fin}.",
                parent=self
            )
            self.load_data()
            self.load_reference_data()
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("No se puede crear la reserva", str(exc), parent=self)

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in ReservationService.list_all():
            prestatario = (
                f'{row["cedula"]} — {row["prestatario_nombre"]} '
                f'{row["prestatario_apellido"]}'
            )
            laboratorio = f'{row["laboratorio_codigo"]} — {row["laboratorio_nombre"]}'
            self.tree.insert("", "end", values=(
                row["id"], row["fecha"], row["hora_inicio"], row["hora_fin"],
                f'{row["duracion_minutos"]} min', laboratorio, prestatario,
                row["estado"], row.get("observaciones") or ""
            ))
