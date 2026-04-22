// frontend/app/ranking/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StatValue } from "@/components/common/StatValue";
import { getDirAccMeta } from "@/lib/utils";
import "@/styles/_ranking.scss"

// ===================================================
// 型定義
// ===================================================

interface RankingStock {
  rank: number;
  code: string;
  company_name: string;
  expected_value: number;
  predicted_return: number;
  up_probability: number;
  r2: number;
  direction_accuracy: number;
}

interface RankingResponse {
  ranking_type: string;
  period: string;
  updated_at: string;
  stocks: RankingStock[];
}

type RankingType = "expected" | "return" | "probability" | "confidence";
type Period = "1d" | "5d" | "10d";

// ===================================================
// ユーティリティ
// ===================================================

const formatRate = (rate: number) => {
  const pct = (rate * 100).toFixed(2);
  return rate >= 0 ? `+${pct}%` : `${pct}%`;
};

const formatProb = (prob: number) => `${(prob * 100).toFixed(1)}%`;

const getRankBadge = (rank: number) => {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return rank;
};

const getDirAccLabel = (acc: number) => {
  if (acc >= 0.6) return { label: "高", color: "var(--up)" };
  if (acc >= 0.5) return { label: "中", color: "var(--yellow)" };
  return { label: "低", color: "var(--text-muted)" };
};

// ===================================================
// メインページ
// ===================================================

export default function RankingPage() {
  const [rankingType, setRankingType] = useState<RankingType>("expected");
  const [period, setPeriod] = useState<Period>("5d");
  const [data, setData] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ランキング取得
  const fetchRanking = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/ranking?ranking_type=${rankingType}&period=${period}&limit=20`
      );
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "ランキング取得に失敗しました");
      }
      const rankingData: RankingResponse = await res.json();
      setData(rankingData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  // 初回読み込み
  useEffect(() => {
    fetchRanking();
  }, []);

  // タブ・期間変更時に再取得
  const handleTabChange = (type: RankingType) => {
    setRankingType(type);
  };

  const handlePeriodChange = (p: Period) => {
    setPeriod(p);
  };

  useEffect(() => {
    fetchRanking();
  }, [rankingType, period]);

  const rankingTabs = [
    { id: "expected" as const, label: "期待値順", icon: "🏆" },
    { id: "return" as const, label: "騰落率順", icon: "📈" },
    { id: "probability" as const, label: "確率順", icon: "🎯" },
    { id: "confidence" as const, label: "信頼度順", icon: "✅" },
  ];

  const periodButtons = [
    { id: "1d" as const, label: "翌日" },
    { id: "5d" as const, label: "5日後" },
    { id: "10d" as const, label: "10日後" },
  ];

  return (
    <main className="main">
      {/* ヘッダー */}
      <header className="header">
        <div className="header-inner">
          <Link href="/" className="logo" style={{ textDecoration: "none" }}>
            <span className="logo-bracket">[</span>
            <span className="logo-text">STOCK PREDICTOR</span>
            <span className="logo-bracket">]</span>
          </Link>
          <div className="header-sub">ML-Powered Japanese Equity Forecast</div>
        </div>
      </header>

      {/* ナビゲーション */}
      <nav className="nav-section">
        <div className="nav-inner">
          <Link href="/" className="nav-link">
            検索
          </Link>
          <Link href="/ranking" className="nav-link nav-link-active">
            🏆 ランキング
          </Link>
        </div>
      </nav>

      {/* ランキングコントロール */}
      <section className="ranking-controls">
        <div className="controls-inner">
          {/* ランキング種別タブ */}
          <div className="control-group">
            <label className="control-label">ランキング種別</label>
            <div className="tab-buttons">
              {rankingTabs.map((tab) => (
                <button
                  key={tab.id}
                  className={`tab-btn ${
                    rankingType === tab.id ? "tab-btn-active" : ""
                  }`}
                  onClick={() => handleTabChange(tab.id)}
                  disabled={loading}
                >
                  <span className="tab-icon">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* 期間選択 */}
          <div className="control-group">
            <label className="control-label">予測期間</label>
            <div className="period-buttons">
              {periodButtons.map((btn) => (
                <button
                  key={btn.id}
                  className={`period-btn ${
                    period === btn.id ? "period-btn-active" : ""
                  }`}
                  onClick={() => handlePeriodChange(btn.id)}
                  disabled={loading}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* エラー表示 */}
      {error && (
        <div className="error-box">
          <span className="error-icon">⚠</span> {error}
        </div>
      )}

      {/* ローディング */}
      {loading && (
        <div className="loading-box">
          <span className="btn-loading">
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span className="loading-dot" />
          </span>
          <span className="loading-text">ランキング取得中...</span>
        </div>
      )}

      {/* ランキングテーブル */}
      {data && !loading && (
        <section className="ranking-section">
          {/* 更新時刻 */}
          <div className="ranking-meta">
            <div className="meta-item">
              <span className="meta-label">最終更新:</span>
              <span className="meta-value">
                {new Date(data.updated_at).toLocaleString("ja-JP")}
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">表示件数:</span>
              <span className="meta-value">{data.stocks.length}件</span>
            </div>
          </div>

          {/* テーブル */}
          <div className="ranking-table-wrapper">
            <table className="ranking-table">
              <thead>
                <tr>
                  <th className="th-rank">順位</th>
                  <th className="th-code">コード</th>
                  <th className="th-name">銘柄名</th>
                  <th className="th-value">期待値</th>
                  <th className="th-return">予測騰落率</th>
                  <th className="th-prob">上昇確率</th>
                  <th className="th-dir">方向正解率</th>
                  <th className="th-r2">R²</th>
                </tr>
              </thead>
              <tbody>
                {data.stocks.map((stock) => {
                  const dirMeta = getDirAccMeta(stock.direction_accuracy);

                  return (
                    <tr key={stock.code} className="table-row">
                      {/* 順位 */}
                      <td className="td-rank">
                        <span className="rank-badge">
                          {getRankBadge(stock.rank)}
                        </span>
                      </td>

                      {/* コード */}
                      <td className="td-code">
                        <Link
                          href={`/?code=${stock.code}`}
                          className="code-link"
                        >
                          {stock.code}
                        </Link>
                      </td>

                      {/* 銘柄名 */}
                      <td className="td-name">{stock.company_name}</td>

                      {/* 期待値 */}
                      <td className="td-value">
                        <span className="value-highlight">
                          {formatRate(stock.expected_value / 100)}
                        </span>
                      </td>

                      {/* 騰落率 */}
                      <td className="td-return">
                        <StatValue value={stock.predicted_return} type="rate" />
                      </td>
                      {/* 上昇確率 */}
                      <td className="td-prob">
                        <StatValue value={stock.up_probability} type="prob" />
                      </td>
                      {/* 方向正解率 */}
                      <td className="td-dir">
                        <span style={{ color: dirMeta.color }}>
                          {formatProb(stock.direction_accuracy)}
                          <span className="dir-badge-inline">{dirMeta.label}</span>
                        </span>
                      </td>

                      {/* R² */}
                      <td className="td-r2">
                        {stock.r2.toFixed(3)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* 注意書き */}
          <p className="disclaimer">
            ※
            本ランキングは機械学習モデルによる参考値です。投資判断はご自身の責任で行ってください。
          </p>
        </section>
      )}
    </main>
  );
}