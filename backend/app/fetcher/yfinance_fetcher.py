from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

# 取得対象のマクロ指標
MACRO_TICKERS = {
    "USDJPY=X": "ドル円",
    "^GSPC": "S&P500",
    "^TNX": "米10年債利回り",
}


class YFinanceFetcher:
    def fetch_macro_indicators(self, days_back: int = 730):
        """
        マクロ指標の終値を取得してDataFrameで返す。

        Returns:
            DataFrame: Date, Ticker, Close の3カラム
        """
        since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        records = []

        for ticker, name in MACRO_TICKERS.items():
            print(f"📥 {name}（{ticker}）を取得中...")
            try:
                df = yf.download(
                    ticker,
                    start=since,
                    end=today,
                    progress=False,
                    auto_adjust=True,
                )
                if df.empty:
                    print(f"⚠️ {ticker}: データが空でした")
                    continue

                for date, row in df.iterrows():
                    records.append(
                        {
                            "Date": date.strftime("%Y-%m-%d"),
                            "Ticker": ticker,
                            "Close": float(row["Close"]),
                        }
                    )

                print(f"✅ {ticker}: {len(df)}件取得")

            except Exception as e:
                print(f"❌ {ticker} の取得に失敗しました: {e}")

        return pd.DataFrame(records)

    def fetch_macro_since(self, since: str):
        """
        指定日以降のマクロ指標を取得する（差分更新用）。
        """
        today = datetime.now().strftime("%Y-%m-%d")

        records = []

        for ticker, name in MACRO_TICKERS.items():
            try:
                df = yf.download(
                    ticker,
                    start=since,
                    end=today,
                    progress=False,
                    auto_adjust=True,
                )
                if df.empty:
                    continue

                for date, row in df.iterrows():
                    records.append(
                        {
                            "Date": date.strftime("%Y-%m-%d"),
                            "Ticker": ticker,
                            "Close": float(row["Close"]),
                        }
                    )

            except Exception as e:
                print(f"❌ {ticker} の取得に失敗しました: {e}")

        return pd.DataFrame(records)
