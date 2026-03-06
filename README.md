*このアプリケーションは作成途中です。*


# 📝 実験レポート作成支援アプリ

AIとの対話を通じて、実験レポートの考察を深める学習支援Webアプリケーションです。  
AIが答えを教えるのではなく、**教員役として学生に問いかけ、自分で考えさせる**ファシリテーション型の設計になっています。

---

## 🎯 コンセプト

> 「AIがレポートを代筆するのではなく、AIが実験データや図表を提示しながらユーザーに問いかけることで、ユーザー自身に考察させる」

- ✅ AIは**絶対に答えを先に言いません**
- ✅ データを示しながら「何が読み取れますか？」と問いかけます
- ✅ 間違いにはヒントで対応します
- ✅ 対話を通じて深まった考察を、そのままレポートに反映します

---

## ✨ 主な機能

| フェーズ | 機能 |
|---|---|
| **1. ファイル読み込み** | Excel（実験データ）・PDF（指導書）・TeX（テンプレート）を自動検出して読み込む |
| **2. ルール抽出** | Gemini APIが指導書を解析し、グラフの軸設定・考察ポイント・レポートフォーマットを抽出 |
| **3. ファシリテーション** | 高専教員役のAIがチャット形式でユーザーに問いかけ、考察を引き出す |
| **4. コード生成** | 対話結果をもとに gnuplot スクリプト と LaTeX 本文コードを自動生成 |
| **5. レポート完成** | gnuplot でグラフを描画し、pdflatex でPDFをコンパイル。ダウンロードボタンで取得 |

---

## 🖼️ アプリの画面構成

```
┌─────────────────┬─────────────────────────────────────────────┐
│    サイドバー     │              メインエリア                      │
│                 │                                             │
│ [API Key入力]   │  📄 読み込んだファイル (折りたたみ)               │
│ [ディレクトリ入力] │  📋 抽出されたルール (折りたたみ)                │
│ [読み込みボタン]  │                                             │
│                 │  💬 チャット欄                                │
│ ─── 進捗状況 ─── │  ┌────────────────────────────────────┐    │
│ ✅ 初期化待ち    │  │ AI: このデータから何が読み取れますか？  │    │
│ ✅ ファイル読込   │  │ You: 周波数が高くなると...             │    │
│ ▶️ ルール抽出    │  │ AI: 良い観察です。では次に...          │    │
│ ⬜ 対話中       │  └────────────────────────────────────┘    │
│ ⬜ 生成中       │  [メッセージを入力...]                         │
│ ⬜ 完了         │                                             │
│                 │  [レポートを生成する]  [対話をリセット]           │
│ ─── ログ ───    │                                             │
└─────────────────┴─────────────────────────────────────────────┘
```

---

## 🛠️ 技術スタック

