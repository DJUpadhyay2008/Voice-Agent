import numpy as np
from unittest.mock import MagicMock
from backend.voice.vad import SileroVADProvider, VADResult

def test_silero_vad_real_model_silence():
    vad = SileroVADProvider(
        min_speech_duration_ms=100,
        min_silence_duration_ms=300
    )
    # 512 samples of silence (1024 bytes)
    silence = bytes(1024)
    result = vad.process_chunk(silence)
    
    assert result.is_speech is False
    assert result.probability < 0.05
    assert result.event is None

def test_vad_state_machine_speech_start_and_end():
    # Instantiate VAD and mock the internal ONNX session run method
    vad = SileroVADProvider(
        threshold=0.5,
        neg_threshold=0.35,
        min_speech_duration_ms=64,
        min_silence_duration_ms=200
    )
    
    # Sequence of probabilities: silence -> speech burst -> silence
    probs = [0.01, 0.01, 0.85, 0.92, 0.88, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
    
    speech_started = False
    speech_ended = False
    speech_start_index = -1
    speech_end_index = -1

    dummy_chunk = bytes(1024)
    
    for idx, prob in enumerate(probs):
        # Mock session output: [prob_array, h_state, c_state]
        vad.session.run = MagicMock(return_value=[
            np.array([[prob]], dtype=np.float32),
            np.zeros((2, 1, 64), dtype=np.float32),
            np.zeros((2, 1, 64), dtype=np.float32)
        ])
        res = vad.process_chunk(dummy_chunk)
        
        if res.event == "speech_start":
            speech_started = True
            speech_start_index = idx
        elif res.event == "speech_end":
            speech_ended = True
            speech_end_index = idx

    assert speech_started is True
    assert speech_ended is True
    assert speech_start_index < speech_end_index
    assert vad._triggered is False

def test_silero_vad_reset():
    vad = SileroVADProvider()
    vad._triggered = True
    vad._speech_samples = 1000
    vad.reset()
    assert vad._triggered is False
    assert vad._speech_samples == 0

if __name__ == "__main__":
    test_silero_vad_real_model_silence()
    test_vad_state_machine_speech_start_and_end()
    test_silero_vad_reset()
    print("All Silero VAD unit tests passed successfully!")
