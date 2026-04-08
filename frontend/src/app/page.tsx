"use client";

import { useState } from "react";

// ===================================================
// 型定義
// ===================================================

interface PredictionDetail {
  rate: number;
  up_prob: number;
}

interface MetricDetail {
  mae: number;
  r2: number;
  direction_accuracy: number;  // 方向正解率
}

interface PredictResponse {
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
// ユーティリティ
// ===================================================

const formatRate = (rate: number) => {
  const pct = (rate * 100).toFixed(2);
  return rate >= 0 ? `+${pct}%` : `${pct}%`;
};

const formatProb = (prob: number) => `${(prob * 100).toFixed(1)}%`;

const formatPrice = (price: number) =>
  price.toLocaleString("ja-JP", { style: "currency", currency: "JPY" });

// 方向正解率のラベルと色
const getDirAccLabel = (acc: number) => {
  if (acc >= 0.6) return { label: "高", color: "var(--up)" };
  if (acc >= 0.5) return { label: "中", color: "var(--yellow)" };
  return { label: "低", color: "var(--text-muted)" };
};

// ===================================================
// コンポーネント
// ===================================================

function PredictionCard({
  label,
  prediction,
  metric,
}: {
  label: string;
  prediction: PredictionDetail;
  metric: MetricDetail;
}) {
  const isUp = prediction.rate >= 0;
  const probColor =
    prediction.up_prob >= 0.6
      ? "text-up"
      : prediction.up_prob >= 0.5
      ? "text-yellow"
      : "text-down";

  const dirAcc = getDirAccLabel(metric.direction_accuracy);

  return (
    <div className="prediction-card">
      <div className="card-label">{label}</div>

      <div className={`card-rate ${isUp ? "rate-up" : "rate-down"}`}>
        {formatRate(prediction.rate)}
      </div>

      <div className="card-prob-row">
        <span className="prob-label">上昇確率</span>
        <span className={`prob-value ${probColor}`}>
          {formatProb(prediction.up_prob)}
        </span>
      </div>

      <div className="card-divider" />

      {/* 評価指標 */}
      <div className="card-metrics">
        <div className="metric-item">
          <span className="metric-label">R²</span>
          <span className="metric-value">{metric.r2.toFixed(4)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">MAE</span>
          <span className="metric-value">{metric.mae.toFixed(4)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">方向正解率</span>
          <span className="metric-value" style={{ color: dirAcc.color }}>
            {formatProb(metric.direction_accuracy)}
            <span className="dir-acc-badge">{dirAcc.label}</span>
          </span>
        </div>
      </div>

      {/* 方向正解率バー */}
      <div className="r2-bar-bg">
        <div
          className="dir-bar-fill"
          style={{
            width: `${metric.direction_accuracy * 100}%`,
            background:
              metric.direction_accuracy >= 0.6
                ? "var(--up)"
                : metric.direction_accuracy >= 0.5
                ? "var(--yellow)"
                : "var(--text-muted)",
          }}
        />
      </div>
      {/* 50%ラインのマーカー */}
      <div className="bar-markers">
        <span className="bar-marker-50">50%</span>
      </div>
    </div>
  );
}

// ===================================================
// メインページ
// ===================================================

export default function Home() {
  const [code, setCode] = useState("");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePredict = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/predict/${code.trim()}`
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "予測に失敗しました");
      }
      const data: PredictResponse = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handlePredict();
  };

  const priceChangeColor =
    result && result.price_change_rate >= 0 ? "rate-up" : "rate-down";

  return (
    <main className="main">
      {/* ヘッダー */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-bracket">[</span>
            <span className="logo-text">STOCK PREDICTOR</span>
            <span className="logo-bracket">]</span>
          </div>
          <div className="header-sub">ML-Powered Japanese Equity Forecast</div>
        </div>
      </header>

      {/* 検索セクション */}
      <section className="search-section">
        <div className="search-inner">
          <label className="search-label">銘柄コード入力</label>
          <div className="search-row">
            <div className="input-wrapper">
              <span className="input-prefix">¥</span>
              <input
                className="code-input"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="5401"
                maxLength={5}
              />
            </div>
            <button
              className="predict-btn"
              onClick={handlePredict}
              disabled={loading || !code.trim()}
            >
              {loading ? (
                <span className="btn-loading">
                  <span className="loading-dot" />
                  <span className="loading-dot" />
                  <span className="loading-dot" />
                </span>
              ) : (
                "PREDICT →"
              )}
            </button>
          </div>
        </div>
      </section>

      {/* エラー */}
      {error && (
        <div className="error-box">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}

      {/* 結果 */}
      {result && (
        <section className="result-section">
          {/* 銘柄基本情報 */}
          <div className="stock-info">
            <div className="stock-info-left">
              <div className="stock-code">{result.code}</div>
              <div className="stock-name">{result.company_name}</div>
            </div>
            <div className="stock-info-right">
              <div className="stock-price">
                {formatPrice(result.current_price)}
              </div>
              <div className={`stock-change ${priceChangeColor}`}>
                {formatRate(result.price_change_rate)} (前日比)
              </div>
            </div>
          </div>

          {/* 予測カード */}
          <div className="cards-grid">
            <PredictionCard
              label="翌日予測 (1D)"
              prediction={result.predictions.target_1d}
              metric={result.metrics.target_1d}
            />
            <PredictionCard
              label="5日後予測 (5D)"
              prediction={result.predictions.target_5d}
              metric={result.metrics.target_5d}
            />
            <PredictionCard
              label="10日後予測 (10D)"
              prediction={result.predictions.target_10d}
              metric={result.metrics.target_10d}
            />
          </div>

          {/* 注意書き */}
          <p className="disclaimer">
            ※ 本予測は機械学習モデルによる参考値です。投資判断はご自身の責任で行ってください。
          </p>
        </section>
      )}
    </main>
  );
}