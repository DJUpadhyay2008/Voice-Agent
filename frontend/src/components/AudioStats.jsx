import React from 'react';
import { Volume2, Cpu, Repeat, Clock, Mic, Sparkles } from 'lucide-react';

export function AudioStats({
  telemetry,
  chunksSent,
  pingMs,
  loopbackEnabled,
  onToggleLoopback,
  isSimulatingSpeech,
  onToggleSimulateSpeech,
  isCalling,
}) {
  const vadProb = telemetry?.vad_prob ?? 0;
  const isSpeech = telemetry?.vad_speech ?? false;

  return (
    <div className="w-full bg-neutral-900/40 border border-neutral-800 rounded-2xl p-4 text-xs font-mono space-y-3">
      <div className="flex items-center justify-between text-neutral-400 font-semibold border-b border-neutral-800/80 pb-2">
        <span className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-neutral-400" />
          Stream Telemetry & VAD
        </span>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={loopbackEnabled}
              disabled={isCalling}
              onChange={(e) => onToggleLoopback(e.target.checked)}
              className="rounded border-neutral-700 bg-neutral-800 text-emerald-500 focus:ring-0 cursor-pointer"
            />
            <span className={`text-[11px] flex items-center gap-1 ${loopbackEnabled ? 'text-emerald-400 font-bold' : 'text-neutral-500'}`}>
              <Repeat className="w-3 h-3" />
              Loopback
            </span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isSimulatingSpeech}
              onChange={(e) => onToggleSimulateSpeech(e.target.checked)}
              className="rounded border-neutral-700 bg-neutral-800 text-amber-500 focus:ring-0 cursor-pointer"
            />
            <span className={`text-[11px] flex items-center gap-1 ${isSimulatingSpeech ? 'text-amber-400 font-bold' : 'text-neutral-500'}`}>
              <Sparkles className="w-3 h-3 text-amber-400" />
              Test Audio
            </span>
          </label>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-neutral-300">
        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Audio Source</div>
          <div className="font-semibold text-neutral-200 mt-0.5">
            {isSimulatingSpeech ? 'Synthetic Test Audio' : 'Microphone Stream'}
          </div>
        </div>

        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">VAD Speech Detector</div>
          <div className="font-semibold mt-0.5 flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isSpeech ? 'bg-emerald-400 animate-ping' : 'bg-neutral-600'}`} />
            <span className={isSpeech ? 'text-emerald-400 font-bold' : 'text-neutral-400'}>
              {isSpeech ? 'SPEECH ACTIVE' : 'Silence'}
            </span>
          </div>
        </div>

        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Frames Sent / Received</div>
          <div className="font-semibold text-emerald-400 mt-0.5">
            {chunksSent} / {telemetry?.chunks_received || 0}
          </div>
        </div>

        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Signal Level & VAD Prob</div>
          <div className="font-semibold text-neutral-200 mt-0.5 flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Volume2 className="w-3 h-3 text-neutral-400" />
              {telemetry ? `${telemetry.db} dB` : '—'}
            </span>
            <span className={`text-[11px] font-mono ${vadProb >= 0.5 ? 'text-emerald-400 font-bold' : 'text-neutral-400'}`}>
              {(vadProb * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* VAD Confidence Bar */}
      <div className="space-y-1 pt-0.5">
        <div className="flex justify-between text-[10px] text-neutral-500">
          <span>Silero VAD Confidence</span>
          <span className={vadProb >= 0.5 ? 'text-emerald-400 font-bold' : 'text-neutral-500'}>
            {(vadProb * 100).toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-150 ${vadProb >= 0.5 ? 'bg-emerald-400' : 'bg-neutral-500'}`}
            style={{ width: `${Math.min(100, vadProb * 100)}%` }}
          />
        </div>
      </div>

      {pingMs !== null && (
        <div className="flex items-center justify-between text-[11px] text-neutral-500 pt-1">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" /> WebSocket RTT Latency:
          </span>
          <span className="text-emerald-400 font-semibold">{pingMs} ms</span>
        </div>
      )}
    </div>
  );
}
