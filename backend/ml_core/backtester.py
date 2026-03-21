import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from .data_utils import merge_with_financials, preprocess_jquants_data
from .features import FeatureEngineer


class Backtester:
  def __init__(self, api_client):
    self.api_client = api_client
    self.engineer = FeatureEngineer()
    self.model = LGBMRegressor(
      n_estimators=100, learning_rate=0.05, random_state=42, importance_type="gain"
    )

  def run(self, code: str, start_date: str, end_date: str):
    print(f"--- Backtest Start: {code} ({start_date} to {end_date}) ---")

    # 1. データの取得 (個別株 + 財務 + 日経平均)
    print("Fetching data...")
    raw_prices = self.api_client.get_prices_daily_quotes(
      code=code, from_date=start_date, to_date=end_date
    )
    raw_fins = self.api_client.get_statements(code=code)
    # 日経平均(0000)を取得して市場の地合いデータとする
    raw_index = self.api_client.get_prices_daily_quotes(
      code="0000", from_date=start_date, to_date=end_date
    )

    # 2. 前処理
    print("Preprocessing...")
    df_stock = preprocess_jquants_data(raw_prices)
    df_index = preprocess_jquants_data(raw_index)
    df_merged = merge_with_financials(df_stock, raw_fins)

    # 3. 特徴量生成 (日経平均データを渡す)
    print("Engineering features...")
    X, y = self.engineer.create_features_and_target(df_merged, index_df=df_index)

    if X.empty:
      print("Error: Not enough data to create features.")
      return

    # 4. 時系列順に訓練データとテストデータに分割 (直近20%をテスト)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # 5. モデル学習
    print("Training model...")
    self.model.fit(X_train, y_train)

    # 6. 予測とシミュレーション
    print("Simulating trades...")
    preds = self.model.predict(X_test)

    # 結果格納用DataFrame
    results = pd.DataFrame(index=X_test.index)
    results["actual_ret"] = y_test
    results["pred_ret"] = preds

    # シンプルな戦略: 予測値がプラスなら「買い(1)」、マイナスなら「ノーポジ(0)」
    results["signal"] = np.where(results["pred_ret"] > 0, 1, 0)
    # 翌日のリターンを当日のシグナルで計算
    results["strategy_ret"] = results["signal"] * results["actual_ret"]

    # 累積リターンの計算
    results["cum_strategy"] = (1 + results["strategy_ret"]).cumprod()
    results["cum_market"] = (1 + results["actual_ret"]).cumprod()

    # 7. 評価指標の算出
    final_return = results["cum_strategy"].iloc[-1] - 1
    win_rate = (
      len(results[results["strategy_ret"] > 0]) / len(results[results["signal"] > 0])
      if len(results[results["signal"] > 0]) > 0
      else 0
    )

    print("\n[Results]")
    print(f"Total Strategy Return: {final_return:.2%}")
    print(f"Market (Buy & Hold) Return: {(results['cum_market'].iloc[-1] - 1):.2%}")
    print(f"Win Rate (when signaled): {win_rate:.2%}")

    # 8. 可視化
    self._plot_results(results, code)

    return results

  def _plot_results(self, results, code):
    plt.figure(figsize=(12, 6))
    plt.plot(results["cum_strategy"], label="AI Strategy", color="blue", linewidth=2)
    plt.plot(
      results["cum_market"], label="Market (Buy & Hold)", color="gray", linestyle="--"
    )
    plt.title(f"Backtest Result: {code}")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.grid(True, alpha=0.3)
    # ここでは表示せず、呼び出し元でplt.show()できるようにする、
    # または画像として保存する運用が一般的です。
    plt.show()
