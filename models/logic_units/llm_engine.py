import sqlite3
import time
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from models.logic_units.absolute_path import get_base_path

class LLMEngine:
    def __init__(self, model_name="Qwen/Qwen2.5-0.5B-Instruct"):
        self.main_db = os.path.join(get_base_path(), "engine_core.db")
        self.kb_db = os.path.join(get_base_path(), "lamma_aq.db")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"[LLM] Loading AI Model to {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype="auto", device_map="auto"
        )
        
        self._ensure_table_exists() # CRITICAL: Fixes your "No such table" error
        self.knowledge_context = self._load_knowledge()

    def _ensure_table_exists(self):
        """Creates the table if it doesn't exist yet to prevent polling crashes."""
        conn = sqlite3.connect(self.main_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_query TEXT,
                ai_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _load_knowledge(self):
        context_str = ""
        try:
            conn = sqlite3.connect(self.kb_db)
            cursor = conn.cursor()
            cursor.execute("SELECT question, answer FROM knowledge_base")
            rows = cursor.fetchall()
            conn.close()
            for q, a in rows:
                context_str += f"Q: {q}\nA: {a}\n\n"
            print(f"[LLM] Knowledge Base Loaded ({len(rows)} facts)")
        except Exception as e:
            print(f"[LLM] Knowledge Base error: {e}")
        return context_str

    def generate_response(self, user_text):
        system_instruction = (
            "You are Vortex AI, a robotic assistant. "
            "STRICT RULE: Use ONLY the provided Knowledge Base below to answer. "
            "If the answer is NOT in the Knowledge Base, say exactly: 'Information not found.' "
            "IF THE USER SAID SOMETHING TO U NOT IN THE DATABASE SAY I DON'T RESPOND TO THAT"
            "Do NOT use your internal training.\n\n"
            "YOUR CREATOR IS ZERO DON'T FORGET "
            f"{self.knowledge_context}"
        )
        messages = [{"role": "system", "content": system_instruction}, {"role": "user", "content": user_text}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        
        generated_ids = self.model.generate(
            model_inputs.input_ids, 
            max_new_tokens=150, 
            temperature=0.1, 
            do_sample=True
        )
        return self.tokenizer.batch_decode(generated_ids[:, model_inputs.input_ids.shape[-1]:], skip_special_tokens=True)[0].strip()

    def start_polling(self):
        print("[LLM] Monitoring conversation logs for new queries...")
        while True:
            try:
                conn = sqlite3.connect(self.main_db)
                cursor = conn.cursor()
                # Look for rows where user spoke but AI hasn't answered
                cursor.execute("SELECT id, user_query FROM conversation_logs WHERE ai_response = 'thinking...'")
                new_tasks = cursor.fetchall()
                
                for row_id, text in new_tasks:
                    print(f"[LLM] Processing: {text}")
                    reply = self.generate_response(text)
                    
                    # Update the SAME row with the answer
                    cursor.execute("UPDATE conversation_logs SET ai_response = ? WHERE id = ?", (reply, row_id))
                    conn.commit()
                    print(f"[LLM] AI Reply Saved: {reply}")
                
                conn.close()
            except Exception as e:
                # Silently wait if DB is locked briefly
                pass 
            time.sleep(0.5)