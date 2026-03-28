import pandas as pd
from sqlalchemy import text

from .base import Database


class MacroIndicatorsRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "MacroIndicators"
        self._create_table()

    def _create_table(self):
        """MacroIndicators テーブルが存在しない場合は作成する"""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS MacroIndicators (
                    Date   TEXT NOT NULL,
                    Ticker TEXT NOT NULL,
                    Close  REAL,
                    PRIMARY KEY (Date, Ticker)
                )
            """)
            )

    def save(self, df: pd.DataFrame):
        """マクロ指標データを INSERT OR IGNORE で差分保存する"""
        if df is None or df.empty:
            return 0

        with self.engine.begin() as conn:
            rows_before = conn.execute(
                text(f"SELECT COUNT(*) FROM {self.table_name}")
            ).scalar()

            df.to_sql("temp_macro", conn, if_exists="replace", index=False)
            conn.execute(
                text("""
                INSERT OR IGNORE INTO MacroIndicators (Date, Ticker, Close)
                SELECT Date, Ticker, Close FROM temp_macro
            """)
            )
            conn.execute(text("DROP TABLE temp_macro"))

            rows_after = conn.execute(
                text(f"SELECT COUNT(*) FROM {self.table_name}")
            ).scalar()

        return rows_after - rows_before

    def get_latest_date(self, ticker: str):
        """指定ティッカーの最新日付を取得する（差分更新用）"""
        df = pd.read_sql(
            f"SELECT MAX(Date) as latest FROM {self.table_name} WHERE Ticker = ?",
            self.engine,
            params=(ticker,),
        )
        return df.iloc[0]["latest"] if not df.empty else None

    def get_all_pivoted(self):
        """
        全マクロ指標を日付×ティッカーのピボット形式で返す。
        FeatureEngineer での結合用。

        Returns:
            DataFrame: Date をインデックス、Ticker 名をカラムにした横持ちDF
                       例: Date | USDJPY=X | ^GSPC | CL=F | ...
        """
        df = pd.read_sql(
            f"SELECT Date, Ticker, Close FROM {self.table_name} ORDER BY Date ASC",
            self.engine,
        )
        if df.empty:
            return pd.DataFrame()

        pivoted = df.pivot(index="Date", columns="Ticker", values="Close")
        pivoted.index = pd.to_datetime(pivoted.index)
        pivoted = pivoted.ffill()

        # カラム名をわかりやすくリネーム
        pivoted = pivoted.rename(
            columns={
                "USDJPY=X": "usdjpy",
                "^GSPC": "sp500",
                "CL=F": "crude_oil",
                "TIO=F": "iron_ore",
                "^TNX": "us10y",
            }
        )

        return pivoted
