import { useState } from 'react'
import {
  Sparkles,
  Send,
  CheckCircle2,
  FileQuestion,
  BookOpen,
  ArrowRight,
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
      return 'Illustrative demo · not official policy'
    case 'GUIDANCE':
      return 'General guidance'
    default:
      return 'Source type unverified'
  }
}

interface AssistantPanelProps {
  caseId: string
  analysis: CaseAnalysisResponse | null
  onRunAnalysis: () => Promise<void>
  onSendMessage: (msg: string) => Promise<{ answer: string; supporting_policy_sources?: PolicySearchResultItem[] }>
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
      text: "I've reviewed the case context. Run an analysis or ask about the uploaded records, warranty terms, and possible next steps.",
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
    if (!input.trim() || loading) return

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
    if (analyzing) return
    setAnalyzing(true)
    setAnalysisError(null)
    try {
      await onRunAnalysis()
    } catch (err: any) {
      setAnalysisError(err.message || 'Failed to complete case analysis.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleDraftActionClick = async () => {
    if (!analysis || draftingAction) return
    setDraftingAction(true)
    setActionErrorMessage(null)
    setActionSuccessMessage(null)

    try {
      const rawTitle = analysis.recommended_next_step.trim()
      const title = rawTitle.length > 250 ? `${rawTitle.slice(0, 247)}...` : rawTitle

      const rawSubject = `Case follow-up: ${rawTitle}`
      const subject = rawSubject.length > 250 ? `${rawSubject.slice(0, 247)}...` : rawSubject

      const description = analysis.reasoning
        ? `${analysis.summary}\n\nReasoning: ${analysis.reasoning}`
        : analysis.summary

      const messageParts = [
        analysis.summary,
        analysis.reasoning ? `Justification: ${analysis.reasoning}` : '',
        analysis.suggested_action ? `Proposed Action: ${analysis.suggested_action}` : '',
      ].filter(Boolean)

      const payload = {
        recipient: 'Official Service Provider',
        subject,
        message_body: messageParts.join('\n\n') || analysis.summary,
        is_simulated: true,
      }

      await onPrepareAction(title, description, 'SEND_MESSAGE', payload)
      setActionSuccessMessage('Action successfully drafted and added to Agent Actions for approval.')
    } catch (err: any) {
      setActionErrorMessage(err.message || 'Failed to draft action from recommendation.')
    } finally {
      setDraftingAction(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-[#D5D9D9] shadow-sm flex flex-col h-full min-h-[640px] overflow-hidden">
      {/* Top Header Bar */}
      <div className="bg-[#232F3E] text-white p-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-[#FFD814] flex items-center justify-center text-[#131921] font-bold shadow-sm">
            <Bot className="w-5 h-5 text-[#131921]" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold font-['Hanken_Grotesk'] text-white">
                ResolveAI Assistant
              </span>
              <span className="bg-[#FFD814]/20 text-[#FFE16B] border border-[#FFE16B]/40 px-1.5 py-0.2 rounded text-[10px] font-bold uppercase">
                {analysis?.engine_mode ? `${analysis.engine_mode} mode` : 'Demo Mode'}
              </span>
            </div>
            <span className="text-[11px] text-[#8A97A9]">
              Policy & Repair Reasoning Engine
            </span>
          </div>
        </div>

        <button
          onClick={handleRunAnalysisClick}
          disabled={analyzing}
          className="h-7 px-2.5 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-[11px] rounded border border-[#FCD200] shadow-sm flex items-center gap-1 transition-colors disabled:opacity-50"
        >
          {analyzing ? (
            <AIProcessingIndicator variant="inline" label="Analyzing" tone="yellow" />
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-[#0F1111]" />
              <span>Run Case Analysis</span>
            </>
          )}
        </button>
      </div>

      {/* Latency & Mode Ribbon */}
      <div className="bg-[#F3F3F3] px-3.5 py-1.5 border-b border-[#D5D9D9] flex items-center justify-between text-[11px] text-[#565959] shrink-0">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#067D62]" />
          <span>Case analysis and policy references</span>
        </span>
        <span>Local Persistent SQLite</span>
      </div>

      {/* Scrollable Main Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Analyzing In-Flight Indicator */}
        {analyzing && (
          <AIProcessingIndicator
            variant="card"
            label="Analyzing Case Context & Warranty Policies"
            sublabel="Reviewing the reported issue, evidence coverage, and available policy references..."
          />
        )}

        {/* Analysis Error Alert */}
        {analysisError && !analyzing && (
          <div className="p-3 bg-[#FCF4F2] border border-[#F2BEB1] rounded text-xs text-[#B12704] flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{analysisError}</span>
            </div>
            <button
              type="button"
              onClick={() => setAnalysisError(null)}
              className="text-[#565959] hover:text-[#B12704] text-xs font-bold px-1"
            >
              ×
            </button>
          </div>
        )}

        {/* Structured Analysis Recommendation Card */}
        {analysis && (
          <div className="bg-[#F9F9F9] border border-[#007185]/40 rounded-lg p-3.5 space-y-3 shadow-xs">
            <div className="flex items-center justify-between pb-1.5 border-b border-[#D5D9D9]">
              <span className="flex items-center gap-1.5 text-[#007185] font-bold text-xs">
                <CheckCircle2 className="w-4 h-4 text-[#007185]" />
                <span>Case Analysis · Suggested Next Step</span>
              </span>
              <span className="text-[10px] bg-[#FFD814]/30 text-[#0F1111] px-1.5 py-0.5 rounded font-bold">
                {analysis.engine_mode} reasoning
              </span>
            </div>

            <div>
              <h4 className="text-sm font-bold text-[#0F1111] font-['Hanken_Grotesk']">
                {analysis.recommended_next_step}
              </h4>
              <p className="text-xs text-[#565959] mt-1 leading-relaxed">
                {analysis.summary}
              </p>
              {analysis.reasoning && (
                <p className="text-xs text-[#0F1111] mt-1.5 leading-relaxed bg-white p-2 rounded border border-[#EAEDED]">
                  <strong>Reasoning:</strong> {analysis.reasoning}
                </p>
              )}
            </div>

            {/* Known Facts & Missing Info */}
            <div className="space-y-2 bg-white p-2.5 rounded border border-[#D5D9D9]">
              {analysis.known_facts.length > 0 && (
                <div>
                  <span className="text-[11px] font-bold text-[#067D62] flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Case Facts &amp; Evidence Notes:</span>
                  </span>
                  <ul className="list-disc list-inside text-[11px] text-[#0F1111] pl-1 space-y-0.5 mt-0.5">
                    {analysis.known_facts.map((factItem, i) => (
                      <li key={i}>
                        <span className="font-semibold">{factItem.category}:</span> {factItem.fact}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {analysis.missing_information.length > 0 && (
                <div>
                  <span className="text-[11px] font-bold text-[#B12704] flex items-center gap-1">
                    <FileQuestion className="w-3.5 h-3.5" />
                    <span>Missing Information to Address:</span>
                  </span>
                  <ul className="list-disc list-inside text-[11px] text-[#B12704] pl-1 space-y-0.5 mt-0.5">
                    {analysis.missing_information.map((item, i) => (
                      <li key={i}>
                        <span className="font-semibold">{item.item}:</span> {item.impact}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Policy and reference sources */}
            {analysis.supporting_policy_sources.length > 0 && (
              <div className="bg-white p-2.5 rounded border border-[#D5D9D9] space-y-1">
                <span className="text-[11px] font-bold text-[#0F1111] flex items-center gap-1">
                  <BookOpen className="w-3.5 h-3.5 text-[#007185]" />
                  <span>Policy &amp; Reference Sources:</span>
                </span>
                {analysis.supporting_policy_sources.map((c) => (
                  <div key={c.source_id} className="text-[11px] border-l-2 border-[#007185] pl-2 py-0.5">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <strong className="text-[#0F1111]">{c.source_title}</strong>
                      <span className="rounded bg-[#F3F3F3] px-1.5 py-0.5 text-[9px] font-semibold text-[#565959]">
                        {policyProvenanceLabel(c.source_type)}
                      </span>
                      {c.jurisdiction && <span>({c.jurisdiction})</span>}
                    </div>
                    <p className="text-[#565959] text-[10px] mt-0.5 italic">
                      "{c.passage}"
                    </p>
                  </div>
                ))}
              </div>
            )}

            {/* Action Trigger Buttons */}
            <div className="pt-1 flex flex-col sm:flex-row items-center gap-2">
              <button
                type="button"
                onClick={handleDraftActionClick}
                disabled={draftingAction || analyzing}
                className="w-full sm:flex-1 h-8 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {draftingAction ? (
                  <AIProcessingIndicator variant="inline" label="Drafting Action" tone="yellow" />
                ) : (
                  <>
                    <span>Draft Action from Recommendation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={onOpenSimulateModal}
                disabled={draftingAction || analyzing}
                className="w-full sm:w-auto h-8 px-3 bg-white hover:bg-[#F3F3F3] text-[#007185] font-semibold text-xs rounded border border-[#D5D9D9] shadow-xs flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
              >
                <span>Simulate Response</span>
              </button>
            </div>

            {/* Inline Action Feedback Alerts */}
            {actionSuccessMessage && (
              <div className="p-2.5 bg-[#F0F8F5] border border-[#067D62]/40 rounded text-xs text-[#067D62] flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 font-medium">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-[#067D62]" />
                  <span>{actionSuccessMessage}</span>
                </span>
                <button
                  type="button"
                  onClick={() => setActionSuccessMessage(null)}
                  className="text-[#565959] hover:text-[#0F1111] text-xs font-bold px-1"
                >
                  ×
                </button>
              </div>
            )}

            {actionErrorMessage && (
              <div className="p-2.5 bg-[#FCF4F2] border border-[#F2BEB1] rounded text-xs text-[#B12704] flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 font-medium">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-[#B12704]" />
                  <span>{actionErrorMessage}</span>
                </span>
                <button
                  type="button"
                  onClick={() => setActionErrorMessage(null)}
                  className="text-[#565959] hover:text-[#B12704] text-xs font-bold px-1"
                >
                  ×
                </button>
              </div>
            )}
          </div>
        )}

        {/* Chat Messages */}
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[88%] p-3 rounded-lg text-xs leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-[#F3F3F3] text-[#0F1111] rounded-tr-none border border-[#D5D9D9]'
                  : 'bg-white text-[#0F1111] rounded-tl-none border border-[#D5D9D9] shadow-xs'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1 text-[10px] text-[#565959]">
                {m.sender === 'user' ? (
                  <>
                    <User className="w-3 h-3 text-[#565959]" />
                    <span className="font-semibold">Consumer</span>
                  </>
                ) : (
                  <>
                    <Bot className="w-3 h-3 text-[#007185]" />
                    <span className="font-semibold text-[#007185]">ResolveAI Assistant</span>
                  </>
                )}
                <span className="ml-auto">{m.time}</span>
              </div>
              <p className="whitespace-pre-wrap">{m.text}</p>

              {m.citations && m.citations.length > 0 && (
                <div className="mt-2 pt-1.5 border-t border-[#EAEDED] space-y-1">
                  <span className="text-[10px] font-bold text-[#565959] uppercase">
                    Cited References:
                  </span>
                  {m.citations.map((c) => (
                    <div key={c.source_id} className="text-[10px] text-[#007185] italic">
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
            sublabel="Examining case events, repair history, and available guidance..."
          />
        )}
      </div>

      {/* Suggested Quick Prompts */}
      <div className="px-3.5 py-1.5 bg-[#F3F3F3] border-t border-[#D5D9D9] flex items-center gap-1.5 overflow-x-auto no-scrollbar shrink-0">
        <button
          onClick={() => {
            setInput('What are my escalation options after 2 failed repairs?')
          }}
          className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-[#D5D9D9] text-[11px] text-[#0F1111] hover:bg-[#E8E8E7] transition-colors"
        >
          2 failed repairs options?
        </button>
        <button
          onClick={() => {
            setInput('Can I request a replacement under manufacturer warranty?')
          }}
          className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-[#D5D9D9] text-[11px] text-[#0F1111] hover:bg-[#E8E8E7] transition-colors"
        >
          Warranty replacement?
        </button>
        <button
          onClick={() => {
            setInput('What evidence is recommended for National Consumer Helpline escalation?')
          }}
          className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-[#D5D9D9] text-[11px] text-[#0F1111] hover:bg-[#E8E8E7] transition-colors"
        >
          NCH grievance evidence?
        </button>
      </div>

      {/* Input Box */}
      <form
        onSubmit={handleSend}
        className="p-3 bg-white border-t border-[#D5D9D9] flex items-center gap-2 shrink-0"
      >
        <input
          type="text"
          placeholder="Ask about case records, warranty terms, or possible next steps..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          className="flex-1 h-9 px-3 border border-[#888C8C] rounded text-xs text-[#0F1111] focus:outline-none focus:border-[#007185] focus:ring-2 focus:ring-[#007185]/20 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="h-9 px-3 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] rounded border border-[#FCD200] shadow-sm flex items-center justify-center transition-colors disabled:opacity-50"
          title="Send query"
        >
          <Send className="w-4 h-4 text-[#0F1111]" />
        </button>
      </form>
    </div>
  )
}
