export type FinancialTrend = "improving" | "stable" | "declining" | "unknown";

export interface FinancialSummaryResponse {
  code: string;
  summary: string;
  positives: string[];
  concerns: string[];
  trend: FinancialTrend;
  cached: boolean;
}

export const TREND_LABEL: Record<FinancialTrend, string> = {
  improving: "改善傾向",
  stable: "横ばい",
  declining: "悪化傾向",
  unknown: "判定不可",
};