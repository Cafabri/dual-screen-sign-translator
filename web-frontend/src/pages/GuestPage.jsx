import { useEffect, useState } from 'react';
import useSocket from '../hooks/useSocket';

function GuestPage() {
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

  const sendResponseToHost = () => {
    socket.emit('test-message', '¡Respuesta desde el Guest!');
  };

  return (
    <div>
      <h1>Guest Page — Receptor de la traducción</h1>
      <button onClick={sendResponseToHost}>Responder al Host</button>
      <ul>
        {receivedMessages.map((message, index) => (
          <li key={index}>{message}</li>
        ))}
      </ul>
    </div>
  );
}

export default GuestPage;
