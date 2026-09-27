/**
 * Gapless PCM Audio Player using Web Audio API.
 * Schedules audio buffers smoothly on the AudioContext timeline.
 * Supports instantaneous flushing on barge-in / interruption.
 */
export class AudioPlayer {
  constructor(sampleRate = 16000) {
    this.sampleRate = sampleRate;
    this.audioContext = null;
    this.nextStartTime = 0;
    this.activeSources = new Set();
    this.isPlaying = false;
  }

  async init(existingContext = null) {
    if (existingContext) {
      this.audioContext = existingContext;
    } else if (!this.audioContext || this.audioContext.state === 'closed') {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContextClass({ sampleRate: this.sampleRate });
    }

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
  }

  /**
   * Queue and schedule an Int16 PCM chunk for playback.
   * @param {ArrayBuffer} pcmBuffer 16-bit Mono PCM
   */
  playChunk(pcmBuffer) {
    if (!this.audioContext || this.audioContext.state === 'closed') return;

    const int16Array = new Int16Array(pcmBuffer);
    const float32Array = new Float32Array(int16Array.length);

    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = this.audioContext.createBuffer(
      1,
      float32Array.length,
      this.sampleRate
    );
    audioBuffer.getChannelData(0).set(float32Array);

    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);

    const currentTime = this.audioContext.currentTime;
    // Schedule immediately or seamlessly after the previous chunk
    const startTime = Math.max(currentTime, this.nextStartTime);
    source.start(startTime);
    this.nextStartTime = startTime + audioBuffer.duration;

    this.activeSources.add(source);
    this.isPlaying = true;

    source.onended = () => {
      this.activeSources.delete(source);
      if (this.activeSources.size === 0) {
        this.isPlaying = false;
      }
    };
  }

  /**
   * Immediate cancellation of all queued and currently playing audio.
   * Essential for barge-in / interruption.
   */
  flush() {
    for (const source of this.activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch (e) {
        // Source may have already ended
      }
    }
    this.activeSources.clear();
    if (this.audioContext) {
      this.nextStartTime = this.audioContext.currentTime;
    }
    this.isPlaying = false;
  }

  close() {
    this.flush();
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
    }
    this.audioContext = null;
  }
}
