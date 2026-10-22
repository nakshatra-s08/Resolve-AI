import React from 'react'
import type { CaseStatus } from '../api/types'

interface StatusBadgeProps {
  status: CaseStatus | string
  size?: 'sm' | 'md'
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toUpperCase()

  let bg = 'bg-[#F3F8F8]'
  let text = 'text-[#007185]'
  let border = 'border-[#98D0D9]'
  let dot = 'bg-[#007185]'

  switch (normalized) {
    case 'ACTION_REQUIRED':
    case 'PENDING_APPROVAL':
    case 'FAILED':
      bg = 'bg-[#FCF4F2]'
      text = 'text-[#B12704]'
      border = 'border-[#F2BEB1]'
      dot = 'bg-[#B12704]'
      break
    case 'RESOLVED':
    case 'EXECUTED':
    case 'APPROVED':
      bg = 'bg-[#F0F8F4]'
      text = 'text-[#067D62]'
      border = 'border-[#9FD3BC]'
      dot = 'bg-[#067D62]'
      break
    case 'AWAITING_PROVIDER_RESPONSE':
    case 'ESCALATED':
      bg = 'bg-[#FFF8E7]'
      text = 'text-[#C45500]'
      border = 'border-[#FCD200]'
      dot = 'bg-[#C45500]'
      break
    case 'CLOSED':
    case 'REJECTED':
    case 'CANCELLED':
      bg = 'bg-[#F3F3F3]'
      text = 'text-[#565959]'
      border = 'border-[#D5D9D9]'
      dot = 'bg-[#75777C]'
      break
    case 'IN_PROGRESS':
    case 'DRAFT':
    default:
      bg = 'bg-[#F3F8F8]'
      text = 'text-[#007185]'
      border = 'border-[#98D0D9]'
      dot = 'bg-[#007185]'
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
