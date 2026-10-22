import React, { useState } from 'react'
import {
  Send,
  Calendar,
  CheckCircle,
  XCircle,
  Play,
  AlertTriangle,
  Plus,
} from 'lucide-react'
import type { Action, ActionType } from '../api/types'
import { StatusBadge } from './StatusBadge'
import { AIProcessingIndicator } from './AIProcessingIndicator'

interface ActionManagerProps {
  actions: Action[]
  onApprove: (actionId: string) => Promise<void>
  onReject: (actionId: string, reason?: string) => Promise<void>
  onExecute: (actionId: string) => Promise<void>
  onCreateAction: (
    title: string,
    description: string,
    actionType: ActionType,
    payload: Record<string, any>
  ) => Promise<void>
}

export const ActionManager: React.FC<ActionManagerProps> = ({
  actions,
  onApprove,
  onReject,
  onExecute,
  onCreateAction,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('Escalation notice exercising warranty and consumer grievance escalation following repeat repair failures.')
  const [newType, setNewType] = useState<ActionType>('SEND_MESSAGE')
  const [recipient, setRecipient] = useState('Official Service Center')
  const [subject, setSubject] = useState('Formal Notice: Hardware Defect Escalation')
  const [bodyText, setBodyText] = useState(
    'Following repeat unsuccessful repair attempts, the reported defect has recurred. Under applicable warranty terms and consumer guidance, I request an expedited supervisor review, replacement, or appropriate commercial resolution.'
  )
  const [followUpDays, setFollowUpDays] = useState(5)
  const [actionInProgress, setActionInProgress] = useState<string | null>(null)
  const [actionOperation, setActionOperation] = useState<'approve' | 'reject' | 'execute' | null>(null)
  const [creatingAction, setCreatingAction] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim() || !newDescription.trim() || creatingAction) return

    setCreatingAction(true)
    setError(null)
    try {
      let payload: Record<string, any> = {}
      if (newType === 'SEND_MESSAGE') {
        payload = {
          recipient,
          subject,
          message_body: bodyText,
          is_simulated: true,
        }
      } else {
        const dueDate = new Date()
        dueDate.setDate(dueDate.getDate() + followUpDays)
        payload = {
          due_at: dueDate.toISOString(),
          purpose: newDescription,
        }
      }

      await onCreateAction(newTitle.trim(), newDescription.trim(), newType, payload)
      setShowCreateModal(false)
      setNewTitle('')
    } catch (err: any) {
      setError(err.message || 'Failed to create action')
    } finally {
      setCreatingAction(false)
    }
  }

  const handleApproveClick = async (actionId: string) => {
    if (actionInProgress) return
    setActionInProgress(actionId)
    setActionOperation('approve')
    setError(null)
    try {
      await onApprove(actionId)
    } catch (err: any) {
      setError(err.message || 'Approval failed')
    } finally {
      setActionInProgress(null)
      setActionOperation(null)
    }
  }

  const handleRejectClick = async (actionId: string) => {
    if (actionInProgress) return
    setActionInProgress(actionId)
    setActionOperation('reject')
    setError(null)
    try {
      await onReject(actionId, 'User requested revision of drafted parameters.')
    } catch (err: any) {
      setError(err.message || 'Rejection failed')
    } finally {
      setActionInProgress(null)
      setActionOperation(null)
    }
  }

  const handleExecuteClick = async (actionId: string) => {
    if (actionInProgress) return
    setActionInProgress(actionId)
    setActionOperation('execute')
    setError(null)
    try {
      await onExecute(actionId)
    } catch (err: any) {
      setError(err.message || 'Execution failed')
    } finally {
      setActionInProgress(null)
      setActionOperation(null)
    }
  }

  return (
    <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#EAEDED] gap-2">
        <div>
          <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111] flex items-center gap-2">
            <Send className="w-5 h-5 text-[#007185]" />
            <span>Agent Actions & Controlled Approval Workflow</span>
          </h2>
          <p className="text-xs text-[#565959]">
            Explicit approval required. Execution occurs strictly in a simulated environment.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="h-8 px-3 bg-white hover:bg-[#F3F3F3] text-[#0F1111] font-bold text-xs rounded border border-[#D5D9D9] shadow-xs flex items-center gap-1.5 transition-colors shrink-0"
        >
          <Plus className="w-4 h-4 text-[#007185]" />
          <span>Draft New Action</span>
        </button>
      </div>

      {error && (
        <div className="bg-[#FCF4F2] border border-[#F2BEB1] rounded p-2.5 text-xs text-[#B12704] flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Actions List */}
      {actions.length > 0 ? (
        <div className="space-y-3">
          {actions.map((act) => {
            const isPending = act.status === 'PENDING_APPROVAL' || act.status === 'DRAFT'
            const isApproved = act.status === 'APPROVED'
            const isExecuted = act.status === 'EXECUTED'
            const isProcessing = actionInProgress === act.id

            return (
              <div
                key={act.id}
                className="p-4 rounded-lg border border-[#D5D9D9] bg-[#F9F9F9] space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {act.action_type === 'SEND_MESSAGE' ? (
                      <Send className="w-4 h-4 text-[#007185]" />
                    ) : (
                      <Calendar className="w-4 h-4 text-[#C45500]" />
                    )}
                    <h4 className="text-xs font-bold text-[#0F1111]">{act.title}</h4>
                    <span className="text-[10px] text-[#565959] uppercase font-bold bg-[#EAEDED] px-1.5 py-0.2 rounded">
                      {act.action_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <StatusBadge status={act.status} size="sm" />
                </div>

                <p className="text-xs text-[#565959]">{act.description}</p>

                {/* Payload Preview */}
                <div className="bg-white p-3 rounded border border-[#D5D9D9] text-xs space-y-1">
                  {act.payload_json?.recipient && (
                    <p className="text-[#565959]">
                      <strong className="text-[#0F1111]">Recipient:</strong> {act.payload_json.recipient}
                    </p>
                  )}
                  {act.payload_json?.subject && (
                    <p className="text-[#565959]">
                      <strong className="text-[#0F1111]">Subject:</strong> {act.payload_json.subject}
                    </p>
                  )}
                  {act.payload_json?.message_body && (
                    <div className="mt-1 pt-1 border-t border-[#EAEDED] text-[#0F1111] whitespace-pre-wrap leading-relaxed font-sans text-xs">
                      {act.payload_json.message_body}
                    </div>
                  )}
                  {act.payload_json?.due_at && (
                    <p className="text-[#565959]">
                      <strong className="text-[#0F1111]">Due At:</strong> {new Date(act.payload_json.due_at).toLocaleString()}
                    </p>
                  )}
                  {act.payload_json?.purpose && (
                    <p className="text-[#565959]">
                      <strong className="text-[#0F1111]">Purpose:</strong> {act.payload_json.purpose}
                    </p>
                  )}
                </div>

                {/* Execution Result preview */}
                {isExecuted && act.execution_result_json && (
                  <div className="bg-[#F0F8F4] border border-[#9FD3BC] rounded p-2.5 text-xs text-[#067D62] space-y-1">
                    <p className="font-bold flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" />
                      <span>Simulated Execution Completed</span>
                    </p>
                    <p className="text-[11px] text-[#0F1111]">
                      Executed at: {new Date(act.executed_at || '').toLocaleString()}
                    </p>
                    <p className="text-[11px] text-[#565959]">
                      Environment: Simulated Sandbox Dispatch
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
                  {isPending && (
                    <>
                      <button
                        onClick={() => handleRejectClick(act.id)}
                        disabled={actionInProgress !== null}
                        className="h-8 px-3 bg-white hover:bg-[#FCF4F2] text-[#B12704] font-semibold text-xs rounded border border-[#F2BEB1] flex items-center gap-1 transition-colors disabled:opacity-50"
                      >
                        {isProcessing && actionOperation === 'reject' ? (
                          <AIProcessingIndicator variant="inline" label="Rejecting" tone="teal" />
                        ) : (
                          <>
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject Draft</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => handleApproveClick(act.id)}
                        disabled={actionInProgress !== null}
                        className="h-8 px-4 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center gap-1.5 transition-colors disabled:opacity-50"
                      >
                        {isProcessing && actionOperation === 'approve' ? (
                          <AIProcessingIndicator variant="inline" label="Approving" tone="yellow" />
                        ) : (
                          <>
                            <CheckCircle className="w-3.5 h-3.5 text-[#0F1111]" />
                            <span>Approve Action</span>
                          </>
                        )}
                      </button>
                    </>
                  )}

                  {isApproved && (
                    <button
                      onClick={() => handleExecuteClick(act.id)}
                      disabled={actionInProgress !== null}
                      className="h-8 px-4 bg-[#FF9900] hover:bg-[#E68A00] text-[#0F1111] font-bold text-xs rounded border border-[#E68A00] shadow-sm flex items-center gap-1.5 transition-colors disabled:opacity-50"
                    >
                      {isProcessing && actionOperation === 'execute' ? (
                        <AIProcessingIndicator variant="inline" label="Executing in Simulation" tone="yellow" />
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-current text-[#0F1111]" />
                          <span>Execute in Simulation</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-6 text-xs text-[#565959]">
          No actions prepared yet. Run an analysis or click "Draft New Action" to prepare one.
        </div>
      )}

      {/* Draft Action Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#131921]/70 p-4 backdrop-blur-xs">
          <div className="bg-white rounded-lg shadow-xl border border-[#D5D9D9] w-full max-w-lg overflow-hidden">
            <div className="bg-[#232F3E] text-white px-5 py-3.5 flex items-center justify-between">
              <h3 className="text-sm font-bold font-['Hanken_Grotesk'] text-white">
                Draft New Action
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-[#8A97A9] hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-5 space-y-3.5 text-xs">
              <div>
                <label className="block font-bold text-[#0F1111] mb-1">Action Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as ActionType)}
                  className="w-full h-9 px-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                >
                  <option value="SEND_MESSAGE">Send Message / Escalation Letter</option>
                  <option value="SCHEDULE_FOLLOW_UP">Schedule Follow-up Reminder</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#0F1111] mb-1">Action Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Formal Grievance Escalation Notice"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full h-9 px-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                />
              </div>

              <div>
                <label className="block font-bold text-[#0F1111] mb-1">Description / Rationale</label>
                <input
                  type="text"
                  required
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full h-9 px-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                />
              </div>

              {newType === 'SEND_MESSAGE' ? (
                <>
                  <div>
                    <label className="block font-bold text-[#0F1111] mb-1">Recipient</label>
                    <input
                      type="text"
                      required
                      value={recipient}
                      onChange={(e) => setRecipient(e.target.value)}
                      className="w-full h-9 px-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-[#0F1111] mb-1">Subject Line</label>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="w-full h-9 px-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-[#0F1111] mb-1">Message Content</label>
                    <textarea
                      rows={4}
                      required
                      value={bodyText}
                      onChange={(e) => setBodyText(e.target.value)}
                      className="w-full p-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="block font-bold text-[#0F1111] mb-1">Follow-up Days</label>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={followUpDays}
                    onChange={(e) => setFollowUpDays(Number(e.target.value))}
                    className="w-full h-9 px-2.5 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185]"
                  />
                </div>
              )}

              <div className="pt-3 border-t border-[#D5D9D9] flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="h-8 px-3 bg-white border border-[#D5D9D9] text-[#0F1111] rounded text-xs hover:bg-[#F3F3F3]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingAction}
                  className="h-8 px-4 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold rounded border border-[#FCD200] text-xs disabled:opacity-50"
                >
                  {creatingAction ? (
                    <AIProcessingIndicator variant="inline" label="Creating Action" tone="yellow" />
                  ) : (
                    <span>Create Action</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
