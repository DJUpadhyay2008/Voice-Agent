import logging
import sys
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    """Clean structured log formatter with millisecond UTC timestamps."""
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.levelname.ljust(5)
        name = record.name
        message = record.getMessage()
        
        session_id = getattr(record, "session_id", None)
        if session_id:
            return f"[{timestamp}] [{level}] [{name}] [session={session_id[:8]}] {message}"
        return f"[{timestamp}] [{level}] [{name}] {message}"

def get_logger(name: str = "voice-agent") -> logging.Logger:
    """Returns a preconfigured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
