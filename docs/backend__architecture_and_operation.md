> **Module:** [`backend-sockets/`](../backend-sockets/)
> **Phase:** Cross-cutting — architecture in use since Phase 1, expanded in Phase 5

# DualSign Backend — Architecture and Operation

**Project:** DualSign — Real-Time Bidirectional ASL Translator
**Stack:** Node.js · Express · Socket.io · Groq SDK · ElevenLabs SDK
**Port:** 3000
**Report date:** May 2026

---

## 1. Overview

The DualSign backend is a **real-time messaging server**. Its job is not to serve web pages or manage a database: it is the communication bridge between two browsers — the Host (Deaf user) and the Guest (hearing listener) — applying AI logic to the messages that pass through it.

The most important architectural characteristic is that it strictly follows **Clean Architecture**. This means code is organised into concentric layers where dependencies only point inward: infrastructure depends on application, and application depends on domain. The domain (`asl-core`) imports nothing external.

```
┌─────────────────────────────────────────────┐
│  INFRASTRUCTURE (Socket.io, Groq, ElevenLabs)│
│  ┌─────────────────────────────────────────┐ │
│  │  APPLICATION (Use Cases / Orchestration)│ │
│  │  ┌───────────────────────────────────┐  │ │
│  │  │  DOMAIN (asl-core / translator)   │  │ │
│  │  └───────────────────────────────────┘  │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 2. File Tree and Responsibilities

```
backend-sockets/
├── src/
│   ├── entry-points/
│   │   └── main.js                          # Bootstrap: Express + Socket.io + CORS
│   ├── infrastructure/
│   │   ├── socket-server/
│   │   │   ├── connection-manager.js        # Socket lifecycle and event routing
│   │   │   └── controllers/
│   │   │       ├── SignController.js        # Handles 'sign-data' (Host → Guest)
│   │   │       ├── GuestReplyController.js  # Handles 'guest-reply' (text, Guest → Host)
│   │   │       ├── AudioController.js       # Handles 'guest-audio': Whisper → sentiment → Host
│   │   │       └── TestMessageController.js # Handles 'test-message' (debug broadcast)
│   │   ├── nlp/
│   │   │   ├── GroqNlpService.js            # ASL gloss → natural English (Groq/LLaMA)
│   │   │   └── SentimentService.js          # Text → positive/neutral/negative (Groq/LLaMA)
│   │   └── tts/
│   │       └── ElevenLabsTtsService.js      # Text → base64 MP3 (ElevenLabs)
│   ├── application/
│   │   └── use-cases/
│   │       ├── TranslateSign.js             # Orchestrates: validate gloss + enrich with NLP
│   │       ├── AnalyzeGuestReply.js         # Orchestrates: validate text + analyse sentiment
│   │       └── TranscribeAudio.js           # Groq Whisper: ArrayBuffer → transcribed text
│   └── asl-core/
│       └── translator.js                    # Pure domain: validate and normalise the gloss
├── test/
│   └── test-connection.js                   # Manual integration test (requires running server)
└── .env                                     # PORT, CLIENT_URL, GROQ_API_KEY, ELEVENLABS_*
```

---

## 3. Layer by Layer

### 3.1 Entry Point — `main.js`

This is the only file that "touches the physical world": opens the port, configures CORS, and wires the pieces together. Contains no business logic.

```js
const io = new Server(server, {
  cors: { origin: CLIENT_URL, methods: ["GET", "POST"] }
});
setupConnectionManager(io);          // delegates ALL socket control
server.listen(PORT, () => { ... });  // starts listening
```

Two environment variables control behaviour:

| Variable | Default | Effect |
|---|---|---|
| `PORT` | `3000` | Listening port |
| `CLIENT_URL` | `http://localhost:5173` | Only origin allowed by CORS |

### 3.2 Connection Manager — `connection-manager.js`

The **gatekeeper and event router**. When a socket connects, it registers all the listeners that socket can emit. Contains no business logic — it delegates to controllers.

```js
io.on('connection', (socket) => {

  socket.on('join-room', ({ roomId, role }) => {
    socket.join(roomId);           // joins the socket to a Socket.io room
    socket.data.roomId = roomId;   // persists roomId on the socket for later routing
  });

  socket.on('sign-data',      handleSignData(socket));    // Host signing
  socket.on('guest-reply',    handleGuestReply(socket));  // Guest text reply
  socket.on('guest-audio',    handleGuestAudio(socket));  // Guest audio → Whisper → Host
  socket.on('guest-speaking', (data) => { ... });         // direct relay with no logic
  socket.on('test-message',   handleTestMessage(socket)); // debug broadcast
  socket.on('disconnect',     () => { ... });             // log cleanup
});
```

`guest-speaking` is the only event processed directly here without going through a controller. It is a pure relay: when the Guest starts speaking, the server forwards the event to the room so the Host sees a real-time visual indicator — there is nothing to orchestrate.

### 3.3 Controllers — `SignController`, `GuestReplyController`, `TestMessageController`

Controllers are **translators between the Socket.io protocol and use cases**. They have three fixed responsibilities:

