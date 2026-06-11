// frontend/src/app/signals/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SignalBadge } from "@/components/common/SignalBadge";
import { formatProb, formatRate } from "@/lib/utils";
import type {
  SignalItem,
  SignalListResponse,
  StrengthType,
  TargetType,
} from "@/types/signal";
import "@/styles/_signals.scss";

type Period = "1d" | "5d" | "10d";

const TARGET_MAP: Record<Period, TargetType> = {
  "1d":  "target_1d",
  "5d":  "target_5d",
  "10d": "target_10d",
};

export default function SignalsPage() {
  const [period, setPeriod]     = useState<Period>("5d");
  const [strength, setStrength] = useState<StrengthType>("ALL");
  const [data, setData]         = useState<SignalListResponse | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [signalFilter, setSignalFilter] = useState<"BUY" | "SELL">("BUY");

  const fetchSignals = async () => {
    setLoading(true);
    setError(null);
    try {
      const target = TARGET_MAP[period];
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/signals/`
        + `?signal=${signalFilter}&target=${target}&strength=${strength}&limit=30`
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "シグナル取得に失敗しました");
      }
      setData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
  }, [period, strength, signalFilter]);

  const periodButtons: { id: Period; label: string }[] = [
    { id: "1d",  label: "翌日"  },
    { id: "5d",  label: "5日後" },
    { id: "10d", label: "10日後"},
  ];

  const strengthButtons: { id: StrengthType; label: string }[] = [
    { id: "ALL",    label: "すべて"       },
    { id: "STRONG", label: "🟢 STRONG"   },
    { id: "WEAK",   label: "🔵 WEAK"     },
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
          <Link href="/home"    className="nav-link">検索</Link>
          <Link href="/ranking" className="nav-link">🏆 ランキング</Link>
          <Link href="/signals" className="nav-link nav-link-active">🟢 シグナル</Link>
        </div>
      </nav>

      {/* コントロール */}
      <section className="signals-controls">
        <div className="controls-inner">
          {/* 予測期間 */}
          <div className="control-group">
            <label className="control-label">予測期間</label>
            <div className="period-buttons">
              {periodButtons.map((btn) => (
                <button
                  key={btn.id}
                  className={`period-btn ${period === btn.id ? "period-btn-active" : ""}`}
                  onClick={() => setPeriod(btn.id)}
                  disabled={loading}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          {/* 強度フィルター */}
          <div className="control-group">
            <label className="control-label">シグナル強度</label>
            <div className="period-buttons">
              {strengthButtons.map((btn) => (
                <button
                  key={btn.id}
                  className={`period-btn ${strength === btn.id ? "period-btn-active" : ""}`}
                  onClick={() => setStrength(btn.id)}
                  disabled={loading}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          {/* シグナル種別 */}
          <div className="control-group">
            <label className="control-label">シグナル種別</label>
            <div className="period-buttons">
              <button
                className={`period-btn ${signalFilter === "BUY" ? "period-btn-active" : ""}`}
                onClick={() => setSignalFilter("BUY")}
              >
                🟢 買いシグナル
              </button>
              <button
                className={`period-btn ${signalFilter === "SELL" ? "period-btn-active" : ""}`}
                onClick={() => setSignalFilter("SELL")}
              >
                🔴 売りシグナル
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* エラー */}
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
          <span className="loading-text">シグナル取得中...</span>
        </div>
      )}

      {/* シグナル一覧 */}
      {data && !loading && (
        <section className="signals-section">
          {/* メタ情報 */}
          <div className="ranking-meta">
            <div className="meta-item">
              <span className="meta-label">算出日:</span>
              <span className="meta-value">
                {new Date(data.signal_date).toLocaleDateString("ja-JP")}
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">BUY銘柄数:</span>
              <span className="meta-value">{data.total}件</span>
            </div>
          </div>

          {/* テーブル */}
          <div className="ranking-table-wrapper">
            <table className="ranking-table">
              <thead>
                <tr>
                  <th className="th-code">コード</th>
                  <th className="th-name">銘柄名</th>
                  <th>シグナル</th>
                  <th className="th-prob">上昇確率</th>
                  <th className="th-return">予測騰落率</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item: SignalItem) => (
                  <tr key={item.code} className="table-row">
                    <td className="td-code">
                      <Link href={`/home?code=${item.code}`} className="code-link">
                        {item.code}
                      </Link>
                    </td>
                    <td className="td-name">{item.company_name ?? "-"}</td>
                    <td>
                      <SignalBadge signal={item.signal} strength={item.strength} />
                    </td>
                    <td className="td-prob">{formatProb(item.up_prob)}</td>
                    <td className="td-return"
                      style={{ color: item.pred_rate >= 0 ? "var(--up)" : "var(--down)" }}
                    >
                      {formatRate(item.pred_rate)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="disclaimer">
            ※ 本シグナルは機械学習モデルによる参考値です。投資判断はご自身の責任で行ってください。
          </p>
        </section>
      )}
    </main>
  );
}