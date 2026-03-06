"""レポート作成支援アプリ - メインUI"""

import os
import logging
import streamlit as st
from pathlib import Path

from config import TEX_MARKER_START, TEX_MARKER_END
from file_parser import find_files, read_excel_to_markdown, extract_pdf_pages, TexTemplate
from gemini_client import (
    create_client,
    list_available_models,
    extract_rules,
    create_chat_session,
    send_chat_message,
    generate_code,
    generate_final_review,
)
from report_builder import run_gnuplot, compile_latex, ensure_output_dir

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="実験レポート作成支援",
    page_icon="📝",
    layout="wide",
)

# ---------- セッション状態の初期化 ----------

DEFAULTS = {
    "phase": "init",            # init -> loaded -> rules_extracted -> chatting -> generating -> done
    "api_key": "",
    "gemini_model": "",         # 選択中のモデル
    "available_models": [],     # API から取得したモデル一覧
    "directory": "",
    "files": None,
    "excel_markdown": "",
    "pdf_images": [],
    "pdf_text": "",
    "tex_template": None,
    "rules": "",
    "chat_history": [],         # [{role, content}, ...]
    "gemini_chat": None,
    "generated_code": None,
    "gnuplot_result": None,
    "latex_result": None,
    "final_review": "",
    "log_messages": [],
}

for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


def add_log(message: str):
    """ログメッセージを追加"""
    st.session_state.log_messages.append(message)
    logger.info(message)


# ---------- サイドバー ----------

