require('dotenv').config();
const chalk = require('chalk');

// Importamos las librerías necesarias de infraestructura (el mundo exterior)
const express = require('express');
const http = require('http');
const cors = require('cors');
const { Server } = require('socket.io');

// 👉 1. Importamos a nuestro "Portero". Aquí es donde conectamos 
// nuestra arquitectura limpia con el servidor físico.
const setupConnectionManager = require('../infrastructure/socket-server/connection-manager');

// 👉 Inicializamos Express (servidor web) y HTTP
const app = express();
const server = http.createServer(app);

// 👉 2. Configuramos las variables de entorno (dónde escuchamos y a quién permitimos entrar)
const CLIENT_URL = process.env.CLIENT_URL || "http://localhost:5173";
const PORT = process.env.PORT || 3000;

const corsOrigin = process.env.NODE_ENV === 'production'
  ? CLIENT_URL
  : (origin, callback) => callback(null, true); // allow all origins in dev (LAN mobile access)

// 👉 3. Inicializamos Socket.io aplicando reglas de CORS
// (Seguridad: solo dejamos que nuestra app de React/Vue se conecte)
const io = new Server(server, {
  cors: {
    origin: corsOrigin,
    methods: ["GET", "POST"]
  }
});

app.use(cors());

// 👉 4. ¡EL ENLACE MÁGICO! Le pasamos el control de la red a nuestra capa de infraestructura
setupConnectionManager(io);

// 👉 5. Encendemos el servidor y pintamos el banner de bienvenida
server.listen(PORT, () => {
  console.log(chalk.yellow.bold(`\n========================================`));
  console.log(chalk.green.bold(`🚀 ASL System Online `) + chalk.white(`| Port: ${PORT}`));
  console.log(chalk.blue(`📡 Listening to Frontend at: `) + chalk.underline(CLIENT_URL));
  console.log(chalk.yellow.bold(`========================================\n`));
});
