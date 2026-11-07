import { useState } from 'react'
import {
  Sparkles,
  Send,
  CheckCircle2,
  FileQuestion,
  BookOpen,
  Bot,
  User,
  AlertTriangle,
} from 'lucide-react'
import type { ActionType, CaseAnalysisResponse, PolicySearchResultItem } from '../api/types'
import { AIProcessingIndicator } from './AIProcessingIndicator'

const policyProvenanceLabel = (sourceType: string) => {
  switch (sourceType.toUpperCase()) {
    case 'OFFICIAL':
      return 'Official source'
    case 'ILLUSTRATIVE':
      return 'Illustrative standard'
    case 'GUIDANCE':
      return 'General guidance'
    default:
      return 'Source unverified'
  }
}

interface AssistantPanelProps {
  caseId: string
  analysis: CaseAnalysisResponse | null
  onRunAnalysis?: () => Promise<void>
  onSendMessage?: (msg: string) => Promise<{ answer: string; supporting_policy_sources?: PolicySearchResultItem[] }>
  onPrepareAction: (
    title: string,
    description: string,
    actionType: ActionType,
    payload: Record<string, any>
  ) => Promise<void>
  onOpenSimulateModal: () => void
}

interface ChatMessage {
  sender: 'user' | 'assistant'
  text: string
  time: string
  citations?: PolicySearchResultItem[]
}

