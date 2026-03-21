import json
import os

import joblib
from ml_core.engine import build_and_train_model, evaluate_model


class Trainer:
    def __init__(self, sector_code, sector_name):
        self.sector_code = sector_code
        self.sector_name = sector_name

        # 保存先を "models/sector_7_steel" のような形式にする
        self.model_dir = f"models/sector_{sector_code}_{sector_name}"

        os.makedirs(self.model_dir, exist_ok=True)
        self.targets = ["target_1d", "target_5d", "target_10d"]

    def train(self, X, y_all):
        """
        X: 特徴量データ
        y_all: target_1d, 5d, 10d が含まれるDataFrame
        """

        print(f"DEBUG: 特徴量生成後の総行数: {len(X)}")

        if len(X) < 50:
            print(
                "⚠️ データが少なすぎます。DBの取得期間を延ばすか、銘柄を確認してください。"
            )
            return

        # --- データの分割 (Train/Test) ---
        # 時系列データなので、後ろの方をテストデータにする
        split_date = X.index.sort_values()[int(len(X) * 0.8)]
        X_train = X[X.index <= split_date]
        X_test = X[X.index > split_date]

        print(
            f"📅 Train期間: {X_train.index.min().date()} 〜 {X_train.index.max().date()}"
        )
        print(
            f"📅 Test期間:  {X_test.index.min().date()} 〜 {X_test.index.max().date()}"
        )

        metrics_summary = {}

        for target_col in self.targets:
            print(f"🌲 {self.sector_name} [{target_col}] の学習を開始...")

            y = y_all[target_col]
            print(
                f"📊 {target_col} -> 平均: {y.mean():.4f}, 標準偏差: {y.std():.4f}, 範囲: [{y.min():.4f}, {y.max():.4f}]"
            )
            y_train = y[y.index <= split_date]
            y_test = y[y.index > split_date]

            # --- 学習（X_test を early_stopping の val として渡す）---
            model, scaler = build_and_train_model(X_train, y_train, X_test, y_test)

            # --- 評価 ---
            preds, mae, r2 = evaluate_model(model, scaler, X_test, y_test)

            print(f"📊 {target_col} 評価結果 -> MAE: {mae:.4f}, R2: {r2:.4f}")

            # --- 保存 ---
            save_data = {
                "model": model,
                "scaler": scaler,
                "feature_names": X.columns.tolist(),
            }
            model_path = os.path.join(self.model_dir, f"model_{target_col}.joblib")
            joblib.dump(save_data, model_path)

            metrics_summary[target_col] = {"mae": mae, "r2": r2}

        # --- 成績表(metrics)をJSONで保存 ---
        with open(os.path.join(self.model_dir, "metrics.json"), "w") as f:
            json.dump(metrics_summary, f, indent=4)

        print(f"✨ 全ターゲットの学習が完了しました。保存先: {self.model_dir}")
