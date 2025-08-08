import { useEffect, useCallback } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

export interface WebSocketMessage {
  type: 'account_update' | 'system_status' | 'container_status' | 'error';
  data: any;
  timestamp: string;
}

export interface WebSocketProviderProps {
  onMessage?: (message: WebSocketMessage) => void;
  onConnectionStateChange?: (state: ReadyState) => void;
}

export const useWebSocketProvider = ({
  onMessage,
  onConnectionStateChange
}: WebSocketProviderProps = {}) => {
  const socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/dashboard/stream`;
  
  const {
    sendMessage,
    lastMessage,
    readyState,
    getWebSocket
  } = useWebSocket(
    socketUrl,
    {
      onOpen: () => {
        console.log('WebSocket connection opened');
        onConnectionStateChange?.(ReadyState.OPEN);
      },
      onClose: () => {
        console.log('WebSocket connection closed');
        onConnectionStateChange?.(ReadyState.CLOSED);
      },
      onError: (event) => {
        console.error('WebSocket error:', event);
      },
      shouldReconnect: (closeEvent) => {
        // Reconnect unless it was a manual close
        return closeEvent.code !== 1000;
      },
      reconnectAttempts: 10,
      reconnectInterval: 3000,
    }
  );

  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('WebSocket message received:', message);
    onMessage?.(message);
  }, [onMessage]);

  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const message: WebSocketMessage = JSON.parse(lastMessage.data);
        handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    }
  }, [lastMessage, handleMessage]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  return {
    sendMessage,
    readyState,
    connectionStatus,
    isConnected: readyState === ReadyState.OPEN,
    getWebSocket
  };
};

// Hook for subscribing to specific data updates
export const useRealTimeData = (
  dataType: 'accounts' | 'containers' | 'system',
  onUpdate?: (data: any) => void
) => {
  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (dataType) {
      case 'accounts':
        if (message.type === 'account_update') {
          onUpdate?.(message.data);
        }
        break;
      case 'containers':
        if (message.type === 'container_status') {
          onUpdate?.(message.data);
        }
        break;
      case 'system':
        if (message.type === 'system_status') {
          onUpdate?.(message.data);
        }
        break;
    }
  }, [dataType, onUpdate]);

  return useWebSocketProvider({ onMessage: handleMessage });
};

export default useWebSocketProvider;