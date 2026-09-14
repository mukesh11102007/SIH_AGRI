/**
 * WebSocket hook — connects to the backend real-time update stream.
 * Reconnects automatically on disconnect.
 */
import { useEffect, useRef, useCallback } from 'react';
import type { WebSocketMessage } from '../types';

interface UseRealtimeOptions {
  farmId: string;
  onMessage: (msg: WebSocketMessage) => void;
  enabled?: boolean;
}

export function useRealtimeUpdates({ farmId, onMessage, enabled = true }: UseRealtimeOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!enabled || !farmId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = (import.meta.env['VITE_WS_HOST'] as string) ?? window.location.host;
    const url = `${protocol}://${host}/ws/farm/${farmId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.debug('[WS] Connected to farm', farmId);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WebSocketMessage;
        if (msg.event !== 'connected') {
          onMessageRef.current(msg);
        }
      } catch {
        // Non-JSON messages (e.g. pong) — ignore
      }
    };

    ws.onclose = () => {
      console.debug('[WS] Disconnected — reconnecting in 3s');
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    // Keepalive ping every 30s
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    ws.addEventListener('close', () => clearInterval(pingInterval));
  }, [farmId, enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
