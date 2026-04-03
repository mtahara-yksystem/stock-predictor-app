import os

from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.macro_indicators_repo import MacroIndicatorsRepo
from ml_core.feature_engineer import FeatureEngineer


def prepare_sector_data(sector_code: str, sector_name: str):
    repo = EquitiesMasterRepo()
    macro_repo = MacroIndicatorsRepo()
    engineer = FeatureEngineer()

    output_dir = os.path.join("data", f"sector_{sector_code}_{sector_name}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"🚀 セクター {sector_code} ({sector_name}) から学習データを生成中...")

    # ← train_model.py と同じ方法で取得
    raw_df = repo.get_quotes_with_financials_by_sector(sector_code)
    macro_df = macro_repo.get_all_pivoted()

    X, y = engineer.create_features_and_targets(raw_df, macro_df=macro_df)

    if not X.empty:
        X.to_csv(os.path.join(output_dir, "train_X.csv"), index=True)
        y.to_csv(os.path.join(output_dir, "train_y.csv"), index=True)
        print(f"✨ 完了！ {output_dir} に保存しました。")
        print(f"📊 合計データ件数: {len(X)}件")


if __name__ == "__main__":
    prepare_sector_data("7", "steel")
