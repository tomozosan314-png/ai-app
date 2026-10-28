# AI ライティングツール（個人用）

Python + Streamlit + Gemini API で動く、ライティング系 AI ツールのまとめアプリです。

## 機能

| ツール | 内容 |
|---|---|
| 📝 ブログ記事作成 | テーマ・キーワード・読者・トーン・文字数から記事を丸ごと執筆（メタディスクリプション付き） |
| 🗂️ 記事の構成案 | タイトル案と H2/H3 の見出し構成 |
| ↩️ メール返信 | 受信メールを貼るだけで返信文を複数パターン |
| ✉️ メール新規作成 | 箇条書きの要点から整ったメールを作成 |
| 📄 要約 | 箇条書き / 3行 / 段落 / TL;DR、アクションアイテム抽出、ファイル読込対応 |
| 🔁 リライト・言い換え | フォーマル・やさしく・簡潔などに書き換え |
| ✅ 校正・添削 | 修正後の全文と「修正前／修正後／理由」の表 |
| 🌐 翻訳 | 自然な翻訳、訳注オプション |
| 📣 SNS投稿 | X / Instagram / Threads / LinkedIn / Facebook 向け |
| 💡 タイトル・キャッチコピー | タイトル・コピー・商品名・件名などを量産 |
| ✍️ 文章の続き・肉付け | 続きを書く / メモを文章化 / 膨らませる / 短くする |
| 💬 フリー入力 | 自由な依頼 |
| 📚 履歴 | 生成結果を `history.json` に保存。検索・Markdown 一括ダウンロード |

共通機能:
- ストリーミング表示
- 生成後に「もっと短く」などのワンクリック修正や、チャットで追加指示して書き直し
- 結果のコピー・`.md` ダウンロード・文字数表示
- サイドバーでモデルと創造性（temperature）を切り替え

## セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # GEMINI_API_KEY を記入
streamlit run app.py
```

API キーは https://aistudio.google.com/apikey で取得できます。
`.env` を作らずに、アプリのサイドバーで入力しても使えます。

## ツールの追加方法

`tools.py` に `build_prompt` 関数を書き、`TOOLS` リストに `Tool(...)` を追加するだけです。
入力フォームは `fields` から自動で作られます（`text` / `textarea` / `select` / `slider` / `number` / `checkbox`）。
