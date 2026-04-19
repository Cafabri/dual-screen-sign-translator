import { useEffect, useState } from 'react';
import useSocket from '../hooks/useSocket';

function HostPage() {
  const socket = useSocket();
  const [receivedMessages, setReceivedMessages] = useState([]);

  useEffect(() => {
    const onTestMessage = (messageText) => {
      setReceivedMessages((previous) => [...previous, messageText]);
    };

    socket.on('test-message', onTestMessage);

    return () => {
      socket.off('test-message', onTestMessage);
    };
  }, [socket]);

  const sendSignalToGuest = () => {
    socket.emit('test-message', '¡Señal desde el Host!');
  };

  return (
    <div>
      <h1>Host Page — Emisor de señas</h1>
      <button onClick={sendSignalToGuest}>Enviar señal al Guest</button>
      <ul>
        {receivedMessages.map((message, index) => (
          <li key={index}>{message}</li>
        ))}
      </ul>
    </div>
  );
}

export default HostPage;
