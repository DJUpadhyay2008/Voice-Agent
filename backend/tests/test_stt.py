import asyncio
import wave
from backend.voice.stt import FasterWhisperSTTProvider

async def main():
    stt = FasterWhisperSTTProvider(model_size="tiny.en")
    
    with wave.open("backend/tests/hello.wav", "rb") as wf:
        pcm_bytes = wf.readframes(wf.getnframes())
        sample_rate = wf.getframerate()
        
    res = await stt.transcribe(pcm_bytes, sample_rate=sample_rate)
    
    assert res.is_final is True
    assert "hello" in res.text.lower()
    assert res.duration_ms > 0
    print(f"STT Unit Test Success! Transcribed text: '{res.text}' in {res.duration_ms} ms")

if __name__ == "__main__":
    asyncio.run(main())
