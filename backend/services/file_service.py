import base64
import binascii
import io
import re
from pathlib import Path


MAX_EXTRACTED_TEXT_CHARS = 5000

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".log",
    ".text",
    ".rtf",
}

BINARY_EXTENSIONS = {
    ".pdf",
    ".docx",
}

SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | BINARY_EXTENSIONS


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _decode_base64_content(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except binascii.Error as error:
        raise ValueError("The uploaded file content could not be decoded.") from error


def _decode_text_bytes(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def _extract_rtf_text(raw_text: str) -> str:
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw_text)
    text = re.sub(r"\\par[d]? ?", "\n", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return text


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("PDF extraction requires the 'pypdf' package.")

    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("DOCX extraction requires the 'python-docx' package.")

    document = Document(io.BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _truncate_text(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_EXTRACTED_TEXT_CHARS:
        return text, False
    return text[:MAX_EXTRACTED_TEXT_CHARS].rstrip(), True


def extract_text_from_upload(filename: str, content_base64: str):
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Supported formats: TXT, MD, CSV, LOG, RTF, PDF, DOCX."
        )

    file_bytes = _decode_base64_content(content_base64)

    if suffix in TEXT_EXTENSIONS:
        text = _decode_text_bytes(file_bytes)
        if suffix == ".rtf":
            text = _extract_rtf_text(text)
    elif suffix == ".pdf":
        text = _extract_text_from_pdf(file_bytes)
    else:
        text = _extract_text_from_docx(file_bytes)

    normalized = _normalize_text(text)
    truncated_text, was_truncated = _truncate_text(normalized)

    if not truncated_text:
        return {
            "text": "",
            "sourceType": suffix.lstrip("."),
            "usedFallback": True,
            "notice": (
                "No readable text was found in this file. If it is a scanned PDF or image-based document, "
                "please paste the text manually."
            ),
        }

    notice = ""
    if was_truncated:
        notice = (
            f"Only the first {MAX_EXTRACTED_TEXT_CHARS} characters were loaded so the text fits the reading tool."
        )

    return {
        "text": truncated_text,
        "sourceType": suffix.lstrip("."),
        "usedFallback": False,
        "notice": notice,
    }
