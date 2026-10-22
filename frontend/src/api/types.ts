// Case Status Types matching backend app/models/case.py
export type CaseStatus =
  | 'NEW'
  | 'COLLECTING_EVIDENCE'
  | 'UNDER_REVIEW'
  | 'ACTION_READY'
  | 'AWAITING_RESPONSE'
  | 'FOLLOW_UP_DUE'
  | 'RESOLVED'
  | 'CLOSED'

// Workflow State matching backend app/schemas/workflow.py
export type WorkflowStage =
  | 'INTAKE'
  | 'EVIDENCE_GATHERING'
  | 'UNDER_REVIEW'
  | 'ACTION_PENDING'
  | 'AWAITING_RESPONSE'
  | 'RESOLVED'
  | 'CLOSED'

export type WorkflowWaitState =
  | 'NONE'
  | 'WAITING_FOR_USER_INPUT'
  | 'WAITING_FOR_ACTION_APPROVAL'
  | 'WAITING_FOR_EXTERNAL_RESPONSE'
  | 'PROCESSING'
  | 'COMPLETED'

export interface WorkflowState {
  id: string
  case_id: string
  goal: string
  stage: WorkflowStage
  wait_state: WorkflowWaitState
  latest_recommendation?: string | null
  pending_evidence: string[]
  outstanding_commitments: string[]
  active_action_id?: string | null
  active_action?: Action | null
  last_reassessed_at: string
  updated_at: string
  created_at: string
}

// Case Model matching backend app/schemas/case.py
export interface Case {
  id: string
  title: string
  product_name: string
  issue_description: string
  status: CaseStatus
  created_at: string
  updated_at: string
  workflow_state?: WorkflowState | null
}

export interface CaseCreatePayload {
  title: string
  product_name: string
  issue_description: string
}

export interface CaseUpdatePayload {
  title?: string
  product_name?: string
  issue_description?: string
}

// Case Event / Timeline matching app/schemas/event.py
export interface CaseEvent {
  id: string
  case_id: string
  event_type: string
  description: string
  source_type: string
  metadata_json?: Record<string, any> | null
  created_at: string
}

// Evidence matching app/schemas/evidence.py
export type EvidenceType =
  | 'INVOICE'
  | 'WARRANTY'
  | 'REPAIR_RECEIPT'
  | 'SERVICE_COMMUNICATION'
  | 'OTHER'

export type ExtractionStatus =
  | 'PENDING'
  | 'COMPLETED'
  | 'NO_TEXT_FOUND'
  | 'UNSUPPORTED'
  | 'FAILED'

export interface Evidence {
  id: string
  case_id: string
  original_filename: string
  evidence_type: EvidenceType
  mime_type: string
  file_size_bytes: number
  extraction_status: ExtractionStatus
  created_at: string
  extracted_text?: string | null
  suggested_evidence_type?: EvidenceType | null
}

export interface EvidenceChecklistResponse {
  represented_categories: EvidenceType[]
  missing_categories: EvidenceType[]
  explanation: string
}

// Actions matching app/schemas/action.py
export type ActionType = 'SEND_MESSAGE' | 'SCHEDULE_FOLLOW_UP'

export type ActionStatus =
  | 'DRAFT'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXECUTED'
  | 'FAILED'
  | 'CANCELLED'

export interface Action {
  id: string
  case_id: string
  action_type: ActionType
  title: string
  description: string
  payload_json: Record<string, any>
  status: ActionStatus
  created_at: string
  updated_at: string
  approved_at?: string | null
  executed_at?: string | null
  execution_result_json?: Record<string, any> | null
  error_message?: string | null
}

export interface ActionCreatePayload {
  action_type: ActionType
  title: string
  description: string
  payload: Record<string, any>
}

export interface ActionUpdatePayload {
  title?: string
  description?: string
  payload?: Record<string, any>
}

// Follow-ups matching app/schemas/action.py
export interface FollowUpItem {
  action_id: string
  case_id: string
  title: string
  due_at: string
  purpose: string
  status: ActionStatus
  is_overdue: boolean
}

// Analysis & Chat matching app/schemas/analysis.py
export interface PolicySearchResultItem {
  source_id: string
  source_title: string
  source_url?: string | null
  source_type: string
  jurisdiction?: string | null
  product_category?: string | null
  passage: string
  relevance_score: number
}

export interface AnalysisKnownFact {
  category: string
  fact: string
}

export interface AnalysisMissingInfo {
  item: string
  impact: string
}

export interface CaseAnalysisResponse {
  case_id: string
  engine_mode: 'demo' | 'live' | 'ollama'
  summary: string
  recommended_next_step: string
  reasoning: string
  known_facts: AnalysisKnownFact[]
  missing_information: AnalysisMissingInfo[]
  evidence_considered: string[]
  supporting_policy_sources: PolicySearchResultItem[]
  uncertainty_notes: string[]
  suggested_action?: string | null
  generated_at: string
}

export interface CaseChatRequest {
  message: string
}

export interface CaseChatResponse {
  case_id: string
  engine_mode: 'demo' | 'live' | 'ollama'
  question: string
  answer: string
  distinction_notes: string[]
  supporting_policy_sources: PolicySearchResultItem[]
  generated_at: string
}

// Simulated Provider Responses matching app/schemas/response.py
export interface SimulatedResponse {
  id: string
  case_id: string
  related_action_id?: string | null
  provider_name: string
  response_text: string
  source_type: 'SIMULATION'
  status: 'PENDING' | 'PROCESSED'
  created_at: string
  processed_at?: string | null
  is_simulated: boolean
}

export interface SimulatedResponseCreatePayload {
  response_text: string
  related_action_id?: string | null
  provider_name?: string
}

export interface ResponseProcessingResult {
  case_id: string
  response_id: string
  engine_mode: 'demo' | 'live'
  summary: string
  requested_information: string[]
  identified_commitments: string[]
  ambiguities: string[]
  evidence_already_available: string[]
  evidence_still_needed: string[]
  recommended_next_step: string
  supporting_policy_sources: PolicySearchResultItem[]
  uncertainty_notes: string[]
  suggested_action?: Record<string, any> | null
  suggested_case_status?: string | null
  workflow_state?: WorkflowState | null
  proposed_action?: Action | null
  processed_at: string
}

// Policy matching app/schemas/policy.py
export interface PolicySourceRead {
  id: string
  title: string
  source_url?: string | null
  source_type: string
  jurisdiction?: string | null
  product_category?: string | null
}
