import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface WebSocketContextType {
  socket: WebSocket | null;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  activeDownloads: number;
  queueStatus: any;
}

const WebSocketContext = createContext<WebSocketContextType>({
  socket: null,
  connectionStatus: 'disconnected',
  activeDownloads: 0,
  queueStatus: null,
});

export const useWebSocket = () => useContext(WebSocketContext);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [activeDownloads, setActiveDownloads] = useState(0);
  const [queueStatus, setQueueStatus] = useState(null);

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;
    
    const connect = () => {
      setConnectionStatus('connecting');
      
      // Create WebSocket connection
      const wsUrl = 'ws://localhost:8000/ws';
      const newSocket = new WebSocket(wsUrl);

    newSocket.onopen = () => {
      setConnectionStatus('connected');
      console.log('WebSocket connected');
    };

      newSocket.onclose = () => {
        setConnectionStatus('disconnected');
        console.log('WebSocket disconnected');
        // Attempt reconnection after 3 seconds
        reconnectTimer = setTimeout(connect, 3000);
      };

    newSocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
    };

    newSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        switch (data.type) {
          case 'progress_update':
            // Handle download progress updates
            break;
          case 'download_completed':
            // Handle download completion
            break;
          case 'download_failed':
            // Handle download failure
            break;
          case 'initial_state':
            setActiveDownloads(data.active_downloads || 0);
            break;
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

      setSocket(newSocket);
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  const value = {
    socket,
    connectionStatus,
    activeDownloads,
    queueStatus,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};
