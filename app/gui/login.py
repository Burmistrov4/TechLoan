import tkinter as tk
from tkinter import messagebox
from app.services.auth_service import AuthService
from app.gui.session import Session

class LoginWindow(tk.Toplevel):
    def __init__(self, master, on_success):
        super().__init__(master); self.on_success=on_success
        self.title("TechLoan — Iniciar sesión"); self.resizable(False,False); self.grab_set()
        frame=tk.Frame(self,padx=25,pady=25); frame.pack()
        tk.Label(frame,text="TECHLOAN",font=("Segoe UI",18,"bold")).pack(pady=(0,15))
        tk.Label(frame,text="Usuario").pack(anchor="w")
        self.username=tk.Entry(frame,width=32); self.username.pack(pady=(0,10))
        tk.Label(frame,text="Contraseña").pack(anchor="w")
        self.password=tk.Entry(frame,width=32,show="•"); self.password.pack(pady=(0,15))
        tk.Button(frame,text="Iniciar sesión",width=25,command=self._login).pack()
        self.password.bind("<Return>",lambda _:self._login()); self.username.focus_set()

    def _login(self):
        try:
            user=AuthService.authenticate(self.username.get(),self.password.get())
            Session.start(user); self.grab_release(); self.destroy(); self.on_success(user)
        except ValueError as exc:
            messagebox.showerror("Acceso denegado",str(exc),parent=self)
