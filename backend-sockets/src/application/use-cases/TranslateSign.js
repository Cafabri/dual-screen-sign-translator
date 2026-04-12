const chalk = require('chalk');
// 👉 Importamos la lógica pura (El Cerebro)
const { processSignData } = require('../../asl-core/translator');

const executeTranslateSign = (rawData) => {
  console.log(chalk.magenta(`[UseCase] ⚙️ Orquestando traducción...`));
  
  // 👉 1. Le pedimos al Core que haga el cálculo matemático/IA pesado
  const translationResult = processSignData(rawData);

  // 👉 2. Si el Core detecta que los datos son basura, abortamos
  if (translationResult.status === "error") {
    console.log(chalk.magenta.dim(`[UseCase] ⚠️ Proceso abortado por error en el Core.`));
    return translationResult;
  }

  // 👉 3. Responsabilidad de Aplicación: Generamos la hora exacta del servidor
  const generatedTimestamp = new Date().toISOString();
  console.log(chalk.magenta(`[UseCase] ✅ Añadiendo timestamp: `) + chalk.white(generatedTimestamp));
  
  // 👉 4. Empaquetamos la respuesta del Core JUNTO con nuestro nuevo timestamp
  return {
    ...translationResult, // Esparce los datos que devolvió el Core (status y text)
    timestamp: generatedTimestamp // Añade nuestra variable de tiempo
  };
};

module.exports = { executeTranslateSign };