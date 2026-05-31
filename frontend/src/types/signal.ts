// frontend/src/types/signal.ts

export type SignalType = "BUY" | "HOLD";
export type StrengthType = "STRONG" | "WEAK" | "NONE" | "ALL";
export type TargetType = "target_1d" | "target_5d" | "target_10d";

export interface SignalItem {
  code: string;
  company_name: string | null;
  signal_date: string;
  target: TargetType;
  signal: SignalType;
  strength: StrengthType;
  up_prob: number;
  pred_rate: number;
}

export interface SignalListResponse {
  signal_date: string;
  target: TargetType;
  total: number;
  items: SignalItem[];
}

export interface SignalHistoryItem {
  signal_date: string;
  signal: SignalType;
  strength: StrengthType;
  up_prob: number;
  pred_rate: number;
}

export interface SignalHistoryResponse {
  code: string;
  target: TargetType;
  history: SignalHistoryItem[];
}