"use client";

import { useEffect, useState } from "react";
import type { FinancialSummaryResponse } from "@/types/analysis";
import { TREND_LABEL } from "@/types/analysis";

interface Props {
  code: string;
}

export const FinancialSummaryCard = ({ code }: Props) => {
  const [data, setData] = useState<FinancialSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/financial-summary/${code}`)
      .then((res) => {
        if (!res.ok) throw new Error("財務サマリーを取得できませんでした");
        return res.json();
      })
      .then((json: FinancialSummaryResponse) => {
        if (!cancelled) setData(json);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "エラーが発生しました");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  return (
    <div className="analysis-card">
      <div className="analysis-card-header">
        <span className="analysis-icon">💰</span>
        <span className="analysis-title">財務サマリー</span>
        {data && (
          <span className={`analysis-trend-badge analysis-trend-badge-${data.trend}`}>
            {TREND_LABEL[data.trend]}
          </span>
        )}
      </div>

      {loading && <div className="analysis-loading">読み込み中...</div>}
      {error && <div className="analysis-error">{error}</div>}

      {data && !loading && !error && (
        <>
          <p className="analysis-summary-text">{data.summary}</p>
          <div className="analysis-points">
            {data.positives.map((p, i) => (
              <div key={`p-${i}`} className="analysis-point analysis-point-positive">
                ＋ {p}
              </div>
            ))}
            {data.concerns.map((c, i) => (
              <div key={`c-${i}`} className="analysis-point analysis-point-concern">
                － {c}
              </div>
            ))}
          </div>
          <div className="analysis-disclaimer">
            ※ 決算数値の客観的な傾向整理です。投資判断はご自身の責任で行ってください。
          </div>
        </>
      )}
    </div>
  );
};