# batch/prepare_training_data.py

import os

from app.fetcher.jquants_fetcher import JQuantsFetcher
from ml_core.data_sync import DataSync
from ml_core.feature_engineer import FeatureEngineer


def prepare_sector_data(sector_code: str, sector_name: str):
    fetcher = JQuantsFetcher()
    sync = DataSync(fetcher)
    engineer = FeatureEngineer()

    # 💡 保存先ディレクトリの作成 (例: data/sector_7_steel)
    output_dir = os.path.join("data", f"sector_{sector_code}_{sector_name}")
    os.makedirs(output_dir, exist_ok=True)

    # セクターに属する銘柄を取得
    targets = sync.master_repo.get_learning_targets(sector_code)

    all_X, all_y = [], []
    print(f"🚀 セクター {sector_code} ({sector_name}) から学習データを生成中...")

    for code, name in targets:
        df = sync.load_combined_data(code)
        X, y = engineer.create_features_and_target(df)

        if not X.empty:
            all_X.append(X)
            all_y.append(y)
            print(f"  ✅ {code} ({name}): {len(X)}件のデータを抽出")

    if all_X:
        import pandas as pd

        X_final = pd.concat(all_X)
        y_final = pd.concat(all_y)

        # 💡 指定したディレクトリに保存
        X_final.to_csv(os.path.join(output_dir, "train_X.csv"), index=False)
        y_final.to_csv(os.path.join(output_dir, "train_y.csv"), index=False)

        print(f"✨ 完了！ {output_dir} に保存しました。")
        print(f"📊 合計データ件数: {len(X_final)}件")


if __name__ == "__main__":
    # 今回はセクター7 (鉄鋼・非鉄)
    prepare_sector_data("7", "steel")
