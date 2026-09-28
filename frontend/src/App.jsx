import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AudioManager } from './audio/audio-manager';
import { SpeechSimulator } from './audio/speech-simulator';
import { VoiceWebSocketClient } from './services/websocket';
import { CallButton } from './components/CallButton';
import { CallStatus } from './components/CallStatus';
import { Waveform } from './components/Waveform';
import { AudioStats } from './components/AudioStats';
import { Transcript } from './components/Transcript';
import { Bot, AlertCircle } from 'lucide-react';

export function App() {
  const [isCalling, setIsCalling] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('disconnected');
  const [sessionId, setSessionId] = useState(null);
  const [rms, setRms] = useState(0);
  const [chunksSent, setChunksSent] = useState(0);
  const [telemetry, setTelemetry] = useState(null);
  const [pingMs, setPingMs] = useState(null);
  const [loopbackEnabled, setLoopbackEnabled] = useState(false);
  const [isSimulatingSpeech, setIsSimulatingSpeech] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);

  const audioManagerRef = useRef(null);
  const speechSimulatorRef = useRef(null);
  const wsClientRef = useRef(null);
  const pingIntervalRef = useRef(null);

  // Ping interval for RTT calculation
  const startPingInterval = useCallback((wsClient) => {
    pingIntervalRef.current = setInterval(() => {
      if (wsClient && wsClient.isConnected) {
        wsClient.sendJson({ type: 'ping', timestamp: Date.now() });
      }
    }, 2000);
  }, []);

  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const handleStopCall = useCallback(() => {
    stopPingInterval();

    if (speechSimulatorRef.current) {
      speechSimulatorRef.current.stop();
      speechSimulatorRef.current = null;
    }

    if (wsClientRef.current) {
      wsClientRef.current.sendJson({ type: 'stop_call' });
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }

    if (audioManagerRef.current) {
      audioManagerRef.current.stop();
      audioManagerRef.current = null;
    }

    setIsCalling(false);
    setIsLoading(false);
    setStatus('disconnected');
    setRms(0);
    setPingMs(null);
  }, [stopPingInterval]);

  const handleStartCall = async () => {
    setErrorMessage(null);
    setIsLoading(true);
    setStatus('connecting');

    try {
      const newSessionId = (typeof crypto.randomUUID === 'function')
        ? crypto.randomUUID()
        : 'session-' + Date.now();
      setSessionId(newSessionId);
      setChunksSent(0);
      setTelemetry(null);
      setTranscripts([]);

      // 1. If not using synthetic test audio, start browser microphone
      if (!isSimulatingSpeech) {
        const audioManager = new AudioManager({
          sampleRate: 16000,
          chunkSize: 512,
          onAudioChunk: (pcmBuffer) => {
            if (wsClientRef.current?.isConnected) {
              wsClientRef.current.sendAudio(pcmBuffer);
              setChunksSent((prev) => prev + 1);
            }
          },
          onRmsUpdate: (val) => {
            setRms(val);
          },
        });
        audioManagerRef.current = audioManager;
        await audioManager.start();
      }

      // 2. Connect WebSocket
      const wsUrl = `ws://${window.location.hostname}:8000/ws/call/${newSessionId}?loopback=${loopbackEnabled}`;
      const wsClient = new VoiceWebSocketClient({
        url: wsUrl,
        onOpen: () => {
          setStatus('connected');
          setIsCalling(true);
          setIsLoading(false);
          wsClient.sendJson({ type: 'start_call' });
          startPingInterval(wsClient);

          // If synthetic test audio is active, start simulator
          if (isSimulatingSpeech) {
            const simulator = new SpeechSimulator({
              sampleRate: 16000,
              chunkSize: 512,
              onAudioChunk: (pcmBuffer, simRms) => {
                if (wsClientRef.current?.isConnected) {
                  wsClientRef.current.sendAudio(pcmBuffer);
                  setChunksSent((prev) => prev + 1);
                  setRms(simRms);
                }
              },
            });
            speechSimulatorRef.current = simulator;
            simulator.start();
          }
        },
        onClose: () => {
          handleStopCall();
        },
        onError: () => {
          setErrorMessage('WebSocket connection failed. Verify backend server is running on port 8000.');
          handleStopCall();
          setStatus('error');
        },
        onBinaryMessage: (arrayBuffer) => {
          if (audioManagerRef.current) {
            audioManagerRef.current.playIncomingChunk(arrayBuffer);
          }
        },
        onJsonMessage: (data) => {
          if (data.type === 'audio_telemetry') {
            setTelemetry(data);
          } else if (data.type === 'vad') {
            if (data.event === 'speech_start') {
              setStatus('user_speaking');
            } else if (data.event === 'speech_end') {
              setStatus('listening');
            }
          } else if (data.type === 'transcript') {
            setTranscripts((prev) => [...prev, {
              role: data.role || 'user',
              text: data.text,
              confidence: data.confidence,
              duration_ms: data.duration_ms,
              is_final: data.is_final,
            }]);
          } else if (data.type === 'call_status') {
            setStatus(data.status);
          } else if (data.type === 'pong' && data.client_time) {
            setPingMs(Date.now() - data.client_time);
          }
        },
      });

      wsClientRef.current = wsClient;
      wsClient.connect();
    } catch (err) {
      console.error('Failed to start call:', err);
      let errorMsg = 'Could not access microphone.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errorMsg = 'Microphone permission denied. Please grant microphone access in browser settings.';
      } else if (err.message) {
        errorMsg = err.message;
      }
      setErrorMessage(errorMsg);
      handleStopCall();
      setStatus('error');
    }
  };

  useEffect(() => {
    return () => {
      handleStopCall();
    };
  }, [handleStopCall]);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center justify-center p-4 antialiased selection:bg-emerald-500/30">
      <div className="w-full max-w-md flex flex-col items-center space-y-6">
        
        {/* App Header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-inner">
            <Bot className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white">Real-Time Voice Agent</h1>
          <p className="text-xs text-neutral-400 max-w-xs">
            Milestone 3 — Speech-to-Text (STT) & Real-Time Transcription
          </p>
        </div>

        {/* Status Badge */}
        <div className="w-full">
          <CallStatus status={status} sessionId={sessionId} />
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="w-full flex items-start gap-2.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Waveform Visualizer */}
        <Waveform rms={rms} isCalling={isCalling} />

        {/* Action Call Button */}
        <div className="py-1">
          <CallButton
            isCalling={isCalling}
            isLoading={isLoading}
            onStart={handleStartCall}
            onStop={handleStopCall}
          />
        </div>

        {/* Live Conversation Transcript Card */}
        <div className="w-full">
          <Transcript transcripts={transcripts} />
        </div>

        {/* Audio Telemetry Card */}
        <AudioStats
          telemetry={telemetry}
          chunksSent={chunksSent}
          pingMs={pingMs}
          loopbackEnabled={loopbackEnabled}
          onToggleLoopback={setLoopbackEnabled}
          isSimulatingSpeech={isSimulatingSpeech}
          onToggleSimulateSpeech={setIsSimulatingSpeech}
          isCalling={isCalling}
        />

        {/* Footer Note */}
        <div className="text-[11px] text-neutral-500 text-center space-y-1">
          <div>Next Phase: Milestone 4 — LLM Conversational Brain</div>
        </div>

      </div>
    </div>
  );
}

export default App;
