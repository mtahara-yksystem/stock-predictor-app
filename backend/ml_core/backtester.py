from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.macro_indicators_repo import MacroIndicatorsRepo
from ml_core.feature_engineer import FeatureEngineer


class Backtester:
    def __init__(self, sector_code: str):
        self.sector_code = sector_code
        self.repo = EquitiesMasterRepo()
        self.macro_repo = MacroIndicatorsRepo()
        self.engineer = FeatureEngineer()

        # モデルパスの設定 (開発規約に従う)
        # 例: models/sector_7_steel/model.joblib
        sector_info = self.repo.get_sector_info_by_code(sector_code)
        self.model_dir = (
            Path("models") / f"sector_{sector_code}_{sector_info['S17NmEn']}"
        )

    def load_model_assets(self):
        """学習済みモデルとスケーラーをロード"""
        model = joblib.load(self.model_dir / "model.joblib")
        scaler = joblib.load(self.model_dir / "scaler.joblib")
        features = joblib.load(self.model_dir / "feature_names.joblib")
        return model, scaler, features

    def run(self, code: str):
        print(f"--- Backtest Start: {code} ---")

        # 1. DBからデータ取得
        raw_df = self.repo.get_quotes_with_financials_by_sector(self.sector_code)
        # 特定の銘柄のみに絞り込み
        raw_df = raw_df[raw_df["Code"] == code].copy()

        macro_df = self.macro_repo.get_all_pivoted()

        if raw_df.empty or macro_df.empty:
            print("❌ データが不足しています。")
            return

        # 2. 特徴量生成 (trainer.pyと同じロジックを使用)
        X, y_all = self.engineer.create_features_and_targets(raw_df, macro_df=macro_df)

        # ターゲット（例：5日後の騰落率）を選択
        target_col = "target_5d"
        y = y_all[target_col]

        # 3. モデル等のロード
        model, scaler, feature_names = self.load_model_assets()

        # 4. バックテスト期間の分割 (直近20%を検証用とする)
        split_idx = int(len(X) * 0.8)
        X_test = X.iloc[split_idx:]
        y_test = y.iloc[split_idx:]

        # FeatureEngineer で X のインデックスは既に Date (DatetimeIndex) に設定されているため
        # そのまま利用できます
        test_dates = X_test.index

        # 5. 推論
        X_test_scaled = scaler.transform(X_test[feature_names])
        preds = model.predict(X_test_scaled)

        # 6. シミュレーション
        results = pd.DataFrame(
            {"actual_ret": y_test, "pred_ret": preds}, index=test_dates
        )  # ここで test_dates (日付) を index にセット

        # 戦略: 予測がプラスなら買い
        results["signal"] = np.where(results["pred_ret"] > 0, 1, 0)
        results["strategy_ret"] = results["signal"] * results["actual_ret"]

        # 累積リターン
        results["cum_strategy"] = (1 + results["strategy_ret"]).cumprod()
        results["cum_market"] = (1 + results["actual_ret"]).cumprod()

        self._print_metrics(results)
        self._plot_results(results, code)

    def run_sector_backtest(self, limit=10):
        """セクター内の全銘柄（または上位n銘柄）を巡回してバックテストを実行"""
        # 1. セクター内の銘柄リストを取得
        targets = self.repo.get_learning_targets(self.sector_code, limit=limit)  #
        print(
            f"📊 セクター {self.sector_code} の {len(targets)} 銘柄でバックテストを開始します..."
        )

        all_results = []

        for code, name in targets:
            try:
                # 各銘柄のバックテストを実行（可視化はオフにするなどの調整が可能）
                # ここでは簡易的にリターンだけを収集するイメージ
                res = self._calculate_metrics_only(code)
                if res is not None:
                    all_results.append(res)
                    print(f"✅ {code} {name[:10]}: Return {res['final_return']:.2%}")
            except Exception as e:
                print(f"❌ {code} エラー: {e}")

        # 2. セクター全体の統計を算出
        if all_results:
            df_sector = pd.DataFrame(all_results)
            print("\n" + "=" * 30)
            print(f"【セクター {self.sector_code} バックテスト集計】")
            print(f"平均リターン: {df_sector['final_return'].mean():.2%}")
            print(f"平均勝率    : {df_sector['win_rate'].mean():.2%}")
            print(f"プラス銘柄比率: {(df_sector['final_return'] > 0).mean():.2%}")
            print("=" * 30)

    def _print_metrics(self, results):
        final_ret = results["cum_strategy"].iloc[-1] - 1
        market_ret = results["cum_market"].iloc[-1] - 1
        win_rate = (results[results["signal"] > 0]["strategy_ret"] > 0).mean()

        print("\n[結果報告]")
        print(f"戦略累計リターン: {final_ret:.2%}")
        print(f"市場累計リターン: {market_ret:.2%}")
        print(f"シグナル発生時勝率: {win_rate:.2%}")

    def _plot_results(self, results, code):
        plt.figure(figsize=(10, 5))
        plt.plot(results["cum_strategy"], label="AI Strategy")
        plt.plot(results["cum_market"], label="Market (Buy & Hold)", linestyle="--")
        plt.title(f"Backtest Result: {code}")
        plt.legend()
        plt.grid(True)
        plt.show()
