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
      <div className="bg-white rounded-xl p-5 shadow-xs border border-[#E4E1E8]">
        <AIProcessingIndicator
          variant="card"
          label="Loading Workflow State"
          sublabel="Connecting to local orchestrator state..."
          tone="indigo"
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
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#FBF4E8] text-[#A06C18] border border-[#E7B76A]/40">
            <AlertCircle className="w-3.5 h-3.5 text-[#E7B76A]" />
            <span>Waiting for User Input</span>
          </span>
        )
      case 'WAITING_FOR_ACTION_APPROVAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#F0EEFA] text-[#5B4B8A] border border-[#8B7BC4]/40">
            <ShieldCheck className="w-3.5 h-3.5 text-[#5B4B8A]" />
            <span>Action Approval Required</span>
          </span>
        )
      case 'WAITING_FOR_EXTERNAL_RESPONSE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#FBF4E8] text-[#A06C18] border border-[#E7B76A]/40">
            <Clock className="w-3.5 h-3.5 text-[#E7B76A]" />
            <span>Awaiting Provider Reply</span>
          </span>
        )
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#F0EEFA] text-[#312E81] border border-[#8B7BC4]/40">
            <RotateCw className="w-3.5 h-3.5 animate-spin text-[#312E81]" />
            <span>Processing</span>
          </span>
        )
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#EAF3EF] text-[#3E7C68] border border-[#3E7C68]/30">
            <CheckCircle className="w-3.5 h-3.5 text-[#3E7C68]" />
            <span>Completed</span>
          </span>
        )
      case 'NONE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#F7F6F3] text-[#625F70] border border-[#E4E1E8]">
            <Compass className="w-3.5 h-3.5 text-[#8E8B99]" />
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
    <div className="bg-white rounded-xl p-5 shadow-xs border border-[#E4E1E8] space-y-4">
      {/* Header with Title and Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#E4E1E8] gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-[#312E81]" />
            <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#27243A]">
              Resolution Workflow State
            </h2>
          </div>
          <p className="text-xs text-[#625F70]">
            Autonomous lifecycle tracking evidence completeness, deadlines, and next actions.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {onReassessWorkflow && (
            <button
              onClick={handleReassessClick}
              disabled={reassessing}
              className="h-7 px-2.5 bg-white hover:bg-[#F0EEFA] text-[#312E81] font-bold text-xs rounded-md border border-[#E4E1E8] shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
              title="Trigger orchestrator reassessment across case context"
            >
              {reassessing ? (
                <AIProcessingIndicator variant="inline" label="Reassessing" tone="indigo" />
              ) : (
                <>
                  <RotateCw className="w-3.5 h-3.5 text-[#312E81]" />
                  <span>Reassess Workflow</span>
                </>
              )}
            </button>
          )}
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-[#312E81] text-white">
            Stage: {formatStageLabel(workflowState.stage)}
          </span>
          {renderWaitStateBadge(workflowState.wait_state)}
        </div>
      </div>

      {/* Reassessing Workflow In-Flight Card */}
      {reassessing && (
        <AIProcessingIndicator
          variant="card"
          label="Reassessing Resolution Workflow State"
          sublabel="Evaluating evidence checklist completeness, provider commitments, and determining next recommended step..."
          tone="indigo"
        />
      )}

      {reassessError && (
        <div className="p-2.5 bg-[#F9ECEB] border border-[#B94A48]/30 rounded-lg text-xs text-[#B94A48] flex items-center justify-between">
          <span>{reassessError}</span>
          <button onClick={() => setReassessError(null)} className="font-bold ml-2 cursor-pointer">×</button>
        </div>
      )}

      {/* Case Goal */}
      <div className="bg-[#F7F6F3] rounded-lg p-3 border border-[#E4E1E8] text-xs space-y-1">
        <span className="font-bold text-[#625F70] uppercase tracking-wider text-[11px]">
          Objective & Goal
        </span>
        <p className="text-[#27243A] font-medium leading-relaxed">
          {workflowState.goal}
        </p>
      </div>

      {/* Recommended Next Step Box */}
      <div className="bg-[#F0EEFA] border-l-4 border-[#312E81] rounded-r-lg p-3.5 space-y-1 text-xs">
        <div className="flex items-center justify-between">
          <span className="font-bold text-[#312E81] flex items-center gap-1.5 text-xs">
            <ArrowRight className="w-4 h-4 text-[#D97757]" />
            <span>Recommended Next Step</span>
          </span>
          <span className="text-[11px] text-[#625F70]">
            Updated: {new Date(workflowState.last_reassessed_at).toLocaleTimeString()}
          </span>
        </div>
        <p className="text-[#27243A] font-medium leading-relaxed">
          {workflowState.latest_recommendation || 'Evaluating case context and evidence checklist.'}
        </p>
      </div>

      {/* Outstanding Requirements Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {/* Pending Evidence */}
        <div className="border border-[#E4E1E8] rounded-lg p-3 space-y-2 text-xs bg-[#FFFFFF]">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[#27243A] flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-[#5B4B8A]" />
              <span>Pending Evidence</span>
            </span>
            {workflowState.pending_evidence && workflowState.pending_evidence.length > 0 ? (
              <span className="bg-[#FBF4E8] text-[#A06C18] px-2 py-0.5 rounded-full text-[10px] font-bold">
                {workflowState.pending_evidence.length} Needed
              </span>
            ) : (
              <span className="text-[#3E7C68] text-[11px] font-semibold flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Complete
              </span>
            )}
          </div>

          {workflowState.pending_evidence && workflowState.pending_evidence.length > 0 ? (
            <div className="space-y-1.5">
              <ul className="list-disc list-inside space-y-1 text-[#625F70]">
                {workflowState.pending_evidence.map((item, idx) => (
                  <li key={idx} className="text-[#B94A48] font-medium">
                    {item}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => onSelectTab('EVIDENCE')}
                className="mt-1 text-xs font-semibold text-[#312E81] hover:text-[#5B4B8A] hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>Go to Evidence tab to upload</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <p className="text-[11px] text-[#625F70]">
              No documents are currently blocking this stage.
            </p>
          )}
        </div>

        {/* Outstanding Commitments */}
        <div className="border border-[#E4E1E8] rounded-lg p-3 space-y-2 text-xs bg-[#FFFFFF]">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[#27243A] flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#3E7C68]" />
              <span>Provider Commitments & Offers</span>
            </span>
            {workflowState.outstanding_commitments && workflowState.outstanding_commitments.length > 0 ? (
              <span className="bg-[#EAF3EF] text-[#3E7C68] px-2 py-0.5 rounded-full text-[10px] font-bold">
                {workflowState.outstanding_commitments.length} Active
              </span>
            ) : (
              <span className="text-[#8E8B99] text-[11px]">None recorded</span>
            )}
          </div>

          {workflowState.outstanding_commitments && workflowState.outstanding_commitments.length > 0 ? (
            <ul className="list-disc list-inside space-y-1 text-[#3E7C68] font-medium">
              {workflowState.outstanding_commitments.map((comm, idx) => (
                <li key={idx}>{comm}</li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] text-[#625F70]">
              No formal commitments or deadlines registered yet.
            </p>
          )}
        </div>
      </div>

      {/* Active Pending Action Summary (if present) */}
      {activeAction && activeAction.status === 'PENDING_APPROVAL' && (
        <div className="bg-[#FBF4E8] border border-[#E7B76A]/40 rounded-xl p-4 space-y-2.5 text-xs">
          <div className="flex items-center justify-between flex-wrap gap-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#D97757]" />
              <span className="font-bold text-[#27243A]">
                Proposed Agent Action Requires Your Approval
              </span>
            </div>
            <span className="bg-white text-[#A06C18] px-2 py-0.5 rounded-full text-[11px] font-bold border border-[#E7B76A]/40">
              PENDING APPROVAL
            </span>
          </div>

          <div className="bg-white p-3 rounded-lg border border-[#E4E1E8] space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#27243A]">{activeAction.title}</span>
              <span className="text-[10px] uppercase font-bold text-[#5B4B8A] bg-[#F0EEFA] px-2 py-0.5 rounded-full">
                {activeAction.action_type} (Simulated)
              </span>
            </div>
            <p className="text-[#625F70] line-clamp-2">{activeAction.description}</p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-[#625F70]">
              Action is strictly blocked from executing until you approve it.
            </span>
            <div className="flex items-center gap-2">
              {onApproveAction && (
                <button
                  onClick={() => handleApproveFromPanel(activeAction.id)}
                  disabled={approvingActive}
                  className="px-3.5 py-1.5 bg-[#3E7C68] hover:bg-[#346756] text-white font-bold rounded-lg text-xs transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-xs"
                >
                  {approvingActive ? (
                    <AIProcessingIndicator variant="inline" label="Approving" tone="indigo" />
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
                className="px-3 py-1.5 bg-[#312E81] hover:bg-[#262366] text-white font-bold rounded-lg text-xs transition-colors cursor-pointer shadow-xs"
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
