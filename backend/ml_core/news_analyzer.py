# backend/ml_core/news_analyzer.py

import json
from datetime import datetime

from app.config import settings
from app.db.equities_master_repo import EquitiesMasterRepo
from app.db.predictions_cache_repo import PredictionsCacheRepo
from app.fetcher.rss_fetcher import RssFetcher
from google import genai
from google.genai import types


class NewsAnalyzer:
    def __init__(self):
        self.rss = RssFetcher()
        self.master_repo = EquitiesMasterRepo()
        self.pred_repo = PredictionsCacheRepo()
        self.client = genai.Client(api_key=settings.gemini_api_key)

    # ===================================================
    # ステップ2: 候補から関連記事を「選ばせる」
    # ===================================================
    def _select_relevant(self, company_name: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []

        # LLMに渡す用に番号付きリストを作成
        listing = "\n".join(
            f"{i}: {c['title']} ({c['source']})" for i, c in enumerate(candidates)
        )

        prompt = f"""あなたはプロの金融アナリストです。
以下は直近のニュース見出し一覧です。この中から「{company_name}」に
直接関連するものだけを選んでください。

【ニュース一覧】
{listing}

【出力形式】
関連する番号のみをJSON配列で出力してください。関連するものが無ければ空配列 []。
一覧に無い番号や存在しない記事を作り出さないこと。
例: [2, 5, 9]
"""
        response = self.client.models.generate_content(
            model="gemini-3.5-flash",  # 軽量かつ高速な最新モデル
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        try:
            indices = json.loads(response.text)
            return [candidates[i] for i in indices if 0 <= i < len(candidates)]
        except (json.JSONDecodeError, TypeError, IndexError):
            return []

    # ===================================================
    # ステップ3: 選ばれた記事＋数値データを統合分析
    # ===================================================
    def _analyze(
        self, company_name: str, code: str, articles: list[dict], numeric_context: dict
    ) -> dict:
        articles_text = (
            "\n\n".join(
                f"[{a['source']}] {a['title']}\n{a.get('summary', '')}"
                for a in articles
            )
            or "（関連ニュースなし）"
        )

        prompt = f"""あなたは客観的な情報整理アシスタントです。
以下の【予測データ】と【関連ニュース】のみを根拠に分析してください。

# 厳守事項
- 与えられた情報に書かれていない事実を作り出さないこと
- 数値は与えられたものをそのまま使うこと（勝手に計算しない）
- 「上がる」「下がる」の断定や投資助言は行わないこと
- ニュースに情報が無ければ topics は空配列にすること

【銘柄】{company_name}（{code}）

【予測データ】
{json.dumps(numeric_context, ensure_ascii=False, indent=2)}

【関連ニュース】
{articles_text}

# 出力形式（JSON）
{{
  "topics": [{{"text": "...", "source": "ニュース見出しそのまま or 決算データ"}}],
  "sentiment": {{"positive": ["..."], "negative": ["..."]}},
  "summary": "3〜4文程度の客観的な状況整理"
}}
"""
        response = self.client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)

    # ===================================================
    # パブリックメソッド
    # ===================================================
    def analyze(self, code: str) -> dict:
        info = self.master_repo.get_by_code(code)
        if info.empty:
            raise ValueError(f"銘柄 {code} が見つかりません。")
        company_name = info.iloc[0]["CoName"]

        # ① 事実収集
        raw_candidates = self.rss.fetch_all_candidates(days_back=7)
        keyword_filtered = self.rss.filter_by_keyword(raw_candidates, [company_name])

        # ② 目利き（LLMに選ばせる）
        selected = self._select_relevant(
            company_name, keyword_filtered or raw_candidates
        )

        # 数値コンテキスト（既存の予測結果を利用）
        prediction = self.pred_repo.get_latest(code)
        numeric_context = prediction["predictions"] if prediction else {}

        # ③ 分析
        result = self._analyze(company_name, code, selected, numeric_context)
        result["code"] = code
        result["company_name"] = company_name
        result["generated_at"] = datetime.now().strftime("%Y-%m-%d")
        result["sources_used"] = [a["url"] for a in selected]

        return result
