import React, { useState } from 'react'
import {
  Clock,
  Plus,
  MessageSquare,
  AlertCircle,
  FileText,
  Send,
  CheckCircle,
} from 'lucide-react'
import type { CaseEvent } from '../api/types'

interface TimelineProps {
  events: CaseEvent[]
  onAddUserNote: (note: string) => Promise<void>
}

export const Timeline: React.FC<TimelineProps> = ({ events, onAddUserNote }) => {
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!note.trim()) return

    setSubmitting(true)
    setError(null)
    try {
      await onAddUserNote(note.trim())
      setNote('')
    } catch (err: any) {
      setError(err.message || 'Failed to add note')
    } finally {
      setSubmitting(false)
    }
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'CASE_CREATED':
        return <Plus className="w-3.5 h-3.5 text-white" />
      case 'EVIDENCE_UPLOADED':
        return <FileText className="w-3.5 h-3.5 text-white" />
      case 'ACTION_PROPOSED':
      case 'ACTION_APPROVED':
        return <CheckCircle className="w-3.5 h-3.5 text-white" />
      case 'ACTION_EXECUTED':
        return <Send className="w-3.5 h-3.5 text-white" />
      case 'PROVIDER_RESPONSE_RECEIVED':
      case 'PROVIDER_RESPONSE_PROCESSED':
        return <MessageSquare className="w-3.5 h-3.5 text-white" />
      case 'USER_NOTE':
        return <Clock className="w-3.5 h-3.5 text-white" />
      default:
        return <AlertCircle className="w-3.5 h-3.5 text-white" />
    }
  }

  const getEventBadgeColor = (type: string) => {
    switch (type) {
      case 'ACTION_EXECUTED':
      case 'PROVIDER_RESPONSE_PROCESSED':
        return 'bg-[#067D62]'
      case 'PROVIDER_RESPONSE_RECEIVED':
      case 'ACTION_PROPOSED':
        return 'bg-[#007185]'
      case 'CASE_CREATED':
      case 'EVIDENCE_UPLOADED':
        return 'bg-[#232F3E]'
      case 'USER_NOTE':
      default:
        return 'bg-[#75777C]'
    }
  }

  return (
    <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-5">
      <div className="flex items-center justify-between pb-3 border-b border-[#EAEDED]">
        <div>
          <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111] flex items-center gap-2">
            <Clock className="w-5 h-5 text-[#007185]" />
            <span>Chronological Case Trajectory & Audit Trail</span>
          </h2>
          <p className="text-xs text-[#565959]">
            Full append-only audit trail recorded for this dispute
          </p>
        </div>
        <span className="text-xs font-semibold text-[#565959]">
          {events.length} Recorded Events
        </span>
      </div>

      {/* Vertical Stepper */}
      <div className="relative pl-6 space-y-4 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-[#D5D9D9]">
        {events.map((ev) => (
          <div key={ev.id} className="relative flex items-start gap-3">
            <span
              className={`absolute -left-6 top-1 h-5 w-5 rounded-full ${getEventBadgeColor(
                ev.event_type
              )} ring-4 ring-white flex items-center justify-center`}
            >
              {getEventIcon(ev.event_type)}
            </span>
            <div className="flex-1 bg-[#F3F3F3] p-3 rounded border border-[#D5D9D9]">
              <div className="flex items-center justify-between flex-wrap gap-1">
                <span className="text-xs font-bold text-[#0F1111]">
                  {ev.event_type.replace(/_/g, ' ')}
                </span>
                <span className="text-[11px] text-[#565959]">
                  {new Date(ev.created_at).toLocaleString()}
                </span>
              </div>
              <p className="text-xs text-[#0F1111] mt-1 whitespace-pre-wrap leading-relaxed">
                {ev.description}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Add User Note Box */}
      <form onSubmit={handleAddNote} className="pt-3 border-t border-[#EAEDED] space-y-2">
        <label className="block text-xs font-bold text-[#0F1111]">
          Add User Note or Incident Update
        </label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="e.g. Technician called and confirmed fault code PWR-09..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="flex-1 h-9 px-3 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185] focus:ring-2 focus:ring-[#007185]/20"
          />
          <button
            type="submit"
            disabled={!note.trim() || submitting}
            className="h-9 px-4 bg-white hover:bg-[#F3F3F3] text-[#0F1111] font-bold text-xs rounded border border-[#D5D9D9] shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 shrink-0"
          >
            <Plus className="w-4 h-4 text-[#007185]" />
            <span>Add Note</span>
          </button>
        </div>
        {error && <p className="text-xs text-[#B12704]">{error}</p>}
      </form>
    </div>
  )
}
