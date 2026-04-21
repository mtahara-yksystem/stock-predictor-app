import pandas as pd
from sqlalchemy import text

from .base import Database


class PredictionsCacheRepo(Database):
    def __init__(self):
        super().__init__()
        self.table_name = "PredictionsCache"
        self._create_table()

    def _create_table(self):
        """PredictionsCache テーブルが存在しない場合は作成する"""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS PredictionsCache (
                    Code            TEXT NOT NULL,
                    PredDate        TEXT NOT NULL,
                    CompanyName     TEXT,
                    CurrentPrice    REAL,
                    PriceChangeRate REAL,
                    Rate1d          REAL,
                    UpProb1d        REAL,
                    Mae1d           REAL,
                    R2_1d           REAL,
                    DirAcc1d        REAL,
                    Rate5d          REAL,
                    UpProb5d        REAL,
                    Mae5d           REAL,
                    R2_5d           REAL,
                    DirAcc5d        REAL,
                    Rate10d         REAL,
                    UpProb10d       REAL,
                    Mae10d          REAL,
                    R2_10d          REAL,
                    DirAcc10d       REAL,
                    PRIMARY KEY (Code, PredDate)
                )
            """)
            )

    def get_ranking(
        self, ranking_type: str, period: str, sector_code: str = None, limit: int = 10
    ):
        """
        最新日の予測データからランキングを取得する。
        """
        # カラム名のマッピング
        rate_col = f"Rate{period}"  # 例: Rate5d
        prob_col = f"UpProb{period}"  # 例: UpProb5d
        conf_col = f"R2_{period}"  # 例: R2_5d

        # ソート条件の決定
        order_by_map = {
            "expected": f"({rate_col} * {prob_col}) DESC",
            "return": f"{rate_col} DESC",
            "probability": f"{prob_col} DESC",
            "confidence": f"{conf_col} DESC",
        }
        order_by = order_by_map.get(ranking_type, f"{rate_col} DESC")

        # セクターフィルターのWHERE句（EquitiesMaster等とJOINが必要な場合は適宜修正）
        # ※現在はPredictionsCache単体で取れる範囲を想定
        sector_filter = ""
        if sector_code:
            # EquitiesMasterテーブルにSector17Codeがあると仮定してJOINする場合の例
            join_clause = "JOIN EquitiesMaster m ON p.Code = m.Code"
            sector_filter = f"AND m.Sector17Code = '{sector_code}'"
        else:
            join_clause = ""

        query = f"""
            SELECT p.*, ({rate_col} * {prob_col}) as ExpectedValue
            FROM {self.table_name} p
            {join_clause}
            WHERE p.PredDate = (SELECT MAX(PredDate) FROM {self.table_name})
            {sector_filter}
            ORDER BY {order_by}
            LIMIT {limit}
        """

        df = pd.read_sql(query, self.engine)
        return df.to_dict(orient="records")

    def save(self, result: dict):
        """
        Predictor.predict() の返り値をそのまま受け取って保存する。
        同じ (Code, PredDate) がある場合は上書きする。
        """
        predictions = result["predictions"]
        metrics = result["metrics"]

        with self.engine.begin() as conn:
            conn.execute(
                text("""
                INSERT OR REPLACE INTO PredictionsCache (
                    Code, PredDate,
                    CompanyName, CurrentPrice, PriceChangeRate,
                    Rate1d, UpProb1d, Mae1d, R2_1d, DirAcc1d,
                    Rate5d, UpProb5d, Mae5d, R2_5d, DirAcc5d,
                    Rate10d, UpProb10d, Mae10d, R2_10d, DirAcc10d
                ) VALUES (
                    :code, :pred_date,
                    :company_name, :current_price, :price_change_rate,
                    :rate_1d, :up_prob_1d, :mae_1d, :r2_1d, :dir_acc_1d,
                    :rate_5d, :up_prob_5d, :mae_5d, :r2_5d, :dir_acc_5d,
                    :rate_10d, :up_prob_10d, :mae_10d, :r2_10d, :dir_acc_10d
                )
            """),
                {
                    "code": result["code"],
                    "pred_date": result["pred_date"],
                    "company_name": result["company_name"],
                    "current_price": result["current_price"],
                    "price_change_rate": result["price_change_rate"],
                    "rate_1d": predictions["target_1d"]["rate"],
                    "up_prob_1d": predictions["target_1d"]["up_prob"],
                    "mae_1d": metrics["target_1d"]["mae"],
                    "r2_1d": metrics["target_1d"]["r2"],
                    "dir_acc_1d": metrics["target_1d"]["direction_accuracy"],
                    "rate_5d": predictions["target_5d"]["rate"],
                    "up_prob_5d": predictions["target_5d"]["up_prob"],
                    "mae_5d": metrics["target_5d"]["mae"],
                    "r2_5d": metrics["target_5d"]["r2"],
                    "dir_acc_5d": metrics["target_5d"]["direction_accuracy"],
                    "rate_10d": predictions["target_10d"]["rate"],
                    "up_prob_10d": predictions["target_10d"]["up_prob"],
                    "mae_10d": metrics["target_10d"]["mae"],
                    "r2_10d": metrics["target_10d"]["r2"],
                    "dir_acc_10d": metrics["target_10d"]["direction_accuracy"],
                },
            )

    def get_latest(self, code: str) -> dict | None:
        """
        指定銘柄の最新予測結果を取得して PredictResponse 形式の dict で返す。
        """
        df = pd.read_sql(
            f"""
            SELECT * FROM {self.table_name}
            WHERE Code = ?
            ORDER BY PredDate DESC
            LIMIT 1
            """,
            self.engine,
            params=(code,),
        )

        if df.empty:
            return None

        row = df.iloc[0]
        return {
            "code": row["Code"],
            "company_name": row["CompanyName"],
            "current_price": row["CurrentPrice"],
            "price_change_rate": row["PriceChangeRate"],
            "predictions": {
                "target_1d": {"rate": row["Rate1d"], "up_prob": row["UpProb1d"]},
                "target_5d": {"rate": row["Rate5d"], "up_prob": row["UpProb5d"]},
                "target_10d": {"rate": row["Rate10d"], "up_prob": row["UpProb10d"]},
            },
            "metrics": {
                "target_1d": {
                    "mae": row["Mae1d"],
                    "r2": row["R2_1d"],
                    "direction_accuracy": row["DirAcc1d"],
                },
                "target_5d": {
                    "mae": row["Mae5d"],
                    "r2": row["R2_5d"],
                    "direction_accuracy": row["DirAcc5d"],
                },
                "target_10d": {
                    "mae": row["Mae10d"],
                    "r2": row["R2_10d"],
                    "direction_accuracy": row["DirAcc10d"],
                },
            },
        }

    def get_latest_date(self, code: str) -> str | None:
        """指定銘柄の最新予測日を取得する"""
        df = pd.read_sql(
            f"SELECT MAX(PredDate) as latest FROM {self.table_name} WHERE Code = ?",
            self.engine,
            params=(code,),
        )
        return df.iloc[0]["latest"] if not df.empty else None
