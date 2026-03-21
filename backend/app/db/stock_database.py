import os
import sqlite3

import pandas as pd
from sqlalchemy import create_engine


class StockDatabase:
    def __init__(self, db_name="stock_system.db"):
        # パス解決: backend/data/stock_system.db
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, db_name)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self._create_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _create_tables(self):
        with self._get_connection() as conn:
            # 1. EquitiesMaster: 銘柄属性
            conn.execute("""
              CREATE TABLE IF NOT EXISTS EquitiesMaster (
                Date TEXT, Code TEXT PRIMARY KEY, CoName TEXT, CoNameEn TEXT,
                S17 TEXT, S17Nm TEXT, S33 TEXT, S33Nm TEXT, ScaleCat TEXT,
                Mkt TEXT, MktNm TEXT, Mrgn TEXT, MrgnNm TEXT
              );
              """)

            # 2. DailyQuotes: 日次株価 (APIのキー名に準拠)
            conn.execute("""
              CREATE TABLE IF NOT EXISTS DailyQuotes (
                Code TEXT, Date TEXT,
                O REAL, H REAL, L REAL, C REAL,
                UpperLimit TEXT, LowerLimit TEXT,
                Vo REAL, Va REAL,
                AdjFactor REAL,
                AdjO REAL,
                AdjH REAL,
                AdjL REAL,
                AdjC REAL,
                AdjVo REAL,
                PRIMARY KEY (Code, Date),
                FOREIGN KEY (Code) REFERENCES EquitiesMaster (Code)
              );
              """)

            # 3. FinancialSummaries: 財務詳細 (提示された全項目)
            conn.execute("""
              CREATE TABLE IF NOT EXISTS FinancialSummaries (
                Code TEXT, DiscNo TEXT, DiscDate TEXT, DiscTime TEXT, DocType TEXT,
                CurPerType TEXT, CurPerSt TEXT, CurPerEn TEXT, CurFYSt TEXT, CurFYEn TEXT,
                NxtFYSt TEXT, NxtFYEn TEXT,
                Sales REAL, OP REAL, OdP REAL, NP REAL, EPS REAL, DEPS REAL,
                TA REAL, Eq REAL, EqAR REAL, BPS REAL,
                CFO REAL, CFI REAL, CFF REAL, CashEq REAL,
                Div1Q REAL, Div2Q REAL, Div3Q REAL, DivFY REAL, DivAnn REAL, DivUnit REAL, DivTotalAnn REAL, PayoutRatioAnn REAL,
                FDiv1Q REAL, FDiv2Q REAL, FDiv3Q REAL, FDivFY REAL, FDivAnn REAL, FDivUnit REAL, FDivTotalAnn REAL, FPayoutRatioAnn REAL,
                NxFDiv1Q REAL, NxFDiv2Q REAL, NxFDiv3Q REAL, NxFDivFY REAL, NxFDivAnn REAL, NxFDivUnit REAL, NxFPayoutRatioAnn REAL,
                FSales2Q REAL, FOP2Q REAL, FOdP2Q REAL, FNP2Q REAL, FEPS2Q REAL,
                NxFSales2Q REAL, NxFOP2Q REAL, NxFOdP2Q REAL, NxFNp2Q REAL, NxFEPS2Q REAL,
                FSales REAL, FOP REAL, FOdP REAL, FNP REAL, FEPS REAL,
                NxFSales REAL, NxFOP REAL, NxFOdP REAL, NxFNp REAL, NxFEPS REAL,
                MatChgSub TEXT, SigChgInC TEXT, ChgByASRev TEXT, ChgNoASRev TEXT, ChgAcEst TEXT, RetroRst TEXT,
                ShOutFY REAL, TrShFY REAL, AvgSh REAL,
                NCSales REAL, NCOP REAL, NCOdP REAL, NCNP REAL, NCEPS REAL, NCTA REAL, NCEq REAL, NCEqAR REAL, NCBPS REAL,
                FNCSales2Q REAL, FNCOP2Q REAL, FNCOdP2Q REAL, FNCNP2Q REAL, FNCEPS2Q REAL,
                NxFNCSales2Q REAL, NxFNCOP2Q REAL, NxFNCOdP2Q REAL, NxFNCNP2Q REAL, NxFNCEPS2Q REAL,
                FNCSales REAL, FNCOP REAL, FNCOdP REAL, FNCNP REAL, FNCEPS REAL,
                NxFNCSales REAL, NxFNCOP REAL, NxFNCOdP REAL, NxFNCNP REAL, NxFNCEPS REAL,
                PRIMARY KEY (Code, DiscNo),
                FOREIGN KEY (Code) REFERENCES EquitiesMaster (Code)
              );
              """)

    def upsert(self, table_name, df):
        if isinstance(df, list):
            df = pd.DataFrame(df)
        if df is None or df.empty:
            return

        with self._get_connection() as conn:
            # DBに存在するカラムのみを抽出
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            db_cols = [row[1] for row in cursor.fetchall()]
            valid_cols = [c for c in df.columns if c in db_cols]
            df_to_save = df[valid_cols].copy()

            if df_to_save.empty:
                return

            df_to_save.to_sql("temp_upsert", conn, if_exists="replace", index=False)
            cols_str = ", ".join(valid_cols)
            query = f"""
      INSERT OR REPLACE INTO {table_name} ({cols_str})
      SELECT {cols_str} FROM temp_upsert
      """
            conn.execute(query)
            conn.execute("DROP TABLE temp_upsert")
            conn.commit()

    def get_latest_date(self, table_name, code):
        query = f"SELECT MAX(Date) FROM {table_name} WHERE Code = ?"
        with self._get_connection() as conn:
            res = conn.execute(query, (code,)).fetchone()
            return res[0] if res else None
