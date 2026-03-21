from app.db.equities_master_repo import EquitiesMasterRepo
from ml_core.feature_engineer import FeatureEngineer
from ml_core.trainer import Trainer

if __name__ == "__main__":
    repo = EquitiesMasterRepo()
    target_s17 = "7"

    # 1. セクター情報をRepoから取得
    sector = repo.get_sector_info_by_code(target_s17)
    if not sector:
        print("❌ セクター情報が見つかりません。")
        exit()

    # 2. 株価データ＋財務データをRepoから取得（ルックアヘッドバイアス回避済み）
    print(f"📥 {sector['S17Nm']}セクターのデータをロード中...")
    raw_df = repo.get_quotes_with_financials_by_sector(target_s17)  # ← 変更

    # 3. 特徴量生成 & 学習
    engineer = FeatureEngineer()
    X, y_all = engineer.create_features_and_targets(raw_df)

    trainer = Trainer(target_s17, sector["S17NmEn"])
    trainer.train(X, y_all)
