from typing import Final

import pandas as pd

from .base import Database


class EquitiesMasterRepo(Database):
    S17_CODE_LIST: Final = tuple(str(i) for i in range(1, 18))

    def __init__(self):
        super().__init__()
        self.table_name = "EquitiesMaster"

    def get_by_code(self, code: str):
        """銘柄コード(Code)で銘柄を取得する"""
        query = f"""SELECT CoName FROM {self.table_name} WHERE Code = ?"""
        return pd.read_sql(query, self.engine, params=(str(code),))

    def get_codes_by_17sector(self, sector_code: str):
        """17業種コード(S17)で銘柄を検索する"""
        query = f"""SELECT Code FROM {self.table_name} WHERE S17 = ?"""
        df = pd.read_sql(query, self.engine, params=(str(sector_code),))
        return df["Code"].tolist()

    def get_all_codes(self):
        """全銘柄コードを取得する"""
        query = f"""SELECT Code FROM {self.table_name}"""
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
        学習対象銘柄のコードと会社名を一括取得。
        プライム市場かつ中型株以上に絞る（流動性確保のため）
        """
        query = f"""
            SELECT Code, CoName FROM {self.table_name}
            WHERE S17 = ?
            AND Mkt = '0111'
            AND ScaleCat IN ('TOPIX Core30', 'TOPIX Large70', 'TOPIX Mid400')
            LIMIT ?
        """
        df = pd.read_sql(query, self.engine, params=(sector_code, limit))
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
        対象銘柄は get_learning_targets で絞った銘柄のみ。
        """
        # 1. 対象銘柄を get_learning_targets から取得（選定基準を一元化）
        targets = self.get_learning_targets(s17_code)
        if not targets:
            return pd.DataFrame()
        target_codes = [code for code, _ in targets]
        placeholders = ",".join("?" * len(target_codes))

        # 2. 株価データを取得
        quotes_query = f"""
            SELECT q.* FROM DailyQuotes q
            WHERE q.Code IN ({placeholders})
            ORDER BY q.Code ASC, q.Date ASC
        """
        quotes_df = pd.read_sql(quotes_query, self.engine, params=tuple(target_codes))

        # 3. 財務データを取得
        financials_query = f"""
            SELECT Code, DiscDate, EPS, BPS, EqAR, Sales, OP, NP, Eq
            FROM FinancialSummaries
            WHERE Code IN ({placeholders})
            ORDER BY Code ASC, DiscDate ASC
        """
        financials_df = pd.read_sql(
            financials_query, self.engine, params=tuple(target_codes)
        )

        # 4. 日付型に統一
        quotes_df["Date"] = pd.to_datetime(quotes_df["Date"])
        financials_df["DiscDate"] = pd.to_datetime(financials_df["DiscDate"])

        # 5. merge_asof で銘柄ごとに「その日以前の最新財務データ」を結合
        merged_parts = []
        for code, quote_group in quotes_df.groupby("Code"):
            fin_group = financials_df[financials_df["Code"] == code].sort_values(
                "DiscDate"
            )
            if fin_group.empty:
                continue
            merged = pd.merge_asof(
                quote_group.sort_values("Date"),
                fin_group.drop(columns=["Code"]),
                left_on="Date",
                right_on="DiscDate",
                direction="backward",
            )
            merged_parts.append(merged)

        if not merged_parts:
            return pd.DataFrame()

        result_df = (
            pd.concat(merged_parts).sort_values(["Code", "Date"]).reset_index(drop=True)
        )

        financial_cols = ["EPS", "BPS", "EqAR", "Sales", "OP", "NP", "Eq"]
        result_df = result_df.dropna(subset=financial_cols, how="all")

        return result_df
