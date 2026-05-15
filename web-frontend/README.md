# DualSign — Host App (Deaf User Interface)

> **Status:** Milestones 1–6 complete. The camera captures input, MediaPipe extracts landmarks, the LSTM model classifies signs in real time, and a physical gesture system controls when to record and when to send.

---

## What Has Been Built

### General Architecture

The frontend follows a **specialised hooks architecture** (one hook = one responsibility). `HostPage.jsx` acts as an orchestrator that connects them but contains no logic of its own. Each hook is independent, testable, and easy to replace.

```
web-frontend/src/
├── hooks/
│   ├── useWebcam.js          # Camera lifecycle
│   ├── useMediaPipe.js       # Landmark extraction + skeleton drawing
│   ├── useSignClassifier.js  # LSTM inference with TF.js
│   ├── useSendGesture.js     # State machine: idle → recording → send
│   └── useSocket.js          # Socket.io connection to the backend
└── pages/
    └── HostPage.jsx          # Orchestrator: connects the 5 hooks
```

Data flow per frame:

```
Camera (30fps)
  → useMediaPipe.sendFrameLoop()
    → holistic.send(videoFrame)
      → onResults(results)
        → buildFeatureVector()  →  Float32Array(1629)
          → useSignClassifier.addFrame()  →  LSTM inference  →  predictedGloss / stableGloss
          → useSendGesture.addFrame()     →  state machine   →  isRecording / isSendGestureActive
```

---

## Milestone 1 — Webcam (`useWebcam`)

Manages the `getUserMedia` lifecycle. Key points:

- `streamRef` is separate from `videoRef`: the stream is saved in a ref so the `useEffect` cleanup can call `track.stop()` even after the component has unmounted.
- `startVideoStreaming` is idempotent: if a stream is already active, it does nothing. Prevents opening multiple streams on re-render.
- Distinguishes between permission denied (`NotAllowedError`) and technical errors to show useful messages.

---

## Milestone 2 — MediaPipe Holistic (`useMediaPipe`)

### What it does

Initialises MediaPipe Holistic, starts the frame loop, draws the skeleton on a `<canvas>` overlaid on the `<video>`, and on every frame builds a `Float32Array(1629)` with all landmarks flattened:

```
pose (33 pts × 3) = 99 values       → indices [0..98]
face (468 pts × 3) = 1404 values    → indices [99..1502]
left_hand (21 pts × 3) = 63 values  → indices [1503..1565]
right_hand (21 pts × 3) = 63 values → indices [1566..1628]
```

This order is identical to the one used by `extract_features.py` in the ML pipeline. Any discrepancy breaks inference.

### Problem 1 — MediaPipe is incompatible with Vite (npm vs CDN)

**Symptom:** The page went completely blank when importing `@mediapipe/holistic` from npm.

**Cause:** `@mediapipe/*` packages are compiled with Closure Compiler as IIFEs (global page scripts). They are not ESM modules. When Vite tries to analyse them as ESM for its bundling pipeline, it fails because no valid exports are found. The WASM bundled with MediaPipe also cannot be loaded by the bundler in the standard way.

**Fix:** Uninstall the npm packages and load MediaPipe directly from CDN as classic scripts in `index.html`, before the React bundle:

```html
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675471629/holistic.js" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils@0.3.1675466124/drawing_utils.js" crossorigin="anonymous"></script>
```

The symbols `Holistic`, `drawConnectors`, `drawLandmarks`, `POSE_CONNECTIONS`, etc. become available on `window` and are accessed from hooks via `window.Holistic`, `window.drawConnectors`, etc.

### Problem 2 — `holistic.initialize()` never resolved

**Symptom:** The status badge stayed on "Loading MediaPipe…" indefinitely even though the CDN scripts loaded correctly.

**Cause:** `holistic.initialize()` returns a Promise that, under certain network or WASM loading conditions, never resolves. There is no official documentation about when it silently fails.

**Fix:** Remove `initialize()` entirely. MediaPipe Holistic loads WASM lazily on the first `holistic.send()` call. The frame loop starts immediately and `isMediaPipeReady` is set to `true` on the first `onResults` callback, which confirms that inference is running.

### Problem 3 — Feature vectors all zeros (JS API ≠ Python API)

**Symptom:** The classifier never produced predictions. Inspecting the vectors showed all values were `0`.

**Cause:** In the Python API, `results.pose_landmarks` is an object with a `.landmark` property (a list of points). In the JavaScript API, `results.poseLandmarks` is directly a flat array of `{x, y, z}` objects. The original code tried to access `landmarkArray?.landmark` as in Python, which in JS always returns `undefined`, causing the fallback function to fill the buffer with zeros.

