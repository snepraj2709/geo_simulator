import { PipelineMessage, PipelineState } from '@/types/pipeline';

type PipelineUpdateCallback = (state: PipelineState) => void;
type ErrorCallback = (error: string) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private subscribers: Map<string, Set<PipelineUpdateCallback>> = new Map();
  private errorSubscribers: Set<ErrorCallback> = new Set();
  private isConnecting = false;
  private shouldReconnect = true;

  constructor(private baseUrl: string) {}

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    const wsUrl = this.baseUrl.replace(/^http/, 'ws');

    try {
      this.ws = new WebSocket(`${wsUrl}/ws/pipeline`);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to pipeline updates');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: PipelineMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        this.isConnecting = false;
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Connection closed');
        this.isConnecting = false;
        this.ws = null;

        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  private handleMessage(message: PipelineMessage): void {
    switch (message.type) {
      case 'pipeline_update':
        const callbacks = this.subscribers.get(message.data.id);
        if (callbacks) {
          callbacks.forEach((callback) => callback(message.data));
        }
        break;

      case 'pipeline_error':
        this.errorSubscribers.forEach((callback) => callback(message.error));
        break;

      default:
        console.warn('[WebSocket] Unknown message type:', message);
    }
  }

  subscribe(pipelineId: string, callback: PipelineUpdateCallback): () => void {
    if (!this.subscribers.has(pipelineId)) {
      this.subscribers.set(pipelineId, new Set());
    }

    this.subscribers.get(pipelineId)!.add(callback);

    // Send subscription message to backend
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        pipelineId,
      }));
    }

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscribers.get(pipelineId);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscribers.delete(pipelineId);

          // Send unsubscribe message to backend
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
              type: 'unsubscribe',
              pipelineId,
            }));
          }
        }
      }
    };
  }

  onError(callback: ErrorCallback): () => void {
    this.errorSubscribers.add(callback);

    return () => {
      this.errorSubscribers.delete(callback);
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscribers.clear();
    this.errorSubscribers.clear();
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const websocketService = new WebSocketService(API_BASE_URL);

// Auto-connect on module load
websocketService.connect();
