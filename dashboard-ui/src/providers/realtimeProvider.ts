import { useEffect, useRef } from 'react';
import { useRefresh, useNotify } from 'react-admin';

interface WebSocketMessage {
  type: 'account_update' | 'system_status' | 'container_status' | 'error';
  data: any;
  timestamp: string;
}

class RealtimeSubscriptionManager {
  private ws: WebSocket | null = null;
  private subscriptions: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 3000;

  constructor() {
    this.connect();
  }

  private connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/api/dashboard/stream`;
    
    try {
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed', event);
        if (event.code !== 1000) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      this.connect();
    }, this.reconnectDelay);
  }

  private handleMessage(message: WebSocketMessage) {
    // Map message types to resource subscriptions
    const resourceMap: Record<string, string> = {
      'account_update': 'accounts',
      'container_status': 'containers',
      'system_status': 'dashboard',
    };

    const resource = resourceMap[message.type];
    if (resource) {
      const callbacks = this.subscriptions.get(resource);
      if (callbacks) {
        callbacks.forEach(callback => callback(message.data));
      }
    }
  }

  subscribe(resource: string, callback: (data: any) => void) {
    if (!this.subscriptions.has(resource)) {
      this.subscriptions.set(resource, new Set());
    }
    this.subscriptions.get(resource)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscriptions.get(resource);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscriptions.delete(resource);
        }
      }
    };
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    if (this.ws) {
      this.ws.close(1000);
      this.ws = null;
    }
  }
}

// Singleton instance
let subscriptionManager: RealtimeSubscriptionManager | null = null;

export const getSubscriptionManager = () => {
  if (!subscriptionManager) {
    subscriptionManager = new RealtimeSubscriptionManager();
  }
  return subscriptionManager;
};

// React hook for subscribing to real-time updates
export const useRealtimeResource = (resource: string) => {
  const refresh = useRefresh();
  const notify = useNotify();
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const manager = getSubscriptionManager();
    
    const handleUpdate = (data: any) => {
      console.log(`Real-time update for ${resource}:`, data);
      
      // Refresh the resource data
      refresh();
      
      // Optional: Show notification for important updates
      if (resource === 'accounts' && data.alert) {
        notify(`Account ${data.account_id} updated`, { type: 'info' });
      }
    };

    unsubscribeRef.current = manager.subscribe(resource, handleUpdate);

    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, [resource, refresh, notify]);
};

// Hook for global real-time connection status
export const useRealtimeStatus = () => {
  // This could be enhanced to track connection state
  return {
    isConnected: true, // Simplified for now
  };
};

export default {
  useRealtimeResource,
  useRealtimeStatus,
  getSubscriptionManager,
};