**Fix:** In `flattenLandmarks`, use `landmarkArray` directly with a `.length` check:

```js
function flattenLandmarks(landmarkArray, pointCount) {
  if (!landmarkArray || !landmarkArray.length) return new Float32Array(pointCount * 3);
  const buffer = new Float32Array(pointCount * 3);
  landmarkArray.forEach(({ x, y, z }, index) => {
    buffer[index * 3]     = x;
    buffer[index * 3 + 1] = y;
    buffer[index * 3 + 2] = z;
  });
  return buffer;
}
```

### Problem 4 — The frame loop died silently

**Symptom:** Landmarks froze after a few seconds. The camera stayed active but the skeleton stopped updating.

**Cause:** A one-off error on a frame (corrupt frame, MediaPipe internal error) threw an uncaught exception inside `sendFrameLoop`, which terminated the `requestAnimationFrame` cycle with no recovery path.

**Fix:** Wrap `holistic.send()` in a `try/catch`. The error is ignored and the loop continues:

```js
const sendFrameLoop = async () => {
  const video = videoRef.current;
  if (video && !video.paused && video.readyState >= 2) {
    try {
      await holistic.send({ image: video });
    } catch {
      // Ignore per-frame errors and keep looping.
    }
  }
  animationFrameIdRef.current = requestAnimationFrame(sendFrameLoop);
};
```

### `onFrameReadyRef` pattern — avoiding stale closures in the loop

The MediaPipe loop is created once in the mount `useEffect` (deps `[]`). If `onFrameReady` were captured by value in that closure, it would always call the initial version of the callback, ignoring later updates (e.g. when `classifyFrame` or `gestureFrame` change reference).

The fix is a ref kept in sync with the prop:

```js
const onFrameReadyRef = useRef(onFrameReady);
useEffect(() => { onFrameReadyRef.current = onFrameReady; }, [onFrameReady]);
// In the loop: onFrameReadyRef.current?.(featureVector)
```

---

## Milestone 3 — LSTM Classifier (`useSignClassifier`)

### What it does

Loads the TF.js model from `public/models/model.json` (LSTM trained on 905 augmented WLASL samples, 82.32% test accuracy). Maintains a FIFO sliding window of 30 frames. Every 5 frames, if the window is full, it builds a `[1, 30, 1629]` tensor and runs inference. Returns the label with the highest probability if it exceeds the 0.50 threshold.

**10 classes:** `apple`, `bye`, `hello`, `help`, `more`, `no`, `please`, `thank_you`, `water`, `yes` — in alphabetical order, which is what `sorted(os.listdir())` generates in the Python pipeline. The order must always stay in sync.

### `stableGloss` — flicker filter

The model can oscillate between labels on consecutive frames. To prevent the UI from flickering, `stableGloss` is only updated after receiving **2 identical consecutive predictions**. `predictedGloss` updates every frame for immediate feedback.

### Problem — `addFrame` was discarding all frames (stale closure)

**Symptom:** The classifier never produced predictions even though `isModelReady` was `true`.

**Cause:** A previous version of `addFrame` had `if (!isModelReady) return` as its first line and was defined with `useCallback([isModelReady])`. On first render `isModelReady` is `false`. When it flipped to `true`, the callback was recreated with the new reference, but during the time it took to propagate to the MediaPipe loop, frames were still being discarded by the old reference.

**Fix:** Remove the `isModelReady` check from `addFrame`. The guard is placed inside `runInference` with `if (!modelRef.current) return`, which reads the ref directly and is never stale. The deps of `addFrame` become only `[runInference]`.

### Model export — problems in the Python pipeline

The model is trained in Keras and exported to TF.js with `tensorflowjs_converter`. Two problems were encountered during export:

**Protobuf conflict:** `tensorflowjs` installs `tensorflow-decision-forests` as a dependency, which requires protobuf 6.x, but the environment had protobuf 5.x. The fix was to mock the conflicting modules in `sys.modules` before importing `tensorflowjs`:

```python
import sys
sys.modules["tensorflow_decision_forests"] = type(sys)("mock")
sys.modules["tensorflow_hub"] = type(sys)("mock")
import tensorflowjs as tfjs
```

**snake_case keys in `model.json`:** TF.js expects camelCase keys in the architecture JSON, but the Python converter generates them in snake_case. The `ml/scripts/export_tfjs.py` script post-processes the JSON with 6 replacements: `batch_shape→batchInputShape`, `return_sequences→returnSequences`, `use_bias→useBias`, `recurrent_activation→recurrentActivation`, `unit_forget_bias→unitForgetBias`, `recurrent_dropout→recurrentDropout`.

