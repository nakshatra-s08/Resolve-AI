from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.schemas.policy import PolicySearchResultItem
from app.schemas.analysis import (
    CaseAnalysisResponse,
    CaseChatResponse,
    AnalysisKnownFact,
    AnalysisMissingInfo,
)


class BaseAIProvider:
    """Abstract interface for AI reasoning engines."""

    def analyze_case(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
    ) -> CaseAnalysisResponse:
        raise NotImplementedError

    def answer_case_question(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
        question: str,
    ) -> CaseChatResponse:
        raise NotImplementedError


class DemoAIProvider(BaseAIProvider):
    """
    Deterministic rule-based reasoning engine operating in demo mode.
    Requires no external API keys or network calls.
    Derives its output directly from the case's actual state, evidence, and retrieved policies.
    """

    def analyze_case(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
    ) -> CaseAnalysisResponse:
        case_id = context["case_id"]
        product_name = context["product_name"]
        issue = context["issue_description"]
        status = context["status"]
        missing = context["missing_categories"]
        evidence_items = context["evidence"]

        # Known facts
        known_facts = [
            AnalysisKnownFact(
                category="USER_REPORTED",
                fact=f"Product '{product_name}' reported with issue: '{issue}'. Current case status: {status}.",
            )
        ]

        # Add facts from successfully extracted documents
        evidence_considered = []
        for ev in evidence_items:
            evidence_considered.append(f"{ev['filename']} ({ev['type']})")
            if ev["extraction_status"] == "COMPLETED" and ev["extracted_text_snippet"]:
                snippet = ev["extracted_text_snippet"][:150].replace("\n", " ")
                known_facts.append(
                    AnalysisKnownFact(
                        category="EXTRACTED_FROM_DOCUMENT",
                        fact=f"Extracted from {ev['filename']}: '{snippet}...'",
                    )
                )

        # Missing information
        missing_info = []
        if "INVOICE" in missing:
            missing_info.append(
                AnalysisMissingInfo(
                    item="Proof of Purchase (Invoice)",
                    impact="Required to establish warranty commencement date and retail jurisdiction.",
                )
            )
        if "REPAIR_RECEIPT" in missing:
            missing_info.append(
                AnalysisMissingInfo(
                    item="Prior Repair Receipts / Job Sheets",
                    impact="Crucial to substantiate the claim that the device underwent multiple unsuccessful repair attempts.",
                )
            )
        if "WARRANTY" in missing:
            missing_info.append(
                AnalysisMissingInfo(
                    item="Warranty Terms / Card",
                    impact="Useful to verify specific remedies, turnaround time commitments, and escalation contacts.",
                )
            )

        # Formulate recommendation and reasoning based on available vs missing evidence
        if "REPAIR_RECEIPT" in missing:
            recommended_step = (
                f"Collect and upload repair job sheets documenting the prior service visits for your {product_name}."
            )
            reasoning = (
                f"The case reports a recurring defect in {product_name}. However, without service center documentation "
                "verifying the dates and parts replaced during prior repair attempts, manufacturer escalations cannot "
                "verify repeated failure history."
            )
            suggested_action = "Upload prior service center receipts or job sheets."
        elif "INVOICE" in missing:
            recommended_step = (
                "Provide your original purchase invoice to verify active warranty eligibility."
            )
            reasoning = (
                "Service receipts confirm previous repair cycles, but proof of purchase is required to substantiate "
                "that the unit remains within the manufacturer's active limited warranty or consumer protection period."
            )
            suggested_action = "Upload original invoice or proof of purchase."
        else:
            recommended_step = (
                f"Prepare a formal escalation request for replacement or full refund under repeat defect guidelines."
            )
            reasoning = (
                f"Key supporting documents (invoice and repair history) are accounted for. The recurring defect in "
                f"{product_name} justifies an escalation under applicable policy standards rather than a third repair."
            )
            suggested_action = "Draft formal escalation notice to manufacturer support."

        uncertainty_notes = [
            "This recommendation was generated by ResolveAI in DEMO MODE using deterministic rules.",
            "Document contents have not been independently validated for authenticity.",
            "This analysis serves as an organizational aid and does not constitute formal legal counsel.",
        ]

        summary = (
            f"Case analysis for {product_name}: Status is {status}. "
            f"Identified {len(missing)} missing key evidence categories."
        )

        return CaseAnalysisResponse(
            case_id=case_id,
            engine_mode="demo",
            summary=summary,
            recommended_next_step=recommended_step,
            reasoning=reasoning,
            known_facts=known_facts,
            missing_information=missing_info,
            evidence_considered=evidence_considered,
            supporting_policy_sources=retrieved_policies,
            uncertainty_notes=uncertainty_notes,
            suggested_action=suggested_action,
            generated_at=datetime.now(timezone.utc),
        )

    def answer_case_question(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
        question: str,
    ) -> CaseChatResponse:
        case_id = context["case_id"]
        product_name = context["product_name"]
        issue = context["issue_description"]
        status = context["status"]

        # Formulate grounded response
        q_lower = question.lower()
        policy_summary = ""
        if retrieved_policies:
            top = retrieved_policies[0]
            policy_summary = f" Based on policy excerpt from '{top.source_title}', {top.passage[:200]}..."

        if any(w in q_lower for w in ["next", "step", "what should i do", "recommend"]):
            answer = (
                f"For your {product_name} (Status: {status}), your next priority should be ensuring all previous "
                f"repair receipts and purchase proof are attached. {policy_summary}"
            )
        elif any(w in q_lower for w in ["status", "where is", "progress"]):
            answer = (
                f"Your case is currently at status '{status}'. {len(context['timeline'])} timeline events "
                f"have been logged so far."
            )
        elif any(w in q_lower for w in ["refund", "replacement", "replace", "policy"]):
            answer = (
                f"Regarding remedies for {product_name}: Under applicable guidelines, devices that fail repeatedly "
                f"after two repair attempts may qualify for replacement or credit escalation rather than a third repair.{policy_summary}"
            )
        else:
            answer = (
                f"Regarding your query on {product_name} ('{issue}'): We are tracking your case under status '{status}'. "
                f"Grounded guidance suggests retaining all service documents to support your complaint.{policy_summary}"
            )

        distinctions = [
            f"User Fact: {product_name} has reported fault '{issue}'.",
            f"Case State: Current workflow status is '{status}'.",
            f"Policy Grounding: {len(retrieved_policies)} relevant policy passage(s) referenced.",
            "Engine Mode: Operating in deterministic Demo Mode without external AI API calls.",
        ]

        return CaseChatResponse(
            case_id=case_id,
            engine_mode="demo",
            question=question,
            answer=answer,
            distinction_notes=distinctions,
            supporting_policy_sources=retrieved_policies,
            generated_at=datetime.now(timezone.utc),
        )
