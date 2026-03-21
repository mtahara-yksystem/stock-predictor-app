from pydantic import BaseModel


class PredictionDetail(BaseModel):
    rate: float  # 予測騰落率（例: 0.005 = +0.5%）
    up_prob: float  # 上がる確率（例: 0.58 = 58%）


class MetricDetail(BaseModel):
    mae: float
    r2: float


class PredictResponse(BaseModel):
    code: str
    company_name: str
    current_price: float
    price_change_rate: float  # 前日比騰落率
    predictions: dict[str, PredictionDetail]
    metrics: dict[str, MetricDetail]
