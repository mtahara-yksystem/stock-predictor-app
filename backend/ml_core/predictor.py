import os
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.macro_indicators_repo import MacroIndicatorsRepo
from ml_core.feature_engineer import FeatureEngineer


class Predictor:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        self.repo = EquitiesMasterRepo()
        self.macro_repo = MacroIndicatorsRepo()
        self.engineer = FeatureEngineer()
        self.targets = ["target_1d", "target_5d", "target_10d"]

    # ===================================================
    # プライベートメソッド
    # ===================================================

    def _load_model(self, sector_code: str, sector_name_en: str, target: str):
        """学習済みモデルを読み込む"""
        model_path = os.path.join(
            self.models_dir,
            f"sector_{sector_code}_{sector_name_en}",
            f"model_{target}.joblib",
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"モデルが見つかりません: {model_path}")
        return joblib.load(model_path)

    def _load_metrics(self, sector_code: str, sector_name_en: str):
        """metrics.json（R2/MAE）を読み込む"""
        import json

        metrics_path = os.path.join(
            self.models_dir,
            f"sector_{sector_code}_{sector_name_en}",
            "metrics.json",
        )
        if not os.path.exists(metrics_path):
            return {}
        with open(metrics_path) as f:
            data = json.load(f)
        return data["metrics"]

    def _get_recent_data(self, code: str, days: int = 120):
        """指定銘柄の直近データを株価＋財務込みで取得する"""

        # DBの最新日を基準に直近N日の株価を取得
        latest_date_df = pd.read_sql(
            "SELECT MAX(Date) as latest FROM DailyQuotes WHERE Code = ?",
            self.repo.engine,
            params=(code,),
        )
        if latest_date_df.empty or latest_date_df.iloc[0]["latest"] is None:
            return None

        latest_date = pd.to_datetime(latest_date_df.iloc[0]["latest"])
        since = (latest_date - timedelta(days=days)).strftime("%Y-%m-%d")

        quotes_df = pd.read_sql(
            "SELECT * FROM DailyQuotes WHERE Code = ? AND Date >= ? ORDER BY Date ASC",
            self.repo.engine,
            params=(code, since),
        )
        if quotes_df.empty:
            return None

        # ★ 財務データは期間を絞らず全件取得（直近120日に開示がない銘柄に対応）
        financials_df = pd.read_sql(
            """SELECT Code, DiscDate, EPS, BPS, EqAR, Sales, OP, NP, Eq
               FROM FinancialSummaries
               WHERE Code = ?
               ORDER BY DiscDate ASC""",
            self.repo.engine,
            params=(code,),
        )
        if financials_df.empty:
            return None

        quotes_df["Date"] = pd.to_datetime(quotes_df["Date"])
        financials_df["DiscDate"] = pd.to_datetime(financials_df["DiscDate"])

        # merge_asof で「その日時点で最新の財務データ」を結合
        merged_df = pd.merge_asof(
            quotes_df.sort_values("Date"),
            financials_df.drop(columns=["Code"]).sort_values("DiscDate"),
            left_on="Date",
            right_on="DiscDate",
            direction="backward",
        )

        return merged_df  # マクロ結合はcreate_features_and_targetsに任せる

    def _build_latest_features(self, df: pd.DataFrame):
        """
        FeatureEngineerで特徴量を生成し、最新の1行だけを返す。
        推論に使うのは最新日のデータのみ。

        注意: 推論時は1銘柄のみなので、groupbyは不要
        """
        df = df.copy()
        df["Code"] = df["Code"].astype(str)
        df = df.sort_values("Date").copy()  # Codeでソート不要（1銘柄のみ）

        # ===================================================
        # 時間特徴量
        # ===================================================
        df["Date"] = pd.to_datetime(df["Date"])
        df["day_of_week"] = df["Date"].dt.dayofweek
        df["month"] = df["Date"].dt.month
        df["is_month_end"] = df["Date"].dt.is_month_end.astype(int)

        # ===================================================
        # テクニカル特徴量（1銘柄なのでgroupby不要）
        # ===================================================

        # 移動平均
        df["sma5"] = df["AdjC"].rolling(window=5).mean()
        df["sma25"] = df["AdjC"].rolling(window=25).mean()
        df["sma_dist"] = (df["AdjC"] - df["sma5"]) / df["sma5"]

        # 過去リターン
        for p in [1, 5, 10, 25]:
            df[f"return_{p}d"] = df["AdjC"].pct_change(periods=p, fill_method=None)

        # ボラティリティ
        df["volatility_20d"] = (
            df["AdjC"].pct_change(fill_method=None).rolling(window=20).std()
        )

        # RSI
        df["rsi14"] = self.engineer._calc_rsi(df["AdjC"])

        # MACD
        df["macd"] = self.engineer._calc_macd(df["AdjC"])
        df["macd_signal"] = self.engineer._calc_macd_signal(df["AdjC"])
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # ボリンジャーバンド
        df["bb_percent"] = self.engineer._calc_bb_percent(df["AdjC"])

        # 出来高比率
        df["volume_ratio"] = df["AdjVo"] / df["AdjVo"].rolling(window=20).mean()

        # ===================================================
        # 追加テクニカル指標（1銘柄なので直接計算）
        # ===================================================

        # ストキャスティクス %K
        k_window = 14
        lowest_low = df["L"].rolling(window=k_window).min()
        highest_high = df["H"].rolling(window=k_window).max()
        denominator = (highest_high - lowest_low).replace(0, float("nan"))
        df["stoch_k"] = 100 * (df["AdjC"] - lowest_low) / denominator

        # ATR
        atr_window = 14
        hl = df["H"] - df["L"]
        hc = np.abs(df["H"] - df["AdjC"].shift())
        lc = np.abs(df["L"] - df["AdjC"].shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(window=atr_window).mean()

        # ===================================================
        # ラグ特徴量
        # ===================================================

        # 株価のラグ
        for lag in [1, 3, 5]:
            df[f"close_lag_{lag}"] = df["AdjC"].shift(lag)

        # リターンのラグ
        for lag in [1, 3, 5]:
            df[f"return_lag_{lag}"] = df["AdjC"].pct_change(fill_method=None).shift(lag)

        # RSIのラグ
        df["rsi_lag_1"] = df["rsi14"].shift(1)

        # ===================================================
        # ローリング統計量
        # ===================================================

        # リターンの統計量
        returns = df["AdjC"].pct_change(fill_method=None)
        df["return_mean_5d"] = returns.rolling(window=5).mean()
        df["return_std_5d"] = returns.rolling(window=5).std()

        # 出来高の標準偏差
        df["volume_std_10d"] = df["AdjVo"].rolling(window=10).std()

        # ===================================================
        # 財務特徴量
        # ===================================================

        financial_raw_cols = ["EPS", "BPS", "EqAR", "Sales", "OP", "NP", "Eq"]
        for col in financial_raw_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["per"] = np.where(df["EPS"] > 0, df["AdjC"] / df["EPS"], np.nan)
        df["eq_ar"] = df["EqAR"]
        df["op_margin"] = np.where(df["Sales"] > 0, df["OP"] / df["Sales"], np.nan)
        df["roe"] = np.where(df["Eq"] > 0, df["NP"] / df["Eq"], np.nan)

        # ===================================================
        # 財務指標の変化率
        # ===================================================

        financial_metrics = ["per", "roe", "op_margin"]

        for metric in financial_metrics:
            if metric in df.columns:
                # 前四半期比（約60営業日）
                df[f"{metric}_qoq"] = df[metric].pct_change(
                    periods=60, fill_method=None
                )
                # 前年同期比（約250営業日）
                df[f"{metric}_yoy"] = df[metric].pct_change(
                    periods=250, fill_method=None
                )

        # 売上高成長率
        if "Sales" in df.columns:
            df["sales_growth_yoy"] = df["Sales"].pct_change(
                periods=250, fill_method=None
            )

        # ===================================================
        # クリーニング
        # ===================================================

        df = df.replace([np.inf, -np.inf], np.nan)

        # 最新行だけ取得
        latest = df.iloc[[-1]].copy()

        return latest

    # ===================================================
    # パブリックメソッド
    # ===================================================

    def predict(self, code: str):
        """
        指定銘柄の予測値を返す。

        Returns:
            {
                "code": "5401",
                "company_name": "日本製鉄",
                "current_price": 3000.0,
                "price_change_rate": 0.012,
                "predictions": {
                    "target_1d":  {"rate": 0.005, "up_prob": 0.58},
                    "target_5d":  {"rate": 0.012, "up_prob": 0.63},
                    "target_10d": {"rate": 0.021, "up_prob": 0.67},
                },
                "metrics": {
                    "target_1d":  {"mae": 0.0135, "r2": 0.0053},
                    "target_5d":  {"mae": 0.0300, "r2": 0.0206},
                    "target_10d": {"mae": 0.0445, "r2": 0.0062},
                }
            }
        """

        # 1. セクター情報を取得
        company_and_sector = pd.read_sql(
            "SELECT CoName, S17 FROM EquitiesMaster WHERE Code = ?",
            self.repo.engine,
            params=(code,),
        )
        if company_and_sector.empty:
            raise ValueError(f"銘柄 {code} のセクター情報が見つかりません。")

        sector_code = company_and_sector.iloc[0]["S17"]
        company_name = company_and_sector.iloc[0]["CoName"]
        sector_name_en = self.repo.get_sector_info_by_code(sector_code)["S17NmEn"]

        # 2. 直近データを取得（★ days を 120 に拡大 — 特徴量計算に必要なウィンドウ分を確保）
        df = self._get_recent_data(code, days=120)
        if df is None or df.empty:
            raise ValueError(f"銘柄 {code} のデータがDBに存在しません。")

        # 3. ★ feature_engineer で特徴量を生成（学習時と完全に同じロジック）
        df["Code"] = code  # ★ Code列が確実に存在するよう補完
        macro_df = self.macro_repo.get_all_pivoted()
        X, _ = self.engineer.create_features_and_targets(df, macro_df=macro_df)

        if X.empty:
            raise ValueError(f"銘柄 {code} の特徴量生成に失敗しました。")

        # 最新の1行だけ使う
        latest = X.iloc[[-1]].copy()

        # 4. 銘柄基本情報を取得（変更なし）
        current_price = float(df["AdjC"].iloc[-1])
        prev_price = float(df["AdjC"].iloc[-2]) if len(df) >= 2 else current_price
        price_change_rate = (current_price - prev_price) / prev_price

        # 5. 各ターゲットのモデルで推論（変更なし）
        metrics = self._load_metrics(sector_code, sector_name_en)
        predictions = {}

        for target in self.targets:
            save_data = self._load_model(sector_code, sector_name_en, target)
            model = save_data["model"]
            feature_names = save_data["feature_names"]
            model_type = save_data.get("model_type", "regressor")

            missing_features = [f for f in feature_names if f not in latest.columns]
            if missing_features:
                print(f"⚠️ 特徴量欠損（0埋め）: {missing_features}")
                for feat in missing_features:
                    latest[feat] = 0.0

            X_input = latest[feature_names].values

            if model_type == "classifier":
                up_probability = float(model.predict_proba(X_input)[0, 1])
                predicted_rate = (up_probability - 0.5) * 0.1
            else:
                scaler = save_data.get("scaler")
                if scaler is not None:
                    X_input = scaler.transform(X_input)
                predicted_rate = float(model.predict(X_input)[0]) / 100
                up_probability = float(np.clip(0.5 + predicted_rate * 10, 0.0, 1.0))

            predictions[target] = {
                "rate": round(predicted_rate, 6),
                "up_prob": round(up_probability, 4),
            }

        return {
            "code": code,
            "company_name": company_name,
            "current_price": current_price,
            "price_change_rate": round(price_change_rate, 6),
            "pred_date": datetime.now().strftime("%Y-%m-%d"),
            "predictions": predictions,
            "metrics": metrics,
        }
