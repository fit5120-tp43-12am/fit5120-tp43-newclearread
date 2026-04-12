from langchain_text_splitters import RecursiveCharacterTextSplitter
import random

def _word_count(text: str) -> int:
    """自定义的长度计算函数：按空格和换行统计真实的英文词数"""
    return len(text.split())

def chunk_text(text: str, target_word_size: int = 650, overlap_words: int = 50) -> list[str]:
    """
    将长文本按自然段落/语义进行弹性切分。
    
    :param text: 原始长文本
    :param target_word_size: 目标切块的词数上限 (默认 650 词)
    :param overlap_words: 块与块之间的重叠词数 (防止上下文断裂)
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " ", ""], 
        chunk_size=target_word_size,   # 现在这里代表的是“词数”了！
        chunk_overlap=overlap_words,   # 重叠也是“词数”
        length_function=_word_count,   # 把尺子换成我们的词数统计函数
        is_separator_regex=False,
    )
    
    chunks = splitter.create_documents([text])
    return [chunk.page_content for chunk in chunks]