export interface Question {
  id: string;
  text: string;
}

export interface SessionLogEntry {
  at: string;
  source: string;
  message: string;
}

export interface SessionStartResponse {
  session_id: string;
  round: number;
  mock_mode: boolean;
  logs: SessionLogEntry[];
  questions: Question[];
}

export interface SessionSubmitResponse {
  round: number;
  questions: Question[];
  round_summary: string;
  is_complete: boolean;
  checklist_preview?: string;
}

export interface MockAnswerPreview {
  question_id: string;
  question_text: string;
  transcript: string;
}

export interface MockAnswersResponse {
  session_id: string;
  round: number;
  answers: MockAnswerPreview[];
  logs: string[];
}

export interface SessionSubmitAcceptedResponse {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_step?: string;
  eta_seconds_left: number;
  progress_pct: number;
}

export interface JobStep {
  key: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  eta_seconds: number;
}

export interface SubmitJobStatusResponse {
  job_id: string;
  session_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_step?: string;
  steps: JobStep[];
  eta_seconds_left: number;
  progress_pct: number;
  error?: string;
  result?: SessionSubmitResponse;
}

export interface ToolInsight {
  tool_name: string;
  title: string;
  summary: string;
  details: Record<string, string>;
}

export interface ChecklistItem {
  category: string;
  item: string;
  status: "confirmed" | "needs_clarification" | "not_discussed";
  notes?: string;
}

export interface PortraitSignal {
  question_number: number;
  round_number: number;
  question_in_round: number;
  question_text: string;
  tension: number;
  uncertainty: number;
  valence: number;
}

export interface PortraitTrigger {
  question_number: number;
  round_number: number;
  question_in_round: number;
  question_text: string;
  reason: string;
  score: number;
}

export interface PortraitCard {
  emotional_stability: number;
  hidden_tension: number;
  confidence_proxy: number;
  dominant_emotions: string[];
  trigger_questions: number[];
  triggers: PortraitTrigger[];
  recommendation: string;
  signals: PortraitSignal[];
}

export interface SessionResultsResponse {
  session_id: string;
  is_complete: boolean;
  checklist: ChecklistItem[];
  tool_insights: ToolInsight[];
  logs: SessionLogEntry[];
  markdown: string;
  round_summaries: string[];
  portrait?: PortraitCard;
}
