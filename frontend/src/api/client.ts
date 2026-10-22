import type {
  Case,
  CaseCreatePayload,
  CaseUpdatePayload,
  CaseStatus,
  CaseEvent,
  Evidence,
  EvidenceChecklistResponse,
  EvidenceType,
  Action,
  ActionCreatePayload,
  FollowUpItem,
  CaseAnalysisResponse,
  CaseChatResponse,
  SimulatedResponse,
  SimulatedResponseCreatePayload,
  ResponseProcessingResult,
  PolicySourceRead,
  WorkflowState,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`
    try {
      const errJson = await response.json()
      if (errJson.detail) {
        if (typeof errJson.detail === 'string') {
          errorDetail = errJson.detail
        } else if (Array.isArray(errJson.detail)) {
          errorDetail = errJson.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ')
        } else {
          errorDetail = JSON.stringify(errJson.detail)
        }
      }
    } catch {
      // ignore parsing error
    }
    throw new Error(errorDetail)
  }

  // 204 No Content
  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}

export const api = {
  // Cases
  async listCases(): Promise<Case[]> {
    return request<Case[]>('/cases')
  },

  async getCase(id: string): Promise<Case> {
    return request<Case>(`/cases/${id}`)
  },

  async createCase(payload: CaseCreatePayload): Promise<Case> {
    return request<Case>('/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },

  async updateCase(id: string, payload: CaseUpdatePayload): Promise<Case> {
    return request<Case>(`/cases/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },

  async updateCaseStatus(id: string, status: CaseStatus): Promise<Case> {
    return request<Case>(`/cases/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
  },

  // Agentic Workflow State
  async getWorkflowState(caseId: string): Promise<WorkflowState> {
    return request<WorkflowState>(`/cases/${caseId}/workflow-state`)
  },

  async reassessWorkflow(caseId: string): Promise<WorkflowState> {
    return request<WorkflowState>(`/cases/${caseId}/reassess`, {
      method: 'POST',
    })
  },

  // Case Timeline & Events
  async getCaseTimeline(caseId: string): Promise<CaseEvent[]> {
    return request<CaseEvent[]>(`/cases/${caseId}/timeline`)
  },

  async addCaseEvent(caseId: string, description: string): Promise<CaseEvent> {
    return request<CaseEvent>(`/cases/${caseId}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description, event_type: 'NOTE_ADDED' }),
    })
  },

  // Evidence
  async listEvidence(caseId: string): Promise<Evidence[]> {
    return request<Evidence[]>(`/cases/${caseId}/evidence`)
  },

  async uploadEvidence(caseId: string, file: File, evidenceType?: EvidenceType): Promise<Evidence> {
    const formData = new FormData()
    formData.append('file', file)
    if (evidenceType) {
      formData.append('evidence_type', evidenceType)
    }

    const url = `${BASE_URL}/cases/${caseId}/evidence`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      let errorDetail = `Upload failed with status ${response.status}`
      try {
        const errJson = await response.json()
        if (errJson.detail) errorDetail = errJson.detail
      } catch {
        // ignore
      }
      throw new Error(errorDetail)
    }

    return response.json()
  },

  async deleteEvidence(caseId: string, evidenceId: string): Promise<void> {
    return request<void>(`/cases/${caseId}/evidence/${evidenceId}`, {
      method: 'DELETE',
    })
  },

  async getEvidenceChecklist(caseId: string): Promise<EvidenceChecklistResponse> {
    return request<EvidenceChecklistResponse>(`/cases/${caseId}/evidence-checklist`)
  },

  // Actions
  async listActions(caseId: string): Promise<Action[]> {
    return request<Action[]>(`/cases/${caseId}/actions`)
  },

  async createAction(caseId: string, payload: ActionCreatePayload): Promise<Action> {
    return request<Action>(`/cases/${caseId}/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },

  async getAction(actionId: string): Promise<Action> {
    return request<Action>(`/actions/${actionId}`)
  },

  async approveAction(actionId: string): Promise<Action> {
    return request<Action>(`/actions/${actionId}/approve`, {
      method: 'POST',
    })
  },

  async rejectAction(actionId: string, reason?: string): Promise<Action> {
    return request<Action>(`/actions/${actionId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reason ? { reason } : {}),
    })
  },

  async executeAction(actionId: string): Promise<Action> {
    return request<Action>(`/actions/${actionId}/execute`, {
      method: 'POST',
    })
  },

  // Follow-ups
  async listFollowUps(caseId: string): Promise<FollowUpItem[]> {
    return request<FollowUpItem[]>(`/cases/${caseId}/follow-ups`)
  },

  // Analysis & Chat
  async runAnalysis(caseId: string): Promise<CaseAnalysisResponse> {
    return request<CaseAnalysisResponse>(`/cases/${caseId}/analysis`, {
      method: 'POST',
    })
  },

  async sendChatMessage(caseId: string, message: string): Promise<CaseChatResponse> {
    return request<CaseChatResponse>(`/cases/${caseId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
  },

  // Simulated Responses
  async listSimulatedResponses(caseId: string): Promise<SimulatedResponse[]> {
    return request<SimulatedResponse[]>(`/cases/${caseId}/responses`)
  },

  async simulateResponse(caseId: string, payload: SimulatedResponseCreatePayload): Promise<SimulatedResponse> {
    return request<SimulatedResponse>(`/cases/${caseId}/simulate-response`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },

  async processResponse(caseId: string, responseId: string): Promise<ResponseProcessingResult> {
    return request<ResponseProcessingResult>(`/cases/${caseId}/responses/${responseId}/process`, {
      method: 'POST',
    })
  },

  // Policies
  async listPolicies(): Promise<PolicySourceRead[]> {
    return request<PolicySourceRead[]>('/policies')
  },
}
