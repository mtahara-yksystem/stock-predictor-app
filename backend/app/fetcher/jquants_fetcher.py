import requests


class JQuantsFetcher:
    def __init__(self):
        self.api_key = "sDyJr0EaP2XtWsEq9_dTcl0HMpX_ZO7G_WsvLMNm3cU"
        self.base_url = "https://api.jquants.com/v2"
        self.headers = {"x-api-key": self.api_key}

    def fetch_equities_master(self):
        url = f"{self.base_url}/equities/master"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            data = res.json()
            # v2は 'info' か 'data' に格納されている
            return data.get("info") or data.get("data") or []
        return []

    def fetch_daily_quotes(self, code, from_date=None, to_date=None):
        url = f"{self.base_url}/equities/bars/daily"
        params = {"code": code}
        if from_date:
            params["from"] = from_date

        res = requests.get(url, headers=self.headers, params=params)
        print(f"DEBUG: Status={res.status_code}, Response={res.text[:200]}")

        if res.status_code == 200:
            data = res.json()
            # キー名を全部書き出してみる
            print(f"DEBUG: Keys found in JSON = {data.keys()}")
            return data.get("daily_quotes") or data.get("data") or []
        return []

    def fetch_financial_summary(self, code):
        url = f"{self.base_url}/fins/summary"
        params = {"code": code}
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code == 200:
            data = res.json()
            return data.get("statements") or data.get("data") or []
        return []
