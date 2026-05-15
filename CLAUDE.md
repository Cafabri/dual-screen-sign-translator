# DualSign (Traductor Web ASL)

Este archivo proporciona la guía técnica y estratégica para Claude Code (claude.ai/code) al trabajar en este repositorio.

## 🎯 Visión Global y Estrategia de Producto (El "Por qué")

Estamos construyendo **DualSign**, un Traductor Bidireccional en Tiempo Real de Lenguaje de Señas Americano (ASL) a Inglés Hablado/Escrito (Zero-Touch). 
El objetivo es eliminar la fricción de comunicación entre personas sordas y oyentes al quitar la necesidad de descargar aplicaciones o pasarse un teléfono de mano en mano.

**La Arquitectura "Doble Pantalla" 100% Web:**
Este es un sistema híbrido Edge + Cloud (Borde y Nube).
1. **El Host (Usuario Sordo):** Abre `/host` en su dispositivo. El navegador usa la cámara web local, MediaPipe JS y TensorFlow.js (Edge) para extraer glosas de ASL localmente (ahorrando costos de servidor). Se genera un código QR.
2. **El Guest (Usuario Oyente):** Escanea el código QR para abrir `/guest` en su propio teléfono. Lee los subtítulos enriquecidos y responde usando la Web Speech API nativa (voz a texto).
3. **El Puente Cloud:** Un servidor ligero en Node.js + Socket.io enruta mensajes de texto de baja latencia entre los dos navegadores.

**Requisitos Críticos de IA y UX (Fases Futuras):**
- **Ecosistema 100% en Inglés:** Las glosas de ASL, el enriquecimiento de NLP y las respuestas habladas operarán estrictamente en inglés para minimizar la latencia. Las glosas crudas (ej. `["I", "WANT", "WATER"]`) se reescriben en inglés conversacional natural (ej. `"I'd like some water, please"`), no se traducen al español.
- **El Gatillo de "Fin de Frase":** La IA local dependerá de un gesto físico específico (ej. bajar las manos) para saber cuándo el usuario ha terminado de signar antes de enviar el paquete de datos.
- **Enriquecimiento con NLP:** Las glosas crudas de ASL (ej. "I WANT APPLE") se enviarán a una API de NLP (como OpenAI) para reescribirse en inglés conversacional natural antes de mostrarse al Guest.
- **TTS Emocional:** El texto enriquecido se leerá en voz alta para el Guest usando una API avanzada de Texto-a-Voz (como ElevenLabs) que refleje la emoción humana de los signos originales.

---

## 📁 Estructura del Monorepo

```
asl-translator-monorepo/
├── docs/                  # Todos los reportes del proyecto (prefijo ml_ o backend_)
│   └── training_logs/     # Logs de ejecución auto-generados por ml/reporter/generator.py
├── backend-sockets/       # Servidor Node.js + Socket.io (Clean Architecture)
├── ml/                    # Pipeline de entrenamiento Python
│   ├── data/              # Datos reales: source/ (WLASL raw), filtered/ (videos por clase), features/ (.npy)
│   ├── pipeline/          # Módulos Python: carga y preprocesado de datos
│   ├── augmentation/      # Lógica de data augmentation
│   ├── model/             # Arquitectura, entrenamiento y evaluación del modelo
│   ├── reporter/          # Generación de logs de entrenamiento
│   ├── dashboard/         # Visualización Streamlit
│   ├── scripts/           # Scripts ejecutables (train_model.py, export_tfjs.py, etc.)
│   └── artifacts/         # Outputs generados: modelo_dualsign.keras, tfjs_export/, dashboard_data/
└── web-frontend/          # App React/Vite
    └── public/models/     # Modelo TF.js que consume el navegador (model.json + *.bin)
```

`backend-sockets` está completamente activo. `web-frontend` (React/Vite) en Fase 5. `ml/` contiene el pipeline completo de entrenamiento ASL con LSTM (82.32% accuracy sobre 10 clases).

## 💻 Comandos

Todos los comandos del backend se ejecutan desde la carpeta `backend-sockets/`:

```bash
npm install          # Instalar dependencias
npm run dev          # Iniciar servidor con nodemon (puerto 3000, recarga en vivo)
npm start            # Iniciar en producción vía node server.js
npm test             # Ejecutar test de integración (requiere que el servidor ya esté corriendo en otra terminal)
```

No hay un linter configurado. No hay framework de pruebas unitarias — solo la prueba de integración manual en `test/test-connection.js`.

## 🌍 Variables de Entorno

| Variable     | Por defecto               | Propósito                    |
|--------------|---------------------------|------------------------------|
| `PORT`       | `3000`                    | Puerto del servidor          |
| `CLIENT_URL` | `http://localhost:5173`   | Origen CORS permitido (Vite) |

## 🏗️ Arquitectura (Backend)

El backend sigue la **Clean Architecture** (Arquitectura Limpia). Las dependencias siempre deben apuntar hacia **adentro** — infraestructura → aplicación → dominio. La capa de dominio (`asl-core`) nunca debe importar elementos de la aplicación o de la infraestructura.

```text
entry-points/main.js            # Configuración de Express + Socket.io, CORS, inicio del servidor
infrastructure/socket-server/
  connection-manager.js         # Ciclo de vida del Socket (conectar/desconectar), enrutamiento de eventos
  controllers/SignController.js # Maneja eventos 'sign-data'; usa currying con la instancia del socket
application/use-cases/
  TranslateSign.js              # Orquesta la lógica central, añade timestamp ISO
asl-core/
  translator.js                 # Lógica pura de traducción, validación de entrada (sin dependencias de frameworks)
```

### Flujo de Eventos en Tiempo Real

```text
El Cliente emite 'sign-data' { phrase: ["APPLE", "PLEASE"] }
  → SignController.handleSignData(socket)
    → TranslateSign (añade timestamp)
      → translator.processSignData() (valida + traduce)
    → en error:   socket.emit('translation-error')             [solo al emisor]
    → en éxito: socket.to(roomId).emit('translation-update')  [solo a la sala]
```

### Patrones Clave y Reglas de Clean Code

- **Convenciones de Nombres:** Usar nombres de variables y funciones altamente descriptivos que revelen su intención.
- **Currying para Inyección de Dependencias:** `SignController` exporta `handleSignData(socket)` retornando el manejador real, permitiendo la vinculación a Socket.io mientras mantiene el socket aislado como dependencia.
- **Respuesta Estandarizada del Core:** `{ status: "success"|"error", text?, message? }` — las capas superiores dependen de esta estructura exacta.
- **Logs por Capas:** Prefijos coloreados con `chalk` por capa (`[Core]` verde, `[UseCase]` magenta, `[Controller]` cian) — sigue estas convenciones al añadir logs.

### Estado Actual (Fase 5 — en progreso)

Hitos 1–6 del frontend completos. El flujo de signing → chips → envío funciona end-to-end.
GuestPage es un esqueleto que solo hace `join-room`. Pendiente: subtítulos, NLP (OpenAI), TTS, sentiment analysis.
`asl-core/translator.js` sigue siendo placeholder — la integración real de OpenAI va en un nuevo use-case.