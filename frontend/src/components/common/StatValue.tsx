// frontend/src/components/common/StatValue.tsx
import { formatRate } from "@/lib/utils";

interface Props {
  value: number;
  type: "rate" | "prob";
  showColor?: boolean;
}

export const StatValue = ({ value, type, showColor = true }: Props) => {
  const formatted = type === "rate" ? formatRate(value) : `${(value * 100).toFixed(1)}%`;

  let colorClass = "";
  if (showColor) {
    if (type === "rate") {
      colorClass = value >= 0 ? "text-up" : "text-down";
    } else {
      // 確率の場合は 50% 以上かどうか
      colorClass = value >= 0.6 ? "text-up" : value >= 0.5 ? "text-yellow" : "text-down";
    }
  }

  return <span className={colorClass}>{formatted}</span>;
};