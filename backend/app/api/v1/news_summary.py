# backend/app/api/v1/news_summary.py

from datetime import datetime

from app.db.news_summary_cache_repo import NewsSummaryCacheRepo
from app.schemas.news_summary import NewsSummaryResponse
from fastapi import APIRouter, HTTPException
from ml_core.news_analyzer import NewsAnalyzer

router = APIRouter()
cache_repo = NewsSummaryCacheRepo()
analyzer = NewsAnalyzer()


@router.get("/news-summary/{code}", response_model=NewsSummaryResponse)
async def get_news_summary(code: str):
    """
    指定銘柄のニュース・決算材料をLLMで整理して返す（オンデマンド）。
    同日中はキャッシュを返し、無料枠を節約する。
    """
    today = datetime.now().strftime("%Y-%m-%d")

    cached = cache_repo.get_today(code, today)
    if cached:
        return cached

    try:
        result = analyzer.analyze(code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析に失敗しました: {e}")

    cache_repo.save(result)
    return result
