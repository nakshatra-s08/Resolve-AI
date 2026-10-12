import io
import re
from typing import Tuple, Optional
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from app.models.evidence import ExtractionStatus, EvidenceType

# Maximum text characters to store per document to avoid runaway memory
MAX_EXTRACTED_CHARS = 100_000


def normalize_extracted_text(text: str) -> str:
    """Normalize extracted text by stripping excessive whitespace while preserving paragraph structure."""
    if not text:
        return ""
    # Normalize unicode spaces and non-breaking spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace sequences of 3 or more newlines with double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing and leading whitespace
    return text.strip()


def extract_text_from_file(
    content: bytes,
    mime_type: str,
    file_extension: str,
) -> Tuple[Optional[str], ExtractionStatus]:
    """
    Extract selectable text from file content.
    Returns: (extracted_text, extraction_status)
    """
    if file_extension == "pdf" or mime_type == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            extracted_pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)

            full_text = "\n\n".join(extracted_pages)
            normalized = normalize_extracted_text(full_text)

            if not normalized:
                # Valid PDF, but image-only or empty
                return None, ExtractionStatus.NO_TEXT_FOUND

            # Truncate if exceptionally large
            if len(normalized) > MAX_EXTRACTED_CHARS:
                normalized = normalized[:MAX_EXTRACTED_CHARS]

            return normalized, ExtractionStatus.COMPLETED

        except (PdfReadError, Exception):
            # Corrupted or malformed PDF
            return None, ExtractionStatus.FAILED

    elif file_extension in {"png", "jpg", "jpeg"} or mime_type.startswith("image/"):
        # Image formats supported for upload; OCR is out-of-scope for Phase 3
        return None, ExtractionStatus.UNSUPPORTED

    return None, ExtractionStatus.UNSUPPORTED


def classify_document(filename: str, extracted_text: Optional[str] = None) -> EvidenceType:
    """
    Lightweight deterministic rule-based classifier that suggests an evidence category
    based on keywords in filename and extracted text.
    """
    corpus = filename.lower()
    if extracted_text:
        # Include first 1000 characters of text for keyword analysis
        corpus += " " + extracted_text[:1000].lower()

    if any(k in corpus for k in ["invoice", "bill", "tax invoice", "receipt of purchase", "order summary"]):
        return EvidenceType.INVOICE
    elif any(k in corpus for k in ["warranty", "guarantee", "protection plan", "care pack"]):
        return EvidenceType.WARRANTY
    elif any(k in corpus for k in ["repair receipt", "repair", "service receipt", "job sheet", "work order", "rma"]):
        return EvidenceType.REPAIR_RECEIPT
    elif any(k in corpus for k in ["communication", "email", "chat", "service communication", "support ticket", "complaint"]):
        return EvidenceType.SERVICE_COMMUNICATION

    return EvidenceType.OTHER
