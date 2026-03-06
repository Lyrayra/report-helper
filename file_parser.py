"""ファイル解析エンジン: PDF, Excel, TeXの読み込みと前処理"""

import os
import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import fitz  # PyMuPDF
from PIL import Image

from config import TEX_MARKER_START, TEX_MARKER_END

logger = logging.getLogger(__name__)


def find_files(directory: str) -> dict:
    """指定ディレクトリ内のExcel, PDF, TeXファイルを検索する"""
    result = {"excel": [], "pdf": [], "tex": []}
    extensions = {
        ".xlsx": "excel", ".xls": "excel",
        ".pdf": "pdf",
        ".tex": "tex",
    }
    try:
        for entry in os.scandir(directory):
            if entry.is_file():
                ext = Path(entry.name).suffix.lower()
                if ext in extensions:
                    result[extensions[ext]].append(entry.path)
        logger.info(
            "ファイル検出: Excel=%d, PDF=%d, TeX=%d",
            len(result["excel"]), len(result["pdf"]), len(result["tex"]),
        )
    except OSError as e:
        logger.error("ディレクトリ読み込みエラー: %s", e)
    return result


# ---------- Excel処理 ----------

def read_excel_to_markdown(filepath: str) -> str:
    """Excelファイルを読み込み、各シートをMarkdownテーブルに変換する"""
    logger.info("Excel読み込み: %s", filepath)
    try:
        xls = pd.ExcelFile(filepath, engine="openpyxl")
    except Exception as e:
        logger.error("Excelファイルを開けません: %s", e)
        return f"[Excelエラー] {e}"

    md_parts = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if df.empty:
            continue
        md_parts.append(f"### シート: {sheet_name}\n")
        md_parts.append(df.to_markdown(index=False))
        md_parts.append("")
        logger.info("  シート '%s': %d行 x %d列", sheet_name, len(df), len(df.columns))

    return "\n".join(md_parts) if md_parts else "[空のExcelファイル]"


# ---------- PDF処理 ----------

def extract_pdf_pages(filepath: str) -> tuple[list[Image.Image], str]:
    """
    PDFを読み込み、各ページのPNG画像とテキストを返す。
    PyMuPDFでテキスト抽出とページ画像化を行う。
    """
    logger.info("PDF読み込み: %s", filepath)
    images = []
    text_parts = []

    try:
        doc = fitz.open(filepath)
        for page_num, page in enumerate(doc):
            # テキスト抽出
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"--- ページ {page_num + 1} ---\n{text}")

            # ページを画像化 (150 DPI)
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)

            logger.info("  ページ %d: テキスト %d文字, 画像 %dx%d",
                        page_num + 1, len(text), img.width, img.height)
        doc.close()
    except Exception as e:
        logger.error("PDF処理エラー: %s", e)

    full_text = "\n\n".join(text_parts) if text_parts else "[テキスト抽出不可]"
    return images, full_text


# ---------- TeX処理 ----------

class TexTemplate:
    """TeXテンプレートを個人情報部分とAI編集部分に分割して管理する"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.header = ""   # プリアンブル＋表紙（個人情報を含む、APIに送らない）
        self.body = ""     # AI編集対象の本文
        self.footer = ""   # ドキュメント終端
        self._parse(filepath)

    def _parse(self, filepath: str):
        logger.info("TeXテンプレート読み込み: %s", filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error("TeXファイルを開けません: %s", e)
            return

        start_idx = content.find(TEX_MARKER_START)
        end_idx = content.find(TEX_MARKER_END)

        if start_idx == -1 or end_idx == -1:
            logger.warning(
                "マーカーが見つかりません。ファイル全体を本文として扱います。"
                " マーカー: '%s' / '%s'",
                TEX_MARKER_START, TEX_MARKER_END,
            )
            # マーカーがない場合: \begin{document} と \end{document} で分割を試みる
            doc_begin = content.find("\\begin{document}")
            doc_end = content.find("\\end{document}")
            if doc_begin != -1 and doc_end != -1:
                split_begin = doc_begin + len("\\begin{document}")
                self.header = content[:split_begin] + "\n"
                self.body = content[split_begin:doc_end].strip()
                self.footer = "\n" + content[doc_end:]
            else:
                self.body = content
            return

        self.header = content[:start_idx + len(TEX_MARKER_START)] + "\n"
        self.body = content[start_idx + len(TEX_MARKER_START):end_idx].strip()
        self.footer = "\n" + content[end_idx:]
        logger.info("TeXテンプレート分割: ヘッダ=%d文字, 本文=%d文字, フッタ=%d文字",
                     len(self.header), len(self.body), len(self.footer))

    def reconstruct(self, new_body: str) -> str:
        """AIが生成した本文を再結合して完全なTeXソースを返す"""
        return self.header + new_body + self.footer

    def get_body_for_ai(self) -> str:
        """AIに送信する本文部分のみを返す（個人情報を含まない）"""
        return self.body
