import numpy as np
import pandas as pd


class FeatureEngineer:
    def __init__(self):
        self.target_periods = [1, 5, 10]

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

    # ===================================================
    # パブリックメソッド
    # ===================================================

    def create_features_and_targets(self, df: pd.DataFrame):
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # CodeとDateでソートして、銘柄ごとにデータが並ぶようにする
        df = df.sort_values(["Code", "Date"]).copy()

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
        df["macd_hist"] = df["macd"] - df["macd_signal"]  # 勢いの変化

        # ボリンジャーバンド位置（%B）
        df["bb_percent"] = df.groupby("Code")["AdjC"].transform(self._calc_bb_percent)

        # 出来高変化率（直近の出来高が20日平均の何倍か）
        df["volume_ratio"] = df.groupby("Code")["AdjVo"].transform(
            lambda x: x / x.rolling(window=20).mean()
        )

        # ===================================================
        # 2. 財務特徴量（FinancialSummariesから結合済みのカラムを使用）
        # ===================================================

        # 財務カラムを数値型に変換（DBから文字列で取得される場合があるため）
        financial_raw_cols = ["EPS", "BPS", "EqAR", "Sales", "OP", "NP", "Eq"]
        for col in financial_raw_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # PER（株価収益率）: 低いほど割安
        df["per"] = np.where(
            df["EPS"] > 0,
            df["AdjC"] / df["EPS"],
            np.nan,  # EPSが0以下は意味がないのでNaN
        )

        # 自己資本比率（そのまま使用）
        df["eq_ar"] = df["EqAR"]

        # 営業利益率: 高いほど収益性が高い
        df["op_margin"] = np.where(
            df["Sales"] > 0,
            df["OP"] / df["Sales"],
            np.nan,
        )

        # ROE（自己資本利益率）: 高いほど効率的
        df["roe"] = np.where(
            df["Eq"] > 0,
            df["NP"] / df["Eq"],
            np.nan,
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

        # inf を NaN に変換
        df = df.replace([np.inf, -np.inf], np.nan)

        # 必須カラムがNaNの行を除外
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
            "DiscDate",  # merge_asof で追加された結合キー
            "EPS",
            "BPS",  # per に変換済みなので除外
            "Sales",
            "OP",
            "NP",
            "Eq",  # op_margin / roe に変換済みなので除外
            "EqAR",  # eq_ar として変換済み
        ]
        actual_drop_cols = [c for c in drop_cols if c in df.columns]
        feature_cols = [c for c in df.columns if c not in actual_drop_cols]

        # Date をインデックスに設定して返す
        df_features = df[feature_cols].copy()
        df_features.index = df["Date"]

        df_targets = df[target_cols].copy()
        df_targets.index = df["Date"]

        return df_features, df_targets
