import React, { useState } from 'react'
import {
  FileText,
  Clock,
  Send,
  MessageSquare,
  ShieldAlert,
  ArrowLeft,
  RefreshCw,
} from 'lucide-react'
import type {
  Case,
  CaseEvent,
  Evidence,
  EvidenceChecklistResponse,
  Action,
  CaseAnalysisResponse,
  SimulatedResponse,
  EvidenceType,
  ActionType,
  SimulatedResponseCreatePayload,
  ResponseProcessingResult,
  PolicySearchResultItem,
} from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { Timeline } from '../components/Timeline'
import { EvidenceManager } from '../components/EvidenceManager'
import { ActionManager } from '../components/ActionManager'
import { AssistantPanel } from '../components/AssistantPanel'
import { SimulatedResponseManager } from '../components/SimulatedResponseManager'
import { AgentWorkflowStatusPanel } from '../components/AgentWorkflowStatusPanel'
import { AIProcessingIndicator } from '../components/AIProcessingIndicator'

interface CaseDetailsViewProps {
  caseData: Case
  events: CaseEvent[]
  evidenceList: Evidence[]
  checklist: EvidenceChecklistResponse | null
  actions: Action[]
  analysis: CaseAnalysisResponse | null
  simulatedResponses: SimulatedResponse[]
  onBackToDashboard: () => void
  onRefreshCase: () => Promise<void>
  onReassessWorkflow: () => Promise<void>
  onAddUserNote: (note: string) => Promise<void>
  onUploadEvidence: (file: File, type?: EvidenceType) => Promise<void>
  onDeleteEvidence: (evidenceId: string) => Promise<void>
  onApproveAction: (actionId: string) => Promise<void>
  onRejectAction: (actionId: string) => Promise<void>
  onExecuteAction: (actionId: string) => Promise<void>
  onSimulateResponse: (payload: SimulatedResponseCreatePayload) => Promise<void>
  onProcessResponse: (responseId: string) => Promise<ResponseProcessingResult>
  onRunAnalysis?: () => Promise<void>
  onSendMessage?: (msg: string) => Promise<{ answer: string; supporting_policy_sources?: PolicySearchResultItem[] }>
  onCreateAction?: (
    title: string,
    description: string,
    actionType: ActionType,
    payload: Record<string, any>
  ) => Promise<void>
}

