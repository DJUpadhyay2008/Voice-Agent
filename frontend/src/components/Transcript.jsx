import React, { useEffect, useRef } from 'react';
import { User, Bot, MessageSquare, CheckCircle2, Zap } from 'lucide-react';

export function Transcript({ transcripts = [] }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [transcripts]);

  if (!transcripts || transcripts.length === 0) {
    return (
      <div className="w-full bg-neutral-900/40 border border-neutral-800 rounded-2xl p-6 flex flex-col items-center justify-center text-center space-y-2 min-h-[140px]">
        <MessageSquare className="w-6 h-6 text-neutral-600" />
        <p className="text-xs text-neutral-400 font-medium">No transcripts yet</p>
        <p className="text-[11px] text-neutral-500 max-w-xs">
          Speak into your microphone or toggle "Test Audio" to see real-time Speech-to-Text transcription.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full bg-neutral-900/40 border border-neutral-800 rounded-2xl p-4 flex flex-col space-y-3">
      <div className="flex items-center justify-between text-neutral-400 font-semibold border-b border-neutral-800/80 pb-2 text-xs font-mono">
        <span className="flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-neutral-400" />
          Live Transcripts (Milestone 3)
        </span>
        <span className="text-[11px] text-neutral-500 font-normal">
          {transcripts.length} {transcripts.length === 1 ? 'turn' : 'turns'}
        </span>
      </div>

      <div
        ref={containerRef}
        className="w-full max-h-[220px] overflow-y-auto space-y-3 pr-1 scrollbar-thin scrollbar-thumb-neutral-800"
      >
        {transcripts.map((t, idx) => (
          <div
            key={idx}
            className={`flex flex-col space-y-1.5 p-3 rounded-xl border transition-all ${
              t.role === 'user'
                ? 'bg-emerald-500/5 border-emerald-500/20 ml-4'
                : 'bg-neutral-800/40 border-neutral-700/50 mr-4'
            }`}
          >
            <div className="flex items-center justify-between text-[11px]">
              <span className="flex items-center gap-1.5 font-semibold text-neutral-300">
                {t.role === 'user' ? (
                  <>
                    <User className="w-3.5 h-3.5 text-emerald-400" />
                    <span>You</span>
                  </>
                ) : (
                  <>
                    <Bot className="w-3.5 h-3.5 text-sky-400" />
                    <span>Agent</span>
                  </>
                )}
              </span>

              <div className="flex items-center gap-2 text-[10px] text-neutral-500 font-mono">
                {t.duration_ms && (
                  <span className="flex items-center gap-0.5 text-neutral-400">
                    <Zap className="w-2.5 h-2.5 text-amber-400" />
                    {t.duration_ms}ms
                  </span>
                )}
                {t.confidence && (
                  <span className="flex items-center gap-0.5 text-emerald-400">
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    {(t.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>

            <p className="text-xs text-neutral-100 font-sans leading-relaxed tracking-wide">
              "{t.text}"
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
