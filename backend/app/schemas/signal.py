# backend/app/schemas/signal.py

from pydantic import BaseModel


class SignalItem(BaseModel):
    code: str
    company_name: str | None
    signal_date: str
    target: str
    signal: str  # "BUY" | "HOLD"
    strength: str  # "STRONG" | "WEAK" | "NONE"
    up_prob: float
    pred_rate: float


class SignalListResponse(BaseModel):
    signal_date: str
    target: str
    total: int
    items: list[SignalItem]


class SignalHistoryItem(BaseModel):
    signal_date: str
    signal: str
    strength: str
    up_prob: float
    pred_rate: float


class SignalHistoryResponse(BaseModel):
    code: str
    target: str
    history: list[SignalHistoryItem]
