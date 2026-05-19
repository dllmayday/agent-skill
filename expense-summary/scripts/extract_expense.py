#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# /// script
# dependencies = [
#   "PyMuPDF>=1.23.0",
#   "pdfplumber>=0.10.0",
#   "pillow>=10.0.0",
#   "pytesseract>=0.3.10",
# ]
# ///

"""
出差报销费用提取脚本
提取PDF、图片中的文本信息
支持多种OCR引擎（Tesseract / CnOCR）自动回退
"""

import os
import sys
import argparse
import json

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='出差报销费用提取工具 - 提取PDF/图片中的文本内容',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python3 extract_expense.py --dir ./象山出差05.3-05.10
  python3 extract_expense.py -d /path/to/出差目录
        '''
    )
    parser.add_argument(
        '-d', '--dir',
        type=str,
        required=True,
        help='出差费用凭证所在目录路径'
    )
    return parser.parse_args()


def extract_pdf_with_pymupdf(filepath):
    """使用PyMuPDF提取PDF文本（保持原样）"""
    print(f"\n{'='*60}")
    print(f"文件: {os.path.basename(filepath)}")
    print(f"{'='*60}")

    try:
        doc = fitz.open(filepath)
        text = ""
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            if page_text.strip():
                text += f"\n--- 第{page_num+1}页 ---\n"
                text += page_text

        # 尝试提取表格
        with pdfplumber.open(filepath) as doc2:
            for page_num, page in enumerate(doc2.pages):
                tables = page.extract_tables()
                if tables:
                    text += f"\n--- 第{page_num+1}页表格数据 ---\n"
                    for table_idx, table in enumerate(tables):
                        text += f"\n表格{table_idx+1}:\n"
                    for row in table:
                        text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"

        doc.close()

        if text.strip():
            print(text)
        else:
            print("未能提取到文本内容")

        return text
    except Exception as e:
        print(f"提取失败: {e}")
        return ""


def ocr_image_with_fallback(image_path):
    """
    多引擎OCR识别图片文字
    优先级: Tesseract -> CnOCR -> 失败提示
    返回识别出的文本字符串
    """
    # ---------- 1. 尝试 Tesseract ----------
    try:
        import pytesseract
        # 可选：检查tesseract命令是否可用
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            raise RuntimeError("Tesseract 未正确安装或不在 PATH 中")
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        if text.strip():
            print("[OCR] 使用 Tesseract (chi_sim+eng) 识别成功")
            return text
        else:
            print("[OCR] Tesseract 未识别出文本，尝试备选引擎...")
    except ImportError:
        print("[OCR] pytesseract 未安装，跳过 Tesseract")
    except Exception as e:
        print(f"[OCR] Tesseract 失败: {e}")

    # ---------- 2. 尝试 CnOCR (轻量级中文OCR，无需额外系统依赖) ----------
    try:
        from cnocr import CnOcr
        # 初始化读取器（首次使用会自动下载模型，约几MB，较快）
        ocr = CnOcr()
        result = ocr.ocr(image_path)
        # result格式: [{'text': '识别文本', 'score': 0.9, 'position': ...}]
        text = "\n".join([item['text'] for item in result])
        if text.strip():
            print("[OCR] 使用 CnOCR 识别成功")
            return text
        else:
            print("[OCR] CnOCR 未识别出文本")
    except ImportError:
        print("[OCR] cnocr 未安装，跳过 CnOCR")
    except Exception as e:
        print(f"[OCR] CnOCR 失败: {e}")

    # ---------- 3. 所有引擎均失败，给出安装指导 ----------
    print("\n" + "="*60)
    print("OCR 识别失败：未找到可用的 OCR 引擎或识别结果为空。")
    print("请尝试以下任一方案：")
    print("1. 安装 Tesseract 引擎（推荐）：")
    print("   Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-chi-sim")
    print("   macOS: brew install tesseract tesseract-lang")
    print("   Windows: 下载安装 https://github.com/UB-Mannheim/tesseract/wiki 并添加到 PATH")
    print("2. 或安装纯 Python 的 CnOCR（无需系统依赖，模型较小）：")
    print("   pip install cnocr")
    print("="*60)
    return ""


def extract_image_text(filepath):
    """使用OCR提取图片中的文字（改进版，支持多引擎后备）"""
    print(f"\n{'='*60}")
    print(f"图片: {os.path.basename(filepath)}")
    print(f"{'='*60}")

    text = ocr_image_with_fallback(filepath)
    if text:
        print(text)
    else:
        print("未能提取到文本内容")
    return text


def main():
    args = parse_args()
    base_dir = args.dir

    if not os.path.isdir(base_dir):
        print(f"\n❌ 错误: 目录不存在 - {base_dir}")
        sys.exit(1)

    print("开始提取出差报销文件内容...")
    print(f"目录: {base_dir}")

    all_results = {}

    # 递归遍历所有子目录，自动获取子目录下的文件
    for root, dirs, files in sorted(os.walk(base_dir)):
        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()

            # 使用相对路径作为key，避免子目录下同名文件冲突
            rel_path = os.path.relpath(filepath, base_dir)

            if ext == '.pdf':
                result = extract_pdf_with_pymupdf(filepath)
                all_results[rel_path] = {"type": "pdf", "content": result}
            elif ext in ['.jpg', '.jpeg', '.png']:
                result = extract_image_text(filepath)
                all_results[rel_path] = {"type": "image", "content": result}

    # 保存结果到JSON
    output_file = os.path.join(base_dir, "extracted_content.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n\n结果已保存到: {output_file}")


if __name__ == "__main__":
    main()