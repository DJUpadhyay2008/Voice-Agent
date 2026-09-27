/**
 * AudioWorkletProcessor with automatic linear interpolation resampling.
 * Resamples native browser hardware input (e.g., 44.1kHz or 48kHz) down to 16kHz Int16 PCM.
 * Runs on the browser's dedicated high-priority audio rendering thread.
 */
class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetSampleRate = options?.processorOptions?.targetSampleRate || 16000;
    this.chunkSize = options?.processorOptions?.chunkSize || 512; // 512 samples at 16kHz (32ms)

    // Global sampleRate variable provided by AudioWorkletGlobalScope
    this.inputSampleRate = sampleRate || 48000;
    this.ratio = this.inputSampleRate / this.targetSampleRate;
    
    this.outputBuffer = new Int16Array(this.chunkSize);
    this.outputIndex = 0;
    this.inputOffset = 0.0;
    this.lastSample = 0.0;
    this.isRecording = true;

    this.port.onmessage = (event) => {
      if (event.data?.type === 'set_recording') {
        this.isRecording = event.data.isRecording;
        if (!this.isRecording) {
          this.outputIndex = 0;
          this.inputOffset = 0.0;
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

    const inputLength = channelData.length;

    // Resample from inputSampleRate down to targetSampleRate (16000 Hz)
    while (this.inputOffset < inputLength) {
      const index = Math.floor(this.inputOffset);
      const nextIndex = Math.min(index + 1, inputLength - 1);
      const weight = this.inputOffset - index;

      const sample1 = channelData[index];
      const sample2 = channelData[nextIndex];
      const interpolated = sample1 + (sample2 - sample1) * weight;

      // Clamp to [-1.0, 1.0] and convert to 16-bit Int16 [-32768, 32767]
      const s = Math.max(-1, Math.min(1, interpolated));
      this.outputBuffer[this.outputIndex++] = s < 0 ? s * 0x8000 : s * 0x7fff;

      // When output buffer reaches chunkSize (512 samples = 32ms), emit PCM chunk
      if (this.outputIndex >= this.chunkSize) {
        this.flushBuffer();
        this.outputIndex = 0;
      }

      this.inputOffset += this.ratio;
    }

    // Wrap offset relative to next input block
    this.inputOffset -= inputLength;

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
