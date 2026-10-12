from sqlalchemy.orm import Session
from app.models.policy import PolicySource, PolicySourceType

# Curated reference policy documents with explicit provenance labels
SEED_POLICIES = [
    {
        "id": "policy_demo_mfg_repair_01",
        "title": "DEMO POLICY — NOT AN OFFICIAL MANUFACTURER POLICY: Standard Hardware Repair & Replacement Guidelines",
        "source_url": None,
        "source_type": PolicySourceType.ILLUSTRATIVE,
        "jurisdiction": "GLOBAL",
        "product_category": "laptop",
        "document_text": (
            "DEMO POLICY — NOT AN OFFICIAL MANUFACTURER POLICY\n\n"
            "Section 1: Repair Attempt Limitations\n"
            "1.1 If a consumer hardware product undergoes two (2) separate repair attempts for the exact same "
            "hardware defect within the active warranty period, and the fault recurs within thirty (30) days of the second repair, "
            "the product qualifies for escalated review.\n"
            "1.2 Upon qualification under Section 1.1, the consumer may request an authorization for unit replacement or "
            "a commercial credit/refund rather than submitting to a third repair cycle.\n"
            "1.3 Requisite documentation: Original purchase invoice, job sheets or repair receipts from both prior service visits, "
            "and a clear description of the recurring failure symptoms."
        ),
    },
    {
        "id": "policy_demo_warranty_remedies_02",
        "title": "DEMO POLICY — NOT AN OFFICIAL MANUFACTURER POLICY: Limited Warranty Remediation Standards",
        "source_url": None,
        "source_type": PolicySourceType.ILLUSTRATIVE,
        "jurisdiction": "GLOBAL",
        "product_category": "laptop",
        "document_text": (
            "DEMO POLICY — NOT AN OFFICIAL MANUFACTURER POLICY\n\n"
            "Section 2: Warranty Remedy Escalation\n"
            "2.1 Authorized service centers must endeavor to restore hardware to functional operating specifications.\n"
            "2.2 In cases where repeated component replacements (such as motherboards or display assemblies) fail to resolve the defect, "
            "the warranty provider's tier-2 technical escalation team must evaluate the unit for inherent manufacturing failure.\n"
            "2.3 The warranty provider is obligated to provide a formal resolution proposal in writing within five (5) business days "
            "of receiving complete repair documentation."
        ),
    },
    {
        "id": "policy_official_consumer_guidance_in_03",
        "title": "REFERENCE POINTER: National Consumer Helpline",
        "source_url": "https://consumerhelpline.gov.in/",
        "source_type": PolicySourceType.GUIDANCE,
        "jurisdiction": "IN",
        "product_category": "electronics",
        "document_text": (
            "Reference pointer only: https://consumerhelpline.gov.in/\n\n"
            "This seed stores a link to the National Consumer Helpline. It does not contain a verified excerpt from that site. "
            "No legal rule, eligibility test, remedy, or required-document list is asserted by this record. "
            "Consult the linked source and applicable official materials for current guidance."
        ),
    },
    {
        "id": "policy_guidance_evidence_checklist_04",
        "title": "GUIDANCE: Best Practice Evidence Package for Repeat Repair Grievances",
        "source_url": None,
        "source_type": PolicySourceType.GUIDANCE,
        "jurisdiction": "GLOBAL",
        "product_category": "laptop",
        "document_text": (
            "GUIDANCE DOCUMENT: Evidence Best Practices for Recurring Hardware Failures\n\n"
            "To present a compelling and irrefutable grievance for recurring product repairs:\n"
            "1. Document Chain of Custody: Secure service center work orders / RMA receipts proving the device was delivered for service on specific dates.\n"
            "2. Verify Defect Description Matching: Ensure that each job sheet accurately records the identical customer-reported symptom "
            "(e.g., 'no display / screen flickering') rather than generic inspection notes.\n"
            "3. Timeline Chronology: Create a date-indexed timeline illustrating purchase date, date of first repair, return date, "
            "date of second repair, and date the defect resurfaced.\n"
            "4. Formal Demand: Request a written acknowledgment from the brand escalations team before agreeing to any third repair attempt."
        ),
    },
]


def seed_policy_library(db: Session) -> int:
    """
    Idempotently seeds the policy library into SQLite.
    Returns the count of newly inserted policy records.
    """
    inserted_count = 0
    changed = False

    for p in SEED_POLICIES:
        existing = db.query(PolicySource).filter(PolicySource.id == p["id"]).first()
        if not existing:
            new_policy = PolicySource(
                id=p["id"],
                title=p["title"],
                source_url=p["source_url"],
                source_type=p["source_type"],
                jurisdiction=p["jurisdiction"],
                product_category=p["product_category"],
                document_text=p["document_text"],
                retrieved_at=None,
            )
            db.add(new_policy)
            inserted_count += 1
            changed = True
        else:
            # Keep bundled records' provenance accurate across upgrades while leaving
            # user-created policy records untouched.
            for field in (
                "title", "source_url", "source_type", "jurisdiction",
                "product_category", "document_text", "retrieved_at",
            ):
                value = None if field == "retrieved_at" else p[field]
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True

    if changed:
        db.commit()

    return inserted_count
