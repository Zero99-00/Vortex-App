import tkinter.messagebox as messagebox
from ..dashboard import dashboard_gui
def verify_login(self):
        user = self.username_entry.get()
        pwd = self.password_entry.get()
        #if user or pwd in ['();:']:return
        if user == "admin" and pwd == "admin":
            print("[LOGS] auth__ : Access Granted!\n[LOGS] auth__ :Sending Next Page Request")
            self.auth_flag = True
            self.login_frame.destroy() 
            dashboard_gui(self)
            print('[LOGS] auth__ : Got Response!')
        else:
            print("[LOGS] auth__ : Access Denied! : return")
            messagebox.showerror("Access Denied", "Invalid Data.")
            self.username_entry.configure(border_width=2,border_color="#D32F2F")
            self.password_entry.configure(border_width=2,border_color="#D32F2F")
            self.password_entry.delete(0, "end")
            self.username_entry.delete(0, "end")
            # Reset UI to allow retry
            self.reset_login_ui()
            return