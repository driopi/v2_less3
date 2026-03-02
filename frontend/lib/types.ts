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
  markdown: string;
  round_summaries: string[];
  portrait?: PortraitCard;
}
