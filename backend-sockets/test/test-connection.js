const { io } = require("socket.io-client");

const SERVER_URL = "http://localhost:3000";
const socket = io(SERVER_URL, {
  reconnectionAttempts: 3,
  timeout: 5000
});

console.log(`🔍 Testing connection to: ${SERVER_URL}...`);

socket.on("connect", () => {
  console.log("-----------------------------------------");
  console.log("✅ TEST PASSED: Connection established!");
  console.log(`🆔 Assigned Client ID: ${socket.id}`);
  console.log("-----------------------------------------");
  
  setTimeout(() => {
    socket.disconnect();
    process.exit(0);
  }, 1000);
});

socket.on("connect_error", (error) => {
  console.log("-----------------------------------------");
  console.log("❌ TEST FAILED: Connection refused.");
  console.log(`⚠️ Reason: ${error.message}`);
  console.log("-----------------------------------------");
  
  process.exit(1);
});