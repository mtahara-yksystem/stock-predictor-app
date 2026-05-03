import numpy as np
import pandas as pd


class FeatureEngineer:
    def __init__(self):
        self.target_periods = [1, 5, 10]
        self._macro_cols = ["usdjpy", "sp500", "crude_oil", "iron_ore", "us10y"]

    # ===================================================
    # プライベートメソッド（特徴量計算）
    # ===================================================

    def _calc_rsi(self, series, window=14):
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(window=window).mean()
        loss = -delta.clip(upper=0).rolling(window=window).mean()
        rs = gain / loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    def _calc_macd(self, series):
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        return ema12 - ema26

    def _calc_macd_signal(self, series):
        macd = self._calc_macd(series)
        return macd.ewm(span=9, adjust=False).mean()

    def _calc_bb_percent(self, series, window=20):
        """ボリンジャーバンド位置（%B）: 0=下限, 0.5=中央, 1=上限"""
        sma = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        return (series - lower) / (upper - lower).replace(0, float("nan"))

    def _calc_stochastic(self, group_df, k_window=14):
        """ストキャスティクス %K（グループ単位で計算）"""
        high = group_df["H"]
        low = group_df["L"]
        close = group_df["AdjC"]

        lowest_low = low.rolling(window=k_window).min()
        highest_high = high.rolling(window=k_window).max()

        denominator = (highest_high - lowest_low).replace(0, float("nan"))
        stoch_k = 100 * (close - lowest_low) / denominator

        return stoch_k

    def _calc_atr(self, group_df, window=14):
        """ATR（平均トゥルーレンジ）"""
        high = group_df["H"]
        low = group_df["L"]
        close = group_df["AdjC"]

        hl = high - low
        hc = np.abs(high - close.shift())
        lc = np.abs(low - close.shift())

        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(window=window).mean()

    def _merge_macro(self, df: pd.DataFrame, macro_df: pd.DataFrame):
        """マクロ指標を merge_asof で結合する"""
        if macro_df is None or macro_df.empty:
            return df

        macro_df = macro_df.copy()
        macro_df.index = pd.to_datetime(macro_df.index)
        macro_df = macro_df.reset_index().rename(columns={"index": "Date"})
        macro_df["Date"] = pd.to_datetime(macro_df["Date"])

        df["Date"] = pd.to_datetime(df["Date"])

        merged = pd.merge_asof(
            df.sort_values("Date"),
            macro_df.sort_values("Date"),
            on="Date",
            direction="backward",
        )

        return merged

    # ===================================================
    # パブリックメソッド
    # ===================================================

    def create_features_and_targets(
        self, df: pd.DataFrame, macro_df: pd.DataFrame = None
    ):
        """
        Args:
            df: 株価＋財務データ（get_quotes_with_financials_by_sector の返り値）
            macro_df: マクロ指標データ（MacroIndicatorsRepo.get_all_pivoted の返り値）
        """
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        df = df.sort_values(["Code", "Date"]).copy()

        # ===================================================
        # 0. マクロ指標を結合
        # ===================================================
        if macro_df is not None and not macro_df.empty:
            df = self._merge_macro(df, macro_df)
            print(f"✅ マクロ指標を結合しました: {self._macro_cols}")

            for col in self._macro_cols:
                if col in df.columns:
                    df[f"{col}_chg"] = df[col].pct_change(fill_method=None)
        else:
            print("⚠️ マクロ指標なしで学習します。")

        # ===================================================
        # 時間特徴量
        # ===================================================
        df["Date"] = pd.to_datetime(df["Date"])
        df["day_of_week"] = df["Date"].dt.dayofweek
        df["month"] = df["Date"].dt.month
        df["is_month_end"] = df["Date"].dt.is_month_end.astype(int)

        # ===================================================
        # 1. テクニカル特徴量（株価系）
        # ===================================================

        # 移動平均
        df["sma5"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.rolling(window=5).mean()
        )
        df["sma25"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.rolling(window=25).mean()
        )

        # 乖離率
        df["sma_dist"] = (df["AdjC"] - df["sma5"]) / df["sma5"]

        # 過去リターン（モメンタム）
        for p in [1, 5, 10, 25]:
            df[f"return_{p}d"] = df.groupby("Code")["AdjC"].transform(
                lambda x: x.pct_change(periods=p, fill_method=None)
            )

        # ボラティリティ（過去20日の標準偏差）
        df["volatility_20d"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.pct_change(fill_method=None).rolling(window=20).std()
        )

        # RSI（14日）
        df["rsi14"] = df.groupby("Code")["AdjC"].transform(self._calc_rsi)

        # MACD
        df["macd"] = df.groupby("Code")["AdjC"].transform(self._calc_macd)
        df["macd_signal"] = df.groupby("Code")["AdjC"].transform(self._calc_macd_signal)
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # ボリンジャーバンド位置（%B）
        df["bb_percent"] = df.groupby("Code")["AdjC"].transform(self._calc_bb_percent)

        # 出来高変化率
        df["volume_ratio"] = df.groupby("Code")["AdjVo"].transform(
            lambda x: x / x.rolling(window=20).mean()
        )

        # ===================================================
        # 追加テクニカル指標
        # ===================================================

        # ストキャスティクス（グループごとに計算）
        df["stoch_k"] = df.groupby("Code", group_keys=False).apply(
            self._calc_stochastic
        )

        # ATR
        df["atr_14"] = df.groupby("Code", group_keys=False).apply(self._calc_atr)

        # ===================================================
        # ラグ特徴量
        # ===================================================

        # 株価のラグ
        for lag in [1, 3, 5]:
            df[f"close_lag_{lag}"] = df.groupby("Code")["AdjC"].transform(
                lambda x: x.shift(lag)
            )

        # リターンのラグ
        for lag in [1, 3, 5]:
            df[f"return_lag_{lag}"] = df.groupby("Code")["AdjC"].transform(
                lambda x: x.pct_change(fill_method=None).shift(lag)
            )

        # RSIのラグ
        df["rsi_lag_1"] = df.groupby("Code")["rsi14"].transform(lambda x: x.shift(1))

        # ===================================================
        # ローリング統計量
        # ===================================================

        # リターンの統計量
        df["return_mean_5d"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.pct_change(fill_method=None).rolling(window=5).mean()
        )
        df["return_std_5d"] = df.groupby("Code")["AdjC"].transform(
            lambda x: x.pct_change(fill_method=None).rolling(window=5).std()
        )

        # 出来高の標準偏差
        df["volume_std_10d"] = df.groupby("Code")["AdjVo"].transform(
            lambda x: x.rolling(window=10).std()
        )

        # ===================================================
        # 2. 財務特徴量
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
                df[f"{metric}_qoq"] = df.groupby("Code")[metric].transform(
                    lambda x: x.pct_change(periods=60, fill_method=None)
                )
                # 前年同期比（約250営業日）
                df[f"{metric}_yoy"] = df.groupby("Code")[metric].transform(
                    lambda x: x.pct_change(periods=250, fill_method=None)
                )

        # 売上高成長率
        if "Sales" in df.columns:
            df["sales_growth_yoy"] = df.groupby("Code")["Sales"].transform(
                lambda x: x.pct_change(periods=250, fill_method=None)
            )

        # ===================================================
        # 3. マルチターゲットの生成
        # ===================================================
        target_cols = []
        for p in self.target_periods:
            col_name = f"target_{p}d"
            df[col_name] = df.groupby("Code")["AdjC"].transform(
                lambda x: x.pct_change(periods=p, fill_method=None).shift(-p)
            )
            target_cols.append(col_name)

        # ===================================================
        # 4. データのクリーニング
        # ===================================================

        df = df.replace([np.inf, -np.inf], np.nan)

        # 必須カラム（確実に存在するもののみ）
        essential_cols = [
            "sma5",
            "sma25",
            "sma_dist",
            "return_1d",
            "return_5d",
            "rsi14",
            "macd_hist",
            "bb_percent",
            "target_1d",
            "target_5d",
            "target_10d",
            "per",
            "roe",
            "op_margin",
        ]

        initial_len = len(df)
        df = df.dropna(subset=essential_cols)
        print(f"DEBUG: Feature Engineering完了 (保持率: {len(df)}/{initial_len})")

        if df.empty:
            print("⚠️ 警告: dropna後にデータが0件になりました。")
            return pd.DataFrame(), pd.DataFrame()

        # ===================================================
        # 5. 学習に使わないカラムを除外
        # ===================================================
        drop_cols = target_cols + [
            "Date",
            "Code",
            "O",
            "H",
            "L",
            "C",
            "Vo",
            "Va",
            "AdjFactor",
            "UpperLimit",
            "LowerLimit",
            "DiscDate",
            "EPS",
            "BPS",
            "Sales",
            "OP",
            "NP",
            "Eq",
            "EqAR",
        ]
        actual_drop_cols = [c for c in drop_cols if c in df.columns]
        feature_cols = [c for c in df.columns if c not in actual_drop_cols]

        df_features = df[feature_cols].copy()
        df_features.index = df["Date"]

        df_targets = df[target_cols].copy()
        df_targets.index = df["Date"]

        print(f"✅ 特徴量数: {len(feature_cols)}個")
        print(f"✅ 特徴量一覧（最初の10個）: {feature_cols[:10]}")

        return df_features, df_targets
