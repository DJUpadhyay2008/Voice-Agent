/**
 * Speech Audio Simulator.
 * Generates synthetic human vocal formant audio at 16kHz Int16 PCM
 * to test VAD turn detection without requiring a physical microphone.
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

      for (let i = 0; i < this.chunkSize; i++) {
        const t = (this.phase + i) / this.sampleRate;
        
        // Fundamental vocal frequency (130 Hz male / 220 Hz female formant mixture)
        const f0 = 130.0 + 10.0 * Math.sin(2 * Math.PI * 1.5 * t);
        
        // Formants: F1 (500 Hz), F2 (1500 Hz), F3 (2500 Hz) with pitch modulation
        const v1 = 0.50 * Math.sin(2 * Math.PI * f0 * t);
        const v2 = 0.30 * Math.sin(2 * Math.PI * (f0 * 2) * t);
        const v3 = 0.15 * Math.sin(2 * Math.PI * (f0 * 4) * t);
        const v4 = 0.10 * Math.sin(2 * Math.PI * 500 * t) * Math.sin(2 * Math.PI * f0 * t);

        // Amplitude envelope (speech phrase cadence: 2s speech, 1s pause)
        const phraseCadence = Math.sin(2 * Math.PI * 0.4 * t);
        const speechEnvelope = phraseCadence > -0.2 ? Math.max(0.05, Math.min(1.0, (phraseCadence + 0.2) * 2.0)) : 0.0;

        const sampleFloat = (v1 + v2 + v3 + v4) * speechEnvelope * 0.6;
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
