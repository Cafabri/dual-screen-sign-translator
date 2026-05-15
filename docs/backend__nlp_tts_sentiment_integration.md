> **Module:** [`backend-sockets/src/infrastructure/nlp/`](../backend-sockets/src/infrastructure/nlp/) · [`backend-sockets/src/infrastructure/tts/`](../backend-sockets/src/infrastructure/tts/)
> **Phase:** 5 — NLP, TTS, and Sentiment Integration

# Phase 5 — NLP, TTS, and Sentiment Analysis Integration

**Project:** DualSign — Real-Time Bidirectional ASL Translator
**Date:** May 2026
**Branch:** `develop`

---

## 1. Context and Goals

At the start of Phase 5, DualSign had the full signing flow working end-to-end: the Deaf user signed in front of the camera, the LSTM model detected the glosses, and the "lower wrists" gesture sent the phrase to the backend. However, what reached the Guest was a raw array of labels (`["more", "apple"]`) with no linguistic processing, and the listener's screen was an empty skeleton.

The goal of Phase 5 was to turn that technical flow into a real conversation experience:

| Task | Goal |
|---|---|
| **T1** | Enrich raw glosses with NLP → natural English |
| **T2** | Read the translation aloud on the listener's device |
| **T3** | Capture the listener's spoken reply and analyse it emotionally |
| **T4** | Render dynamic subtitles on the Host screen based on detected sentiment |
| **Bonus** | Conversation history on the Guest + visual indicator on the Host |

---

## 2. Task 1 — NLP Enrichment with Groq

### What was built

An NLP layer was added between the backend and the Guest to transform raw ASL glosses into conversational natural English before displaying them.

**Flow:**
```
["more", "apple"]  →  Groq (llama-3.1-8b-instant)  →  "I'd like to have some more apples."
```

**Files created/modified:**
- `infrastructure/nlp/GroqNlpService.js` — adapter that calls the Groq API
- `application/use-cases/TranslateSign.js` — orchestrates validation + enrichment (now async)
- `asl-core/translator.js` — replaces placeholder; validates that `phrase` is a non-empty array, returns `rawGloss`
- `infrastructure/socket-server/controllers/SignController.js` — handler becomes `async/await`
- `entry-points/main.js` — adds `require('dotenv').config()` to load environment variables

### Design decisions

**Why Groq and not OpenAI?**
The user did not have a paid OpenAI account. Groq offers a very generous free tier with the `llama-3.1-8b-instant` model, which has ~200–500ms latency — critical for a real-time experience. The Groq API is compatible with the OpenAI API, so migrating in the future would only require changing the base URL and model name.

**Why does NLP live in infrastructure and not in the core?**
Clean Architecture was respected: `asl-core/translator.js` is pure logic with no external dependencies. The external API call lives in `infrastructure/nlp/`, and the use case orchestrates it. This ensures that replacing Groq with any other provider (OpenAI, Cohere, Gemini) only requires touching the adapter.

### Problems encountered

| Problem | Cause | Fix |
|---|---|---|
| Port 3000 occupied on server start | Previous test process was not properly closed | `lsof -ti :3000 \| xargs kill -9` |
| Server crashed if Groq failed | No `try/catch` in the controller | Added try/catch block in `SignController` to capture external service errors |
| Glosses arrive in lowercase (`'more', 'apple'`) | Frontend did not normalise before emitting | Kept as-is — Groq understands it equally and normalising to uppercase is cosmetic |

### Result

```
[NLP] ✅ Enriched: "I'd like to have some more apples."
[Controller] 📤 Emitting to room <id>: { status: 'success', text: "...", timestamp: "..." }
```

---

## 3. Task 2 — Text-to-Speech (TTS)

### Original plan: ElevenLabs

The initial plan was to integrate ElevenLabs in the backend: the server would generate the audio as MP3, encode it in base64, and include it in the `translation-update` event. The GuestPage would receive it and play it with `new Audio(dataUrl).play()`.

`@elevenlabs/elevenlabs-js` (the official package — the previous `elevenlabs` was deprecated) was installed and `infrastructure/tts/ElevenLabsTtsService.js` was created.

