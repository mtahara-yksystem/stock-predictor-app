# backend/ml_core/signal_generator.py


class SignalGenerator:
    """
    バックテストで検証した閾値をもとにシグナルを生成する。

    STRONG BUY : up_prob >= 0.65 かつ pred_rate >= 0.02
    BUY        : up_prob >= 0.60 かつ pred_rate >= 0.00
    HOLD       : 上記以外
    """

    # バックテスト検証済み閾値
    THRESHOLDS = {
        "STRONG": {"up_prob": 0.65, "pred_rate": 0.02},
        "WEAK": {"up_prob": 0.60, "pred_rate": 0.00},
    }

    def generate(self, up_prob: float, pred_rate: float) -> dict:
        """
        Returns:
            {"signal": "BUY"|"HOLD", "strength": "STRONG"|"WEAK"|None}
        """
        strong = self.THRESHOLDS["STRONG"]
        weak = self.THRESHOLDS["WEAK"]

        if up_prob >= strong["up_prob"] and pred_rate >= strong["pred_rate"]:
            return {"signal": "BUY", "strength": "STRONG"}

        if up_prob >= weak["up_prob"] and pred_rate >= weak["pred_rate"]:
            return {"signal": "BUY", "strength": "WEAK"}

        return {"signal": "HOLD", "strength": None}
