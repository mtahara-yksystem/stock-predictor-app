from typing import Literal, Optional

from app.db.predictions_cache_repo import PredictionsCacheRepo
from fastapi import APIRouter, Query

router = APIRouter()
cache_repo = PredictionsCacheRepo()


@router.get("/")
async def get_ranking(
    ranking_type: Literal[
        "expected", "return", "probability", "confidence"
    ] = "expected",
    period: Literal["1d", "5d", "10d"] = "5d",
    sector: Optional[str] = None,
    limit: int = Query(10, le=50),
):
    # リポジトリからデータを取得
    rows = cache_repo.get_ranking(ranking_type, period, sector, limit)

    if not rows:
        return {"stocks": []}

    return {
        "ranking_type": ranking_type,
        "period": period,
        "updated_at": rows[0]["PredDate"],
        "stocks": [
            {
                "rank": idx + 1,
                "code": row["Code"],
                "company_name": row["CompanyName"],
                "expected_value": row.get("ExpectedValue", 0),
                "predicted_return": row[f"Rate{period}"],
                "up_probability": row[f"UpProb{period}"],
                "direction_accuracy": row[f"DirAcc{period}"],
                "r2": row[f"R2_{period}"],
            }
            for idx, row in enumerate(rows)
        ],
    }
