# llm-api-diagnostics

LLM API の動作確認・診断ツール集。

## Gemini

利用可能な全モデルに対して短文生成テストを実行し、各モデルの応答状況をサマリ表示する。

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

[2] 各モデルで短文生成テスト
...

=======================================
モデル                   ステータス
---------------------    ---------------
models/gemini-2.5-flash  ✅ OK
models/gemini-2.5-pro    ✅ OK
...
=======================================

合計: 42 モデル / 成功: 30 / 失敗等: 12
```
