import customtkinter as ctk
import time
from models.logic_units.engine_state import get_engine

class StatusPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#121212", corner_radius=15)

        # Track when the dashboard was opened for the Uptime counter
        self.start_time = time.time()

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
                val_label = ctk.CTkLabel(prog_frame, text=value_text, font=("Consolas", 16, "bold"), text_color="white")
                val_label.pack(side="right")
                return val_label
            else:
                val_label = ctk.CTkLabel(card, text=value_text, font=("Consolas", 24, "bold"), text_color="white")
                val_label.pack(anchor="w", padx=20, pady=(5, 10))
                return val_label

        # Row 0
        create_modern_card(self.stats_frame, 0, 0, "🔋", "Core Battery", "85%", is_progress=True, progress_val=0.85)
        create_modern_card(self.stats_frame, 0, 1, "🌡️", "Control Unit Temp", "42°C")
        
        # Row 1
        create_modern_card(self.stats_frame, 1, 0, "⚡", "Motor Draw", "2.4 Amps")
        self.audio_status_label = create_modern_card(self.stats_frame, 1, 1, "🗣️", "Audio Subsystem", "🔴 OFFLINE")
        
        # Row 2
        create_modern_card(self.stats_frame, 2, 0, "⚠️", "Diagnostics", "SYSTEM NOMINAL")
        create_modern_card(self.stats_frame, 2, 1, "🧭", "Movement Status", "IDLE / STATIONARY")

        # Row 3
        self.uptime_label = create_modern_card(self.stats_frame, 3, 0, "⏱️", "System Uptime", "00:00:00")
        
        # Start the background loop to update stats dynamically
        self.update_dynamic_stats()

    def update_dynamic_stats(self):
        # 1. Update Uptime Timer
        elapsed = int(time.time() - self.start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.uptime_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        # 2. Update Audio Subsystem Status
        engine = get_engine()
        if engine and getattr(engine, 'is_running', False):
            # Fetch the current state from the engine (defaults to LISTENING if not set)
            current_state = getattr(engine, 'current_state', 'LISTENING...').upper()
            
            # Change color based on the state for that extra polish
            if "PROCESS" in current_state:
                color = "#FFD700"  # Yellow
            elif "CHOOSE" in current_state or "LANGUAGE" in current_state:
                color = "#00FFFF"  # Cyan
            else:
                color = "#00FF00"  # Green
                
            self.audio_status_label.configure(text=f"🟢 {current_state}", text_color=color)
        else:
            self.audio_status_label.configure(text="🔴 OFFLINE", text_color="#D32F2F")
            
        # Loop this check every 1 second
        self.after(1000, self.update_dynamic_stats)