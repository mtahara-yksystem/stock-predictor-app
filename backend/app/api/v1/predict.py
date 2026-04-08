from app.db.predictions_cache_repo import PredictionsCacheRepo
from app.schemas.predict import PredictResponse
from fastapi import APIRouter, HTTPException

router = APIRouter()
cache_repo = PredictionsCacheRepo()


@router.get("/predict/{code}", response_model=PredictResponse)
async def predict_stock(code: str):
    """
    指定した銘柄コードの最新予測結果を返す。
    予測結果は日次バッチ（predict_all.py）によってDBに保存済みのものを返す。

    - **code**: 銘柄コード（例: 5401）
    """
    result = cache_repo.get_latest(code)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"銘柄 {code} の予測結果がDBに存在しません。"
                "先に batch/predict_all.py を実行してください。"
            ),
        )

    return result
