# backend/app/db/news_summary_cache_repo.py

import json

import pandas as pd
from sqlalchemy import text

from .base import Database


class NewsSummaryCacheRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "NewsSummaryCache"
        self._create_table()

    def _create_table(self):
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS NewsSummaryCache (
                    Code         TEXT NOT NULL,
                    SummaryDate  TEXT NOT NULL,
                    Topics       TEXT,
                    SentimentPos TEXT,
                    SentimentNeg TEXT,
                    Summary      TEXT,
                    SourcesUsed  TEXT,
                    PRIMARY KEY (Code, SummaryDate)
                )
            """)
            )

    def get_today(self, code: str, date: str) -> dict | None:
        df = pd.read_sql(
            f"SELECT * FROM {self.table_name} WHERE Code = ? AND SummaryDate = ?",
            self.engine,
            params=(code, date),
        )
        if df.empty:
            return None
        row = df.iloc[0]
        return {
            "code": row["Code"],
            "generated_at": row["SummaryDate"],
            "topics": json.loads(row["Topics"]),
            "sentiment": {
                "positive": json.loads(row["SentimentPos"]),
                "negative": json.loads(row["SentimentNeg"]),
            },
            "summary": row["Summary"],
            "sources_used": json.loads(row["SourcesUsed"]),
        }

    def save(self, result: dict):
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                INSERT OR REPLACE INTO NewsSummaryCache
                    (Code, SummaryDate, Topics, SentimentPos, SentimentNeg, Summary, SourcesUsed)
                VALUES
                    (:code, :date, :topics, :pos, :neg, :summary, :sources)
            """),
                {
                    "code": result["code"],
                    "date": result["generated_at"],
                    "topics": json.dumps(result["topics"], ensure_ascii=False),
                    "pos": json.dumps(
                        result["sentiment"]["positive"], ensure_ascii=False
                    ),
                    "neg": json.dumps(
                        result["sentiment"]["negative"], ensure_ascii=False
                    ),
                    "summary": result["summary"],
                    "sources": json.dumps(result["sources_used"], ensure_ascii=False),
                },
            )
