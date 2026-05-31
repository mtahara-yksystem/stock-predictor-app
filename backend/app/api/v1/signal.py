# backend/app/api/v1/signal.py

from typing import Literal

from app.db.signal_cache_repo import SignalCacheRepo
from app.schemas.signal import (
    SignalHistoryItem,
    SignalHistoryResponse,
    SignalItem,
    SignalListResponse,
)
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
signal_repo = SignalCacheRepo()


@router.get("/", response_model=SignalListResponse)
async def get_signals(
    signal: Literal["BUY", "HOLD"] = "BUY",
    target: Literal["target_1d", "target_5d", "target_10d"] = "target_5d",
    strength: Literal["STRONG", "WEAK", "ALL"] = "ALL",
    limit: int = Query(20, le=50),
):
    """
    最新日のシグナル一覧を返す。

    - **signal**: BUY or HOLD
    - **target**: 予測期間
    - **strength**: STRONG / WEAK / ALL
    - **limit**: 最大返却件数
    """
    rows = signal_repo.get_latest_signals(
        signal=signal,
        target=target,
        limit=limit,
    )

    # strengthフィルター
    if strength != "ALL":
        rows = [r for r in rows if r.get("Strength") == strength]

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{signal}シグナルが見つかりません。"
                "先に batch/generate_signals.py を実行してください。"
            ),
        )

    signal_date = rows[0]["SignalDate"]

    items = [
        SignalItem(
            code=r["Code"],
            company_name=r.get("CompanyName"),
            signal_date=r["SignalDate"],
            target=r["Target"],
            signal=r["Signal"],
            strength=r["Strength"],
            up_prob=r["UpProb"],
            pred_rate=r["PredRate"],
        )
        for r in rows
    ]

    return SignalListResponse(
        signal_date=signal_date,
        target=target,
        total=len(items),
        items=items,
    )


@router.get("/{code}", response_model=SignalHistoryResponse)
async def get_signal_history(
    code: str,
    target: Literal["target_1d", "target_5d", "target_10d"] = "target_5d",
):
    """
    特定銘柄のシグナル履歴を返す（直近60日）。

    - **code**: 銘柄コード
    - **target**: 予測期間
    """
    rows = signal_repo.get_signal_history(code=code, target=target)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"銘柄 {code} のシグナル履歴がありません。",
        )

    history = [
        SignalHistoryItem(
            signal_date=r["SignalDate"],
            signal=r["Signal"],
            strength=r["Strength"],
            up_prob=r["UpProb"],
            pred_rate=r["PredRate"],
        )
        for r in rows
    ]

    return SignalHistoryResponse(
        code=code,
        target=target,
        history=history,
    )
