import React, { useState } from 'react'
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  Clock,
  Trash2,
  AlertTriangle,
  FileCheck,
} from 'lucide-react'
import type { Evidence, EvidenceChecklistResponse, EvidenceType } from '../api/types'
import { AIProcessingIndicator } from './AIProcessingIndicator'

interface EvidenceManagerProps {
  evidenceList: Evidence[]
  checklist: EvidenceChecklistResponse | null
  onUpload: (file: File, docType?: EvidenceType) => Promise<void>
  onDelete: (evidenceId: string) => Promise<void>
}

const CATEGORY_LABELS: Record<EvidenceType, string> = {
  INVOICE: 'Purchase Invoice / Receipt',
  WARRANTY: 'Warranty Certificate / Policy',
  REPAIR_RECEIPT: 'Repair Job Sheet / Service Receipt',
  SERVICE_COMMUNICATION: 'Service Email / Written Notice',
  OTHER: 'Other Supporting Document',
}

export const EvidenceManager: React.FC<EvidenceManagerProps> = ({
  evidenceList,
  checklist,
  onUpload,
  onDelete,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedDocType, setSelectedDocType] = useState<EvidenceType>('INVOICE')
  const [uploading, setUploading] = useState(false)
  const [uploadingFileName, setUploadingFileName] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
      setUploadError(null)
    }
  }

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile || uploading) {
      if (!selectedFile) setUploadError('Please select a file to upload')
      return
    }

    const fileToUpload = selectedFile
    setUploadingFileName(fileToUpload.name)
    setUploading(true)
    setUploadError(null)
    try {
      await onUpload(fileToUpload, selectedDocType)
      setSelectedFile(null)
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
      setUploadingFileName(null)
    }
  }

  const handleDeleteClick = async (evidenceId: string) => {
    if (deletingId) return
    setDeletingId(evidenceId)
    try {
      await onDelete(evidenceId)
    } finally {
      setDeletingId(null)
    }
  }

  const represented = checklist?.represented_categories || []
  const missing = checklist?.missing_categories || []
  const total = represented.length + missing.length
  const percentComplete = total > 0 ? Math.round((represented.length / total) * 100) : 0

  return (
    <div className="bg-white rounded-xl p-5 shadow-xs border border-[#E4E1E8] space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#E4E1E8] gap-2">
        <div>
          <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#27243A] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#5B4B8A]" />
            <span>Evidence Repository & Document Checklist</span>
          </h2>
          <p className="text-xs text-[#625F70]">
            Supported formats: PDF (text extraction), PNG, JPEG (up to 10MB)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-[#3E7C68] bg-[#EAF3EF] border border-[#3E7C68]/30 px-2.5 py-1 rounded-full">
            {represented.length} of {total} Categories Represented ({percentComplete}%)
          </span>
        </div>
      </div>

      {/* Checklist Grid */}
      {checklist && (
        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-[#625F70] block">
            Baseline Evidence Coverage
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {represented.map((cat) => (
              <div
                key={cat}
                className="p-3 rounded-lg border bg-[#EAF3EF] border-[#3E7C68]/30 flex items-start gap-3"
              >
                <CheckCircle2 className="w-5 h-5 text-[#3E7C68] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <p className="text-xs font-bold text-[#3E7C68] truncate">
                      {CATEGORY_LABELS[cat] || cat}
                    </p>
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase bg-white text-[#3E7C68]">
                      Attached
                    </span>
                  </div>
                  <p className="text-xs text-[#625F70] mt-0.5">
                    Document present in case record
                  </p>
                </div>
              </div>
            ))}

            {missing.map((cat) => (
              <div
                key={cat}
                className="p-3 rounded-lg border bg-[#F9ECEB] border-[#B94A48]/30 flex items-start gap-3"
              >
                <Clock className="w-5 h-5 text-[#B94A48] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <p className="text-xs font-bold text-[#B94A48] truncate">
                      {CATEGORY_LABELS[cat] || cat}
                    </p>
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase bg-white text-[#B94A48]">
                      Missing
                    </span>
                  </div>
                  <p className="text-xs text-[#625F70] mt-0.5">
                    Recommended for dispute substantiation
                  </p>
                </div>
              </div>
            ))}
          </div>

          {checklist.explanation && (
            <p className="text-[11px] text-[#625F70] italic pt-1">
              Note: {checklist.explanation}
            </p>
          )}
        </div>
      )}

      {/* Uploading In-Flight Indicator */}
      {uploading && (
        <AIProcessingIndicator
          variant="card"
          label="Extracting & Processing Document Evidence"
          sublabel={`Analyzing "${uploadingFileName || 'document'}" — extracting text, classifying its category, and updating evidence coverage...`}
          tone="indigo"
        />
      )}

      {/* Upload Box */}
      <form
        onSubmit={handleUploadSubmit}
        className="bg-[#F7F6F3] border border-dashed border-[#8B7BC4] rounded-xl p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3"
      >
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-1">
          <label className={`h-9 px-3.5 bg-white border border-[#E4E1E8] hover:bg-[#F0EEFA] text-xs font-semibold text-[#27243A] rounded-lg flex items-center justify-center gap-1.5 cursor-pointer shadow-xs shrink-0 transition-colors ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
            <UploadCloud className="w-4 h-4 text-[#312E81]" />
            <span>{selectedFile ? 'Change File' : 'Choose Document'}</span>
            <input
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.png,.jpg,.jpeg"
              disabled={uploading}
              className="hidden"
            />
          </label>

          {selectedFile ? (
            <span className="text-xs text-[#27243A] font-semibold truncate max-w-xs">
              {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
            </span>
          ) : (
            <span className="text-xs text-[#625F70]">No file selected</span>
          )}

          <select
            value={selectedDocType}
            onChange={(e) => setSelectedDocType(e.target.value as EvidenceType)}
            disabled={uploading}
            className="h-9 px-2 bg-white border border-[#E4E1E8] rounded-lg text-xs text-[#27243A] focus:outline-none focus:border-[#5B4B8A] disabled:opacity-50"
          >
            <option value="INVOICE">Purchase Receipt / Invoice</option>
            <option value="REPAIR_RECEIPT">Repair Sheet / Service Job Report</option>
            <option value="WARRANTY">Warranty Certificate / Terms</option>
            <option value="SERVICE_COMMUNICATION">Service Communication / Email</option>
            <option value="OTHER">Other Documentation</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={!selectedFile || uploading}
          className="h-9 px-4 bg-[#312E81] hover:bg-[#262366] text-white font-bold text-xs rounded-lg shadow-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 shrink-0 cursor-pointer"
        >
          {uploading ? (
            <AIProcessingIndicator variant="inline" label="Processing" tone="indigo" />
          ) : (
            <span>Upload & Process</span>
          )}
        </button>
      </form>

      {uploadError && (
        <div className="text-xs text-[#B94A48] flex items-center gap-1 bg-[#F9ECEB] p-2.5 rounded-lg border border-[#B94A48]/30">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Uploaded Files Table */}
      {evidenceList.length > 0 ? (
        <div className="border border-[#E4E1E8] rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F7F6F3] text-[#625F70] border-b border-[#E4E1E8] font-bold">
                <th className="py-2.5 px-3">File Name</th>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3">Extraction Status</th>
                <th className="py-2.5 px-3">Uploaded</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E1E8]">
              {evidenceList.map((doc) => (
                <tr key={doc.id} className="hover:bg-[#F0EEFA]/40 transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-[#27243A] max-w-[200px] truncate">
                    <div className="flex items-center gap-1.5">
                      <FileCheck className="w-4 h-4 text-[#3E7C68] shrink-0" />
                      <span className="truncate" title={doc.original_filename}>
                        {doc.original_filename}
                      </span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-[#625F70]">
                    <span className="bg-[#F0EEFA] px-2 py-0.5 rounded-full text-[11px] font-semibold text-[#312E81]">
                      {CATEGORY_LABELS[doc.evidence_type] || doc.evidence_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        doc.extraction_status === 'COMPLETED'
                          ? 'bg-[#EAF3EF] text-[#3E7C68]'
                          : doc.extraction_status === 'UNSUPPORTED' || doc.extraction_status === 'NO_TEXT_FOUND'
                          ? 'bg-[#F7F6F3] text-[#625F70]'
                          : 'bg-[#F9ECEB] text-[#B94A48]'
                      }`}
                    >
                      {doc.extraction_status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-[#625F70]">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => handleDeleteClick(doc.id)}
                      disabled={deletingId === doc.id || uploading}
                      className="p-1 text-[#8E8B99] hover:text-[#B94A48] rounded transition-colors disabled:opacity-50 cursor-pointer"
                      title="Delete evidence document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-6 text-xs text-[#625F70]">
          No evidence uploaded yet. Add purchase invoices or repair job sheets to substantiate the dispute.
        </div>
      )}
    </div>
  )
}
