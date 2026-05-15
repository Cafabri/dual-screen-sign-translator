const chalk = require('chalk');
const { processSignData } = require('../../asl-core/translator');
const { enrichGlossToNaturalEnglish } = require('../../infrastructure/nlp/GroqNlpService');
// ElevenLabsTtsService kept for future paid-tier integration
// const { synthesizeSpeech } = require('../../infrastructure/tts/ElevenLabsTtsService');

const executeTranslateSign = async (rawData) => {
  console.log(chalk.magenta(`[UseCase] ⚙️ Orchestrating translation...`));

  const coreResult = processSignData(rawData);
  if (coreResult.status === 'error') {
    console.log(chalk.magenta.dim(`[UseCase] ⚠️ Aborted due to core validation error.`));
    return coreResult;
  }

  const enrichedText = await enrichGlossToNaturalEnglish(coreResult.rawGloss);

  return {
    status: 'success',
    text: enrichedText,
    timestamp: new Date().toISOString(),
  };
};

module.exports = { executeTranslateSign };
