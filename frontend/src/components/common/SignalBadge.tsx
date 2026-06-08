// frontend/src/components/common/SignalBadge.tsx

import type { SignalType, StrengthType } from "@/types/signal";

interface Props {
  signal: SignalType;
  strength: StrengthType;
}

export const SignalBadge = ({ signal, strength }: Props) => {
  const isStrong = strength === "STRONG";

  if (signal === "BUY") {
    return (
      <span className={`signal-badge ${isStrong ? "signal-badge--strong-buy" : "signal-badge--buy"}`}>
        {isStrong ? "🟢 STRONG BUY" : "🔵 BUY"}
      </span>
    );
  }

  if (signal === "SELL") {
    return (
      <span className={`signal-badge ${isStrong ? "signal-badge--strong-sell" : "signal-badge--sell"}`}>
        {isStrong ? "🔴 STRONG SELL" : "🟠 SELL"}
      </span>
    );
  }

  return null;
};