import pandas as pd

from .base import Database


class EquitiesMasterRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "EquitiesMaster"

    def get_codes_by_17sector(self, sector_code: str):
        """17業種コード(S17)で銘柄を検索する"""
        query = "SELECT Code FROM {self.table_name} WHERE S17 = ?"
        df = pd.read_sql(query, self.engine, params=(str(sector_code),))
        return df["Code"].tolist()

    def get_all_codes(self):
        """全銘柄コードを取得する"""
        query = "SELECT Code FROM {self.table_name}"
        df = pd.read_sql(query, self.engine)
        return df["Code"].tolist()

    def get_sector_info(self, code: str):
        """特定の銘柄の業種情報を取得する"""
        query = (
            f"""SELECT Code, S17, S17Nm, S33Nm FROM {self.table_name} WHERE Code = ?"""
        )
        return pd.read_sql(query, self.engine, params=(code,))

    def get_learning_targets(self, sector_code: str, limit=20):
        """
        学習対象銘柄のコードと会社名を一括取得
        """
        query = f"""SELECT Code, CoName FROM {self.table_name} WHERE S17 = ? LIMIT ?"""

        # DataFrameとして取得
        df = pd.read_sql(query, self.engine, params=(sector_code, limit))

        # リスト形式で返す [(Code, CoName), (Code, CoName), ...]
        return df.to_records(index=False).tolist()

    def get_sector_info_by_code(self, s17_code: str):
        """S17コードからセクターの日本語名と英名(S17NmEn)を取得する"""
        query = f"""SELECT S17Nm, S17NmEn FROM {self.table_name} WHERE S17 = ?"""
        df = pd.read_sql(query, self.engine, params=(str(s17_code),))

        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def get_quotes_by_sector(self, s17_code: str):
        """指定したセクターに属する全銘柄の株価データを取得する"""
        query = f"""
            SELECT q.* FROM DailyQuotes q
            JOIN {self.table_name} m ON q.Code = m.Code
            WHERE m.S17 = ?
            ORDER BY q.Date ASC
        """
        return pd.read_sql(query, self.engine, params=(str(s17_code),))

    def get_quotes_with_financials_by_sector(self, s17_code: str):
        """
        指定セクターの株価データに、その日時点で最新の財務データを結合して返す。
        merge_asof を使うことでルックアヘッドバイアスを回避する。
        """
        # 1. 株価データを取得
        quotes_query = f"""
            SELECT q.* FROM DailyQuotes q
            JOIN {self.table_name} m ON q.Code = m.Code
            WHERE m.S17 = ?
            ORDER BY q.Code ASC, q.Date ASC
        """
        quotes_df = pd.read_sql(quotes_query, self.engine, params=(str(s17_code),))

        # 2. 財務データを取得（必要なカラムに絞る）
        financials_query = """
            SELECT
                Code,
                DiscDate,
                EPS,
                BPS,
                EqAR,
                Sales,
                OP,
                NP,
                Eq
            FROM FinancialSummaries
            ORDER BY Code ASC, DiscDate ASC
        """
        financials_df = pd.read_sql(financials_query, self.engine)

        # 3. 日付型に統一
        quotes_df["Date"] = pd.to_datetime(quotes_df["Date"])
        financials_df["DiscDate"] = pd.to_datetime(financials_df["DiscDate"])

        # 4. merge_asof で銘柄ごとに「その日以前の最新財務データ」を結合
        merged_parts = []
        for code, quote_group in quotes_df.groupby("Code"):
            fin_group = financials_df[financials_df["Code"] == code].sort_values(
                "DiscDate"
            )
            if fin_group.empty:
                continue
            merged = pd.merge_asof(
                quote_group.sort_values("Date"),
                fin_group.drop(columns=["Code"]),  # Code重複を避ける
                left_on="Date",
                right_on="DiscDate",
                direction="backward",  # その日以前で最新
            )
            merged_parts.append(merged)

        if not merged_parts:
            return pd.DataFrame()

        result_df = (
            pd.concat(merged_parts).sort_values(["Code", "Date"]).reset_index(drop=True)
        )

        # 5. 財務データがまだない行（上場直後など）は除外
        financial_cols = ["EPS", "BPS", "EqAR", "Sales", "OP", "NP", "Eq"]
        result_df = result_df.dropna(subset=financial_cols, how="all")

        return result_df