| 技術 | 用途 | バージョン |
|---|---|---|
| [Streamlit](https://streamlit.io/) | WebUI フレームワーク | ≥ 1.30.0 |
| [Google Gemini API](https://ai.google.dev/) | AI（ルール抽出・ファシリテーション・コード生成） | gemini-2.5-flash-preview |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | PDF テキスト抽出・画像化 | ≥ 1.24.0 |
| [pandas](https://pandas.pydata.org/) | Excel データ読み込み・Markdown 変換 | ≥ 2.0.0 |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel ファイル読み書き | ≥ 3.1.0 |
| [Pillow](https://pillow.readthedocs.io/) | 画像処理 | ≥ 10.0.0 |
| [gnuplot](http://www.gnuplot.info/) | グラフ描画 | ≥ 6.0 |
| [TeX Live / pdflatex](https://www.tug.org/texlive/) | PDF コンパイル | TeX Live 2023 |
| Python | バックエンド全般 | 3.10 以上 |

---

## 📋 動作環境

- **OS**: Linux / WSL (Windows Subsystem for Linux) Ubuntu 環境を想定
- **Python**: 3.10 以上
- **必須外部コマンド**:
  - `gnuplot` （グラフ描画）
  - `pdflatex` （PDF コンパイル、TeX Live に含まれる）

---

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/<your-username>/report-helper.git
cd report-helper
```

### 2. Python パッケージのインストール

```bash
pip install -r requirements.txt
```

または Conda 環境を使用する場合：

```bash
conda create -n report_app python=3.10
conda activate report_app
pip install -r requirements.txt
```

### 3. 外部コマンドのインストール

**gnuplot**:
```bash
sudo apt install gnuplot
```

**TeX Live** (pdflatex):
```bash
sudo apt install texlive-full
# または最小構成の場合:
sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-recommended
```

日本語フォントを使う場合は追加パッケージが必要です：
```bash
sudo apt install texlive-lang-japanese fonts-noto-cjk
```

### 4. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. 「Get API key」から API キーを発行
3. アプリ起動後、サイドバーの「Gemini API Key」欄に入力

> ⚠️ **APIキーをソースコードにハードコードしないでください。** `.gitignore` に `.env` が設定されていますので、環境変数や `.env` ファイルで管理することを推奨します。

---

## 📁 実験データの準備

アプリに読み込ませるファイルを1つのディレクトリにまとめてください。

```
experiment_data/
├── data.xlsx        # 実験データ（複数シート対応）
├── manual.pdf       # 実験指導書
└── template.tex     # レポートテンプレート（下記参照）
```

- **Excel**: 複数シート対応。シートごとに Markdown テーブルに変換されます
- **PDF**: 全ページをテキスト抽出 + 画像化して Gemini に送信します
- **TeX**: 後述するマーカーで本文部分と個人情報部分を分離します

### TeXテンプレートのマーカー設定（重要）

レポートテンプレートに以下のコメントマーカーを追加することで、表紙・氏名・学籍番号などの個人情報が **外部AIに送信されるのを防ぎます**。

```latex
\documentclass[a4paper]{jarticle}
\usepackage{graphicx}

\begin{document}

% --- 表紙（個人情報 - AIには送信されません）---
\begin{titlepage}
  \title{実験レポート}
  \author{山田 太郎 \\ 学籍番号: 12345}
  \date{\today}
  \maketitle
\end{titlepage}

% --- AI_TARGET_START ---
% ↑ このマーカーより下がAIの編集対象です

\section{目的}
（ここに目的を記述）

\section{理論}
（ここに理論を記述）

\section{実験方法}
（ここに実験方法を記述）

\section{結果}
（ここに結果を記述）

\section{考察}
（ここに考察を記述）

\section{結論}
（ここに結論を記述）

% --- AI_TARGET_END ---
% ↑ このマーカーより上がAIの編集対象です

\end{document}
```

> マーカーが存在しない場合は `\begin{document}` ～ `\end{document}` の範囲で自動分割を試みます。

---

## 🔒 プライバシーと個人情報保護

このアプリは個人情報保護を設計の中心に置いています。

```
[TeXファイル]
    │
    ├─ ヘッダー部（氏名・学籍番号など）  ─────────────────────▶ APIに送信されない
    │   % --- AI_TARGET_START --- より前
    │
    └─ 本文部（考察・実験内容など）      ──▶ Gemini API ──▶ レポート生成
        % --- AI_TARGET_START --- から
        % --- AI_TARGET_END --- まで
```

**実装上の保証**:
- TeX の分割処理は API 通信より**必ず前に**実行されます
- 個人情報を含むヘッダー部は変数としても保持しますが、外部に送信しません
- PDF・Excelのデータは実験データのみを含む想定です（氏名等を記載しないことを推奨）

---

## 📖 使い方

### Step 1: アプリ起動

```bash
streamlit run app.py
```

ブラウザが自動で開きます（デフォルト: `http://localhost:8501`）。

### Step 2: 設定

1. サイドバーの「**Gemini API Key**」欄に API キーを入力
2. 「**実験データのディレクトリパス**」に実験データフォルダの絶対パスを入力
3. 「**📂 ファイルを読み込む**」ボタンをクリック

### Step 3: ルール抽出

- 「**🔍 指導書からルールを抽出する**」ボタンをクリック
- AIが指導書 PDF を解析し、グラフ作成ルールや考察ポイントを抽出します（数十秒かかります）

### Step 4: 対話（ファシリテーション）

- 「**💬 対話を開始する**」ボタンをクリック
- AIが教員役として実験データに関する問いかけを開始します
- チャット欄に自分の考えを入力して対話を進めます
- 十分な考察ができたら「**📄 レポートを生成する**」ボタンをクリック

### Step 5: レポート生成・ダウンロード

- gnuplot でグラフが自動生成されます
- LaTeX がコンパイルされ PDF が生成されます
- 「**📥 PDFをダウンロード**」ボタンでレポートを取得します
- AI による最終レビューも表示されます

生成されたファイルは `<指定ディレクトリ>/output/` に保存されます。

---

## 📂 プロジェクト構成

```
report-helper/
├── app.py              # Streamlit メインUI・フロー制御
├── config.py           # 設定・AIシステムプロンプト・プロンプトテンプレート
├── file_parser.py      # ファイル解析エンジン（PDF・Excel・TeX）
├── gemini_client.py    # Gemini API クライアント
├── report_builder.py   # レポート生成パイプライン（gnuplot・pdflatex）
├── requirements.txt    # Python パッケージ依存関係
├── .gitignore          # APIキー等の除外設定
└── README.md           # このファイル
```

---

## ⚙️ 設定のカスタマイズ

`config.py` を編集することで動作をカスタマイズできます。

```python
# 使用するGeminiモデル
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

# TeXテンプレートの分割マーカー
TEX_MARKER_START = "% --- AI_TARGET_START ---"
TEX_MARKER_END = "% --- AI_TARGET_END ---"

# AIの役割設定（システムプロンプト）
FACILITATOR_SYSTEM_PROMPT = """
あなたは高専の電気電子工学の実験指導教員です。
絶対に答えを先に言わず...
"""
```

---

## 🐛 トラブルシューティング

### gnuplot でグラフが生成されない

```
gnuplotエラー: ...
```

- gnuplot がインストールされているか確認: `which gnuplot`
- 日本語フォント `Noto Sans CJK JP` が必要な場合: `sudo apt install fonts-noto-cjk`
- エラーメッセージはアプリ上に表示されるので確認してください

### pdflatex でコンパイルに失敗する

- 日本語文書の場合は `jarticle` や `pxjartcls` などが必要です
- 必要なパッケージがない場合: `sudo apt install texlive-full` で全パッケージをインストール
- エラーログはアプリ上に表示されます（先頭20行）

### PDF が読み込めない / テキスト抽出が空になる

- スキャン画像のみの PDF はテキスト抽出できません（画像情報は AI に送信されます）
- パスワードで保護されている PDF は対応していません

### Gemini API エラー

- API キーが正しいか確認してください
- 無料枠のレート制限に引っかかっている場合は、しばらく待ってから再試行してください
- PDF の画像枚数が多い場合、リクエストが大きくなりすぎることがあります。PDF のページ数を減らしてください

### チャット履歴がリセットされる

- Streamlit を再起動するとセッションがリセットされます
- ブラウザを閉じずに操作してください

---

## 🔧 開発者向け情報

### ログ確認

サイドバー下部の「📋 ログ」欄で直近20件の処理ログを確認できます。  
ターミナルには詳細なデバッグログも出力されます（`logging.INFO` レベル）。

### 生成される中間ファイル

`<ディレクトリ>/output/` に以下のファイルが生成されます：

| ファイル | 内容 |
|---|---|
| `plot.gp` | gnuplot スクリプト |
| `graph.png` | 生成されたグラフ画像 |
| `report.tex` | 生成された LaTeX ソース |
| `report.pdf` | 最終 PDF |

### フェーズ管理

アプリのフロー制御は `st.session_state.phase` で管理されています：

```
init → loaded → rules_extracted → chatting → generating → done
```

### Gitコミット履歴

```
fd7b4bc  Feat: Phase 1 - 環境構築とベースUIの作成
f10e2c1  Feat: Phase 2 - ファイル解析エンジンの実装と動作確認
2739d2b  Feat: Phase 3 - Gemini 3 Flash連携とルール抽出
0f1f4c8  Feat: Phase 4 - 対話型ファシリテーションとコード生成ロジック
11d6d36  Fix: レビュー指摘のバグ修正
```

---

## 📜 ライセンス

MIT License

---

## 🙏 謝辞

- [Google Gemini](https://ai.google.dev/) - AI APIの提供
- [Streamlit](https://streamlit.io/) - Webアプリフレームワーク
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF処理ライブラリ
