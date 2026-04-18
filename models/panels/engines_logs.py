import customtkinter as ctk
import sys
import os
import sqlite3
import threading
import re
import time

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

from models.logic_units.absolute_path import get_base_path
from models.logic_units.stt_engine import STTEngine
from models.logic_units.engine_state import get_engine, is_engine_starting, set_engine, set_engine_starting

class PrintRedirector:
    def __init__(self, textbox, status_callback):
        self.textbox = textbox
        self.console = sys.__stdout__ 
        self.status_callback = status_callback
        self.ignore_next_newline = False 
        
        self.color_map = {
            '96': "#00FFFF", '92': "#00FF00", '93': "#FFFF00", 
            '95': "#FF00FF", '91': "#FF3333", '94': "#5555FF", 
            '97': "#FFFFFF", '2':  "#888888",
        }
        
        for code, hex_color in self.color_map.items():
            self.textbox.tag_config(f"color_{code}", foreground=hex_color)
        
        self.ansi_escape = re.compile(r'\x1b\[([0-9;]+)m')

    def write(self, text):
        if self.console:
            try: self.console.write(text)
            except Exception: pass

        if "[LOGS]" in text:
            self.ignore_next_newline = True
            return
        if self.ignore_next_newline and text == "\n":
            self.ignore_next_newline = False
            return
        self.ignore_next_newline = False

        # FIX 2: Wrapped in update_ui and pushed to main thread via .after()
        def update_ui():
            try:
                self.textbox.configure(state="normal")
                parts = self.ansi_escape.split(text)
                current_tags = []
                
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        if part:
                            if HAS_BIDI and any("\u0600" <= c <= "\u06FF" for c in part):
                                part = get_display(arabic_reshaper.reshape("\u200F" + part))
                                
                            self.textbox.insert("end", part, tuple(current_tags))
                    else:
                        if part == "0": current_tags.clear()
                        elif part == "1": pass 
                        elif part in self.color_map:
                            current_tags = [t for t in current_tags if not t.startswith("color_")]
                            current_tags.append(f"color_{part}")

                self.textbox.see("end")
                self.textbox.configure(state="disabled")
            except Exception:
                pass

            # Dynamic Status
            if "Waiting for speech" in text:
                self.status_callback("🟢 LISTENING", "#00FF00")
            elif "Transcribing" in text or "Heard:" in text:
                self.status_callback("🟡 PROCESSING VOICE...", "#FFC107")
            elif "Calibrating" in text:
                self.status_callback("🔵 CALIBRATING MIC...", "#29B6F6")
            elif "Loading Whisper" in text:
                self.status_callback("🟡 LOADING AI MODEL...", "#FFC107")
            elif "ENGINE STOP SIGNAL SENT" in text:
                self.status_callback("🟠 SHUTTING DOWN...", "#FF9800")
            elif "ENGINE SUCCESSFULLY OFFLINE" in text:
                self.status_callback("🔴 OFFLINE", "#D32F2F")
            elif "Auto-Restart" in text:
                self.status_callback("🔄 AUTO-RESTARTING...", "#E040FB")

        self.textbox.after(0, update_ui)

    def flush(self):
        if self.console:
            try: self.console.flush()
            except Exception: pass

class EnginesLogsPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#121212", corner_radius=15)
        self.engine = None
        self.engine_thread = None
        self.last_db_count = -1
        self.last_engine_state = None  # Track last known engine state
        
        # Check if an engine is already running or starting from auth
        running_engine = get_engine()
        if running_engine and getattr(running_engine, 'is_running', False):
            self.engine = running_engine
            self.last_engine_state = "running"
        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=40, pady=(40, 20))
        
        ctk.CTkLabel(
            self.header_frame, text="⚙️ ENGINES LOGS", 
            font=("Segoe UI", 24, "bold"), text_color="white"
        ).pack(side="left")
        
        self.status_indicator = ctk.CTkLabel(
            self.header_frame, text="🔴 OFFLINE", 
            font=("Segoe UI", 14, "bold"), text_color="#D32F2F"
        )
        self.status_indicator.pack(side="right")
        
        self.tabview = ctk.CTkTabview(self, fg_color="#1E1E1E", segmented_button_selected_color="#D32F2F")
        self.tabview.pack(expand=True, fill="both", padx=40, pady=(0, 20))
        
        self.tab_console = self.tabview.add("Console Logs")
        self.tab_db = self.tabview.add("STT Database (Live)")
        
        self.terminal = ctk.CTkTextbox(
            self.tab_console, fg_color="#050505", text_color="#CCCCCC", font=("Consolas", 13)
        )
        self.terminal.pack(expand=True, fill="both", padx=10, pady=10)
        self.terminal.insert("0.0", ">> SYSTEM READY. WAITING FOR ENGINE STARTUP...\n")
        self.terminal.configure(state="disabled")
        
        sys.stdout = PrintRedirector(self.terminal, self.update_status)
        sys.stderr = PrintRedirector(self.terminal, self.update_status)
        
        self.db_textbox = ctk.CTkTextbox(
            self.tab_db, fg_color="#0B1320", text_color="#FFFFFF", font=("Consolas", 14)
        )
        self.db_textbox.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.db_textbox.tag_config("id_tag", foreground="#FF4081")
        self.db_textbox.tag_config("time_tag", foreground="#00E5FF")
        self.db_textbox.tag_config("text_tag", foreground="#E0E0E0")
        self.db_textbox.tag_config("divider", foreground="#333333")
        self.db_textbox.configure(state="disabled")

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=40, pady=(0, 40))
        
        self.start_stop_btn = ctk.CTkButton(
            self.btn_frame, text="▶ START ENGINE", fg_color="#2E7D32", hover_color="#1B5E20",
            font=("Segoe UI", 14, "bold"), height=40, command=self.toggle_engine
        )
        self.start_stop_btn.pack(side="left", padx=(0, 10))

        self.restart_btn = ctk.CTkButton(
            self.btn_frame, text="🔄 RESTART", fg_color="#1976D2", hover_color="#0D47A1",
            font=("Segoe UI", 14, "bold"), height=40, command=self.restart_engine, state="disabled"
        )
        self.restart_btn.pack(side="left")
        
        # Check if engine is starting
        if is_engine_starting():
            self.start_stop_btn.configure(text="⏳ STARTING ENGINE...", fg_color="#FFC107", hover_color="#FFA000", state="disabled")
            self.last_engine_state = "starting"
            self.update_status("🟡 STARTING ENGINE...", "#FFC107")
        # Or if already running
        elif self.engine and getattr(self.engine, 'is_running', False):
            self.start_stop_btn.configure(text="■ STOP ENGINE", fg_color="#D32F2F", hover_color="#B71C1C")
            self.restart_btn.configure(state="normal")
            self.last_engine_state = "running"
            self.update_status("🟢 LISTENING", "#00FF00")

        self.refresh_db_view()
        self.monitor_engine_state()  # Start monitoring engine state

    def update_status(self, text, color):
        self.status_indicator.configure(text=text, text_color=color)

    def monitor_engine_state(self):
        """Monitor engine state changes and update UI accordingly"""
        # Determine current engine state - check actual engine state first
        current_state = None
        running_engine = get_engine()
        
        # Priority: actual engine running state > starting flag > stopped
        if running_engine and getattr(running_engine, 'is_running', False):
            current_state = "running"
            self.engine = running_engine
        elif is_engine_starting():
            current_state = "starting"
        else:
            current_state = "stopped"
        
        # Only update UI if state changed
        if current_state != self.last_engine_state:
            self.last_engine_state = current_state
            
            if current_state == "starting":
                self.start_stop_btn.configure(text="⏳ STARTING ENGINE...", fg_color="#FFC107", hover_color="#FFA000", state="disabled")
                self.restart_btn.configure(state="disabled")
                self.update_status("🟡 STARTING ENGINE...", "#FFC107")
                
            elif current_state == "running":
                self.start_stop_btn.configure(text="■ STOP ENGINE", fg_color="#D32F2F", hover_color="#B71C1C", state="normal")
                self.restart_btn.configure(state="normal")
                self.update_status("🟢 LISTENING", "#00FF00")
                
            elif current_state == "stopped":
                self.start_stop_btn.configure(text="▶ START ENGINE", fg_color="#2E7D32", hover_color="#1B5E20", state="normal")
                self.restart_btn.configure(state="disabled")
                self.update_status("🔴 OFFLINE", "#D32F2F")
        
        # Check again in a second
        self.after(1000, self.monitor_engine_state)

    def _get_current_engine(self):
        running_engine = get_engine()
        if running_engine:
            self.engine = running_engine
        return self.engine

    def toggle_engine(self):
        # Prevent starting if already starting
        if is_engine_starting():
            return

        engine = self._get_current_engine()
        if engine and getattr(engine, 'is_running', False):
            # Stop the engine properly
            engine.stop()
            self.engine = None  # Clear local reference
            set_engine(None)    # Clear global reference
            self.last_engine_state = "stopped"
            self.start_stop_btn.configure(text="▶ START ENGINE", fg_color="#2E7D32", hover_color="#1B5E20", state="normal")
            self.restart_btn.configure(state="disabled")
            self.update_status("🔴 OFFLINE", "#D32F2F")
        else:
            self.last_engine_state = "starting"
            self.start_stop_btn.configure(text="⏳ STARTING ENGINE...", fg_color="#FFC107", hover_color="#FFA000", state="disabled")
            self.restart_btn.configure(state="disabled")
            self.engine_thread = threading.Thread(target=self._run_stt_backend, daemon=True)
            self.engine_thread.start()

    def restart_engine(self):
        engine = self._get_current_engine()
        if engine and getattr(engine, 'is_running', False):
            self.last_engine_state = "restarting"
            self.start_stop_btn.configure(state="disabled", text="⏳ RESTARTING...", fg_color="#FF9800", hover_color="#F57C00")
            self.restart_btn.configure(state="disabled")
            
            self.terminal.configure(state="normal")
            self.terminal.insert("end", "\n[SYSTEM] Initiating Restart Sequence...\n")
            self.terminal.configure(state="disabled")
            
            # Stop the engine properly
            engine.stop()
            self.engine = None  # Clear local reference
            set_engine(None)    # Clear global reference
            threading.Thread(target=self._wait_and_restart, daemon=True).start()

    def _wait_and_restart(self):
        # Wait for the engine thread to finish
        while self.engine_thread and self.engine_thread.is_alive():
            time.sleep(0.2) 
        # Only restart the engine, not the UI
        self.after(0, self._restart_engine_only)

    def _restart_engine_only(self):
        """Restart only the engine, not the entire UI"""
        self.last_engine_state = "starting"
        self.start_stop_btn.configure(text="⏳ STARTING ENGINE...", fg_color="#FFC107", hover_color="#FFA000", state="disabled")
        self.restart_btn.configure(state="disabled")
        self.update_status("🟡 STARTING ENGINE...", "#FFC107")
        self.engine_thread = threading.Thread(target=self._run_stt_backend, daemon=True)
        self.engine_thread.start() 

    def _run_stt_backend(self):
        try:
            set_engine_starting(True)
            self.engine = STTEngine(model_size="medium")
            set_engine(self.engine)
            self.engine.load_engine_to_vram()
            
            # FIX 1: Set starting state to False BEFORE the blocking loop
            set_engine_starting(False)
            
            self.engine.start_listening()
            
            if getattr(self.engine, "auto_restart_triggered", False):
                self.after(0, self.restart_engine)

        except Exception as e:
            print(f"\n\033[91m[CRITICAL ERROR in Engine Thread]: {e}\033[0m")
            self.last_engine_state = "stopped"
            self.update_status("🔴 CRASHED", "#D32F2F")
            self.start_stop_btn.configure(text="▶ START ENGINE", fg_color="#2E7D32", state="normal")
            self.restart_btn.configure(state="disabled")
            set_engine(None)
        finally:
            set_engine_starting(False)

    def refresh_db_view(self):
        db_path = os.path.join(get_base_path(), "stt_store.db")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # FIX: ORDER BY id ASC puts newest messages at the BOTTOM naturally!
                cursor.execute("SELECT id, text, timestamp FROM transcripts ORDER BY id ASC")
                rows = cursor.fetchall()
                conn.close()
                
                # Only redraw if the number of rows changed (prevents constant flickering)
                if len(rows) != self.last_db_count:
                    self.db_textbox.configure(state="normal")
                    self.db_textbox.delete("0.0", "end")
                    
                    if not rows:
                        self.db_textbox.insert("end", "\n  >> Database is empty. Waiting for speech...\n", "time_tag")
                    else:
                        for r in rows:
                            self.db_textbox.insert("end", f" [ID: {r[0]:02d}] ", "id_tag")
                            self.db_textbox.insert("end", f"[{r[2]}]\n", "time_tag")
                            
                            db_text = r[1]
                            if HAS_BIDI and any("\u0600" <= c <= "\u06FF" for c in db_text):
                                db_text = get_display(arabic_reshaper.reshape("\u200F" + db_text))
                                
                            self.db_textbox.insert("end", f"  {db_text}\n", "text_tag")
                            self.db_textbox.insert("end", "  " + "─"*70 + "\n\n", "divider")
                    
                    # FIX: ALWAYS AUTO-SCROLL TO THE BOTTOM TO SEE THE NEWEST MESSAGE
                    self.db_textbox.see("end")
                    self.db_textbox.configure(state="disabled")
                    self.last_db_count = len(rows)
                    
            except Exception:
                pass 

        self.after(1000, self.refresh_db_view)