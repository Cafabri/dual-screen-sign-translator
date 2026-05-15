import { useEffect, useRef, useState, useCallback } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import useWebcam from '../hooks/useWebcam';
import useMediaPipe from '../hooks/useMediaPipe';
import useSignClassifier from '../hooks/useSignClassifier';
import useSendGesture, { WORD_SEPARATOR_RATIO } from '../hooks/useSendGesture';
import useSocket from '../hooks/useSocket';
import GestureOnboarding from '../components/GestureOnboarding';

const VIDEO_WIDTH  = 640;
const VIDEO_HEIGHT = 480;

const SENTIMENT_CONFIG = {
  positive: {
    label: 'Positive',
    emojis: '😊 ✨',
    wrapper: 'border-emerald-500/20 bg-emerald-500/[0.04]',
    badge:   'border-emerald-500/30 text-emerald-400',
    text:    'text-emerald-300/90',
  },
  neutral: {
    label: 'Neutral',
    emojis: '💬',
    wrapper: 'border-blue-500/20 bg-blue-500/[0.04]',
    badge:   'border-blue-500/30 text-blue-400',
    text:    'text-blue-300/90',
  },
  negative: {
    label: 'Concerned',
    emojis: '😔',
    wrapper: 'border-red-500/20 bg-red-500/[0.04]',
    badge:   'border-red-500/30 text-red-400',
    text:    'text-red-300/90',
  },
};

const STATUS_PILL = {
  error:     'border-red-500/30 bg-red-500/10 text-red-400',
  recording: 'border-red-500/30 bg-red-500/10 text-red-400',
  live:      'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
  loading:   'border-amber-500/30 bg-amber-500/10 text-amber-400',
};

