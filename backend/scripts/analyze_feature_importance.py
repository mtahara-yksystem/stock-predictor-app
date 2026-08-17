"""
scripts/analyze_feature_importance.py

全セクターのモデルから特徴量重要度を集計して、
削除候補（重要度が低い・ノイズになっている特徴量）を特定する。

実行方法:
    cd backend
    python scripts/analyze_feature_importance.py
"""

import json
from pathlib import Path

import joblib
import pandas as pd

MODELS_DIR = Path("models")
TARGETS = ["target_1d", "target_5d", "target_10d"]


def load_all_importances():
    """全セクター・全ターゲットの特徴量重要度を収集する"""
    records = []

    for sector_dir in sorted(MODELS_DIR.glob("sector_*")):
        if not sector_dir.is_dir():
            continue

        sector_name = sector_dir.name

        # metrics.json から方向正解率を取得
        metrics_path = sector_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                metrics = json.load(f)
        else:
            metrics = {}

        for target in TARGETS:
            model_path = sector_dir / f"model_{target}.joblib"
            if not model_path.exists():
                continue

            save_data = joblib.load(model_path)
            model = save_data["model"]
            feature_names = save_data["feature_names"]
            model_type = save_data.get("model_type", "regressor")

            if model_type != "classifier":
                print(f"⚠️  {sector_name}/{target}: 旧モデル（回帰）はスキップ")
                continue

            importances = model.feature_importances_
            dir_acc = (
                metrics.get("metrics", {})
                .get(target, {})
                .get("direction_accuracy", None)
            )

            for feat, imp in zip(feature_names, importances):
                records.append(
                    {
                        "sector": sector_name,
                        "target": target,
                        "feature": feat,
                        "importance": imp,
                        "direction_accuracy": dir_acc,
                    }
                )

    return pd.DataFrame(records)


def analyze(df: pd.DataFrame):
    """重要度を集計して削除候補を出力する"""

    # ===================================================
    # 1. 全セクター・全ターゲットの平均重要度（上位・下位）
    # ===================================================
    mean_imp = (
        df.groupby("feature")["importance"]
        .agg(["mean", "std", "min", "max", "count"])
        .sort_values("mean", ascending=False)
        .reset_index()
    )
    mean_imp.columns = ["feature", "mean_imp", "std_imp", "min_imp", "max_imp", "count"]

    print("\n" + "=" * 60)
    print("📊 全セクター平均 特徴量重要度 TOP 20")
    print("=" * 60)
    print(mean_imp.head(20).to_string(index=False))

    print("\n" + "=" * 60)
    print("🗑️  全セクター平均 特徴量重要度 BOTTOM 20（削除候補）")
    print("=" * 60)
    print(mean_imp.tail(20).to_string(index=False))

    # ===================================================
    # 2. 重要度が全セクターで常に低い特徴量（ノイズ候補）
    # ===================================================
    # mean_imp が閾値未満 かつ max_imp も低い = どのセクターでも使われていない
    threshold_mean = 0.005  # 平均重要度0.5%未満
    threshold_max = 0.02  # 最大でも2%未満

    noise_features = mean_imp[
        (mean_imp["mean_imp"] < threshold_mean) & (mean_imp["max_imp"] < threshold_max)
    ]["feature"].tolist()

    print("\n" + "=" * 60)
    print(f"🚨 ノイズ候補特徴量（mean<{threshold_mean}, max<{threshold_max}）")
    print("=" * 60)
    for f in noise_features:
        row = mean_imp[mean_imp["feature"] == f].iloc[0]
        print(f"  {f:<35} mean={row['mean_imp']:.4f}  max={row['max_imp']:.4f}")

    # ===================================================
    # 3. ターゲット別の重要特徴量トップ10
    # ===================================================
    for target in TARGETS:
        target_df = df[df["target"] == target]
        top10 = (
            target_df.groupby("feature")["importance"]
            .mean()
            .sort_values(ascending=False)
            .head(10)
        )
        print(f"\n{'=' * 60}")
        print(f"🎯 {target} — 重要特徴量 TOP 10（全セクター平均）")
        print("=" * 60)
        for feat, imp in top10.items():
            print(f"  {feat:<35} {imp:.4f}")

    # ===================================================
    # 4. セクター別の方向正解率と重要特徴量の関係
    # ===================================================
    sector_acc = (
        df[df["target"] == "target_5d"]
        .groupby("sector")["direction_accuracy"]
        .first()
        .sort_values(ascending=False)
    )
    print(f"\n{'=' * 60}")
    print("📈 target_5d 方向正解率（セクター別）")
    print("=" * 60)
    for sector, acc in sector_acc.items():
        bar = "█" * int((acc - 0.45) * 100) if acc else ""
        acc_str = f"{acc:.4f}" if acc else "N/A"
        print(f"  {sector:<35} {acc_str}  {bar}")

    # ===================================================
    # 5. 削除推奨リストをJSONで保存
    # ===================================================
    output = {
        "noise_features": noise_features,
        "top20_features": mean_imp.head(20)["feature"].tolist(),
        "bottom20_features": mean_imp.tail(20)["feature"].tolist(),
    }
    out_path = MODELS_DIR / "feature_analysis.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n💾 分析結果を保存しました: {out_path}")
    print(f"   ノイズ候補: {len(noise_features)}個")

    return mean_imp, noise_features


if __name__ == "__main__":
    print("📥 全モデルから特徴量重要度を読み込み中...")
    df = load_all_importances()

    if df.empty:
        print("❌ モデルが見つかりません。先に train_model を実行してください。")
        exit(1)

    print(
        f"✅ {df['sector'].nunique()}セクター × {df['target'].nunique()}ターゲット × "
        f"{df['feature'].nunique()}特徴量 を読み込みました"
    )

    mean_imp, noise_features = analyze(df)
