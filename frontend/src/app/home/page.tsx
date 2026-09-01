"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { formatPrice, formatRate, formatProb, getStatusMeta } from "@/lib/utils";
import { NewsSummaryResponse } from "@/types/newsSummary";
import { NewsSummaryCard } from "@/components/common/NewsSummaryCard";
import { FinancialSummaryCard } from "@/components/common/FinancialSummaryCard";

export interface PredictionDetail {
  rate: number;
  up_prob: number;
}

export interface MetricDetail {
  mae: number;
  r2: number;
  direction_accuracy: number;
}

export interface PredictResponse {
  code: string;
  company_name: string;
  current_price: number;
  price_change_rate: number;
  predictions: {
    target_1d: PredictionDetail;
    target_5d: PredictionDetail;
    target_10d: PredictionDetail;
  };
  metrics: {
    target_1d: MetricDetail;
    target_5d: MetricDetail;
    target_10d: MetricDetail;
  };
}

// ===================================================
// サブコンポーネント: 予測カード
// ===================================================
interface CardProps {
  label: string;
  prediction: PredictionDetail;
  metric: MetricDetail;
}

function PredictionCard({ label, prediction, metric }: CardProps) {
  const rateMeta = getStatusMeta(prediction.rate, "rate");
  const probMeta = getStatusMeta(prediction.up_prob, "prob");
  const dirMeta = getStatusMeta(metric.direction_accuracy, "dir");

  return (
    <div className="prediction-card">
      <div className="card-label">{label}</div>
      <div className={`card-rate ${rateMeta.colorClass}`}>
        {formatRate(prediction.rate)}
      </div>
      <div className="card-prob-row">
        <span className="prob-label">上昇確率</span>
        <span className={`prob-value ${probMeta.colorClass}`}>
          {formatProb(prediction.up_prob)}
        </span>
      </div>
      <div className="card-divider" />
      <div className="card-metrics">
        <div className="metric-item">
          <span className="metric-label">方向正解率</span>
          <span className={`metric-value ${dirMeta.colorClass}`}>
            {formatProb(metric.direction_accuracy)}
            <span className="dir-acc-badge">{dirMeta.label}</span>
          </span>
        </div>
        <div className="metric-row-small">
          <span>R²: {metric.r2.toFixed(3)}</span>
          <span>MAE: {metric.mae.toFixed(3)}</span>
        </div>
      </div>
      <div className="r2-bar-bg">
        <div
          className="dir-bar-fill"
          style={{
            width: `${metric.direction_accuracy * 100}%`,
            backgroundColor: dirMeta.color
          }}
        />
      </div>
    </div>
  );
}

