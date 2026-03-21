import pandas as pd


def preprocess_v2_data(raw_data):
  # データが空でも最低限のカラムを持つDFを返す
  cols = ["Date", "open", "high", "low", "close", "volume"]
  if not raw_data:
    return pd.DataFrame(columns=cols)

  df = pd.DataFrame(raw_data)
  rename_map = {
    "O": "open",
    "H": "high",
    "L": "low",
    "C": "close_raw",
    "Vo": "volume",
    "AdjC": "close",
  }
  df = df.rename(columns=rename_map)

  if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
  else:
    # Dateがない場合も空DFを返す
    return pd.DataFrame(columns=cols)
  return df


def merge_v2_financials(df_stock, raw_fin):
  # 株価データ自体が空なら空DFを返す
  if df_stock.empty:
    return df_stock

  if not raw_fin or len(raw_fin) == 0:
    df_res = df_stock.copy()
    df_res["eps"] = 0.0
    df_res["equity_ratio"] = 0.0
    return df_res.set_index("Date")

  df_fin = pd.DataFrame(raw_fin)
  date_col = "DiscDate" if "DiscDate" in df_fin.columns else None

  if not date_col:
    df_res = df_stock.copy()
    df_res["eps"] = 0.0
    df_res["equity_ratio"] = 0.0
    return df_res.set_index("Date")

  df_fin["Date_fin"] = pd.to_datetime(df_fin[date_col])
  df_fin = df_fin.rename(columns={"EPS": "eps", "EqAR": "equity_ratio"})

  for c in ["eps", "equity_ratio"]:
    if c in df_fin.columns:
      df_fin[c] = pd.to_numeric(df_fin[c], errors="coerce").fillna(0.0)
    else:
      df_fin[c] = 0.0

  df_fin = df_fin[["Date_fin", "eps", "equity_ratio"]].drop_duplicates(
    subset=["Date_fin"], keep="last"
  )

  df_merged = pd.merge_asof(
    df_stock.sort_values("Date"),
    df_fin.sort_values("Date_fin"),
    left_on="Date",
    right_on="Date_fin",
    direction="backward",
  )
  return df_merged.set_index("Date").ffill().fillna(0)
