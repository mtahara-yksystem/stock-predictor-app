import json

from app.config import settings
from app.db.financial_summaries_repo import FinancialSummariesRepo
from google import genai
from google.genai import types


class FinancialAnalyzer:
    """
    DB保存済みの財務データ（FinancialSummaries）をLLMに渡し、
    客観的な要約・評価を生成する。
    LLMは「事実整理役」であり、投資判断そのものは行わない。
    """

    def __init__(self):
        self.repo = FinancialSummariesRepo()
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def _build_prompt(self, code: str, records: list[dict]) -> str:
        rows_text = "\n".join(
            f"- {r['DiscDate']} ({r.get('CurPerType', '')}): "
            f"売上高={r.get('Sales')}, 営業利益={r.get('OP')}, "
            f"経常利益={r.get('OdP')}, 当期純利益={r.get('NP')}, "
            f"EPS={r.get('EPS')}, 自己資本比率={r.get('EqAR')}"
            for r in records
        )

        return f"""あなたは株式投資家向けに決算データを客観的に整理するアシスタントです。
以下は銘柄コード {code} の直近の決算数値です。

{rows_text}

以下のJSON形式のみで出力してください。前置き・後書き・Markdown記法は不要です。
{{
  "summary": "直近の業績トレンドを2〜3文で要約",
  "positives": ["ポジティブな材料を箇条書きで最大3件"],
  "concerns": ["注意すべき材料を箇条書きで最大3件"],
  "trend": "improving | stable | declining のいずれか"
}}

注意: これは投資助言ではありません。数値の傾向を客観的に整理するのみとし、
「買い」「売り」等の推奨表現は使わないでください。
"""

    def analyze(self, code: str, quarters: int = 4) -> dict:
        records = self.repo.get_recent_for_llm(code, limit=quarters)
        if not records:
            return {
                "summary": "財務データが見つかりませんでした。",
                "positives": [],
                "concerns": [],
                "trend": "unknown",
            }

        prompt = self._build_prompt(code, records)
        response = self.client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        raw_text = response.text.strip()

        # ```json ... ``` で囲まれて返ってきた場合の除去
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            print(f"⚠️ JSON解析失敗、生テキストのまま返します: {raw_text[:100]}")
            parsed = {
                "summary": raw_text,
                "positives": [],
                "concerns": [],
                "trend": "unknown",
            }

        return parsed
