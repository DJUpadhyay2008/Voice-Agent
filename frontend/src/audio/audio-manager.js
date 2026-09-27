import { AudioPlayer } from './audio-player.js';

/**
 * Manages browser microphone capture and audio pipeline lifecycle.
 */
export class AudioManager {
  constructor({ sampleRate = 16000, chunkSize = 512, onAudioChunk, onRmsUpdate } = {}) {
    this.targetSampleRate = sampleRate; // 16000 Hz
    this.chunkSize = chunkSize;         // 512 samples = 32ms
    this.onAudioChunk = onAudioChunk;
    this.onRmsUpdate = onRmsUpdate;

    this.audioContext = null;
    this.mediaStream = null;
    this.sourceNode = null;
    this.workletNode = null;
    this.player = new AudioPlayer(sampleRate);
    this.isRecording = false;
  }

  async start() {
    if (this.isRecording) return;

    // 1. Request microphone access with echo cancellation and noise suppression
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    // 2. Initialize AudioContext at native hardware sample rate (e.g. 48000Hz or 44100Hz)
    // Avoid forcing 16000Hz on Linux PipeWire/ALSA to prevent zero-filled resampler buffers!
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this.audioContext = new AudioContextClass();

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    // Initialize playback player (runs at 16kHz for TTS/loopback)
    await this.player.init(this.audioContext);

    // 3. Load AudioWorklet module
    await this.audioContext.audioWorklet.addModule('/audio-processor.js');

    // 4. Create source and worklet nodes
    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-capture-processor', {
      processorOptions: {
        targetSampleRate: this.targetSampleRate,
        chunkSize: this.chunkSize,
      },
    });

    // 5. Handle audio chunks and RMS values from AudioWorklet
    this.workletNode.port.onmessage = (event) => {
      const { type, pcm, rms } = event.data;
      if (type === 'audio_chunk') {
        if (this.onAudioChunk && pcm) {
          this.onAudioChunk(pcm);
        }
        if (this.onRmsUpdate && typeof rms === 'number') {
          this.onRmsUpdate(rms);
        }
      }
    };

    // Connect nodes: Mic -> WorkletNode -> Silent Gain -> Destination
    // Silent Gain (0 volume) keeps Web Audio engine active without mic feedback into speakers!
    const silentGain = this.audioContext.createGain();
    silentGain.gain.value = 0;

    this.sourceNode.connect(this.workletNode);
    this.workletNode.connect(silentGain);
    silentGain.connect(this.audioContext.destination);

    this.isRecording = true;
  }

  playIncomingChunk(pcmBuffer) {
    if (this.player) {
      this.player.playChunk(pcmBuffer);
    }
  }

  flushPlayback() {
    if (this.player) {
      this.player.flush();
    }
  }

  stop() {
    this.isRecording = false;

    if (this.workletNode) {
      this.workletNode.port.postMessage({ type: 'set_recording', isRecording: false });
      this.workletNode.disconnect();
      this.workletNode = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.player) {
      this.player.flush();
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}
