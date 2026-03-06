"""レポート生成パイプライン: gnuplot実行, TeXコンパイル"""

import os
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def run_gnuplot(script: str, output_dir: str, filename: str = "graph.png") -> dict:
    """gnuplotスクリプトを実行して画像を生成する"""
    script_path = os.path.join(output_dir, "plot.gp")
    output_path = os.path.join(output_dir, filename)

    # 出力先を強制的に設定
    preamble = f'set terminal pngcairo enhanced font "Noto Sans CJK JP,12" size 800,600\n'
    preamble += f'set output "{output_path}"\n'
    full_script = preamble + script

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_script)

        result = subprocess.run(
            ["gnuplot", script_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=output_dir,
        )

        if result.returncode != 0:
            logger.error("gnuplotエラー:\n%s", result.stderr)
            return {
                "success": False,
                "error": result.stderr,
                "script_path": script_path,
            }

        if os.path.exists(output_path):
            logger.info("グラフ生成成功: %s", output_path)
            return {
                "success": True,
                "output_path": output_path,
                "script_path": script_path,
            }
        else:
            return {
                "success": False,
                "error": "出力ファイルが生成されませんでした",
                "script_path": script_path,
            }

    except subprocess.TimeoutExpired:
        logger.error("gnuplot タイムアウト")
        return {"success": False, "error": "gnuplot実行がタイムアウトしました"}
    except Exception as e:
        logger.error("gnuplot実行エラー: %s", e)
        return {"success": False, "error": str(e)}


def compile_latex(tex_source: str, output_dir: str, filename: str = "report") -> dict:
    """LaTeXソースをコンパイルしてPDFを生成する"""
    tex_path = os.path.join(output_dir, f"{filename}.tex")
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")

    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_source)

        # 2回コンパイル（相互参照の解決のため）
        for i in range(2):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={output_dir}",
                    tex_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=output_dir,
            )

            if result.returncode != 0 and i == 1:
                # 2回目のコンパイルでもエラーの場合
                log_path = os.path.join(output_dir, f"{filename}.log")
                log_content = ""
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                        log_content = lf.read()
                    # エラー行を抽出
                    error_lines = [
                        line for line in log_content.split("\n")
                        if line.startswith("!") or "Error" in line
                    ]
                    error_summary = "\n".join(error_lines[:20])
                else:
                    error_summary = result.stderr

                logger.error("LaTeXコンパイルエラー:\n%s", error_summary)
                return {
                    "success": False,
                    "error": error_summary,
                    "tex_path": tex_path,
                    "stdout": (result.stdout or "")[-500:],
                }

        if os.path.exists(pdf_path):
            logger.info("PDF生成成功: %s", pdf_path)
            return {
                "success": True,
                "pdf_path": pdf_path,
                "tex_path": tex_path,
            }
        else:
            return {
                "success": False,
                "error": "PDFファイルが生成されませんでした",
                "tex_path": tex_path,
            }

    except subprocess.TimeoutExpired:
        logger.error("pdflatex タイムアウト")
        return {"success": False, "error": "pdflatexの実行がタイムアウトしました"}
    except Exception as e:
        logger.error("LaTeXコンパイルエラー: %s", e)
        return {"success": False, "error": str(e)}


def ensure_output_dir(base_dir: str) -> str:
    """出力ディレクトリを作成して返す"""
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir
