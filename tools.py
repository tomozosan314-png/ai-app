"""ライティングツールの定義。

ツールを追加したいときは Tool を1つ作って TOOLS に足すだけで、
UI（入力フォーム）は fields から自動生成されます。
"""

from dataclasses import dataclass, field
from typing import Any, Callable

BASE_SYSTEM = (
    "あなたは日本語に精通したプロのライター兼編集者です。"
    "指示された形式だけを出力し、前置きや「承知しました」などの挨拶は書かないでください。"
    "見出しや箇条書きが必要な場合は Markdown を使ってください。"
)


@dataclass
class Field:
    key: str
    label: str
    kind: str = "text"  # text | textarea | select | slider | number
    options: list[Any] = field(default_factory=list)
    default: Any = None
    help: str | None = None
    required: bool = False
    min_value: int | None = None
    max_value: int | None = None
    step: int | None = None
    placeholder: str | None = None


@dataclass
class Tool:
    id: str
    name: str
    icon: str
    description: str
    system: str
    fields: list[Field]
    build_prompt: Callable[[dict], str]
    allow_file_upload: str | None = None  # アップロード内容を流し込むフィールドの key


def _opt(label: str, value: str) -> str:
    """値が空なら行ごと省く。"""
    return f"- {label}: {value}\n" if value else ""


# ---------- 各ツールのプロンプト ----------

def _blog(v: dict) -> str:
    return (
        "以下の条件でブログ記事を執筆してください。\n\n"
        f"- テーマ: {v['topic']}\n"
        + _opt("含めたいキーワード", v["keywords"])
        + _opt("想定読者", v["audience"])
        + f"- トーン: {v['tone']}\n"
        f"- 目安の文字数: 約{v['length']}文字\n"
        + _opt("補足・盛り込みたい内容", v["notes"])
        + "\n構成: 魅力的なタイトル（# 見出し）→ 導入 → 本文（## 見出しで複数セクション）→ まとめ。"
        "読者が具体的に行動できる情報を入れてください。"
        + ("\n最後に SEO 用のメタディスクリプション（120文字程度）を付けてください。" if v["seo"] else "")
    )


def _outline(v: dict) -> str:
    return (
        "以下のテーマで記事の構成案を作成してください。\n\n"
        f"- テーマ: {v['topic']}\n"
        + _opt("想定読者", v["audience"])
        + _opt("記事の目的", v["goal"])
        + f"\nタイトル案を{v['count']}つ、続いて見出し構成（H2/H3）と各見出しで書くべき要点を箇条書きで出してください。"
    )


def _email_reply(v: dict) -> str:
    return (
        "以下の受信メールへの返信文を作成してください。\n\n"
        f"## 受信メール\n{v['received']}\n\n"
        f"## 返信で伝えたいこと\n{v['points'] or '（特になし。内容に合わせて適切に返信）'}\n\n"
        f"- 相手との関係: {v['relation']}\n"
        f"- トーン: {v['tone']}\n"
        + _opt("署名（差出人名）", v["signature"])
        + f"\n返信文を{v['variants']}パターン作成し、それぞれ「### 案1」のように見出しを付けてください。"
        "件名が必要な場合は「件名: Re: ...」を先頭に付けてください。"
    )


def _email_new(v: dict) -> str:
    return (
        "以下の内容でメールを新規作成してください。\n\n"
        f"- 宛先: {v['to']}\n"
        f"- 目的: {v['purpose']}\n"
        f"- 伝えたい要点:\n{v['points']}\n"
        f"- トーン: {v['tone']}\n"
        + _opt("署名（差出人名）", v["signature"])
        + "\n先頭に「件名: ...」を付け、続けて本文を書いてください。"
    )


def _summarize(v: dict) -> str:
    style = {
        "箇条書き": "重要なポイントを箇条書きで",
        "3行要約": "ちょうど3行で",
        "段落": "読みやすい段落の文章で",
        "TL;DR + 詳細": "冒頭に1文の TL;DR、その後に箇条書きの詳細を",
    }[v["style"]]
    return (
        f"以下の文章を{style}要約してください。長さの目安は「{v['length']}」です。\n"
        + ("最後に「## アクションアイテム」として、やるべきことを抜き出してください。\n" if v["actions"] else "")
        + f"\n---\n{v['text']}"
    )