### Real-world model performance (domain shift)

The model achieves 82.32% accuracy on the WLASL test set, but only **MORE, PLEASE, APPLE** and occasionally **HELP** work consistently on a real webcam.

The cause is **domain shift**: WLASL was recorded by professional interpreters under studio conditions (controlled lighting, standard angles, neutral clothing). A home webcam produces landmark distributions that are statistically very different from the training data.

The definitive fix is fine-tuning with 10–15 real recordings per class. This remains pending in the ML pipeline.

---

## Milestone 4 — Gesture State Machine (`useSendGesture`)

### Design: why two gestures, not one

The first version used a single gesture: lowering the hands. The problem was that the model kept classifying during the lowering transition and almost always predicted "hello" (the motion of lowering hands from chest level resembles the HELLO sign in intermediate frames). That "hello" was sent instead of the intended sign.

The fix was to split the cycle into two explicit gestures:

| Gesture | Action | Detection |
|---|---|---|
| **Raise both hands** | Start recording | Both hand sections (feat[1503..1628]) with non-zero values for 5 frames |
| **Lower both wrists below shoulders** | Send captured gloss | Both wrists with `wrist_y > shoulder_y + 0.35` for 25 frames |

This way the classifier only runs during the active recording window. Everything that happens after the hands go down (including erroneous "hello" predictions) is ignored because the latch is already frozen.

### Pose landmark detection (not hand sections)

The first implementation of the send gesture checked whether the hand sections of the feature vector were all zeros (hands absent). This was too fragile: MediaPipe loses hand tracking before the wrists are physically down, causing false positives.

The current implementation uses **pose landmarks** to compare wrist position against shoulders:

```
Left shoulder  → feat[34]  (pose[11].y)
Right shoulder → feat[37]  (pose[12].y)
Left wrist     → feat[46]  (pose[15].y)
Right wrist    → feat[49]  (pose[16].y)
```

In MediaPipe's coordinate system, `y=0` is the top of the image and `y=1` is the bottom. "Wrists below shoulders" translates to `wrist_y > shoulder_y + 0.35`. Requiring **both** wrists simultaneously prevents false positives during signs that only raise one hand.

### Problem — stale closure in `addFrame` (the most complex bug)

**Symptom:** The state machine never transitioned from `idle` to `recording`, even with both hands visible. `isRecording` always remained `false`.

**Cause:** `addFrame` was defined as `useCallback((featureVector) => { if (!isRecording) { ... } }, [isRecording])`. With `isRecording` as a dependency, `addFrame` was recreated on every change. The new reference reached `handleFrame` in `HostPage`, which in turn updated `onFrameReadyRef` in `useMediaPipe`. In the interval between renders, the frame loop called the old version of the callback, which had `isRecording` frozen at its previous value. The state machine never advanced because it always read the wrong state.

**Fix:** Introduce `isRecordingRef` — a ref that mirrors the state and is updated synchronously alongside `setIsRecording`:

```js
const isRecordingRef = useRef(false);

// Inside addFrame:
if (!isRecordingRef.current) {
  // ...
  isRecordingRef.current = true;  // updates the ref (synchronous, immediate)
  setIsRecording(true);           // updates state (triggers re-render)
}

// addFrame with empty deps — stable reference forever
const addFrame = useCallback((featureVector) => { ... }, []);
```

**General rule extracted:** in callbacks passed as data to other hooks, refs are read for logic; state is used only for rendering.

### Problem — `addFrame` was missing from the hook's return

**Symptom:** `gestureFrame` in `HostPage` was `undefined`. The state machine never received frames, with no console error.

**Cause:** `addFrame` was declared inside the hook but was absent from the return object.

**Lesson:** Always verify the `return` of a hook when a function "does nothing". JavaScript does not warn about missing properties in a destructured object — it simply returns `undefined`.

### The `lastStableGlossRef` latch

The classifier's `stableGloss` updates continuously while the model is inferring. To ensure the send gesture captures the last confirmed sign rather than a transient prediction during the lowering motion, `HostPage` maintains a ref that only updates when two conditions are met:

```js
if (isRecording && sendGestureProgress === 0 && stableGloss) {
  lastStableGlossRef.current = stableGloss;
}
```

As soon as `sendGestureProgress > 0` (the user starts lowering), the latch freezes. The socket emits whatever was in the latch at that moment.

---

## Milestone 5 — QR Code and Room System

### What it does

When `/host` loads, a unique `roomId` is generated with `crypto.randomUUID()` (with fallback for browsers without support). From that ID, the guest URL is constructed and a QR code is rendered that the listener scans with their phone.

