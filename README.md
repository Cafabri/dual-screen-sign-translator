# 🤟 DualSign — Traductor Web Bidireccional de ASL a Inglés

> ✅ **FASE 1 COMPLETADA:** Infraestructura de red y enrutamiento visual listos. El terreno está preparado para integrar la IA.

---

## 🌍 ¿Qué es DualSign y por qué existe?

DualSign es una herramienta de comunicación en tiempo real que permite a una persona sorda "hablar" con cualquier oyente sin necesidad de instalar ninguna aplicación, sin pasarse el teléfono de mano en mano, y sin depender de un intérprete humano.

La persona sorda realiza señas frente a la cámara de su dispositivo. Esas señas se traducen a texto en inglés y ese texto aparece —al instante— en la pantalla del teléfono del oyente al otro lado de la mesa.

### 🔑 La decisión de diseño más importante: "Doble Pantalla, Zero-Touch"

La mayoría de las apps de traducción de señas tienen un problema de usabilidad crítico: obligan a los dos interlocutores a compartir un único dispositivo, pasándoselo uno al otro para cada turno. Eso rompe el flujo de la conversación y hace que la tecnología sea más un obstáculo que una solución.

DualSign resuelve esto con un modelo de **"Doble Pantalla"**:

| Rol | Dispositivo | ¿Qué hace? |
|---|---|---|
| 🧏 **Host** (usuario sordo) | Su propio teléfono/PC | Abre `/host`, activa la cámara y signa |
| 👂 **Guest** (usuario oyente) | Su propio teléfono | Escanea el código QR, lee los subtítulos y responde por voz |

El flujo de una conversación funciona así:
1. El Host abre `/host` en su navegador. La app genera un **código QR único** para esa sesión.
2. El Guest escanea el QR con su cámara. Se abre `/guest` en su propio teléfono, sin instalar nada.
3. Ambos están conectados. El Host signa, el Guest lee. El Guest habla, el Host lee. La conversación fluye.

> 💡 **¿Por qué el QR y no una app instalable?** La web es universal. No requiere pasar por App Store, no requiere cuenta, no requiere descargas. Un QR es la forma más rápida del mundo de compartir una URL.

---

## 🧠 Las Grandes Decisiones de IA y UX (Fases Futuras)

Estas decisiones ya están tomadas y guían toda la arquitectura, aunque su implementación llegará en las próximas fases.

### 1. 🇺🇸 Ecosistema 100% en Inglés
Toda la cadena de IA —reconocimiento de señas (ASL), enriquecimiento de texto y voz— opera exclusivamente en inglés. El motivo es la latencia: cada traducción intermedia (señas → español → inglés → voz) añade cientos de milisegundos de retraso que hacen la conversación incómoda. Al eliminar el paso intermedio, la respuesta es casi instantánea.

### 2. ⚡ IA en el Edge (en el navegador, no en el servidor)
El reconocimiento de señas se hará **localmente en el navegador del Host** usando librerías como MediaPipe y TensorFlow.js. Esto tiene dos ventajas enormes: primero, la privacidad (el vídeo nunca sale del dispositivo del usuario); segundo, el coste (no necesitamos servidores potentes para procesar vídeo de miles de usuarios simultáneos).

El servidor solo recibe texto, que ocupa muy poco ancho de banda.

### 3. ✍️ NLP para convertir "señas en bruto" a inglés conversacional
ASL tiene su propia gramática, muy diferente al inglés hablado. Una persona puede signar `"I WANT APPLE"` y el sistema recibiría esas glosas en ese orden. Un modelo de NLP (como la API de OpenAI) reescribirá ese mensaje a `"I'd like an apple, please"` antes de mostrárselo al Guest. El resultado es una conversación natural, no un telegrama.

### 4. 🎙️ TTS Emocional: una voz que transmite sentimientos
El texto enriquecido no solo se mostrará en pantalla, sino que se leerá en voz alta para el Guest usando una API de Texto-a-Voz avanzada (como ElevenLabs). El objetivo es que la voz generada refleje la emoción del signo original —entusiasmo, calma, urgencia— para que la conversación sea lo más humana posible.

---

## ✅ Estado Actual: Fase 1 Completada

Acabamos de terminar los **cimientos** del proyecto. Es el equivalente a construir los cimientos y la estructura de un edificio: no es lo más vistoso, pero sin ello nada de lo demás se sostiene.

**Lo que está listo:**
- ✅ Servidor WebSocket en tiempo real (Node.js + Socket.io) funcionando en el puerto 3000
- ✅ Clean Architecture implementada en el backend, lista para enchufar la IA
- ✅ Frontend React + Vite inicializado y limpio de código basura
- ✅ Sistema de rutas (`/host` y `/guest`) funcionando
- ✅ Conexión Socket.io bidireccional verificada entre Host y Guest
- ✅ Desconexión limpia de sockets al cambiar de página

**Lo que viene a continuación:**
- 🔜 Fase 2: Integración de MediaPipe en `/host` para detectar la mano en la cámara
- 🔜 Fase 3: Modelo de clasificación de señas (TensorFlow.js) y pipeline de NLP
- 🔜 Fase 4: Generación del QR, sistema de "salas" y TTS emocional

---

## 🏗️ Arquitectura del Proyecto

```
asl-translator-monorepo/
├── backend-sockets/       # El servidor: el "túnel" entre los dos dispositivos
├── web-frontend/          # La interfaz: las dos "habitaciones" (/host y /guest)
└── ia-entrenamiento/      # (Reservado) Scripts Python para entrenar modelos de señas
```

---

## 🔧 El Backend a Fondo: El "Puente" entre los dos teléfonos

