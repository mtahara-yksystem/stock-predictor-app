// frontend/src/components/common/SignalBadge.tsx

import type { SignalType, StrengthType } from "@/types/signal";

interface Props {
  signal: SignalType;
  strength: StrengthType;
}

export const SignalBadge = ({ signal, strength }: Props) => {
  if (signal !== "BUY") return null;

  const isStrong = strength === "STRONG";

  return (
    <span className={`signal-badge ${isStrong ? "signal-badge--strong" : "signal-badge--weak"}`}>
      {isStrong ? "🟢 STRONG BUY" : "🔵 BUY"}
    </span>
  );
};