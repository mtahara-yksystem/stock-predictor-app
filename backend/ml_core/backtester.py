# backend/ml_core/backtester.py

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.macro_indicators_repo import MacroIndicatorsRepo
from ml_core.feature_engineer import FeatureEngineer


class Backtester:
    # ターゲットと保有日数の対応
    HOLDING_DAYS = {
        "target_1d": 1,
        "target_5d": 5,
        "target_10d": 10,
    }

    def __init__(self, sector_code: str):
        self.sector_code = sector_code
        self.repo = EquitiesMasterRepo()
        self.macro_repo = MacroIndicatorsRepo()
        self.engineer = FeatureEngineer()

        sector_info = self.repo.get_sector_info_by_code(sector_code)
        if not sector_info:
            raise ValueError(f"セクター {sector_code} の情報が見つかりません")

        self.sector_name_en = sector_info["S17NmEn"]
        self.model_dir = Path("models") / f"sector_{sector_code}_{self.sector_name_en}"

    # ===================================================
    # モデルロード
    # ===================================================

    def _load_model_assets(self, target: str):
        model_path = self.model_dir / f"model_{target}.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"モデルが見つかりません: {model_path}")
        save_data = joblib.load(model_path)
        return save_data["model"], save_data["scaler"], save_data["feature_names"]

    # ===================================================
    # 特徴量・予測値の準備
    # ===================================================

    def _prepare_predictions(self, code: str, target: str) -> pd.DataFrame | None:
        raw_df = self.repo.get_quotes_with_financials_by_sector(self.sector_code)
        raw_df = raw_df[raw_df["Code"] == code].copy()
        if raw_df.empty:
            return None

        macro_df = self.macro_repo.get_all_pivoted()

        X, y_all = self.engineer.create_features_and_targets(raw_df, macro_df=macro_df)
        if X.empty:
            return None

        # ===================================================
        # データリークチェック: 日付が現実的か確認
        # ===================================================
        today = pd.Timestamp.today().normalize()
        future_mask = X.index > today
        if future_mask.any():
            print(
                f"⚠️  未来日付を検出: {future_mask.sum()}件を除外します "
                f"({X.index[future_mask][0].date()} 〜)"
            )
            X = X[~future_mask]
            y_all = y_all[~future_mask]

        if X.empty:
            return None

        y = y_all[target].dropna()
        X = X.loc[y.index]  # NaNを除いた行に揃える

        model, scaler, feature_names = self._load_model_assets(target)

        for feat in feature_names:
            if feat not in X.columns:
                X[feat] = 0.0

        X_scaled = scaler.transform(X[feature_names])
        pred_rates = model.predict(X_scaled) / 100
        up_probs = np.clip(0.5 + pred_rates * 10, 0.0, 1.0)

        return pd.DataFrame(
            {
                "actual_ret": y,
                "pred_ret": pred_rates,
                "up_prob": up_probs,
            },
            index=X.index,
        ).dropna()

    # ===================================================
    # シグナル生成
    # ===================================================

    def _generate_signals(
        self,
        df: pd.DataFrame,
        prob_threshold: float,
        rate_threshold: float,
    ) -> pd.DataFrame:
        df = df.copy()
        df["signal"] = np.where(
            (df["up_prob"] >= prob_threshold) & (df["pred_ret"] >= rate_threshold),
            1,
            0,
        )
        return df

    # ===================================================
    # パフォーマンス計算（重複期間を除外）
    # ===================================================

    def _calc_performance(self, df: pd.DataFrame, holding_days: int) -> dict:
        """
        重複しない取引のみを使ってパフォーマンスを計算する。

        target_5dなら「5日ごとにシグナルを見て、
        買いなら5日後のリターンを1回だけ計上」する。
        これにより二重計上を防ぐ。
        """
        # シグナルが立っている行だけ対象
        signal_df = df[df["signal"] == 1].copy()

        if len(signal_df) == 0:
            return {
                "total_trades": 0,
                "win_rate": None,
                "avg_return": None,
                "cumulative_return": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
            }

        # ===================================================
        # 重複しない取引に絞る
        # 直前の取引から holding_days 経過していないものはスキップ
        # ===================================================
        non_overlap = []
        last_trade_date = None

        for date, row in signal_df.iterrows():
            if last_trade_date is None:
                non_overlap.append(row)
                last_trade_date = date
            else:
                elapsed = (date - last_trade_date).days
                if elapsed >= holding_days:
                    non_overlap.append(row)
                    last_trade_date = date

        trade_df = pd.DataFrame(non_overlap)

        if len(trade_df) == 0:
            return {
                "total_trades": 0,
                "win_rate": None,
                "avg_return": None,
                "cumulative_return": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
            }

        # 各取引は独立した holding_days 間のリターン
        returns = trade_df["actual_ret"].values

        win_rate = float((returns > 0).mean())
        avg_return = float(returns.mean())

        # 累積リターン（取引ごとに独立してコンパウンド）
        cum_returns = pd.Series((1 + returns).cumprod())  # ← pd.Series()で囲む
        cumulative_return = float(cum_returns.iloc[-1] - 1)

        # シャープレシオ
        trades_per_year = 252 / holding_days
        if returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(trades_per_year)
        else:
            sharpe = None

        # 最大ドローダウン
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns - rolling_max) / rolling_max
        max_drawdown = float(drawdown.min())

        return {
            "total_trades": len(trade_df),
            "win_rate": round(win_rate, 4),
            "avg_return": round(avg_return, 6),
            "cumulative_return": round(cumulative_return, 4),
            "sharpe_ratio": round(float(sharpe), 4) if sharpe else None,
            "max_drawdown": round(max_drawdown, 4),
        }

    # ===================================================
    # パブリックメソッド
    # ===================================================

    def run(
        self,
        code: str,
        target: str = "target_5d",
        prob_threshold: float = 0.6,
        rate_threshold: float = 0.0,
        test_ratio: float = 0.2,
    ) -> dict:
        holding_days = self.HOLDING_DAYS.get(target, 5)

        print(f"\n--- Backtest Start: {code} [{target}] ---")
        print(f"    保有日数: {holding_days}日")
        print(f"    閾値: up_prob>={prob_threshold}, pred_rate>={rate_threshold:.1%}")

        df = self._prepare_predictions(code, target)
        if df is None or df.empty:
            print("❌ データ不足のためスキップ")
            return {}

        # 学習データとテストデータを分割
        # 時系列なので末尾X%をテストに使う
        split_idx = int(len(df) * (1 - test_ratio))
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].copy()

        print(
            f"    学習期間: {train_df.index[0].date()} 〜 {train_df.index[-1].date()}"
        )
        print(
            f"    テスト期間: {test_df.index[0].date()} 〜 {test_df.index[-1].date()}"
        )
        print(f"    テストサンプル数: {len(test_df)}")

        test_df = self._generate_signals(test_df, prob_threshold, rate_threshold)
        perf = self._calc_performance(test_df, holding_days)

        # ベンチマーク: 全期間ひたすら買い持ち（同じく重複除外で計算）
        dummy_all_buy = test_df.copy()
        dummy_all_buy["signal"] = 1
        benchmark_perf = self._calc_performance(dummy_all_buy, holding_days)
        benchmark_ret = benchmark_perf.get("cumulative_return", 0.0)

        result = {
            "code": code,
            "target": target,
            "prob_threshold": prob_threshold,
            "rate_threshold": rate_threshold,
            "benchmark_return": benchmark_ret,
            **perf,
        }

        self._print_result(result)
        return result

    def run_threshold_search(
        self,
        code: str,
        target: str = "target_5d",
        test_ratio: float = 0.2,
        min_trades: int = 15,  # ← 追加: 取引回数が少なすぎる結果を除外
    ) -> pd.DataFrame:
        print(f"\n=== 閾値探索開始: {code} [{target}] (最低{min_trades}取引) ===")

        holding_days = self.HOLDING_DAYS.get(target, 5)

        df = self._prepare_predictions(code, target)
        if df is None or df.empty:
            print("❌ データ不足")
            return pd.DataFrame()

        split_idx = int(len(df) * (1 - test_ratio))
        test_df = df.iloc[split_idx:].copy()

        dummy_all_buy = test_df.copy()
        dummy_all_buy["signal"] = 1
        benchmark_ret = self._calc_performance(
            dummy_all_buy, holding_days
        ).get("cumulative_return", 0.0)

        prob_thresholds = [0.55, 0.60, 0.65, 0.70]
        rate_thresholds = [0.0, 0.01, 0.02, 0.03]

        rows = []
        for prob_th in prob_thresholds:
            for rate_th in rate_thresholds:
                signal_df = self._generate_signals(test_df, prob_th, rate_th)
                perf = self._calc_performance(signal_df, holding_days)
                rows.append(
                    {
                        "prob_threshold": prob_th,
                        "rate_threshold": rate_th,
                        "benchmark_return": round(float(benchmark_ret), 4),
                        **perf,
                    }
                )

        result_df = pd.DataFrame(rows)

        # ===================================================
        # 最低取引回数でフィルター（サンプル数が少ない結果を除外）
        # ===================================================
        valid_df = result_df[result_df["total_trades"] >= min_trades].copy()

        if valid_df.empty:
            print(f"⚠️  最低{min_trades}取引を満たす閾値がありませんでした")
            print("    閾値を下げるか min_trades を減らしてください")
            # フィルターなしで全件表示
            valid_df = result_df

        valid_df = valid_df.sort_values(
            "sharpe_ratio", ascending=False, na_position="last"
        )

        show_cols = [
            "prob_threshold", "rate_threshold",
            "total_trades", "win_rate",
            "cumulative_return", "benchmark_return",
            "sharpe_ratio", "max_drawdown",
        ]
        print("\n【閾値探索結果 Top5（最低取引回数フィルター適用済み）】")
        print(valid_df[show_cols].head(5).to_string(index=False))

        # ベンチマークを上回った閾値だけ表示
        beat_bm = valid_df[
            valid_df["cumulative_return"] > valid_df["benchmark_return"]
        ]
        if not beat_bm.empty:
            print(f"\n✅ ベンチマーク({benchmark_ret:.1%})超えの閾値:")
            print(beat_bm[show_cols].to_string(index=False))
        else:
            print(f"\n⚠️  ベンチマーク({benchmark_ret:.1%})を超える閾値はありませんでした")

        return valid_df

    def run_sector(
        self,
        target: str = "target_5d",
        prob_threshold: float = 0.6,
        rate_threshold: float = 0.0,
        limit: int = 10,
    ) -> pd.DataFrame:
        targets = self.repo.get_learning_targets(self.sector_code, limit=limit)
        print(
            f"\n=== セクターバックテスト: {self.sector_name_en} ({len(targets)}銘柄) ==="
        )

        rows = []
        for code, company_name in targets:
            try:
                result = self.run(
                    code,
                    target=target,
                    prob_threshold=prob_threshold,
                    rate_threshold=rate_threshold,
                )
                if result:
                    result["company_name"] = company_name
                    rows.append(result)
            except Exception as e:
                print(f"⚠️ {code} スキップ: {e}")

        if not rows:
            return pd.DataFrame()

        result_df = pd.DataFrame(rows)

        wins = result_df["cumulative_return"] > result_df["benchmark_return"]
        print("\n【セクター集計】")
        print(f"  銘柄数              : {len(result_df)}")
        print(f"  平均勝率            : {result_df['win_rate'].mean():.1%}")
        print(f"  平均累積リターン    : {result_df['cumulative_return'].mean():.1%}")
        print(f"  平均シャープ        : {result_df['sharpe_ratio'].mean():.3f}")
        print(f"  戦略>ベンチマーク   : {wins.mean():.0%}")

        return result_df.sort_values("sharpe_ratio", ascending=False)

    # ===================================================
    # ユーティリティ
    # ===================================================

    def _print_result(self, result: dict):
        trades = result.get("total_trades", 0)
        if trades == 0:
            print("    シグナル発生なし（閾値が高すぎる可能性）")
            return
        print(f"    取引回数          : {trades}")
        print(f"    勝率              : {result['win_rate']:.1%}")
        print(f"    平均リターン      : {result['avg_return']:.2%}")
        print(f"    累積リターン(戦略): {result['cumulative_return']:.1%}")
        print(f"    累積リターン(BM)  : {result['benchmark_return']:.1%}")
        print(f"    シャープレシオ    : {result['sharpe_ratio']}")
        print(f"    最大ドローダウン  : {result['max_drawdown']:.1%}")
