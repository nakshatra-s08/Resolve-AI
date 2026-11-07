import React, { useState } from 'react'
import { X, AlertCircle } from 'lucide-react'
import type { CaseCreatePayload } from '../api/types'
import { VoiceIntakeRecorder } from './VoiceIntakeRecorder'

interface CreateCaseModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CaseCreatePayload) => Promise<void>
}

export const CreateCaseModal: React.FC<CreateCaseModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [formData, setFormData] = useState<CaseCreatePayload>({
    title: '',
    product_name: '',
    issue_description: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.product_name.trim() || !formData.issue_description.trim()) {
      setError('Please fill out all required fields marked with *')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await onSubmit({
        title: formData.title.trim(),
        product_name: formData.product_name.trim(),
        issue_description: formData.issue_description.trim(),
      })
      onClose()
      setFormData({ title: '', product_name: '', issue_description: '' })
    } catch (err: any) {
      setError(err.message || 'Failed to create case')
    } finally {
      setLoading(false)
    }
  }

  const handleTranscriptConfirmed = (transcript: string) => {
    setFormData((prev) => ({
      ...prev,
      issue_description: prev.issue_description.trim()
        ? `${prev.issue_description.trim()}\n\n${transcript}`
        : transcript,
    }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#27243A]/60 p-4 backdrop-blur-xs overflow-y-auto">
      <div className="bg-[#FFFFFF] rounded-xl shadow-2xl border border-[#E4E1E8] w-full max-w-xl overflow-hidden my-8">
        {/* Header */}
        <div className="bg-[#312E81] text-white px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold font-['Hanken_Grotesk'] text-white">
              Start a New Repair & Resolution Case
            </h2>
            <p className="text-xs text-[#F0EEFA]">
              Track repeat product failures, organize evidence, and coordinate warranty resolutions.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[#F0EEFA] hover:text-white p-1.5 rounded-lg hover:bg-[#5B4B8A] transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-[#F9ECEB] border border-[#B94A48]/30 rounded-lg p-3 text-xs text-[#B94A48] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#27243A] mb-1">
                Case Title *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Repeated laptop thermal shutdown failure"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full h-9 px-3 border border-[#E4E1E8] rounded-md text-sm text-[#27243A] bg-[#FFFFFF] focus:outline-none focus:border-[#5B4B8A] focus:ring-2 focus:ring-[#8B7BC4]/30"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#27243A] mb-1">
                Product Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Dell XPS 15 9520"
                value={formData.product_name}
                onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
                className="w-full h-9 px-3 border border-[#E4E1E8] rounded-md text-sm text-[#27243A] bg-[#FFFFFF] focus:outline-none focus:border-[#5B4B8A] focus:ring-2 focus:ring-[#8B7BC4]/30"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-[#27243A]">
                  Issue Description *
                </label>
                <VoiceIntakeRecorder
                  onConfirmTranscript={handleTranscriptConfirmed}
                  disabled={loading}
                />
              </div>

              <textarea
                required
                rows={4}
                placeholder="Describe the defect, previous repair attempts (e.g. 2 motherboard replacements), or click 'Record Voice' above to dictate with speech recognition..."
                value={formData.issue_description}
                onChange={(e) => setFormData({ ...formData, issue_description: e.target.value })}
                className="w-full p-2.5 border border-[#E4E1E8] rounded-md text-sm text-[#27243A] bg-[#FFFFFF] focus:outline-none focus:border-[#5B4B8A] focus:ring-2 focus:ring-[#8B7BC4]/30"
              />
              <p className="text-[11px] text-[#625F70]">
                Tip: You can speak naturally using the mic button, or type manually above.
              </p>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-[#E4E1E8] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="h-9 px-4 bg-[#FFFFFF] border border-[#E4E1E8] hover:bg-[#F7F6F3] text-[#27243A] text-xs font-semibold rounded-md transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="h-9 px-5 bg-[#D97757] hover:bg-[#B85F44] text-white font-bold text-xs rounded-md shadow-xs flex items-center gap-2 transition-colors disabled:opacity-50 cursor-pointer"
            >
              {loading ? 'Creating Case...' : 'Create Case'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
