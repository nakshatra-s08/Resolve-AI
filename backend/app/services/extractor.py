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


def sanitize_extracted_snippet(text: str, max_chars: int = 200) -> str:
    """
    Sanitize extracted text snippet to prevent leaking personal information,
    addresses, phone numbers, and emails into logs or assistant context.
    """
    if not text:
        return ""

    sanitized = text
    # Mask emails
    sanitized = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL REDACTED]", sanitized)
    # Mask phone numbers (10+ digits with optional separators)
    sanitized = re.sub(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE REDACTED]", sanitized)
    # Mask explicit address lines
    sanitized = re.sub(r"(?i)\b(address|flat no|plot no|street|road|lane|nagar|colony|apartment|sector)\b[^\n,;]{5,40}", "[ADDRESS REDACTED]", sanitized)
    # Mask Indian pin codes / zip codes (e.g., 6 digits)
    sanitized = re.sub(r"\b\d{6}\b", "[POSTAL CODE REDACTED]", sanitized)

    # Normalize whitespace
    clean_snippet = " ".join(sanitized.split())
    if len(clean_snippet) > max_chars:
        return clean_snippet[:max_chars] + "..."
    return clean_snippet


def assess_evidence_relevance(
    filename: str,
    extracted_text: Optional[str],
    product_name: str,
    issue_description: str,
) -> Tuple[str, str]:
    """
    Assess evidence relevance conservatively against the reported case product and issue.
    Returns: (relevance_status, relevance_reason)
    Possible statuses: 'MISMATCH', 'RELEVANT', 'UNVERIFIED'
    """
    combined_content = f"{filename} {extracted_text or ''}".lower()

    # Academic, coursework, or unrelated workplace document indicators
    unrelated_academic_indicators = [
        "lab manual", "laboratory", "experiment", "teleportation", "quantum",
        "mathematics", "calculus", "differential equations", "theorem",
        "curriculum", "syllabus", "assignment", "semester", "university",
        "offer letter", "employment agreement", "ctc", "salary slip", "internship",
    ]

    for indicator in unrelated_academic_indicators:
        if indicator in combined_content:
            return "MISMATCH", f"Document appears unrelated to hardware repair (detected '{indicator}'). Content not admitted as verified case fact."

    # Product-specific keyword tokens
    product_tokens = [t.lower() for t in re.findall(r"\w+", product_name) if len(t) >= 3]
    # Standard hardware repair keywords
    repair_keywords = [
        "repair", "service", "invoice", "receipt", "warranty", "serial",
        "defect", "fault", "technician", "job sheet", "replacement",
        "hardware", "sound", "headphone", "audio", "battery", "motherboard",
        "screen", "display", "power", "charger"
    ]

    has_product_match = any(token in combined_content for token in product_tokens)
    has_repair_match = any(kw in combined_content for kw in repair_keywords)

    if has_product_match and has_repair_match:
        return "RELEVANT", "Document references product and hardware/service terminology."

    # Conservative default when neither clear mismatch nor clear correlation exists
    return "UNVERIFIED", "Relevance not verified. Category presence does not verify authenticity or case correlation."
