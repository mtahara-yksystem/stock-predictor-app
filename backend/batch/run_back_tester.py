# backend/batch/run_back_tester.py

from ml_core.backtester import Backtester


def main():
    sector_code = "11"
    # stock_code = "95320"

    bt = Backtester(sector_code)

    # 単体バックテスト
    # bt.run(stock_code, target="target_5d")

    # 最適閾値を探す
    # bt.run_threshold_search(stock_code, target="target_5d")

    # セクター全体を検証
    bt.run_sector(target="target_5d", prob_threshold=0.6)


if __name__ == "__main__":
    main()
