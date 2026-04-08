import os
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from app.db.equities_master_repo import EquitiesMasterRepo

# __init__ に MacroIndicatorsRepo を追加
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

    def _get_recent_data(self, code: str, days: int = 60):
        """指定銘柄の直近データを株価＋財務込みで取得する"""

        # datetime.now() ではなく DB の最新日を基準にする
        # （無料版J-Quantsは直近12週のデータがないため）
        latest_date_df = pd.read_sql(
            "SELECT MAX(Date) as latest FROM DailyQuotes WHERE Code = ?",
            self.repo.engine,
            params=(code,),
        )
        if latest_date_df.empty or latest_date_df.iloc[0]["latest"] is None:
            return None

        latest_date = pd.to_datetime(latest_date_df.iloc[0]["latest"])
        since = (latest_date - timedelta(days=days)).strftime("%Y-%m-%d")

        # 株価データ
        quotes_query = """
            SELECT q.* FROM DailyQuotes q
            WHERE q.Code = ?
            AND q.Date >= ?
            ORDER BY q.Date ASC
        """
        quotes_df = pd.read_sql(quotes_query, self.repo.engine, params=(code, since))

        print(f"{code}: {quotes_df} {since}")
        if quotes_df.empty:
            return None

        # 財務データ
        financials_query = """
            SELECT Code, DiscDate, EPS, BPS, EqAR, Sales, OP, NP, Eq
            FROM FinancialSummaries
            WHERE Code = ?
            ORDER BY DiscDate ASC
        """
        financials_df = pd.read_sql(financials_query, self.repo.engine, params=(code,))

        if financials_df.empty:
            return None

        # 日付型に統一
        quotes_df["Date"] = pd.to_datetime(quotes_df["Date"])
        financials_df["DiscDate"] = pd.to_datetime(financials_df["DiscDate"])

        # merge_asof でルックアヘッドバイアスなく結合
        merged_df = pd.merge_asof(
            quotes_df.sort_values("Date"),
            financials_df.drop(columns=["Code"]),
            left_on="Date",
            right_on="DiscDate",
            direction="backward",
        )

        macro_df = self.macro_repo.get_all_pivoted()
        if not macro_df.empty:
            macro_df = macro_df.reset_index().rename(columns={"index": "Date"})
            macro_df["Date"] = pd.to_datetime(macro_df["Date"])
            merged_df = pd.merge_asof(
                merged_df.sort_values("Date"),
                macro_df.sort_values("Date"),
                on="Date",
                direction="backward",
            )
            # 変化率を追加
            macro_cols = ["usdjpy", "sp500", "us10y"]
            for col in macro_cols:
                if col in merged_df.columns:
                    merged_df[f"{col}_chg"] = merged_df[col].pct_change(
                        fill_method=None
                    )

        return merged_df

    def _build_latest_features(self, df: pd.DataFrame):
        """
        FeatureEngineerで特徴量を生成し、最新の1行だけを返す。
        推論に使うのは最新日のデータのみ。
        """
        # FeatureEngineer はターゲット列も生成するが、推論時は不要なので無視する
        # target_*d は未来データなので NaN になり dropna で除外されてしまう
        # → essential_cols からターゲットを外した推論用モードが必要なため
        #   ここでは直接特徴量だけ作る

        df = df.copy()
        df["Code"] = df["Code"].astype(str)

        # FeatureEngineer の特徴量生成部分だけ呼ぶ（ターゲット生成は不要）
        # 内部実装と同じ処理を再現する
        df = df.sort_values(["Code", "Date"]).copy()

        # テクニカル
        df["sma5"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.rolling(window=5).mean()
        )
        df["sma25"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.rolling(window=25).mean()
        )
        df["sma_dist"] = (df["AdjC"] - df["sma5"]) / df["sma5"]

        for p in [1, 5, 10, 25]:
            df[f"return_{p}d"] = df.groupby("Code")["AdjC"].transform(
                lambda x: x.pct_change(periods=p, fill_method=None)
            )

        df["volatility_20d"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.pct_change(fill_method=None).rolling(window=20).std()
        )
        df["rsi14"] = df.groupby("Code")["AdjC"].transform(self.engineer._calc_rsi)
        df["macd"] = df.groupby("Code")["AdjC"].transform(self.engineer._calc_macd)
        df["macd_signal"] = df.groupby("Code")["AdjC"].transform(
            self.engineer._calc_macd_signal
        )
        df["macd_hist"] = df["macd"] - df["macd_signal"]
        df["bb_percent"] = df.groupby("Code")["AdjC"].transform(
            self.engineer._calc_bb_percent
        )
        df["volume_ratio"] = df.groupby("Code")["AdjVo"].transform(
            lambda x: x / x.rolling(window=20).mean()
        )

        # 財務
        financial_raw_cols = ["EPS", "BPS", "EqAR", "Sales", "OP", "NP", "Eq"]
        for col in financial_raw_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["per"] = np.where(df["EPS"] > 0, df["AdjC"] / df["EPS"], np.nan)
        df["eq_ar"] = df["EqAR"]
        df["op_margin"] = np.where(df["Sales"] > 0, df["OP"] / df["Sales"], np.nan)
        df["roe"] = np.where(df["Eq"] > 0, df["NP"] / df["Eq"], np.nan)

        # inf を NaN に変換
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

        # 2. 直近60日の株価＋財務データを取得
        df = self._get_recent_data(code, days=60)
        if df is None or df.empty:
            raise ValueError(f"銘柄 {code} のデータがDBに存在しません。")

        # 3. 特徴量を生成（最新の1行）
        latest = self._build_latest_features(df)

        # 4. 銘柄基本情報を取得
        current_price = float(latest["AdjC"].iloc[0])
        prev_price = float(df["AdjC"].iloc[-2]) if len(df) >= 2 else current_price
        price_change_rate = (current_price - prev_price) / prev_price

        # 5. 各ターゲットのモデルで推論
        metrics = self._load_metrics(sector_code, sector_name_en)
        predictions = {}

        for target in self.targets:
            save_data = self._load_model(sector_code, sector_name_en, target)
            model = save_data["model"]
            scaler = save_data["scaler"]
            feature_names = save_data["feature_names"]

            # モデルが期待する特徴量だけを抽出・順序を揃える
            X = latest[feature_names].values
            X_scaled = scaler.transform(X)

            # 予測（学習時に*100しているので/100で戻す）
            predicted_rate = float(model.predict(X_scaled)[0]) / 100
            up_probability = float(np.clip(0.5 + predicted_rate * 10, 0.0, 1.0))

            predictions[target] = {
                "rate": round(predicted_rate, 6),  # 騰落率
                "up_prob": round(up_probability, 4),  # 上がる確率
            }

        return {
            "code": code,
            "company_name": company_name,
            "current_price": current_price,
            "price_change_rate": round(price_change_rate, 6),
            "pred_date": datetime.now().strftime("%Y-%m-%d"),  # ← 追加
            "predictions": predictions,
            "metrics": metrics,
        }
