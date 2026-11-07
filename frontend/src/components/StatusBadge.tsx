import React from 'react'
import type { CaseStatus } from '../api/types'

interface StatusBadgeProps {
  status: CaseStatus | string
  size?: 'sm' | 'md'
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toUpperCase()

  let bg = 'bg-[#F0EEFA]'
  let text = 'text-[#312E81]'
  let border = 'border-[#8B7BC4]/30'
  let dot = 'bg-[#312E81]'

  switch (normalized) {
    case 'FAILED':
    case 'REJECTED':
      bg = 'bg-[#F9ECEB]'
      text = 'text-[#B94A48]'
      border = 'border-[#B94A48]/30'
      dot = 'bg-[#B94A48]'
      break
    case 'RESOLVED':
    case 'EXECUTED':
    case 'APPROVED':
      bg = 'bg-[#EAF3EF]'
      text = 'text-[#3E7C68]'
      border = 'border-[#3E7C68]/30'
      dot = 'bg-[#3E7C68]'
      break
    case 'PENDING_APPROVAL':
    case 'ACTION_READY':
    case 'FOLLOW_UP_DUE':
    case 'AWAITING_RESPONSE':
    case 'AWAITING_PROVIDER_RESPONSE':
    case 'ESCALATED':
      bg = 'bg-[#FBF4E8]'
      text = 'text-[#A06C18]'
      border = 'border-[#E7B76A]/40'
      dot = 'bg-[#E7B76A]'
      break
    case 'CLOSED':
    case 'CANCELLED':
    case 'DRAFT':
      bg = 'bg-[#F7F6F3]'
      text = 'text-[#625F70]'
      border = 'border-[#E4E1E8]'
      dot = 'bg-[#8E8B99]'
      break
    case 'NEW':
    case 'COLLECTING_EVIDENCE':
    case 'UNDER_REVIEW':
    case 'IN_PROGRESS':
    default:
      bg = 'bg-[#F0EEFA]'
      text = 'text-[#312E81]'
      border = 'border-[#8B7BC4]/30'
      dot = 'bg-[#312E81]'
      break
  }

  const label = normalized.replace(/_/g, ' ')
  const isSm = size === 'sm'

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-full border ${bg} ${text} ${border} ${
        isSm ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      <span>{label}</span>
    </span>
  )
}
