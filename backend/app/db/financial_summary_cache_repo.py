import json
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from .base import Database


class FinancialSummaryCacheRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "FinancialSummaryCache"
        self._create_table()

    def _create_table(self):
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS FinancialSummaryCache (
                    Code        TEXT NOT NULL,
                    SummaryDate TEXT NOT NULL,
                    Summary     TEXT,
                    Positives   TEXT,
                    Concerns    TEXT,
                    Trend       TEXT,
                    PRIMARY KEY (Code, SummaryDate)
                )
            """)
            )

    def get_today(self, code: str) -> dict | None:
        today = datetime.now().strftime("%Y-%m-%d")
        df = pd.read_sql(
            f"SELECT * FROM {self.table_name} WHERE Code = ? AND SummaryDate = ?",
            self.engine,
            params=(code, today),
        )
        if df.empty:
            return None

        row = df.iloc[0]
        return {
            "summary": row["Summary"],
            "positives": json.loads(row["Positives"]) if row["Positives"] else [],
            "concerns": json.loads(row["Concerns"]) if row["Concerns"] else [],
            "trend": row["Trend"],
        }

    def save(self, code: str, result: dict):
        today = datetime.now().strftime("%Y-%m-%d")
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                INSERT OR REPLACE INTO FinancialSummaryCache
                    (Code, SummaryDate, Summary, Positives, Concerns, Trend)
                VALUES
                    (:code, :date, :summary, :positives, :concerns, :trend)
            """),
                {
                    "code": code,
                    "date": today,
                    "summary": result.get("summary", ""),
                    "positives": json.dumps(
                        result.get("positives", []), ensure_ascii=False
                    ),
                    "concerns": json.dumps(
                        result.get("concerns", []), ensure_ascii=False
                    ),
                    "trend": result.get("trend", "unknown"),
                },
            )
