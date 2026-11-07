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
  Mic,
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
      {/* Dashboard introduction banner */}
      <section className="bg-white rounded-xl shadow-xs border border-[#E4E1E8] p-6 lg:p-8 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="max-w-2xl space-y-2.5">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#F0EEFA] text-[#312E81] text-[11px] font-bold uppercase tracking-wider">
              ResolveAI • Consumer Repair Workspace
            </span>
            <span className="text-xs text-[#625F70] flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-[#3E7C68]" />
              Voice-First Intake Ready
            </span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold font-['Hanken_Grotesk'] text-[#27243A] tracking-tight">
            Resolve recurring repair issues, step by step.
          </h1>
          <p className="text-sm text-[#625F70] leading-relaxed">
            Record or describe product defects, organize purchase and service job sheets, and let ResolveAI build grounded escalation strategies based on consumer rights.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 w-full sm:w-auto">
          <button
            onClick={onNewCaseClick}
            className="w-full sm:w-auto px-5 py-2.5 bg-[#D97757] hover:bg-[#B85F44] text-white font-bold text-xs rounded-lg shadow-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <Mic className="w-4 h-4" />
            <span>Start a New Case</span>
          </button>
        </div>
      </section>

      {/* Metric Statistics Strip */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl shadow-xs border border-[#E4E1E8] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#625F70] uppercase tracking-wider block">
              Active Cases
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#27243A] mt-0.5 block">
              {activeCases.length}
            </span>
            <span className="text-xs text-[#5B4B8A] font-semibold">
              {actionRequiredCases.length} In Progress
            </span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#F0EEFA] flex items-center justify-center text-[#312E81]">
            <Wrench className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl shadow-xs border border-[#E4E1E8] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#625F70] uppercase tracking-wider block">
              Resolved Claims
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#27243A] mt-0.5 block">
              {resolvedCases.length}
            </span>
            <span className="text-xs text-[#3E7C68] font-semibold">Closed With Outcome</span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#EAF3EF] flex items-center justify-center text-[#3E7C68]">
            <CheckCircle className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl shadow-xs border border-[#E4E1E8] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#625F70] uppercase tracking-wider block">
              Scheduled Follow-ups
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#27243A] mt-0.5 block">
              {followUps.length}
            </span>
            <span className="text-xs text-[#E7B76A] font-semibold">
              {followUps.filter((f) => f.is_overdue).length} Overdue
            </span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#FBF4E8] flex items-center justify-center text-[#E7B76A]">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl shadow-xs border border-[#E4E1E8] flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-[#625F70] uppercase tracking-wider block">
              Rights Guidance
            </span>
            <span className="text-2xl font-bold font-['Hanken_Grotesk'] text-[#27243A] mt-0.5 block">
              Active
            </span>
            <span className="text-xs text-[#3E7C68] font-semibold">Consumer Protection Rules</span>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#EAF3EF] flex items-center justify-center text-[#3E7C68]">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>
      </section>

      {/* Priority active case */}
      {priorityCase && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#D97757] animate-pulse" />
              <h2 className="text-lg font-bold font-['Hanken_Grotesk'] text-[#27243A]">
                Active Repair Case
              </h2>
              <StatusBadge status={priorityCase.status} size="sm" />
            </div>

            <button
              onClick={() => onSelectCase(priorityCase.id)}
              className="text-xs font-semibold text-[#312E81] hover:text-[#5B4B8A] flex items-center gap-1 cursor-pointer"
            >
              <span>Open Case Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Priority case card */}
          <div className="bg-white rounded-xl shadow-xs border border-[#E4E1E8] overflow-hidden">
            {/* Header Strip */}
            <div className="bg-[#F0EEFA] p-4 flex flex-wrap items-center justify-between gap-4 text-xs border-b border-[#E4E1E8]">
              <div className="flex flex-wrap items-center gap-6">
                <div>
                  <span className="text-[11px] text-[#625F70] uppercase tracking-wider block">
                    Created Date
                  </span>
                  <span className="font-bold text-[#27243A]">
                    {new Date(priorityCase.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-[#625F70] uppercase tracking-wider block">
                    Case ID
                  </span>
                  <span className="font-mono font-bold text-[#27243A]">
                    #{priorityCase.id.slice(0, 8)}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-[#625F70] uppercase tracking-wider block">
                    Product
                  </span>
                  <span className="font-bold text-[#27243A]">
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
                <h3 className="text-base font-bold font-['Hanken_Grotesk'] text-[#27243A]">
                  {priorityCase.title}
                </h3>
                <p className="text-xs text-[#625F70] leading-relaxed line-clamp-3">
                  {priorityCase.issue_description}
                </p>
              </div>

              <div className="shrink-0 flex flex-col gap-2 w-full sm:w-auto">
                <button
                  onClick={() => onSelectCase(priorityCase.id)}
                  className="px-5 py-2.5 bg-[#312E81] hover:bg-[#262366] text-white font-bold text-xs rounded-lg shadow-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span>Review Evidence & Actions</span>
                  <ArrowRight className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* All Cases Table Strip */}
      <section className="bg-white rounded-xl p-5 shadow-xs border border-[#E4E1E8] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#E4E1E8]">
          <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#27243A] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#5B4B8A]" />
            <span>All Repair & Resolution Cases ({cases.length})</span>
          </h2>

          <button
            onClick={onNewCaseClick}
            className="text-xs text-[#312E81] hover:text-[#5B4B8A] font-semibold flex items-center gap-1 cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Start a Case</span>
          </button>
        </div>

        {cases.length > 0 ? (
          <div className="border border-[#E4E1E8] rounded-lg overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#F7F6F3] text-[#625F70] border-b border-[#E4E1E8] font-bold">
                  <th className="py-2.5 px-3">Case ID</th>
                  <th className="py-2.5 px-3">Title & Product</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Workspace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E1E8]">
                {cases.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => onSelectCase(c.id)}
                    className="hover:bg-[#F0EEFA]/50 transition-colors cursor-pointer"
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-[#27243A]">
                      #{c.id.slice(0, 8)}
                    </td>
                    <td className="py-2.5 px-3">
                      <p className="font-bold text-[#27243A]">{c.title}</p>
                      <p className="text-[11px] text-[#625F70]">{c.product_name}</p>
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={c.status} size="sm" />
                    </td>
                    <td className="py-2.5 px-3 text-[#625F70]">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="text-[#312E81] hover:underline font-semibold flex items-center justify-end gap-1">
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
          <div className="text-center py-8 text-xs text-[#625F70]">
            No cases created yet. Click "Start a New Case" to begin with voice or text.
          </div>
        )}
      </section>

      {/* Follow-ups Widget Strip */}
      {followUps.length > 0 && (
        <section className="bg-white rounded-xl p-5 shadow-xs border border-[#E4E1E8] space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#E4E1E8]">
            <h2 className="text-base font-bold font-['Hanken_Grotesk'] text-[#27243A] flex items-center gap-2">
              <Calendar className="w-5 h-5 text-[#E7B76A]" />
              <span>Upcoming Scheduled Follow-up Reminders</span>
            </h2>
            <span className="text-xs text-[#625F70]">
              {followUps.length} Pending Actions
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {followUps.map((f) => (
              <div
                key={f.action_id}
                onClick={() => onSelectCase(f.case_id)}
                className="p-3 bg-[#F7F6F3] rounded-lg border border-[#E4E1E8] hover:border-[#5B4B8A] transition-colors cursor-pointer space-y-1 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#27243A] truncate">{f.title}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      f.is_overdue
                        ? 'bg-[#F9ECEB] text-[#B94A48]'
                        : 'bg-[#FBF4E8] text-[#E7B76A]'
                    }`}
                  >
                    {f.is_overdue ? 'Overdue' : 'Pending'}
                  </span>
                </div>
                <p className="text-[11px] text-[#625F70]">
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
