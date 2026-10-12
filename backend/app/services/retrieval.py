import re
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.policy import PolicySource
from app.schemas.policy import PolicySearchResultItem

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "can", "could", "should", "would", "will", "shall",
    "it", "its", "this", "that", "these", "those", "after", "before", "same", "laptop",
}


def tokenize(text: str) -> List[str]:
    """Extract lowercased alphanumeric words, excluding common stop words."""
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


def split_into_passages(document_text: str) -> List[str]:
    """Split document into coherent sections or paragraphs."""
    raw_passages = [p.strip() for p in document_text.split("\n\n") if p.strip()]
    cleaned = []
    for p in raw_passages:
        # Don't treat standalone headings of less than 30 chars as isolated passages
        if len(p) < 30 and len(raw_passages) > 1:
            continue
        cleaned.append(p)
    return cleaned or [document_text.strip()]


class PolicyRetrievalService:
    """Deterministic lexical retrieval service for the policy library."""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query: str,
        product_category: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 5,
    ) -> List[PolicySearchResultItem]:
        """Search policy library for passages matching query tokens."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Retrieve eligible policy documents from SQLite
        db_query = self.db.query(PolicySource)
        if product_category:
            cat = product_category.lower()
            db_query = db_query.filter(
                (PolicySource.product_category == None)  # noqa: E711
                | (PolicySource.product_category == "electronics")
                | (PolicySource.product_category == cat)
            )
        if jurisdiction:
            jur = jurisdiction.upper()
            db_query = db_query.filter(
                (PolicySource.jurisdiction == None)  # noqa: E711
                | (PolicySource.jurisdiction == "GLOBAL")
                | (PolicySource.jurisdiction == jur)
            )

        sources = db_query.all()
        scored_passages = []

        for source in sources:
            title_tokens = set(tokenize(source.title))
            passages = split_into_passages(source.document_text)

            for passage in passages:
                passage_tokens = tokenize(passage)
                if not passage_tokens:
                    continue

                passage_token_set = set(passage_tokens)
                matched_query_tokens = [t for t in query_tokens if t in passage_token_set]

                if not matched_query_tokens:
                    continue

                # Lexical score: term matches weighted by frequency + title match bonus
                score = 0.0
                for t in matched_query_tokens:
                    count = passage_tokens.count(t)
                    score += 1.0 + (0.5 * (count - 1))
                # Title token match bonus
                for t in query_tokens:
                    if t in title_tokens:
                        score += 0.5

                scored_passages.append({
                    "source_id": source.id,
                    "source_title": source.title,
                    "source_url": source.source_url,
                    "source_type": source.source_type,
                    "jurisdiction": source.jurisdiction,
                    "product_category": source.product_category,
                    "passage": passage,
                    "score": round(score, 2),
                })

        # Sort descending by score
        scored_passages.sort(key=lambda x: x["score"], reverse=True)

        # De-duplicate identical stored passages; equal prefixes can be distinct evidence.
        seen_passages = set()
        results = []
        for sp in scored_passages:
            passage_key = (sp["source_id"], sp["passage"])
            if passage_key in seen_passages:
                continue
            seen_passages.add(passage_key)

            results.append(
                PolicySearchResultItem(
                    source_id=sp["source_id"],
                    source_title=sp["source_title"],
                    source_url=sp["source_url"],
                    source_type=sp["source_type"],
                    jurisdiction=sp["jurisdiction"],
                    product_category=sp["product_category"],
                    passage=sp["passage"],
                    relevance_score=sp["score"],
                )
            )
            if len(results) >= limit:
                break

        return results
