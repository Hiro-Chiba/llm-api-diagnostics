# llm-api-diagnostics

LLM API の動作確認・診断ツール集。

## Gemini

利用可能な全モデルに対して短文生成テストを実行し、各モデルの応答状況をサマリ表示する。

- `list()` API で取得できる GA モデルを自動テスト
- Preview モデル（Gemini 3 系など `list()` に含まれないもの）も明示的にテスト

### セットアップ

```bash
cd llm-api-diagnostics
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 使い方

```bash
# 環境変数で API キーを渡す場合
export GEMINI_API_KEY="your-api-key"
python gemini/model_checker.py

# 対話入力で API キーを渡す場合
python gemini/model_checker.py
```

### 出力例

```
=== Gemini API モデル診断 ===

[1] モデル一覧を取得中...
  42 モデル取得

[2] 各モデルで短文生成テスト（list() 取得分）
...

[3] Preview モデル追加テスト（list() 未収録分: 4 件）
...

==============================================
Model                          Status
------------------------------  ---------------
models/gemini-2.5-flash         ✅ OK
gemini-3.1-pro-preview          ✅ OK
gemini-3-flash-preview          ✅ OK
models/text-embedding-004       ⏭️ SKIPPED
...
==============================================

合計: 46 モデル / 成功: 32 / 失敗等: 14
```