### Problem: ElevenLabs free tier block

On the first API call, ElevenLabs returned a `401 detected_unusual_activity` error:

```json
{
  "detail": {
    "status": "detected_unusual_activity",
    "message": "Unusual activity detected. Free Tier usage disabled..."
  }
}
```

ElevenLabs blocked the user's IP directly. It was not a VPN issue (the user had none active) nor an API key issue — the block was at the account/IP level. Creating a new key within the same account produced the same error.

### Fix: pivot to Web Speech API

The decision was made to pivot to the browser's native Web Speech API (`speechSynthesis`). Advantages:
- Completely free and unlimited
- Native in modern Chrome, Edge, and Safari
- No additional network latency
- The ElevenLabs integration was left commented out in the code for activation in the future with a paid account

**Backend change:** removed the `synthesizeSpeech()` call from the use case. The payload no longer includes `audio`.

**Frontend change:** GuestPage uses `window.speechSynthesis.speak(utterance)` when `translation-update` arrives.

**Important detail:** modern browsers block `speechSynthesis` until the user interacts with the page. The Guest must click on the page at least once for the first audio to work.

---

## 4. Task 3 — Sentiment Analysis on the Listener's Reply

### What was built

The full bidirectional flow was implemented: the Guest can reply with voice, and that reply is analysed emotionally before reaching the Host.

**Flow:**
```
Guest records audio → MediaRecorder → ArrayBuffer
  → socket.emit('guest-audio', buffer, mimeType)
  → Groq Whisper transcribes → "Yes, that sounds great!"
  → socket.emit('guest-transcript', { text })   ← confirmation to Guest
  → Groq analyses sentiment → "positive" | "neutral" | "negative"
  → socket.to(roomId).emit('guest-reply-update', { text, sentiment, timestamp })
  → Host receives the categorised reply
```

**Files created/modified:**
- `infrastructure/nlp/SentimentService.js` — calls Groq with a prompt specialised in emotional classification
- `application/use-cases/AnalyzeGuestReply.js` — validates the text and orchestrates the analysis
- `application/use-cases/TranscribeAudio.js` — writes audio to a temp file and calls Groq Whisper (`whisper-large-v3-turbo`)
- `controllers/GuestReplyController.js` — handles `guest-reply` event with async/await and try/catch
- `controllers/AudioController.js` — handles `guest-audio`: transcribes with Whisper → analyses sentiment → emits to Host
- `connection-manager.js` — registers `socket.on('guest-audio', handleGuestAudio(socket))`
- `GuestPage.jsx` — microphone button with `MediaRecorder`, shows transcript received from backend

### Problems encountered

**Problem 1: iOS Safari blocked voice recognition (`service-not-allowed`)**

The original plan used `webkitSpeechRecognition` (Web Speech API). During mobile access tests via local network + Cloudflare Tunnel, iOS Safari consistently returned `service-not-allowed` even with microphone permission and Dictation enabled. The root cause is a WebKit restriction: the speech recognition API does not work in tabs opened externally (from QR or link) and depends on Apple infrastructure that is not always available.

**Definitive fix:** `webkitSpeechRecognition` was replaced with `MediaRecorder` + **Groq Whisper** (`whisper-large-v3-turbo`). Audio is recorded in the browser, sent as an `ArrayBuffer` to the backend via socket, the backend transcribes it with Whisper and returns the text. This architecture works in any browser (Safari, Chrome, Firefox, Opera) on any device, without secure-context restrictions or native implementation constraints.

**Problem 2: Everything was classified as "neutral"**

With `temperature: 0`, the `llama-3.1-8b-instant` model was excessively conservative and assigned `neutral` to almost any English phrase.

**Fix:** the `SentimentService` prompt was improved with:
- More directive instructions ("Be decisive")
- 6 concrete examples (2 per category) to calibrate the model
- `temperature: 0.2` to allow more decisive responses

```javascript
// Before
'reply with ONLY one word: positive, neutral, or negative'

// After
'Be decisive — lean positive for warm/happy/grateful messages... Examples:\n"Yes that sounds great!" → positive\n...'
```

---

## 5. Task 4 — Dynamic Sentiment-Based Subtitles on the Host