1. Verify the socket is in a room (minimal security guard)
2. Call the corresponding use case
3. Emit the result to the correct destination (sender or room)

**Currying pattern:** all controllers use the same signature:

```js
const handleSignData = (socket) => {    // 1st call: injects the socket
  return async (data) => {              // 2nd call: Socket.io passes the payload here
    ...
  };
};
```

This lets the handler be registered as: `socket.on('sign-data', handleSignData(socket))`. The socket is captured in the closure without global variables or event-argument passing. Dependency injection without a framework.

**Emission targets:**

| Controller | On success emits to... | On error emits to... |
|---|---|---|
| `SignController` | `socket.to(roomId).emit('translation-update')` | `socket.emit('translation-error')` |
| `GuestReplyController` | `socket.to(roomId).emit('guest-reply-update')` | `socket.emit('guest-reply-error')` |
| `AudioController` | `socket.emit('guest-transcript')` + `socket.to(roomId).emit('guest-reply-update')` | `socket.emit('guest-audio-error')` |
| `TestMessageController` | `socket.broadcast.emit('test-message')` | — |

`socket.to(roomId)` sends to all room members **except the sender**. `socket.broadcast` sends to all sockets connected to the server except the sender.

### 3.4 Use Cases — `TranslateSign`, `AnalyzeGuestReply`

Use cases are the **conductors**. They know which services to call and in what order, but know nothing about Socket.io, HTTP, or how the request arrived.

**`TranslateSign`:**

```
rawData (phrase: ["MORE", "WATER"])
  │
  ├─▶ processSignData()          → validates + converts to rawGloss "MORE WATER"
  │                                  on failure → returns { status: 'error' }
  │
  ├─▶ enrichGlossToNaturalEnglish("MORE WATER")
  │                              → calls Groq LLaMA → "Could I have more water, please?"
  │
  └─▶ returns { status: 'success', text: "...", timestamp: ISO }
```

**`AnalyzeGuestReply`:**

```
rawData (text: "Yes, thank you!")
  │
  ├─▶ trim() + empty text validation
  │
  ├─▶ analyzeSentiment("Yes, thank you!")
  │                              → calls Groq LLaMA → "positive"
  │
  └─▶ returns { status: 'success', text: "...", sentiment: "positive", timestamp: ISO }
```

### 3.5 Domain — `asl-core/translator.js`

The purest module in the system. Receives the raw client payload and applies the only business rule that does not depend on any external service:

```js
const processSignData = (rawData) => {
  if (!rawData?.phrase || !Array.isArray(rawData.phrase) || rawData.phrase.length === 0) {
    return { status: 'error', message: 'Invalid sign data: phrase array is required.' };
  }
  const rawGloss = rawData.phrase.join(' ');   // ["MORE", "WATER"] → "MORE WATER"
  return { status: 'success', rawGloss };
};
```

Imports nothing from infrastructure. Can be tested in complete isolation.

### 3.6 NLP — `GroqNlpService` and `SentimentService`

Both services use the same Groq client (LLaMA 3.1 8B Instant) with different prompts.

**`GroqNlpService` — Gloss enrichment:**

- **Temperature:** 0.4 — enough variety to sound natural, no hallucinations
- **Max tokens:** 120 — a sentence, not a paragraph
- **System prompt:** instructs the model to act as an ASL → English translator and respond ONLY with the translated sentence

**`SentimentService` — Sentiment classification:**

- **Temperature:** 0.2 — very deterministic, only three possible outputs
- **Max tokens:** 5 — one word: `positive`, `neutral`, or `negative`
- **Sanitisation:** if the model returns something unexpected, falls back to `neutral`

```js
const sentiment = ['positive', 'negative', 'neutral'].includes(raw) ? raw : 'neutral';
```

### 3.7 TTS — `ElevenLabsTtsService` (integrated but inactive)

The service exists and works, but is commented out in `TranslateSign.js`:

```js
// ElevenLabsTtsService kept for future paid-tier integration
// const { synthesizeSpeech } = require('../../infrastructure/tts/ElevenLabsTtsService');
```

When reactivated, the flow will add a step: text enriched by Groq is sent to ElevenLabs, which returns MP3 audio encoded in base64. That base64 travels via socket to the Guest, which decodes it and plays it in the browser. The configurable voice ID in `.env` (`ELEVENLABS_VOICE_ID`) allows choosing the voice without touching code.

---

## 4. Complete End-to-End Flows

### Flow A — Host signs → Guest receives (main path)

```
[Host Browser]
  camera + MediaPipe + LSTM → detects "lower wrists" gesture
  → socket.emit('sign-data', { phrase: ["MORE", "WATER"] })

[Server]
  connection-manager.js     → socket.on('sign-data', handleSignData(socket))
  SignController.js         → checks roomId, calls executeTranslateSign(data)
  TranslateSign.js          → processSignData()  → rawGloss "MORE WATER"
                            → enrichGlossToNaturalEnglish("MORE WATER")
  GroqNlpService.js         → Groq API (LLaMA 3.1 8B) → "Could I have more water?"
  TranslateSign.js          → returns { status:'success', text:'...', timestamp:'...' }
  SignController.js         → socket.to(roomId).emit('translation-update', result)

[Guest Browser]
  socket.on('translation-update') → renders subtitle on screen
```

