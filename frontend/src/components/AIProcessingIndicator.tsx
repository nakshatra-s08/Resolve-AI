import React from 'react'
import { Bot, Sparkles } from 'lucide-react'

export interface AIProcessingIndicatorProps {
  variant?: 'inline' | 'card' | 'message' | 'compact'
  label?: string
  sublabel?: string
  className?: string
  tone?: 'teal' | 'yellow' | 'navy'
}

export const TypingDots: React.FC<{ className?: string }> = ({ className = 'bg-[#007185]' }) => (
  <span className="inline-flex items-center gap-1 px-0.5" aria-hidden="true">
    <span className={`w-1.5 h-1.5 rounded-full animate-resolveai-dot-1 ${className}`} />
    <span className={`w-1.5 h-1.5 rounded-full animate-resolveai-dot-2 ${className}`} />
    <span className={`w-1.5 h-1.5 rounded-full animate-resolveai-dot-3 ${className}`} />
  </span>
)

export const OrbitalSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg'; tone?: 'teal' | 'yellow' | 'navy' }> = ({
  size = 'md',
  tone = 'teal',
}) => {
  const sizeClasses = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-8 h-8' : 'w-5 h-5'
  const borderColors =
    tone === 'yellow'
      ? 'border-t-[#FF9900] border-r-[#FFD814]'
      : tone === 'navy'
      ? 'border-t-[#131921] border-r-[#007185]'
      : 'border-t-[#007185] border-r-[#FFD814]'

  const coreDot =
    tone === 'yellow'
      ? 'bg-[#FF9900]/40'
      : tone === 'navy'
      ? 'bg-[#131921]/30'
      : 'bg-[#007185]/30'

  return (
    <div className={`relative ${sizeClasses} shrink-0`} aria-hidden="true">
      {/* Outer subtle track ring */}
      <div className="absolute inset-0 rounded-full border border-black/10 dark:border-white/10" />
      {/* Rotating gradient ring */}
      <div
        className={`absolute inset-0 rounded-full border-2 border-transparent ${borderColors} animate-resolveai-orbit`}
      />
      {/* Inner pulsing core dot */}
      <div className={`absolute inset-1.5 rounded-full ${coreDot} animate-resolveai-pulse`} />
    </div>
  )
}

export const AIProcessingIndicator: React.FC<AIProcessingIndicatorProps> = ({
  variant = 'card',
  label = 'Processing request...',
  sublabel,
  className = '',
  tone = 'teal',
}) => {
  // 1. Inline Variant (Button or table cell)
  if (variant === 'inline') {
    return (
      <span
        role="status"
        aria-live="polite"
        className={`inline-flex items-center gap-1.5 text-xs font-semibold ${className}`}
      >
        <OrbitalSpinner size="sm" tone={tone} />
        {label && <span>{label}</span>}
        <TypingDots
          className={
            tone === 'yellow' ? 'bg-[#131921]' : tone === 'navy' ? 'bg-white' : 'bg-[#007185]'
          }
        />
      </span>
    )
  }

  // 2. Chat Message Variant (Inside chat stream)
  if (variant === 'message') {
    return (
      <div
        role="status"
        aria-live="polite"
        className={`flex justify-start transition-opacity duration-300 ${className}`}
      >
        <div className="max-w-[88%] bg-white rounded-lg rounded-tl-none border border-[#007185]/30 shadow-xs p-3 space-y-2 text-xs">
          <div className="flex items-center gap-2 text-[10px] text-[#565959] border-b border-[#EAEDED] pb-1.5">
            <div className="w-5 h-5 rounded-full bg-[#007185] flex items-center justify-center text-white shrink-0 shadow-xs">
              <Bot className="w-3 h-3" />
            </div>
            <span className="font-bold text-[#007185]">ResolveAI Assistant</span>
            <span className="ml-auto text-[#75777C] flex items-center gap-1">
              <OrbitalSpinner size="sm" tone="teal" />
              <span>Analyzing</span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-[#0F1111] font-medium pt-0.5">
            <span>{label}</span>
            <TypingDots className="bg-[#007185]" />
          </div>

          {sublabel && (
            <p className="text-[11px] text-[#565959] leading-relaxed italic bg-[#F0F8FA] p-2 rounded border border-[#A0D3DC]/40">
              {sublabel}
            </p>
          )}
        </div>
      </div>
    )
  }

  // 3. Compact Bar Variant
  if (variant === 'compact') {
    return (
      <div
        role="status"
        aria-live="polite"
        className={`flex items-center justify-between gap-2 px-3 py-2 bg-[#F0F8FA] border border-[#007185]/30 rounded text-xs text-[#0F1111] ${className}`}
      >
        <div className="flex items-center gap-2">
          <OrbitalSpinner size="sm" tone={tone} />
          <span className="font-semibold">{label}</span>
          <TypingDots className="bg-[#007185]" />
        </div>
        {sublabel && <span className="text-[11px] text-[#565959] truncate max-w-xs">{sublabel}</span>}
      </div>
    )
  }

  // 4. Default: Card / Panel Variant
  return (
    <div
      role="status"
      aria-live="polite"
      className={`bg-[#F0F8FA] border border-[#007185]/40 rounded-lg p-4 shadow-xs space-y-2.5 transition-all duration-300 ${className}`}
    >
      <div className="flex items-center justify-between border-b border-[#A0D3DC]/50 pb-2">
        <div className="flex items-center gap-2.5">
          <OrbitalSpinner size="md" tone={tone} />
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-xs text-[#007185] font-['Hanken_Grotesk']">
              {label}
            </span>
            <TypingDots className="bg-[#007185]" />
          </div>
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase bg-[#FFD814]/25 text-[#0F1111] px-2 py-0.5 rounded border border-[#FFD814]">
          <Sparkles className="w-3 h-3 text-[#0F1111]" />
          <span>Active Agent Task</span>
        </span>
      </div>

      {sublabel ? (
        <p className="text-xs text-[#565959] leading-relaxed pl-7">{sublabel}</p>
      ) : (
        <p className="text-xs text-[#565959] leading-relaxed pl-7">
          Synthesizing case context, evidence attachments, and relevant policy references...
        </p>
      )}
    </div>
  )
}
