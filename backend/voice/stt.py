import io
import time
import wave
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from backend.config import settings
from backend.logger import get_logger
from backend.voice.audio import pcm_to_float32

logger = get_logger("stt")


def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Converts raw Int16 PCM bytes into in-memory WAV file bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


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


class GroqSTTProvider(STTProvider):
    """
    Cloud STT provider using Groq Whisper API (whisper-large-v3-turbo).
    Delivers sub-150ms transcription with state-of-the-art accuracy.
    Requires GROQ_API_KEY in environment.
    """

    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key
        self.model = model
        import httpx
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"Initialized GroqSTTProvider with model '{model}'")

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> STTTranscript:
        if not pcm_bytes or len(pcm_bytes) < 1024:
            return STTTranscript(text="", is_final=True)

        t0 = time.time()
        wav_bytes = pcm_to_wav_bytes(pcm_bytes, sample_rate=sample_rate)
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        files = {
            "file": ("speech.wav", wav_bytes, "audio/wav"),
        }
        data = {
            "model": self.model,
            "language": "en",
            "temperature": "0.0",
            "response_format": "json",
        }

        try:
            response = await self.client.post(url, headers=headers, files=files, data=data)
            t1 = time.time()
            duration_ms = round((t1 - t0) * 1000.0, 1)

            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "").strip()
                if text:
                    logger.info(f"Groq STT (dur={duration_ms}ms): \"{text}\"")
                return STTTranscript(
                    text=text,
                    is_final=True,
                    confidence=0.98,
                    duration_ms=duration_ms,
                )
            else:
                logger.error(f"Groq STT error HTTP {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Groq STT request exception: {e}")

        return STTTranscript(text="", is_final=True)


class FasterWhisperSTTProvider(STTProvider):
    """
    Local Speech-to-Text provider using CTranslate2 Faster-Whisper.
    Tuned with strict anti-hallucination and zero-temperature decoding to prevent repetition loops.
    """

    def __init__(
        self,
        model_size: str = "base.en",
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

        # Run transcription with strict anti-hallucination settings
        segments, info = self.model.transcribe(
            audio_float,
            beam_size=1,
            language="en",
            task="transcribe",
            vad_filter=False,
            temperature=0.0,                      # Disable temperature fallbacks (prevents latency spikes)
            condition_on_previous_text=False,     # Disable past text conditioning (prevents infinite repetition loops)
            no_speech_threshold=0.6,              # Ignore ambient noise frames
            compression_ratio_threshold=2.4,       # Reject repetitive hallucinated outputs
        )

        texts = []
        confidences = []
        for segment in segments:
            clean_text = segment.text.strip()
            # Filter out known hallucination phrases
            if clean_text and not self._is_hallucination(clean_text):
                texts.append(clean_text)
                confidences.append(getattr(segment, "avg_logprob", 0.0))

        full_text = " ".join(texts)
        t1 = time.time()
        duration_ms = round((t1 - t0) * 1000.0, 1)

        avg_confidence = float(np.exp(np.mean(confidences))) if confidences else 1.0

        if full_text:
            logger.info(f"Local Faster-Whisper STT (dur={duration_ms}ms): \"{full_text}\"")

        return STTTranscript(
            text=full_text,
            is_final=True,
            confidence=round(avg_confidence, 3),
            language=info.language or "en",
            duration_ms=duration_ms,
        )

    def _is_hallucination(self, text: str) -> bool:
        """Filters out typical Whisper hallucination patterns on background noise."""
        lower = text.lower().strip()
        hallucination_phrases = [
            "thank you.", "thank you for watching.", "subscribe to my channel",
            "bye.", "quail", "optament", "carrying the blue", "he's sleeping so much"
        ]
        if lower in hallucination_phrases or len(set(lower.split())) <= 2 and len(lower.split()) > 6:
            return True
        return False


class DeepgramSTTProvider(STTProvider):
    """
    Cloud Speech-to-Text provider using Deepgram REST API.
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
    """
    Factory function providing singleton STTProvider instance.
    Priority order:
    1. GroqSTTProvider (if GROQ_API_KEY is available — ultra-fast sub-100ms whisper-large-v3-turbo)
    2. DeepgramSTTProvider (if DEEPGRAM_API_KEY is available — ultra-fast Nova-2)
    3. FasterWhisperSTTProvider (local base.en fallback with strict anti-hallucination tuning)
    """
    global _stt_provider_instance
    if _stt_provider_instance is None:
        if settings.GROQ_API_KEY:
            logger.info("Initializing Groq STT Provider (whisper-large-v3-turbo)...")
            _stt_provider_instance = GroqSTTProvider(api_key=settings.GROQ_API_KEY)
        elif settings.DEEPGRAM_API_KEY:
            logger.info("Initializing Deepgram STT Provider (nova-2)...")
            _stt_provider_instance = DeepgramSTTProvider(api_key=settings.DEEPGRAM_API_KEY)
        else:
            logger.info("Initializing Local Faster-Whisper STT Provider (base.en with anti-hallucination tuning)...")
            _stt_provider_instance = FasterWhisperSTTProvider(model_size="base.en")
    return _stt_provider_instance
