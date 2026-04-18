# Global engine state to avoid circular imports
_running_engine = None
_engine_starting = False

def set_engine(engine):
    """Set the running engine instance"""
    global _running_engine
    _running_engine = engine

def get_engine():
    """Get the running engine instance"""
    return _running_engine

def set_engine_starting(is_starting):
    """Set whether engine is in starting process"""
    global _engine_starting
    _engine_starting = is_starting

def is_engine_starting():
    """Check if engine is currently starting"""
    return _engine_starting
