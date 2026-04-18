import customtkinter as ctk 
import tkinter as tk
from .panels.mapping_panel import MappingPanel
from .panels.qa_panel import QAPanel
from .panels.command_panel import CommandPanel
from .panels.settings_panel import SettingsPanel
from .panels.status_panel import StatusPanel  
from .panels.servo_panel import ServoPanel  
from .panels.engines_logs import EnginesLogsPanel

def dashboard_gui(self):
        self.title('Vortex | Command Center')
        # icon_path = os.path.join("images", "icon.png")
        # if os.name == 'nt':
        #     ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('vortex.app.1')

        # self.img = tk.PhotoImage(file=icon_path)
        # self.iconphoto(False, self.img)
        self.configure(fg_color="#050505")
        self.geometry(f"1300x700+{(self.winfo_screenwidth() - 1300) // 2}+{(self.winfo_screenheight() - 700) // 2}")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1) 

        self.nav_frame = ctk.CTkFrame(self, width=260, fg_color="#121212", border_color="#D32F2F", border_width=2, corner_radius=15)
        self.nav_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ns")
        
        # FIX: Row 7 is now the "spring" that pushes settings to the bottom
        self.nav_frame.grid_rowconfigure(7, weight=1)
        self.logo_label = ctk.CTkLabel(self.nav_frame, text="> VORTEX _", font=("Courier", 32, "bold"), text_color="#D32F2F")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))

        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)

        self.pages = {
            "status": StatusPanel(self.main_content_frame),  
            "mapping": MappingPanel(self.main_content_frame),
            "qa": QAPanel(self.main_content_frame),
            "command": CommandPanel(self.main_content_frame),
            "servo": ServoPanel(self.main_content_frame),  # <-- Added Servo Panel
            "settings": SettingsPanel(self.main_content_frame),
            "engine": EnginesLogsPanel(self.main_content_frame)
        }

        def select_page(page_name):
            for page in self.pages.values():
                page.grid_forget()
            self.pages[page_name].grid(row=0, column=0, sticky="nsew")

        btn_font = ("Segoe UI", 15, "bold")
        btn_kwargs = {
            "anchor": "w",           
            "font": btn_font,
            "fg_color": "transparent",
            "text_color": "#AAAAAA", 
            "hover_color": "#D32F2F",
            "height": 45,            
            "corner_radius": 8       
        }

        self.btn_status = ctk.CTkButton(self.nav_frame, text="📊  Status", command=lambda: select_page("status"), **btn_kwargs)
        self.btn_status.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="ew")

        self.menu_separator = ctk.CTkFrame(self.nav_frame, height=2, fg_color="#333333")
        self.menu_separator.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # self.btn_map = ctk.CTkButton(self.nav_frame, text="🔍  Mapping View", command=lambda: select_page("mapping"), **btn_kwargs)
        # self.btn_map.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.btn_qa = ctk.CTkButton(self.nav_frame, text="🧠  Edit Q&A", command=lambda: select_page("qa"), **btn_kwargs)
        self.btn_qa.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.btn_cmd = ctk.CTkButton(self.nav_frame, text="⚡  Command Panel", command=lambda: select_page("command"), **btn_kwargs)
        self.btn_cmd.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        # <-- Added Servo Tab Button
        self.btn_servo = ctk.CTkButton(self.nav_frame, text="🦾  Servo Control", command=lambda: select_page("servo"), **btn_kwargs)
        self.btn_servo.grid(row=6, column=0, padx=20, pady=5, sticky="ew")



        self.btn_engine = ctk.CTkButton(self.nav_frame, text=" ⚗️  Engine Logs", command=lambda: select_page("engine"), **btn_kwargs)
        self.btn_engine.grid(row=7, column=0, padx=20, pady=5, sticky="ew")





        # Pushed Settings to Row 8
        self.btn_settings = ctk.CTkButton(self.nav_frame, text="⚙️  Settings", command=lambda: select_page("settings"), **btn_kwargs)
        self.btn_settings.grid(row=8, column=0, padx=20, pady=(0, 30), sticky="ew") 





        select_page("status")

        print('[LOGS] dashboard : Window Loaded!')