export const CaseDetailsView: React.FC<CaseDetailsViewProps> = ({
  caseData,
  events,
  evidenceList,
  checklist,
  actions,
  analysis,
  simulatedResponses,
  onBackToDashboard,
  onRefreshCase,
  onReassessWorkflow,
  onAddUserNote,
  onUploadEvidence,
  onDeleteEvidence,
  onApproveAction,
  onRejectAction,
  onExecuteAction,
  onSimulateResponse,
  onProcessResponse,
  onRunAnalysis,
  onSendMessage,
  onCreateAction,
}) => {
  const [activeTab, setActiveTab] = useState<
    'OVERVIEW' | 'EVIDENCE' | 'ACTIONS' | 'SIMULATION' | 'TIMELINE'
  >('OVERVIEW')

  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await onRefreshCase()
    } finally {
      setRefreshing(false)
    }
  }

  const handlePrepareActionFromAssistant = async (
    title: string,
    description: string,
    actionType: ActionType,
    payload: Record<string, any>
  ) => {
    if (onCreateAction) {
      await onCreateAction(title, description, actionType, payload)
      setActiveTab('ACTIONS')
    }
  }

  return (
    <div className="space-y-5">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5 text-[#625F70]">
          <button
            onClick={onBackToDashboard}
            className="text-[#312E81] hover:text-[#5B4B8A] font-semibold flex items-center gap-1 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </button>
          <span>›</span>
          <span className="font-semibold text-[#27243A]">
            Case #{caseData.id.slice(0, 8)} ({caseData.product_name})
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="h-8 px-3 bg-white hover:bg-[#F0EEFA] text-[#27243A] font-semibold text-xs rounded-lg border border-[#E4E1E8] shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {refreshing ? (
              <AIProcessingIndicator variant="inline" label="Refreshing" tone="indigo" />
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5 text-[#312E81]" />
                <span>Refresh State</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Primary Case Banner */}
      <div className="bg-white rounded-xl p-6 shadow-xs border border-[#E4E1E8] space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-[#E4E1E8]">
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold font-['Hanken_Grotesk'] text-[#27243A] tracking-tight">
                {caseData.title}
              </h1>
              <StatusBadge status={caseData.status} />
            </div>

            <p className="text-sm font-semibold text-[#625F70]">
              Product: {caseData.product_name}
            </p>

            <div className="flex items-center gap-4 text-xs text-[#625F70] flex-wrap pt-0.5">
              <span>
                Case ID: <strong className="font-mono text-[#27243A]">#{caseData.id.slice(0, 8)}</strong>
              </span>
              <span>•</span>
              <span>Created: <strong className="text-[#27243A]">{new Date(caseData.created_at).toLocaleDateString()}</strong></span>
              <span>•</span>
              <span>Last Updated: <strong className="text-[#27243A]">{new Date(caseData.updated_at).toLocaleTimeString()}</strong></span>
            </div>
          </div>

          <div className="flex flex-col items-start md:items-end gap-1 shrink-0 bg-[#F0EEFA] p-3 rounded-lg border border-[#8B7BC4]/20">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#312E81]">
              Consumer Rights Context
            </span>
            <div className="flex items-center gap-1.5 text-[#312E81] font-bold text-xs">
              <ShieldAlert className="w-4 h-4 text-[#D97757]" />
              <span>Consumer Protection Guidelines</span>
            </div>
            <span className="text-[11px] text-[#625F70]">
              Statutory Replacement & Refund Standards
            </span>
          </div>
        </div>

        {/* Tab Selection Navigation */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar border-b border-[#E4E1E8] pb-2 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('OVERVIEW')}
            className={`px-3 py-1.5 rounded-md transition-colors cursor-pointer ${
              activeTab === 'OVERVIEW'
                ? 'bg-[#312E81] text-white font-bold shadow-xs'
                : 'text-[#625F70] hover:bg-[#F0EEFA] hover:text-[#27243A]'
            }`}
          >
            Overview & Summary
          </button>

          <button
            onClick={() => setActiveTab('EVIDENCE')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'EVIDENCE'
                ? 'bg-[#312E81] text-white font-bold shadow-xs'
                : 'text-[#625F70] hover:bg-[#F0EEFA] hover:text-[#27243A]'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Evidence ({evidenceList.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('ACTIONS')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'ACTIONS'
                ? 'bg-[#312E81] text-white font-bold shadow-xs'
                : 'text-[#625F70] hover:bg-[#F0EEFA] hover:text-[#27243A]'
            }`}
          >
            <Send className="w-3.5 h-3.5" />
            <span>Agent Actions ({actions.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('SIMULATION')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'SIMULATION'
                ? 'bg-[#312E81] text-white font-bold shadow-xs'
                : 'text-[#625F70] hover:bg-[#F0EEFA] hover:text-[#27243A]'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Inbound Provider Simulator ({simulatedResponses.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('TIMELINE')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'TIMELINE'
                ? 'bg-[#312E81] text-white font-bold shadow-xs'
                : 'text-[#625F70] hover:bg-[#F0EEFA] hover:text-[#27243A]'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Timeline Audit ({events.length})</span>
          </button>
        </div>
      </div>

      {/* Main Split Grid (Left content + Right Assistant Panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Dynamic according to selected tab */}
        <div className="lg:col-span-7 space-y-5">
          {activeTab === 'OVERVIEW' && (
            <>
              {/* Agentic Workflow Status Panel */}
              <AgentWorkflowStatusPanel
                workflowState={caseData.workflow_state}
                actions={actions}
                onSelectTab={setActiveTab}
                onApproveAction={onApproveAction}
                onReassessWorkflow={onReassessWorkflow}
              />

              {/* Incident Assessment Card */}
              <div className="bg-white rounded-xl p-5 shadow-xs border border-[#E4E1E8] space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-[#E4E1E8]">
                  <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#27243A]">
                    Incident Narrative & Claim Facts
                  </h2>
                  <span className="text-xs text-[#625F70]">
                    Status: {caseData.status}
                  </span>
                </div>

                <p className="text-xs text-[#27243A] leading-relaxed whitespace-pre-wrap">
                  {caseData.issue_description}
                </p>
              </div>

              {/* Evidence Snapshot Card */}
              <EvidenceManager
                evidenceList={evidenceList}
                checklist={checklist}
                onUpload={onUploadEvidence}
                onDelete={onDeleteEvidence}
              />

              {/* Timeline Snapshot */}
              <Timeline events={events} onAddUserNote={onAddUserNote} />
            </>
          )}

          {activeTab === 'EVIDENCE' && (
            <EvidenceManager
              evidenceList={evidenceList}
              checklist={checklist}
              onUpload={onUploadEvidence}
              onDelete={onDeleteEvidence}
            />
          )}

          {activeTab === 'ACTIONS' && (
            <ActionManager
              actions={actions}
              onApprove={onApproveAction}
              onReject={onRejectAction}
              onExecute={onExecuteAction}
              onCreateAction={onCreateAction}
            />
          )}

          {activeTab === 'SIMULATION' && (
            <SimulatedResponseManager
              responses={simulatedResponses}
              onSimulate={onSimulateResponse}
              onProcess={onProcessResponse}
            />
          )}

          {activeTab === 'TIMELINE' && (
            <Timeline events={events} onAddUserNote={onAddUserNote} />
          )}
        </div>

        {/* Right Column: Assistant Panel */}
        <div className="lg:col-span-5 sticky top-28">
          <AssistantPanel
            caseId={caseData.id}
            analysis={analysis}
            onRunAnalysis={onRunAnalysis}
            onSendMessage={onSendMessage}
            onPrepareAction={handlePrepareActionFromAssistant}
            onOpenSimulateModal={() => setActiveTab('SIMULATION')}
          />
        </div>
      </div>
    </div>
  )
}
