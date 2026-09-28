# Real-Time Voice Call Agent — Master Implementation Plan

> **Goal**: Build a production-grade, low-latency, real-time AI voice agent running locally in a web browser, designed for natural two-way conversations with barge-in / interruption support, modular provider architecture, and structured state.

---

## 1. Architectural Philosophy & Strategy

1. **Local-First Where Feasible**:
   - **VAD**: 100% Local via **Silero VAD (ONNX)**. Fast (~1–2 ms), zero API cost, runs on CPU.
   - **STT**: Dual-mode abstraction:
     - *Local Option*: **Faster-Whisper** (small.en / base.en) running locally on CPU / RTX 3050.
     - *Cloud Option*: **Deepgram Nova-2** or **Groq Whisper** for sub-200ms turnaround when API key is provided.
   - **TTS**: Dual-mode abstraction:
     - *Local Option*: **Piper TTS** or **Kokoro** (high speed, offline ONNX synthesis).
     - *Cloud Option*: **Cartesia Sonic** or **Deepgram Aura** / **ElevenLabs** for ultra-expressive streaming.
   - **LLM**: API-based streaming (Groq Llama-3.1/3.3, OpenAI GPT-4o-mini, or Gemini Flash) for ultra-low TTFT (<150ms), with an optional fallback to local **Ollama** (Llama-3.2-3B).

2. **Decoupled Architecture**:
   - **Transport Layer**: WebSocket (PCM audio chunks + JSON events). Can migrate to WebRTC or SIP later without changing the voice pipeline.
   - **Pipeline Engine**: Manages audio flow, turn detection, barge-in, and streaming sentence chunking.
   - **Provider Interfaces**: Clean Python ABCs (`VADProvider`, `STTProvider`, `LLMProvider`, `TTSProvider`) allowing instant swapping via `.env`.
   - **Frontend**: Clean React + Vite interface with Web Audio API (`AudioWorklet`) for raw PCM capture and playback.

---

## 2. Component Selection Matrix (Local vs API)

| Component | Default (Local-First Focus) | Cloud Alternative (API Key Enabled) | Latency Target |
| :--- | :--- | :--- | :--- |
| **Transport** | Browser WebSocket (FastAPI) | WebRTC (Milestone 15) | < 30 ms |
| **Audio Capture** | Web Audio API / AudioWorklet (16 kHz Int16 PCM) | Same | 32 ms chunks |
| **VAD** | **Silero VAD v5 (ONNX)** | Client-side WASM VAD | 1–3 ms |
| **STT** | **Faster-Whisper (base.en/small.en)** | **Deepgram Nova-2** / **Groq Whisper** | 150–500 ms |
| **LLM** | **Groq Llama-3.1-8B** / **OpenAI GPT-4o-mini** | Local Ollama (Llama-3.2) | 100–250 ms TTFT |
| **TTS** | **Piper TTS** / **Kokoro ONNX** | **Cartesia Sonic** / **Deepgram Aura** | 100–200 ms TTFA |
| **Playback** | Web Audio API Scheduled BufferSource Queue | Same | Gapless / Instant Flush |

---

## 3. Project Directory Structure

```
voice-agent/
├── IMPLEMENTATION_PLAN.md      # This master document
├── README.md                   # Setup & execution instructions
├── .env.example                # Configuration template
├── .gitignore
│
├── backend/
│   ├── main.py                 # FastAPI application & WebSocket routes
│   ├── config.py               # Pydantic Settings & environment loader
│   ├── logger.py               # Structured logging with millisecond timestamps
│   │
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── audio.py            # Audio utilities (PCM conversion, RMS, resamplers)
│   │   ├── vad.py              # VADProvider base + SileroVAD implementation
│   │   ├── stt.py              # STTProvider base + FasterWhisper / Deepgram
│   │   ├── tts.py              # TTSProvider base + Piper / Cartesia
│   │   └── pipeline.py         # Full bidirectional streaming coordinator & barge-in
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── llm.py              # LLMProvider base + Groq / OpenAI / Ollama
│   │   ├── state.py            # Conversation turn & session state
│   │   ├── chunker.py          # Sentence/clause streaming chunker for TTS
│   │   └── prompts.py          # Real-time voice persona & prompt templates
│   │
│   └── tests/                  # Unit and integration test scripts
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx             # Main container & layout
        ├── App.css
        │
        ├── audio/
        │   ├── audio-processor.js  # AudioWorkletProcessor (captures 16kHz Int16)
        │   ├── audio-player.js     # Gapless PCM audio queue & instant barge-in flush
        │   └── audio-manager.js    # Web Audio Context & stream coordinator
        │
        ├── components/
        │   ├── CallButton.jsx      # Start / Stop Call toggle
        │   ├── CallStatus.jsx      # Listening / Thinking / Speaking badge
        │   ├── Waveform.jsx        # Live mic and agent audio visualizer
        │   ├── Transcript.jsx      # Live conversation transcript stream
        │   └── LatencyStats.jsx    # Real-time latency metrics display
        │
        └── services/
            └── websocket.js        # Robust WebSocket client with auto-reconnect
```

---

## 4. Phase-by-Phase Roadmap

### Milestone 0: Architecture & Technical Decisions (Current)
- [x] Analyze master specification.
- [x] Inspect local environment and runtime prerequisites.
- [x] Define local vs. cloud provider trade-offs.
- [x] Formulate `IMPLEMENTATION_PLAN.md`.

---

### Milestone 1: Basic Audio Connection (Completed)
**Objective**: Solidify the audio transport pipeline between browser and FastAPI. No AI models yet.
- **Frontend**:
  - React + Vite setup.
  - Custom `AudioWorklet` capturing microphone input at 16 kHz 16-bit Mono PCM.
  - WebSocket service streaming binary PCM packets to backend.
  - Start / Stop Call controls with visual audio activity meter.
  - Connection status indicator (`Connecting`, `Connected`, `Disconnected`, `Error`).
