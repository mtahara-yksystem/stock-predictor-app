# backend/app/main.py

from app.api.v1.news_summary import router as news_summary_router
from app.api.v1.predict import router as predict_router
from app.api.v1.ranking import router as ranking_router
from app.api.v1.signal import router as signal_router  # ← 追加
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Stock Predictor API",
    description="機械学習を使った株価予測API",
    version="1.0.0",
)

app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
app.include_router(ranking_router, prefix="/api/v1/ranking", tags=["ranking"])
app.include_router(signal_router, prefix="/api/v1/signals", tags=["signal"])
app.include_router(news_summary_router, prefix="/api/v1", tags=["news_summary"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
