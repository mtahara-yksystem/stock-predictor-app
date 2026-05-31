# backend/batch/generate_signals.py

"""
PredictionsCacheに保存済みの予測値を読み込み、
シグナルを判定してSignalCacheに保存する。

predict_all.py の後に実行する想定。
"""

import traceback

import pandas as pd
from app.db.base import Database
from app.db.signal_cache_repo import SignalCacheRepo
from ml_core.signal_generator import SignalGenerator


def run_generate_signals(target: str = "target_5d"):
    db = Database()
    signal_repo = SignalCacheRepo()
    generator = SignalGenerator()

    # PredictionsCacheから最新日の全銘柄を取得
    rate_col = f"Rate{target.replace('target_', '')}"  # Rate5d
    prob_col = f"UpProb{target.replace('target_', '')}"  # UpProb5d

    df = pd.read_sql(
        f"""
        SELECT Code, PredDate, {rate_col}, {prob_col}
        FROM PredictionsCache
        WHERE PredDate = (SELECT MAX(PredDate) FROM PredictionsCache)
    """,
        db.engine,
    )

    if df.empty:
        print("⚠️  PredictionsCacheにデータがありません。")
        print("   先に batch/predict_all.py を実行してください。")
        return

    today = df["PredDate"].iloc[0]
    print(f"📅 対象日: {today}  銘柄数: {len(df)}")

    buy_count = 0
    hold_count = 0
    error_count = 0

    for _, row in df.iterrows():
        try:
            up_prob = float(row[prob_col]) if row[prob_col] is not None else 0.0
            pred_rate = float(row[rate_col]) if row[rate_col] is not None else 0.0

            result = generator.generate(up_prob, pred_rate)

            signal_repo.save(
                {
                    "code": str(row["Code"]),
                    "signal_date": today,
                    "target": target,
                    "signal": result["signal"],
                    "strength": result["strength"] or "NONE",
                    "up_prob": up_prob,
                    "pred_rate": pred_rate,
                }
            )

            if result["signal"] == "BUY":
                buy_count += 1
                strength = result["strength"]
                print(
                    f"  🟢 {row['Code']} BUY({strength})"
                    f"  up_prob={up_prob:.1%}"
                    f"  pred_rate={pred_rate:.2%}"
                )
            else:
                hold_count += 1

        except Exception as e:
            error_count += 1
            print(f"  ❌ {row['Code']} エラー: {e}")
            print(traceback.format_exc())

    print(f"\n✨ 完了: BUY={buy_count}, HOLD={hold_count}, ERROR={error_count}")


if __name__ == "__main__":
    # 3つのターゲット全部生成する
    for target in ["target_1d", "target_5d", "target_10d"]:
        run_generate_signals(target=target)