### What was built

A panel in `HostPage.jsx` that appears when a Guest reply arrives, with a completely different visual design depending on the detected sentiment.

**Sentiment map:**

| Sentiment | Background | Text colour | Border | Emojis | Label |
|---|---|---|---|---|---|
| `positive` | `#0b2216` | `#56d364` | `#3fb950` | 😊 ✨ | Positive |
| `neutral` | `#0b1a2b` | `#79c0ff` | `#58a6ff` | 💬 | Neutral |
| `negative` | `#2b0b0b` | `#ff7b72` | `#f85149` | 😔 | Concerned |

The panel includes:
- Dark background tinted with the sentiment colour
- Luminous border with colour `box-shadow`
- Descriptive emoji cluster
- Badge with the emotional state label
- Reply text in italics with the sentiment colour

The colour configuration lives in a `SENTIMENT_CONFIG` object outside the component, keeping the JSX clean.

---

## 6. Additional Features

### 6.1 — Conversation history on the Guest

**Problem:** the Guest only saw the last message, losing conversation context.

**Fix:** the `subtitle` state (string) was replaced with `messages` (array). Each message stores the text and a formatted timestamp (`HH:MM`). A `ref` (`messagesEndRef`) is used for auto-scroll to the most recent message. The history has `maxHeight: 50vh` with vertical scroll to not occupy the whole screen.

### 6.2 — Visual indicator on the Host when the Guest speaks

**Goal:** the Host (Deaf user) cannot hear the listener — they need to know when the Guest is speaking to avoid signing over them.

**Implementation:**
- `GuestPage` emits `guest-speaking: { active: true/false }` when starting and stopping `MediaRecorder`
- The backend performs a simple relay in `connection-manager.js` (no use case, no controller — no business logic)
- `HostPage` listens to the event and shows a pulsing blue banner: *"Listener is responding…"*

---

## 7. Phase 5 Final Architecture

```
Host signs → ["more", "apple"]
  → SignController → TranslateSign (use-case)
    → translator.js (Core): validates array
    → GroqNlpService: "I'd like more apples."
  → socket.to(roomId).emit('translation-update', { text, timestamp })
  → GuestPage: adds to history + speechSynthesis.speak()

Guest replies (push-to-talk)
  → MediaRecorder records audio → ArrayBuffer
  → socket.emit('guest-speaking', { active: true })   ← relay to Host
  → socket.emit('guest-audio', buffer, mimeType)
    → AudioController → TranscribeAudio (use-case)
      → Groq Whisper (whisper-large-v3-turbo): "Yes, that sounds great!"
    → socket.emit('guest-transcript', { text })        ← confirmation to Guest
    → AudioController → AnalyzeGuestReply (use-case)
      → SentimentService: "positive"
  → socket.to(roomId).emit('guest-reply-update', { text, sentiment })
  → HostPage: green panel with 😊 ✨
```

---

## 8. Status at Phase 5 Close

| Component | Status |
|---|---|
| NLP (Groq) glosses → natural English | ✅ Working |
| TTS Web Speech API (`speechSynthesis`) | ✅ Working (speech synthesis, any browser) |
| STT Groq Whisper (`whisper-large-v3-turbo`) | ✅ Working (transcription via MediaRecorder, any browser/OS) |
| TTS ElevenLabs | ⏸ Pending paid account |
| Sentiment analysis (Groq) | ✅ Working |
| Dynamic sentiment-based subtitles | ✅ Working |
| Conversation history on Guest | ✅ Working |
| "Guest responding" indicator on Host | ✅ Working |

## 9. Identified Technical Debt

- **Debug panel** in `HostPage.jsx` — was temporary since Milestone 4, pending removal
- **LSTM model domain shift** — only `MORE`, `PLEASE`, `APPLE` are reliable on a real webcam; requires fine-tuning with ~10–15 real recordings per class
- **Emotional TTS** — `ElevenLabsTtsService.js` is ready in code, needs a paid ElevenLabs account
- **Mobile-first Host design** — currently fixed at 640px, does not work well on mobile
- **Production deploy** — Render/Railway for backend, Vercel for frontend