with st.sidebar:
    st.header("⚙️ 設定")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.api_key,
        help="Google AI StudioからAPIキーを取得してください",
    )
    if api_key:
        st.session_state.api_key = api_key

    # モデル取得ボタン
    if st.button("🔄 利用可能なモデルを取得", use_container_width=True, help="入力されたAPIキーで利用可能なGeminiモデルの一覧を取得します"):
        if not api_key:
            st.error("先にAPIキーを入力してください。")
        else:
            with st.spinner("モデル一覧を取得中..."):
                models = list_available_models(api_key)
            if models:
                st.session_state.available_models = models
                if st.session_state.gemini_model not in models:
                    st.session_state.gemini_model = models[0]
                st.success(f"{len(models)} 件のモデルを取得しました")
            else:
                st.error("モデルの取得に失敗しました。APIキーを確認してください。")

    if st.session_state.available_models:
        selected = st.selectbox(
            "🤖 使用するモデル",
            options=st.session_state.available_models,
            index=st.session_state.available_models.index(st.session_state.gemini_model)
                  if st.session_state.gemini_model in st.session_state.available_models else 0,
        )
        st.session_state.gemini_model = selected
    elif st.session_state.gemini_model:
        st.info(f"モデル: `{st.session_state.gemini_model}`")
    else:
        st.caption("⬆️ APIキーを入力後、モデルを取得してください")

    st.divider()

    directory = st.text_input(
        "📁 実験データのディレクトリパス",
        value=st.session_state.directory,
        placeholder="/home/user/experiment_data",
        help="Excel（実験データ）、PDF（指導書）、TeX（テンプレート）が含まれるディレクトリの絶対パスを指定してください"
    )
    # バックスラッシュをスラッシュに正規化（Windowsスタイルのパス対応）
    if directory:
        directory = directory.replace("\\", "/")
        st.session_state.directory = directory

    if st.button("📂 ファイルを読み込む", use_container_width=True, type="primary", help="指定されたディレクトリ内のファイルを読み込み、解析の準備をします"):
        if not directory or not os.path.isdir(directory):
            st.error("有効なディレクトリパスを指定してください。")
        elif not api_key:
            st.error("APIキーを入力してください。")
        else:
            with st.spinner("ファイルを読み込み中..."):
                files = find_files(directory)
                st.session_state.files = files
                add_log(f"ディレクトリ読み込み: {directory}")

                # Excel処理
                if files["excel"]:
                    md_parts = []
                    for fp in files["excel"]:
                        md = read_excel_to_markdown(fp)
                        md_parts.append(f"## {Path(fp).name}\n{md}")
                        add_log(f"Excel処理完了: {Path(fp).name}")
                    st.session_state.excel_markdown = "\n\n".join(md_parts)
                else:
                    add_log("⚠️ Excelファイルが見つかりません")

                # PDF処理
                if files["pdf"]:
                    all_images = []
                    all_text = []
                    for fp in files["pdf"]:
                        images, text = extract_pdf_pages(fp)
                        all_images.extend(images)
                        all_text.append(f"## {Path(fp).name}\n{text}")
                        add_log(f"PDF処理完了: {Path(fp).name} ({len(images)}ページ)")
                    st.session_state.pdf_images = all_images
                    st.session_state.pdf_text = "\n\n".join(all_text)
                else:
                    add_log("⚠️ PDFファイルが見つかりません")

                # TeX処理
                if files["tex"]:
                    tex = TexTemplate(files["tex"][0])
                    st.session_state.tex_template = tex
                    add_log(f"TeXテンプレート処理完了: {Path(files['tex'][0]).name}")
                else:
                    add_log("⚠️ TeXファイルが見つかりません")

                st.session_state.phase = "loaded"
                add_log("✅ ファイル読み込み完了")

        # ディレクトリ構造を表示
        st.success(f"✅ ディレクトリを読み込みました: `{directory}`")
        try:
            all_entries = sorted(os.listdir(directory))
            st.caption("📂 ディレクトリ内のファイル一覧")
            for entry in all_entries:
                full = os.path.join(directory, entry)
                icon = "📁" if os.path.isdir(full) else "📄"
                st.text(f"  {icon} {entry}")
        except Exception as e:
            st.warning(f"ディレクトリ一覧の取得に失敗しました: {e}")

    st.divider()

    # フェーズ表示
    phase = st.session_state.phase
    phase_labels = {
        "init": "🔲 初期化待ち",
        "loaded": "📄 ファイル読み込み済み",
        "rules_extracted": "📋 ルール抽出済み",
        "chatting": "💬 対話中",
        "generating": "⚙️ 生成中",
        "done": "✅ 完了",
    }
    st.subheader("進捗状況")
    phases_order = ["init", "loaded", "rules_extracted", "chatting", "generating", "done"]
    current_idx = phases_order.index(phase)
    st.progress((current_idx) / (len(phases_order) - 1))
    for i, p in enumerate(phases_order):
        icon = "✅" if i < current_idx else ("▶️" if i == current_idx else "⬜")
        st.text(f"{icon} {phase_labels[p]}")

    # ログ表示
    st.divider()
    with st.expander("📋 ログ", expanded=False):
        for msg in st.session_state.log_messages[-20:]:
            st.text(msg)


# ---------- メインエリア ----------

st.title("📝 実験レポート作成支援")
st.caption("AIとの対話を通じて、実験レポートの考察を深めましょう。")

# --- ファイル読み込み状況 ---
if st.session_state.files:
    with st.expander("📄 読み込んだファイル", expanded=False):
        files = st.session_state.files
        for ftype, label in [("excel", "📊 Excel"), ("pdf", "📕 PDF"), ("tex", "📄 TeX")]:
            if files[ftype]:
                for fp in files[ftype]:
                    st.text(f"  {label}: {Path(fp).name}")
            else:
                st.text(f"  {label}: なし")

        if st.session_state.excel_markdown:
            st.subheader("実験データプレビュー")
            st.markdown(st.session_state.excel_markdown[:3000])

# --- ルール抽出 ---
if st.session_state.phase == "loaded":
    st.info("ファイルの読み込みが完了しました。ルール抽出を開始してください。")

    if st.button("🔍 指導書からルールを抽出する", type="primary", help="PDFの指導書をAIに解析させ、グラフ作成のルールや考察ポイントを抽出します"):
        if not st.session_state.pdf_images and not st.session_state.pdf_text:
            st.warning("PDFが読み込まれていません。Excelデータのみで進めます。")

        with st.spinner("AIがルールを抽出中...（数十秒かかることがあります）"):
            client = create_client(st.session_state.api_key)
            rules = extract_rules(
                client,
                st.session_state.pdf_images,
                st.session_state.pdf_text,
                st.session_state.excel_markdown,
                model=st.session_state.gemini_model,
            )
            st.session_state.rules = rules
            st.session_state.phase = "rules_extracted"
            add_log("✅ ルール抽出完了")
            st.rerun()

