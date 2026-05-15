const chalk = require('chalk');
const { executeTranslateSign } = require('../../../application/use-cases/TranslateSign');

const handleSignData = (socket) => {
  return async (data) => {
    console.log(chalk.cyan(`[Controller] 📥 sign-data received from ${socket.id}:`), data);

    const roomId = socket.data?.roomId;
    if (!roomId) {
      socket.emit('translation-error', { status: 'error', message: 'Not in a room.' });
      return;
    }

    let result;
    try {
      result = await executeTranslateSign(data);
    } catch (err) {
      console.log(chalk.red.bold(`[Controller] ❌ Unexpected error:`), err.message);
      socket.emit('translation-error', { status: 'error', message: err.message });
      return;
    }

    if (result.status === 'error') {
      console.log(chalk.red.bold(`[Controller] ❌ Validation error:`), result);
      socket.emit('translation-error', result);
      return;
    }

    console.log(chalk.cyan(`[Controller] 📤 Emitting to room ${roomId}:`), result);
    socket.to(roomId).emit('translation-update', result);
  };
};

module.exports = { handleSignData };
