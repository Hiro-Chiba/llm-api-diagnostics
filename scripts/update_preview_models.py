"""Preview モデル一覧を自動更新するスクリプト

Gemini REST API からモデル一覧を取得し、list() では返らない
Preview モデルを検出して model_checker.py のハードコードリストを更新する。
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

API_BASE = "https://generativelanguage.googleapis.com"
MODEL_CHECKER_PATH = os.path.join(os.path.dirname(__file__), "..", "gemini", "model_checker.py")
HTTP_TIMEOUT_SEC = 30
MAX_PAGES = 50
REQUEST_INTERVAL_SEC = 1.0  # レート制限対策: API 呼び出し間の最小インターバル


def _fetch_json(url: str, api_key: str) -> dict:
    """API キーはヘッダーで送り、URL には含めない。エラー時は API キーを漏らさない。"""
    req = urllib.request.Request(url, headers={"x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {e.reason}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"ネットワークエラー: {e.reason}") from None
    except TimeoutError:
        raise RuntimeError(f"タイムアウト（{HTTP_TIMEOUT_SEC}s）") from None


def _paginate(path: str, api_key: str) -> list[dict]:
    """pageToken を辿って全ページをまとめて返す。ページ数には上限を設ける。"""
    items: list[dict] = []
    params = {"pageSize": "100"}
    for page in range(MAX_PAGES):
        if page > 0:
            time.sleep(REQUEST_INTERVAL_SEC)
        url = f"{API_BASE}{path}?{urlencode(params)}"
        data = _fetch_json(url, api_key)
        items.extend(data.get("models", []))
        token = data.get("nextPageToken")
        if not token:
            return items
        params["pageToken"] = token
    raise RuntimeError(f"ページ数が上限（{MAX_PAGES}）を超えました")


def fetch_all_models(api_key: str) -> list[dict]:
    """v1beta API から全モデルを取得する（Preview 含む）。"""
    return _paginate("/v1beta/models", api_key)


def fetch_ga_model_names(api_key: str) -> set[str]:
    """v1 API（GA のみ）からモデル名を取得する。"""
    models = _paginate("/v1/models", api_key)
    return {m["name"].removeprefix("models/") for m in models}


def find_preview_models(all_models: list[dict], ga_names: set[str]) -> list[str]:
    """v1beta にあるが v1 にないモデルのうち、generateContent 対応のものを返す。"""
    preview = []
    for m in all_models:
        name = m["name"].removeprefix("models/")
        if name in ga_names:
            continue
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            preview.append(name)
    preview.sort()
    return preview


def read_current_list(path: str) -> list[str]:
    """model_checker.py から現在の preview_models リストを読み取る。"""
    with open(path) as f:
        content = f.read()
    match = re.search(r"preview_models\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def update_model_checker(path: str, new_list: list[str]) -> bool:
    """model_checker.py の preview_models リストを更新する。変更があれば True。"""
    with open(path) as f:
        content = f.read()

    items = ",\n".join(f'        "{name}"' for name in new_list)
    new_block = f"preview_models = [\n{items},\n    ]"

    updated = re.sub(
        r"preview_models\s*=\s*\[.*?\]",
        new_block,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if updated == content:
        return False

    with open(path, "w") as f:
        f.write(updated)
    return True


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY が設定されていません。")
        sys.exit(1)

    path = os.path.normpath(MODEL_CHECKER_PATH)

    try:
        print("v1beta API から全モデル取得中...")
        all_models = fetch_all_models(api_key)
        print(f"  {len(all_models)} モデル取得")

        time.sleep(REQUEST_INTERVAL_SEC)

        print("v1 API から GA モデル取得中...")
        ga_names = fetch_ga_model_names(api_key)
        print(f"  {len(ga_names)} GA モデル取得")
    except RuntimeError as e:
        print(f"API 呼び出し失敗: {e}")
        sys.exit(1)

    preview = find_preview_models(all_models, ga_names)
    print(f"  Preview（generateContent 対応）: {len(preview)} 件")
    for name in preview:
        print(f"    - {name}")

    current = read_current_list(path)
    print(f"\n現在のハードコード: {current}")
    print(f"API から検出:       {preview}")

    added = set(preview) - set(current)
    removed = set(current) - set(preview)
    if added:
        print(f"\n新規追加: {sorted(added)}")
    if removed:
        print(f"削除（廃止等）: {sorted(removed)}")

    if not added and not removed:
        print("\n変更なし。")
        return

    if update_model_checker(path, preview):
        print(f"\n{path} を更新しました。")
    else:
        print("\nファイル更新に失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()