def _rewrite(v: dict) -> str:
    return (
        f"以下の文章を「{v['style']}」なスタイルに書き換えてください。"
        "元の意味や情報は保ったまま、書き換えた文章のみを出力してください。\n"
        + _opt("追加の指示", v["extra"])
        + f"\n---\n{v['text']}"
    )


def _proofread(v: dict) -> str:
    return (
        "以下の文章を校正・添削してください。\n"
        f"チェックの強さ: {v['level']}\n\n"
        "出力形式:\n"
        "## 修正後の文章\n（修正済みの全文）\n\n"
        "## 修正点\n| 修正前 | 修正後 | 理由 |\n の表形式で、誤字脱字・文法・表記ゆれ・分かりにくい表現を挙げてください。\n\n"
        f"---\n{v['text']}"
    )


def _translate(v: dict) -> str:
    return (
        f"以下の文章を{v['target']}に翻訳してください。スタイル: {v['style']}。\n"
        + ("翻訳の後に「## 補足」として、訳し方に迷った表現や文化的な注意点を簡潔に添えてください。\n" if v["notes"] else "翻訳文のみを出力してください。\n")
        + f"\n---\n{v['text']}"
    )


def _sns(v: dict) -> str:
    limits = {
        "X (Twitter)": "全角140文字以内",
        "Instagram": "キャプションとして読みやすく、改行と絵文字を適度に使う",
        "Threads": "500文字以内、会話的なトーン",
        "LinkedIn": "ビジネス向けで、冒頭2行で興味を引く",
        "Facebook": "親しみやすく、適度な長さ",
    }
    return (
        f"{v['platform']}向けの投稿文を{v['count']}パターン作成してください。\n"
        f"- 条件: {limits[v['platform']]}\n"
        f"- 伝えたい内容: {v['content']}\n"
        f"- トーン: {v['tone']}\n"
        + ("- ハッシュタグを3〜5個付ける\n" if v["hashtags"] else "- ハッシュタグは付けない\n")
        + "\nそれぞれ「### 案1」のように見出しを付けてください。"
    )


def _catchcopy(v: dict) -> str:
    return (
        f"以下の内容について、「{v['usage']}」として使える案を{v['count']}個出してください。\n\n"
        f"- 内容: {v['content']}\n"
        + _opt("ターゲット", v["target"])
        + _opt("方向性・NG", v["direction"])
        + "\n番号付きリストで出し、それぞれに一言で狙いを添えてください。最後におすすめを1つ選んで理由を書いてください。"
    )


def _expand(v: dict) -> str:
    mode = {
        "続きを書く": "以下の文章の続きを、文体と流れを合わせて書いてください。",
        "箇条書きを文章化": "以下の箇条書き・メモを、自然につながる文章に仕上げてください。",
        "もっと詳しく": "以下の文章を、具体例や説明を加えてより詳しく膨らませてください。",
        "短くする": "以下の文章を、要点を残したまま短く簡潔にしてください。",
    }[v["mode"]]
    return mode + f"\n目安の文字数: 約{v['length']}文字\n\n---\n{v['text']}"


def _free(v: dict) -> str:
    return v["prompt"]


# ---------- ツール一覧 ----------

TONES = ["丁寧", "カジュアル", "フレンドリー", "専門的", "熱量高め", "落ち着いた"]

