"""Preview モデル一覧を自動更新するスクリプト

Gemini REST API からモデル一覧を取得し、list() では返らない
Preview モデルを検出して model_checker.py のハードコードリストを更新する。
"""

import json
import os
import re
import sys
import urllib.request

API_BASE = "https://generativelanguage.googleapis.com"
MODEL_CHECKER_PATH = os.path.join(os.path.dirname(__file__), "..", "gemini", "model_checker.py")


def fetch_all_models(api_key: str) -> list[dict]:
    """v1beta API から全モデルを取得する（Preview 含む）。"""
    models = []
    url = f"{API_BASE}/v1beta/models?key={api_key}&pageSize=100"
    while url:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        models.extend(data.get("models", []))
        token = data.get("nextPageToken")
        if token:
            url = f"{API_BASE}/v1beta/models?key={api_key}&pageSize=100&pageToken={token}"
        else:
            url = None
    return models


def fetch_ga_model_names(api_key: str) -> set[str]:
    """v1 API（GA のみ）からモデル名を取得する。"""
    names = set()
    url = f"{API_BASE}/v1/models?key={api_key}&pageSize=100"
    while url:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        for m in data.get("models", []):
            names.add(m["name"].removeprefix("models/"))
        token = data.get("nextPageToken")
        if token:
            url = f"{API_BASE}/v1/models?key={api_key}&pageSize=100&pageToken={token}"
        else:
            url = None
    return names


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
        flags=re.DOTALL,
    )

    if updated == content:
        return False

    with open(path, "w") as f:
        f.write(updated)
    return True


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY が設定されていません。")
        sys.exit(1)

    path = os.path.normpath(MODEL_CHECKER_PATH)

    print("v1beta API から全モデル取得中...")
    all_models = fetch_all_models(api_key)
    print(f"  {len(all_models)} モデル取得")

    print("v1 API から GA モデル取得中...")
    ga_names = fetch_ga_model_names(api_key)
    print(f"  {len(ga_names)} GA モデル取得")

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
