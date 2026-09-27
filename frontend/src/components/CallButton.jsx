import React from 'react';
import { Phone, PhoneOff, Loader2 } from 'lucide-react';

export function CallButton({ isCalling, isLoading, onStart, onStop }) {
  if (isCalling) {
    return (
      <button
        onClick={onStop}
        disabled={isLoading}
        className="group relative flex items-center justify-center gap-3 px-8 py-4 rounded-full font-semibold text-white bg-rose-600 hover:bg-rose-500 active:scale-95 transition-all duration-200 shadow-lg shadow-rose-600/30 cursor-pointer disabled:opacity-50"
      >
        <span className="absolute -inset-1 rounded-full bg-rose-500/20 animate-ping group-hover:bg-rose-500/30 pointer-events-none" />
        <PhoneOff className="w-5 h-5 text-white" />
        <span>End Call</span>
      </button>
    );
  }

  return (
    <button
      onClick={onStart}
      disabled={isLoading}
      className="group flex items-center justify-center gap-3 px-8 py-4 rounded-full font-semibold text-white bg-emerald-600 hover:bg-emerald-500 active:scale-95 transition-all duration-200 shadow-lg shadow-emerald-600/30 cursor-pointer disabled:opacity-50"
    >
      {isLoading ? (
        <>
          <Loader2 className="w-5 h-5 animate-spin text-white" />
          <span>Starting Call...</span>
        </>
      ) : (
        <>
          <Phone className="w-5 h-5 text-white group-hover:rotate-12 transition-transform" />
          <span>Start Voice Call</span>
        </>
      )}
    </button>
  );
}
