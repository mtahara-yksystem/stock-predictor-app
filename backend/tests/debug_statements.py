from ml_core.data_fetcher import JQuantsFetcher
import json

def debug_print_statements():
  fetcher = JQuantsFetcher()
  if not fetcher.authenticate():
    return

  print("📥 財務データを取得中...")
  # 例として日本取引所(8697)のデータを取得
  statements_raw = fetcher.fetch_financial_statements(code="8697")

  if statements_raw and 'statements' in statements_raw:
    # 最初の1件だけ中身をきれいに表示
    first_data = statements_raw['statements'][0]
    print("\n--- 財務データ(最新の1件)の中身 ---")
    print(json.dumps(first_data, indent=2, ensure_ascii=False))

    print(f"\n合計 {len(statements_raw['statements'])} 件の決算データが見つかりました。")
  else:
    print("データが見つかりませんでした。")

if __name__ == "__main__":
  debug_print_statements()