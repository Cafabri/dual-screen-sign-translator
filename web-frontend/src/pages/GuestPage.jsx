import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import useSocket from '../hooks/useSocket';

function MicIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}

function StopIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

function SpeakerIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  );
}

function GuestPage() {
  const [searchParams] = useSearchParams();
  const roomId = searchParams.get('room');
  const socket = useSocket();

  const [messages, setMessages]         = useState([]);
  const [isSpeaking, setIsSpeaking]     = useState(false);
  const [isListening, setIsListening]   = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript]     = useState('');
  const [micError, setMicError]         = useState(null);
  const [audioReady, setAudioReady]     = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef        = useRef([]);
  const messagesEndRef   = useRef(null);

  useEffect(() => {
    if (!roomId) return;
    socket.emit('join-room', { roomId, role: 'guest' });
  }, []);

  useEffect(() => {
    socket.on('translation-update', ({ text }) => {
      const timestamp = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      setMessages((prev) => [...prev, { text, timestamp, from: 'host' }]);
      speakText(text);
    });
    socket.on('guest-transcript', ({ text }) => {
      setTranscript(text);
      setIsProcessing(false);
    });
    socket.on('guest-audio-error', ({ message }) => {
      setMicError(message);
      setIsProcessing(false);
    });
    return () => {
      socket.off('translation-update');
      socket.off('guest-transcript');
      socket.off('guest-audio-error');
    };
  }, [socket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const unlockAudio = () => {
    if (audioReady) return;
    // Fire a silent utterance so the browser marks this session as gesture-initiated.
    const silent = new SpeechSynthesisUtterance('');
    window.speechSynthesis.speak(silent);
    setAudioReady(true);
  };

  const speakText = (text) => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 0.95;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend   = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const toggleListening = async () => {
    setMicError(null);

    if (isListening) {
      mediaRecorderRef.current?.stop();
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setMicError('Microphone permission denied. Allow access in your browser settings.');
      return;
    }

    const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm'
      : MediaRecorder.isTypeSupported('audio/mp4')  ? 'audio/mp4'
      : '';

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      setIsListening(false);
      setIsProcessing(true);
      socket.emit('guest-speaking', { active: false });

      const blob   = new Blob(chunksRef.current, { type: recorder.mimeType });
      const buffer = await blob.arrayBuffer();
      socket.emit('guest-audio', buffer, recorder.mimeType);
    };

    recorder.start(250);
    mediaRecorderRef.current = recorder;
    setIsListening(true);
    setTranscript('');
    socket.emit('guest-speaking', { active: true });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col sm:items-center sm:justify-center sm:py-8 sm:px-4" onClick={unlockAudio}>

      {/* ── Inner card — full screen on mobile, centered panel on desktop ── */}
      <div className="flex flex-col w-full sm:max-w-sm sm:rounded-3xl sm:border sm:border-white/[0.07] sm:bg-white/[0.02] sm:backdrop-blur-xl sm:overflow-hidden sm:shadow-2xl sm:shadow-black/60 sm:min-h-0 min-h-screen">

      {/* ── Audio unlock banner ───────────────────────────────────────── */}
      {!audioReady && (
        <div className="shrink-0 flex items-center justify-center gap-2 px-4 py-2 mx-5 mt-10 sm:mt-4 mb-0 rounded-xl border border-amber-500/20 bg-amber-500/[0.06]">
          <span className="text-amber-400 text-[11px]">🔔</span>
          <span className="text-[11px] text-amber-400/80 font-medium">Tap anywhere to enable audio</span>
        </div>
      )}

      {/* ── Header ────────────────────────────────────────────────────── */}
      <header className="shrink-0 flex items-center justify-between px-5 pt-4 sm:pt-6 pb-4">
        <span className="text-[11px] font-semibold tracking-[0.28em] uppercase text-white/25 select-none">
          DualSign · Listener
        </span>

        {/* TTS speaking indicator */}
        {isSpeaking && (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-emerald-500/25 bg-emerald-500/[0.08]">
            <SpeakerIcon className="w-3 h-3 text-emerald-400" />
            <span className="text-[11px] font-medium text-emerald-400/80">Speaking…</span>
          </div>
        )}
      </header>

      {/* ── No room error ─────────────────────────────────────────────── */}
      {!roomId && (
        <div className="flex-1 flex flex-col items-center justify-center px-8 gap-4 text-center">
          <div className="w-14 h-14 rounded-2xl border border-red-500/20 bg-red-500/[0.05] flex items-center justify-center">
            <svg className="w-6 h-6 text-red-400/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-[14px] font-semibold text-white/60">No room found</p>
            <p className="text-[12px] text-white/25">Scan the host's QR code to join a session.</p>
          </div>
        </div>
      )}

      {/* ── Messages ──────────────────────────────────────────────────── */}
      {roomId && (
        <main className="flex-1 overflow-y-auto px-5 py-3 flex flex-col gap-3 sm:max-h-[420px]">
          {messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center py-16">
              <div className="w-12 h-12 rounded-full border border-white/[0.06] bg-white/[0.02] flex items-center justify-center select-none">
                <span className="text-xl">💬</span>
              </div>
              <p className="text-[13px] text-white/20 italic">Waiting for the host to sign…</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className="relative rounded-2xl overflow-hidden border border-white/[0.07] bg-white/[0.025] backdrop-blur-xl px-4 pt-3 pb-4"
              >
                {/* Blue accent top line */}
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-blue-500/40 via-blue-500/15 to-transparent" />
                <span className="text-[10px] text-white/25 tracking-wide">{msg.timestamp}</span>
                <p className="text-[19px] font-semibold text-white/90 leading-snug mt-1">
                  {msg.text}
                </p>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </main>
      )}

      {/* ── Footer: mic ───────────────────────────────────────────────── */}
      {roomId && (
        <footer className="shrink-0 flex flex-col items-center gap-4 px-5 pt-5 pb-14 sm:pb-8 border-t border-white/[0.05]">

          {/* Error message */}
          {micError && (
            <p className="text-[12px] text-red-400/80 text-center max-w-xs leading-relaxed">
              {micError}
            </p>
          )}

          {/* Status hint / transcript */}
          <div className="min-h-[20px] flex items-center justify-center">
            {transcript && (
              <p className="text-[13px] text-white/35 italic text-center max-w-xs">
                "{transcript}"
              </p>
            )}
            {isProcessing && (
              <p className="text-[12px] text-white/25 italic tracking-wide animate-pulse">
                transcribing…
              </p>
            )}
            {isListening && (
              <p className="text-[12px] text-white/25 italic tracking-wide">
                recording…
              </p>
            )}
          </div>

          {/* Mic button */}
          <button
            onClick={toggleListening}
            disabled={isProcessing}
            className={`
              relative w-[72px] h-[72px] rounded-full flex items-center justify-center
              transition-all duration-300 select-none
              ${isProcessing
                ? 'bg-white/10 cursor-not-allowed opacity-50'
                : isListening
                  ? 'bg-red-500 shadow-[0_0_48px_rgba(239,68,68,0.4)] scale-105 cursor-pointer'
                  : 'bg-blue-600 hover:bg-blue-500 shadow-[0_0_40px_rgba(37,99,235,0.35)] hover:shadow-[0_0_56px_rgba(37,99,235,0.5)] hover:scale-105 cursor-pointer'}
            `}
          >
            {isListening && (
              <span className="absolute inset-0 rounded-full border-2 border-red-400/50 animate-ping" />
            )}
            {isListening
              ? <StopIcon className="w-6 h-6 text-white" />
              : <MicIcon  className="w-6 h-6 text-white" />
            }
          </button>

          <span className="text-[11px] text-white/20 tracking-widest uppercase select-none">
            {isProcessing ? 'processing…' : isListening ? 'Tap to stop' : 'Tap to reply'}
          </span>
        </footer>
      )}

      </div>{/* end inner card */}
    </div>
  );
}

export default GuestPage;
