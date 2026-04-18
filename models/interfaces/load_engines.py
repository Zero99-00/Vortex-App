import sys, os
# Quickly point to the root so absolute imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from models.logic_units.stt_engine import STTEngine

if __name__ == "__main__":
    engine = STTEngine(model_size="medium")
    engine.load_engine_to_vram()
    engine.start_listening()