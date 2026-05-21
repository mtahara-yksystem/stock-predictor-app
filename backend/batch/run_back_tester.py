from ml_core.backtester import Backtester


def main():
    sector_code = "11"
    stock_code = "95320"

    bt = Backtester(sector_code)
    bt.run(stock_code)


if __name__ == "__main__":
    main()
