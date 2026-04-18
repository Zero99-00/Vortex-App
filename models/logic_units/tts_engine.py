import sqlite3
import time
import os
import asyncio
import edge_tts
import pygame
from models.logic_units.absolute_path import get_base_path

class TTSEngine:
    def __init__(self):
        # FIXED: Changed from "stt_store.db" to "engine_core.db" to match LLM and STT
        self.db_path = os.path.join(get_base_path(), "engine_core.db")
        
        # Voice Settings
        self.voices = {
            "en": "en-US-GuyNeural",
            "ar": "ar-EG-ShakirNeural"
        }
        
        # Initialize Audio Player
        pygame.mixer.init()
        self._ensure_column_exists()

    def _ensure_column_exists(self):
        """Adds a 'spoken' flag so the AI doesn't repeat itself forever."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("ALTER TABLE conversation_logs ADD COLUMN is_spoken INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass # Column already exists

    def _is_arabic(self, text):
        """Simple check if the text contains Arabic characters."""
        return any("\u0600" <= char <= "\u06FF" for char in text)

    def _check_for_interruption(self, current_id):
        """Checks the DB to see if a newer response arrived while speaking."""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM conversation_logs 
                    WHERE ai_response != 'thinking...' 
                    AND ai_response IS NOT NULL 
                    AND is_spoken = 0
                    AND id > ?
                    LIMIT 1
                """, (current_id,))
                return cursor.fetchone() is not None
        except Exception:
            return False

    async def _generate_and_play(self, row_id, text):
        """Generates voice, plays it, and actively listens for interruptions."""
        lang = "ar" if self._is_arabic(text) else "en"
        voice = self.voices[lang]
        
        print(f"\n[TTS] Speaking ({lang.upper()}): {text[:50]}...")
        
        # Use dynamic filenames to avoid Pygame file-lock crashes
        temp_audio = f"reply_{row_id}.mp3"
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_audio)

        try:
            pygame.mixer.music.load(temp_audio)
            pygame.mixer.music.play()
            
            # Active wait loop: check for new messages while playing
            while pygame.mixer.music.get_busy():
                if self._check_for_interruption(row_id):
                    print("\n[TTS] New answer detected! Suspending current speech...")
                    pygame.mixer.music.stop()
                    break # Break out of the loop to process the new message
                
                await asyncio.sleep(0.1)
                
        finally:
            # Cleanup process
            pygame.mixer.music.unload()
            await asyncio.sleep(0.1) # Brief pause to let OS release the file lock
            if os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except OSError as e:
                    print(f"[TTS] Warning: Could not delete {temp_audio}: {e}")

    async def _poll_loop(self):
        """Asynchronous database polling loop."""
        print("[TTS] Voice output engine started... Monitoring replies.")
        
        while True:
            try:
                with sqlite3.connect(self.db_path, timeout=10) as conn:
                    cursor = conn.cursor()
                    
                    # ORDER BY id ASC ensures we process the oldest unspoken message first, 
                    # unless interrupted
                    cursor.execute("""
                        SELECT id, ai_response FROM conversation_logs 
                        WHERE ai_response != 'thinking...' 
                        AND ai_response IS NOT NULL 
                        AND is_spoken = 0
                        ORDER BY id ASC
                        LIMIT 1
                    """)
                    row = cursor.fetchone()

                    if row:
                        row_id, reply_text = row
                        
                        # 1. Mark as spoken IMMEDIATELY so we don't repeat it if interrupted
                        cursor.execute("UPDATE conversation_logs SET is_spoken = 1 WHERE id = ?", (row_id,))
                        conn.commit()
                        
                        # 2. Generate and play (handles its own interruptions)
                        await self._generate_and_play(row_id, reply_text)
                        
            except Exception as e:
                print(f"[TTS] Error: {e}")
            
            await asyncio.sleep(0.5)

    def start_polling(self):
        """Starts the asynchronous loop cleanly."""
        try:
            asyncio.run(self._poll_loop())
        except KeyboardInterrupt:
            print("\n[TTS] Engine stopped by user.")