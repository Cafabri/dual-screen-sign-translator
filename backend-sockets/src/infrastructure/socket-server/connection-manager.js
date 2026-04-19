const chalk = require('chalk');
const { handleSignData } = require('./controllers/SignController');
const { handleTestMessage } = require('./controllers/TestMessageController');

const setupConnectionManager = (io) => {
  // 👉 Escuchamos cada vez que un usuario nuevo abre la app
  io.on('connection', (socket) => {
    console.log(chalk.blue.bold(`[Red] 🌐 Nueva conexión: `) + chalk.gray(socket.id));

    // 👉 ENRUTAMIENTO: Si el usuario envía el evento 'sign-data',
    // se lo pasamos directamente a nuestro Controlador (El Camarero)
    socket.on('sign-data', handleSignData(socket));

    socket.on('test-message', handleTestMessage(socket));

    // 👉 Limpieza: Cuando el usuario cierra la pestaña o pierde el WiFi
    socket.on('disconnect', () => {
      console.log(chalk.blue.dim(`[Red] 🔌 Desconexión: `) + chalk.gray(socket.id));
    });
  });
};

module.exports = setupConnectionManager;
