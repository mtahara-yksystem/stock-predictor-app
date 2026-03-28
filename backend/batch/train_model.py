from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.macro_indicators_repo import MacroIndicatorsRepo
from ml_core.feature_engineer import FeatureEngineer
from ml_core.trainer import Trainer

if __name__ == "__main__":
    repo = EquitiesMasterRepo()
    macro_repo = MacroIndicatorsRepo()
    target_s17 = "7"

    # 1. セクター情報を取得
    sector = repo.get_sector_info_by_code(target_s17)
    if not sector:
        print("❌ セクター情報が見つかりません。")
        exit()

    # 2. 株価＋財務データを取得
    print(f"📥 {sector['S17Nm']}セクターのデータをロード中...")
    raw_df = repo.get_quotes_with_financials_by_sector(target_s17)

    # 3. マクロ指標を取得（ピボット形式）
    print("📥 マクロ指標をロード中...")
    macro_df = macro_repo.get_all_pivoted()
    if macro_df.empty:
        print(
            "⚠️ マクロ指標がDBにありません。先に batch/sync_macro.py を実行してください。"
        )

    # 4. 特徴量生成 & 学習
    engineer = FeatureEngineer()
    X, y_all = engineer.create_features_and_targets(raw_df, macro_df=macro_df)

    trainer = Trainer(target_s17, sector["S17NmEn"])
    trainer.train(X, y_all)
