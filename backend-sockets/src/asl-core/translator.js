const chalk = require('chalk');

const processSignData = (rawData) => {
  console.log(chalk.green(`[Core] 🧠 Validating incoming sign data...`));

  if (!rawData?.phrase || !Array.isArray(rawData.phrase) || rawData.phrase.length === 0) {
    console.log(chalk.red(`[Core] 🚨 Invalid payload: 'phrase' must be a non-empty array.`));
    return { status: 'error', message: 'Invalid sign data: phrase array is required.' };
  }

  const rawGloss = rawData.phrase.join(' ');
  console.log(chalk.green.bold(`[Core] ✨ Raw gloss: `) + chalk.white(`"${rawGloss}"`));

  return { status: 'success', rawGloss };
};

module.exports = { processSignData };
