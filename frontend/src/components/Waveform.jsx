import React, { useEffect, useRef } from 'react';

export function Waveform({ rms = 0, isCalling = false }) {
  const canvasRef = useRef(null);
  const animFrameRef = useRef(null);
  const smoothedRmsRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let phase = 0;

    const render = () => {
      // Smooth interpolation for visual fluidity
      smoothedRmsRef.current += (rms - smoothedRmsRef.current) * 0.25;
      const effectiveRms = isCalling ? Math.max(0.04, smoothedRmsRef.current) : 0.01;

      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      const numBars = 32;
      const barWidth = 3;
      const spacing = (width - numBars * barWidth) / (numBars + 1);

      for (let i = 0; i < numBars; i++) {
        const x = spacing + i * (barWidth + spacing);
        // Harmonic fluctuation
        const wave = Math.sin(phase + (i / numBars) * Math.PI * 2);
        const wave2 = Math.cos(phase * 1.5 + (i / numBars) * Math.PI * 4);
        const barHeight = Math.min(
          height * 0.85,
          Math.max(4, (effectiveRms * 120 + 4) * (0.6 + 0.4 * wave * wave2))
        );

        const y = centerY - barHeight / 2;

        // Gradient coloring based on call state
        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        if (isCalling) {
          gradient.addColorStop(0, 'rgba(16, 185, 129, 0.9)'); // emerald-500
          gradient.addColorStop(0.5, 'rgba(52, 211, 153, 1)'); // emerald-400
          gradient.addColorStop(1, 'rgba(16, 185, 129, 0.4)');
        } else {
          gradient.addColorStop(0, 'rgba(115, 115, 115, 0.3)');
          gradient.addColorStop(1, 'rgba(82, 82, 82, 0.1)');
        }

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }

      phase += isCalling ? 0.08 : 0.02;
      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [rms, isCalling]);

  return (
    <div className="w-full flex flex-col items-center justify-center p-6 bg-neutral-900/40 border border-neutral-800 rounded-2xl backdrop-blur-sm">
      <canvas
        ref={canvasRef}
        width={360}
        height={90}
        className="w-full max-w-[360px] h-[90px]"
      />
      <div className="mt-2 text-xs font-mono text-neutral-400">
        {isCalling ? (
          <span className="text-emerald-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            Audio Input: {(rms * 100).toFixed(1)}% RMS
          </span>
        ) : (
          <span className="text-neutral-500">Microphone idle</span>
        )}
      </div>
    </div>
  );
}
