import { useEffect, useState } from 'react'
import { api } from './api/client'
import type {
  Case,
  CaseEvent,
  Evidence,
  EvidenceChecklistResponse,
  EvidenceType,
  Action,
  FollowUpItem,
  CaseAnalysisResponse,
  SimulatedResponse,
  SimulatedResponseCreatePayload,
  ResponseProcessingResult,
  CaseCreatePayload,
  ActionType,
  PolicySearchResultItem,
} from './api/types'
import { Navbar } from './components/Navbar'
import { Dashboard } from './views/Dashboard'
import { CaseDetailsView } from './views/CaseDetailsView'
import { CreateCaseModal } from './components/CreateCaseModal'

export function App() {
  const [currentTab, setCurrentTab] = useState<'home' | 'cases' | 'case-details' | 'follow-ups'>('home')
  const [cases, setCases] = useState<Case[]>([])
  const [followUps, setFollowUps] = useState<FollowUpItem[]>([])
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const [activeCase, setActiveCase] = useState<Case | null>(null)

  // Sub-resources for active case
  const [events, setEvents] = useState<CaseEvent[]>([])
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([])
  const [checklist, setChecklist] = useState<EvidenceChecklistResponse | null>(null)
  const [actions, setActions] = useState<Action[]>([])
  const [analysis, setAnalysis] = useState<CaseAnalysisResponse | null>(null)
  const [simulatedResponses, setSimulatedResponses] = useState<SimulatedResponse[]>([])

  // Modals & UI states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [errorBanner, setErrorBanner] = useState<string | null>(null)

  // Load detailed sub-resources for selected case
  const loadCaseDetails = async (caseId: string) => {
    try {
      const [
        cData,
        cEvents,
        cEvidence,
        cChecklist,
        cActions,
        cResponses,
      ] = await Promise.all([
        api.getCase(caseId),
        api.getCaseTimeline(caseId),
        api.listEvidence(caseId),
        api.getEvidenceChecklist(caseId),
        api.listActions(caseId),
        api.listSimulatedResponses(caseId),
      ])

      setActiveCase(cData)
      setEvents(cEvents)
      setEvidenceList(cEvidence)
      setChecklist(cChecklist)
      setActions(cActions)
      setSimulatedResponses(cResponses)
    } catch (err: any) {
      console.error(err)
      setErrorBanner(`Failed to load case #${caseId.slice(0, 8)}: ${err.message}`)
    }
  }

  // Fetch initial dashboard data
  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const fetchedCases = await api.listCases()
      setCases(fetchedCases)

      // Collect follow-ups across all cases
      const allFollowUps: FollowUpItem[] = []
      for (const c of fetchedCases) {
        try {
          const caseFollowUps = await api.listFollowUps(c.id)
          allFollowUps.push(...caseFollowUps)
        } catch {
          // ignore individual follow-up errors
        }
      }
      setFollowUps(allFollowUps)

      // If activeCaseId is set, refresh active case too
      if (activeCaseId) {
        await loadCaseDetails(activeCaseId)
      } else if (fetchedCases.length > 0 && !activeCaseId) {
        // Pre-select first case
        setActiveCaseId(fetchedCases[0].id)
      }
    } catch (err: any) {
      console.error(err)
      setErrorBanner(err.message || 'Failed to connect to ResolveAI backend')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboardData()
  }, [])

  const handleSelectCase = async (caseId: string) => {
    setActiveCaseId(caseId)
    await loadCaseDetails(caseId)
    setCurrentTab('case-details')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleCreateCase = async (payload: CaseCreatePayload) => {
    const created = await api.createCase(payload)
    await loadDashboardData()
    await handleSelectCase(created.id)
  }

  // Handlers for active case actions
  const handleAddUserNote = async (note: string) => {
    if (!activeCaseId) return
    await api.addCaseEvent(activeCaseId, note)
    const updatedEvents = await api.getCaseTimeline(activeCaseId)
    setEvents(updatedEvents)
  }

  const handleUploadEvidence = async (file: File, docType?: EvidenceType) => {
    if (!activeCaseId) return
    await api.uploadEvidence(activeCaseId, file, docType)
    const [cEvidence, cChecklist, cEvents, cCase] = await Promise.all([
      api.listEvidence(activeCaseId),
      api.getEvidenceChecklist(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
    ])
    setEvidenceList(cEvidence)
    setChecklist(cChecklist)
    setEvents(cEvents)
    setActiveCase(cCase)
  }

  const handleDeleteEvidence = async (evidenceId: string) => {
    if (!activeCaseId) return
    await api.deleteEvidence(activeCaseId, evidenceId)
    const [cEvidence, cChecklist, cEvents, cCase] = await Promise.all([
      api.listEvidence(activeCaseId),
      api.getEvidenceChecklist(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
    ])
    setEvidenceList(cEvidence)
    setChecklist(cChecklist)
    setEvents(cEvents)
    setActiveCase(cCase)
  }

  const handleRunAnalysis = async () => {
    if (!activeCaseId) return
    const res = await api.runAnalysis(activeCaseId)
    setAnalysis(res)
    const [updatedCase, updatedEvents] = await Promise.all([
      api.getCase(activeCaseId),
      api.getCaseTimeline(activeCaseId),
    ])
    setActiveCase(updatedCase)
    setEvents(updatedEvents)
  }

  const handleReassessWorkflow = async () => {
    if (!activeCaseId) return
    await api.reassessWorkflow(activeCaseId)
    await loadCaseDetails(activeCaseId)
  }

  const handleSendMessage = async (msg: string): Promise<{ answer: string; supporting_policy_sources?: PolicySearchResultItem[] }> => {
    if (!activeCaseId) return { answer: 'No active case selected' }
    return api.sendChatMessage(activeCaseId, msg)
  }

  const handleApproveAction = async (actionId: string) => {
    if (!activeCaseId) return
    await api.approveAction(actionId)
    const [updatedActions, updatedEvents, updatedCase] = await Promise.all([
      api.listActions(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
    ])
    setActions(updatedActions)
    setEvents(updatedEvents)
    setActiveCase(updatedCase)
  }

  const handleRejectAction = async (actionId: string, reason?: string) => {
    if (!activeCaseId) return
    await api.rejectAction(actionId, reason)
    const [updatedActions, updatedEvents, updatedCase] = await Promise.all([
      api.listActions(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
    ])
    setActions(updatedActions)
    setEvents(updatedEvents)
    setActiveCase(updatedCase)
  }

  const handleExecuteAction = async (actionId: string) => {
    if (!activeCaseId) return
    await api.executeAction(actionId)
    const [updatedActions, updatedEvents, updatedCase, updatedFollowUps] = await Promise.all([
      api.listActions(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
      api.listFollowUps(activeCaseId),
    ])
    setActions(updatedActions)
    setEvents(updatedEvents)
    setActiveCase(updatedCase)
    setFollowUps(updatedFollowUps)
  }

  const handleCreateAction = async (
    title: string,
    description: string,
    actionType: ActionType,
    payload: Record<string, any>
  ) => {
    if (!activeCaseId) return
    try {
      setErrorBanner(null)
      await api.createAction(activeCaseId, {
        title,
        description,
        action_type: actionType,
        payload,
      })
      const [updatedActions, updatedEvents, updatedCase] = await Promise.all([
        api.listActions(activeCaseId),
        api.getCaseTimeline(activeCaseId),
        api.getCase(activeCaseId),
      ])
      setActions(updatedActions)
      setEvents(updatedEvents)
      setActiveCase(updatedCase)
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to create action')
      throw err
    }
  }

  const handleSimulateResponse = async (payload: SimulatedResponseCreatePayload) => {
    if (!activeCaseId) return
    await api.simulateResponse(activeCaseId, payload)
    const [updatedResponses, updatedEvents, updatedCase] = await Promise.all([
      api.listSimulatedResponses(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
    ])
    setSimulatedResponses(updatedResponses)
    setEvents(updatedEvents)
    setActiveCase(updatedCase)
  }

  const handleProcessResponse = async (responseId: string): Promise<ResponseProcessingResult> => {
    if (!activeCaseId) throw new Error('No active case')
    const res = await api.processResponse(activeCaseId, responseId)
    const [updatedResponses, updatedEvents, updatedCase, updatedChecklist, updatedActions] = await Promise.all([
      api.listSimulatedResponses(activeCaseId),
      api.getCaseTimeline(activeCaseId),
      api.getCase(activeCaseId),
      api.getEvidenceChecklist(activeCaseId),
      api.listActions(activeCaseId),
    ])
    setSimulatedResponses(updatedResponses)
    setEvents(updatedEvents)
    setActiveCase(updatedCase)
    setChecklist(updatedChecklist)
    setActions(updatedActions)
    return res
  }

  return (
    <div className="min-h-screen bg-[#EAEDED] flex flex-col">
      {/* Navigation Bar */}
      <Navbar
        currentTab={currentTab}
        onTabChange={(tab) => {
          if (tab === 'case-details' && !activeCase && cases.length > 0) {
            handleSelectCase(cases[0].id)
          } else {
            setCurrentTab(tab as any)
          }
        }}
        onNewCaseClick={() => setIsCreateModalOpen(true)}
        activeCaseId={activeCaseId}
      />

      {/* Main Container */}
      <main className="w-full pt-28 pb-16 flex-1">
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8">
          {errorBanner && (
            <div className="mb-4 p-3 bg-[#FCF4F2] border border-[#F2BEB1] rounded text-xs text-[#B12704] flex items-center justify-between">
              <span>{errorBanner}</span>
              <button
                onClick={() => setErrorBanner(null)}
                className="font-bold underline ml-2"
              >
                Dismiss
              </button>
            </div>
          )}

          {loading && !activeCase && cases.length === 0 ? (
            <div className="text-center py-20 text-xs text-[#565959]">
              Connecting to ResolveAI backend and loading cases...
            </div>
          ) : (
            <>
              {currentTab === 'home' && (
                <Dashboard
                  cases={cases}
                  followUps={followUps}
                  onSelectCase={handleSelectCase}
                  onNewCaseClick={() => setIsCreateModalOpen(true)}
                />
              )}

              {currentTab === 'cases' && (
                <Dashboard
                  cases={cases}
                  followUps={followUps}
                  onSelectCase={handleSelectCase}
                  onNewCaseClick={() => setIsCreateModalOpen(true)}
                />
              )}

              {currentTab === 'case-details' && activeCase && (
                <CaseDetailsView
                  caseData={activeCase}
                  events={events}
                  evidenceList={evidenceList}
                  checklist={checklist}
                  actions={actions}
                  analysis={analysis}
                  simulatedResponses={simulatedResponses}
                  onBackToDashboard={() => setCurrentTab('home')}
                  onRefreshCase={() => loadCaseDetails(activeCase.id)}
                  onReassessWorkflow={handleReassessWorkflow}
                  onAddUserNote={handleAddUserNote}
                  onUploadEvidence={handleUploadEvidence}
                  onDeleteEvidence={handleDeleteEvidence}
                  onRunAnalysis={handleRunAnalysis}
                  onSendMessage={handleSendMessage}
                  onApproveAction={handleApproveAction}
                  onRejectAction={handleRejectAction}
                  onExecuteAction={handleExecuteAction}
                  onCreateAction={handleCreateAction}
                  onSimulateResponse={handleSimulateResponse}
                  onProcessResponse={handleProcessResponse}
                />
              )}

              {currentTab === 'follow-ups' && (
                <div className="bg-white rounded-lg p-6 shadow-sm border border-[#D5D9D9] space-y-4">
                  <h2 className="text-lg font-bold font-['Hanken_Grotesk'] text-[#0F1111]">
                    Scheduled Follow-ups Across All Cases ({followUps.length})
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {followUps.map((f) => (
                      <div
                        key={f.action_id}
                        onClick={() => handleSelectCase(f.case_id)}
                        className="p-4 bg-[#F9F9F9] rounded border border-[#D5D9D9] hover:border-[#007185] cursor-pointer space-y-2 text-xs transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[#0F1111]">{f.title}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              f.is_overdue
                                ? 'bg-[#FCF4F2] text-[#B12704]'
                                : 'bg-[#FFF8E7] text-[#C45500]'
                            }`}
                          >
                            {f.is_overdue ? 'Overdue' : 'Pending'}
                          </span>
                        </div>
                        <p className="text-[#565959]">
                          Case ID: #{f.case_id.slice(0, 8)} • Purpose: {f.purpose}
                        </p>
                        <p className="text-[#565959]">Due Date: {new Date(f.due_at).toLocaleDateString()}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Amazon Utility Footer */}
      <footer className="w-full bg-[#131921] text-white text-xs mt-auto">
        <div
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="w-full py-3 text-center bg-[#232F3E] hover:bg-[#37475A] font-semibold text-white cursor-pointer transition-colors border-b border-[#131921]"
        >
          Back to top
        </div>
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-[#8A97A9]">
          <div className="flex items-center gap-3">
            <span className="text-white font-bold font-['Hanken_Grotesk']">
              ResolveAI
            </span>
            <span>•</span>
            <span>Amazon Developer Hackathon Prototype (Simulated Engine)</span>
          </div>
          <p className="text-[11px] text-center md:text-right">
            Autonomous repair-resolution agent with simulated execution & provider response intake.
          </p>
        </div>
      </footer>

      {/* Case Creation Modal */}
      <CreateCaseModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateCase}
      />
    </div>
  )
}

export default App
