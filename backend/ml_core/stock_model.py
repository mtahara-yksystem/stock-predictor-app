import os

import joblib
import xgboost as xgb
from sklearn.metrics import root_mean_squared_error
from sklearn.model_selection import train_test_split


class StockModel:
    def __init__(self, model_path="models/model.pkl"):
        self.model_path = model_path
        self.model = None

        # 保存先ディレクトリ作成
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

    def train(self, X, y):
        """本物のデータでモデルを学習させる"""
        print(f"🚀 学習開始... (サンプル数: {len(X)})")

        # 1. データを「学習用」と「テスト用」に分割 (直近20%をテストに)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

        # 2. XGBoostモデルの設定
        self.model = xgb.XGBRegressor(
            n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42
        )

        # 3. 学習
        self.model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        # 4. 精度評価 (RMSE)
        preds = self.model.predict(X_test)
        rmse = root_mean_squared_error(y_test, preds)
        print(f"✅ 学習完了！ RMSE (平均誤差率): {rmse:.4f}")

        # 5. 保存
        joblib.dump(self.model, self.model_path)
        print(f"💾 モデルを保存しました: {self.model_path}")

    def predict(self, X):
        """予測を実行する"""
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                raise Exception("モデルが見つかりません。先に学習させてください。")
        return self.model.predict(X)
