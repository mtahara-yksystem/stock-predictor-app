from datetime import datetime, timedelta

import pandas as pd
from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.financial_summaries_repo import FinancialSummariesRepo
from app.db.stock_database import StockDatabase


class DataSync:
    def __init__(self, fetcher):
        self.db = StockDatabase()
        self.fetcher = fetcher
        # 財務データ専用のリポジトリを初期化
        self.fin_repo = FinancialSummariesRepo()
        self.master_repo = EquitiesMasterRepo()

    def sync_all(self, codes):
        """マスター・株価・財務をまとめて同期"""
        self.sync_master()
        # ここも1銘柄ずつのループに変更が必要ですが、一旦そのまま
        for code in codes:
            self.sync_daily_quotes(code)
            self.sync_financial_summary(code)

    def sync_master(self):
        print("📋 銘柄マスターを同期中...")
        df_master = self.fetcher.fetch_equities_master()
        if df_master is not None:
            self.db.upsert("EquitiesMaster", df_master)
            print(f"✅ {len(df_master)} 銘柄を更新。")

    def sync_daily_quotes(self, code: str, days_back=730):
        """指定した1銘柄の株価を同期する"""
        latest = self.db.get_latest_date("DailyQuotes", code)

        if latest:
            start_date = (
                datetime.strptime(latest, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )

        print(f"📥 {code}: {start_date} からの差分を取得...")

        raw_data = self.fetcher.fetch_daily_quotes(code, from_date=start_date)
        df_quotes = pd.DataFrame(raw_data)

        if not df_quotes.empty:
            self.db.upsert("DailyQuotes", df_quotes)
            # printはバッチ側で行うなら、ここではログ程度に
            return len(df_quotes)
        else:
            return 0

    def sync_financial_summary(self, code: str):
        """指定した1銘柄の財務情報を同期する"""
        raw_data = self.fetcher.fetch_financial_summary(code)
        df = pd.DataFrame(raw_data)

        if not df.empty:
            count = self.fin_repo.save_summaries(df)
            return count

        return 0

    def load_combined_data(self, code: str):
        """
        DBから指定銘柄の株価と財務データを結合して取得する
        """

        query = """
            SELECT
                dq.Date, dq.Code,
                dq.AdjO, dq.AdjH, dq.AdjL, dq.AdjC, dq.AdjVo, dq.Va,
                fin.Sales, fin.OP, fin.EPS, fin.EqAR
            FROM DailyQuotes dq
            LEFT JOIN FinancialSummaries fin ON dq.Code = fin.Code
                AND dq.Date >= fin.DiscDate
            WHERE dq.Code = ?
            ORDER BY dq.Date ASC
        """

        try:
            df = pd.read_sql(query, self.db.engine, params=(code,))

            if df.empty:
                return None

            df = df.drop_duplicates(subset=["Date"], keep="last")
            # 財務データを前方埋め（決算発表日から次の発表日まで同じ値を保持）
            target_cols = ["Sales", "OP", "EPS", "EqAR"]
            df[target_cols] = df[target_cols].ffill()

            return df
        except Exception as e:
            print(f"❌ DB読み込みエラー ({code}): {e}")
            return None
