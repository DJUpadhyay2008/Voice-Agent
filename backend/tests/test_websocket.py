import asyncio
import json
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.voice.audio import float32_to_pcm

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["audio_config"]["sample_rate"] == 16000
    assert data["audio_config"]["bytes_per_chunk"] == 1024

def test_websocket_audio_flow():
    client = TestClient(app)
    session_id = "test-session-123"
    
    with client.websocket_connect(f"/ws/call/{session_id}?loopback=true") as ws:
        # 1. Verify session created greeting
        init_msg = ws.receive_json()
        assert init_msg["type"] == "session_created"
        assert init_msg["session_id"] == session_id
        assert init_msg["config"]["sample_rate"] == 16000
        assert init_msg["config"]["loopback"] is True
        
        # 2. Send ping, receive pong
        ws.send_text(json.dumps({"type": "ping", "timestamp": 12345}))
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert pong["client_time"] == 12345
        
        # 3. Send binary audio chunk (512 samples = 1024 bytes)
        t = np.linspace(0, 512 / 16000, 512, endpoint=False, dtype=np.float32)
        sine = 0.5 * np.sin(2 * np.pi * 440 * t)
        pcm_bytes = float32_to_pcm(sine)
        assert len(pcm_bytes) == 1024
        
        ws.send_bytes(pcm_bytes)
        
        # In loopback mode, the server echoes the binary audio back
        echoed_bytes = ws.receive_bytes()
        assert echoed_bytes == pcm_bytes
        
        # 4. Stop call control message
        ws.send_text(json.dumps({"type": "stop_call"}))
        status = ws.receive_json()
        assert status["type"] == "call_status"
        assert status["status"] == "disconnected"

if __name__ == "__main__":
    test_health_endpoint()
    test_websocket_audio_flow()
    print("All WebSocket integration tests passed successfully!")
