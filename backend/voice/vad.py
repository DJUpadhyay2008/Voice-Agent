from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import onnxruntime as ort

from backend.voice.audio import pcm_to_float32
from backend.logger import get_logger

logger = get_logger("vad")

@dataclass
class VADResult:
    """Result returned by VAD processing for an audio chunk."""
    is_speech: bool
    probability: float
    event: Optional[str] = None  # "speech_start" | "speech_end" | None
    speech_duration_ms: float = 0.0
    silence_duration_ms: float = 0.0

class VADProvider(ABC):
    """Abstract Base Class for Voice Activity Detection providers."""
    
    @abstractmethod
    def process_chunk(self, chunk: bytes) -> VADResult:
        """Process a raw PCM audio chunk and return turn detection result."""
        pass

    @abstractmethod
    def reset(self):
        """Reset internal VAD states for a new conversation turn or session."""
        pass

class SileroVADProvider(VADProvider):
    """
    Local Voice Activity Detection provider using official Silero VAD v4 ONNX model.
    Runs on CPU with sub-2ms latency per 32ms frame (512 samples at 16kHz).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        neg_threshold: float = 0.35,
        min_speech_duration_ms: int = 100,
        min_silence_duration_ms: int = 400,
    ):
        if model_path is None:
            model_path = str(Path(__file__).resolve().parent / "models" / "silero_vad.onnx")
        
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.neg_threshold = neg_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms

        # ONNX Runtime session setup (CPU Execution Provider)
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        opts.log_severity_level = 3  # Suppress internal warnings
        self.session = ort.InferenceSession(self.model_path, opts, providers=["CPUExecutionProvider"])
        self.sr_tensor = np.array(self.sample_rate, dtype=np.int64)

        self.reset()

    def reset(self):
        """Reset state tensors and turn state machine."""
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._triggered = False
        self._speech_samples = 0
        self._silence_samples = 0

    def process_chunk(self, chunk: bytes) -> VADResult:
        """
        Processes a raw 16-bit PCM chunk (512 samples at 16kHz).
        Calculates speech probability and updates state machine for turn detection.
        """
        if not chunk or len(chunk) < 2:
            return VADResult(is_speech=self._triggered, probability=0.0)

        # Convert Int16 PCM to Float32 [-1.0, 1.0]
        audio_float = pcm_to_float32(chunk)
        chunk_samples = len(audio_float)
        input_tensor = np.expand_dims(audio_float, axis=0)  # Shape [1, num_samples]

        # Run ONNX inference with h and c hidden states
        outputs = self.session.run(
            None,
            {
                "input": input_tensor,
                "h": self._h,
                "c": self._c,
                "sr": self.sr_tensor,
            }
        )
        
        prob = float(outputs[0][0][0])
        self._h = outputs[1]  # Updated h state
        self._c = outputs[2]  # Updated c state

        event: Optional[str] = None
        chunk_ms = (chunk_samples / self.sample_rate) * 1000.0

        # State Machine Transition Logic
        if prob >= self.threshold:
            self._speech_samples += chunk_samples
            self._silence_samples = 0

            speech_dur_ms = (self._speech_samples / self.sample_rate) * 1000.0
            if not self._triggered and speech_dur_ms >= self.min_speech_duration_ms:
                self._triggered = True
                event = "speech_start"
                logger.info(f"VAD Event: speech_start (prob={prob:.2f}, dur={speech_dur_ms:.0f}ms)")

        elif prob < self.neg_threshold:
            if self._triggered:
                self._silence_samples += chunk_samples
                silence_dur_ms = (self._silence_samples / self.sample_rate) * 1000.0

                if silence_dur_ms >= self.min_silence_duration_ms:
                    total_speech_ms = (self._speech_samples / self.sample_rate) * 1000.0
                    self._triggered = False
                    event = "speech_end"
                    logger.info(
                        f"VAD Event: speech_end (silence_dur={silence_dur_ms:.0f}ms, speech_dur={total_speech_ms:.0f}ms)"
                    )
                    self._speech_samples = 0
                    self._silence_samples = 0
            else:
                self._speech_samples = 0

        current_speech_ms = (self._speech_samples / self.sample_rate) * 1000.0
        current_silence_ms = (self._silence_samples / self.sample_rate) * 1000.0

        return VADResult(
            is_speech=self._triggered,
            probability=prob,
            event=event,
            speech_duration_ms=round(current_speech_ms, 1),
            silence_duration_ms=round(current_silence_ms, 1),
        )
