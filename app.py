"""AI ライティングツール（個人用）  —  streamlit run app.py"""

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from gemini_client import GeminiWriter
from tools import TOOLS, TOOLS_BY_ID, Field, Tool

load_dotenv()

HISTORY_FILE = Path(__file__).parent / "history.json"
HISTORY_LIMIT = 200
# API からモデル一覧を取れなかったときの候補
FALLBACK_MODELS = ["gemini-3.8-flash"]
DEFAULT_MODEL = "gemini-3.8-flash"
CUSTOM_MODEL = "その他（手入力）"
HISTORY_VIEW = "history"
QUICK_REFINES = ["もっと短く", "もっと丁寧に", "もっとカジュアルに", "別のパターンも", "具体例を追加"]

st.set_page_config(page_title="AI ライティングツール", page_icon="✍️", layout="wide")


# ---------- 履歴（ローカル JSON に保存） ----------

def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_history(history: list[dict]) -> None:
    HISTORY_FILE.write_text(
        json.dumps(history[:HISTORY_LIMIT], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_history(tool: Tool, request: str, output: str) -> None:
    st.session_state.history.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tool": tool.name,
        "icon": tool.icon,
        "request": request,
        "output": output,
    })
    save_history(st.session_state.history)


# ---------- 初期化 ----------

def get_secret(name: str) -> str:
    if os.getenv(name):
        return os.getenv(name, "")
    try:
        return st.secrets.get(name, "")
    except Exception:  # secrets.toml が無い場合
        return ""


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_models(api_key: str) -> list[str]:
    try:
        return GeminiWriter.list_models(api_key)
    except Exception:
        return []


if "history" not in st.session_state:
    st.session_state.history = load_history()
if "threads" not in st.session_state:
    # ツールごとの会話（初回生成 + 追加指示による修正）
    st.session_state.threads = {}


# ---------- サイドバー ----------

with st.sidebar:
    st.title("✍️ AI ライティング")

    labels = {t.id: f"{t.icon} {t.name}" for t in TOOLS}
    labels[HISTORY_VIEW] = "📚 履歴"
    view = st.radio("ツール", list(labels), format_func=labels.get, label_visibility="collapsed")

    st.divider()
    with st.expander("⚙️ 設定", expanded=not get_secret("GEMINI_API_KEY")):
        env_key = get_secret("GEMINI_API_KEY")
        api_key = st.text_input(
            "Gemini API キー",
            type="password",
            placeholder="設定済み（.env）" if env_key else "AIza...",
            help="https://aistudio.google.com/apikey で取得できます。.env に書いておくと入力不要です。",
        ) or env_key

        models = (fetch_models(api_key) if api_key else []) or FALLBACK_MODELS
        options = models + [CUSTOM_MODEL]
        default_model = get_secret("GEMINI_MODEL") or DEFAULT_MODEL
        if default_model not in models:
            # 既定モデルが無ければ flash 系の最新を選ぶ
            default_model = next((m for m in models if "flash" in m and "lite" not in m), models[0])
        model_choice = st.selectbox("モデル", options, index=options.index(default_model))
        model = st.text_input("モデル名") if model_choice == CUSTOM_MODEL else model_choice
        temperature = st.slider("創造性（temperature）", 0.0, 2.0, 0.7, 0.1,
                                help="低いほど正確・安定、高いほど自由で多様な文章になります。")


def get_writer() -> GeminiWriter | None:
    if not api_key:
        st.warning("サイドバーの「設定」で Gemini API キーを入力してください。")
        return None
    if not model:
        st.warning("モデル名を入力してください。")
        return None
    return GeminiWriter(api_key, model, temperature)


def run_stream(writer: GeminiWriter, system: str, messages: list[dict]) -> str | None:
    try:
        with st.chat_message("assistant"):
            with st.spinner("生成中…（混雑時は自動で再試行します）"):
                return st.write_stream(writer.stream(system, messages))
    except Exception as e:
        code = getattr(e, "code", None)
        if code in (429, 503):
            st.error(
                f"モデル「{writer.model}」が混み合っていて、再試行しても応答がありませんでした。"
                "少し時間をおくか、サイドバーの「設定」で別のモデルを選んでからもう一度お試しください。"
            )
            with st.expander("エラーの詳細"):
                st.code(str(e), language=None)
        else:
            st.error(f"生成に失敗しました: {e}")
        return None


# ---------- 入力フォーム ----------

def render_field(tool: Tool, f: Field):
    key = f"{tool.id}__{f.key}"
    if f.kind == "textarea":
        return st.text_area(f.label, key=key, height=140, placeholder=f.placeholder, help=f.help)
    if f.kind == "select":
        idx = f.options.index(f.default) if f.default in f.options else 0
        return st.selectbox(f.label, f.options, index=idx, key=key, help=f.help)
    if f.kind == "slider":
        return st.slider(f.label, f.min_value, f.max_value, f.default, f.step, key=key, help=f.help)
    if f.kind == "number":
        return st.number_input(f.label, f.min_value, f.max_value, f.default, key=key, help=f.help)
    if f.kind == "checkbox":
        return st.checkbox(f.label, value=bool(f.default), key=key, help=f.help)
    return st.text_input(f.label, key=key, placeholder=f.placeholder, help=f.help)


