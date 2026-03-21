import os
import sys

import pandas as pd

# パスを通す
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from app.db.equities_master import EquitiesMasterRepo
from ml_core.data_sync import DataSync
from ml_core.features import FeatureEngineer
from ml_core.stock_model import StockModel


def test_sector_train(sector_code="7"):
    # インスタンス生成
    data_sync = DataSync()
    feature_engineer = FeatureEngineer()
    stock_model = StockModel()
    repo = EquitiesMasterRepo()

    # 1. 自動車セクター(07)の銘柄を20件取得
    target_codes = repo.get_learning_targets(sector_code, limit=20)
    print(f"🎯 学習対象銘柄: {target_codes}")

    all_X, all_y = [], []

    for code in target_codes:
        # 2. DBから結合データをロード
        df = data_sync.load_combined_data(code)

        if df is None or len(df) < 50:  # データが少なすぎる銘柄は除外
            continue

        # 3. 特徴量作成
        try:
            X, y = feature_engineer.create_features(df)
            all_X.append(X)
            all_y.append(y)
            print(f"✅ {code}: {len(X)}件 追加")
        except Exception as e:
            print(f"⚠️ {code} の特徴量作成に失敗: {e}")

    # 4. 全データを合体して学習
    if all_X:
        X_final = pd.concat(all_X)
        y_final = pd.concat(all_y)

        print(f"\n🚀 セクター学習開始！総サンプル数: {len(X_final)}")
        stock_model.train(X_final, y_final)

        # セクター用モデルとして保存
        model_path = os.path.join(
            project_root, "models", f"sector_{sector_code}_model.pkl"
        )
        stock_model.save(model_path)
        print(f"💾 モデル保存完了: {model_path}")
    else:
        print("❌ 学習できるデータがありませんでした")


if __name__ == "__main__":
    test_sector_train("7")