// ===================================================
// メインページ
// ===================================================
export default function Home() {
  const searchParams = useSearchParams();
  const [code, setCode] = useState("");
  const [predictResult, setPredictResult] = useState<PredictResponse | null>(null);
  const [newsSummaryResult, setNewsSummaryResult] = useState<NewsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetchData = async () => {
    handlePredict();
    handleNewsSummary();
  }

  // 予測実行ロジック
  const handlePredict = async (targetCode?: string) => {
    const activeCode = targetCode || code;
    if (!activeCode.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/predict/${activeCode.trim()}`);
      if (!res.ok) throw new Error("銘柄が見つからないか、予測データがありません");
      const data: PredictResponse = await res.json();
      setPredictResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "予期せぬエラーが発生しました");
      setPredictResult(null);
    } finally {
      setLoading(false);
    }
  };

  // ニュース要約ロジック
  const handleNewsSummary = async (targetCode?: string) => {
    const activeCode = targetCode || code;
    if (!activeCode.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/news-summary/${activeCode.trim()}`);
      if (!res.ok) throw new Error("銘柄が見つからないか、予測データがありません");
      const data: NewsSummaryResponse = await res.json();
      setNewsSummaryResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "予期せぬエラーが発生しました");
      setNewsSummaryResult(null);
    } finally {
      setLoading(false);
    }
  };

  // URLパラメータ（ランキングからの遷移）対応
  useEffect(() => {
    const queryCode = searchParams.get("code");
    if (queryCode) {
      setCode(queryCode);
      handlePredict(queryCode);
      handleNewsSummary(queryCode);
    }
  }, [searchParams]);

  return (
    <main className="main">
      <header className="header">
        <div className="header-inner">
          <div className="logo">[ STOCK PREDICTOR ]</div>
          <div className="header-sub">ML-Powered Japanese Equity Forecast</div>
        </div>
      </header>

      <nav className="nav-section">
        <div className="nav-inner">
          <Link href="/" className="nav-link nav-link-active">検索</Link>
          <Link href="/ranking" className="nav-link">🏆 ランキング</Link>
          <Link href="/signals" className="nav-link">🟢 シグナル</Link>
        </div>
      </nav>

      <section className="search-section">
        <div className="search-inner">
          <div className="search-row">
            <input
              className="code-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleFetchData()}
              placeholder="銘柄コード (例: 5401)"
            />
            <button className="predict-btn" onClick={() => handleFetchData()} disabled={loading}>
              {loading ? "..." : "PREDICT →"}
            </button>
          </div>
        </div>
      </section>

      {error && <div className="error-box">{error}</div>}

      {predictResult && (
        <section className="result-section">
          <div className="stock-info">
            <div className="stock-info-left">
              <div className="stock-code">{predictResult.code}</div>
              <div className="stock-name">{predictResult.company_name}</div>
            </div>
            <div className="stock-info-right">
              <div className="stock-price">{formatPrice(predictResult.current_price)}</div>
              <div className={`stock-change ${getStatusMeta(predictResult.price_change_rate, "rate").colorClass}`}>
                {formatRate(predictResult.price_change_rate)} (前日比)
              </div>
            </div>
          </div>

          <div className="cards-grid">
            <PredictionCard
              label="翌日 (1D)"
              prediction={predictResult.predictions.target_1d}
              metric={predictResult.metrics.target_1d}
            />
            <PredictionCard
              label="5日後 (5D)"
              prediction={predictResult.predictions.target_5d}
              metric={predictResult.metrics.target_5d}
            />
            <PredictionCard
              label="10日後 (10D)"
              prediction={predictResult.predictions.target_10d}
              metric={predictResult.metrics.target_10d}
            />
          </div>
          <div className="analysis-grid">
            <NewsSummaryCard code={predictResult.code} />
            <FinancialSummaryCard code={predictResult.code} />
          </div>
          {newsSummaryResult && (
            <section className="news-summary-section">
              <div className="news-summary-header">
                <span className="mono-label">材料整理（AI要約）</span>
                <span className="news-summary-date">{newsSummaryResult.generated_at}時点</span>
              </div>

              <p className="news-summary-text">{newsSummaryResult.summary}</p>

              <div className="sentiment-grid">
                <div className="sentiment-col sentiment-positive">
                  <div className="sentiment-label">ポジティブ材料</div>
                  {newsSummaryResult.sentiment.positive.map((item, i) => (
                    <div key={i} className="sentiment-item">・{item}</div>
                  ))}
                </div>
                <div className="sentiment-col sentiment-negative">
                  <div className="sentiment-label">ネガティブ材料</div>
                  {newsSummaryResult.sentiment.negative.map((item, i) => (
                    <div key={i} className="sentiment-item">・{item}</div>
                  ))}
                </div>
              </div>

              <div className="topics-list">
                {newsSummaryResult.topics.map((t, i) => (
                  <div key={i} className="topic-item">
                    <span className="topic-source">[{t.source}]</span> {t.text}
                  </div>
                ))}
              </div>

              <p className="disclaimer">
                ※本要約は与えられた情報の客観的整理であり、投資助言ではありません。
              </p>
            </section>
          )}
        </section>
      )}
    </main>
  );
}