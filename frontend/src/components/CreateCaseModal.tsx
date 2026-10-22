import React, { useState } from 'react'
import { X, AlertCircle } from 'lucide-react'
import type { CaseCreatePayload } from '../api/types'

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#131921]/70 p-4 backdrop-blur-xs overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl border border-[#D5D9D9] w-full max-w-xl overflow-hidden my-8">
        {/* Header */}
        <div className="bg-[#232F3E] text-white px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold font-['Hanken_Grotesk'] text-white">
              Start a New Repair & Resolution Case
            </h2>
            <p className="text-xs text-[#8A97A9]">
              ResolveAI tracks repair history, organizes evidence, and surfaces relevant guidance for review.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[#8A97A9] hover:text-white p-1 rounded hover:bg-[#131921]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-[#FCF4F2] border border-[#F2BEB1] rounded p-3 text-xs text-[#B12704] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#0F1111] mb-1">
                Case Title *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Repeated laptop thermal shutdown failure"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full h-9 px-3 border border-[#888C8C] rounded text-sm text-[#0F1111] focus:outline-none focus:border-[#007185] focus:ring-2 focus:ring-[#007185]/20"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#0F1111] mb-1">
                Product Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Dell XPS 15 9520"
                value={formData.product_name}
                onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
                className="w-full h-9 px-3 border border-[#888C8C] rounded text-sm text-[#0F1111] focus:outline-none focus:border-[#007185] focus:ring-2 focus:ring-[#007185]/20"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#0F1111] mb-1">
                Issue Description *
              </label>
              <textarea
                required
                rows={4}
                placeholder="Describe the failure, prior repair history (e.g. 2 motherboard replacements), and the recurring defect..."
                value={formData.issue_description}
                onChange={(e) => setFormData({ ...formData, issue_description: e.target.value })}
                className="w-full p-2.5 border border-[#888C8C] rounded text-sm text-[#0F1111] focus:outline-none focus:border-[#007185] focus:ring-2 focus:ring-[#007185]/20"
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-[#D5D9D9] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="h-9 px-4 bg-white border border-[#D5D9D9] hover:bg-[#F3F3F3] text-[#0F1111] text-xs font-semibold rounded transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="h-9 px-5 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating Case...' : 'Create Case'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