def render_output_actions(tool: Tool, text: str, idx: int) -> None:
    c1, c2 = st.columns([1, 5])
    c1.download_button("⬇️ .md", text, file_name=f"{tool.id}_{datetime.now():%Y%m%d_%H%M}.md",
                       key=f"dl_{tool.id}_{idx}")
    c2.caption(f"{len(text):,} 文字")
    with st.expander("📋 コピー用（右上のアイコンでコピー）"):
        st.code(text, language=None, wrap_lines=True)


def tool_view(tool: Tool) -> None:
    st.header(f"{tool.icon} {tool.name}")
    st.caption(tool.description)

    with st.form(f"form_{tool.id}"):
        # 文章入力は左、オプション類は右に並べて、生成ボタンまでスクロールせずに届くようにする
        left, right = st.columns([3, 2])
        upload = None
        values = {}
        with left:
            for f in tool.fields:
                if f.kind in ("text", "textarea"):
                    values[f.key] = render_field(tool, f)
        with right:
            for f in tool.fields:
                if f.kind not in ("text", "textarea"):
                    values[f.key] = render_field(tool, f)
            if tool.allow_file_upload:
                upload = st.file_uploader("テキストファイルから読み込む（任意）", type=["txt", "md", "csv"])
        submitted = st.form_submit_button("✨ 生成する", type="primary", use_container_width=True)

    if submitted:
        if upload is not None:
            values[tool.allow_file_upload] = upload.getvalue().decode("utf-8", errors="replace")
        missing = [f.label for f in tool.fields if f.required and not str(values[f.key]).strip()]
        if missing:
            st.error("必須項目を入力してください: " + "、".join(missing))
        elif writer := get_writer():
            prompt = tool.build_prompt(values)
            messages = [{"role": "user", "text": prompt}]
            st.session_state.threads.pop(tool.id, None)
            output = run_stream(writer, tool.system, messages)
            if output:
                messages.append({"role": "model", "text": output})
                st.session_state.threads[tool.id] = messages
                add_history(tool, prompt, output)
                st.rerun()

    thread = st.session_state.threads.get(tool.id)
    if not thread:
        return

    st.divider()
    st.subheader("結果")
    # thread[0] は初回プロンプトなので表示しない
    for i, msg in enumerate(thread[1:], start=1):
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["text"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["text"])
                render_output_actions(tool, msg["text"], i)

    st.caption("結果に追加の指示を出して修正できます。")
    cols = st.columns(len(QUICK_REFINES) + 1)
    quick = next((q for q, c in zip(QUICK_REFINES, cols) if c.button(q, key=f"q_{tool.id}_{q}")), None)
    if cols[-1].button("🗑️ クリア", key=f"clear_{tool.id}"):
        st.session_state.threads.pop(tool.id)
        st.rerun()

    instruction = st.chat_input("修正の指示（例: 結論を先に書いて）", key=f"chat_{tool.id}") or quick
    if instruction and (writer := get_writer()):
        with st.chat_message("user"):
            st.markdown(instruction)
        new_thread = thread + [{"role": "user", "text": instruction}]
        output = run_stream(writer, tool.system, new_thread)
        if output:
            new_thread.append({"role": "model", "text": output})
            st.session_state.threads[tool.id] = new_thread
            add_history(tool, f"（追加指示）{instruction}", output)
            st.rerun()


# ---------- 履歴ビュー ----------

def history_view() -> None:
    st.header("📚 履歴")
    history = st.session_state.history
    if not history:
        st.info("まだ履歴はありません。")
        return

    c1, c2, c3 = st.columns([3, 1, 1])
    query = c1.text_input("検索", placeholder="キーワードで絞り込み", label_visibility="collapsed")
    all_md = "\n\n---\n\n".join(f"## {h['icon']} {h['tool']}（{h['time']}）\n\n{h['output']}" for h in history)
    c2.download_button("⬇️ 全件 .md", all_md, file_name="history.md", use_container_width=True)
    if c3.button("🗑️ 全削除", use_container_width=True):
        st.session_state.history = []
        save_history([])
        st.rerun()

    items = [h for h in history if not query or query in h["output"] or query in h["request"]]
    st.caption(f"{len(items)} 件")
    for i, h in enumerate(items):
        preview = h["output"].strip().splitlines()[0][:60] if h["output"].strip() else ""
        with st.expander(f"{h['icon']} {h['tool']} ・ {h['time']} ・ {preview}"):
            with st.popover("依頼内容を見る"):
                st.text(h["request"])
            st.markdown(h["output"])
            st.download_button("⬇️ .md", h["output"], file_name=f"history_{i}.md", key=f"hdl_{i}")


if view == HISTORY_VIEW:
    history_view()
else:
    tool_view(TOOLS_BY_ID[view])
