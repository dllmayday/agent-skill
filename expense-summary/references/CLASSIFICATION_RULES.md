# 提取引擎参考 (Extraction Engine Reference)

## 支持的文件类型

| 扩展名 | 处理方式 | 引擎 |
|:---|:---|:---|
| `.pdf` | 文本提取 + 表格提取 | PyMuPDF (fitz) + pdfplumber |
| `.jpg`, `.jpeg`, `.png` | OCR 文字识别 | Tesseract → CnOCR (回退) |

> `.xlsx`、`.docx`、`.txt` 等格式不在提取范围内。

## OCR 引擎回退策略

```
Tesseract (chi_sim+eng)
    ↓ 失败/未安装/无结果
CnOCR (cnocr)
    ↓ 失败/未安装/无结果
返回空字符串 + 安装指导
```

### Tesseract

- **语言包**: `chi_sim+eng` (简体中文 + 英文)
- **系统依赖**: 需安装 `tesseract-ocr` 和 `tesseract-ocr-chi-sim`
- **调用方式**: `pytesseract.image_to_string(image, lang='chi_sim+eng')`

### CnOCR (备选)

- **纯 Python** 实现，无需系统依赖
- 首次使用自动下载模型 (~几MB)
- **调用方式**: `CnOcr().ocr(image_path)`，返回 `[{'text': ..., 'score': ...}]`

## PDF 提取细节

### PyMuPDF 文本提取

- 逐页提取原始文本
- 保留换行和空格，便于保持发票表格结构
- 每页以 `--- 第N页 ---` 分隔

### pdfplumber 表格提取

- 对每页尝试 `page.extract_tables()`
- 有表格的页面以 `--- 第N页表格数据 ---` 分隔
- 每个表格以 `表格N:` 标记，行数据用 ` | ` 连接

## 目录遍历策略

使用 `os.walk()` 递归扫描所有子目录：

```python
for root, dirs, files in os.walk(base_dir):
    for filename in files:
        filepath = os.path.join(root, filename)
        rel_path = os.path.relpath(filepath, base_dir)
        # rel_path 作为 extracted_content.json 的 key
```

优势：
- 自动处理多级子目录（如 `住宿/`、`打车/`、`机票/`）
- 相对路径作为 key 避免同名文件冲突

## 输出格式

### extracted_content.json

```json
{
  "relative/path/file.pdf": {
    "type": "pdf",
    "content": "--- 第1页 ---\ndzfp_25434000000004614794\nXX酒店管理有限公司\n..."
  },
  "subdir/image.jpg": {
    "type": "image",
    "content": "OCR识别的文字内容..."
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| key | `string` | 文件相对路径（如 `住宿/dzfp_xxx.pdf`） |
| `type` | `string` | `"pdf"` 或 `"image"` |
| `content` | `string` | 提取的原始文本（可能为空字符串） |

## 完整的提取流程请参见

- **expense-reporting** SKILL.md：提取脚本使用说明
- **expense-summary** SKILL.md：分类、汇总和报告生成