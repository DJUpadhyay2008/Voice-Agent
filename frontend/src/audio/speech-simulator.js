/**
 * Speech Audio Simulator.
 * Generates synthetic human vocal speech audio at 16kHz Int16 PCM
 * to test Silero VAD turn detection without requiring a physical microphone.
 */
export class SpeechSimulator {
  constructor({ sampleRate = 16000, chunkSize = 512, onAudioChunk } = {}) {
    this.sampleRate = sampleRate;
    this.chunkSize = chunkSize;
    this.onAudioChunk = onAudioChunk;
    this.intervalId = null;
    this.phase = 0;
    this.isSimulating = false;
  }

  start() {
    if (this.isSimulating) return;
    this.isSimulating = true;
    this.phase = 0;

    // Send 512-sample PCM chunk every 32ms (approx 31.25 chunks/sec)
    this.intervalId = setInterval(() => {
      if (!this.isSimulating) return;

      const pcmData = new Int16Array(this.chunkSize);
      let sumSquares = 0;

      // Phrase cadence: 2.5 seconds speech, 1.5 seconds silence
      const cycleTime = ((this.phase / this.sampleRate) % 4.0);
      const isSpeakingTurn = cycleTime < 2.5;

      for (let i = 0; i < this.chunkSize; i++) {
        const t = (this.phase + i) / this.sampleRate;
        
        let sampleFloat = 0;
        if (isSpeakingTurn) {
          // Fundamental pitch vocal harmonics
          const f0 = 150.0 + 15.0 * Math.sin(2 * Math.PI * 2.0 * t);
          const v1 = 0.45 * Math.sin(2 * Math.PI * f0 * t);
          const v2 = 0.35 * Math.sin(2 * Math.PI * (f0 * 2) * t);
          const v3 = 0.20 * Math.sin(2 * Math.PI * (f0 * 3) * t);
          const v4 = 0.15 * Math.sin(2 * Math.PI * (f0 * 4) * t);
          
          sampleFloat = (v1 + v2 + v3 + v4) * 0.7;
        }

        const s = Math.max(-1, Math.min(1, sampleFloat));
        pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        sumSquares += s * s;
      }

      this.phase += this.chunkSize;
      const rms = Math.sqrt(sumSquares / this.chunkSize);

      if (this.onAudioChunk && pcmData.buffer) {
        this.onAudioChunk(pcmData.buffer, rms);
      }
    }, 32);
  }

  stop() {
    this.isSimulating = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}
