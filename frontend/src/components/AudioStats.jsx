import React from 'react';
import { Volume2, Cpu, Repeat, Clock } from 'lucide-react';

export function AudioStats({
  telemetry,
  chunksSent,
  pingMs,
  loopbackEnabled,
  onToggleLoopback,
  isCalling,
}) {
  return (
    <div className="w-full bg-neutral-900/40 border border-neutral-800 rounded-2xl p-4 text-xs font-mono space-y-3">
      <div className="flex items-center justify-between text-neutral-400 font-semibold border-b border-neutral-800/80 pb-2">
        <span className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-neutral-400" />
          Stream Telemetry (Milestone 1)
        </span>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={loopbackEnabled}
            disabled={isCalling}
            onChange={(e) => onToggleLoopback(e.target.checked)}
            className="rounded border-neutral-700 bg-neutral-800 text-emerald-500 focus:ring-0 cursor-pointer"
          />
          <span className={`text-[11px] flex items-center gap-1 ${loopbackEnabled ? 'text-emerald-400 font-bold' : 'text-neutral-500'}`}>
            <Repeat className="w-3 h-3" />
            Loopback Echo
          </span>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3 text-neutral-300">
        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Format</div>
          <div className="font-semibold text-neutral-200 mt-0.5">16kHz 16-bit Mono</div>
        </div>

        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Frame Size</div>
          <div className="font-semibold text-neutral-200 mt-0.5">512 smp (32ms)</div>
        </div>

        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Frames Sent / Received</div>
          <div className="font-semibold text-emerald-400 mt-0.5">
            {chunksSent} / {telemetry?.chunks_received || 0}
          </div>
        </div>

        <div className="bg-neutral-950/60 p-2.5 rounded-lg border border-neutral-800/50">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Server Signal Level</div>
          <div className="font-semibold text-neutral-200 mt-0.5 flex items-center gap-1.5">
            <Volume2 className="w-3 h-3 text-neutral-400" />
            {telemetry ? `${telemetry.db} dBFS` : '—'}
          </div>
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
