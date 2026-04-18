import multiprocessing
from models.logic_units.stt_engine import STTEngine
from models.logic_units.tts_engine import TTSEngine
from models.logic_units.llm_engine import LLMEngine

def run_llm():
    llm = LLMEngine()
    llm.start_polling()

def run_tts():
    tts = TTSEngine()
    tts.start_polling()

if __name__ == "__main__":
    print("Spawning background processes...")
    # Spawn LLM and TTS in fully separate processes so they don't block STT or UI
    multiprocessing.Process(target=run_llm, daemon=True).start()
    multiprocessing.Process(target=run_tts, daemon=True).start()
    
    # Run STT in the main process
    stt = STTEngine()
    stt.load_engine_to_vram()
    stt.start_listening()