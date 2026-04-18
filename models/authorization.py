import customtkinter as ctk
from PIL import Image
from models.logic_units.auth__ import verify_login
import os
import tkinter as tk
import threading

# Import engine components
from models.dashboard import dashboard_gui
from models.logic_units.stt_engine import STTEngine
from models.logic_units.llm_engine import LLMEngine
from models.logic_units.tts_engine import TTSEngine  # <--- ADDED TTS IMPORT
from models.logic_units.engine_state import set_engine, set_engine_starting

def auth_gui(self):
    self.title('Vortex | Authorization Page')
    self.geometry(f"1300x700+{(self.winfo_screenwidth() - 1300) // 2}+{(self.winfo_screenheight() - 700) // 2}")
    
    # --- ANTI-SPAM LOCK & THREAD STATES ---
    self.is_authenticating = False 
    self.engine_load_finished = False
    self.engine_load_success = False
    
    # --- BULLETPROOF PATH LOGIC ---
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_dir, "images", "icon.ico")
    png_path = os.path.join(base_dir, "images", "icon.png")
    
    eye_path = os.path.join(base_dir, "images", "eye.png")
    closed_eye_path = os.path.join(base_dir, "images", "closed_eye.png")
        
    try:
        self.iconbitmap(ico_path) 
    except:
        pass 

    # --- MAIN UI FRAME ---
    self.login_frame = ctk.CTkFrame(
        self, fg_color="#121212", border_color="#D32F2F", 
        border_width=2, corner_radius=10
    )
    self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

    try:
        raw_img = Image.open(png_path)
        icon_image = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(140, 90))
        self.icon_label = ctk.CTkLabel(self.login_frame, text="", image=icon_image)
        self.icon_label.pack(pady=(40, 10))
    except Exception as e:
        print(f"Frame image missing: {e}")

    self.title_label = ctk.CTkLabel(
        self.login_frame, text="SYSTEM ACCESS", 
        font=("Verdana", 24, "bold"), text_color="#D32F2F"
    )
    self.title_label.pack(pady=(0, 30), padx=50)

    # --- FORM ELEMENTS ---
    self.username_entry = ctk.CTkEntry(
        self.login_frame, font=("Consolas", 18), placeholder_text="Username", 
        width=280, height=45, fg_color="#1E1E1E", border_color="#555555"
    )
    self.username_entry.pack(pady=(0, 20), padx=50)

    self.password_entry = ctk.CTkEntry(
        self.login_frame, font=("Consolas", 18), placeholder_text="Password", 
        show="*", width=280, height=45, fg_color="#1E1E1E", border_color="#555555"
    )
    self.password_entry.pack(pady=(0, 30), padx=50)
    
    try:
        open_eye_raw = Image.open(eye_path)
        closed_eye_raw = Image.open(closed_eye_path)
        self.open_eye_img = ctk.CTkImage(light_image=open_eye_raw, dark_image=open_eye_raw, size=(20, 20))
        self.closed_eye_img = ctk.CTkImage(light_image=closed_eye_raw, dark_image=closed_eye_raw, size=(20, 20))
    except:
        self.open_eye_img = None
        self.closed_eye_img = None

    def toggle_password():
        if self.password_entry.cget("show") == "*":
            self.password_entry.configure(show="")
            self.toggle_btn.configure(image=self.open_eye_img)
        else:
            self.password_entry.configure(show="*")
            self.toggle_btn.configure(image=self.closed_eye_img)

    self.toggle_btn = ctk.CTkButton(
        self.login_frame, text="", image=self.closed_eye_img, width=30, height=30, 
        fg_color="#1E1E1E", bg_color="#1E1E1E", hover_color="#333333", command=toggle_password
    )
    self.toggle_btn.place(in_=self.password_entry, relx=0.92, rely=0.5, anchor="center")
    
    # --- IMPROVED LOADING UI ---
    self.loading_bar = ctk.CTkProgressBar(
        self.login_frame, width=220, mode="indeterminate", progress_color="#D32F2F"
    )
    self.loading_status = ctk.CTkLabel(
        self.login_frame, text="Verifying secure connection...", 
        font=("Consolas", 12), text_color="gray"
    )

    self.loading_log = ctk.CTkTextbox(
        self.login_frame, width=280, height=120, fg_color="#1E1E1E",
        text_color="#FFFFFF", font=("Consolas", 11), border_width=1, border_color="#333333",
    )
    self.loading_log.insert("0.0", "[+] Login ready. Waiting for action...\n")
    self.loading_log.configure(state="disabled")
    
    self.loading_log.tag_config("success", foreground="#00FF00")
    self.loading_log.tag_config("error", foreground="#FF4444")
    self.loading_log.tag_config("engine", foreground="#FFB84D")
    self.loading_log.tag_config("ui", foreground="#BB86FC")

    def append_loading_log(message, tag=None):
        try:
            self.loading_log.configure(state="normal")
            if tag:
                self.loading_log.insert("end", message + "\n", tag)
            else:
                self.loading_log.insert("end", message + "\n")
            self.loading_log.see("end")
            self.loading_log.configure(state="disabled")
        except:
            pass

    # --- THE ENGINE BACKGROUND THREAD ---
    def background_engine_load():
        try:
            set_engine_starting(True)
            
            # 1. Load STT Engine
            append_loading_log("[+] Loading Whisper...", "engine")
            self.temp_engine = STTEngine(model_size="medium")
            self.temp_engine.load_engine_to_vram()
            
            # 2. Load LLM Engine
            append_loading_log("[+] Loading Qwen LLM...", "engine")
            self.temp_llm = LLMEngine() 
            
            # 3. Load TTS Engine  <--- WE NOW INITIALIZE TTS HERE
            append_loading_log("[+] Loading Edge-TTS...", "engine")
            self.temp_tts = TTSEngine() 
            
            self.engine_load_success = True
        except Exception as e:
            print(f"Engine load error: {e}")
            self.engine_load_success = False
        finally:
            set_engine_starting(False)
            self.engine_load_finished = True

    # --- UI POLLING LOOP ---
    def check_engine_loaded():
        if self.engine_load_finished:
            if self.engine_load_success:
                append_loading_log("[+] Engines loaded to VRAM", "engine")
                set_engine(self.temp_engine) # Save globally
                
                # Start ALL listening loops in background threads
                append_loading_log("[+] Starting microphone...", "success")
                threading.Thread(target=self.temp_engine.start_listening, daemon=True).start()
                
                append_loading_log("[+] Starting LLM Polling...", "success")
                threading.Thread(target=self.temp_llm.start_polling, daemon=True).start()
                
                # START TTS POLLING  <--- WE NOW START THE TTS ENGINE LOOP HERE
                append_loading_log("[+] Starting TTS Engine...", "success")
                threading.Thread(target=self.temp_tts.start_polling, daemon=True).start() 
                
                self.after(500, finish_login)
            else:
                append_loading_log("[X] Engines failed to load", "error")
                self.loading_status.configure(text="Engine Load Failed", text_color="#FF3333")
                self.after(2000, self.reset_login_ui)
        else:
            # Check again in 300ms if not finished
            self.after(300, check_engine_loaded)

    # --- LOGIN TRANSITION LOGIC ---
    def handle_login_click(event=None):
        if self.is_authenticating: return
        self.is_authenticating = True
        self.engine_load_finished = False
        self.engine_load_success = False
        
        self.username_entry.pack_forget()
        self.password_entry.pack_forget()
        self.toggle_btn.place_forget()
        self.login_btn.pack_forget()
        
        self.title_label.configure(text="AUTHENTICATING...")
        self.loading_bar.pack(pady=(0, 10))
        self.loading_status.pack(pady=(0, 10))
        self.loading_log.pack(pady=(0, 20), padx=50)
        self.loading_bar.start()
        
        append_loading_log("[+] Checking credentials...")
        self.after(500, execute_login)

    def execute_login():
        if verify_login(self):
            append_loading_log("[+] Credentials verified", "success")
            self.title_label.configure(text="LOADING...")  
            self.loading_status.configure(text="Booting AI Engines to VRAM...", text_color="#FFD700")
            # Start the heavy loading in the background
            threading.Thread(target=background_engine_load, daemon=True).start()
            # Start checking if it's done
            self.after(300, check_engine_loaded)
        else:
            append_loading_log("[X] Credentials verification failed", "error")
            self.title_label.configure(text="AUTHENTICATING...")  
            self.loading_status.configure(text="Invalid credentials", text_color="#FF3333")
            self.after(1200, self.reset_login_ui)

    def finish_login():
        self.loading_bar.stop()
        append_loading_log("[+] UI loaded", "ui")
        append_loading_log("[+] Entering dashboard...", "success")
        self.loading_status.configure(text="✓ Ready! Loading dashboard...", text_color="#00FF00")
        def transition():
            self.login_frame.destroy()
            dashboard_gui(self)
        self.after(600, transition)

    def reset_login_ui():
        self.is_authenticating = False 
        self.loading_bar.pack_forget()
        self.loading_status.pack_forget()
        self.loading_log.pack_forget()
        self.title_label.configure(text="SYSTEM ACCESS")
        self.username_entry.pack(pady=(0, 20), padx=50)
        self.password_entry.pack(pady=(0, 30), padx=50)
        self.toggle_btn.place(in_=self.password_entry, relx=0.92, rely=0.5, anchor="center")
        self.login_btn.pack(pady=(0, 40), padx=50)
        self.loading_log.configure(state="normal")
        self.loading_log.delete("0.0", "end")
        self.loading_log.insert("0.0", "[+] Login ready. Waiting for action...\n")
        self.loading_log.configure(state="disabled")
        self.loading_status.configure(text="Verifying secure connection...", text_color="gray")
        
    self.reset_login_ui = reset_login_ui

    self.password_entry.bind("<Return>", handle_login_click)
    self.username_entry.bind("<Return>", handle_login_click)
    
    self.login_btn = ctk.CTkButton(
        self.login_frame, text="AUTHENTICATE", width=280, height=45, 
        font=("Segoe UI", 18, 'bold'), fg_color="#D32F2F", hover_color="#0FB652",  
        command=handle_login_click
    )
    self.login_btn.pack(pady=(0, 40), padx=50)

    self.footer_label = ctk.CTkLabel(
        self, text="vortex® 2026", font=("Consolas", 12), text_color="white"
    )
    self.footer_label.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)