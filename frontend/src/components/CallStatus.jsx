import React from 'react';
import { Wifi, WifiOff, Activity, Radio } from 'lucide-react';

export function CallStatus({ status, sessionId }) {
  const getStatusBadge = () => {
    switch (status) {
      case 'connected':
        return {
          icon: <Radio className="w-4 h-4 animate-pulse text-emerald-400" />,
          label: 'Connected & Streaming',
          className: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
        };
      case 'connecting':
        return {
          icon: <Activity className="w-4 h-4 animate-spin text-amber-400" />,
          label: 'Connecting...',
          className: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
        };
      case 'error':
        return {
          icon: <WifiOff className="w-4 h-4 text-rose-400" />,
          label: 'Connection Error',
          className: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
        };
      case 'disconnected':
      default:
        return {
          icon: <Wifi className="w-4 h-4 text-neutral-400" />,
          label: 'Ready to Call',
          className: 'bg-neutral-800/80 border-neutral-700 text-neutral-400',
        };
    }
  };

  const badge = getStatusBadge();

  return (
    <div className="flex items-center justify-between px-4 py-2.5 rounded-full border bg-neutral-900/60 backdrop-blur-md transition-all">
      <div className={`flex items-center gap-2 text-xs font-medium px-3 py-1 rounded-full border ${badge.className}`}>
        {badge.icon}
        <span>{badge.label}</span>
      </div>

      {sessionId && (
        <span className="text-[11px] font-mono text-neutral-500 tracking-wider">
          Session: {sessionId.slice(0, 8)}
        </span>
      )}
    </div>
  );
}
