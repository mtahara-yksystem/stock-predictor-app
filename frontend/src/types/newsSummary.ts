export interface NewsSummaryResponse {
  code: string;
  generated_at: string;
  topics: { text: string; source: string }[];
  sentiment: { positive: string[]; negative: string[] };
  summary: string;
  sources_used: string[];
}