import time
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from backend.config import settings
from backend.logger import get_logger
from backend.voice.audio import pcm_to_float32

logger = get_logger("stt")

@dataclass
class STTTranscript:
    """Dataclass holding Speech-to-Text transcription results."""
    text: str
    is_final: bool = True
    confidence: float = 1.0
    language: str = "en"
    duration_ms: float = 0.0

class STTProvider(ABC):
    """Abstract Base Class for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> STTTranscript:
        """Transcribes raw 16-bit PCM audio bytes to text."""
        pass

class FasterWhisperSTTProvider(STTProvider):
    """
    Local Speech-to-Text provider using CTranslate2 Faster-Whisper.
    Runs locally on CPU/GPU with fast C++ inference.
    """

    def __init__(
        self,
        model_size: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        from faster_whisper import WhisperModel
        
        self.model_size = model_size
        logger.info(f"Loading Faster-Whisper model '{model_size}' on {device} ({compute_type})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"Faster-Whisper model '{model_size}' loaded successfully.")

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> STTTranscript:
        if not pcm_bytes or len(pcm_bytes) < 1024:  # Less than 32ms
            return STTTranscript(text="", is_final=True, confidence=0.0)

        t0 = time.time()
        # Convert Int16 PCM bytes to Float32 [-1.0, 1.0]
        audio_float = pcm_to_float32(pcm_bytes)

        # Run transcription
        segments, info = self.model.transcribe(
            audio_float,
            beam_size=1,
            language="en",
            task="transcribe",
            vad_filter=False  # Server VAD has already segmented the speech turn
        )

        texts = []
        confidences = []
        for segment in segments:
            clean_text = segment.text.strip()
            if clean_text:
                texts.append(clean_text)
                confidences.append(getattr(segment, "avg_logprob", 0.0))

        full_text = " ".join(texts)
        t1 = time.time()
        duration_ms = round((t1 - t0) * 1000.0, 1)

        avg_confidence = float(np.exp(np.mean(confidences))) if confidences else 1.0

        if full_text:
            logger.info(f"STT Transcribed (dur={duration_ms}ms): \"{full_text}\"")

        return STTTranscript(
            text=full_text,
            is_final=True,
            confidence=round(avg_confidence, 3),
            language=info.language or "en",
            duration_ms=duration_ms,
        )

class DeepgramSTTProvider(STTProvider):
    """
    Cloud Speech-to-Text provider using Deepgram REST API (or WebSocket streaming).
    Requires DEEPGRAM_API_KEY in environment.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        import httpx
        self.client = httpx.AsyncClient(timeout=5.0)

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> STTTranscript:
        if not pcm_bytes or len(pcm_bytes) < 1024:
            return STTTranscript(text="", is_final=True)

        t0 = time.time()
        url = f"https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&encoding=linear16&sample_rate={sample_rate}&channels=1"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/raw",
        }

        try:
            response = await self.client.post(url, headers=headers, content=pcm_bytes)
            t1 = time.time()
            duration_ms = round((t1 - t0) * 1000.0, 1)

            if response.status_code == 200:
                data = response.json()
                channels = data.get("results", {}).get("channels", [])
                if channels and channels[0].get("alternatives"):
                    alt = channels[0]["alternatives"][0]
                    transcript = alt.get("transcript", "").strip()
                    confidence = alt.get("confidence", 1.0)
                    if transcript:
                        logger.info(f"Deepgram STT (dur={duration_ms}ms): \"{transcript}\"")
                    return STTTranscript(
                        text=transcript,
                        is_final=True,
                        confidence=confidence,
                        duration_ms=duration_ms,
                    )
        except Exception as e:
            logger.error(f"Deepgram STT error: {e}")

        return STTTranscript(text="", is_final=True)

_stt_provider_instance: Optional[STTProvider] = None

def get_stt_provider() -> STTProvider:
    """Factory function providing singleton STTProvider instance."""
    global _stt_provider_instance
    if _stt_provider_instance is None:
        if settings.DEEPGRAM_API_KEY:
            logger.info("Initializing Deepgram STT Provider...")
            _stt_provider_instance = DeepgramSTTProvider(api_key=settings.DEEPGRAM_API_KEY)
        else:
            logger.info("Initializing Local Faster-Whisper STT Provider...")
            _stt_provider_instance = FasterWhisperSTTProvider(model_size="tiny.en")
    return _stt_provider_instance
