import time

from app.db.equities_master_repo import EquitiesMasterRepo
from app.fetcher.jquants_fetcher import JQuantsFetcher
from ml_core.data_sync import DataSync


def run_sector_sync(sector_code="7", limit=20):
    """
    指定したセクターの銘柄を巡回してDBを更新する
    """
    fetcher = JQuantsFetcher()
    sync = DataSync(fetcher=fetcher)
    repo = EquitiesMasterRepo()

    # 1. 銘柄リストを取得
    targets = repo.get_learning_targets(sector_code, limit=limit)
    print(f"🚀 セクター {sector_code} の {len(targets)} 銘柄を同期開始...")

    for i, (code, company_name) in enumerate(targets):
        retry_count = 0
        print(
            f"🔄 [{i + 1:02d}/{len(targets)}] {code} | {company_name:15s} ... ",
            end="",
            flush=True,
        )

        try:
            q_count = sync.sync_daily_quotes(code)
            f_count = sync.sync_financial_summary(code)

            print(f"✅ 完了 (株価:{q_count:3d}件, 財務:{f_count:2d}件)")

            # 1分間に5回制限（1回12秒以上空ける）を考慮
            # 1銘柄で2回APIを叩くなら、次の銘柄まで25秒くらい待つのが確実
            print("⏳ API制限回避のため25秒待機中...")
            time.sleep(25)
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ 制限中... 60秒待機してリトライします({retry_count + 1}/3)")
                time.sleep(60)  # 1分休む
            else:
                print(f"❌ 失敗: {e}")
                break  # 429以外のエラーは飛ばす


if __name__ == "__main__":
    # まずは('7')の20銘柄で試してみる
    run_sector_sync(sector_code="7", limit=20)
