/**
 * WebSocket client for bidirectional voice streaming.
 */
export class VoiceWebSocketClient {
  constructor({
    url,
    onOpen,
    onClose,
    onError,
    onJsonMessage,
    onBinaryMessage,
  } = {}) {
    this.url = url;
    this.onOpen = onOpen;
    this.onClose = onClose;
    this.onError = onError;
    this.onJsonMessage = onJsonMessage;
    this.onBinaryMessage = onBinaryMessage;

    this.ws = null;
    this.isConnected = false;
  }

  connect() {
    if (this.ws) {
      this.disconnect();
    }

    this.ws = new WebSocket(this.url);
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = (event) => {
      this.isConnected = true;
      if (this.onOpen) this.onOpen(event);
    };

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        if (this.onBinaryMessage) {
          this.onBinaryMessage(event.data);
        }
      } else if (typeof event.data === 'string') {
        try {
          const json = JSON.parse(event.data);
          if (this.onJsonMessage) {
            this.onJsonMessage(json);
          }
        } catch (e) {
          console.warn('Failed to parse incoming WebSocket JSON:', event.data);
        }
      }
    };

    this.ws.onerror = (error) => {
      if (this.onError) this.onError(error);
    };

    this.ws.onclose = (event) => {
      this.isConnected = false;
      if (this.onClose) this.onClose(event);
    };
  }

  sendAudio(arrayBuffer) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(arrayBuffer);
    }
  }

  sendJson(payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }
}
