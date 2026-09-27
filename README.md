# Real-Time AI Voice Call Agent

A production-oriented, low-latency real-time voice call agent built with FastAPI, Web Audio API, and React.

---

## Current Status: Milestone 1 Completed (Basic Audio Connection)

The system currently implements **Milestone 1**:
- Browser microphone capture at **16 kHz 16-bit Mono PCM** via high-priority `AudioWorklet`.
- Full-duplex WebSocket connection between React frontend and FastAPI backend.
- Server-side frame validation, volume telemetry (RMS & dBFS), and clean disconnect lifecycle.
- Real-time animated canvas waveform visualizer.
- Optional loopback echo mode for end-to-end audio roundtrip testing.

---

## Project Structure

```
VoiceAgent/
├── IMPLEMENTATION_PLAN.md      # Master technical blueprint & roadmap
├── README.md                   # Setup and execution guide
├── .env.example                # Configuration template
├── .env                        # Local configuration
├── .gitignore
│
├── backend/
│   ├── main.py                 # FastAPI server & WebSocket endpoint (/ws/call)
│   ├── config.py               # Pydantic Settings configuration
│   ├── logger.py               # Structured logging with millisecond timestamps
│   ├── requirements.txt        # Python backend dependencies
│   ├── voice/
│   │   ├── __init__.py
│   │   └── audio.py            # PCM validation, RMS volume, and audio converters
│   └── tests/
│       ├── test_audio.py       # Audio mathematics & conversion unit tests
│       └── test_websocket.py   # WebSocket audio streaming integration tests
│
└── frontend/
    ├── package.json
    ├── vite.config.js          # Vite config with Tailwind CSS plugin
    ├── index.html
    ├── public/
    │   └── audio-processor.js  # AudioWorkletProcessor for zero-copy 16-bit PCM capture
    └── src/
        ├── main.jsx
        ├── App.jsx             # Main interactive call interface
        ├── index.css           # Styling
        ├── audio/
        │   ├── audio-manager.js# Web Audio coordinator
        │   └── audio-player.js # Gapless PCM player with instant flush support
        ├── components/
        │   ├── CallButton.jsx  # Start/Stop call toggle button
        │   ├── CallStatus.jsx  # Connection status badge
        │   ├── Waveform.jsx    # Real-time animated canvas audio wave
        │   └── AudioStats.jsx  # Live stream metrics and loopback toggle
        └── services/
            └── websocket.js    # Resilient WebSocket streaming client
```

---

## Quick Start & Running Locally

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 2. Backend Setup & Startup
In a terminal, start the FastAPI server:
```bash
# From the project root
export PYTHONPATH=.
backend/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend will be live at `http://localhost:8000` (Health check at `http://localhost:8000/health`).

### 3. Frontend Startup
In a second terminal, start the Vite development server:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## How to Test Milestone 1

1. Open `http://localhost:5173` in Chrome, Firefox, or Brave.
2. (Optional) Check the **"Loopback Echo"** checkbox to hear your voice echoed back from the server with sub-50ms latency.
3. Click **"Start Voice Call"**.
4. Grant microphone access when prompted by the browser.
5. Speak into your microphone:
   - Observe the green animated waveform reacting dynamically to your voice.
   - Observe the live audio telemetry: frames sent, frames received by the server, and signal level in dBFS.
   - Check the backend console to see continuous framed audio validation logs.
6. Click **"End Call"** to verify clean stream teardown and WebSocket disconnect.

---

## Running Automated Tests

Run the test suite from the project root:
```bash
# Audio unit tests
PYTHONPATH=. backend/venv/bin/python backend/tests/test_audio.py

# WebSocket integration tests
PYTHONPATH=. backend/venv/bin/python backend/tests/test_websocket.py
```

---

## Next Milestone: Milestone 2 — Voice Activity Detection (VAD)
Adding **Silero VAD (ONNX)** on the backend to detect `speech_start`, `speech_continue`, and silence endpointing (`speech_end`).
