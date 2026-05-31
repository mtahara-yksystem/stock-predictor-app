# backend/app/db/signal_cache_repo.py

import pandas as pd
from sqlalchemy import text

from .base import Database


class SignalCacheRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "SignalCache"
        self._create_table()

    def _create_table(self):
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS SignalCache (
                    Code        TEXT NOT NULL,
                    SignalDate  TEXT NOT NULL,
                    Target      TEXT NOT NULL,
                    Signal      TEXT NOT NULL,
                    Strength    TEXT NOT NULL,
                    UpProb      REAL,
                    PredRate    REAL,
                    PRIMARY KEY (Code, SignalDate, Target)
                )
            """)
            )

    def save(self, record: dict):
        """
        record = {
            "code": "5401",
            "signal_date": "2025-05-31",
            "target": "target_5d",
            "signal": "BUY",
            "strength": "STRONG",
            "up_prob": 0.72,
            "pred_rate": 0.031,
        }
        """
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                INSERT OR REPLACE INTO SignalCache
                    (Code, SignalDate, Target, Signal, Strength, UpProb, PredRate)
                VALUES
                    (:code, :signal_date, :target, :signal, :strength,
                     :up_prob, :pred_rate)
            """),
                {
                    "code": record["code"],
                    "signal_date": record["signal_date"],
                    "target": record["target"],
                    "signal": record["signal"],
                    "strength": record["strength"],
                    "up_prob": record["up_prob"],
                    "pred_rate": record["pred_rate"],
                },
            )

    def get_latest_signals(
        self,
        signal: str = "BUY",
        target: str = "target_5d",
        limit: int = 20,
    ) -> list[dict]:
        df = pd.read_sql(
            text("""
            SELECT s.Code, s.SignalDate, s.Target, s.Signal, s.Strength,
                  s.UpProb, s.PredRate, p.CompanyName
            FROM SignalCache s
            LEFT JOIN PredictionsCache p
                ON s.Code = p.Code
                AND p.PredDate = (SELECT MAX(PredDate) FROM PredictionsCache)
            WHERE s.SignalDate = (SELECT MAX(SignalDate) FROM SignalCache)
              AND s.Signal  = :signal
              AND s.Target  = :target
            GROUP BY s.Code          -- ← 銘柄ごとに1行に絞る
            ORDER BY s.UpProb DESC
            LIMIT :limit
        """),
            self.engine,
            params={
                "signal": signal,
                "target": target,
                "limit": limit,
            },
        )
        return df.to_dict(orient="records")

    def get_signal_history(self, code: str, target: str = "target_5d") -> list[dict]:
        """特定銘柄のシグナル履歴を取得"""
        df = pd.read_sql(
            text("""
            SELECT * FROM SignalCache
            WHERE Code   = :code
              AND Target = :target
            ORDER BY SignalDate DESC
            LIMIT 60
        """),
            self.engine,
            params={"code": code, "target": target},
        )
        return df.to_dict(orient="records")
