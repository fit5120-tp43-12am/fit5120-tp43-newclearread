import pymupdf4llm

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    将 PDF 文件转换为干净的 Markdown 文本。
    自动处理基础的图表过滤和排版解析。
    """
    try:
        md_text = pymupdf4llm.to_markdown(pdf_path)
        return md_text
    except Exception as e:
        # 实际项目中建议接入真实的 Logger
        print(f"PDF提取失败: {e}")
        return ""