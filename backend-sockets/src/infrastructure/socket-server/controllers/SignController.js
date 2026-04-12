const chalk = require('chalk');
// 👉 Importamos la capa de Aplicación (nunca la de Dominio directamente)
const { executeTranslateSign } = require('../../../application/use-cases/TranslateSign');

const handleSignData = (socket) => {
  // 👉 Devolvemos una función para que Socket.io la ejecute cuando llegue el dato
  return (data) => {
    console.log(chalk.cyan(`[Controller] 📥 Dato recibido de ${socket.id}:`), data);
    
    // 👉 1. Entregamos el paquete de datos al Caso de Uso (Jefe de Cocina)
    const result = executeTranslateSign(data);
    
    // 👉 2. Manejo de Errores: Si hubo fallo, avisamos ÚNICAMENTE al usuario que envió el dato
    if (result.status === "error") {
      console.log(chalk.red.bold(`[Controller] ❌ Error de validación:`), result);
      socket.emit('translation-error', result); // 'emit' solo responde a ese socket
      return; // Cortamos la ejecución aquí
    }

    // 👉 3. Éxito: Si todo fue bien, enviamos la traducción al RESTO de usuarios en la sala
    console.log(chalk.cyan(`[Controller] 📤 Emitiendo broadcast a la sala con payload:`), result);
    socket.broadcast.emit('translation-update', result); // 'broadcast' ignora al emisor original
  };
};

module.exports = { handleSignData };