import tkinter as tk
from app.database import init_database
from app.gui.login import LoginWindow
from app.gui.dashboard import DashboardWindow

class Application:
    def __init__(self):
        init_database(); self.root=tk.Tk(); self.root.withdraw(); self.show_login()
    def show_login(self): LoginWindow(self.root,self.show_dashboard)
    def show_dashboard(self,user): DashboardWindow(self.root)
    def run(self): self.root.mainloop()

if __name__=="__main__": Application().run()
