import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import speech_recognition as sr
import whisper
import os
import warnings
import colorama
import sqlite3
import torch
import time

from models.logic_units.absolute_path import get_base_path

colorama.init()
warnings.filterwarnings("ignore")

# ── Colors ──────────────────────────────────────────────────────────────────
R   = '\033[0m'
CY  = '\033[96m'
GR  = '\033[92m'
YL  = '\033[93m'
MG  = '\033[95m'
RD  = '\033[91m'
BL  = '\033[94m'
WH  = '\033[97m'
DIM = '\033[2m'
BLD = '\033[1m'

OK   = f"{GR}[OK]{R}"
FAIL = f"{YL}[--]{R}"
ERR  = f"{RD}[!!]{R}"
DOT  = f"{CY} > {R}"

def log(msg):        print(f"  {GR}[+]{R} {WH}{msg}{R}")
def log_info(msg):   print(f"  {CY}[~]{R} {msg}")
def log_warn(msg):   print(f"  {YL}[!]{R} {YL}{msg}{R}")
def log_err(msg):    print(f"  {RD}[X]{R} {RD}{msg}{R}")

def divider(color=DIM): print(f"{color}  {'─' * 52}{R}")
def section(title): print(f"\n  {BLD}{CY}{title}{R}"); divider(CY)

def banner():
    print(f"\n{RD}  ╔{'═' * 50}╗{R}")
    print(f"{RD}  ║{BLD}{'  VORTEX  VOICE  ENGINE':<50}{R}{RD}║{R}")
    print(f"{RD}  ╚{'═' * 50}╝{R}\n")

def status_row(label, value, note="", state="ok"):
    icon      = OK if state == "ok" else (FAIL if state == "warn" else ERR)
    print(f"  {DOT}{YL}{label:<16}{R}{WH}{value:<24}{R}  {icon}  {DIM}{note}{R}")

def vram_bar(used, total, width=18):
    ratio  = used / total if total > 0 else 0
    filled = int(ratio * width)
    color  = GR if ratio < 0.6 else (YL if ratio < 0.85 else RD)
    return f"[{color}{'█' * filled}{DIM}{'░' * (width - filled)}{R}] {color}{ratio*100:.0f}%{R}  {WH}{used:.2f}{DIM}/{total:.1f} GB{R}"

