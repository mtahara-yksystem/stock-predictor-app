# backend/app/schemas/news_summary.py

from pydantic import BaseModel


class SentimentDetail(BaseModel):
    positive: list[str]
    negative: list[str]


class TopicItem(BaseModel):
    text: str
    source: str


class NewsSummaryResponse(BaseModel):
    code: str
    company_name: str | None = None
    generated_at: str
    topics: list[TopicItem]
    sentiment: SentimentDetail
    summary: str
    sources_used: list[str]
