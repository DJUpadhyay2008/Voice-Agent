import json
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["vad_provider"] == "SileroVADProvider (v4 ONNX)"
    assert data["stt_provider"] == "FasterWhisperSTTProvider"

def test_websocket_vad_and_stt_flow():
    client = TestClient(app)
    session_id = "test-vad-stt-session"
    
    with client.websocket_connect(f"/ws/call/{session_id}?loopback=false") as ws:
        # 1. Verify session created greeting
        init_msg = ws.receive_json()
        assert init_msg["type"] == "session_created"
        assert init_msg["config"]["vad"] == "silero_v4"
        assert init_msg["config"]["stt"] == "FasterWhisperSTTProvider"
        
        # 2. Send ping, receive pong
        ws.send_text(json.dumps({"type": "ping", "timestamp": 12345}))
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        
        # 3. Send silence chunk (512 samples)
        silence_pcm = bytes(1024)
        ws.send_bytes(silence_pcm)
        
        # 4. Stop call control message
        ws.send_text(json.dumps({"type": "stop_call"}))
        status = ws.receive_json()
        assert status["type"] == "call_status"
        assert status["status"] == "disconnected"

if __name__ == "__main__":
    test_health_endpoint()
    test_websocket_vad_and_stt_flow()
    print("All WebSocket VAD & STT integration tests passed successfully!")
