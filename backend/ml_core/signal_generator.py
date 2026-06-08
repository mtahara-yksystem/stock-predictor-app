# backend/ml_core/signal_generator.py


class SignalGenerator:
    """
    STRONG BUY  : up_prob >= 0.65 かつ pred_rate >= 0.02
    BUY         : up_prob >= 0.60 かつ pred_rate >= 0.00
    STRONG SELL : up_prob <= 0.35 かつ pred_rate <= -0.02
    SELL        : up_prob <= 0.40 かつ pred_rate <= 0.00
    HOLD        : 上記以外
    """

    THRESHOLDS = {
        "STRONG_BUY": {"up_prob_min": 0.65, "pred_rate_min": 0.02},
        "BUY": {"up_prob_min": 0.60, "pred_rate_min": 0.00},
        "STRONG_SELL": {"up_prob_max": 0.35, "pred_rate_max": -0.02},
        "SELL": {"up_prob_max": 0.40, "pred_rate_max": 0.00},
    }

    def generate(self, up_prob: float, pred_rate: float) -> dict:
        """
        Returns:
            {"signal": "BUY"|"SELL"|"HOLD", "strength": "STRONG"|"WEAK"|None}
        """
        t = self.THRESHOLDS

        if (
            up_prob >= t["STRONG_BUY"]["up_prob_min"]
            and pred_rate >= t["STRONG_BUY"]["pred_rate_min"]
        ):
            return {"signal": "BUY", "strength": "STRONG"}

        if (
            up_prob >= t["BUY"]["up_prob_min"]
            and pred_rate >= t["BUY"]["pred_rate_min"]
        ):
            return {"signal": "BUY", "strength": "WEAK"}

        if (
            up_prob <= t["STRONG_SELL"]["up_prob_max"]
            and pred_rate <= t["STRONG_SELL"]["pred_rate_max"]
        ):
            return {"signal": "SELL", "strength": "STRONG"}

        if (
            up_prob <= t["SELL"]["up_prob_max"]
            and pred_rate <= t["SELL"]["pred_rate_max"]
        ):
            return {"signal": "SELL", "strength": "WEAK"}

        return {"signal": "HOLD", "strength": None}
