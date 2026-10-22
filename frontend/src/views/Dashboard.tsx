import React from 'react'
import {
  Wrench,
  CheckCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  PlusCircle,
  FileText,
  Calendar,
} from 'lucide-react'
import type { Case, FollowUpItem } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'

interface DashboardProps {
  cases: Case[]
  followUps: FollowUpItem[]
  onSelectCase: (caseId: string) => void
  onNewCaseClick: () => void
}

export const Dashboard: React.FC<DashboardProps> = ({
  cases,
  followUps,
  onSelectCase,
  onNewCaseClick,
}) => {
  const activeCases = cases.filter(
    (c) => c.status !== 'RESOLVED' && c.status !== 'CLOSED'
  )
  const resolvedCases = cases.filter((c) => c.status === 'RESOLVED')
  const actionRequiredCases = cases.filter(
    (c) => c.status === 'ACTION_READY' || c.status === 'NEW' || c.status === 'FOLLOW_UP_DUE'
  )

  // Primary attention case (first action-ready case, or first active case)
  const priorityCase = actionRequiredCases[0] || activeCases[0] || cases[0]

  return (
    <div className="space-y-6">
      {/* Hero Banner Strip - Exactly as in Stitch Prototype */}
      <section className="bg-white rounded-lg shadow-sm border border-[#D5D9D9] p-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="max-w-2xl space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#FFD814] text-[#0F1111] text-[11px] font-bold uppercase tracking-wide">
              ResolveAI Agent • Hackathon Demo
            </span>
            <span className="text-xs text-[#565959] flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-[#067D62]" />
              Operational Engine Active
            </span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold font-['Hanken_Grotesk'] text-[#0F1111] tracking-tight">
            Resolve your product issues, step by step.
          </h1>
          <p className="text-sm text-[#565959] leading-relaxed">
            Keep your repair history, evidence, next steps, and follow-ups together in one place. Powered by consumer guidance intelligence.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0 w-full sm:w-auto">
          <button
            onClick={onNewCaseClick}
            className="w-full sm:w-auto px-5 py-2.5 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center justify-center gap-2 transition-all"
          >
            <PlusCircle className="w-4 h-4 text-[#0F1111]" />
            <span>Start a New Case</span>
          </button>
        </div>
      </section>

      {/* Metric Statistics Strip */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow-sm border border-[#D5D9D9] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#565959] uppercase block">
              Active Cases
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#0F1111] mt-0.5 block">
              {activeCases.length}
            </span>
            <span className="text-xs text-[#007185] font-bold">
              {actionRequiredCases.length} In Progress
            </span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#F3F3F3] flex items-center justify-center text-[#0F1111]">
            <Wrench className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow-sm border border-[#D5D9D9] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#565959] uppercase block">
              Resolved Claims
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#0F1111] mt-0.5 block">
              {resolvedCases.length}
            </span>
            <span className="text-xs text-[#067D62] font-bold">Closed With Outcome</span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#F0F8F4] flex items-center justify-center text-[#067D62]">
            <CheckCircle className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow-sm border border-[#D5D9D9] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#565959] uppercase block">
              Scheduled Follow-ups
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#0F1111] mt-0.5 block">
              {followUps.length}
            </span>
            <span className="text-xs text-[#C45500] font-bold">
              {followUps.filter((f) => f.is_overdue).length} Overdue
            </span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#FFF8E7] flex items-center justify-center text-[#C45500]">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow-sm border border-[#D5D9D9] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#565959] uppercase block">
              Rights Guidance
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#0F1111] mt-0.5 block">
              Active
            </span>
            <span className="text-xs text-[#067D62] font-bold">Consumer Guidance (India)</span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#F0F8F4] flex items-center justify-center text-[#067D62]">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>
      </section>

      {/* Attention Required Banner (Featured Order-Style Box from Stitch) */}
      {priorityCase && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#B12704] animate-pulse" />
              <h2 className="text-lg font-bold font-['Hanken_Grotesk'] text-[#0F1111]">
                Active Repair Case
              </h2>
              <StatusBadge status={priorityCase.status} size="sm" />
            </div>

            <button
              onClick={() => onSelectCase(priorityCase.id)}
              className="text-xs font-semibold text-[#007185] hover:text-[#C7511F] flex items-center gap-1"
            >
              <span>Open Case Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Amazon Order Card Style Case Box */}
          <div className="bg-white rounded-lg shadow-sm border border-[#D5D9D9] overflow-hidden">
            {/* Order-Style Header Strip */}
            <div className="bg-[#F3F3F3] p-4 flex flex-wrap items-center justify-between gap-4 text-xs border-b border-[#D5D9D9]">
              <div className="flex flex-wrap items-center gap-6">
                <div>
                  <span className="text-[11px] text-[#565959] uppercase block">
                    Created Date
                  </span>
                  <span className="font-bold text-[#0F1111]">
                    {new Date(priorityCase.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-[#565959] uppercase block">
                    Case ID
                  </span>
                  <span className="font-mono font-bold text-[#0F1111]">
                    #{priorityCase.id.slice(0, 8)}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-[#565959] uppercase block">
                    Product
                  </span>
                  <span className="font-bold text-[#0F1111]">
                    {priorityCase.product_name}
                  </span>
                </div>
              </div>

              <div>
                <StatusBadge status={priorityCase.status} />
              </div>
            </div>

            {/* Main Content Area */}
            <div className="p-5 flex flex-col md:flex-row items-start justify-between gap-6">
              <div className="flex-1 space-y-2">
                <h3 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111]">
                  {priorityCase.title}
                </h3>
                <p className="text-xs text-[#0F1111] leading-relaxed line-clamp-3">
                  {priorityCase.issue_description}
                </p>
              </div>

              <div className="shrink-0 flex flex-col gap-2 w-full sm:w-auto">
                <button
                  onClick={() => onSelectCase(priorityCase.id)}
                  className="px-5 py-2.5 bg-[#FFD814] hover:bg-[#F7CA00] text-[#0F1111] font-bold text-xs rounded border border-[#FCD200] shadow-sm flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>Review Evidence & Actions</span>
                  <ArrowRight className="w-4 h-4 text-[#0F1111]" />
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* All Cases Table Strip */}
      <section className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#EAEDED]">
          <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#007185]" />
            <span>All Repair & Resolution Cases ({cases.length})</span>
          </h2>

          <button
            onClick={onNewCaseClick}
            className="text-xs text-[#007185] hover:text-[#C7511F] font-semibold flex items-center gap-1"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Add Another Case</span>
          </button>
        </div>

        {cases.length > 0 ? (
          <div className="border border-[#D5D9D9] rounded-lg overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#F3F3F3] text-[#565959] border-b border-[#D5D9D9] font-bold">
                  <th className="py-2.5 px-3">Case ID</th>
                  <th className="py-2.5 px-3">Title & Product</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Workspace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EAEDED]">
                {cases.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => onSelectCase(c.id)}
                    className="hover:bg-[#F9F9F9] transition-colors cursor-pointer"
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-[#0F1111]">
                      #{c.id.slice(0, 8)}
                    </td>
                    <td className="py-2.5 px-3">
                      <p className="font-bold text-[#0F1111]">{c.title}</p>
                      <p className="text-[11px] text-[#565959]">{c.product_name}</p>
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={c.status} size="sm" />
                    </td>
                    <td className="py-2.5 px-3 text-[#565959]">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="text-[#007185] hover:underline font-semibold flex items-center justify-end gap-1">
                        <span>Open</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-xs text-[#565959]">
            No cases created yet. Click "Start a New Case" to begin.
          </div>
        )}
      </section>

      {/* Follow-ups Widget Strip */}
      {followUps.length > 0 && (
        <section className="bg-white rounded-lg p-5 shadow-sm border border-[#D5D9D9] space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#EAEDED]">
            <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#0F1111] flex items-center gap-2">
              <Calendar className="w-5 h-5 text-[#C45500]" />
              <span>Upcoming Scheduled Follow-up Reminders</span>
            </h2>
            <span className="text-xs text-[#565959]">
              {followUps.length} Pending Actions
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {followUps.map((f) => (
              <div
                key={f.action_id}
                onClick={() => onSelectCase(f.case_id)}
                className="p-3 bg-[#F9F9F9] rounded border border-[#D5D9D9] hover:border-[#007185] transition-colors cursor-pointer space-y-1 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#0F1111] truncate">{f.title}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                      f.is_overdue
                        ? 'bg-[#FCF4F2] text-[#B12704]'
                        : 'bg-[#FFF8E7] text-[#C45500]'
                    }`}
                  >
                    {f.is_overdue ? 'Overdue' : 'Pending'}
                  </span>
                </div>
                <p className="text-[11px] text-[#565959]">
                  Purpose: {f.purpose} • Due: {new Date(f.due_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