class STTEngine:
    def __init__(self, model_size="medium"):
        self.model_size = model_size
        self.model = None
        self.target_language = None
        self.call_count = 0
        self.is_running = False 
        self.auto_restart_triggered = False 
        self.current_state = "INITIALIZING..." # Added back for your UI
        
        self.r = sr.Recognizer()
        self.r.dynamic_energy_threshold = True
        self.r.pause_threshold = 1.0
        self.r.non_speaking_duration = 0.5
        
        self.use_fp16 = False
        self.device = "cpu"
        self.vram_total = 0.0

        banner()
        self._detect_hardware()
        self._print_audio_status()
        self._init_database()

    def _init_database(self):
        # FIXED: Matching LLM database name
        self.db_path = os.path.join(get_base_path(), "engine_core.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # FIXED: Matching LLM table format
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_query TEXT,
                ai_response TEXT,
                is_spoken INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("DELETE FROM conversation_logs")
        self.conn.commit()
        status_row("Database", "engine_core.db", "wiped and ready", "ok")

    def _store_in_db(self, text):
        if not text: return
        cursor = self.conn.cursor()
        # FIXED: Insert as user_query and set AI to thinking
        cursor.execute("INSERT INTO conversation_logs (user_query, ai_response) VALUES (?, ?)", (text, "thinking..."))
        cursor.execute("DELETE FROM conversation_logs WHERE id NOT IN (SELECT id FROM conversation_logs ORDER BY id DESC LIMIT 50)")
        self.conn.commit()

    def _detect_hardware(self):
        section("HARDWARE")
        if torch.cuda.is_available():
            self.vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            self.device     = "cuda"
            self.use_fp16   = True
            status_row("GPU", torch.cuda.get_device_name(0), "CUDA detected", "ok")
        else:
            status_row("GPU", "Not found", "CUDA unavailable", "warn")

    def _print_audio_status(self):
        section("AUDIO PIPELINE")
        status_row("Filter", "Whisper Defaults", "pure detection", "ok")
        status_row("Timeout", "60 Seconds", "auto-restart enabled", "ok")

    def load_engine_to_vram(self):
        section("MODEL")
        log_info(f"Loading Whisper {BLD}{self.model_size}{R} — please wait...")
        self.model = whisper.load_model(self.model_size, device=self.device, in_memory=True)

        if self.device == "cuda":
            torch.cuda.empty_cache()
            status_row("Model", f"Whisper {self.model_size}", "ready", "ok")

    def stop(self):
        self.is_running = False
        self.current_state = "OFFLINE" # Added back for your UI
        print(f"\n{YL}>> ENGINE STOP SIGNAL SENT. WAITING FOR SAFE EXIT...{R}\n")

    def _get_target_language(self, source):
        self.current_state = "CHOOSING LANGUAGE..." # Added back for your UI
        while self.target_language is None and self.is_running:
            print(f"\n  {MG}[?]{R} {BLD}Say your language:{R} {GR}English{R} or {YL}Arabic{R} ...")
            try:
                lang_audio = self.r.listen(source, timeout=3, phrase_time_limit=5)
                with open("temp_lang.wav", "wb") as f: f.write(lang_audio.get_wav_data())

                lang_text = self.model.transcribe("temp_lang.wav", language="en", fp16=self.use_fp16)['text'].lower().strip()
                os.remove("temp_lang.wav")

                if lang_text:
                    log_info(f"Heard: {CY}'{lang_text}'{R}")

                if "arabic" in lang_text or "عربي" in lang_text:
                    self.target_language = "ar"
                    status_row("Language", "ARABIC", "native mode", "ok")
                elif "english" in lang_text:
                    self.target_language = "en"
                    status_row("Language", "ENGLISH", "standard", "ok")

            except sr.WaitTimeoutError:
                pass 
            except Exception as e:
                log_err(f"Language detection issue: {e}")

    def start_listening(self):
        if not self.model: return log_err("Call load_engine_to_vram() first.")
        
        self.is_running = True
        self.auto_restart_triggered = False

        with sr.Microphone() as source:
            section("MICROPHONE")
            log_info("Calibrating for ambient noise — stay quiet for 2s...")
            self.current_state = "CALIBRATING..." # Added back for your UI
            self.r.adjust_for_ambient_noise(source, duration=2.0)
            status_row("Microphone", "Calibrated", "locked", "ok")

            self._get_target_language(source)

            if not self.is_running:
                return log_info("Engine stopped before entering main loop.")

            lang_label = "AR" if self.target_language == "ar" else "EN"

            print(f"\n{RD}  ╔{'═' * 50}╗{R}")
            print(f"{RD}  ║{BLD}{f'  LISTENING ACTIVE  [{lang_label}]':<50}{R}{RD}║{R}")
            print(f"{RD}  ╚{'═' * 50}╝{R}")

            last_speech_time = time.time()

            while self.is_running:
                if time.time() - last_speech_time > 60:
                    log_warn("1 Minute of Absolute Silence. Triggering Auto-Restart...")
                    self.is_running = False
                    self.auto_restart_triggered = True
                    break

                try:
                    divider(MG)
                    log_info("Waiting for speech...")
                    self.current_state = "LISTENING..." # Added back for your UI
                    
                    audio = self.r.listen(source, timeout=1, phrase_time_limit=10)

                    if not self.is_running: break

                    self.current_state = "PROCESSING..." # Added back for your UI
                    if self.device == "cuda": torch.cuda.empty_cache()
                    log_info("Transcribing...")

                    with open("temp_voice.wav", "wb") as f:
                        f.write(audio.get_wav_data())

                    result = self.model.transcribe(
                        "temp_voice.wav", 
                        language=self.target_language,
                        fp16=self.use_fp16
                    )

                    valid_text_blocks = []
                    for segment in result.get("segments", []):
                        no_speech = segment.get("no_speech_prob", 0)
                        txt = segment.get("text", "").strip()

                        if no_speech < 0.6 and len(txt) > 2:
                            valid_text_blocks.append(txt)
                            
                    final_text = " ".join(valid_text_blocks).strip()
                    os.remove("temp_voice.wav")

                    if final_text:
                        last_speech_time = time.time() 
                        self.call_count += 1
                        self._store_in_db(final_text)

                        if self.device == "cuda":
                            print(f"  {CY}  VRAM{R}  {vram_bar(torch.cuda.memory_allocated(0)/(1024**3), self.vram_total)}")

                        print(f"\n  {GR}╭{'─' * 50}{R}")
                        print(f"  {GR}│{R}  {BLD}{WH}{final_text}{R}")
                        print(f"  {GR}╰{'─' * 50}{R}")
                        print(f"  {DIM}  call #{self.call_count} · {lang_label} · DB Saved{R}\n")

                except sr.WaitTimeoutError:
                    pass 
                except Exception as e:
                    log_err(f"Transcription error: {e}")
            
            self.current_state = "OFFLINE" # Added back for your UI
            print(f"\n{RD}>> ENGINE SUCCESSFULLY OFFLINE.{R}\n")