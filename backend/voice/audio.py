import math
import numpy as np

def validate_pcm_chunk(chunk: bytes, expected_bytes: int | None = None) -> bool:
    """
    Validates that a raw audio chunk consists of whole 16-bit PCM samples.
    If expected_bytes is provided, checks if chunk length matches.
    """
    if not chunk or len(chunk) % 2 != 0:
        return False
    if expected_bytes is not None and len(chunk) != expected_bytes:
        return False
    return True

def pcm_to_float32(chunk: bytes) -> np.ndarray:
    """Converts 16-bit signed integer PCM bytes to Float32 array in [-1.0, 1.0]."""
    samples = np.frombuffer(chunk, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0

def float32_to_pcm(audio_float: np.ndarray) -> bytes:
    """Converts Float32 array in [-1.0, 1.0] to 16-bit signed integer PCM bytes."""
    clipped = np.clip(audio_float, -1.0, 1.0)
    samples = (clipped * 32767.0).astype(np.int16)
    return samples.tobytes()

def compute_rms(chunk: bytes) -> float:
    """Computes normalized Root Mean Square (RMS) volume in [0.0, 1.0]."""
    if not chunk or len(chunk) < 2:
        return 0.0
    samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float64) / 32768.0
    mean_square = np.mean(samples ** 2)
    return float(np.sqrt(mean_square))

def compute_db(rms: float) -> float:
    """Converts normalized RMS to dBFS (-100 dBFS to 0 dBFS)."""
    if rms <= 1e-5:
        return -100.0
    db = 20.0 * math.log10(rms)
    return max(-100.0, min(0.0, round(db, 1)))
