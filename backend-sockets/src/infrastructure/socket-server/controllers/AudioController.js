const chalk = require('chalk');
const { transcribeAudio }       = require('../../../application/use-cases/TranscribeAudio');
const { executeAnalyzeGuestReply } = require('../../../application/use-cases/AnalyzeGuestReply');

const handleGuestAudio = (socket) => {
  return async (audioBuffer, mimeType) => {
    console.log(chalk.cyan(`[Controller] 🎙️ guest-audio from ${socket.id} (${mimeType})`));

    const roomId = socket.data?.roomId;
    if (!roomId) {
      socket.emit('guest-audio-error', { message: 'Not in a room.' });
      return;
    }

    const transcribeResult = await transcribeAudio(audioBuffer, mimeType);
    if (transcribeResult.status === 'error') {
      socket.emit('guest-audio-error', { message: transcribeResult.message });
      return;
    }

    const { text } = transcribeResult;
    socket.emit('guest-transcript', { text });

    const replyResult = await executeAnalyzeGuestReply({ text });
    if (replyResult.status === 'error') {
      socket.emit('guest-audio-error', { message: replyResult.message });
      return;
    }

    console.log(chalk.cyan(`[Controller] 📤 guest-reply-update → room ${roomId}`));
    socket.to(roomId).emit('guest-reply-update', replyResult);
  };
};

module.exports = { handleGuestAudio };
