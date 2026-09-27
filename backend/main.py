import json
import time
import uuid
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logger import get_logger
from backend.voice.audio import validate_pcm_chunk, compute_rms, compute_db

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
    }

@app.websocket("/ws/call/{session_id}")
async def websocket_call_endpoint(
    websocket: WebSocket,
    session_id: str,
    loopback: bool = Query(default=False)
):
    """
    Bidirectional WebSocket endpoint for the real-time voice session.
    Receives continuous 16kHz 16-bit Mono PCM audio chunks.
    Sends control events, stats, and optional loopback audio.
    """
    await websocket.accept()
    
    is_loopback_active = loopback or settings.ENABLE_LOOPBACK
    start_time = time.time()
    chunks_received = 0
    total_bytes = 0
    last_stats_time = time.time()
    
    logger.info(
        f"Client connected. loopback={is_loopback_active}, expected_bytes={settings.bytes_per_chunk}",
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
        },
        "status": "connected"
    }))

    try:
        while True:
            # Receive either binary audio data or JSON control messages
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
                
                # Compute audio volume metrics
                rms = compute_rms(audio_chunk)
                db = compute_db(rms)
                
                # Optional loopback echo for audio verification
                if is_loopback_active:
                    await websocket.send_bytes(audio_chunk)

                # Send telemetry update every ~500ms (approx every 15 frames)
                now = time.time()
                if now - last_stats_time >= 0.5:
                    await websocket.send_text(json.dumps({
                        "type": "audio_telemetry",
                        "chunks_received": chunks_received,
                        "total_bytes": total_bytes,
                        "rms": round(rms, 4),
                        "db": db,
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
                        logger.info("Call started by client", extra={"session_id": session_id})
                        await websocket.send_text(json.dumps({
                            "type": "call_status",
                            "status": "listening"
                        }))
                    elif msg_type == "stop_call":
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
