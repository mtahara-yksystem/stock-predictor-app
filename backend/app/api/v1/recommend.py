from app.db.equities_master_repo import EquitiesMasterRepo
from app.schemas.recommend import RecommendItem, RecommendResponse
from fastapi import APIRouter, HTTPException
from ml_core.predictor import Predictor

router = APIRouter()
predictor = Predictor()
repo = EquitiesMasterRepo()

# 全セクターコード
ALL_SECTORS = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
]


@router.get("/recommend", response_model=RecommendResponse)
async def recommend_stocks(top_n: int = 5, limit_per_sector: int = 20):
    """
    全セクターの主要銘柄をスキャンして、5日後に上がる確率が高い銘柄トップNを返す。

    - **top_n**: 返す銘柄数（デフォルト5）
    - **limit_per_sector**: セクターごとにスキャンする銘柄数（デフォルト20）
    """
    results = []
    total_scanned = 0

    for sector_code in ALL_SECTORS:
        # セクターの主要銘柄を取得
        targets = repo.get_learning_targets(sector_code, limit=limit_per_sector)
        if not targets:
            continue

        for code, company_name in targets:
            try:
                result = predictor.predict(str(code))
                total_scanned += 1

                predictions = result["predictions"]
                results.append(
                    RecommendItem(
                        code=result["code"],
                        company_name=result["company_name"],
                        current_price=result["current_price"],
                        price_change_rate=result["price_change_rate"],
                        target_5d=predictions["target_5d"],
                        target_1d=predictions["target_1d"],
                        target_10d=predictions["target_10d"],
                        metrics=result["metrics"],
                    )
                )
            except FileNotFoundError:
                # モデルが存在しないセクターはスキップ
                continue
            except Exception as e:
                # 個別銘柄のエラーはスキップしてログだけ出す
                print(f"⚠️ {code} のスキップ: {e}")
                continue

    if not results:
        raise HTTPException(
            status_code=404,
            detail="予測可能な銘柄が見つかりませんでした。先に学習バッチを実行してください。",
        )

    # target_5d の up_prob で降順ソートしてトップNを返す
    rankings = sorted(
        results,
        key=lambda x: x.target_5d.up_prob,
        reverse=True,
    )[:top_n]

    return RecommendResponse(rankings=rankings, total_scanned=total_scanned)
