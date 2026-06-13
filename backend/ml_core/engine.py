import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score


def _direction_eval(y_pred, dtrain):
    """XGBoostのカスタム評価関数：方向正解率を直接監視する"""
    y_true = dtrain.get_label()
    pred_class = (y_pred > 0.5).astype(int)
    acc = accuracy_score(y_true, pred_class)
    # XGBoostのカスタムmetricは (name, value) を返す
    # maximize=True にするため、そのままaccを返す（後述のeval_metricsで設定）
    return "dir_acc", acc


def build_and_train_model(
    X_train,
    y_train,
    X_val,
    y_val,
    max_depth: int = 6,
    colsample_bytree: float = 0.7,
):
    """
    XGBClassifier で方向（上昇/下落）を直接分類する。
    スケーラーは不要なので削除。
    戻り値: (model, None) — trainer.py側のインターフェースを保つためNoneを返す
    """
    # ターゲットはすでに 0/1 のクラスラベルを想定（trainer.pyで変換済み）
    model = xgb.XGBClassifier(
        n_estimators=2000,
        learning_rate=0.01,
        max_depth=max_depth,
        subsample=0.8,
        colsample_bytree=colsample_bytree,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=100,
        eval_metric="logloss",
        enable_categorical=True,  # ★ 追加
    )

    print("🌲 XGBClassifier で方向分類を学習中...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    print(f"✅ 最適イテレーション数: {model.best_iteration}")

    importance = pd.DataFrame(
        {"feature": X_train.columns, "importance": model.feature_importances_}
    ).sort_values(by="importance", ascending=False)

    print("\n📊 AIが重視した指標 Top 5:")
    print(importance.head(5))

    # スケーラーはNoneで返す（predictor.py側もNoneチェックを追加）
    return model, None


def evaluate_model(model, scaler, X_test, y_test):
    """
    分類モデルの評価。
    scaler は使わない（Noneで渡される）が引数は維持してインターフェースを統一。
    """
    # predict_proba で上昇確率を取得
    up_probs = model.predict_proba(X_test)[:, 1]
    pred_class = (up_probs > 0.5).astype(int)

    direction_accuracy = float(accuracy_score(y_test, pred_class))

    # trainer.py の metrics_summary との互換性のため mae/r2 も返す
    # 分類なので意味は薄いが、既存のJSON構造を壊さないよう残す
    from sklearn.metrics import log_loss

    mae = float(log_loss(y_test, up_probs))  # 代わりにlog_lossを格納
    r2 = 0.0  # 分類では不使用

    return up_probs, mae, r2, direction_accuracy
