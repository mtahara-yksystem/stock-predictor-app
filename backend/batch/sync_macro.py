from datetime import datetime, timedelta

from app.db.macro_indicators_repo import MacroIndicatorsRepo
from app.fetcher.yfinance_fetcher import YFinanceFetcher, MACRO_TICKERS


def run_macro_sync():
    """
    マクロ指標をyfinanceから取得してDBに差分保存する。
    初回: 過去730日分を全取得
    2回目以降: 最新日の翌日から差分取得
    """
    fetcher = YFinanceFetcher()
    repo = MacroIndicatorsRepo()

    # 各ティッカーの最新日を確認して差分取得の起点を決める
    latest_dates = [
        repo.get_latest_date(ticker) for ticker in MACRO_TICKERS.keys()
    ]
    latest_dates = [d for d in latest_dates if d is not None]

    if not latest_dates:
        # 初回: 過去730日分を全取得
        print("🆕 初回取得: 過去730日分のマクロ指標を取得します...")
        df = fetcher.fetch_macro_indicators(days_back=730)
    else:
        # 差分取得: 最も古い最新日の翌日から取得
        oldest_latest = min(latest_dates)
        since = (
            datetime.strptime(oldest_latest, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        print(f"🔄 差分取得: {since} 以降のマクロ指標を取得します...")
        df = fetcher.fetch_macro_since(since)

    if df.empty:
        print("✅ 新しいデータはありませんでした。")
        return

    count = repo.save(df)
    print(f"✨ マクロ指標の同期完了: {count}件を新規保存しました。")


if __name__ == "__main__":
    run_macro_sync()
