import tkinter as tk
from tkinter import messagebox

import urllib.error
import urllib.request


class TechLoanApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TechLoan - Gestión de Recursos Tecnológicos")
        self.geometry("900x560")
        self.resizable(False, False)
        self._build()

    def _build(self):
        frame = tk.Frame(self, padx=30, pady=30)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="TECHLOAN",
            font=("Segoe UI", 26, "bold"),
        ).pack(pady=(30, 5))

        tk.Label(
            frame,
            text="Sistema de Gestión de Reservas y Préstamos",
            font=("Segoe UI", 12),
        ).pack(pady=(0, 30))

        tk.Button(
            frame,
            text="Comprobar servidor Flask",
            width=28,
            command=self.check_server,
        ).pack(pady=10)

        tk.Button(
            frame,
            text="Salir",
            width=28,
            command=self.destroy,
        ).pack(pady=10)

    def check_server(self):
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=3) as response:
                messagebox.showinfo("TechLoan", response.read().decode("utf-8"))
        except urllib.error.URLError:
            messagebox.showerror(
                "TechLoan",
                "No se pudo conectar con Flask. Inicia primero run_server.py.",
            )


if __name__ == "__main__":
    TechLoanApp().mainloop()
