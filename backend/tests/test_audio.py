import numpy as np
from backend.voice.audio import (
    validate_pcm_chunk,
    compute_rms,
    compute_db,
    pcm_to_float32,
    float32_to_pcm
)

def test_pcm_validation():
    # 512 samples * 2 bytes = 1024 bytes
    valid_chunk = bytes(1024)
    assert validate_pcm_chunk(valid_chunk, 1024) is True
    assert validate_pcm_chunk(valid_chunk, 512) is False
    assert validate_pcm_chunk(bytes(1023), 1024) is False  # Odd bytes
    assert validate_pcm_chunk(b"") is False

def test_rms_and_db_silence():
    silence = bytes(1024)
    rms = compute_rms(silence)
    db = compute_db(rms)
    assert rms == 0.0
    assert db == -100.0

def test_rms_and_db_sine_wave():
    # Generate 16kHz sine wave at 440 Hz
    sample_rate = 16000
    t = np.linspace(0, 512 / sample_rate, 512, endpoint=False, dtype=np.float32)
    # Sine wave amplitude 0.5 (-6 dBFS approx)
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)
    pcm = float32_to_pcm(sine)
    
    assert len(pcm) == 1024
    rms = compute_rms(pcm)
    db = compute_db(rms)
    
    # RMS of sine with amplitude A is A / sqrt(2) = 0.5 / 1.414 = ~0.3535
    assert 0.33 < rms < 0.37
    # dB is approx 20 * log10(0.3535) = -9 dB
    assert -10.0 <= db <= -8.0

def test_float_pcm_roundtrip():
    original = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)
    pcm = float32_to_pcm(original)
    recovered = pcm_to_float32(pcm)
    assert np.allclose(original, recovered, atol=1e-3)

if __name__ == "__main__":
    test_pcm_validation()
    test_rms_and_db_silence()
    test_rms_and_db_sine_wave()
    test_float_pcm_roundtrip()
    print("All audio utility tests passed successfully!")
