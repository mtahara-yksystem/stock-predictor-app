import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler


def build_and_train_model(
    X_train,
    y_train,
    X_val,
    y_val,
    max_depth: int = 6,
    colsample_bytree: float = 0.7,
):
    y_train_scaled = y_train * 100
    y_val_scaled = y_val * 100

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(
        X_val
    )  # fit済みのscalerでtransformのみ（データリーク防止）

    model = xgb.XGBRegressor(
        n_estimators=2000,
        learning_rate=0.01,
        max_depth=max_depth,
        subsample=0.8,
        colsample_bytree=colsample_bytree,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=100,
    )

    print("🌲 XGBoost エンジンを再教育中...")
    model.fit(
        X_train_scaled,
        y_train_scaled,
        eval_set=[(X_val_scaled, y_val_scaled)],
        verbose=False,
    )

    print(f"✅ 最適なイテレーション数: {model.best_iteration}")

    importance = pd.DataFrame(
        {"feature": X_train.columns, "importance": model.feature_importances_}
    ).sort_values(by="importance", ascending=False)

    print("\n📊 AIが重視した指標 Top 5:")
    print(importance.head(5))

    return model, scaler


def evaluate_model(model, scaler, X_test, y_test):
    X_test_scaled = scaler.transform(X_test)
    # 予測結果を元の単位に戻す（/100）
    predictions = model.predict(X_test_scaled) / 100

    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # 方向正解率: 予測と実績の符号（上昇/下落方向）が一致した割合
    # 0.5を超えれば方向予測に意味があると判断できる
    direction_accuracy = float(np.mean(np.sign(predictions) == np.sign(y_test)))

    return predictions, mae, r2, direction_accuracy
