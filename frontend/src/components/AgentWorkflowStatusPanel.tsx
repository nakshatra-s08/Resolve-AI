import React, { useState } from 'react'
import {
  Compass,
  Clock,
  AlertCircle,
  CheckCircle,
  FileText,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  RotateCw,
} from 'lucide-react'
import type { WorkflowState, WorkflowWaitState, WorkflowStage, Action } from '../api/types'
import { AIProcessingIndicator } from './AIProcessingIndicator'

interface AgentWorkflowStatusPanelProps {
  workflowState?: WorkflowState | null
  actions: Action[]
  onSelectTab: (tab: 'OVERVIEW' | 'EVIDENCE' | 'TIMELINE' | 'ACTIONS' | 'SIMULATION') => void
  onApproveAction?: (actionId: string) => Promise<void>
  onReassessWorkflow?: () => Promise<void>
}

export const AgentWorkflowStatusPanel: React.FC<AgentWorkflowStatusPanelProps> = ({
  workflowState,
  actions,
  onSelectTab,
  onApproveAction,
  onReassessWorkflow,
}) => {
  const [reassessing, setReassessing] = useState(false)
  const [reassessError, setReassessError] = useState<string | null>(null)
  const [approvingActive, setApprovingActive] = useState(false)

  const handleReassessClick = async () => {
    if (!onReassessWorkflow || reassessing) return
    setReassessing(true)
    setReassessError(null)
    try {
      await onReassessWorkflow()
    } catch (err: any) {
      setReassessError(err.message || 'Workflow reassessment failed.')
    } finally {
      setReassessing(false)
    }
  }

  const handleApproveFromPanel = async (actionId: string) => {
    if (!onApproveAction || approvingActive) return
    setApprovingActive(true)
    try {
      await onApproveAction(actionId)
    } finally {
      setApprovingActive(false)
    }
  }

  if (!workflowState) {
    return (
      <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9]">
        <AIProcessingIndicator
          variant="card"
          label="Loading Persistent Workflow State"
          sublabel="Connecting to local SQLite orchestrator state..."
        />
      </div>
    )
  }

  // Identify active pending action from workflow state or current actions
  const activeAction =
    workflowState.active_action ||
    actions.find((a) => a.id === workflowState.active_action_id) ||
    actions.find((a) => a.status === 'PENDING_APPROVAL')

  // Helper for wait state badge styling
  const renderWaitStateBadge = (waitState: WorkflowWaitState) => {
    switch (waitState) {
      case 'WAITING_FOR_USER_INPUT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-[#FFF8E7] text-[#C45500] border border-[#FCD200]">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Waiting for User Input</span>
          </span>
        )
      case 'WAITING_FOR_ACTION_APPROVAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-[#F7F2FA] text-[#5C248A] border border-[#D6C2E8]">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Waiting for Action Approval</span>
          </span>
        )
      case 'WAITING_FOR_EXTERNAL_RESPONSE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-[#F0F8FA] text-[#007185] border border-[#A0D3DC]">
            <Clock className="w-3.5 h-3.5" />
            <span>Waiting for External Reply</span>
          </span>
        )
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-[#E8F4F8] text-[#006699] border border-[#B2D8E8]">
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
            <span>Processing</span>
          </span>
        )
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-[#F0F8F4] text-[#067D62] border border-[#9FD3BC]">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Completed</span>
          </span>
        )
      case 'NONE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-[#F3F3F3] text-[#565959] border border-[#D5D9D9]">
            <Compass className="w-3.5 h-3.5" />
            <span>Active</span>
          </span>
        )
    }
  }

  // Format stage display label
  const formatStageLabel = (stage: WorkflowStage): string => {
    switch (stage) {
      case 'INTAKE':
        return 'Intake & Triage'
      case 'EVIDENCE_GATHERING':
        return 'Evidence Gathering'
      case 'UNDER_REVIEW':
        return 'Under Review'
      case 'ACTION_PENDING':
        return 'Action Pending Approval'
      case 'AWAITING_RESPONSE':
        return 'Awaiting Provider Response'
      case 'RESOLVED':
        return 'Resolved'
      case 'CLOSED':
        return 'Closed'
      default:
        return stage
    }
  }

  return (
    <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-4">
      {/* Header with Title and Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#EAEDED] gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-[#007185]" />
            <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111]">
              Agentic Orchestration State
            </h2>
          </div>
          <p className="text-xs text-[#565959]">
            Persistent workflow lifecycle managed automatically by the ResolveAI orchestrator.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {onReassessWorkflow && (
            <button
              onClick={handleReassessClick}
              disabled={reassessing}
              className="h-7 px-2.5 bg-white hover:bg-[#F3F3F3] text-[#007185] font-bold text-xs rounded border border-[#D5D9D9] shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Trigger orchestrator reassessment across case context"
            >
              {reassessing ? (
                <AIProcessingIndicator variant="inline" label="Reassessing" tone="teal" />
              ) : (
                <>
                  <RotateCw className="w-3.5 h-3.5 text-[#007185]" />
                  <span>Reassess Workflow</span>
                </>
              )}
            </button>
          )}
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-[#232F3E] text-white">
            Stage: {formatStageLabel(workflowState.stage)}
          </span>
          {renderWaitStateBadge(workflowState.wait_state)}
        </div>
      </div>

      {/* Reassessing Workflow In-Flight Card */}
      {reassessing && (
        <AIProcessingIndicator
          variant="card"
          label="Reassessing Agentic Workflow State"
          sublabel="Evaluating evidence checklist completeness, provider commitments, and determining next recommended step..."
        />
      )}

      {reassessError && (
        <div className="p-2.5 bg-[#FCF4F2] border border-[#F2BEB1] rounded text-xs text-[#B12704] flex items-center justify-between">
          <span>{reassessError}</span>
          <button onClick={() => setReassessError(null)} className="font-bold ml-2">×</button>
        </div>
      )}

      {/* Case Goal */}
      <div className="bg-[#F9F9F9] rounded-md p-3 border border-[#EAEDED] text-xs space-y-1">
        <span className="font-bold text-[#565959] uppercase tracking-wider text-[11px]">
          Objective & Goal
        </span>
        <p className="text-[#0F1111] font-medium leading-relaxed">
          {workflowState.goal}
        </p>
      </div>

      {/* Recommended Next Step Box */}
      <div className="bg-[#F0F8FA] border-l-4 border-[#007185] rounded-r-md p-3.5 space-y-1 text-xs">
        <div className="flex items-center justify-between">
          <span className="font-bold text-[#007185] flex items-center gap-1.5 text-xs">
            <ArrowRight className="w-4 h-4" />
            <span>Recommended Next Step</span>
          </span>
          <span className="text-[11px] text-[#565959]">
            Updated: {new Date(workflowState.last_reassessed_at).toLocaleTimeString()}
          </span>
        </div>
        <p className="text-[#0F1111] font-medium leading-relaxed">
          {workflowState.latest_recommendation || 'Evaluating case context and evidence checklist.'}
        </p>
      </div>

      {/* Outstanding Requirements Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {/* Pending Evidence */}
        <div className="border border-[#D5D9D9] rounded-md p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[#0F1111] flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-[#565959]" />
              <span>Pending Evidence</span>
            </span>
            {workflowState.pending_evidence && workflowState.pending_evidence.length > 0 ? (
              <span className="bg-[#FFF8E7] text-[#C45500] px-1.5 py-0.5 rounded text-[10px] font-bold">
                {workflowState.pending_evidence.length} Needed
              </span>
            ) : (
              <span className="text-[#067D62] text-[11px] font-semibold flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> None
              </span>
            )}
          </div>

          {workflowState.pending_evidence && workflowState.pending_evidence.length > 0 ? (
            <div className="space-y-1.5">
              <ul className="list-disc list-inside space-y-1 text-[#565959]">
                {workflowState.pending_evidence.map((item, idx) => (
                  <li key={idx} className="text-[#B12704] font-medium">
                    {item}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => onSelectTab('EVIDENCE')}
                className="mt-1 text-xs font-semibold text-[#007185] hover:text-[#C7511F] hover:underline flex items-center gap-1"
              >
                <span>Go to Evidence tab to upload</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <p className="text-[11px] text-[#565959]">
              No documents are currently blocking this stage.
            </p>
          )}
        </div>

        {/* Outstanding Commitments */}
        <div className="border border-[#D5D9D9] rounded-md p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[#0F1111] flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#565959]" />
              <span>Provider Commitments & Offers</span>
            </span>
            {workflowState.outstanding_commitments && workflowState.outstanding_commitments.length > 0 ? (
              <span className="bg-[#F0F8F4] text-[#067D62] px-1.5 py-0.5 rounded text-[10px] font-bold">
                {workflowState.outstanding_commitments.length} Active
              </span>
            ) : (
              <span className="text-[#565959] text-[11px]">None recorded</span>
            )}
          </div>

          {workflowState.outstanding_commitments && workflowState.outstanding_commitments.length > 0 ? (
            <ul className="list-disc list-inside space-y-1 text-[#067D62] font-medium">
              {workflowState.outstanding_commitments.map((comm, idx) => (
                <li key={idx}>{comm}</li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] text-[#565959]">
              No formal commitments or deadlines registered yet.
            </p>
          )}
        </div>
      </div>

      {/* Active Pending Action Summary (if present) */}
      {activeAction && activeAction.status === 'PENDING_APPROVAL' && (
        <div className="bg-[#FFFDF5] border border-[#FCD200] rounded-md p-3.5 space-y-2 text-xs">
          <div className="flex items-center justify-between flex-wrap gap-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#C45500]" />
              <span className="font-bold text-[#0F1111]">
                Proposed Agent Action Requires Review
              </span>
            </div>
            <span className="bg-[#FFF8E7] text-[#C45500] px-2 py-0.5 rounded text-[11px] font-bold border border-[#FCD200]">
              Status: PENDING_APPROVAL
            </span>
          </div>

          <div className="bg-white p-2.5 rounded border border-[#EAEDED] space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#0F1111]">{activeAction.title}</span>
              <span className="text-[10px] uppercase font-bold text-[#565959] bg-[#F3F3F3] px-1.5 py-0.5 rounded">
                {activeAction.action_type} (Simulated)
              </span>
            </div>
            <p className="text-[#565959] line-clamp-2">{activeAction.description}</p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-[#565959]">
              Action will not execute until explicitly approved.
            </span>
            <div className="flex items-center gap-2">
              {onApproveAction && (
                <button
                  onClick={() => handleApproveFromPanel(activeAction.id)}
                  disabled={approvingActive}
                  className="px-3 py-1 bg-[#067D62] hover:bg-[#05634E] text-white font-bold rounded text-xs transition-colors flex items-center gap-1 disabled:opacity-50"
                >
                  {approvingActive ? (
                    <AIProcessingIndicator variant="inline" label="Approving" tone="navy" />
                  ) : (
                    <>
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Approve Action</span>
                    </>
                  )}
                </button>
              )}
              <button
                onClick={() => onSelectTab('ACTIONS')}
                className="px-3 py-1 bg-[#232F3E] hover:bg-[#131921] text-white font-bold rounded text-xs transition-colors"
              >
                Review in Actions
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
