from app.db.financial_summary_cache_repo import FinancialSummaryCacheRepo
from fastapi import APIRouter
from ml_core.financial_analyzer import FinancialAnalyzer

router = APIRouter()
cache_repo = FinancialSummaryCacheRepo()
analyzer = FinancialAnalyzer()


@router.get("/{code}")
async def get_financial_summary(code: str):
    """
    指定銘柄の財務データをLLMで要約・評価した結果を返す。
    同日中はキャッシュを返す（Gemini無料枠節約のため）。
    """
    cached = cache_repo.get_today(code)
    if cached:
        return {"code": code, **cached, "cached": True}

    result = analyzer.analyze(code)
    cache_repo.save(code, result)
    return {"code": code, **result, "cached": False}
