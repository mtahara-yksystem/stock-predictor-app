from app.api.v1.predict import router as predict_router
from fastapi import FastAPI

app = FastAPI(
    title="Stock Predictor API",
    description="機械学習を使った株価予測API",
    version="1.0.0",
)

# ルーターを登録
app.include_router(predict_router, prefix="/api/v1", tags=["predict"])


@app.get("/health")
async def health_check():
    """サーバーの死活確認用"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
