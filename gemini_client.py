"""Gemini API クライアント: ルール抽出、ファシリテーション、コード生成"""

import json
import logging
from typing import Optional

from PIL import Image
from google import genai
from google.genai import types

from config import (
    GEMINI_MODEL,
    MAX_OUTPUT_TOKENS,
    FACILITATOR_SYSTEM_PROMPT,
    CODE_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)


def list_available_models(api_key: str) -> list[str]:
    """generateContentに対応している利用可能なGeminiモデルの一覧を返す"""
    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        result = []
        for m in models:
            name = m.name  # "models/gemini-..." 形式
            # generateContent対応かつgeminiモデルのみ絞り込む
            supported = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", [])
            supports_gen = (
                not supported  # 属性なしの場合は一旦含める
                or "generateContent" in supported
                or "generate_content" in supported
            )
            if "gemini" in name and supports_gen:
                # 表示用に "models/" プレフィックスを除く
                result.append(name.removeprefix("models/"))
        return sorted(result)
    except Exception as e:
        logger.error("モデル一覧取得エラー: %s", e)
        return []


def create_client(api_key: str) -> genai.Client:
    """Gemini APIクライアントを作成する"""
    return genai.Client(api_key=api_key)


def extract_rules(
    client: genai.Client,
    pdf_images: list[Image.Image],
    pdf_text: str,
    excel_markdown: str,
    model: str = GEMINI_MODEL,
) -> str:
    """指導書PDF・テキスト・Excelデータからレポートルールを抽出する"""
    logger.info("ルール抽出開始: 画像%d枚, テキスト%d文字, Excelデータ%d文字",
                len(pdf_images), len(pdf_text), len(excel_markdown))

    prompt_text = (
        "以下は実験の指導書と実験データです。\n\n"
        "【指導書テキスト（OCR抽出）】\n"
        f"{pdf_text}\n\n"
        "【実験データ（Excel）】\n"
        f"{excel_markdown}\n\n"
        "テキストデータを正として扱い、画像からグラフ作成のルール（軸の設定、単位、スケールなど）"
        "やレポートのフォーマット（セクション構成、必要な考察ポイントなど）を読み取ってください。\n"
        "結果は以下の形式で整理してください：\n"
        "1. グラフ作成ルール（軸ラベル、単位、プロットの種類など）\n"
        "2. レポートフォーマット（セクション構成）\n"
        "3. 考察で触れるべきポイント\n"
        "4. その他注意事項"
    )

    contents = []
    # PDF画像を追加
    for img in pdf_images:
        contents.append(img)
    contents.append(prompt_text)

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.3,
            ),
        )
        result = response.text
        logger.info("ルール抽出完了: %d文字", len(result))
        return result
    except Exception as e:
        logger.error("ルール抽出エラー: %s", e)
        return f"[ルール抽出エラー] {e}"


def create_chat_session(
    client: genai.Client,
    rules: str,
    excel_markdown: str,
    tex_body: str,
    history: list[dict] | None = None,
    model: str = GEMINI_MODEL,
) -> "genai.ChatSession":
    """ファシリテーション用チャットセッションを作成する"""
    system_instruction = (
        FACILITATOR_SYSTEM_PROMPT + "\n\n"
        "【抜出されたレポートルール】\n" + rules + "\n\n"
        "【実験データ】\n" + excel_markdown + "\n\n"
        "【TeXテンプレート本文構造】\n" + tex_body
    )

    chat_history = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )

    chat = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.7,
        ),
        history=chat_history,
    )
    return chat


def send_chat_message(chat, message: str) -> str:
    """チャットメッセージを送信し、応答を返す"""
    try:
        response = chat.send_message(message)
        return response.text
    except Exception as e:
        logger.error("チャットエラー: %s", e)
        return f"[エラー] AI応答の取得に失敗しました: {e}"


def generate_code(
    client: genai.Client,
    rules: str,
    excel_markdown: str,
    chat_history_text: str,
    tex_body: str,
    model: str = GEMINI_MODEL,
) -> dict:
    """対話結果に基づおgnuplotスクリプトとLaTeX本文を生成する"""
    logger.info("コード生成開始")

    prompt = (
        CODE_GENERATION_PROMPT + "\n\n"
        "【レポートルール】\n" + rules + "\n\n"
        "【実験データ】\n" + excel_markdown + "\n\n"
        "【対話履歴（考察内容）】\n" + chat_history_text + "\n\n"
        "【元のTeXテンプレート本文】\n" + tex_body
    )

    response = None
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        logger.info("コード生成完了")
        return result
    except json.JSONDecodeError as e:
        logger.error("JSON解析エラー: %s", e)
        if response is not None:
            text = response.text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return {"error": f"コード生成結果のパースに失敗: {e}"}
    except Exception as e:
        logger.error("コード生成エラー: %s", e)
        return {"error": str(e)}


def generate_final_review(
    client: genai.Client,
    rules: str,
    chat_history_text: str,
    latex_body: str,
    model: str = GEMINI_MODEL,
) -> str:
    """生成されたレポートの最終レビューを行う"""
    prompt = (
        "あなたは高専の実験指導教員です。以下のレポート本文をレビューしてください。\n\n"
        "【レポートルール】\n" + rules + "\n\n"
        "【対話履歴】\n" + chat_history_text + "\n\n"
        "【生成されたLaTeX本文】\n" + latex_body + "\n\n"
        "以下の観点でレビューしてください：\n"
        "1. 考察の深さと正確性\n"
        "2. データとの整合性\n"
        "3. 改善提案（あれば）\n"
        "簡潔に日本語で回答してください。"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.3,
            ),
        )
        return response.text
    except Exception as e:
        logger.error("最終レビューエラー: %s", e)
        return f"[レビューエラー] {e}"
