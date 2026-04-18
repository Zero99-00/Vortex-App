import customtkinter as ctk

class StatusPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#121212", corner_radius=15)

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=40, pady=(40, 20))
        
        ctk.CTkLabel(self.header_frame, text="📊 SYSTEM STATUS", font=("Segoe UI", 28, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(self.header_frame, text="🟢 VORTEX ONLINE", font=("Segoe UI", 16, "bold"), text_color="#AAAAAA").pack(side="right")

        self.stats_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.stats_frame.pack(expand=True, fill="both", padx=30, pady=(0, 30))
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)

        def create_modern_card(parent, row, col, icon, title, value_text, is_progress=False, progress_val=0.0):
            card = ctk.CTkFrame(parent, fg_color="#1A1A1A", border_color="#333333", border_width=1, corner_radius=10, height=120)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)
            
            top_frame = ctk.CTkFrame(card, fg_color="transparent")
            top_frame.pack(fill="x", padx=20, pady=(15, 5))
            
            ctk.CTkLabel(top_frame, text=f"{icon}  {title.upper()}", font=("Segoe UI", 13, "bold"), text_color="#888888").pack(side="left")
            
            if is_progress:
                prog_frame = ctk.CTkFrame(card, fg_color="transparent")
                prog_frame.pack(fill="x", padx=20, pady=(10, 5))
                prog = ctk.CTkProgressBar(prog_frame, progress_color="#D32F2F", fg_color="#333333", height=12)
                prog.pack(side="left", fill="x", expand=True, padx=(0, 15))
                prog.set(progress_val) 
                ctk.CTkLabel(prog_frame, text=value_text, font=("Consolas", 16, "bold"), text_color="white").pack(side="right")
            else:
                ctk.CTkLabel(card, text=value_text, font=("Consolas", 24, "bold"), text_color="white").pack(anchor="w", padx=20, pady=(5, 10))

        # Row 0
        create_modern_card(self.stats_frame, 0, 0, "🔋", "Core Battery", "85%", is_progress=True, progress_val=0.85)
        create_modern_card(self.stats_frame, 0, 1, "📍", "Global Coordinates", "X: 14.25  Y: -5.80")
        
        # Row 1
        create_modern_card(self.stats_frame, 1, 0, "🌡️", "Control Unit Temp", "42°C")
        create_modern_card(self.stats_frame, 1, 1, "⚡", "Motor Draw", "2.4 Amps")
        
        # Row 2
        create_modern_card(self.stats_frame, 2, 0, "🗣️", "Audio Subsystem", "LISTENING...")
        create_modern_card(self.stats_frame, 2, 1, "⚠️", "Diagnostics", "SYSTEM NOMINAL")

        # Row 3 (FIXED ICON)
        create_modern_card(self.stats_frame, 3, 0, "🧭", "Movement Status", "IDLE / STATIONARY")
        create_modern_card(self.stats_frame, 3, 1, "⏱️", "System Uptime", "02:14:30")