El backend es el corazón del sistema de comunicación. Su única responsabilidad es recibir un mensaje de texto de un dispositivo y enviárselo al otro en tiempo real. No procesa vídeo, no guarda datos. Es un túnel muy rápido y muy eficiente.

Usa **WebSockets** (a través de Socket.io) en lugar de peticiones HTTP tradicionales porque los WebSockets mantienen una conexión permanente abierta entre el navegador y el servidor. Esto elimina la necesidad de que el navegador "pregunte" repetidamente si hay nuevos mensajes —el servidor se los envía en el momento en que llegan.

### 🧅 La Arquitectura de Cebolla (Clean Architecture)

El código del backend está organizado como una cebolla: tiene capas, y las capas externas dependen de las internas, nunca al revés. La capa del centro (el núcleo) es totalmente ignorante del mundo exterior.

Imagina un restaurante:

```
┌─────────────────────────────────────────┐
│  🌐 infrastructure (El Camarero)        │  ← Socket.io, controladores de red
│  ┌───────────────────────────────────┐  │
│  │  🧑‍💼 application (Jefe de Cocina)  │  │  ← Orquesta el flujo, añade timestamps
│  │  ┌─────────────────────────────┐  │  │
│  │  │  🧠 asl-core (El Cocinero)  │  │  │  ← Lógica pura de traducción
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

- **`asl-core` (El Cocinero):** El cerebro puro. Solo sabe transformar datos de entrada en una traducción. No sabe si los datos llegaron por WiFi, Bluetooth o por correo postal. Actualmente contiene un simulador (placeholder) que será reemplazado por el modelo de IA real en la Fase 3. **Cambiar el modelo de IA no requiere tocar ninguna otra capa.**

- **`application` (El Jefe de Cocina):** Sabe cuál es el flujo correcto. Le dice al cocinero qué preparar, recoge el resultado y le añade lo que la aplicación necesita (como un sello de tiempo). No habla directamente con los clientes.

- **`infrastructure` (El Camarero):** Es la única capa que toca la red. Gestiona las conexiones WebSocket, escucha los eventos del frontend y decide si enviar la respuesta solo al emisor (en caso de error) o a todos los demás (cuando la traducción es exitosa). Si mañana reemplazamos Socket.io por otra tecnología, solo se cambia esta capa. El cocinero y el jefe de cocina no se enteran.

```
backend-sockets/src/
├── entry-points/
│   └── main.js                     # Arranca el servidor Express + Socket.io
├── infrastructure/
│   └── socket-server/
│       ├── connection-manager.js   # Gestiona el ciclo de vida de cada conexión
│       └── controllers/
│           ├── SignController.js   # Maneja el evento 'sign-data'
│           └── TestMessageController.js  # Maneja 'test-message' (verificación bidireccional)
├── application/
│   └── use-cases/
│       └── TranslateSign.js        # Orquesta la traducción y añade metadatos
└── asl-core/
    └── translator.js               # Lógica pura de traducción (ahora: simulador)
```

### ⚙️ Variables de Entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `PORT` | `3000` | Puerto del servidor WebSocket |
| `CLIENT_URL` | `http://localhost:5173` | Origen permitido por CORS (la URL del frontend) |

---

## 🎨 El Frontend a Fondo: Las Dos Habitaciones

El frontend vive en la carpeta `web-frontend/` y está construido con **React + Vite**. Vite es la herramienta de desarrollo que hace que el servidor local arranque en menos de un segundo y que los cambios en el código se reflejen en el navegador instantáneamente.

### ¿Por qué React Router? La metáfora de las habitaciones

Técnicamente, DualSign es una sola aplicación web (un único `index.html`). Pero necesita dos experiencias de usuario completamente diferentes:

- La habitación del **Host** (`/host`): Tiene acceso a la cámara, muestra el código QR y envía señas.
- La habitación del **Guest** (`/guest`): Muestra los subtítulos y tiene acceso al micrófono.

React Router nos permite crear esas dos "habitaciones" dentro de la misma aplicación, gestionando qué componente se muestra dependiendo de la URL, sin necesidad de recargar la página. Si el usuario entra en una URL que no existe, se muestra una página 404.

```
web-frontend/src/
├── App.jsx               # El "pasillo": define las rutas /host, /guest y la 404
├── hooks/
│   └── useSocket.js      # Hook reutilizable: gestiona la conexión y desconexión limpia del socket
├── pages/
│   ├── HostPage.jsx       # Habitación del Host (cámara + emisor de señas)
│   ├── GuestPage.jsx      # Habitación del Guest (receptor de traducción + micrófono)
│   └── NotFoundPage.jsx   # Página 404
└── components/           # (Reservado) Componentes visuales reutilizables
```

> 💡 **Detalle técnico:** El hook `useSocket.js` garantiza que cada página tenga exactamente una conexión WebSocket activa. Cuando el usuario navega de `/host` a `/guest`, el socket de la página anterior se desconecta limpiamente antes de que se abra el nuevo, evitando conexiones "fantasma" en el servidor.

---

## 🚀 Cómo Ejecutar el Proyecto en Local

Necesitas dos terminales abiertas simultáneamente.

**Terminal 1 — Backend:**
```bash
cd backend-sockets
npm install
npm run dev
# El servidor arranca en http://localhost:3000
```

**Terminal 2 — Frontend:**
```bash
cd web-frontend
npm install
npm run dev
# La app arranca en http://localhost:5173
```

Abre `http://localhost:5173/host` en una pestaña y `http://localhost:5173/guest` en otra. Los mensajes enviados desde una pestaña aparecerán en la otra en tiempo real.
