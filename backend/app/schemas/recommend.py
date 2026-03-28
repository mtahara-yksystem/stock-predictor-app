from app.schemas.predict import MetricDetail, PredictionDetail
from pydantic import BaseModel


class RecommendItem(BaseModel):
    code: str
    company_name: str
    current_price: float
    price_change_rate: float
    target_5d: PredictionDetail  # ランキング基準
    target_1d: PredictionDetail  # 参考情報
    target_10d: PredictionDetail  # 参考情報
    metrics: dict[str, MetricDetail]


class RecommendResponse(BaseModel):
    rankings: list[RecommendItem]
    total_scanned: int  # 何銘柄をスキャンしたか
