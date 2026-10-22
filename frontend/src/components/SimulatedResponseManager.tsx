import React, { useState } from 'react'
import {
  MessageSquare,
  CheckCircle,
  AlertTriangle,
  Play,
} from 'lucide-react'
import type {
  SimulatedResponse,
  SimulatedResponseCreatePayload,
  ResponseProcessingResult,
} from '../api/types'
import { AIProcessingIndicator } from './AIProcessingIndicator'

interface SimulatedResponseManagerProps {
  responses: SimulatedResponse[]
  onSimulate: (payload: SimulatedResponseCreatePayload) => Promise<void>
  onProcess: (responseId: string) => Promise<ResponseProcessingResult>
}

export const SimulatedResponseManager: React.FC<SimulatedResponseManagerProps> = ({
  responses,
  onSimulate,
  onProcess,
}) => {
  const [providerName, setProviderName] = useState('Official Service Center')
  const [responseText, setResponseText] = useState(
    'We acknowledge receipt of your notice regarding the repeat thermal failures on your device. We offer a full replacement unit or commercial resolution under applicable warranty terms.'
  )
  const [simulating, setSimulating] = useState(false)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<ResponseProcessingResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSimulateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!responseText.trim() || simulating) return

    setSimulating(true)
    setError(null)
    try {
      await onSimulate({
        provider_name: providerName.trim(),
        response_text: responseText.trim(),
      })
    } catch (err: any) {
      setError(err.message || 'Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  const handleProcessClick = async (responseId: string) => {
    if (processingId) return
    setProcessingId(responseId)
    setError(null)
    try {
      const res = await onProcess(responseId)
      setLastResult(res)
    } catch (err: any) {
      setError(err.message || 'Processing failed')
    } finally {
      setProcessingId(null)
    }
  }

  return (
    <div className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#EAEDED] gap-2">
        <div>
          <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111] flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-[#007185]" />
            <span>Simulated Provider Responses & Inbound Intake</span>
          </h2>
          <p className="text-xs text-[#565959]">
            Simulate incoming service centre or manufacturer replies and trigger AI reasoning.
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-[#FCF4F2] border border-[#F2BEB1] rounded p-2.5 text-xs text-[#B12704] flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Processed Outcome Callout */}
      {lastResult && (
        <div className="bg-[#F0F8F4] border border-[#9FD3BC] rounded-lg p-4 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[#067D62] flex items-center gap-1.5 text-sm">
              <CheckCircle className="w-4 h-4" />
              <span>Response Successfully Processed by ResolveAI</span>
            </span>
            {lastResult.suggested_case_status && (
              <span className="bg-white text-[#067D62] border border-[#9FD3BC] px-2 py-0.5 rounded text-[11px] font-bold">
                Status Updated to: {lastResult.suggested_case_status}
              </span>
            )}
          </div>

          <p className="text-[#0F1111] font-semibold">
            Next Recommendation: {lastResult.recommended_next_step}
          </p>

          <p className="text-[#565959] leading-relaxed">
            {lastResult.summary}
          </p>

          {lastResult.identified_commitments.length > 0 && (
            <div className="space-y-1">
              <span className="text-[#067D62] font-bold text-[11px]">Provider Commitments:</span>
              <ul className="list-disc list-inside text-[#0F1111] pl-1">
                {lastResult.identified_commitments.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {lastResult.requested_information.length > 0 && (
            <div className="space-y-1">
              <span className="text-[#565959] font-bold text-[11px]">Requested Information:</span>
              <ul className="list-disc list-inside text-[#0F1111] pl-1">
                {lastResult.requested_information.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {lastResult.evidence_still_needed.length > 0 && (
            <div className="text-[#B12704]">
              <span className="font-bold text-[11px]">Evidence Still Needed:</span>
              <ul className="list-disc list-inside pl-1">
                {lastResult.evidence_still_needed.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Simulator Form */}
      <form
        onSubmit={handleSimulateSubmit}
        className="bg-[#F3F3F3] p-4 rounded-lg border border-[#D5D9D9] space-y-3 text-xs"
      >
        <span className="font-bold text-[#0F1111] uppercase tracking-wider block">
          Inject Simulated Inbound Provider Response
        </span>

        <div className="space-y-3">
          <div>
            <label className="block font-bold text-[#0F1111] mb-1">Provider Name</label>
            <input
              type="text"
              value={providerName}
              onChange={(e) => setProviderName(e.target.value)}
              className="w-full h-8 px-2.5 bg-white border border-[#888C8C] rounded text-xs text-[#0F1111]"
            />
          </div>

          <div>
            <label className="block font-bold text-[#0F1111] mb-1">Inbound Message Body</label>
            <textarea
              rows={3}
              value={responseText}
              onChange={(e) => setResponseText(e.target.value)}
              disabled={simulating || processingId !== null}
              className="w-full p-2.5 bg-white border border-[#888C8C] rounded text-xs text-[#0F1111] disabled:opacity-50"
            />
          </div>
        </div>

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={simulating || processingId !== null}
            className="h-8 px-4 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            {simulating ? (
              <AIProcessingIndicator variant="inline" label="Injecting Reply" tone="yellow" />
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Inject Simulated Reply</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Response Processing In-Flight Indicator */}
      {processingId && (
        <AIProcessingIndicator
          variant="card"
          label="Processing Inbound Provider Response"
          sublabel="Extracting provider commitments, analyzing requested documents, and triggering orchestrator workflow reassessment..."
        />
      )}

      {/* Past Inbound Responses */}
      <div className="space-y-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-[#565959] block">
          Inbound Response Inbox ({responses.length})
        </span>

        {responses.length > 0 ? (
          <div className="space-y-3">
            {responses.map((resp) => {
              const isProcessing = processingId === resp.id

              return (
                <div
                  key={resp.id}
                  className="p-3.5 rounded border border-[#D5D9D9] bg-white space-y-2 text-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <div className="flex items-center gap-2">
                      <strong className="text-[#0F1111]">{resp.provider_name}</strong>
                      <span className="text-[10px] bg-[#EAEDED] px-1.5 py-0.2 rounded font-bold text-[#565959]">
                        {resp.source_type}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                          resp.status === 'PROCESSED'
                            ? 'bg-[#F0F8F4] text-[#067D62]'
                            : 'bg-[#FFF8E7] text-[#C45500]'
                        }`}
                      >
                        {resp.status}
                      </span>
                    </div>

                    <span className="text-[11px] text-[#565959]">
                      {new Date(resp.created_at).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-[#0F1111] whitespace-pre-wrap bg-[#F9F9F9] p-2.5 rounded border border-[#EAEDED] leading-relaxed">
                    {resp.response_text}
                  </p>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-[#565959]">
                      {resp.status === 'PROCESSED' ? (
                        <span className="text-[#067D62] font-semibold flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" />
                          <span>Processed into Case Context</span>
                        </span>
                      ) : (
                        <span className="text-[#C45500] font-semibold">
                          Unprocessed — Requires AI analysis
                        </span>
                      )}
                    </span>

                    {resp.status !== 'PROCESSED' && (
                      <button
                        onClick={() => handleProcessClick(resp.id)}
                        disabled={isProcessing || processingId !== null}
                        className="h-7 px-3 bg-[#FF9900] hover:bg-[#E68A00] text-[#0F1111] font-bold text-xs rounded border border-[#E68A00] shadow-xs flex items-center gap-1 transition-colors disabled:opacity-50"
                      >
                        {isProcessing ? (
                          <AIProcessingIndicator variant="inline" label="Processing" tone="yellow" />
                        ) : (
                          <span>Process Response</span>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-center py-5 text-xs text-[#565959]">
            No inbound provider responses yet. Use the simulator above to inject one.
          </div>
        )}
      </div>
    </div>
  )
}
