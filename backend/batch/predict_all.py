"""
batch/predict_all.py

全セクターの監視銘柄を巡回して予測を実行し、結果を PredictionsCache に保存する。
日次で実行する想定。
"""

import time
from pathlib import Path

from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.predictions_cache_repo import PredictionsCacheRepo
from ml_core.predictor import Predictor

# モデルが格納されているベースディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/ ディレクトリ
MODELS_DIR = BASE_DIR / "models"


def get_trained_sector_codes():
    """
    modelsディレクトリを走査し、'sector_{code}_{name}' 形式のディレクトリから
    codeを抽出してリストで返す。
    """
    sector_codes = []
    if not MODELS_DIR.exists():
        print(f"⚠️ モデルディレクトリが見つかりません: {MODELS_DIR}")
        return []

    # sector_ で始まるディレクトリを探す
    for path in MODELS_DIR.glob("sector_*"):
        if path.is_dir():
            # "sector_7_steel" -> ["sector", "7", "steel"]
            parts = path.name.split("_")
            if len(parts) >= 2:
                sector_codes.append(parts[1])

    # 重複排除してソートして返す
    return sorted(list(set(sector_codes)), key=int)


def run_predict_all():
    target_sectors = get_trained_sector_codes()

    if not target_sectors:
        print("📭 学習済みモデルが見つかりませんでした。終了します。")
        return

    print(f"📂 検出された学習済みセクター: {target_sectors}")

    repo = EquitiesMasterRepo()
    cache_repo = PredictionsCacheRepo()
    predictor = Predictor()

    total_success = 0
    total_skip = 0
    total_error = 0

    for sector_code in target_sectors:
        sector_info = repo.get_sector_info_by_code(sector_code)
        if not sector_info:
            print(f"⚠️ セクター {sector_code} の情報が見つかりません。スキップします。")
            continue

        targets = repo.get_learning_targets(sector_code)
        print(
            f"\n🚀 セクター {sector_info['S17Nm']} ({len(targets)}銘柄) の予測を開始..."
        )

        for i, (code, company_name) in enumerate(targets):
            print(
                f"  🔄 [{i + 1:02d}/{len(targets)}] {code} | {company_name[:15]:15s} ... ",
                end="",
                flush=True,
            )

            try:
                result = predictor.predict(str(code))
                cache_repo.save(result)
                total_success += 1
                print(
                    f"✅ 完了 "
                    f"(5d: {result['predictions']['target_5d']['rate'] * 100:+.2f}%)"
                )

            except FileNotFoundError:
                total_skip += 1
                print("⏭️  モデル未学習のためスキップ")

            except Exception as e:
                total_error += 1
                print(f"❌ エラー: {e}")

            # 連続実行による負荷を避けるため少し待機
            time.sleep(0.5)

    print(
        f"\n✨ 予測バッチ完了: 成功={total_success}, スキップ={total_skip}, エラー={total_error}"
    )


if __name__ == "__main__":
    run_predict_all()