TOOLS: list[Tool] = [
    Tool(
        id="blog", name="ブログ記事作成", icon="📝",
        description="テーマとキーワードから、構成付きのブログ記事を丸ごと書きます。",
        system=BASE_SYSTEM + "SEO と読みやすさを意識したブログ記事を書くのが得意です。",
        fields=[
            Field("topic", "テーマ", "text", required=True, placeholder="例: 在宅ワークで集中力を保つコツ"),
            Field("keywords", "含めたいキーワード（任意）", "text", placeholder="例: ポモドーロ, デスク環境"),
            Field("audience", "想定読者（任意）", "text", placeholder="例: リモートワーク初心者の会社員"),
            Field("tone", "トーン", "select", options=TONES, default="フレンドリー"),
            Field("length", "文字数の目安", "slider", min_value=500, max_value=6000, step=500, default=2000),
            Field("notes", "補足・盛り込みたい内容（任意）", "textarea"),
            Field("seo", "メタディスクリプションも作る", "checkbox", default=True),
        ],
        build_prompt=_blog,
    ),
    Tool(
        id="outline", name="記事の構成案", icon="🗂️",
        description="記事を書く前の、タイトル案と見出し構成を作ります。",
        system=BASE_SYSTEM + "編集者として、読者に刺さる記事構成を設計します。",
        fields=[
            Field("topic", "テーマ", "text", required=True),
            Field("audience", "想定読者（任意）", "text"),
            Field("goal", "記事の目的（任意）", "text", placeholder="例: 商品ページへの誘導、ノウハウ共有"),
            Field("count", "タイトル案の数", "number", min_value=1, max_value=10, default=5),
        ],
        build_prompt=_outline,
    ),
    Tool(
        id="email_reply", name="メール返信", icon="↩️",
        description="受け取ったメールを貼り付けると、返信文の案を作ります。",
        system=BASE_SYSTEM + "日本のビジネスメールのマナーに精通しています。",
        fields=[
            Field("received", "受信したメール", "textarea", required=True),
            Field("points", "返信で伝えたいこと（任意）", "textarea", placeholder="例: 日程はOK。資料は金曜までに送る"),
            Field("relation", "相手との関係", "select", options=["社外（取引先）", "社外（初対面）", "上司", "同僚", "部下", "友人・知人"]),
            Field("tone", "トーン", "select", options=["丁寧", "とても丁寧", "簡潔", "カジュアル"]),
            Field("signature", "署名（任意）", "text"),
            Field("variants", "パターン数", "number", min_value=1, max_value=3, default=2),
        ],
        build_prompt=_email_reply,
    ),
    Tool(
        id="email_new", name="メール新規作成", icon="✉️",
        description="要点を箇条書きで渡すと、整ったメールにします。",
        system=BASE_SYSTEM + "日本のビジネスメールのマナーに精通しています。",
        fields=[
            Field("to", "宛先（どんな相手か）", "text", required=True, placeholder="例: 取引先の担当者 山田様"),
            Field("purpose", "目的", "text", required=True, placeholder="例: 打ち合わせ日程の調整"),
            Field("points", "伝えたい要点", "textarea", required=True),
            Field("tone", "トーン", "select", options=["丁寧", "とても丁寧", "簡潔", "カジュアル"]),
            Field("signature", "署名（任意）", "text"),
        ],
        build_prompt=_email_new,
    ),
    Tool(
        id="summarize", name="要約", icon="📄",
        description="長い文章・議事録・記事を要約します。テキストファイルのアップロードも可。",
        system=BASE_SYSTEM + "情報を正確に、抜け漏れなく整理するのが得意です。原文にない情報は追加しないでください。",
        fields=[
            Field("text", "要約したい文章", "textarea", required=True),
            Field("style", "形式", "select", options=["箇条書き", "3行要約", "段落", "TL;DR + 詳細"]),
            Field("length", "長さ", "select", options=["短め", "普通", "詳しめ"], default="普通"),
            Field("actions", "アクションアイテムも抜き出す", "checkbox", default=False),
        ],
        build_prompt=_summarize,
        allow_file_upload="text",
    ),
    Tool(
        id="rewrite", name="リライト・言い換え", icon="🔁",
        description="文章のトーンや読みやすさを変えて書き直します。",
        system=BASE_SYSTEM,
        fields=[
            Field("text", "元の文章", "textarea", required=True),
            Field("style", "書き換え後のスタイル", "select",
                  options=["やさしく分かりやすい", "フォーマル", "カジュアル", "簡潔", "説得力のある", "小学生にも分かる", "ビジネス文書"]),
            Field("extra", "追加の指示（任意）", "text", placeholder="例: です・ます調に統一"),
        ],
        build_prompt=_rewrite,
    ),
    Tool(
        id="proofread", name="校正・添削", icon="✅",
        description="誤字脱字・文法・表記ゆれをチェックし、修正点を一覧にします。",
        system=BASE_SYSTEM + "校閲者として、細かな誤りも見逃しません。",
        fields=[
            Field("text", "チェックしたい文章", "textarea", required=True),
            Field("level", "チェックの強さ", "select", options=["誤字脱字のみ", "標準", "表現まで踏み込んで改善"], default="標準"),
        ],
        build_prompt=_proofread,
    ),
    Tool(
        id="translate", name="翻訳", icon="🌐",
        description="自然な表現で翻訳します。",
        system=BASE_SYSTEM + "プロの翻訳者として、直訳ではなく自然な訳文を作ります。",
        fields=[
            Field("text", "翻訳したい文章", "textarea", required=True),
            Field("target", "翻訳先の言語", "select", options=["英語", "日本語", "中国語（簡体字）", "韓国語", "スペイン語", "フランス語", "ドイツ語"]),
            Field("style", "スタイル", "select", options=["自然", "ビジネス", "カジュアル", "直訳寄り"]),
            Field("notes", "補足（訳注）を付ける", "checkbox", default=False),
        ],
        build_prompt=_translate,
        allow_file_upload="text",
    ),
    Tool(
        id="sns", name="SNS投稿", icon="📣",
        description="各SNSに合わせた投稿文を複数パターン作ります。",
        system=BASE_SYSTEM + "SNS マーケティングに精通し、反応が取れる投稿を書きます。",
        fields=[
            Field("content", "伝えたい内容", "textarea", required=True),
            Field("platform", "プラットフォーム", "select", options=["X (Twitter)", "Instagram", "Threads", "LinkedIn", "Facebook"]),
            Field("tone", "トーン", "select", options=TONES, default="カジュアル"),
            Field("count", "パターン数", "number", min_value=1, max_value=5, default=3),
            Field("hashtags", "ハッシュタグを付ける", "checkbox", default=True),
        ],
        build_prompt=_sns,
    ),
    Tool(
        id="catchcopy", name="タイトル・キャッチコピー", icon="💡",
        description="記事タイトル、キャッチコピー、商品名などのアイデアを量産します。",
        system=BASE_SYSTEM + "コピーライターとして、印象に残る言葉を作ります。",
        fields=[
            Field("content", "対象の内容", "textarea", required=True),
            Field("usage", "用途", "select", options=["ブログ記事タイトル", "キャッチコピー", "YouTube動画タイトル", "商品・サービス名", "メール件名", "プレゼン資料のタイトル"]),
            Field("target", "ターゲット（任意）", "text"),
            Field("direction", "方向性・NGワード（任意）", "text"),
            Field("count", "案の数", "number", min_value=3, max_value=20, default=10),
        ],
        build_prompt=_catchcopy,
    ),
    Tool(
        id="expand", name="文章の続き・肉付け", icon="✍️",
        description="続きを書く、メモを文章化する、膨らませる、短くする。",
        system=BASE_SYSTEM,
        fields=[
            Field("text", "元の文章・メモ", "textarea", required=True),
            Field("mode", "やりたいこと", "select", options=["続きを書く", "箇条書きを文章化", "もっと詳しく", "短くする"]),
            Field("length", "文字数の目安", "slider", min_value=100, max_value=3000, step=100, default=600),
        ],
        build_prompt=_expand,
    ),
    Tool(
        id="free", name="フリー入力", icon="💬",
        description="上記に当てはまらない文章作成を自由に依頼できます。",
        system=BASE_SYSTEM,
        fields=[
            Field("prompt", "依頼内容", "textarea", required=True, placeholder="例: 退職のあいさつ文を、お世話になった部署向けに書いて"),
        ],
        build_prompt=_free,
    ),
]

TOOLS_BY_ID = {t.id: t for t in TOOLS}