```
/host generates roomId  →  guestUrl = origin/guest?room=<roomId>
                        →  <QRCodeSVG> displays the QR
                        →  socket.emit('join-room', { roomId, role: 'host' })

Guest scans QR          →  /guest?room=<roomId>
                        →  useSearchParams() reads the roomId
                        →  socket.emit('join-room', { roomId, role: 'guest' })
```

The guest URL uses `VITE_PUBLIC_URL` if defined in the environment, or `window.location.origin` as fallback, making the QR work both locally and in production without code changes.

### Room system in the backend

`connection-manager.js` handles `join-room` with `socket.join(roomId)` and stores the ID in `socket.data.roomId`. `SignController` emits `sign-data` only to `socket.to(roomId)`, so messages only reach participants in that room and not other connected hosts.

### Library

`qrcode.react` (v4.2.0) — added to `dependencies`. Exposes `<QRCodeSVG>`, which renders the QR as native SVG with no canvas dependencies.

---

## Milestone 6 — Full Phrases (Word Accumulation)

### Design: one gesture, two duration thresholds

Instead of sending a single word per session, the user can accumulate an array of glosses before sending. The same "lower wrists below shoulders" gesture has two meanings depending on how long it is held:

```
Wrists lower
  ├─ ~8 frames  (~0.27s)  → WORD SEPARATOR: adds word to array, keeps signing
  └─ ~25 frames (~0.83s)  → SEND: emits full phrase, returns to idle
```

No new gesture to learn. Duration communicates intent.

### Changes in `useSendGesture`

Two constants instead of one:
- `WORD_SEPARATOR_FRAMES = 8`
- `SEND_HOLD_FRAMES = 25`
- `WORD_SEPARATOR_RATIO = 8/25` — exported so `HostPage` can draw the mark on the progress bar

New `isWordSeparatorActive` pulse (identical in implementation to `isSendGestureActive`): fires exactly once per lowering thanks to `separatorFiredRef`, which resets when the wrists rise again.

```
Wrist lowering:
  frame 8  → separatorFiredRef = false → fires isWordSeparatorActive, separatorFiredRef = true
  frame 25 → fires isSendGestureActive, resets everything to idle
  wrists rise before frame 25 → sendHoldCount = 0, separatorFiredRef = false
```

### Changes in `HostPage`

Two new phrase variables:
- `phraseRef` (useRef) — accumulator array, written from effects, no own render
- `phrase` (useState) — copy for the UI

When `isWordSeparatorActive` fires: reads `lastStableGlossRef.current`, adds it to `phraseRef`, updates `phrase`, clears the latch.

When `isSendGestureActive` fires: emits `socket.emit('sign-data', { phrase: [...] })`, clears array and latch.

The `lastStableGlossRef` latch continues to freeze at `sendGestureProgress > 0`, as before, protecting against transition predictions.

### Problem — PLEASE stopped being detected

**Symptom:** After enabling phrase accumulation, the PLEASE sign (rubbing the chest) was being interrupted by the word separator.

**Cause:** PLEASE is performed at chest level, which with `BELOW_SHOULDER_MARGIN = 0.25` could fall within the detection threshold. With the shoulder at y≈0.35, the threshold required wrist at y>0.60, and the chest can be in that zone depending on camera position.

**Fix:** Raise `BELOW_SHOULDER_MARGIN` from `0.25` to `0.35`. This raises the threshold to y>0.70 (waist/abdomen), well below the signing space.

### Progress bar with separator mark

The existing bar is reused with two visual improvements:
- A fixed vertical mark at `32%` (position of `WORD_SEPARATOR_RATIO`) indicates the "add word" point
- The colour changes from yellow to green after crossing that mark, visually confirming the word has been captured

---

## Current UI State

```
[Camera + skeleton]   ← canvas overlaid on video (scaleX(-1) for mirror effect)
[Status badge]        ← Starting camera… → Loading MediaPipe… → Loading model…
                         → ● Live → ● REC → Lower to add word… → Keep lowering to send…
[QR panel]            ← QR generated on mount, points to /guest?room=<roomId>
[Prediction panel]    ← confirmed word chips + large active gloss with confidence
                         Green flash "✓ SENT" with chips of the sent phrase
[Progress bar]        ← yellow up to 32% (add), green past 32% (send)
                         fixed vertical mark at the separation point
[Probability bars]    ← all 10 classes with their probability in real time
```

---

## How to Run

```bash
# Terminal 1 — Backend (port 3000)
cd backend-sockets && npm install && npm run dev

# Terminal 2 — Frontend (port 5173)
cd web-frontend && npm install && npm run dev
```

Open `http://localhost:5173/host`. The TF.js model is in `public/models/` (already included in the repo).
