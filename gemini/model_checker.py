"""Gemini API モデル診断スクリプト

利用可能な全モデル + Preview モデルに対して短文生成テストを実行し、結果をサマリ表示する。
list() API は GA モデルのみ返すため、Preview モデルは別途明示的にテストする。
"""

import os
import sys
import time

try:
    from google import genai
except ImportError:
    print("必要なパッケージがありません。以下を実行してください:")
    print("  pip install google-genai")
    sys.exit(1)


def get_api_key() -> str:
    """環境変数 GEMINI_API_KEY またはユーザー入力から API キーを取得する。"""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        print("環境変数 GEMINI_API_KEY を使用します。")
        return key

    key = input("APIキーを入力してください: ").strip()
    if not key:
        print("APIキー未入力。終了します。")
        sys.exit(0)
    return key


def test_model(client: genai.Client, model_name: str, prompt: str = "これはテストです。") -> str:
    """モデルに対して短文生成を試し、結果ステータスを返す。"""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = response.text.strip() if response.text else ""
        if text:
            print(f"  結果（先頭200文字）: {text[:200]}")
            return "OK"
        else:
            return "EMPTY"
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            return "QUOTA"
        elif "400" in err or "INVALID_ARGUMENT" in err:
            return "INVALID"
        else:
            return f"ERROR: {err[:80]}"


def print_summary(summary: dict[str, str]) -> None:
    """テーブル形式で診断サマリを表示する。"""
    if not summary:
        print("診断結果なし。")
        return

    max_name = max(len(name) for name in summary)
    max_name = max(max_name, 5)

    print(f"\n{'=' * (max_name + 20)}")
    print(f"{'Model':<{max_name}}  Status")
    print(f"{'-' * max_name}  {'-' * 15}")
    for name, status in summary.items():
        icon = {"OK": "✅", "EMPTY": "⚠️", "QUOTA": "⏳", "INVALID": "❌", "SKIPPED": "⏭️"}.get(status, "❌")
        print(f"{name:<{max_name}}  {icon} {status}")
    print(f"{'=' * (max_name + 20)}")

    # 統計
    total = len(summary)
    ok = sum(1 for s in summary.values() if s == "OK")
    print(f"\n合計: {total} モデル / 成功: {ok} / 失敗等: {total - ok}")


def main() -> None:
    print("=== Gemini API モデル診断 ===\n")

    api_key = get_api_key()
    client = genai.Client(api_key=api_key)

    # モデル一覧取得
    print("\n[1] モデル一覧を取得中...")
    try:
        models = list(client.models.list())
        print(f"  {len(models)} モデル取得")
    except Exception as e:
        print(f"  モデル一覧取得失敗: {e}")
        return

    # list() に含まれるモデル名を集める
    listed_names = set()
    summary: dict[str, str] = {}

    # 各モデル診断
    # SDK内部で API の supportedGenerationMethods が supported_actions にマッピングされる
    print("\n[2] 各モデルで短文生成テスト（list() 取得分）")
    for m in models:
        name = m.name
        listed_names.add(name)
        supported = m.supported_actions or []
        if supported and "generateContent" not in supported:
            summary[name] = "SKIPPED"
            print(f"\n--- {name} --- generateContent 非対応 → SKIPPED")
            continue

        print(f"\n--- {name} ---")
        status = test_model(client, name)
        summary[name] = status

        # レート制限回避
        time.sleep(2)

    # Preview モデルは list() に含まれないことがあるため明示的にテスト
    # この一覧は定期的に更新が必要
    preview_models = [
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-3-pro-image-preview",
        "gemini-3.1-flash-image-preview",
    ]
    extra = [name for name in preview_models if name not in listed_names]
    if extra:
        print(f"\n[3] Preview モデル追加テスト（list() 未収録分: {len(extra)} 件）")
        for name in extra:
            print(f"\n--- {name} ---")
            status = test_model(client, name)
            summary[name] = status
            time.sleep(2)

    print_summary(summary)
    print("\n診断完了。")


if __name__ == "__main__":
    main()
