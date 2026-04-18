import customtkinter as ctk
import tkinter as tk
import ctypes
import os
from models.authorization import auth_gui

class main_window(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.auth_flag = False
        self.resizable(False, False)
        icon_path = os.path.abspath(os.path.join(os.getcwd(), "images", "icon.png"))
    
        try:
            self.img = tk.PhotoImage(file=icon_path)
        # 'True' forces the icon to apply to this window and all future child windows
            self.wm_iconphoto(True, self.img) 
        except Exception as e:
            print(f"CRITICAL ICON ERROR: Could not load {icon_path}")
            print(f"Exact error: {e}")
        if self.auth_flag:
            self.title('Vortex | Robot Management App')
            self.geometry(f"1300x700+{(self.winfo_screenwidth() - 1300) // 2}+{(self.winfo_screenheight() - 700) // 2}")
        else:
            auth_gui(self)

    def set_window_icon(self):
        icon_path = os.path.join("images", "icon.png")
        try:
            if os.name == 'nt':
                app_id = 'vortex.robotics.management.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            
            self.img = tk.PhotoImage(file=icon_path)
            self.iconphoto(False, self.img)
        except Exception as e:
            print(f"Icon Error: {e}")