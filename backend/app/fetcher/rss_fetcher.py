# backend/app/fetcher/rss_fetcher.py

import difflib

import feedparser

# 経済ニュースRSS（必要に応じて追加）
NEWS_FEEDS = {
    "yahoo": "https://news.yahoo.co.jp/rss/categories/business.xml",
    "investing_stock": "https://jp.investing.com/rss/news_25.rss",  # 株式市場
    "investing_company": "https://jp.investing.com/rss/news_356.rss",  # 企業ニュース
    "investing_insider": "https://jp.investing.com/rss/news_357.rss",  # インサイダー
    "investing_analyst": "https://jp.investing.com/rss/news_1061.rss",  # 株式アナリスト評価
    "investing_earnings_report": "https://jp.investing.com/rss/news_1062.rss",  # 決算発表
    # 銘柄によってはIR系フィードも有効
}


class RssFetcher:
    def fetch_all_candidates(self, days_back: int = 7) -> list[dict]:
        """
        全フィードから直近days_back日以内の記事を取得する。
        「事実」として100%そのままリスト化する（AIは一切介在しない）。
        """
        candidates = []

        for source_name, url in NEWS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    candidates.append(
                        {
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "source": source_name,
                            "summary": entry.get("summary", ""),  # RSSの短い要約
                        }
                    )
            except Exception as e:
                print(f"⚠️ {source_name} のRSS取得に失敗: {e}")

        return candidates

    def deduplicate(
        self, candidates: list[dict], threshold: float = 0.85
    ) -> list[dict]:
        """URLの完全一致 ＋ タイトルの類似度（あいまい一致）で重複排除する。

        threshold: 0.85 (85%以上一致したら同じニュースとみなして除外)
        """
        deduped = []
        seen_urls = set()
        seen_titles = []

        for c in candidates:
            url = c.get("url")
            title = c.get("title", "").strip()

            # 1. URLによる完全重複チェック（最も高速）
            if url and url in seen_urls:
                continue

            # 2. タイトル類似度によるチェック（転載記事・類似見出し対策）
            is_duplicate = False
            for seen_title in seen_titles:
                ratio = difflib.SequenceMatcher(None, title, seen_title).ratio()
                if ratio >= threshold:
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            # 重複でなければ保持リストに追加
            if url:
                seen_urls.add(url)
            seen_titles.append(title)
            deduped.append(c)

        return deduped

    def filter_by_keyword(
        self, candidates: list[dict], keywords: list[str]
    ) -> list[dict]:
        """
        会社名・銘柄コードなどのキーワードで一次フィルタ（軽量なノイズ削減）。
        ここではまだLLMを使わず、単純な文字列マッチで絞り込む。
        """
        filtered = []
        for c in candidates:
            text = c["title"] + c.get("summary", "")
            if any(kw in text for kw in keywords):
                filtered.append(c)
        return filtered
