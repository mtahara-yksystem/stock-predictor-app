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
                "expected_value": round(row.get("ExpectedValue", 0), 2),
                "predicted_return": round(row[f"Rate{period}"], 2),
                "up_probability": round(row[f"UpProb{period}"], 2),
                "direction_accuracy": round(row[f"DirAcc{period}"], 2),
                "r2": round(row[f"R2_{period}"], 2),
            }
            for idx, row in enumerate(rows)
        ],
    }