function HostPage() {
  const { videoRef, isStreaming, cameraError, startVideoStreaming } = useWebcam();
  const canvasRef     = useRef(null);
  const frameCountRef = useRef(0);
  const roomIdRef     = useRef(
    typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  );
  const guestUrl = `${import.meta.env.VITE_PUBLIC_URL || window.location.origin}/guest?room=${roomIdRef.current}`;

  // eslint-disable-next-line no-unused-vars
  const [debugInfo, setDebugInfo] = useState({ frames: 0, leftHandNonZeros: 0, rightHandNonZeros: 0, handsVisible: 0 });
  const [isQrOpen, setIsQrOpen]   = useState(false);

  const {
    isModelReady, predictedGloss, stableGloss, confidence, allProbabilities,
    addFrame: classifyFrame,
  } = useSignClassifier();

  const {
    isRecording, isWordSeparatorActive, isSendGestureActive, sendGestureProgress,
    addFrame: gestureFrame,
    handsVisibleCountRef,
  } = useSendGesture();

  const socket = useSocket();

  const [guestReply, setGuestReply]         = useState(null);
  const [isGuestSpeaking, setIsGuestSpeaking] = useState(false);

  useEffect(() => {
    socket.on('guest-reply-update', ({ text, sentiment }) => setGuestReply({ text, sentiment }));
    socket.on('guest-speaking', ({ active }) => setIsGuestSpeaking(active));
    return () => {
      socket.off('guest-reply-update');
      socket.off('guest-speaking');
    };
  }, [socket]);

  const phraseRef          = useRef([]);
  const [phrase, setPhrase] = useState([]);
  const lastStableGlossRef = useRef(null);

  useEffect(() => {
    if (isRecording && sendGestureProgress === 0 && stableGloss) {
      lastStableGlossRef.current = stableGloss;
    }
  }, [isRecording, sendGestureProgress, stableGloss]);

  useEffect(() => {
    if (!isWordSeparatorActive) return;
    const word = lastStableGlossRef.current;
    if (!word) return;
    phraseRef.current = [...phraseRef.current, word];
    setPhrase([...phraseRef.current]);
    lastStableGlossRef.current = null;
  }, [isWordSeparatorActive]);

  const [sentFlash, setSentFlash] = useState(null);

  useEffect(() => {
    if (!isSendGestureActive || !phraseRef.current.length) return;
    socket.emit('sign-data', { phrase: phraseRef.current, timestamp: new Date().toISOString() });
    setSentFlash([...phraseRef.current]);
    phraseRef.current = [];
    setPhrase([]);
    lastStableGlossRef.current = null;
    setTimeout(() => setSentFlash(null), 2500);
  }, [isSendGestureActive]);

  const handleFrame = useCallback((featureVector) => {
    classifyFrame(featureVector);
    gestureFrame(featureVector);

    frameCountRef.current += 1;
    if (frameCountRef.current % 15 === 0) {
      let leftHandNonZeros = 0;
      let rightHandNonZeros = 0;
      for (let i = 1503; i < 1566; i++) if (featureVector[i] !== 0) leftHandNonZeros++;
      for (let i = 1566; i < 1629; i++) if (featureVector[i] !== 0) rightHandNonZeros++;
      setDebugInfo({ frames: frameCountRef.current, leftHandNonZeros, rightHandNonZeros, handsVisible: handsVisibleCountRef.current });
    }
  }, [classifyFrame, gestureFrame]);

  const { isMediaPipeReady } = useMediaPipe(videoRef, canvasRef, handleFrame);

  useEffect(() => {
    startVideoStreaming();
    socket.emit('join-room', { roomId: roomIdRef.current, role: 'host' });
  }, []);

  const systemReady = isMediaPipeReady && isModelReady;

  const statusLabel = cameraError                                       ? 'Camera Error'
    : !isStreaming                                                      ? 'Starting…'
    : !isMediaPipeReady                                                 ? 'Loading MediaPipe…'
    : !isModelReady                                                     ? 'Loading Model…'
    : isRecording && sendGestureProgress >= WORD_SEPARATOR_RATIO       ? 'Keep lowering…'
    : isRecording && sendGestureProgress > 0                           ? 'Lower to add word…'
    : isRecording                                                       ? 'REC'
    : 'Live';

  const statusVariant = cameraError ? 'error' : isRecording ? 'recording' : systemReady ? 'live' : 'loading';
  const currentWord   = stableGloss || predictedGloss;
  const showOnboarding = !isRecording && phrase.length === 0 && !sentFlash;

  // allProbabilities kept in scope — available for future diagnostic overlay
  void allProbabilities;

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center pt-8 sm:pt-10 pb-20 px-4 sm:px-6 gap-4 sm:gap-5">

      {/* ── Header ────────────────────────────────────────────────────── */}
      <header className="w-full max-w-[640px] flex items-center justify-between">
        <span className="text-[11px] font-semibold tracking-[0.28em] uppercase text-white/25 select-none">
          DualSign · Host
        </span>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[11px] font-semibold tracking-wide ${STATUS_PILL[statusVariant]}`}>
          {(statusVariant === 'recording' || statusVariant === 'live') && (
            <span className={`w-1.5 h-1.5 rounded-full ${statusVariant === 'recording' ? 'bg-red-400 animate-pulse' : 'bg-emerald-400'}`} />
          )}
          {statusLabel}
        </div>
      </header>

      {/* ── Video ─────────────────────────────────────────────────────── */}
      {/* Container uses aspect-[4/3] so it scales fluidly on any screen.
          Video/canvas keep their native 640×480 intrinsic dims for MediaPipe
          but display fills the container via object-cover. */}
      <div className="relative w-full max-w-[640px] rounded-2xl sm:rounded-3xl overflow-hidden border border-white/[0.07] shadow-2xl shadow-black/70 aspect-[4/3]">
        {cameraError ? (
          <div className="absolute inset-0 flex items-center justify-center bg-white/[0.02]">
            <p className="text-red-400/80 text-sm text-center px-10">{cameraError}</p>
          </div>
        ) : (
          <>
            <video
              ref={videoRef} autoPlay muted playsInline
              width={VIDEO_WIDTH} height={VIDEO_HEIGHT}
              className="absolute inset-0 w-full h-full object-cover [transform:scaleX(-1)]"
            />
            {/* Canvas stays in DOM so MediaPipe can draw — hidden from the user */}
            <canvas
              ref={canvasRef}
              width={VIDEO_WIDTH} height={VIDEO_HEIGHT}
              className="absolute inset-0 w-full h-full opacity-0 pointer-events-none [transform:scaleX(-1)]"
            />
          </>
        )}
        {/* Depth vignette */}
        <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/60 to-transparent pointer-events-none" />
      </div>

      {/* ── Live Detection Badge ───────────────────────────────────────── */}
      {isRecording && (
        <div className="flex items-center gap-2.5 px-4 py-2 rounded-full border border-white/[0.08] bg-white/[0.03] backdrop-blur-xl shadow-lg shadow-black/30">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shrink-0" />
          <span className="text-[13px] text-white/40">Detecting:</span>
          <span className="text-[13px] font-semibold text-white/90 min-w-[60px]">
            {currentWord ? currentWord.toUpperCase() : '—'}
          </span>
          {currentWord && (
            <span className="text-[11px] text-white/30 border-l border-white/10 pl-2.5">
              {Math.round(confidence * 100)}%{stableGloss ? ' ✓' : ''}
            </span>
          )}
        </div>
      )}

      {/* ── Phrase Panel ──────────────────────────────────────────────── */}
      <div className={`w-full max-w-[640px] min-h-[72px] rounded-2xl border transition-all duration-300 flex items-center justify-center flex-wrap gap-2 px-5 py-4 ${
        isRecording ? 'border-blue-500/20 bg-blue-500/[0.03]' : 'border-white/[0.06] bg-white/[0.02]'
      }`}>
        {sentFlash ? (
          <div className="flex flex-col items-center gap-2 w-full">
            <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-emerald-400/70">✓ Sent</span>
            <div className="flex flex-wrap gap-2 justify-center">
              {sentFlash.map((word, i) => (
                <span key={i} className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-semibold tracking-wider">
                  {word.toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        ) : phrase.length > 0 ? (
          <div className="flex flex-wrap gap-2 justify-center">
            {phrase.map((word, i) => (
              <span key={i} className="px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-semibold tracking-wider">
                {word.toUpperCase()}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-[13px] text-white/20 select-none">
            {!systemReady ? 'Loading systems…' : isRecording ? 'Sign a word…' : 'Raise both hands to start signing'}
          </p>
        )}
      </div>

      {/* ── Send Progress Bar ─────────────────────────────────────────── */}
      {sendGestureProgress > 0 && (
        <div className="w-full max-w-[640px] flex flex-col gap-2">
          <div className="relative h-1.5 rounded-full bg-white/[0.05] overflow-visible">
            <div
              className="absolute inset-y-0 left-0 rounded-full transition-all duration-75"
              style={{
                width: `${Math.round(sendGestureProgress * 100)}%`,
                background: sendGestureProgress >= WORD_SEPARATOR_RATIO ? '#34d399' : '#f59e0b',
              }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-px h-3 bg-white/20 rounded-full"
              style={{ left: `${Math.round(WORD_SEPARATOR_RATIO * 100)}%` }}
            />
          </div>
          <p className={`text-[11px] text-center font-medium ${
            sendGestureProgress >= WORD_SEPARATOR_RATIO ? 'text-emerald-400/70' : 'text-amber-400/70'
          }`}>
            {sendGestureProgress >= WORD_SEPARATOR_RATIO ? 'Keep lowering to send phrase…' : 'Lower to add word…'}
          </p>
        </div>
      )}

      {/* ── Guest Speaking Indicator ──────────────────────────────────── */}
      {isGuestSpeaking && (
        <div className="w-full max-w-[640px] flex items-center gap-3 px-4 py-3 rounded-2xl border border-blue-500/20 bg-blue-500/[0.04]">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse shrink-0" />
          <span className="text-[13px] text-blue-300/80 font-medium">Listener is responding…</span>
        </div>
      )}

      {/* ── Guest Reply ───────────────────────────────────────────────── */}
      {guestReply && (() => {
        const cfg = SENTIMENT_CONFIG[guestReply.sentiment] ?? SENTIMENT_CONFIG.neutral;
        return (
          <div className={`w-full max-w-[640px] relative rounded-2xl overflow-hidden border p-5 ${cfg.wrapper}`}>
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            <div className="flex items-center gap-2.5 mb-3">
              <span className="text-base leading-none">{cfg.emojis}</span>
              <span className={`text-[10px] font-semibold tracking-[0.18em] uppercase px-2.5 py-0.5 rounded-full border ${cfg.badge}`}>
                {cfg.label}
              </span>
            </div>
            <p className={`text-[15px] font-medium italic leading-relaxed ${cfg.text}`}>
              "{guestReply.text}"
            </p>
          </div>
        );
      })()}

      {/* ── QR Panel (collapsible) ────────────────────────────────────── */}
      <div className="w-full max-w-[640px] relative rounded-2xl overflow-hidden border border-white/[0.07] bg-white/[0.025] backdrop-blur-xl">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        {/* Header row — always visible, click to toggle */}
        <button
          onClick={() => setIsQrOpen(v => !v)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors duration-150 cursor-pointer"
        >
          <div className="flex items-center gap-2.5">
            {/* QR grid icon */}
            <svg className="w-3.5 h-3.5 text-white/30" viewBox="0 0 16 16" fill="currentColor">
              <rect x="0" y="0" width="6" height="6" rx="1" /><rect x="10" y="0" width="6" height="6" rx="1" />
              <rect x="0" y="10" width="6" height="6" rx="1" /><rect x="10" y="10" width="3" height="3" rx="0.5" />
              <rect x="10" y="7" width="3" height="2" rx="0.5" /><rect x="13" y="10" width="3" height="6" rx="0.5" />
            </svg>
            <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-white/35">
              Listener Link
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            {!isQrOpen && (
              <span className="text-[11px] text-white/20 font-mono truncate max-w-[120px] sm:max-w-[280px]">
                {guestUrl}
              </span>
            )}
            <svg
              className={`w-3.5 h-3.5 text-white/25 transition-transform duration-200 shrink-0 ${isQrOpen ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>

        {/* Expanded content */}
        {isQrOpen && (
          <div className="flex items-center gap-5 px-4 pb-4 pt-3 border-t border-white/[0.05]">
            <div className="shrink-0 bg-white p-2.5 rounded-xl shadow-lg shadow-black/40">
              <QRCodeSVG value={guestUrl} size={110} />
            </div>
            <div className="flex flex-col gap-1.5 min-w-0">
              <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-white/25">
                Share this link with the listener
              </span>
              <p className="text-[11px] text-white/40 break-all leading-relaxed font-mono">
                {guestUrl}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Gesture Onboarding ────────────────────────────────────────── */}
      {showOnboarding && (
        <div className="w-full max-w-[640px]">
          <GestureOnboarding />
        </div>
      )}

    </div>
  );
}

export default HostPage;
