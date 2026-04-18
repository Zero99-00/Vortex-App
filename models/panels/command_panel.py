import customtkinter as ctk
import sys
import re

# Regex to clean terminal color codes from the UI text
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class PrintRedirector:
    def __init__(self, textbox):
        self.textbox = textbox
        # sys.__stdout__ is None when running a windowed PyInstaller .exe
        self.console = sys.__stdout__ 

    def write(self, text):
        # 1. Safely write to background console (keeps your colors in the terminal!)
        if hasattr(self, 'console') and self.console is not None:
            try:
                self.console.write(text)
            except Exception:
                pass
                
        # 2. Strip color codes so the GUI doesn't get ugly symbols
        clean_text = ansi_escape.sub('', text)
        
        # 3. CRITICAL THREAD FIX: Use .after() to tell the main thread to update the UI
        if clean_text:
            try:
                self.textbox.after(0, self._thread_safe_insert, clean_text)
            except Exception:
                pass

    def _thread_safe_insert(self, text):
        try:
            self.textbox.insert("end", text)
            self.textbox.see("end")
        except Exception:
            pass

    def flush(self):
        # Safely flush background console ONLY if it exists
        if hasattr(self, 'console') and self.console is not None:
            try:
                self.console.flush()
            except Exception:
                pass

class CommandPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#121212", corner_radius=15)
        
        self.command_history = []
        
        # --- HEADER SECTION (Title + Lamp) ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=40, pady=(40, 20))
        
        ctk.CTkLabel(self.header_frame, text="⚡ COMMAND TERMINAL", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
        
        # The Status Lamp
        self.status_indicator = ctk.CTkLabel(self.header_frame, text="🔴 No connection established", font=("Segoe UI", 14, "bold"), text_color="#D32F2F")
        self.status_indicator.pack(side="right")
        
        # --- TERMINAL SECTION ---
        self.terminal = ctk.CTkTextbox(self, fg_color="#050505", text_color="#00FF00", font=("Consolas", 14))
        self.terminal.pack(expand=True, fill="both", padx=40, pady=(0, 20))
        self.terminal.insert("0.0", ">> VORTEX COMMAND LINK ESTABLISHED...\n")
        
        # Override standard outputs to feed into our custom GUI terminal
        sys.stdout = PrintRedirector(self.terminal)
        sys.stderr = PrintRedirector(self.terminal)
        
        # --- INPUT SECTION ---
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=40, pady=(0, 40))
        
        self.cmd_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Enter command...", font=("Consolas", 16), height=45)
        self.cmd_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.cmd_entry.bind("<Return>", self.send_command)
        
        ctk.CTkButton(self.input_frame, text="EXECUTE", fg_color="#D32F2F", hover_color="#B71C1C", font=("Segoe UI", 14, "bold"), width=120, height=45, command=self.send_command).pack(side="right")

    def send_command(self, event=None):
        cmd_text = self.cmd_entry.get().strip()
        
        if cmd_text:
            self.command_history.append(cmd_text)
            # Display user input
            self.terminal.insert("end", f"\n>> [USER_INPUT]: {cmd_text}\n")
            self.terminal.see("end")
            self.cmd_entry.delete(0, "end")
            
            # Route to the backend logic
            self.execute_backend_command(cmd_text)

    def execute_backend_command(self, command):
        # Because of PrintRedirector, these prints automatically show up in the GUI terminal!
        if command.lower() == "ping":
            print(">> ERROR: Destination unreachable. Verify robot IP.")
        elif command.lower() == "clear":
            self.terminal.delete("0.0", "end")
            print(">> TERMINAL CLEARED.")
        else:
            print(f">> Command '{command}' queued. Waiting for network connection...")