# --- ルール表示 & チャット開始 ---
if st.session_state.phase in ("rules_extracted", "chatting", "generating", "done"):
    with st.expander("📋 抽出されたルール", expanded=st.session_state.phase == "rules_extracted"):
        st.markdown(st.session_state.rules)

if st.session_state.phase == "rules_extracted":
    st.info("ルールの抽出が完了しました。対話を開始して考察を深めましょう。")
    if st.button("💬 対話を開始する", type="primary", help="抽出されたルールをもとに、AI教員との対話を開始します"):
        st.session_state.phase = "chatting"

        # 初回メッセージをAIから送信
        client = create_client(st.session_state.api_key)
        tex_body = ""
        if st.session_state.tex_template:
            tex_body = st.session_state.tex_template.get_body_for_ai()

        chat = create_chat_session(
            client,
            st.session_state.rules,
            st.session_state.excel_markdown,
            tex_body,
            model=st.session_state.gemini_model,
        )
        st.session_state.gemini_chat = chat

        # AIの初回挨拶
        first_msg = send_chat_message(
            chat,
            "実験データを確認しました。レポート作成の支援を始めてください。まず最初に考えるべきことを問いかけてください。",
        )
        st.session_state.chat_history.append({"role": "assistant", "content": first_msg})
        add_log("💬 対話開始")
        st.rerun()

