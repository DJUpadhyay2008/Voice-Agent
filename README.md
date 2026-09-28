# Real-Time AI Voice Call Agent

A production-grade, low-latency, real-time AI voice call agent built with FastAPI, Web Audio API, Faster-Whisper, Silero VAD, and React.

---

## Current Status: Milestone 3 Completed (Speech-to-Text) & Milestone 4 LLM Foundation

The system currently implements **Milestones 1, 2 & 3**, with initial foundational work for **Milestone 4**:

- **Audio Transport & Worklet**: Browser microphone capture at **16 kHz 16-bit Mono PCM** via zero-copy `AudioWorklet`, streaming over full-duplex WebSockets.
- **Voice Activity Detection (VAD)**: Server-side real-time **Silero VAD (ONNX)** turn detection (< 2ms CPU inference per frame) with 400ms silence endpointing.
- **Speech-to-Text (STT)**: Dual-mode provider architecture:
  - *Local Mode*: **Faster-Whisper (tiny.en / base.en)** running on CPU (`int8`) with ~250–300 ms turn transcription turnaround.
  - *Cloud Mode*: **Deepgram Nova-2** REST / WebSocket provider when `DEEPGRAM_API_KEY` is configured.
- **Live Transcript UI**: Reactive speech transcript stream displaying user utterances in real-time ("You: Hello...").
- **LLM Provider Abstraction**: Extensible `LLMProvider` with streaming support for **Groq** (`llama-3.1-8b-instant`) and **OpenAI** (`gpt-4o-mini`).
- **Testing & Simulation**: Full automated test suite for audio math, VAD state machine, WebSocket handler, STT transcription, and LLM token streaming, plus a frontend speech simulator for headless testing.

---

## Project Structure

```
VoiceAgent/
├── IMPLEMENTATION_PLAN.md      # Master technical blueprint & phase roadmap
├── README.md                   # Setup and execution guide
├── .env.example                # Configuration template
├── .env                        # Local environment settings
├── .gitignore
│
├── backend/
│   ├── main.py                 # FastAPI server & WebSocket endpoint (/ws/call/{session_id})
│   ├── config.py               # Pydantic Settings configuration loader
│   ├── logger.py               # Structured logging with millisecond timestamps
│   ├── requirements.txt        # Python backend dependencies
│   │
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── audio.py            # PCM validation, RMS volume calculation, and audio converters
│   │   ├── vad.py              # Silero VAD ONNX wrapper & turn state machine
│   │   └── stt.py              # STTProvider base + FasterWhisper & Deepgram implementations
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   └── llm.py              # LLMProvider base + Groq & OpenAI streaming providers
│   │
│   └── tests/
│       ├── hello.wav           # Standard test audio sample
│       ├── test_audio.py       # Audio mathematics & conversion unit tests
│       ├── test_vad.py         # Silero VAD state transition tests
│       ├── test_websocket.py   # WebSocket endpoint integration tests
│       ├── test_stt.py         # FasterWhisper STT unit test
│       └── test_llm.py         # LLM Provider & dataclass unit tests
│
└── frontend/
    ├── package.json
    ├── vite.config.js          # Vite configuration with Tailwind CSS
    ├── index.html
    ├── public/
    │   └── audio-processor.js  # AudioWorkletProcessor for zero-copy 16-bit PCM capture
    └── src/
        ├── main.jsx
        ├── App.jsx             # Main interactive call interface & transcript stream
        ├── index.css           # Styling
        ├── audio/
        │   ├── audio-manager.js# Web Audio API coordinator
        │   ├── audio-player.js # Gapless PCM player with instant flush support
        │   └── speech-simulator.js # Synthetic speech generator for testing
        ├── components/
        │   ├── CallButton.jsx  # Start/Stop call toggle button
        │   ├── CallStatus.jsx  # Listening / Speaking / Status badge
        │   ├── Waveform.jsx    # Real-time animated canvas audio wave
        │   ├── AudioStats.jsx  # Live stream metrics and loopback toggle
        │   └── Transcript.jsx  # Real-time transcript list component
        └── services/
            └── websocket.js    # Resilient WebSocket streaming client
```

---

## Quick Start & Running Locally

### 1. Prerequisites
- **Python**: 3.11+ (virtual environment in `backend/venv`)
- **Node.js**: 18+ and `npm`

### 2. Backend Setup & Startup
Start the FastAPI backend server:
```bash
# From the project root directory
export PYTHONPATH=.
backend/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend will run at `http://localhost:8000` (Health check at `http://localhost:8000/health`).

### 3. Frontend Startup
In a separate terminal, start the Vite development server:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## How to Test Speech-to-Text (Milestone 3)

1. Open `http://localhost:5173` in Chrome, Firefox, or Brave.
2. Click **"Start Voice Call"** and grant microphone permissions.
3. Speak clearly into your microphone (e.g. *"Hello, how are you today?"*).
4. Observe:
   - Status changes from **Listening** to **User Speaking** when speech starts.
   - Upon silence (~400ms), VAD triggers `speech_end` and sends the speech buffer to Faster-Whisper.
   - The transcript panel displays **"You: Hello, how are you today?"** within ~300ms.
5. Click **"End Call"** to stop the session.

---

## Running Automated Tests

Run all unit and integration tests from the project root:

```bash
# Execute the full test suite
PYTHONPATH=. backend/venv/bin/python backend/tests/test_audio.py && \
PYTHONPATH=. backend/venv/bin/python backend/tests/test_vad.py && \
PYTHONPATH=. backend/venv/bin/python backend/tests/test_websocket.py && \
PYTHONPATH=. backend/venv/bin/python backend/tests/test_stt.py && \
PYTHONPATH=. backend/venv/bin/python backend/tests/test_llm.py
```

---

## Next Roadmap Items

- **Milestone 4: LLM Integration**: Stream LLM tokens from Groq / OpenAI into a streaming sentence chunker.
- **Milestone 5: Text-to-Speech (TTS)**: Synthesize audio chunks via Piper / Cartesia for low-latency voice output.
- **Milestone 6: Complete Voice Loop & Benchmarking**: End-to-end turn turnaround metrics display.
- **Milestone 7: Barge-in / Interruption**: Immediate server-driven audio flush when user interrupts agent speech.
