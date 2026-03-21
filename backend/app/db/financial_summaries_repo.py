import pandas as pd
from sqlalchemy import text

from .base import Database


class FinancialSummariesRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "FinancialSummaries"

    def save_summaries(self, df: pd.DataFrame):
        """財務諸表データを INSERT OR IGNORE で差分保存する"""
        if df is None or df.empty:
            return 0

        with self.engine.begin() as conn:
            # DBに存在するカラムのみ抽出
            db_cols = [
                row[1]
                for row in conn.execute(
                    text(f"PRAGMA table_info({self.table_name})")
                ).fetchall()
            ]
            valid_cols = [c for c in df.columns if c in db_cols]
            df_to_save = df[valid_cols].copy()

            if df_to_save.empty:
                return 0

            rows_before = conn.execute(
                text(f"SELECT COUNT(*) FROM {self.table_name}")
            ).scalar()

            df_to_save.to_sql("temp_fin", conn, if_exists="replace", index=False)
            cols_str = ", ".join(valid_cols)
            conn.execute(
                text(f"""
                INSERT OR IGNORE INTO {self.table_name} ({cols_str})
                SELECT {cols_str} FROM temp_fin
            """)
            )
            conn.execute(text("DROP TABLE temp_fin"))

            rows_after = conn.execute(
                text(f"SELECT COUNT(*) FROM {self.table_name}")
            ).scalar()

        return rows_after - rows_before

    def get_latest_announcement(self, code: str):
        """特定銘柄の最新の決算発表日を取得する"""
        query = f"SELECT MAX(DiscDate) FROM {self.table_name} WHERE Code = ?"
        df = pd.read_sql(query, self.engine, params=(code,))
        return df.iloc[0, 0] if not df.empty else None
