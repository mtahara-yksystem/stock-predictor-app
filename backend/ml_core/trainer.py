import json
import os

import joblib
import numpy as np
from ml_core.engine import build_and_train_model, evaluate_model

HYPERPARAMS = {
    "target_1d": {"max_depth": 5, "colsample_bytree": 0.6},
    "target_5d": {"max_depth": 6, "colsample_bytree": 0.7},
    "target_10d": {"max_depth": 7, "colsample_bytree": 0.8},
}

# ノイズゾーンの閾値（この絶対値未満のサンプルは学習から除外）
DEAD_ZONE_THRESHOLD = {
    "target_1d": 0.005,  # ±0.5%（翌日は動きが小さいのでそのまま）
    "target_5d": 0.015,  # ±1.5%（5日では適度な閾値）
    "target_10d": 0.02,  # ±2.0%（10日はそのまま）
}


def _to_class_label(y_regression, threshold=DEAD_ZONE_THRESHOLD):
    """
    回帰ターゲット（騰落率）を分類ラベルに変換する。

    - 上昇（> +threshold）  → 1
    - 下落（< -threshold）  → 0
    - ノイズゾーン内        → NaN（学習から除外）

    Returns: pd.Series（NaNを含む）
    """
    import pandas as pd

    labels = pd.Series(np.nan, index=y_regression.index)
    labels[y_regression > threshold] = 1
    labels[y_regression < -threshold] = 0
    return labels


class Trainer:
    def __init__(self, sector_code, sector_name):
        self.sector_code = sector_code
        self.sector_name = sector_name
        self.model_dir = f"models/sector_{sector_code}_{sector_name}"
        os.makedirs(self.model_dir, exist_ok=True)
        self.targets = ["target_1d", "target_5d", "target_10d"]

    def train(self, X, y_all):
        print(f"DEBUG: 特徴量生成後の総行数: {len(X)}")

        if len(X) < 50:
            print("⚠️ データが少なすぎます。")
            return

        split_date = X.index.sort_values()[int(len(X) * 0.9)]
        X_train = X[X.index <= split_date]
        X_test = X[X.index > split_date]

        print(
            f"📅 Train期間: {X_train.index.min().date()} 〜 {X_train.index.max().date()}"
        )
        print(
            f"📅 Test期間:  {X_test.index.min().date()} 〜 {X_test.index.max().date()}"
        )

        metrics_summary = {}
        hyperparams_summary = {}

        for target_col in self.targets:
            y_raw = y_all[target_col]
            # ★ ターゲットごとの閾値を適用
            threshold = DEAD_ZONE_THRESHOLD[target_col]
            y_labeled = _to_class_label(y_raw, threshold=threshold)

            # ② ノイズゾーンのサンプルを除外
            valid_mask_train = y_labeled[y_labeled.index <= split_date].notna()
            valid_mask_test = y_labeled[y_labeled.index > split_date].notna()

            X_tr = X_train[valid_mask_train]
            y_tr = y_labeled[y_labeled.index <= split_date][valid_mask_train].astype(
                int
            )
            X_te = X_test[valid_mask_test]
            y_te = y_labeled[y_labeled.index > split_date][valid_mask_test].astype(int)

            total = len(y_labeled)
            kept = len(y_tr) + len(y_te)
            removed = total - kept
            print(
                f"   ノイズ除外: {removed}件除外 ({removed / total * 100:.1f}%) → 残り{kept}件"
            )
            print(
                f"   クラス比率(train): 上昇={y_tr.mean():.2f}, 下落={1 - y_tr.mean():.2f}"
            )

            if len(y_tr) < 30:
                print("⚠️ 学習サンプルが不足しています。スキップします。")
                continue

            params = HYPERPARAMS[target_col]
            print(
                f"⚙️  max_depth={params['max_depth']}, colsample_bytree={params['colsample_bytree']}"
            )

            model, scaler = build_and_train_model(
                X_tr,
                y_tr,
                X_te,
                y_te,
                max_depth=params["max_depth"],
                colsample_bytree=params["colsample_bytree"],
            )

            _, mae, r2, dir_acc = evaluate_model(model, scaler, X_te, y_te)
            print(f"📊 {target_col} 方向正解率: {dir_acc:.4f}  (log_loss: {mae:.4f})")

            # ③ 保存（scalerはNoneだが構造は維持）
            save_data = {
                "model": model,
                "scaler": scaler,  # None
                "feature_names": X.columns.tolist(),
                "model_type": "classifier",  # 新規追加：推論側で判別するため
            }
            model_path = os.path.join(self.model_dir, f"model_{target_col}.joblib")
            joblib.dump(save_data, model_path)

            metrics_summary[target_col] = {
                "mae": mae,
                "r2": r2,
                "direction_accuracy": dir_acc,
            }
            hyperparams_summary[target_col] = params

        output = {"metrics": metrics_summary, "hyperparams": hyperparams_summary}
        with open(os.path.join(self.model_dir, "metrics.json"), "w") as f:
            json.dump(output, f, indent=4)

        print(f"\n✨ 全ターゲットの学習完了。保存先: {self.model_dir}")
