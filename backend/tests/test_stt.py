import asyncio
import wave
from backend.voice.stt import FasterWhisperSTTProvider, pcm_to_wav_bytes, get_stt_provider

async def main():
    # Test PCM to WAV conversion utility
    dummy_pcm = b"\x00\x00" * 1600
    wav_header = pcm_to_wav_bytes(dummy_pcm)
    assert wav_header.startswith(b"RIFF")
    print("PCM to WAV conversion test passed.")

    # Test local Faster-Whisper with anti-hallucination settings
    stt = FasterWhisperSTTProvider(model_size="tiny.en")
    
    with wave.open("backend/tests/hello.wav", "rb") as wf:
        pcm_bytes = wf.readframes(wf.getnframes())
        sample_rate = wf.getframerate()
        
    res = await stt.transcribe(pcm_bytes, sample_rate=sample_rate)
    
    assert res.is_final is True
    assert "hello" in res.text.lower()
    assert res.duration_ms > 0
    print(f"Faster-Whisper Unit Test Success! Transcribed text: '{res.text}' in {res.duration_ms} ms")

    # Test STT Factory Provider
    factory_stt = get_stt_provider()
    print(f"Factory STT Provider: {type(factory_stt).__name__}")

if __name__ == "__main__":
    asyncio.run(main())
