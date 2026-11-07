import React from 'react'
import { Bot, Sparkles } from 'lucide-react'

export interface AIProcessingIndicatorProps {
  variant?: 'inline' | 'card' | 'message' | 'compact'
  label?: string
  sublabel?: string
  className?: string
  tone?: 'indigo' | 'coral' | 'plum' | 'teal' | 'yellow' | 'navy'
}

export const TypingDots: React.FC<{ className?: string }> = ({ className = 'bg-[#312E81]' }) => (
  <span className="inline-flex items-center gap-1 px-0.5" aria-hidden="true">
    <span className={`w-1.5 h-1.5 rounded-full animate-resolveai-dot-1 ${className}`} />
    <span className={`w-1.5 h-1.5 rounded-full animate-resolveai-dot-2 ${className}`} />
    <span className={`w-1.5 h-1.5 rounded-full animate-resolveai-dot-3 ${className}`} />
  </span>
)

export const OrbitalSpinner: React.FC<{
  size?: 'sm' | 'md' | 'lg'
  tone?: 'indigo' | 'coral' | 'plum' | 'teal' | 'yellow' | 'navy'
}> = ({ size = 'md', tone = 'indigo' }) => {
  const sizeClasses = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-8 h-8' : 'w-5 h-5'

  let borderColors = 'border-t-[#312E81] border-r-[#5B4B8A]'
  let coreDot = 'bg-[#312E81]/30'

  if (tone === 'coral' || tone === 'yellow') {
    borderColors = 'border-t-[#D97757] border-r-[#B85F44]'
    coreDot = 'bg-[#D97757]/40'
  } else if (tone === 'plum') {
    borderColors = 'border-t-[#5B4B8A] border-r-[#8B7BC4]'
    coreDot = 'bg-[#5B4B8A]/30'
  }

  return (
    <div className={`relative ${sizeClasses} shrink-0`} aria-hidden="true">
      <div className="absolute inset-0 rounded-full border border-black/10" />
      <div
        className={`absolute inset-0 rounded-full border-2 border-transparent ${borderColors} animate-resolveai-orbit`}
      />
      <div className={`absolute inset-1.5 rounded-full ${coreDot} animate-resolveai-pulse`} />
    </div>
  )
}

export const AIProcessingIndicator: React.FC<AIProcessingIndicatorProps> = ({
  variant = 'card',
  label = 'Processing request...',
  sublabel,
  className = '',
  tone = 'indigo',
}) => {
  // 1. Inline Variant
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
            tone === 'coral' || tone === 'yellow' ? 'bg-[#D97757]' : 'bg-[#312E81]'
          }
        />
      </span>
    )
  }

  // 2. Chat Message Variant
  if (variant === 'message') {
    return (
      <div
        role="status"
        aria-live="polite"
        className={`flex justify-start transition-opacity duration-300 ${className}`}
      >
        <div className="max-w-[88%] bg-white rounded-xl rounded-tl-none border border-[#8B7BC4]/30 shadow-xs p-3 space-y-2 text-xs">
          <div className="flex items-center gap-2 text-[10px] text-[#625F70] border-b border-[#E4E1E8] pb-1.5">
            <div className="w-5 h-5 rounded-full bg-[#312E81] flex items-center justify-center text-white shrink-0 shadow-xs">
              <Bot className="w-3 h-3" />
            </div>
            <span className="font-bold text-[#312E81]">ResolveAI Assistant</span>
            <span className="ml-auto text-[#8E8B99] flex items-center gap-1">
              <OrbitalSpinner size="sm" tone="indigo" />
              <span>Analyzing</span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-[#27243A] font-medium pt-0.5">
            <span>{label}</span>
            <TypingDots className="bg-[#312E81]" />
          </div>

          {sublabel && (
            <p className="text-[11px] text-[#625F70] leading-relaxed italic bg-[#F0EEFA] p-2 rounded-md border border-[#E4E1E8]">
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
        className={`flex items-center justify-between gap-2 px-3 py-2 bg-[#F0EEFA] border border-[#8B7BC4]/30 rounded-lg text-xs text-[#27243A] ${className}`}
      >
        <div className="flex items-center gap-2">
          <OrbitalSpinner size="sm" tone={tone} />
          <span className="font-semibold">{label}</span>
          <TypingDots className="bg-[#312E81]" />
        </div>
        {sublabel && <span className="text-[11px] text-[#625F70] truncate max-w-xs">{sublabel}</span>}
      </div>
    )
  }

  // 4. Default: Card / Panel Variant
  return (
    <div
      role="status"
      aria-live="polite"
      className={`bg-[#F0EEFA] border border-[#8B7BC4]/30 rounded-xl p-4 shadow-xs space-y-2.5 transition-all duration-300 ${className}`}
    >
      <div className="flex items-center justify-between border-b border-[#E4E1E8] pb-2">
        <div className="flex items-center gap-2.5">
          <OrbitalSpinner size="md" tone={tone} />
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-xs text-[#312E81] font-['Hanken_Grotesk']">
              {label}
            </span>
            <TypingDots className="bg-[#312E81]" />
          </div>
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase bg-white text-[#312E81] px-2 py-0.5 rounded-full border border-[#8B7BC4]/30">
          <Sparkles className="w-3 h-3 text-[#D97757]" />
          <span>Active Analysis</span>
        </span>
      </div>

      {sublabel ? (
        <p className="text-xs text-[#625F70] leading-relaxed pl-7">{sublabel}</p>
      ) : (
        <p className="text-xs text-[#625F70] leading-relaxed pl-7">
          Synthesizing case context, evidence attachments, and relevant consumer standards...
        </p>
      )}
    </div>
  )
}
