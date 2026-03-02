export interface Question {
  id: string;
  text: string;
}

export interface SessionStartResponse {
  session_id: string;
  round: number;
  questions: Question[];
}

export interface SessionSubmitResponse {
  round: number;
  questions: Question[];
  round_summary: string;
  is_complete: boolean;
  checklist_preview?: string;
}

export interface ChecklistItem {
  category: string;
  item: string;
  status: "confirmed" | "needs_clarification" | "not_discussed";
  notes?: string;
}

export interface PortraitSignal {
  question_number: number;
  tension: number;
  uncertainty: number;
  valence: number;
}

export interface PortraitCard {
  emotional_stability: number;
  hidden_tension: number;
  confidence_proxy: number;
  dominant_emotions: string[];
  trigger_questions: number[];
  recommendation: string;
  signals: PortraitSignal[];
}

export interface SessionResultsResponse {
  session_id: string;
  is_complete: boolean;
  checklist: ChecklistItem[];
  markdown: string;
  round_summaries: string[];
  portrait?: PortraitCard;
}
