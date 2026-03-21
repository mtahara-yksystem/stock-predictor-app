from app.schemas.predict import PredictResponse
from fastapi import APIRouter, HTTPException
from ml_core.predictor import Predictor

router = APIRouter()
predictor = Predictor()


@router.get("/predict/{code}", response_model=PredictResponse)
async def predict_stock(code: str):
    """
    指定した銘柄コードの株価予測を返す。

    - **code**: 銘柄コード（例: 5401）
    """
    try:
        result = predictor.predict(code)
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"モデルが見つかりません。先に学習バッチを実行してください。: {e}",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"予測中にエラーが発生しました: {e}"
        )
