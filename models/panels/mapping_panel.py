import customtkinter as ctk

class MappingPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#121212", corner_radius=15)
        
        ctk.CTkLabel(self, text="🔍 ROBOT MAPPING VIEW", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=40, pady=(40, 20))
        
        self.map_display = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=10)
        self.map_display.pack(expand=True, fill="both", padx=40, pady=(0, 40))
        
        ctk.CTkLabel(self.map_display, text="[ Awaiting Telemetry... ]", font=("Consolas", 16), text_color="#555555").place(relx=0.5, rely=0.5, anchor="center")