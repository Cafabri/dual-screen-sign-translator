import { useEffect, useRef } from 'react';
import { io } from 'socket.io-client';

// Socket proxied through Vite (/socket.io → localhost:3000), so same origin works
// for both local dev and Cloudflare tunnel without any extra config.
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || window.location.origin;

function useSocket() {
  const socketRef = useRef(null);

  if (!socketRef.current) {
    socketRef.current = io(BACKEND_URL);
  }

  useEffect(() => {
    const socket = socketRef.current;

    if (!socket.connected) {
      socket.connect();
    }

    return () => {
      socket.disconnect();
    };
  }, []);

  return socketRef.current;
}

export default useSocket;
