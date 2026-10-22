import React, { useState } from 'react'
import {
  ArrowLeft,
  FileText,
  Clock,
  Send,
  MessageSquare,
  ShieldAlert,
  RefreshCw,
} from 'lucide-react'
import type {
  Case,
  CaseEvent,
  Evidence,
  EvidenceChecklistResponse,
  EvidenceType,
  Action,
  CaseAnalysisResponse,
  SimulatedResponse,
  SimulatedResponseCreatePayload,
  ResponseProcessingResult,
  ActionType,
  PolicySearchResultItem,
} from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { EvidenceManager } from '../components/EvidenceManager'
import { Timeline } from '../components/Timeline'
import { AssistantPanel } from '../components/AssistantPanel'
import { ActionManager } from '../components/ActionManager'
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
  onReassessWorkflow?: () => Promise<void>
  onAddUserNote: (note: string) => Promise<void>
  onUploadEvidence: (file: File, docType?: EvidenceType) => Promise<void>
  onDeleteEvidence: (evidenceId: string) => Promise<void>
  onRunAnalysis: () => Promise<void>
  onSendMessage: (msg: string) => Promise<{ answer: string; supporting_policy_sources?: PolicySearchResultItem[] }>
  onApproveAction: (actionId: string) => Promise<void>
  onRejectAction: (actionId: string, reason?: string) => Promise<void>
  onExecuteAction: (actionId: string) => Promise<void>
  onCreateAction: (
    title: string,
    description: string,
    actionType: ActionType,
    payload: Record<string, any>
  ) => Promise<void>
  onSimulateResponse: (payload: SimulatedResponseCreatePayload) => Promise<void>
  onProcessResponse: (responseId: string) => Promise<ResponseProcessingResult>
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
  onRunAnalysis,
  onSendMessage,
  onApproveAction,
  onRejectAction,
  onExecuteAction,
  onCreateAction,
  onSimulateResponse,
  onProcessResponse,
}) => {
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'EVIDENCE' | 'TIMELINE' | 'ACTIONS' | 'SIMULATION'>('OVERVIEW')
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
    await onCreateAction(title, description, actionType, payload)
    setActiveTab('ACTIONS')
  }

  return (
    <div className="space-y-5">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5 text-[#565959]">
          <button
            onClick={onBackToDashboard}
            className="text-[#007185] hover:text-[#C7511F] font-semibold flex items-center gap-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </button>
          <span>›</span>
          <span className="font-semibold text-[#0F1111]">
            Case #{caseData.id.slice(0, 8)} ({caseData.product_name})
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="h-8 px-3 bg-white hover:bg-[#F3F3F3] text-[#0F1111] font-semibold text-xs rounded border border-[#D5D9D9] shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            {refreshing ? (
              <AIProcessingIndicator variant="inline" label="Refreshing" tone="teal" />
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5 text-[#007185]" />
                <span>Refresh State</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Primary Case Banner (Stitch Card 1 Style) */}
      <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-[#EAEDED]">
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold font-['Hanken_Grotesk'] text-[#0F1111] tracking-tight">
                {caseData.title}
              </h1>
              <StatusBadge status={caseData.status} />
            </div>

            <p className="text-sm font-semibold text-[#565959]">
              Product: {caseData.product_name}
            </p>

            <div className="flex items-center gap-4 text-xs text-[#565959] flex-wrap pt-0.5">
              <span>
                Case ID: <strong className="font-mono text-[#0F1111]">#{caseData.id.slice(0, 8)}</strong>
              </span>
              <span>•</span>
              <span>Created: <strong className="text-[#0F1111]">{new Date(caseData.created_at).toLocaleDateString()}</strong></span>
              <span>•</span>
              <span>Last Updated: <strong className="text-[#0F1111]">{new Date(caseData.updated_at).toLocaleTimeString()}</strong></span>
            </div>
          </div>

          <div className="flex flex-col items-start md:items-end gap-1 shrink-0 bg-[#F9F9F9] p-3 rounded border border-[#EAEDED]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#565959]">
              Regulatory Context
            </span>
            <div className="flex items-center gap-1.5 text-[#007185] font-bold text-xs">
              <ShieldAlert className="w-4 h-4 text-[#007185]" />
              <span>Consumer Guidance (India)</span>
            </div>
            <span className="text-[11px] text-[#565959]">
              NCH Escalation (consumerhelpline.gov.in)
            </span>
          </div>
        </div>

        {/* Tab Selection Navigation */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar border-b border-[#EAEDED] pb-2 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('OVERVIEW')}
            className={`px-3 py-1.5 rounded transition-colors ${
              activeTab === 'OVERVIEW'
                ? 'bg-[#232F3E] text-white font-bold'
                : 'text-[#565959] hover:bg-[#F3F3F3] hover:text-[#0F1111]'
            }`}
          >
            Overview & Summary
          </button>

          <button
            onClick={() => setActiveTab('EVIDENCE')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === 'EVIDENCE'
                ? 'bg-[#232F3E] text-white font-bold'
                : 'text-[#565959] hover:bg-[#F3F3F3] hover:text-[#0F1111]'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Evidence ({evidenceList.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('ACTIONS')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === 'ACTIONS'
                ? 'bg-[#232F3E] text-white font-bold'
                : 'text-[#565959] hover:bg-[#F3F3F3] hover:text-[#0F1111]'
            }`}
          >
            <Send className="w-3.5 h-3.5" />
            <span>Agent Actions ({actions.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('SIMULATION')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === 'SIMULATION'
                ? 'bg-[#232F3E] text-white font-bold'
                : 'text-[#565959] hover:bg-[#F3F3F3] hover:text-[#0F1111]'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Inbound Provider Simulator ({simulatedResponses.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('TIMELINE')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === 'TIMELINE'
                ? 'bg-[#232F3E] text-white font-bold'
                : 'text-[#565959] hover:bg-[#F3F3F3] hover:text-[#0F1111]'
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
              <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-[#EAEDED]">
                  <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111]">
                    Incident Narrative & Claim Facts
                  </h2>
                  <span className="text-xs text-[#565959]">
                    Status: {caseData.status}
                  </span>
                </div>

                <p className="text-xs text-[#0F1111] leading-relaxed whitespace-pre-wrap">
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

        {/* Right Column: Sticky Alexa+ / ResolveAI Assistant Panel */}
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
