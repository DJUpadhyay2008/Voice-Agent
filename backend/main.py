import json
import time
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logger import get_logger
from backend.voice.audio import validate_pcm_chunk, compute_rms, compute_db
from backend.voice.vad import SileroVADProvider
from backend.voice.stt import get_stt_provider

logger = get_logger("main")

app = FastAPI(
    title="Voice Agent Real-Time Audio Server",
    description="Low-latency real-time voice call agent backend",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify backend status."""
    stt = get_stt_provider()
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "audio_config": {
            "sample_rate": settings.SAMPLE_RATE,
            "channels": settings.CHANNELS,
            "sample_width": settings.SAMPLE_WIDTH,
            "chunk_size": settings.CHUNK_SIZE,
            "bytes_per_chunk": settings.bytes_per_chunk,
        },
        "loopback_default": settings.ENABLE_LOOPBACK,
        "vad_provider": "SileroVADProvider (v4 ONNX)",
        "stt_provider": stt.__class__.__name__,
    }

@app.websocket("/ws/call/{session_id}")
async def websocket_call_endpoint(
    websocket: WebSocket,
    session_id: str,
    loopback: bool = Query(default=False)
):
    """
    Bidirectional WebSocket endpoint for the real-time voice session.
    Processes 16kHz 16-bit Mono PCM audio chunks with Silero VAD turn detection
    and Speech-to-Text (STT) transcription.
    """
    await websocket.accept()
    
    is_loopback_active = loopback or settings.ENABLE_LOOPBACK
    start_time = time.time()
    chunks_received = 0
    total_bytes = 0
    last_stats_time = time.time()

    # Initialize Voice Pipeline components for this session
    vad_provider = SileroVADProvider(
        sample_rate=settings.SAMPLE_RATE,
        threshold=0.5,
        neg_threshold=0.35,
        min_speech_duration_ms=100,
        min_silence_duration_ms=400,
    )
    stt_provider = get_stt_provider()
    
    # In-memory buffer to accumulate PCM bytes for the active speech turn
    speech_buffer = bytearray()

    logger.info(
        f"Client connected. loopback={is_loopback_active}, vad=SileroVAD, stt={stt_provider.__class__.__name__}",
        extra={"session_id": session_id}
    )

    # Send initial session greeting
    await websocket.send_text(json.dumps({
        "type": "session_created",
        "session_id": session_id,
        "config": {
            "sample_rate": settings.SAMPLE_RATE,
            "channels": settings.CHANNELS,
            "chunk_size": settings.CHUNK_SIZE,
            "loopback": is_loopback_active,
            "vad": "silero_v4",
            "stt": stt_provider.__class__.__name__,
        },
        "status": "connected"
    }))

    try:
        while True:
            # Receive binary audio data or JSON control messages
            message = await websocket.receive()
            
            # 1. Binary Frame: Raw Audio PCM
            if "bytes" in message and message["bytes"]:
                audio_chunk = message["bytes"]
                chunk_len = len(audio_chunk)
                total_bytes += chunk_len
                chunks_received += 1
                
                # Format validation
                is_valid = validate_pcm_chunk(audio_chunk, expected_bytes=settings.bytes_per_chunk)
                if not is_valid:
                    logger.warning(
                        f"Unexpected audio chunk size: received {chunk_len} bytes, expected {settings.bytes_per_chunk}",
                        extra={"session_id": session_id}
                    )
                
                # Run Voice Activity Detection
                vad_result = vad_provider.process_chunk(audio_chunk)

                # Accumulate speech frames during an active speech turn
                if vad_result.is_speech or vad_result.event == "speech_start":
                    speech_buffer.extend(audio_chunk)

                # Handle VAD turn events
                if vad_result.event:
                    await websocket.send_text(json.dumps({
                        "type": "vad",
                        "event": vad_result.event,
                        "probability": round(vad_result.probability, 4),
                        "speech_duration_ms": vad_result.speech_duration_ms,
                        "silence_duration_ms": vad_result.silence_duration_ms,
                        "timestamp": time.time(),
                    }))

                    # Status update
                    new_status = "user_speaking" if vad_result.event == "speech_start" else "listening"
                    await websocket.send_text(json.dumps({
                        "type": "call_status",
                        "status": new_status,
                    }))

                    # When speech finishes, trigger Speech-to-Text transcription
                    if vad_result.event == "speech_end" and len(speech_buffer) > 0:
                        utterance_pcm = bytes(speech_buffer)
                        speech_buffer.clear()

                        # Transcribe user utterance
                        stt_transcript = await stt_provider.transcribe(
                            utterance_pcm, sample_rate=settings.SAMPLE_RATE
                        )

                        if stt_transcript.text:
                            await websocket.send_text(json.dumps({
                                "type": "transcript",
                                "role": "user",
                                "text": stt_transcript.text,
                                "is_final": True,
                                "confidence": stt_transcript.confidence,
                                "duration_ms": stt_transcript.duration_ms,
                                "timestamp": time.time(),
                            }))

                # Compute audio volume metrics
                rms = compute_rms(audio_chunk)
                db = compute_db(rms)
                
                # Optional loopback echo for audio verification
                if is_loopback_active:
                    await websocket.send_bytes(audio_chunk)

                # Send telemetry update every ~100ms
                now = time.time()
                if now - last_stats_time >= 0.1:
                    await websocket.send_text(json.dumps({
                        "type": "audio_telemetry",
                        "chunks_received": chunks_received,
                        "total_bytes": total_bytes,
                        "rms": round(rms, 4),
                        "db": db,
                        "vad_speech": vad_result.is_speech,
                        "vad_prob": round(vad_result.probability, 4),
                        "timestamp": now,
                    }))
                    last_stats_time = now

            # 2. Text Frame: Control / Signaling message
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type", "unknown")
                    
                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "client_time": payload.get("timestamp"),
                            "server_time": time.time(),
                        }))
                    elif msg_type == "start_call":
                        vad_provider.reset()
                        speech_buffer.clear()
                        logger.info("Call started by client", extra={"session_id": session_id})
                        await websocket.send_text(json.dumps({
                            "type": "call_status",
                            "status": "listening"
                        }))
                    elif msg_type == "stop_call":
                        speech_buffer.clear()
                        logger.info("Call stopped by client", extra={"session_id": session_id})
                        await websocket.send_text(json.dumps({
                            "type": "call_status",
                            "status": "disconnected"
                        }))
                    else:
                        logger.debug(f"Received control message: {msg_type}", extra={"session_id": session_id})
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON text frame", extra={"session_id": session_id})

    except (WebSocketDisconnect, RuntimeError):
        duration = round(time.time() - start_time, 2)
        logger.info(
            f"Client disconnected cleanly. Duration={duration}s, Chunks={chunks_received}, Bytes={total_bytes}",
            extra={"session_id": session_id}
        )
    except Exception as e:
        logger.error(f"WebSocket session error: {e}", exc_info=True, extra={"session_id": session_id})
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