- **Backend**:
  - FastAPI server with WebSocket endpoint `/ws/call/{session_id}`.
  - Binary frame handler validating sample rate, chunk sizes, and computing RMS volume.
  - Echo/Loopback test mode (optional parameter `?loopback=true` to verify full bidirectional playback in browser speakers).
  - Clean disconnect and resource teardown handling.
- **Verification Criteria**:
  - Microphone starts cleanly on user click.
  - Continuous binary frames stream over WebSocket.
  - Backend logs frame rate (~30 frames/sec) and RMS audio levels without buffer overflow or memory leaks.

---

### Milestone 2: Voice Activity Detection (VAD) (Completed)
**Objective**: Accurate real-time turn detection and speech boundary segmentation.
- Install and configure **Silero VAD v5** via ONNX Runtime on backend.
- Feed continuous 32ms (512 samples) or 64ms PCM chunks to VAD.
- Implement state machine:
  - `speech_start`: Triggered after $N$ consecutive voice frames (>0.5 probability).
  - `speech_continue`: Emits audio frame to speech buffer.
  - `speech_end`: Triggered after 300–400ms continuous silence.
- Emit JSON events (`{"type": "vad", "event": "speech_start" | "speech_end"}`) to frontend.
- **Verification Criteria**:
  - Frontend visualizer reflects "Speaking" when user talks, and returns to "Listening" after silence.

---

### Milestone 3: Speech-to-Text (STT) (Completed)
**Objective**: Transcribe user speech into text.
- Build `STTProvider` abstraction (`FasterWhisperSTTProvider` local & `DeepgramSTTProvider` cloud API option).
- Process completed utterance buffer accumulated during VAD `speech_start` $\to$ `speech_end`.
- UI displays real-time transcript history ("You: Hello...").
- Distinguish between interim partial transcripts and finalized user utterances.

---

### Milestone 4: LLM Integration
**Objective**: Connect finalized user transcript to streaming conversational LLM.
- Build `LLMProvider` abstraction.
- Implement streaming provider using **Groq** (Llama-3.1/3.3) or **OpenAI** (GPT-4o-mini).
- Build streaming sentence chunker (`chunker.py`) that slices tokens on boundary punctuation (`.`, `!`, `?`, `,`, `\n`) for immediate downstream TTS processing.
- Concise conversational system prompt tuned for voice interaction (avoid markdown asterisks, lists, or excessive verbiage).

---

### Milestone 5: Text-to-Speech (TTS)
**Objective**: Synthesize streaming sentence chunks into audio.
- Build `TTSProvider` abstraction.
- Implement:
  1. *Local Provider*: **Piper TTS** or **Kokoro ONNX**.
  2. *Cloud Provider*: **Cartesia Sonic** or **Deepgram Aura**.
- Stream synthesized audio chunks (PCM or MP3) over WebSocket to browser.
- Browser `AudioPlayer` queues and plays chunks gaplessly.

---

### Milestone 6: Complete Voice Loop & Latency Benchmarking
**Objective**: Full end-to-end conversation with latency instrumentation.
- Connect: Mic $\to$ VAD $\to$ STT $\to$ LLM $\to$ TTS $\to$ Speaker.
- Track and display latency metrics:
  - $T_{\text{VAD}}$: Silence detection window.
  - $T_{\text{STT}}$: Time from speech end to final text.
  - $\text{TTFT}$: LLM time-to-first-token.
  - $\text{TTFA}$: TTS time-to-first-audio chunk.
  - Total turn turnaround latency.

---

### Milestone 7: Barge-in / Interruption (Critical)
**Objective**: Allow user to interrupt agent speech at any time.
- If user speaks while agent state is `speaking`:
  1. Silero VAD flags `speech_start`.
  2. Server immediately sends `{"type": "clear_audio", "turn_id": N}` to frontend.
  3. Frontend immediately stops current audio playback and flushes its queue.
  4. Backend cancels running LLM generation task and running TTS stream.
  5. State switches cleanly to user speech ingestion.
- Implement Acoustic Echo Cancellation (AEC) and threshold gating to prevent agent from interrupting itself.

---

### Subsequent Milestones (V2 & Beyond)
- **Milestone 8**: Structured Conversation State & History.
- **Milestone 9**: LangGraph Integration with explicit tool calling.
- **Milestone 10**: Contextual Session Memory.
- **Milestone 11**: Polished UI/UX with animated waveforms & sound effects.
- **Milestone 12**: Observability & Session Replay.
- **Milestone 13**: Comprehensive Error Handling & Reconnect Resilience.
- **Milestone 14**: Security & Production Hardening.
- **Milestone 15**: WebRTC Media Transport Evaluation.
- **Milestone 16**: SIP / Telephony Gateway Integration.

---

## 5. Immediate Action Plan for Milestone 1

1. **Environment Setup**:
   - Install Node.js LTS in user environment for frontend tooling.
   - Set up Python virtual environment in `backend/` and install `fastapi`, `uvicorn`, `websockets`, `numpy`, `python-dotenv`.
2. **Backend**:
   - Implement `backend/main.py` with WebSocket `/ws/call/{session_id}`.
   - Implement audio chunk validation and RMS audio level calculation.
   - Implement optional loopback echo mode for audio testing.
3. **Frontend**:
   - Initialize React + Vite project in `frontend/`.
   - Implement `AudioWorklet` processor for 16 kHz 16-bit mono PCM capture.
   - Implement WebSocket connection management and basic visualizer UI.
4. **Testing**:
   - Verify continuous audio streaming over WebSocket with clean connect/disconnect lifecycle.
