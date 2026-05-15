const chalk = require('chalk');
const { executeAnalyzeGuestReply } = require('../../../application/use-cases/AnalyzeGuestReply');

const handleGuestReply = (socket) => {
  return async (data) => {
    console.log(chalk.cyan(`[Controller] 📥 guest-reply received from ${socket.id}:`), data);

    const roomId = socket.data?.roomId;
    if (!roomId) {
      socket.emit('guest-reply-error', { status: 'error', message: 'Not in a room.' });
      return;
    }

    let result;
    try {
      result = await executeAnalyzeGuestReply(data);
    } catch (err) {
      console.log(chalk.red.bold(`[Controller] ❌ Unexpected error:`), err.message);
      socket.emit('guest-reply-error', { status: 'error', message: err.message });
      return;
    }

    if (result.status === 'error') {
      socket.emit('guest-reply-error', result);
      return;
    }

    console.log(chalk.cyan(`[Controller] 📤 Emitting guest-reply-update to room ${roomId}:`), result);
    socket.to(roomId).emit('guest-reply-update', result);
  };
};

module.exports = { handleGuestReply };
