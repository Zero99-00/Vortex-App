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

COLOR_CYAN    = '\033[96m'
COLOR_GREEN   = '\033[92m'
COLOR_YELLOW  = '\033[93m'
COLOR_MAGENTA = '\033[95m'
COLOR_RED     = '\033[91m'
COLOR_RESET   = '\033[0m'

def log(msg, color=COLOR_GREEN):
    print(f"{color}[+] {msg}{COLOR_RESET}")

def log_warn(msg):
    print(f"{COLOR_YELLOW}[!] {msg}{COLOR_RESET}")

def log_err(msg):
    print(f"{COLOR_RED}[X] {msg}{COLOR_RESET}")

def log_info(msg):
    print(f"{COLOR_CYAN}[~] {msg}{COLOR_RESET}")

# ==========================================
# 1. GPU / CPU DETECTION
# ==========================================
log_info("Checking hardware...")

USE_FP16 = False  # fp16 only works on GPU

if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    log(f"NVIDIA GPU detected: {gpu_name}")
    log(f"Total VRAM: {vram_total:.1f} GB")
    DEVICE = "cuda"
    USE_FP16 = True
    log("Whisper will run on GPU (fp16 mode — lower VRAM usage)")
else:
    log_warn("No NVIDIA GPU detected.")
    log_warn("CUDA not available — falling back to CPU.")
    DEVICE = "cpu"
    USE_FP16 = False
    log("Whisper will run on CPU (fp32 mode)")

# ==========================================
# 2. LOAD WHISPER MODEL (VRAM OPTIMIZED)
# ==========================================
# VRAM reduction tricks:
#   - fp16=True  cuts model memory in half on GPU (float32 → float16)
#   - torch.cuda.empty_cache() clears leftover allocations after loading
#   - in_memory=True streams audio without extra GPU buffer copies

log_info("Loading Whisper 'medium' model...")

model = whisper.load_model(
    "medium",
    device=DEVICE,
    in_memory=True       # loads weights directly into RAM/VRAM — no temp disk buffer
)

if DEVICE == "cuda":
    # DO NOT call model.half() manually — it breaks input dtype matching.
    # Whisper handles fp16 internally when fp16=True is passed to transcribe().
    torch.cuda.empty_cache()
    used_vram = torch.cuda.memory_allocated(0) / (1024 ** 3)
    log(f"Model loaded on GPU — VRAM used after load: {used_vram:.2f} GB")
else:
    log("Model loaded on CPU — no VRAM used")

# ==========================================
# 3. MICROPHONE SETUP
# ==========================================
r = sr.Recognizer()
r.dynamic_energy_threshold = True
r.pause_threshold = 0.8

log_info("Recognizer initialized")

# ==========================================
# 4. LISTEN AND TRANSCRIBE
# ==========================================
def listen_and_transcribe():
    with sr.Microphone() as source:
        log_info("Calibrating microphone for ambient noise... stay quiet...")
        r.adjust_for_ambient_noise(source, duration=2.0)
        log("Microphone calibrated")

        # --- LANGUAGE SELECTION ---
        target_language = None
        while target_language is None:
            print(f"\n{COLOR_CYAN}[?] What is your language? Say 'English' or 'Arabic'...{COLOR_RESET}")

            try:
                lang_audio = r.listen(source, timeout=5)
                temp_file = "temp_lang.wav"
                with open(temp_file, "wb") as f:
                    f.write(lang_audio.get_wav_data())

                lang_result = model.transcribe(temp_file, language="en", fp16=USE_FP16)
                lang_text = lang_result['text'].lower()
                os.remove(temp_file)

                log_info(f"I heard: '{lang_text.strip()}'")

                if "arabic" in lang_text or "عربي" in lang_text:
                    target_language = "ar"
                    log("Language set to: ARABIC")
                elif "english" in lang_text:
                    target_language = "en"
                    log("Language set to: ENGLISH")
                else:
                    log_warn("Didn't catch that — say 'Arabic' or 'English'.")

            except Exception as e:
                log_err(f"Language detection error: {e}")
                continue

        egyptian_prompt = "بص يا سيدي، إحنا بنتكلم مصري عادي خالص. إزيك؟ عامل إيه؟ إيه الأخبار؟ كله تمام؟"

        print(f"\n{COLOR_MAGENTA}[+] --- LISTENING MODE ACTIVE --- [+]{COLOR_RESET}")

        while True:
            try:
                log_info("Listening...")
                audio = r.listen(source)
                log_info("Applying noise reduction filter...")

                # --- AUDIO FILTERING ---
                wav_bytes  = audio.get_wav_data()
                rate, data = wavfile.read(io.BytesIO(wav_bytes))

                filtered_data = nr.reduce_noise(y=data, sr=rate, prop_decrease=0.8)

                temp_file = "temp_voice.wav"
                wavfile.write(temp_file, rate, filtered_data)
                log("Audio filtered — background noise removed")

                # Clear GPU cache before each transcription to free fragmented VRAM
                if DEVICE == "cuda":
                    torch.cuda.empty_cache()

                log_info("Running Whisper transcription...")

                result = model.transcribe(
                    temp_file,
                    language=target_language,
                    initial_prompt=egyptian_prompt if target_language == "ar" else "",
                    beam_size=5,
                    best_of=5,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    fp16=USE_FP16      # half-precision on GPU, full on CPU
                )

                final_text = result['text'].strip()
                os.remove(temp_file)

                if final_text:
                    if DEVICE == "cuda":
                        used = torch.cuda.memory_allocated(0) / (1024 ** 3)
                        log(f"VRAM in use: {used:.2f} GB")
                    log(f"Transcription: {final_text}")

            except Exception as e:
                log_err(f"Transcription error: {e}")
                continue

if __name__ == "__main__":
    try:
        listen_and_transcribe()
    except KeyboardInterrupt:
        log_warn("Program stopped by user. Bye!")
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
            log("GPU memory cleared")