# --- チャットUI ---
if st.session_state.phase in ("chatting", "generating", "done"):
    st.subheader("💬 対話")

    # チャット履歴表示
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # チャット入力（chatting中のみ）
    if st.session_state.phase == "chatting":
        user_input = st.chat_input("考察を入力してください...")

        if user_input:
            # チャットセッションが切れている場合は再作成
            if st.session_state.gemini_chat is None:
                client = create_client(st.session_state.api_key)
                tex_body = ""
                if st.session_state.tex_template:
                    tex_body = st.session_state.tex_template.get_body_for_ai()
                chat = create_chat_session(
                    client,
                    st.session_state.rules,
                    st.session_state.excel_markdown,
                    tex_body,
                    st.session_state.chat_history,
                    model=st.session_state.gemini_model,
                )
                st.session_state.gemini_chat = chat

            # ユーザーメッセージ追加
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            # AI応答
            response = send_chat_message(st.session_state.gemini_chat, user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

        # レポート生成ボタン
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 レポートを生成する", type="primary", use_container_width=True, help="ここまでの対話内容をもとに、グラフ描画スクリプトとレポート本文を生成します"):
                st.session_state.phase = "generating"
                st.rerun()
        with col2:
            if st.button("🔄 対話をリセット", use_container_width=True, help="これまでの対話履歴をすべて消去して最初からやり直します（この操作は取り消せません）"):
                st.session_state.chat_history = []
                st.session_state.gemini_chat = None
                st.session_state.phase = "rules_extracted"
                add_log("対話をリセットしました")
                st.rerun()

# --- レポート生成 ---
if st.session_state.phase == "generating":
    st.subheader("⚙️ レポート生成中...")

    # 対話履歴をテキスト化
    chat_text = "\n".join(
        f"{'ユーザー' if m['role'] == 'user' else 'AI'}: {m['content']}"
        for m in st.session_state.chat_history
    )

    tex_body = ""
    if st.session_state.tex_template:
        tex_body = st.session_state.tex_template.get_body_for_ai()

    with st.spinner("AIがgnuplotスクリプトとLaTeX本文を生成中..."):
        client = create_client(st.session_state.api_key)
        code = generate_code(
            client,
            st.session_state.rules,
            st.session_state.excel_markdown,
            chat_text,
            tex_body,
            model=st.session_state.gemini_model,
        )
        st.session_state.generated_code = code

    if "error" in code:
        st.error(f"コード生成エラー: {code['error']}")
        if st.button("🔄 再生成"):
            st.rerun()
    else:
        output_dir = ensure_output_dir(st.session_state.directory)

        # gnuplot実行
        if code.get("gnuplot_script"):
            with st.spinner("gnuplotでグラフを生成中..."):
                gp_result = run_gnuplot(code["gnuplot_script"], output_dir)
                st.session_state.gnuplot_result = gp_result

                if gp_result["success"]:
                    add_log(f"✅ グラフ生成成功: {gp_result['output_path']}")
                else:
                    add_log(f"⚠️ グラフ生成エラー: {gp_result['error']}")
                    # エラー時: AIに再修正を要求
                    st.warning(f"gnuplotエラー:\n```\n{gp_result['error']}\n```")

        # LaTeXコンパイル
        if code.get("latex_body"):
            with st.spinner("LaTeXをコンパイル中..."):
                if st.session_state.tex_template:
                    full_tex = st.session_state.tex_template.reconstruct(code["latex_body"])
                else:
                    full_tex = code["latex_body"]

                tex_result = compile_latex(full_tex, output_dir)
                st.session_state.latex_result = tex_result

                if tex_result["success"]:
                    add_log(f"✅ PDF生成成功: {tex_result['pdf_path']}")
                else:
                    add_log(f"⚠️ LaTeXコンパイルエラー: {tex_result['error']}")
                    st.warning(f"LaTeXエラー:\n```\n{tex_result['error']}\n```")

        # 最終レビュー
        with st.spinner("AIが最終レビュー中..."):
            review = generate_final_review(
                client,
                st.session_state.rules,
                chat_text,
                code.get("latex_body", ""),
                model=st.session_state.gemini_model,
            )
            st.session_state.final_review = review

        st.session_state.phase = "done"
        add_log("✅ レポート生成完了")
        st.rerun()

# --- 完了・結果表示 ---
if st.session_state.phase == "done":
    st.subheader("✅ レポート生成完了")

    # グラフ表示
    gp = st.session_state.gnuplot_result
    if gp and gp.get("success") and os.path.exists(gp["output_path"]):
        st.image(gp["output_path"], caption="生成されたグラフ")
    elif gp and not gp.get("success"):
        st.warning(f"グラフ生成に失敗しました: {gp.get('error', '不明なエラー')}")

    # PDF表示・ダウンロード
    tex = st.session_state.latex_result
    if tex and tex.get("success") and os.path.exists(tex["pdf_path"]):
        with open(tex["pdf_path"], "rb") as f:
            pdf_bytes = f.read()

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 PDFをダウンロード",
                data=pdf_bytes,
                file_name="report.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        with col2:
            st.info(f"PDF: {tex['pdf_path']}")
    elif tex and not tex.get("success"):
        st.warning(f"PDF生成に失敗しました: {tex.get('error', '不明なエラー')}")

    # 生成コード表示
    code = st.session_state.generated_code
    if code and "error" not in code:
        with st.expander("🔧 生成されたコード", expanded=False):
            if code.get("gnuplot_script"):
                st.subheader("gnuplotスクリプト")
                st.code(code["gnuplot_script"], language="gnuplot")
            if code.get("latex_body"):
                st.subheader("LaTeX本文")
                st.code(code["latex_body"], language="latex")

    # 最終レビュー
    if st.session_state.final_review:
        st.subheader("📝 AIからの最終レビュー")
        st.markdown(st.session_state.final_review)

    # 再スタート
    st.divider()
    if st.button("🔄 最初からやり直す", use_container_width=True, help="現在のすべての状態（ファイル読み込み、対話履歴、生成されたレポート）をリセットして初期状態に戻します（この操作は取り消せません）"):
        for key, default in DEFAULTS.items():
            st.session_state[key] = default
        st.rerun()
