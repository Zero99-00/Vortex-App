import customtkinter as ctk
import sqlite3

class QAPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#121212", corner_radius=15)
        
        self.current_edit_id = None
        self.init_db()

        ctk.CTkLabel(self, text="🧠 KNOWLEDGE BASE", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=40, pady=(40, 20))
        
        self.q_entry = ctk.CTkEntry(self, placeholder_text="Enter Question...", font=("Segoe UI", 16), width=600, height=45)
        self.q_entry.pack(anchor="w", padx=40, pady=10)
        
        self.a_entry = ctk.CTkEntry(self, placeholder_text="Enter Answer...", font=("Segoe UI", 16), width=600, height=45)
        self.a_entry.pack(anchor="w", padx=40, pady=10)
        
        self.save_btn = ctk.CTkButton(self, text="SAVE", fg_color="#D32F2F", hover_color="#B71C1C", font=("Segoe UI", 14, "bold"), height=40, command=self.save_query)
        self.save_btn.pack(anchor="w", padx=40, pady=20)

        ctk.CTkLabel(self, text="DATABASE RECORDS", font=("Segoe UI", 18, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=40, pady=(20, 10))

        self.records_frame = ctk.CTkScrollableFrame(self, fg_color="#050505", corner_radius=10)
        self.records_frame.pack(expand=True, fill="both", padx=40, pady=(0, 40))

        self.load_queries()

    def init_db(self):
        conn = sqlite3.connect("lamma_aq.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def save_query(self):
        q_text = self.q_entry.get().strip()
        a_text = self.a_entry.get().strip()

        if q_text and a_text:
            conn = sqlite3.connect("lamma_aq.db")
            cursor = conn.cursor()
            
            if self.current_edit_id is None:
                cursor.execute("INSERT INTO knowledge_base (question, answer) VALUES (?, ?)", (q_text, a_text))
            else:
                cursor.execute("UPDATE knowledge_base SET question = ?, answer = ? WHERE id = ?", (q_text, a_text, self.current_edit_id))
                self.current_edit_id = None
                self.save_btn.configure(text="SAVE")
                
            conn.commit()
            conn.close()

            self.q_entry.delete(0, "end")
            self.a_entry.delete(0, "end")
            self.load_queries()

    def load_for_edit(self, record_id, q_text, a_text):
        self.current_edit_id = record_id
        self.q_entry.delete(0, "end")
        self.q_entry.insert(0, q_text)
        self.a_entry.delete(0, "end")
        self.a_entry.insert(0, a_text)
        self.save_btn.configure(text="UPDATE RECORD")

    def delete_query(self, record_id):
        conn = sqlite3.connect("lamma_aq.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_base WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        
        if self.current_edit_id == record_id:
            self.current_edit_id = None
            self.q_entry.delete(0, "end")
            self.a_entry.delete(0, "end")
            self.save_btn.configure(text="SAVE")
            
        self.load_queries()

    def load_queries(self):
        for widget in self.records_frame.winfo_children():
            widget.destroy()

        conn = sqlite3.connect("lamma_aq.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, answer FROM knowledge_base ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            record_id, q_text, a_text = row[0], row[1], row[2]
            
            item_frame = ctk.CTkFrame(self.records_frame, fg_color="#1A1A1A", corner_radius=8)
            item_frame.pack(fill="x", padx=10, pady=5)
            
            text_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True)
            
            btn_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            btn_frame.pack(side="right", padx=15, pady=10)
            
            ctk.CTkLabel(text_frame, text=f"Q: {q_text}", font=("Segoe UI", 16, "bold"), text_color="#D32F2F", anchor="w", justify="left", wraplength=550).pack(fill="x", padx=15, pady=(10, 2))
            ctk.CTkLabel(text_frame, text=f"A: {a_text}", font=("Segoe UI", 14), text_color="white", anchor="w", justify="left", wraplength=550).pack(fill="x", padx=15, pady=(0, 10))
            
            ctk.CTkButton(btn_frame, text="✏️ Edit", width=70, fg_color="#333333", hover_color="#555555", font=("Segoe UI", 12, "bold"), command=lambda r=record_id, q=q_text, a=a_text: self.load_for_edit(r, q, a)).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="🗑️ Delete", width=70, fg_color="#333333", hover_color="#D32F2F", font=("Segoe UI", 12, "bold"), command=lambda r=record_id: self.delete_query(r)).pack(side="left", padx=5)