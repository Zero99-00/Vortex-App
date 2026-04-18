import customtkinter as ctk
from PIL import Image
from models.logic_units.auth__ import verify_login
import os
import tkinter as tk

def auth_gui(self):
    self.title('Vortex | Authorization Page')
    self.geometry(f"1300x700+{(self.winfo_screenwidth() - 1300) // 2}+{(self.winfo_screenheight() - 700) // 2}")
    
    # --- BULLETPROOF PATH LOGIC ---
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_dir, "images", "icon.ico")
    png_path = os.path.join(base_dir, "images", "icon.png")
    
    # New Image Paths for the Eye Toggle
    eye_path = os.path.join(base_dir, "images", "eye.png")
    closed_eye_path = os.path.join(base_dir, "images", "closed_eye.png")
        
    try:
        self.iconbitmap(ico_path) 
    except:
        pass # Suppressed non-fatal terminal warnings

    # --- MAIN UI FRAME ---
    self.login_frame = ctk.CTkFrame(
        self, 
        fg_color="#121212", 
        border_color="#D32F2F", 
        border_width=2, 
        corner_radius=10
    )
    self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

    # The Logo Image
    try:
        raw_img = Image.open(png_path)
        icon_image = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(140, 90))
        self.icon_label = ctk.CTkLabel(self.login_frame, text="", image=icon_image)
        self.icon_label.pack(pady=(40, 10))
    except Exception as e:
        print(f"Frame image missing: {e}")

    self.title_label = ctk.CTkLabel(
        self.login_frame, 
        text="SYSTEM ACCESS", 
        font=("Verdana", 24, "bold"), 
        text_color="#D32F2F"
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
    
    # --- LOAD EYE IMAGES ---
    try:
        # Resize to 20x20 so it fits nicely in the entry box
        open_eye_raw = Image.open(eye_path)
        closed_eye_raw = Image.open(closed_eye_path)
        self.open_eye_img = ctk.CTkImage(light_image=open_eye_raw, dark_image=open_eye_raw, size=(20, 20))
        self.closed_eye_img = ctk.CTkImage(light_image=closed_eye_raw, dark_image=closed_eye_raw, size=(20, 20))
    except Exception as e:
        print(f"Could not load eye PNGs. Make sure eye.png and closed_eye.png exist. Error: {e}")
        self.open_eye_img = None
        self.closed_eye_img = None

    # --- THE EYE TOGGLE ---
    def toggle_password():
        if self.password_entry.cget("show") == "*":
            self.password_entry.configure(show="")
            self.toggle_btn.configure(image=self.open_eye_img) # Show Open Eye
        else:
            self.password_entry.configure(show="*")
            self.toggle_btn.configure(image=self.closed_eye_img) # Show Closed Eye

    # Set initial image to closed eye, remove text completely
    self.toggle_btn = ctk.CTkButton(
        self.login_frame, text="", image=self.closed_eye_img, width=30, height=30, 
        fg_color="#1E1E1E", bg_color="#1E1E1E", hover_color="#333333", 
        command=toggle_password
    )
    self.toggle_btn.place(in_=self.password_entry, relx=0.92, rely=0.5, anchor="center")
    
    # --- IMPROVED LOADING UI (Hidden by default) ---
    self.loading_bar = ctk.CTkProgressBar(
        self.login_frame, width=220, mode="indeterminate", progress_color="#D32F2F"
    )
    self.loading_status = ctk.CTkLabel(
        self.login_frame, text="Verifying secure connection...", 
        font=("Consolas", 12), text_color="gray"
    )

    # --- LOGIN TRANSITION LOGIC ---
    def handle_login_click(event=None):
        # 1. Hide the form fields and buttons
        self.username_entry.pack_forget()
        self.password_entry.pack_forget()
        self.toggle_btn.place_forget() 
        self.login_btn.pack_forget()
        
        # 2. Update text and show the upgraded loading sequence
        self.title_label.configure(text="AUTHENTICATING...")
        self.loading_bar.pack(pady=(0, 10))
        self.loading_status.pack(pady=(0, 30))
        self.loading_bar.start()
        
        # 3. Wait 1.5 seconds for visual effect, then run your actual auth logic
        self.after(1500, execute_login)

    def execute_login():
        self.loading_bar.stop()
        # Call your existing verify logic
        verify_login(self)

    # Clean function to restore UI if login fails
    def reset_login_ui():
        self.loading_bar.pack_forget()
        self.loading_status.pack_forget()
        self.title_label.configure(text="SYSTEM ACCESS")
        self.username_entry.pack(pady=(0, 20), padx=50)
        self.password_entry.pack(pady=(0, 30), padx=50)
        self.toggle_btn.place(in_=self.password_entry, relx=0.92, rely=0.5, anchor="center")
        self.login_btn.pack(pady=(0, 40), padx=50)
        
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