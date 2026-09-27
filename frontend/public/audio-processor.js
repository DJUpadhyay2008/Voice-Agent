/**
 * AudioWorkletProcessor for real-time 16kHz 16-bit Mono PCM audio capture.
 * Runs on the browser's dedicated high-priority audio rendering thread.
 */
class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    // Default chunk size is 512 samples (32ms at 16kHz)
    this.chunkSize = options?.processorOptions?.chunkSize || 512;
    this.buffer = new Float32Array(this.chunkSize);
    this.bufferIndex = 0;
    this.isRecording = true;

    this.port.onmessage = (event) => {
      if (event.data?.type === 'set_recording') {
        this.isRecording = event.data.isRecording;
        if (!this.isRecording) {
          this.bufferIndex = 0;
        }
      }
    };
  }

  process(inputs, outputs, parameters) {
    if (!this.isRecording) return true;

    const input = inputs[0];
    if (!input || input.length === 0) return true;

    // Mono: use first channel (channel 0)
    const channelData = input[0];
    if (!channelData) return true;

    for (let i = 0; i < channelData.length; i++) {
      this.buffer[this.bufferIndex++] = channelData[i];

      // When chunk is full (512 samples = 32ms), convert and emit
      if (this.bufferIndex >= this.chunkSize) {
        this.flushBuffer();
        this.bufferIndex = 0;
      }
    }

    return true;
  }

  flushBuffer() {
    const pcmData = new Int16Array(this.chunkSize);
    let sumSquares = 0;

    for (let i = 0; i < this.chunkSize; i++) {
      const s = Math.max(-1, Math.min(1, this.buffer[i]));
      sumSquares += s * s;
      // Convert Float32 [-1, 1] to Int16 [-32768, 32767]
      pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
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