### Flow B — Guest speaks → Host receives with emotional indicator

```
[Guest Browser]
  MediaRecorder records audio (WebM or MP4) → ArrayBuffer
  → socket.emit('guest-audio', buffer, mimeType)

[Server]
  connection-manager.js       → socket.on('guest-audio', handleGuestAudio(socket))
  AudioController.js          → checks roomId
  TranscribeAudio.js          → writes buffer to temp file
                              → Groq Whisper (whisper-large-v3-turbo) → "Yes, that sounds great!"
  AudioController.js          → socket.emit('guest-transcript', { text })  ← confirmation to Guest
  AnalyzeGuestReply.js        → validates text
                              → analyzeSentiment("Yes, that sounds great!")
  SentimentService.js         → Groq API (LLaMA 3.1 8B) → "positive"
  AnalyzeGuestReply.js        → returns { status:'success', text:'...', sentiment:'positive', timestamp:'...' }
  AudioController.js          → socket.to(roomId).emit('guest-reply-update', result)

[Host Browser]
  socket.on('guest-reply-update') → shows reply + sentiment visual indicator
```

### Flow C — Guest starts speaking (relay with no logic)

```
[Guest Browser]
  MediaRecorder starts recording
  → socket.emit('guest-speaking', { active: true })

[Server]
  connection-manager.js → socket.to(roomId).emit('guest-speaking', data)
  // no controller, no use-case — direct relay

[Host Browser]
  socket.on('guest-speaking') → shows "Listener is responding…" indicator
```

---

## 5. Layer-Based Logging System

The backend uses `chalk` to visually distinguish logs from each layer in the terminal:

| Prefix | Colour | Layer | When it appears |
|---|---|---|---|
| `[Core]` | Green | `asl-core/translator.js` | Gloss validation |
| `[UseCase]` | Magenta | `application/use-cases/` | Orchestration start and result |
| `[Controller]` | Cyan | `infrastructure/controllers/` | Payload received and emitted |
| `[NLP]` | Yellow | `infrastructure/nlp/Groq*` | Groq call and response |
| `[Sentiment]` | Yellow | `infrastructure/nlp/Sentiment*` | Sentiment classification |
| `[TTS]` | Blue | `infrastructure/tts/` | Audio synthesis (when reactivated) |
| `[Net]` | Blue | `connection-manager.js` | Connection, join-room, disconnect |

A complete Flow A trace in terminal looks like this:

```
[Net]        🚪 host joined room: abc123
[Net]        🚪 guest joined room: abc123
[Controller] 📥 sign-data received from XyZ: { phrase: ['MORE', 'WATER'] }
[Core]       🧠 Validating incoming sign data...
[Core]       ✨ Raw gloss: "MORE WATER"
[UseCase]    ⚙️  Orchestrating translation...
[NLP]        🤖 Enriching gloss with Groq: "MORE WATER"
[NLP]        ✅ Enriched: "Could I have more water, please?"
[Controller] 📤 Emitting to room abc123: { status: 'success', text: '...' }
```

---

## 6. Standard Response Contract

All layers that return results use the same structure so that upper layers do not need to know where the error originated:

```js
// Success
{ status: 'success', text: string, timestamp: ISO8601 }

// Success with sentiment (AnalyzeGuestReply)
{ status: 'success', text: string, sentiment: 'positive'|'neutral'|'negative', timestamp: ISO8601 }

// Error (any layer)
{ status: 'error', message: string }
```

---

## 7. External Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `socket.io` | ^4.7.2 | Bidirectional WebSocket with rooms |
| `express` | ^4.18.2 | Base HTTP server (required by socket.io) |
| `groq-sdk` | ^1.2.0 | Official Groq client (NLP + Sentiment + Whisper STT) |
| `@elevenlabs/elevenlabs-js` | ^2.46.0 | Official ElevenLabs client (TTS, inactive) |
| `chalk` | ^4.1.2 | Coloured terminal logs |
| `dotenv` | ^17.4.2 | Environment variables from `.env` |
| `cors` | ^2.8.5 | CORS headers in Express |
| `nodemon` | ^3.0.1 | Live reload in development (devDep) |

---

## 8. Current Status and Next Steps

**100% operational:**
- Flow A complete (Host signs → Groq enriches → Guest receives subtitle)
- Flow B complete (Guest speaks → Groq classifies sentiment → Host receives)
- Room system with `join-room`
- Layer-coloured logs

**Integrated but inactive:**
- `ElevenLabsTtsService` — the service is built and tested; just needs to be uncommented in `TranslateSign.js` when the paid TTS is activated

**Pending:**
- `GuestPage` on the frontend does not yet consume `guest-reply-update` — the server logic exists, the client does not listen yet
- No room authentication — any client that knows the `roomId` can join
