import sys
sys.stdout.reconfigure(encoding='utf-8')

import speech_recognition as sr
import whisper
import os
import warnings
import colorama
import io
import numpy as np
from scipy.io import wavfile
import noisereduce as nr
import torch

colorama.init()
warnings.filterwarnings("ignore")

# ── Colors ──────────────────────────────────────────────────────────────────
R   = '\033[0m'           # reset
CY  = '\033[96m'          # cyan
GR  = '\033[92m'          # green
YL  = '\033[93m'          # yellow
MG  = '\033[95m'          # magenta
RD  = '\033[91m'          # red
BL  = '\033[94m'          # blue
WH  = '\033[97m'          # white
DIM = '\033[2m'           # dim
BLD = '\033[1m'           # bold

# ── Status symbols ───────────────────────────────────────────────────────────
OK   = f"{GR}[OK]{R}"
FAIL = f"{YL}[--]{R}"
ERR  = f"{RD}[!!]{R}"
DOT  = f"{CY} > {R}"

# ── Inline log helpers ───────────────────────────────────────────────────────
def log(msg):        print(f"  {GR}[+]{R} {WH}{msg}{R}")
def log_info(msg):   print(f"  {CY}[~]{R} {msg}")
def log_warn(msg):   print(f"  {YL}[!]{R} {YL}{msg}{R}")
def log_err(msg):    print(f"  {RD}[X]{R} {RD}{msg}{R}")

def divider(color=DIM):
    print(f"{color}  {'─' * 52}{R}")

def section(title):
    print(f"\n  {BLD}{CY}{title}{R}")
    divider(CY)

# ── Startup banner ───────────────────────────────────────────────────────────
def banner():
    print(f"\n{MG}  ╔{'═' * 50}╗{R}")
    print(f"{MG}  ║{BLD}{'  VORTEX  VOICE  ENGINE':<50}{R}{MG}║{R}")
    print(f"{MG}  ╚{'═' * 50}╝{R}\n")

# ── Status row ───────────────────────────────────────────────────────────────
def status_row(label, value, note="", state="ok"):
    icon      = OK if state == "ok" else (FAIL if state == "warn" else ERR)
    label_col = f"{YL}{label:<16}{R}"
    value_col = f"{WH}{value:<24}{R}"
    note_col  = f"{DIM}{note}{R}" if note else ""
    print(f"  {DOT}{label_col}{value_col}  {icon}  {note_col}")

# ── VRAM bar ─────────────────────────────────────────────────────────────────
def vram_bar(used, total, width=18):
    ratio  = used / total if total > 0 else 0
    filled = int(ratio * width)
    empty  = width - filled
    color  = GR if ratio < 0.6 else (YL if ratio < 0.85 else RD)
    bar    = f"{color}{'█' * filled}{DIM}{'░' * empty}{R}"
    pct    = f"{color}{ratio*100:.0f}%{R}"
    return f"[{bar}] {pct}  {WH}{used:.2f}{DIM}/{total:.1f} GB{R}"


# ════════════════════════════════════════════════════════════════════════════
#  1. GPU / CPU DETECTION
# ════════════════════════════════════════════════════════════════════════════
banner()
section("HARDWARE")

USE_FP16   = False
GPU_NAME   = "None"
VRAM_TOTAL = 0.0

if torch.cuda.is_available():
    GPU_NAME   = torch.cuda.get_device_name(0)
    VRAM_TOTAL = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    DEVICE     = "cuda"
    USE_FP16   = True
    status_row("GPU",        GPU_NAME,              "CUDA detected",        "ok")
    status_row("VRAM Total", f"{VRAM_TOTAL:.1f} GB","available",            "ok")
    status_row("Precision",  "FP16 (half)",         "saves ~50% VRAM",      "ok")
    status_row("Backend",    "CUDA / GPU",          "full GPU acceleration", "ok")
else:
    DEVICE = "cpu"
    status_row("GPU",        "Not found",           "CUDA unavailable",     "warn")
    status_row("Precision",  "FP32 (full)",         "CPU mode",             "warn")
    status_row("Backend",    "CPU",                 "slower inference",     "warn")


# ════════════════════════════════════════════════════════════════════════════
#  2. LOAD WHISPER MODEL
# ════════════════════════════════════════════════════════════════════════════
section("MODEL")
log_info(f"Loading Whisper {BLD}medium{R} — please wait...")

model = whisper.load_model("medium", device=DEVICE, in_memory=True)

if DEVICE == "cuda":
    torch.cuda.empty_cache()
    used_vram = torch.cuda.memory_allocated(0) / (1024 ** 3)
    bar = vram_bar(used_vram, VRAM_TOTAL)
    status_row("Model",    "Whisper medium",  "downloaded & ready",     "ok")
    status_row("FP16",     "Enabled",         "via transcribe(fp16=True)", "ok")
    print(f"\n  {CY}  VRAM after load{R}   {bar}\n")
else:
    status_row("Model",    "Whisper medium",  "loaded on CPU",          "ok")
    status_row("FP16",     "Disabled",        "not supported on CPU",   "warn")


# ════════════════════════════════════════════════════════════════════════════
#  3. AUDIO PIPELINE
# ════════════════════════════════════════════════════════════════════════════
section("AUDIO PIPELINE")

