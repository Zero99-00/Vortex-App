import customtkinter as ctk
import sqlite3
import bcrypt
import subprocess
import os

# --- BULLETPROOF PATH RESOLVER ---
def get_image_path(filename):
    """Automatically finds the absolute path to the Vortex/images folder."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(models_dir)
    return os.path.join(root_dir, "images", filename)

# --- DATABASE SETUP ---
def ensure_default_admin():
    """Initializes the database and guarantees 'admin':'admin' exists."""
    conn = sqlite3.connect("robot_dashboard.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", hashed))
    conn.commit()
    conn.close()

# --- WINDOWS NETWORK CHECKER ---
def get_network_name():
    """Checks Windows for the current Wi-Fi SSID or LAN status."""
    try:
        output = subprocess.check_output("netsh wlan show interfaces", shell=True, text=True)
        for line in output.split('\n'):
            if " Profile " in line or " SSID " in line:
                if "BSSID" not in line: 
                    return line.split(":")[1].strip()
        return "Ethernet / LAN"
    except Exception:
        return "Disconnected / Unknown"

# --- MAIN UI CLASS ---
class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#0A0A0A", corner_radius=15)
        
        ensure_default_admin()
        
        # Security Variables for Lockout
        self.login_attempts = 0
        self.lockout_time_left = 0
        
        # 1. Your Requested Fonts Applied
        self.font_main = ("Segoe UI", 18, "bold")
        self.font_title = ("Segoe UI", 24, "bold")
        self.font_body = ("Segoe UI", 14)
        
        # 2. Colors
        self.color_red = "#D32F2F"
        self.color_red_hover = "#B71C1C"
        self.color_green = "#2E7D32"
        self.color_green_hover = "#1B5E20"
        self.color_surface = "#1E1E1E"
        self.color_blue = "#1976D2"
        
        # Header
        ctk.CTkLabel(self, text="⚙️ SYSTEM CONFIGURATION", font=self.font_title, text_color="white").pack(anchor="w", padx=40, pady=(30, 10))
        self.alert_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 12, "italic"))
        self.alert_label.pack(anchor="w", padx=40, pady=(0, 10))
        
        self.create_robot_connection_section()
        self.create_user_management_section()

    def show_alert(self, message, is_success=True):
        color = self.color_green if is_success else self.color_red
        self.alert_label.configure(text=message, text_color=color)
        self.after(4000, lambda: self.alert_label.configure(text=""))

    def create_robot_connection_section(self):
        robot_frame = ctk.CTkFrame(self, fg_color="transparent")
        robot_frame.pack(anchor="w", padx=40, pady=10, fill="x")
        
        header_frame = ctk.CTkFrame(robot_frame, fg_color="transparent")
        header_frame.pack(anchor="w", fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header_frame, text="🤖 Robot Connection", font=self.font_main, text_color="white").pack(side="left")
        
        network_name = get_network_name()
        ctk.CTkLabel(header_frame, text=f"📶 Network: {network_name}", font=self.font_body, text_color="#64B5F6").pack(side="right", padx=10)
        
        self.robot_ip = ctk.CTkEntry(robot_frame, placeholder_text="Robot IP Address", font=self.font_body, width=250, fg_color=self.color_surface)
        self.robot_ip.pack(anchor="w", pady=5)
        
        self.robot_pass = ctk.CTkEntry(robot_frame, placeholder_text="Robot Password", font=self.font_body, show="*", width=250, fg_color=self.color_surface)
        self.robot_pass.pack(anchor="w", pady=5)
        
        btn_frame = ctk.CTkFrame(robot_frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=10)
        
        ctk.CTkButton(btn_frame, text="Connect", font=self.font_main, fg_color=self.color_red, hover_color=self.color_red_hover, width=120).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Auto Connect", font=self.font_main, fg_color=self.color_green, hover_color=self.color_green_hover, width=120).pack(side="left")

    def create_user_management_section(self):
        self.user_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.user_frame.pack(anchor="w", padx=40, pady=10, fill="x")
        
        ctk.CTkLabel(self.user_frame, text="👥 User Management", font=self.font_main, text_color="white").pack(anchor="w", pady=(0, 10))
        
        # --- LOGIN GATE ---
        self.login_frame = ctk.CTkFrame(self.user_frame, fg_color=self.color_surface, corner_radius=10)
        self.login_frame.pack(anchor="w", fill="x", pady=5, ipadx=10, ipady=15)
        
        self.admin_user = ctk.CTkEntry(self.login_frame, placeholder_text="Admin Username", font=self.font_body, width=250)
        self.admin_user.pack(pady=5)
        self.admin_pass = ctk.CTkEntry(self.login_frame, placeholder_text="Admin Password", font=self.font_body, show="*", width=250)
        self.admin_pass.pack(pady=5)
        
        self.login_btn = ctk.CTkButton(self.login_frame, text="Login to Unlock", font=self.font_main, fg_color=self.color_red, hover_color=self.color_red_hover, command=self.attempt_login)
        self.login_btn.pack(pady=10)
        
        self.lockout_label = ctk.CTkLabel(self.login_frame, text="", font=self.font_body, text_color=self.color_red)
        self.lockout_label.pack()
        
        # --- SECURE MANAGEMENT AREA (Hidden until login) ---
        self.manage_frame = ctk.CTkFrame(self.user_frame, fg_color="transparent")
        
        add_frame = ctk.CTkFrame(self.manage_frame, fg_color=self.color_surface, corner_radius=10)
        add_frame.pack(fill="x", pady=(0, 15), ipadx=10, ipady=10)
        
        self.new_user_name = ctk.CTkEntry(add_frame, placeholder_text="New Username", font=self.font_body, width=150)
        self.new_user_name.pack(side="left", padx=5)
        self.new_user_pass = ctk.CTkEntry(add_frame, placeholder_text="Password", font=self.font_body, show="*", width=150)
        self.new_user_pass.pack(side="left", padx=5)
        ctk.CTkButton(add_frame, text="+ Add", font=self.font_main, fg_color=self.color_green, hover_color=self.color_green_hover, width=80, command=self.add_user).pack(side="left", padx=5)
        
        self.user_list_box = ctk.CTkScrollableFrame(self.manage_frame, fg_color=self.color_surface, height=200, corner_radius=10)
        self.user_list_box.pack(fill="x", expand=True)

    # --- LOCKOUT LOGIC ---
    def run_lockout_timer(self):
        if self.lockout_time_left > 0:
            minutes, seconds = divmod(self.lockout_time_left, 60)
            self.lockout_label.configure(text=f"SYSTEM LOCKED. Try again in {minutes}m {seconds}s")
            self.lockout_time_left -= 1
            self.after(1000, self.run_lockout_timer)
        else:
            self.lockout_label.configure(text="")
            self.login_attempts = 0
            self.login_btn.configure(state="normal", fg_color=self.color_red)

    # --- LOGIC ---
    def attempt_login(self):
        if self.lockout_time_left > 0:
            return 
            
        username = self.admin_user.get()
        password = self.admin_pass.get().encode('utf-8')
        
        conn = sqlite3.connect("robot_dashboard.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result and bcrypt.checkpw(password, result[0]):
            self.login_attempts = 0 
            self.show_alert("Login Successful!", True)
            self.login_frame.pack_forget() 
            self.manage_frame.pack(anchor="w", fill="x", pady=5)
            self.refresh_user_list()
        else:
            self.login_attempts += 1
            attempts_left = 4 - self.login_attempts
            
            if attempts_left <= 0:
                self.lockout_time_left = 300 # 5 minutes
                self.login_btn.configure(state="disabled", fg_color="#333333")
                self.show_alert("TOO MANY FAILED ATTEMPTS.", False)
                self.run_lockout_timer()
            else:
                self.show_alert(f"Access Denied. {attempts_left} attempts left.", False)

    def refresh_user_list(self):
        for widget in self.user_list_box.winfo_children():
            widget.destroy()
            
        conn = sqlite3.connect("robot_dashboard.db")
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()
        conn.close()

        for user in users:
            username = user[0]
            row = ctk.CTkFrame(self.user_list_box, fg_color="transparent")
            row.pack(fill="x", pady=5, padx=5)
            
            ctk.CTkLabel(row, text=f"👤 {username}", font=self.font_body, text_color="white").pack(side="left")
            
            del_btn = ctk.CTkButton(row, text="Delete", font=self.font_main, width=80, fg_color=self.color_red, hover_color=self.color_red_hover, command=lambda u=username: self.delete_user(u))
            del_btn.pack(side="right", padx=(5, 0))
            
            edit_btn = ctk.CTkButton(row, text="Edit", font=self.font_main, width=80, fg_color=self.color_blue, hover_color="#1565C0", command=lambda u=username: self.prompt_edit_user(u))
            edit_btn.pack(side="right")

    def add_user(self):
        username = self.new_user_name.get()
        password = self.new_user_pass.get().encode('utf-8')
        
        if not username or not password:
            self.show_alert("Fields cannot be empty!", False)
            return
            
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        
        try:
            conn = sqlite3.connect("robot_dashboard.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            conn.commit()
            self.show_alert(f"User '{username}' added!", True)
            self.new_user_name.delete(0, 'end')
            self.new_user_pass.delete(0, 'end')
            self.refresh_user_list()
        except sqlite3.IntegrityError:
            self.show_alert(f"User '{username}' already exists!", False)
        finally:
            conn.close()

    # --- THE NEW CUSTOM POPUP UI ---
    def prompt_edit_user(self, username):
        """Spawns a compact, centered popup without a logo to edit the password."""
        popup = ctk.CTkToplevel(self)
        popup.title("Vortex | Edit Password")
        
        # Height drastically reduced to 200
        p_width, p_height = 400, 200
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = (screen_w - p_width) // 2
        pos_y = (screen_h - p_height) // 2
        popup.geometry(f"{p_width}x{p_height}+{pos_x}+{pos_y}")
        
        popup.configure(fg_color="#121212")
        popup.grab_set() 
        popup.focus()
        
        # Apply corner icon
        ico_path = get_image_path("icon.ico")
        try:
            popup.after(200, lambda: popup.iconbitmap(ico_path))
        except Exception:
            pass 

        # UI Elements with Segoe UI, 18, bold
        ctk.CTkLabel(popup, text=f"EDIT {username.upper()}", font=("Segoe UI", 18, "bold"), text_color="#D32F2F").pack(pady=(20, 10))
        
        new_pass = ctk.CTkEntry(popup, font=("Segoe UI", 14), placeholder_text="New Password", show="*", width=250, height=35, fg_color="#1E1E1E")
        new_pass.pack(pady=5)
        
        def submit_change():
            password_str = new_pass.get()
            if not password_str:
                return
                
            hashed = bcrypt.hashpw(password_str.encode('utf-8'), bcrypt.gensalt())
            conn = sqlite3.connect("robot_dashboard.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, username))
            conn.commit()
            conn.close()
            
            self.show_alert(f"Password updated for '{username}'", True)
            popup.destroy() 

        # Submit button using Segoe UI, 18, bold
        ctk.CTkButton(popup, text="SUBMIT CHANGE", font=("Segoe UI", 18, "bold"), fg_color="#D32F2F", hover_color="#0FB652", width=250, height=40, command=submit_change).pack(pady=(10, 20))

    def delete_user(self, username):
        if username == "admin":
            self.show_alert("Cannot delete default admin!", False)
            return
            
        conn = sqlite3.connect("robot_dashboard.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        
        self.show_alert(f"User '{username}' deleted.", True)
        self.refresh_user_list()

# --- RUNNING THE APP DIRECTLY FOR TESTING ---
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("650x700")
    app.title("Vortex | Dashboard")
    ctk.set_appearance_mode("dark")
    
    try:
        app.iconbitmap(get_image_path("icon.ico"))
    except:
        pass
    
    panel = SettingsPanel(app)
    panel.pack(fill="both", expand=True, padx=20, pady=20)
    
    app.mainloop()