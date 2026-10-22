import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Generator
import httpx
from fastapi import HTTPException, status
from app.config import get_settings
from app.schemas.policy import PolicySearchResultItem
from app.schemas.analysis import (
    CaseAnalysisResponse,
    CaseChatResponse,
    AnalysisKnownFact,
    AnalysisMissingInfo,
)

logger = logging.getLogger(__name__)


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
        commitments = context.get("commitments", [])

        # Known facts
        known_facts = [
            AnalysisKnownFact(
                category="USER_REPORTED",
                fact=f"Product '{product_name}' reported with issue: '{issue}'. Current case status: {status}.",
            )
        ]

        # Add facts strictly from relevant extracted documents, clearly distinguishing extracted text from verified facts
        evidence_considered = []
        for ev in evidence_items:
            rel_status = ev.get("relevance_status", "UNVERIFIED")
            evidence_considered.append(f"{ev['filename']} ({ev['type']} - {rel_status})")

            if rel_status == "MISMATCH":
                # Explicitly note suspected mismatch without admitting content as case fact
                known_facts.append(
                    AnalysisKnownFact(
                        category="EVIDENCE_STATUS",
                        fact=f"Uploaded file '{ev['filename']}' appears unrelated to {product_name} repair. Content excluded from verified facts.",
                    )
                )
            elif ev["extraction_status"] == "COMPLETED" and ev["extracted_text_snippet"]:
                snippet = ev["extracted_text_snippet"][:150].replace("\n", " ")
                # Conservative attribution: explicitly state it is extracted unverified text
                fact_prefix = "Extracted text snippet" if rel_status == "RELEVANT" else "Unverified text snippet"
                known_facts.append(
                    AnalysisKnownFact(
                        category="EXTRACTED_FROM_DOCUMENT",
                        fact=f"{fact_prefix} from {ev['filename']} (authenticity/relevance not independently certified): '{snippet}'",
                    )
                )
            else:
                known_facts.append(
                    AnalysisKnownFact(
                        category="EVIDENCE_STATUS",
                        fact=f"Attachment '{ev['filename']}' attached under category {ev['type']} (Relevance not verified).",
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

        # Match recommendation branches to terms in the actual retrieved passages.
        # A citation alone does not make a generic recommendation policy-grounded.
        relevant_terms = (
            ("job sheet", "repair receipt", "service documentation")
            if "REPAIR_RECEIPT" in missing
            else ("invoice", "proof of purchase", "purchase documentation")
            if "INVOICE" in missing
            else ("replacement", "refund", "escalation")
        )
        policy_basis = next(
            (
                source for source in retrieved_policies
                if any(term in source.passage.lower() for term in relevant_terms)
            ),
            None,
        )
        if "REPAIR_RECEIPT" in missing:
            if policy_basis:
                recommended_step = (
                    f"Collect the prior repair job sheets called for in the retrieved {policy_basis.source_type.value.lower()} "
                    f"passage '{policy_basis.source_title}', and check that they describe each service visit."
                )
            else:
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
            if policy_basis:
                recommended_step = (
                    f"Locate the purchase invoice referenced by the retrieved {policy_basis.source_type.value.lower()} "
                    f"passage '{policy_basis.source_title}'; use it to verify the purchase date against the warranty terms."
                )
            else:
                recommended_step = "Locate the purchase invoice and compare its date with the applicable warranty terms."
            reasoning = (
                "Repair documentation is attached, but the original purchase invoice is not. The purchase date and "
                "applicable warranty terms therefore remain unverified."
            )
            suggested_action = "Upload original invoice or proof of purchase."
        else:
            if any("replacement" in str(c).lower() for c in commitments):
                recommended_step = (
                    "Provider has offered a replacement authorization. Review the available resolution terms "
                    "and decide whether to draft an appropriate response to confirm replacement details."
                )
                reasoning = (
                    "The service provider has offered a replacement authorization. Core claim documents "
                    "(purchase invoice and repair job sheets) are on file. Review the terms before finalizing next steps."
                )
                suggested_action = "Review the provider replacement offer and draft a response to confirm replacement logistics."
            elif any("refund" in str(c).lower() or "credit note" in str(c).lower() for c in commitments):
                recommended_step = (
                    "Provider has offered a refund or credit note. Review the settlement terms and decide whether to draft an appropriate response."
                )
                reasoning = (
                    "A commercial refund or credit note was recorded in the provider response. Review its terms; no legal entitlement is inferred."
                )
                suggested_action = "Review the stated settlement terms and confirm any unresolved details."
            elif commitments:
                recommended_step = (
                    f"Provider recorded commitment: '{commitments[0]}'. Review the available resolution terms and decide whether to draft an appropriate response."
                )
                reasoning = f"An actionable commitment was recorded from the service provider: '{commitments[0]}'."
                suggested_action = "Review the provider commitment and determine next steps."
            elif policy_basis:
                recommended_step = (
                    f"The retrieved {policy_basis.source_type.value.lower()} passage '{policy_basis.source_title}' "
                    "is available as a reference. Compare records with warranty terms before deciding on next steps."
                )
                reasoning = (
                    "Evidence categories are represented, but this does not verify document authenticity, "
                    "warranty coverage, or eligibility for a particular remedy."
                )
                suggested_action = "Review the records and confirm warranty terms before deciding on a remedy."
            else:
                recommended_step = (
                    "Review the attached purchase and service records and confirm applicable warranty terms with the provider before deciding on a remedy."
                )
                reasoning = (
                    "Evidence categories are represented, but this does not verify document authenticity, "
                    "warranty coverage, or eligibility for a particular remedy."
                )
                suggested_action = "Review the records and confirm warranty terms before deciding on a remedy."

        if policy_basis:
            provenance = policy_basis.source_type.value.lower()
            if policy_basis.source_type.value == "ILLUSTRATIVE":
                provenance = "illustrative demo (not official or legally authoritative)"
            reasoning += (
                f" Retrieved {provenance} passage from '{policy_basis.source_title}': "
                f"{policy_basis.passage[:500]}"
            )
        else:
            reasoning += " No matching policy passage was found; this recommendation is based on case organization only."

        uncertainty_notes = [
            "This recommendation was generated by ResolveAI in DEMO MODE using deterministic rules.",
            "Document contents have not been independently validated for authenticity.",
            "Illustrative demo policy sources are not official manufacturer policies or legal authorities.",
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
            if retrieved_policies:
                source = retrieved_policies[0]
                answer = (
                    f"The retrieved {source.source_type.value.lower()} passage from '{source.source_title}' says: "
                    f"{source.passage[:500]}"
                )
            else:
                answer = "I found no matching policy passage, so I cannot ground a remedy answer in the stored library."
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


def _clean_json_markdown(text: str) -> str:
    """Strip markdown code blocks if the model wrapped the JSON in triple backticks."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


class OllamaAIProvider(BaseAIProvider):
    """
    Local LLM reasoning engine utilizing an Ollama HTTP service.
    Directly interfaces with Ollama's /api/chat endpoint to run bounded,
    grounded analysis and chat without third-party network egress.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        client: Optional[httpx.Client] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS
        self.connect_timeout = (
            connect_timeout if connect_timeout is not None else settings.OLLAMA_CONNECT_TIMEOUT_SECONDS
        )
        self._client = client

    @contextmanager
    def _client_scope(self) -> Generator[httpx.Client, None, None]:
        if self._client is not None:
            yield self._client
        else:
            with httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=self.connect_timeout),
            ) as client:
                yield client

    def check_health(self) -> Tuple[bool, Optional[str]]:
        """Verify that the Ollama service is reachable and the configured model is installed."""
        try:
            with self._client_scope() as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False, f"Ollama health check returned HTTP {resp.status_code}."
                tags_data = resp.json()
                models = tags_data.get("models", [])
                installed_names = []
                for m in models:
                    if isinstance(m, dict):
                        if m.get("name"):
                            installed_names.append(m["name"])
                        if m.get("model"):
                            installed_names.append(m["model"])

                target = self.model.lower()
                target_base = target.split(":")[0]
                found = any(
                    target == n.lower() or target_base == n.lower().split(":")[0]
                    for n in installed_names
                )
                if not found:
                    return False, (
                        f"Configured Ollama model '{self.model}' is not installed locally. "
                        f"Available models: {installed_names}. Run 'ollama pull {self.model}'."
                    )
                return True, None
        except httpx.ConnectError:
            return False, f"Ollama daemon is unreachable at {self.base_url}. Please ensure Ollama is running."
        except httpx.TimeoutException:
            return False, f"Ollama health check timed out at {self.base_url}."
        except Exception as e:
            return False, f"Ollama health check failed: {str(e)}"

    def _call_ollama(self, messages: List[Dict[str, str]], json_format: bool = False) -> str:
        """Dispatch a chat completion request to the Ollama API."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }
        if json_format:
            payload["format"] = "json"

        try:
            with self._client_scope() as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Ollama returned error: {data['error']}",
                    )
                content = data.get("message", {}).get("content", "").strip()
                if not content:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Ollama returned an empty response.",
                    )
                return content
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to Ollama at {self.base_url}. Ensure the service is active.",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Ollama inference timed out after {self.timeout}s.",
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama server returned error status {e.response.status_code}.",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ollama request error: {str(e)}",
            )

    def _build_analysis_prompt(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
    ) -> str:
        product_name = context.get("product_name", "Product")
        issue = context.get("issue_description", "")
        status_val = context.get("status", "UNKNOWN")
        missing_cats = context.get("missing_categories", [])
        commitments = context.get("commitments", [])
        evidence_list = context.get("evidence", [])
        timeline = context.get("timeline", [])

        # Format timeline (limit to 10 most recent if long)
        tl_lines = []
        for e in timeline[-10:]:
            tl_lines.append(f"- [{e.get('timestamp', '')[:10]}] {e.get('event_type')}: {e.get('description')}")
        timeline_str = "\n".join(tl_lines) if tl_lines else "No timeline events recorded yet."

        # Format evidence attachments with honest OCR disclosure
        ev_lines = []
        for ev in evidence_list:
            fn = ev.get("filename", "unknown")
            et = ev.get("type", "OTHER")
            status_ext = ev.get("extraction_status", "")
            snippet = ev.get("extracted_text_snippet")
            rel = ev.get("relevance_status", "UNVERIFIED")

            if snippet and status_ext == "COMPLETED" and rel != "MISMATCH":
                ev_lines.append(
                    f"- Attachment: '{fn}' (Category: {et}, Relevance: {rel})\n  Extracted text snippet: \"{snippet}\""
                )
            elif status_ext == "UNSUPPORTED" or any(fn.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"]):
                ev_lines.append(
                    f"- Attachment: '{fn}' (Category: {et})\n  [Image format attachment: OCR is not supported; document text is unextracted. Do not fabricate contents.]"
                )
            else:
                ev_lines.append(f"- Attachment: '{fn}' (Category: {et}, Extraction status: {status_ext})")
        evidence_str = "\n".join(ev_lines) if ev_lines else "No evidence documents attached."

        # Keep source provenance visible; illustrative demo rules are not official policy.
        pol_lines = []
        for p in retrieved_policies:
            pol_type = p.source_type if isinstance(p.source_type, str) else p.source_type.value
            provenance = (
                "ILLUSTRATIVE DEMO ONLY — NOT OFFICIAL POLICY"
                if pol_type == "ILLUSTRATIVE"
                else pol_type
            )
            pol_lines.append(
                f"- Citation: '{p.source_title}' (Provenance: {provenance}, Jurisdiction: {p.jurisdiction or 'India'})\n  Passage: \"{p.passage}\""
            )
        policies_str = "\n".join(pol_lines) if pol_lines else "No matching policy passages found."

        commitments_str = ", ".join(commitments) if commitments else "None recorded."
        missing_str = ", ".join(missing_cats) if missing_cats else "None missing from baseline checklist."

        return (
            f"Case Subject: {product_name}\n"
            f"Reported Fault: {issue}\n"
            f"Current Workflow Status: {status_val}\n"
            f"Missing Baseline Evidence Categories: {missing_str}\n"
            f"Recorded Provider Commitments: {commitments_str}\n\n"
            f"Timeline History:\n{timeline_str}\n\n"
            f"Evidence Documents:\n{evidence_str}\n\n"
            f"Retrieved Policy Sources (provenance is authoritative):\n{policies_str}\n\n"
            "Task: Generate a case-aware structured evaluation in valid JSON strictly matching this schema:\n"
            "{\n"
            '  "summary": "Concise 1-2 sentence overview of the case status and claim viability.",\n'
            '  "recommended_next_step": "Specific, actionable single next step for the consumer.",\n'
            '  "reasoning": "Explain what the case records establish and what remains unknown.",\n'
            '  "known_facts": [\n'
            '    {"category": "USER_REPORTED | EXTRACTED_FROM_DOCUMENT | POLICY_STANDARD", "fact": "Established fact."}\n'
            "  ],\n"
            '  "missing_information": [\n'
            '    {"item": "Document or fact still missing", "impact": "Why this info is necessary"}\n'
            "  ],\n"
            '  "evidence_considered": ["list of attachment names evaluated"],\n'
            '  "uncertainty_notes": ["explicit notes regarding unverified authenticity or limitations"],\n'
            '  "suggested_action": "Optional concrete action title to draft if next step requires escalation"\n'
            "}\n"
            "Constraints:\n"
            "1. Output ONLY valid JSON.\n"
            "2. Do not make legal, warranty-coverage, or eligibility conclusions unless directly supported by an OFFICIAL source and case records.\n"
            "3. If proof of purchase or repair job sheets are absent, recommend collecting them before formal escalation.\n"
            "4. Clearly distinguish extracted unverified text from verified facts.\n"
            "5. ILLUSTRATIVE sources are fictional demo examples and must never be described as official, statutory, or legally binding.\n"
            "6. Treat Missing Baseline Evidence Categories as category coverage only; never call an attached category absent."
        )

    def _validate_and_build_analysis(
        self,
        data: Dict[str, Any],
        case_id: str,
        retrieved_policies: List[PolicySearchResultItem],
        context: Dict[str, Any],
    ) -> CaseAnalysisResponse:
        summary = str(data.get("summary") or "").strip()
        if not summary:
            raise ValueError("Missing 'summary' in model analysis output.")

        recommended_next_step = str(data.get("recommended_next_step") or "").strip()
        if not recommended_next_step:
            raise ValueError("Missing 'recommended_next_step' in model analysis output.")

        reasoning = str(data.get("reasoning") or "").strip()
        if not reasoning:
            raise ValueError("Missing 'reasoning' in model analysis output.")

        # Model-authored fact statements are not evidence. Rebuild this section from
        # the user report and explicitly attributed extracted snippets.
        known_facts: List[AnalysisKnownFact] = [
            AnalysisKnownFact(
                category="USER_REPORTED",
                fact=f"User reports: {context.get('issue_description', '')}",
            )
        ]
        for evidence in context.get("evidence", []):
            snippet = evidence.get("extracted_text_snippet")
            if snippet:
                known_facts.append(AnalysisKnownFact(
                    category="EXTRACTED_FROM_DOCUMENT",
                    fact=(f"Unverified extracted text from {evidence.get('filename', 'attachment')}: "
                          f"{snippet[:400]}"),
                ))

        # Never trust generated missing-document claims. Build them from the actual
        # evidence category coverage supplied by CaseContextService.
        missing_info: List[AnalysisMissingInfo] = []
        missing_categories = set(context.get("missing_categories", []))
        for category, label, impact in (
            ("INVOICE", "Proof of purchase (invoice)", "Useful to establish the purchase date; warranty coverage remains unverified."),
            ("REPAIR_RECEIPT", "Repair receipts or job sheets", "Useful to document service visits and reported repair history."),
            ("WARRANTY", "Warranty terms or card", "Needed to review the applicable coverage terms; eligibility remains unknown."),
            ("SERVICE_COMMUNICATION", "Service communications", "Useful to document messages exchanged with the provider."),
        ):
            if category in missing_categories:
                missing_info.append(AnalysisMissingInfo(item=label, impact=impact))

        raw_evidence = data.get("evidence_considered", [])
        evidence_considered: List[str] = []
        if isinstance(raw_evidence, list):
            evidence_considered = [str(e).strip() for e in raw_evidence if str(e).strip()]
        elif isinstance(raw_evidence, str) and raw_evidence.strip():
            evidence_considered = [raw_evidence.strip()]

        uncertainty_notes = [
            f"This recommendation was generated by ResolveAI using local Ollama model '{self.model}'.",
            "Document contents have not been independently validated for authenticity.",
            "Evidence category representation does not guarantee statutory remedy eligibility.",
            "Image attachments lack OCR text extraction; contents remain unverified.",
            "This analysis serves as an organizational aid and does not constitute formal legal counsel.",
        ]
        if any(
            (p.source_type.value if hasattr(p.source_type, "value") else p.source_type) == "ILLUSTRATIVE"
            for p in retrieved_policies
        ):
            uncertainty_notes.append("Illustrative demo policy sources are not official manufacturer policies or legal authorities.")
        # Use a deterministic next step so unsupported generated assertions cannot
        # become a recommendation or be copied into a downstream action draft.
        product = str(context.get("product_name") or "the product")
        if "REPAIR_RECEIPT" in missing_categories:
            recommended_next_step = f"Collect and attach available repair receipts or job sheets for {product}."
            suggested_action = "Request or organize repair visit records."
        elif "INVOICE" in missing_categories:
            recommended_next_step = f"Locate and attach proof of purchase for {product}; the purchase date and warranty coverage are currently unknown."
            suggested_action = "Request or organize proof of purchase."
        elif "WARRANTY" in missing_categories:
            recommended_next_step = f"Locate the warranty terms for {product} so coverage can be reviewed; eligibility is currently unknown."
            suggested_action = "Request or review the warranty terms."
        else:
            recommended_next_step = f"Review the attached records for {product} and confirm any unresolved details with the provider before deciding on a remedy."
            suggested_action = "Review the available records and confirm unresolved details."
        reasoning = (
            "These next steps reflect the case record and evidence category coverage only. "
            "Uploaded text is unverified, warranty coverage and legal eligibility are unknown, "
            "and no remedy is concluded."
        )
        summary = (
            f"Case records for {product} are organized for review. "
            "Warranty coverage and remedy eligibility have not been established."
        )
        evidence_considered = [str(ev.get("filename")) for ev in context.get("evidence", []) if ev.get("filename")]

        return CaseAnalysisResponse(
            case_id=case_id,
            engine_mode="ollama",
            summary=summary,
            recommended_next_step=recommended_next_step,
            reasoning=reasoning,
            known_facts=known_facts,
            missing_information=missing_info,
            evidence_considered=evidence_considered,
            supporting_policy_sources=retrieved_policies,
            uncertainty_notes=uncertainty_notes,
            suggested_action=suggested_action,
            generated_at=datetime.now(timezone.utc),
        )

    def analyze_case(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
    ) -> CaseAnalysisResponse:
        case_id = context["case_id"]
        system_prompt = (
            "You are ResolveAI's grounded case analysis assistant for consumer repair disputes. "
            "Evaluate the case records and retrieved policies objectively. "
            "Output strictly valid JSON matching the specified schema with no surrounding text."
        )
        user_prompt = self._build_analysis_prompt(context, retrieved_policies)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_output = self._call_ollama(messages, json_format=True)
        try:
            cleaned = _clean_json_markdown(raw_output)
            parsed_data = json.loads(cleaned)
            return self._validate_and_build_analysis(parsed_data, case_id, retrieved_policies, context)
        except (json.JSONDecodeError, ValueError) as first_err:
            logger.warning(
                "Ollama initial output parse failed: %s. Initiating bounded repair attempt.",
                first_err,
            )
            repair_messages = messages + [
                {"role": "assistant", "content": raw_output},
                {
                    "role": "user",
                    "content": (
                        "The previous output was invalid JSON. Return ONLY valid raw JSON with keys: "
                        "'summary', 'recommended_next_step', 'reasoning', 'known_facts', "
                        "'missing_information', 'evidence_considered', 'uncertainty_notes', 'suggested_action'. "
                        "Do not include conversational text or markdown codeblocks."
                    ),
                },
            ]
            repaired_raw = self._call_ollama(repair_messages, json_format=True)
            try:
                cleaned_repaired = _clean_json_markdown(repaired_raw)
                repaired_data = json.loads(cleaned_repaired)
                return self._validate_and_build_analysis(repaired_data, case_id, retrieved_policies, context)
            except Exception as final_err:
                logger.error("Ollama repair attempt failed: %s", final_err)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ollama local model '{self.model}' produced invalid structured analysis after repair attempt: {str(final_err)}",
                )

    def answer_case_question(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
        question: str,
    ) -> CaseChatResponse:
        case_id = context["case_id"]
        product_name = context.get("product_name", "Product")
        issue = context.get("issue_description", "")
        status_val = context.get("status", "UNKNOWN")

        system_prompt = (
            "You are ResolveAI's intelligent, grounded repair-resolution assistant for Indian consumer disputes. "
            "Answer the consumer's question accurately using ONLY the provided case facts, timeline, "
            "evidence snippets, and retrieved policy or reference passages. "
            "Rules:\n"
            "1. Do not invent legal rights, warranties, or remedies not supported by the provided text.\n"
            "2. Note that image attachments do not have OCR text extraction; do not fabricate image details.\n"
            "3. Keep your response concise, objective, and helpful.\n"
            "4. Treat ILLUSTRATIVE sources as fictional demo material, never as official policy or legal authority. "
            "Clearly distinguish case records, extracted unverified text, official sources, general guidance, and illustrative material."
        )

        user_prompt = self._build_chat_prompt(context, retrieved_policies, question)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_answer = self._call_ollama(messages, json_format=False)
        answer = raw_answer.strip()
        if not answer:
            answer = "I was unable to formulate an answer from the provided case records and policy sources."

        distinctions = [
            f"User Fact: {product_name} reported fault '{issue}'.",
            f"Case State: Current workflow status is '{status_val}'.",
            f"Policy Grounding: {len(retrieved_policies)} relevant policy passage(s) referenced.",
            f"Engine Mode: Local Ollama inference using '{self.model}'.",
        ]

        return CaseChatResponse(
            case_id=case_id,
            engine_mode="ollama",
            question=question,
            answer=answer,
            distinction_notes=distinctions,
            supporting_policy_sources=retrieved_policies,
            generated_at=datetime.now(timezone.utc),
        )

    def _build_chat_prompt(
        self,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
        question: str,
    ) -> str:
        product_name = context.get("product_name", "Product")
        issue = context.get("issue_description", "")
        status_val = context.get("status", "UNKNOWN")
        commitments = context.get("commitments", [])
        evidence_list = context.get("evidence", [])
        timeline = context.get("timeline", [])

        tl_lines = [f"- {e.get('description')}" for e in timeline[-6:]]
        timeline_str = "\n".join(tl_lines) if tl_lines else "None recorded."

        ev_lines = []
        for ev in evidence_list:
            snippet = ev.get("extracted_text_snippet")
            fn = ev.get("filename")
            if snippet:
                ev_lines.append(f"- {fn}: \"{snippet[:200]}\"")
            else:
                ev_lines.append(f"- {fn}: [No text extracted / Image attachment]")
        evidence_str = "\n".join(ev_lines) if ev_lines else "No evidence documents attached."

        pol_lines = []
        for p in retrieved_policies:
            source_type = p.source_type if isinstance(p.source_type, str) else p.source_type.value
            provenance = (
                "ILLUSTRATIVE DEMO ONLY — NOT OFFICIAL POLICY"
                if source_type == "ILLUSTRATIVE"
                else source_type
            )
            pol_lines.append(f"- {p.source_title} (Provenance: {provenance}): \"{p.passage}\"")
        policies_str = "\n".join(pol_lines) if pol_lines else "No matching policy or reference passages found."

        commitments_str = ", ".join(commitments) if commitments else "None recorded."

        return (
            f"Case: {product_name} | Status: {status_val}\n"
            f"Reported Issue: {issue}\n"
            f"Provider Commitments: {commitments_str}\n"
            f"Recent Timeline:\n{timeline_str}\n\n"
            f"Evidence Snippets:\n{evidence_str}\n\n"
            f"Policy and Reference Sources:\n{policies_str}\n\n"
            f"Consumer Question: {question}\n\n"
            "Answer the question clearly and directly based on the above information."
        )
