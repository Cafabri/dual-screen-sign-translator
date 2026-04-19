const chalk = require('chalk');

const handleTestMessage = (socket) => (messageText) => {
  console.log(chalk.cyan('[Controller]'), `test-message recibido: "${messageText}"`);
  socket.broadcast.emit('test-message', messageText);
};

module.exports = { handleTestMessage };
