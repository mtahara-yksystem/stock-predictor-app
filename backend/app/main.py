from app.api.v1.predict import router as predict_router

# from app.api.v1.recommend import router as recommend_router
from app.api.v1.ranking import router as ranking_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Stock Predictor API",
    description="機械学習を使った株価予測API",
    version="1.0.0",
)

app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
# app.include_router(recommend_router, prefix="/api/v1", tags=["recommend"])
app.include_router(ranking_router, prefix="/api/v1/ranking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """サーバーの死活確認用"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
