# This file extracts readable text from uploaded files (TXT, PDF, DOCX).
# It decodes the base64 content sent by the frontend, picks the right parser
# for the file type, and returns clean plain text.

import base64
import binascii
import io
import re
import zipfile
from pathlib import Path

MAX_EXTRACTED_TEXT_CHARS = 50000

# Extensions that can be decoded directly as text.
TEXT_EXTENSIONS = {
    ".txt",
}

# Extensions that need a dedicated parser before text can be read.
BINARY_EXTENSIONS = {
    ".pdf",
    ".docx",
}

SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | BINARY_EXTENSIONS


def _normalize_text(text: str) -> str:
    """
    Normalise line endings and whitespace in extracted text.

    Args:
        text (str): raw extracted text

    Returns:
        str: text with consistent line endings and no excessive blank lines
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _decode_base64_content(content_base64: str) -> bytes:
    """
    Decode a base64 string into raw bytes.

    Args:
        content_base64 (str): base64-encoded file content from the frontend

    Returns:
        bytes: the decoded file bytes

    Raises:
        ValueError: if the string is not valid base64
    """
    try:
        return base64.b64decode(content_base64, validate=True)
    except binascii.Error as error:
        # Raise a client-facing validation error when the payload is not valid base64.
        raise ValueError("The uploaded file content could not be decoded.") from error


def _decode_text_bytes(file_bytes: bytes) -> str:
    """
    Decode raw bytes into a string by trying common encodings in order.
    Falls back to UTF-8 with error replacement if nothing else works.

    Args:
        file_bytes (bytes): the raw bytes of a plain text file

    Returns:
        str: the decoded text
    """
    # Try common encodings first so simple text uploads work without extra configuration.
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF file using pypdf.

    Args:
        file_bytes (bytes): the raw bytes of the PDF file

    Returns:
        str: all text extracted from each page, joined with newlines

    Raises:
        RuntimeError: if the pypdf package is not installed
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("PDF extraction requires the 'pypdf' package.")

    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract plain text from a DOCX file using python-docx.

    Args:
        file_bytes (bytes): the raw bytes of the DOCX file

    Returns:
        str: all paragraph text joined with newlines

    Raises:
        RuntimeError: if the python-docx package is not installed
        ValueError: if the file is empty or not a valid DOCX
    """
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("DOCX extraction requires the 'python-docx' package.")

    try:
        document = Document(io.BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise ValueError("The Word file appears to be empty or corrupted. Please try a different file.")

    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _truncate_text(text: str) -> tuple[str, bool]:
    """
    Cut the text down to the maximum allowed length if needed.

    Args:
        text (str): the full extracted text

    Returns:
        tuple[str, bool]: the (possibly trimmed) text and a flag that is True if it was cut
    """
    if len(text) <= MAX_EXTRACTED_TEXT_CHARS:
        return text, False
    return text[:MAX_EXTRACTED_TEXT_CHARS].rstrip(), True


def extract_text_from_upload(filename: str, content_base64: str):
    """
    Decode a base64-encoded file and extract its readable text.
    Supports TXT, PDF, and DOCX formats.

    Args:
        filename (str): the original file name, used to detect the file type
        content_base64 (str): the base64-encoded file content sent by the frontend

    Returns:
        dict: a dict with "text", "sourceType", "usedFallback", and "notice" fields.
              "notice" is non-empty when the file was truncated or had no readable text.

    Raises:
        ValueError: if the file type is not supported or the base64 content is invalid
        RuntimeError: if a required parsing package (pypdf, python-docx) is not installed
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Supported formats: TXT, PDF, DOCX.")

    file_bytes = _decode_base64_content(content_base64)

    # Choose an extraction strategy based on the uploaded file type.
    if suffix in TEXT_EXTENSIONS:
        text = _decode_text_bytes(file_bytes)
    elif suffix == ".pdf":
        text = _extract_text_from_pdf(file_bytes)
    else:
        text = _extract_text_from_docx(file_bytes)

    normalized = _normalize_text(text)
    truncated_text, was_truncated = _truncate_text(normalized)

    if not truncated_text:
        # Return a helpful notice when the file contains no machine-readable text.
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
        # Tell the frontend when only part of the file was loaded.
        notice = f"Only the first {MAX_EXTRACTED_TEXT_CHARS} characters were loaded so the text fits the reading tool."

    return {
        "text": truncated_text,
        "sourceType": suffix.lstrip("."),
        "usedFallback": False,
        "notice": notice,
    }
