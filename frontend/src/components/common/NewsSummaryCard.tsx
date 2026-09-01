"use client";

import { useEffect, useState } from "react";
import type { NewsSummaryResponse } from "@/types/analysis";

interface Props {
  code: string;
}

export const NewsSummaryCard = ({ code }: Props) => {
  const [data, setData] = useState<NewsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/news-summary/${code}`)
      .then((res) => {
        if (!res.ok) throw new Error("ニュース要約を取得できませんでした");
        return res.json();
      })
      .then((json: NewsSummaryResponse) => {
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
        <span className="analysis-icon">📰</span>
        <span className="analysis-title">ニュース要約</span>
      </div>

      {loading && <div className="analysis-loading">読み込み中...</div>}
      {error && <div className="analysis-error">{error}</div>}

      {data && !loading && !error && (
        <>
          <p className="analysis-summary-text">{data.summary}</p>
          {data.sentiment.positive.length > 0 && (
            <div className="analysis-points">
              {data.sentiment.positive.map((p, i) => (
                <div key={i} className="analysis-point analysis-point-positive">
                  ＋ {p}
                </div>
              ))}
            </div>
          )}
          <div className="analysis-disclaimer">
            ※ 本要約はニュースの客観的整理であり、投資助言ではありません。
          </div>
        </>
      )}
    </div>
  );
};