export const AssistantPanel: React.FC<AssistantPanelProps> = ({
  analysis,
  onRunAnalysis,
  onSendMessage,
  onPrepareAction,
  onOpenSimulateModal,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'assistant',
      text: "I've reviewed the case context. Run an analysis or ask about the uploaded records, warranty terms, and consumer rights next steps.",
      time: 'Just now',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [draftingAction, setDraftingAction] = useState(false)
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null)
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null)

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!input.trim() || loading || !onSendMessage) return

    const userText = input.trim()
    setInput('')
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    setMessages((prev) => [...prev, { sender: 'user', text: userText, time: timeStr }])
    setLoading(true)

    try {
      const res = await onSendMessage(userText)
      setMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: res.answer,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          citations: res.supporting_policy_sources,
        },
      ])
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: `Error processing query: ${err.message || 'Unknown error'}`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleRunAnalysisClick = async () => {
    if (!onRunAnalysis || analyzing) return
    setAnalyzing(true)
    setAnalysisError(null)
    try {
      await onRunAnalysis()
    } catch (err: any) {
      setAnalysisError(err.message || 'Failed to generate case analysis.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleCreateSuggestedAction = async () => {
    if (!analysis || !analysis.recommended_next_step || draftingAction) return
    setDraftingAction(true)
    setActionSuccessMessage(null)
    setActionErrorMessage(null)

    try {
      const isFollowUp =
        analysis.recommended_next_step.toLowerCase().includes('follow') ||
        analysis.recommended_next_step.toLowerCase().includes('check-in') ||
        analysis.recommended_next_step.toLowerCase().includes('schedule')

      const actionType: ActionType = isFollowUp ? 'SCHEDULE_FOLLOW_UP' : 'SEND_MESSAGE'

      const title = `Proposed: ${analysis.recommended_next_step.slice(0, 80)}`
      const description = `Automated recommendation: ${analysis.summary}`

      let payload: Record<string, any> = {}
      if (actionType === 'SCHEDULE_FOLLOW_UP') {
        const targetDate = new Date()
        targetDate.setDate(targetDate.getDate() + 3)
        payload = {
          due_at: targetDate.toISOString(),
          purpose: `Follow-up regarding: ${analysis.recommended_next_step}`,
        }
      } else {
        payload = {
          recipient: 'Authorized Service Center Support / NCH',
          message_body: `Dear Support,\n\nRegarding my product repair claim:\n${analysis.summary}\n\nProposed Next Step: ${analysis.recommended_next_step}\n\nPlease advise promptly.`,
          is_simulated: true,
        }
      }

      await onPrepareAction(title, description, actionType, payload)
      setActionSuccessMessage(
        'Action proposed successfully! It is in PENDING_APPROVAL status and requires your explicit approval before execution.'
      )
    } catch (err: any) {
      setActionErrorMessage(err.message || 'Failed to prepare suggested action.')
    } finally {
      setDraftingAction(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-xs border border-[#E4E1E8] flex flex-col h-[750px] overflow-hidden">
      {/* Deep Indigo Header */}
      <div className="bg-[#312E81] text-white p-4 flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#D97757] flex items-center justify-center text-white shadow-xs">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-sm tracking-tight font-['Hanken_Grotesk'] text-white">
              ResolveAI Intelligence
            </h3>
            <p className="text-[11px] text-[#F0EEFA]">
              Grounded Consumer Guidance & Evidence Synthesis
            </p>
          </div>
        </div>

        {onRunAnalysis && (
          <button
            onClick={handleRunAnalysisClick}
            disabled={analyzing}
            className="h-8 px-3 bg-[#D97757] hover:bg-[#B85F44] text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {analyzing ? (
              <AIProcessingIndicator variant="inline" label="Analyzing" tone="coral" />
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-white" />
                <span>Run Analysis</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Latency & Mode Ribbon */}
      <div className="bg-[#F0EEFA] px-4 py-1.5 border-b border-[#E4E1E8] flex items-center justify-between text-[11px] text-[#625F70] shrink-0">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#3E7C68]" />
          <span>Case facts & statutory references</span>
        </span>
        <span className="font-medium text-[#312E81]">Local Persistent Engine</span>
      </div>

      {/* Scrollable Main Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Analyzing In-Flight Indicator */}
        {analyzing && (
          <AIProcessingIndicator
            variant="card"
            label="Analyzing Case Context & Warranty Policies"
            sublabel="Reviewing reported issues, evidence coverage, and statutory escalation thresholds..."
            tone="indigo"
          />
        )}

        {/* Analysis Error Alert */}
        {analysisError && !analyzing && (
          <div className="p-3 bg-[#F9ECEB] border border-[#B94A48]/30 rounded-lg text-xs text-[#B94A48] flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{analysisError}</span>
            </div>
            <button
              type="button"
              onClick={() => setAnalysisError(null)}
              className="text-[#625F70] hover:text-[#B94A48] text-xs font-bold px-1 cursor-pointer"
            >
              ×
            </button>
          </div>
        )}

        {/* Structured Analysis Recommendation Card */}
        {analysis && (
          <div className="bg-[#F7F6F3] border border-[#8B7BC4]/30 rounded-xl p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between pb-1.5 border-b border-[#E4E1E8]">
              <span className="flex items-center gap-1.5 text-[#312E81] font-bold text-xs">
                <CheckCircle2 className="w-4 h-4 text-[#3E7C68]" />
                <span>Case Analysis · Suggested Next Step</span>
              </span>
              <span className="text-[10px] bg-[#F0EEFA] text-[#312E81] px-2 py-0.5 rounded-full font-bold">
                {analysis.engine_mode} reasoning
              </span>
            </div>

            <div>
              <h4 className="text-sm font-bold text-[#27243A] font-['Hanken_Grotesk']">
                {analysis.recommended_next_step}
              </h4>
              <p className="text-xs text-[#625F70] mt-1 leading-relaxed">
                {analysis.summary}
              </p>
              {analysis.reasoning && (
                <p className="text-xs text-[#27243A] mt-1.5 leading-relaxed bg-white p-2.5 rounded-lg border border-[#E4E1E8]">
                  <strong>Reasoning:</strong> {analysis.reasoning}
                </p>
              )}
            </div>

            {/* Checklist summary */}
            {analysis.missing_information && analysis.missing_information.length > 0 && (
              <div className="p-2.5 bg-[#FBF4E8] rounded-lg border border-[#E7B76A]/40 space-y-1">
                <span className="font-bold text-[#A06C18] flex items-center gap-1 text-[11px]">
                  <FileQuestion className="w-3.5 h-3.5" />
                  <span>Missing Evidence Checklist Items:</span>
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-[#625F70] text-[11px]">
                  {analysis.missing_information.map((info, i) => (
                    <li key={i}>{info.item}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Citations */}
            {analysis.supporting_policy_sources && analysis.supporting_policy_sources.length > 0 && (
              <div className="space-y-1 pt-1 border-t border-[#E4E1E8]">
                <span className="text-[11px] font-bold text-[#625F70] flex items-center gap-1">
                  <BookOpen className="w-3 h-3 text-[#312E81]" />
                  <span>Grounded Policy References:</span>
                </span>
                <div className="space-y-1">
                  {analysis.supporting_policy_sources.map((cite) => (
                    <div
                      key={cite.source_id}
                      className="p-2 bg-white rounded border border-[#E4E1E8] text-[11px]"
                    >
                      <div className="flex items-center justify-between">
                        <strong className="text-[#312E81]">{cite.source_title}</strong>
                        <span className="text-[10px] text-[#625F70]">
                          {policyProvenanceLabel(cite.source_type)}
                        </span>
                      </div>
                      <p className="text-[#625F70] mt-0.5 italic">"{cite.passage}"</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Feedback Messages */}
            {actionSuccessMessage && (
              <div className="p-2.5 bg-[#EAF3EF] border border-[#3E7C68]/30 rounded-lg text-xs text-[#3E7C68] font-semibold">
                {actionSuccessMessage}
              </div>
            )}
            {actionErrorMessage && (
              <div className="p-2.5 bg-[#F9ECEB] border border-[#B94A48]/30 rounded-lg text-xs text-[#B94A48]">
                {actionErrorMessage}
              </div>
            )}

            {/* Propose Action Button */}
            <div className="pt-2 flex flex-wrap gap-2">
              <button
                onClick={handleCreateSuggestedAction}
                disabled={draftingAction}
                className="px-3.5 py-1.5 bg-[#312E81] hover:bg-[#262366] text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
              >
                {draftingAction ? (
                  <AIProcessingIndicator variant="inline" label="Drafting" tone="indigo" />
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Draft Action from Recommendation</span>
                  </>
                )}
              </button>

              <button
                onClick={onOpenSimulateModal}
                className="px-3 py-1.5 bg-white border border-[#E4E1E8] hover:bg-[#F0EEFA] text-[#27243A] text-xs font-semibold rounded-lg transition-colors cursor-pointer"
              >
                Simulate Inbound Reply
              </button>
            </div>
          </div>
        )}

        {/* Chat Messages */}
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-xl p-3 space-y-1.5 text-xs ${
                m.sender === 'user'
                  ? 'bg-[#312E81] text-white rounded-tr-none'
                  : 'bg-[#F7F6F3] text-[#27243A] border border-[#E4E1E8] rounded-tl-none'
              }`}
            >
              <div className="flex items-center gap-1.5 text-[10px] opacity-75 border-b border-black/5 pb-1">
                {m.sender === 'user' ? (
                  <>
                    <User className="w-3 h-3 text-white" />
                    <span className="font-semibold">Consumer</span>
                  </>
                ) : (
                  <>
                    <Bot className="w-3 h-3 text-[#312E81]" />
                    <span className="font-semibold text-[#312E81]">ResolveAI</span>
                  </>
                )}
                <span className="ml-auto">{m.time}</span>
              </div>
              <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>

              {m.citations && m.citations.length > 0 && (
                <div className="mt-2 pt-1.5 border-t border-[#E4E1E8] space-y-1">
                  <span className="text-[10px] font-bold text-[#625F70] uppercase tracking-wider">
                    Cited References:
                  </span>
                  {m.citations.map((c) => (
                    <div key={c.source_id} className="text-[10px] text-[#312E81] italic">
                      <span>• {c.source_title} — {policyProvenanceLabel(c.source_type)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Chat In-Flight AI Response Pending Indicator */}
        {loading && (
          <AIProcessingIndicator
            variant="message"
            label="Reviewing policy references and case evidence"
            sublabel="Examining case events, repair history, and statutory guidance..."
            tone="indigo"
          />
        )}
      </div>

      {/* Suggested Quick Prompts */}
      <div className="px-3.5 py-1.5 bg-[#F0EEFA] border-t border-[#E4E1E8] flex items-center gap-1.5 overflow-x-auto no-scrollbar shrink-0">
        <button
          onClick={() => {
            setInput('What are my escalation options after 2 failed repairs?')
          }}
          className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-[#E4E1E8] text-[11px] text-[#27243A] hover:bg-[#E4E0F5] transition-colors cursor-pointer"
        >
          2 failed repairs options?
        </button>
        <button
          onClick={() => {
            setInput('Can I request a replacement under manufacturer warranty?')
          }}
          className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-[#E4E1E8] text-[11px] text-[#27243A] hover:bg-[#E4E0F5] transition-colors cursor-pointer"
        >
          Warranty replacement?
        </button>
        <button
          onClick={() => {
            setInput('What evidence is recommended for National Consumer Helpline escalation?')
          }}
          className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-[#E4E1E8] text-[11px] text-[#27243A] hover:bg-[#E4E0F5] transition-colors cursor-pointer"
        >
          NCH grievance evidence?
        </button>
      </div>

      {/* Input Box */}
      <form
        onSubmit={handleSend}
        className="p-3 bg-white border-t border-[#E4E1E8] flex items-center gap-2 shrink-0"
      >
        <input
          type="text"
          placeholder="Ask about case records, warranty terms, or possible next steps..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          className="flex-1 h-9 px-3 border border-[#E4E1E8] rounded-md text-xs text-[#27243A] focus:outline-none focus:border-[#5B4B8A] focus:ring-2 focus:ring-[#8B7BC4]/30 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="h-9 px-3.5 bg-[#312E81] hover:bg-[#262366] text-white rounded-md shadow-xs flex items-center justify-center transition-colors disabled:opacity-50 cursor-pointer"
          title="Send query"
        >
          <Send className="w-4 h-4 text-white" />
        </button>
      </form>
    </div>
  )
}
