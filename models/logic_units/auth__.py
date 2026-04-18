import tkinter.messagebox as messagebox

def verify_login(self):
    user = self.username_entry.get()
    pwd = self.password_entry.get()

    if user == "admin" and pwd == "admin":
        print("[LOGS] auth__ : Access Granted!")
        self.auth_flag = True
        return True
    else:
        print("[LOGS] auth__ : Invalid login data. Access Denied! Returning to login.")
        self.username_entry.configure(border_width=2, border_color="#D32F2F")
        self.password_entry.configure(border_width=2, border_color="#D32F2F")
        self.password_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        messagebox.showerror("Login Error", "Invalid data access denied")
        return False