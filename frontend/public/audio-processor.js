/**
 * AudioWorkletProcessor with continuous ring-buffer linear interpolation resampling.
 * Seamlessly resamples native hardware input (44.1kHz / 48kHz) down to 16kHz Int16 PCM
 * without block-boundary click artifacts.
 */
class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetSampleRate = options?.processorOptions?.targetSampleRate || 16000;
    this.chunkSize = options?.processorOptions?.chunkSize || 512; // 512 samples at 16kHz (32ms)

    // Hardware sample rate in AudioWorkletGlobalScope
    this.inputSampleRate = sampleRate || 48000;
    this.ratio = this.inputSampleRate / this.targetSampleRate;

    // Continuous ring buffer (capacity 16384 samples)
    this.bufferSize = 16384;
    this.ringBuffer = new Float32Array(this.bufferSize);
    this.writePos = 0;
    this.readPos = 0;
    this.availableSamples = 0;

    this.outputBuffer = new Int16Array(this.chunkSize);
    this.outputIndex = 0;
    this.isRecording = true;

    this.port.onmessage = (event) => {
      if (event.data?.type === 'set_recording') {
        this.isRecording = event.data.isRecording;
        if (!this.isRecording) {
          this.outputIndex = 0;
          this.writePos = 0;
          this.readPos = 0;
          this.availableSamples = 0;
        }
      }
    };
  }

  process(inputs, outputs, parameters) {
    if (!this.isRecording) return true;

    const input = inputs[0];
    if (!input || input.length === 0) return true;
    const channelData = input[0];
    if (!channelData || channelData.length === 0) return true;

    // 1. Write incoming samples into ring buffer
    for (let i = 0; i < channelData.length; i++) {
      this.ringBuffer[this.writePos] = channelData[i];
      this.writePos = (this.writePos + 1) % this.bufferSize;
      this.availableSamples++;
    }

    // 2. Resample from ring buffer at 16000 Hz target rate
    while (this.availableSamples >= 2) {
      const idx0 = Math.floor(this.readPos) % this.bufferSize;
      const idx1 = (idx0 + 1) % this.bufferSize;
      const frac = this.readPos - Math.floor(this.readPos);

      const s0 = this.ringBuffer[idx0];
      const s1 = this.ringBuffer[idx1];
      const interpolated = s0 + (s1 - s0) * frac;

      // Clamp to [-1.0, 1.0] and convert to 16-bit Int16 [-32768, 32767]
      const s = Math.max(-1, Math.min(1, interpolated));
      this.outputBuffer[this.outputIndex++] = s < 0 ? s * 0x8000 : s * 0x7fff;

      // Emit chunk when 512 samples are accumulated
      if (this.outputIndex >= this.chunkSize) {
        this.flushBuffer();
        this.outputIndex = 0;
      }

      this.readPos = (this.readPos + this.ratio) % this.bufferSize;
      this.availableSamples -= this.ratio;
    }

    return true;
  }

  flushBuffer() {
    let sumSquares = 0;
    const pcmData = new Int16Array(this.chunkSize);

    for (let i = 0; i < this.chunkSize; i++) {
      const val = this.outputBuffer[i];
      pcmData[i] = val;
      const norm = val / 32768.0;
      sumSquares += norm * norm;
    }

    const rms = Math.sqrt(sumSquares / this.chunkSize);

    // Transfer the underlying ArrayBuffer zero-copy
    this.port.postMessage(
      {
        type: 'audio_chunk',
        pcm: pcmData.buffer,
        rms: rms,
      },
      [pcmData.buffer]
    );
  }
}

registerProcessor('audio-capture-processor', AudioCaptureProcessor);
