const GESTURES = [
  {
    icon: '✋',
    title: 'Raise Both Hands',
    description: 'Lift both wrists above shoulder level to activate live detection and start signing.',
    dot: 'bg-blue-500',
    border: 'border-blue-500/25',
    glow: 'from-blue-500/20',
    iconColor: 'text-blue-400/70',
  },
  {
    icon: '⬇︎⬆︎',
    title: 'Add Word',
    description: 'Drop hands quickly, then raise them again to lock the current sign into your phrase.',
    dot: 'bg-emerald-400',
    border: 'border-emerald-400/25',
    glow: 'from-emerald-400/20',
    iconColor: 'text-emerald-400/70',
  },
  {
    icon: '⬇︎…',
    title: 'Send Phrase',
    description: 'Hold hands down for 2 seconds to transmit the full phrase to the listener.',
    dot: 'bg-violet-400',
    border: 'border-violet-400/25',
    glow: 'from-violet-400/20',
    iconColor: 'text-violet-400/70',
  },
];

function GestureOnboarding({ visible = true }) {
  if (!visible) return null;

  return (
    <div className="w-full max-w-lg mx-auto">
      <div className="relative rounded-2xl overflow-hidden border border-white/[0.07] bg-white/[0.025] backdrop-blur-2xl shadow-2xl shadow-black/60 p-6">

        {/* Top shimmer line */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="h-px flex-1 bg-white/[0.06]" />
          <span className="text-[10px] font-semibold tracking-[0.25em] uppercase text-white/25 select-none">
            Gesture Guide
          </span>
          <div className="h-px flex-1 bg-white/[0.06]" />
        </div>

        {/* Cards */}
        <div className="flex flex-col gap-2">
          {GESTURES.map((g) => (
            <div
              key={g.title}
              className={`relative rounded-xl border ${g.border} bg-white/[0.02] hover:bg-white/[0.04] transition-colors duration-200 overflow-hidden`}
            >
              {/* Per-card top accent */}
              <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r ${g.glow} to-transparent`} />

              <div className="flex items-center gap-4 px-4 py-3.5">
                {/* Icon box */}
                <div className="shrink-0 w-11 h-11 rounded-xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center text-lg font-mono select-none">
                  <span className={g.iconColor}>{g.icon}</span>
                </div>

                {/* Content */}
                <div className="flex flex-col gap-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${g.dot}`} />
                    <span className="text-[13px] font-semibold text-white/85 tracking-tight leading-none">
                      {g.title}
                    </span>
                  </div>
                  <p className="text-[12px] text-white/35 leading-relaxed pl-[14px]">
                    {g.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <p className="mt-5 text-center text-[11px] text-white/18 tracking-wide select-none">
          Panel hides automatically once detection activates
        </p>
      </div>
    </div>
  );
}

export default GestureOnboarding;