r = sr.Recognizer()
r.dynamic_energy_threshold = True
r.pause_threshold = 0.8

status_row("Recognizer",    "SpeechRecognition", "ready",              "ok")
status_row("Noise Suppress","Spectral Gating",   "80% noise removal",  "ok")
status_row("Energy Thresh", "Dynamic",           "auto-adjusts",       "ok")
status_row("Pause Thresh",  f"{r.pause_threshold}s", "silence cutoff", "ok")


# ════════════════════════════════════════════════════════════════════════════
#  4. MAIN LOOP
# ════════════════════════════════════════════════════════════════════════════
def listen_and_transcribe():
    with sr.Microphone() as source:

        section("MICROPHONE")
        log_info("Calibrating for ambient noise — stay quiet for 2s...")
        r.adjust_for_ambient_noise(source, duration=2.0)
        status_row("Microphone", "Calibrated", "noise baseline locked", "ok")

        # ── Language selection ───────────────────────────────────────────────
        target_language = None
        while target_language is None:
            print(f"\n  {MG}[?]{R} {BLD}Say your language:{R}  "
                  f"{GR}English{R}  or  {YL}Arabic{R}  ...")
            try:
                lang_audio = r.listen(source, timeout=5)
                temp_file  = "temp_lang.wav"
                with open(temp_file, "wb") as f:
                    f.write(lang_audio.get_wav_data())

                lang_result = model.transcribe(temp_file, language="en", fp16=USE_FP16)
                lang_text   = lang_result['text'].lower()
                os.remove(temp_file)

                log_info(f"Heard: {CY}'{lang_text.strip()}'{R}")

                if "arabic" in lang_text or "عربي" in lang_text:
                    target_language = "ar"
                    status_row("Language", "ARABIC", "Egyptian dialect prompt ON", "ok")
                elif "english" in lang_text:
                    target_language = "en"
                    status_row("Language", "ENGLISH", "standard prompt", "ok")
                else:
                    log_warn("Didn't catch that — say 'Arabic' or 'English'.")

            except Exception as e:
                log_err(f"Language detection: {e}")
                continue

        egyptian_prompt = "بص يا سيدي، إحنا بنتكلم مصري عادي خالص. إزيك؟ عامل إيه؟ إيه الأخبار؟ كله تمام؟"
        lang_label = "AR" if target_language == "ar" else "EN"

        print(f"\n{MG}  ╔{'═' * 50}╗{R}")
        print(f"{MG}  ║{BLD}{f'  LISTENING ACTIVE  [{lang_label}]':<50}{R}{MG}║{R}")
        print(f"{MG}  ╚{'═' * 50}╝{R}")

        call_count = 0

        while True:
            try:
                divider(MG)
                log_info(f"Waiting for speech...")
                audio = r.listen(source)

                # ── Noise reduction ─────────────────────────────────────────
                log_info("Noise suppression running...")
                wav_bytes     = audio.get_wav_data()
                rate, data    = wavfile.read(io.BytesIO(wav_bytes))
                filtered_data = nr.reduce_noise(y=data, sr=rate, prop_decrease=0.8)
                temp_file     = "temp_voice.wav"
                wavfile.write(temp_file, rate, filtered_data)
                log(f"Noise gate applied  {GR}[80% suppression]{R}")

                # ── Transcription ───────────────────────────────────────────
                if DEVICE == "cuda":
                    torch.cuda.empty_cache()

                log_info("Transcribing...")

                result = model.transcribe(
                    temp_file,
                    language=target_language,
                    initial_prompt=egyptian_prompt if target_language == "ar" else "",
                    beam_size=5,
                    best_of=5,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    fp16=USE_FP16
                )

                final_text = result['text'].strip()
                os.remove(temp_file)
                call_count += 1

                if final_text:
                    # VRAM bar on GPU
                    if DEVICE == "cuda":
                        used = torch.cuda.memory_allocated(0) / (1024 ** 3)
                        bar  = vram_bar(used, VRAM_TOTAL)
                        print(f"  {CY}  VRAM{R}  {bar}")

                    # Result box with word-wrapping
                    print(f"\n  {GR}┌{'─' * 50}┐{R}")
                    words, line, lines = final_text.split(), "", []
                    for w in words:
                        if len(line) + len(w) + 1 > 48:
                            lines.append(line); line = w
                        else:
                            line = (line + " " + w).strip()
                    if line: lines.append(line)
                    for ln in lines:
                        print(f"  {GR}│{R}  {BLD}{WH}{ln:<48}{R}  {GR}│{R}")
                    print(f"  {GR}└{'─' * 50}┘{R}")
                    print(f"  {DIM}  call #{call_count} · {lang_label} · beam_size=5{R}\n")

            except Exception as e:
                log_err(f"Transcription error: {e}")
                continue


if __name__ == "__main__":
    try:
        listen_and_transcribe()
    except KeyboardInterrupt:
        print(f"\n{YL}  ╔{'═' * 50}╗{R}")
        print(f"{YL}  ║{'  SESSION ENDED  —  Goodbye!':^50}║{R}")
        print(f"{YL}  ╚{'═' * 50}╝{R}\n")
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
            log("GPU memory cleared")