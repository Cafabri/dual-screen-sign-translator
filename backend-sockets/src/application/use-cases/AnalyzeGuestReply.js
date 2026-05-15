const chalk = require('chalk');
const { analyzeSentiment } = require('../../infrastructure/nlp/SentimentService');

const executeAnalyzeGuestReply = async (rawData) => {
  console.log(chalk.magenta(`[UseCase] ⚙️ Orchestrating guest reply analysis...`));

  const text = rawData?.text?.trim();
  if (!text) {
    console.log(chalk.magenta.dim(`[UseCase] ⚠️ Aborted: empty guest reply.`));
    return { status: 'error', message: 'Guest reply text is required.' };
  }

  const sentiment = await analyzeSentiment(text);

  return {
    status: 'success',
    text,
    sentiment,
    timestamp: new Date().toISOString(),
  };
};

module.exports = { executeAnalyzeGuestReply };
