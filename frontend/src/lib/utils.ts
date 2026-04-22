/**
 * 株価予測アプリ共通ユーティリティ
 */

/**
 * 1. 通貨フォーマット (例: 1234.5 -> ¥1,235)
 * 小数点以下は四捨五入して日本円の表記に合わせます
 */
export const formatPrice = (price: number): string => {
  return price.toLocaleString("ja-JP", {
    style: "currency",
    currency: "JPY",
  });
};

/**
 * 2. 騰落率フォーマット (例: 0.0523 -> +5.23%)
 * @param val 小数点形式の率 (0.05 = 5%)
 */
export const formatRate = (val: number): string => {
  const pct = (val * 100).toFixed(2);
  return val >= 0 ? `+${pct}%` : `${pct}%`;
};

/**
 * 3. 確率・正解率フォーマット (例: 0.854 -> 85.4%)
 * @param val 小数点形式の率 (0.8 = 80%)
 */
export const formatProb = (val: number): string => {
  return `${(val * 100).toFixed(1)}%`;
};

/**
 * 4. ステータスメタ情報取得
 * 数値に基づいて、一貫したカラークラスとラベルを返します
 */
export const getStatusMeta = (val: number, type: "rate" | "prob" | "dir") => {
  // 騰落率の場合：プラスかマイナスか
  if (type === "rate") {
    return {
      colorClass: val >= 0 ? "text-up" : "text-down",
      label: "",
      color: val >= 0 ? "var(--up)" : "var(--down)",
    };
  }

  // 確率・方向正解率の場合：しきい値で「高・中・低」を判定
  if (type === "prob" || type === "dir") {
    if (val >= 0.6) {
      return {
        colorClass: "text-up",
        label: "高",
        color: "var(--up)",
        bgClass: "bg-up",
      };
    }
    if (val >= 0.5) {
      return {
        colorClass: "text-yellow",
        label: "中",
        color: "var(--yellow)",
        bgClass: "bg-yellow",
      };
    }
    return {
      colorClass: "text-muted",
      label: "低",
      color: "var(--text-muted)",
      bgClass: "bg-muted",
    };
  }

  return { colorClass: "", label: "", color: "", bgClass: "" };
};

/**
 * 5. 方向正解率専用のメタ情報取得（getStatusMetaのエイリアス）
 * コードの可読性のために getDirAccMeta という名前でも呼べるようにします
 */
export const getDirAccMeta = (acc: number) => getStatusMeta(acc, "dir");