const { io } = require("socket.io-client");

// Nos conectamos al puerto de nuestro servidor backend
const socket = io("http://localhost:3000");

console.log("⏳ Iniciando test de arquitectura...");

socket.on("connect", () => {
  console.log("✅ [Test] Conectado al servidor con ID:", socket.id);

  // 1. Simulamos que el usuario envía unas coordenadas de sus manos
  const simulacionManos = { 
    hand: "right", 
    coordinates: { x: 120, y: 45, z: 12 } 
  };

  console.log("📤 [Test] Enviando evento 'sign-data'...");
  socket.emit("sign-data", simulacionManos);

  // 2. Le damos 1 segundo al servidor para procesarlo antes de desconectarnos
  setTimeout(() => {
    console.log("👋 [Test] Desconectando...");
    socket.disconnect();
    process.exit(0);
  }, 1000);
});

// Por si el servidor está apagado
socket.on("connect_error", (error) => {
  console.error("❌ [Test] Error de conexión. ¿Está el servidor encendido?", error.message);
  process.exit(1);
});