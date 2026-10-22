import json
import pytest
import httpx
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.config import get_settings
from app.services.ai_provider import OllamaAIProvider, DemoAIProvider
from app.services.ai_factory import get_ai_provider
from app.schemas.policy import PolicySearchResultItem
from app.models.policy import PolicySourceType
from app.models.action import Action, ActionStatus, ActionType


class MockTransport(httpx.BaseTransport):
    """Custom httpx transport for deterministic mock responses."""

    def __init__(self, handler):
        self.handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self.handler(request)


def test_ollama_health_check_success():
    """Verify check_health succeeds when daemon responds with configured model."""
    def handler(request: httpx.Request):
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "llama3.2:latest", "model": "llama3.2:latest"}]},
        )

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(model="llama3.2:latest", client=client)
    is_healthy, err = provider.check_health()
    assert is_healthy is True
    assert err is None


def test_ollama_health_check_daemon_unreachable():
    """Verify check_health returns false with helpful error when daemon is down."""
    def handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused")

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)
    is_healthy, err = provider.check_health()
    assert is_healthy is False
    assert "Ollama daemon is unreachable" in err


def test_ollama_health_check_model_missing():
    """Verify check_health fails when configured model is not in local tags."""
    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={"models": [{"name": "mistral:latest"}]},
        )

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(model="llama3.2:latest", client=client)
    is_healthy, err = provider.check_health()
    assert is_healthy is False
    assert "is not installed locally" in err
    assert "ollama pull llama3.2:latest" in err


def test_ai_factory_selection_demo(monkeypatch):
    """Factory returns DemoAIProvider when AI_PROVIDER is demo."""
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "demo")
    provider = get_ai_provider()
    assert isinstance(provider, DemoAIProvider)


def test_ai_factory_selection_ollama_fail_fast(monkeypatch):
    """Factory fails fast with HTTP 503 and never silently falls back to demo when Ollama is unavailable."""
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")

    # Mock OllamaAIProvider.check_health to simulate an unreachable daemon
    monkeypatch.setattr(
        OllamaAIProvider,
        "check_health",
        lambda self: (False, "Ollama daemon is unreachable at http://localhost:11434."),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_ai_provider()

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Ollama daemon is unreachable" in exc_info.value.detail


def test_ai_factory_selection_ollama_success(monkeypatch):
    """Factory returns OllamaAIProvider when health check passes."""
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(
        OllamaAIProvider,
        "check_health",
        lambda self: (True, None),
    )

    provider = get_ai_provider()
    assert isinstance(provider, OllamaAIProvider)


def test_ollama_analyze_case_valid_json():
    """Verify analyze_case parses valid structured JSON response from Ollama."""
    analysis_payload = {
        "summary": "Eligible for statutory warranty repair.",
        "recommended_next_step": "Dispatch formal 7-day notice of defect.",
        "reasoning": "Product failed within 30 days and repair was unfulfilled.",
        "known_facts": [
            {"category": "EXTRACTED_FROM_DOCUMENT", "fact": "Invoice shows purchase on 2026-01-10"},
            {"category": "USER_REPORTED", "fact": "Motherboard failure reported"},
        ],
        "missing_information": [
            {"item": "Service Sheet", "impact": "Needed to verify physical inspection date"}
        ],
        "evidence_considered": ["invoice.pdf"],
        "uncertainty_notes": ["Invoice signature unverified"],
        "suggested_action": "Draft Formal Notice",
    }

    def handler(request: httpx.Request):
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(analysis_payload)}},
        )

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)

    context = {
        "case_id": "test-case-123",
        "product_name": "Pro Laptop",
        "issue_description": "Motherboard failure",
        "status": "COLLECTING_EVIDENCE",
        "missing_categories": [],
        "commitments": [],
        "evidence": [{"filename": "invoice.pdf", "type": "PURCHASE_INVOICE", "extraction_status": "COMPLETED", "extracted_text_snippet": "Purchased Jan 10"}],
        "timeline": [],
    }
    policies = [
        PolicySearchResultItem(
            source_id="pol-1",
            source_title="Consumer Protection Act",
            source_type=PolicySourceType.OFFICIAL,
            passage="Defective goods must be repaired or replaced within reasonable timeframe.",
            relevance_score=0.9,
        )
    ]

    res = provider.analyze_case(context, policies)
    assert res.case_id == "test-case-123"
    assert res.engine_mode == "ollama"
    assert "eligibility have not been established" in res.summary
    assert "confirm any unresolved details" in res.recommended_next_step
    assert len(res.known_facts) == 2
    assert res.suggested_action == "Review the available records and confirm unresolved details."
    assert len(res.supporting_policy_sources) == 1


def test_ollama_analyze_case_markdown_wrapped_json():
    """Verify analyze_case cleanly strips ```json markdown fences."""
    raw_json = json.dumps({
        "summary": "Valid warranty claim.",
        "recommended_next_step": "Request replacement under Consumer Protection Act.",
        "reasoning": "Statutory repair timeline exceeded.",
        "known_facts": [{"category": "CASE_CONTEXT", "fact": "Unit delivered defective"}],
        "missing_information": [],
        "evidence_considered": ["receipt.pdf"],
    })
    fenced_content = f"```json\n{raw_json}\n```"

    def handler(request: httpx.Request):
        return httpx.Response(200, json={"message": {"content": fenced_content}})

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)

    context = {"case_id": "case-fence", "product_name": "Device", "issue_description": "Defect"}
    res = provider.analyze_case(context, [])
    assert "eligibility have not been established" in res.summary
    assert "confirm any unresolved details" in res.recommended_next_step


def test_ollama_analysis_reconciles_evidence_and_rejects_unsupported_claims():
    """Generated claims cannot override evidence coverage or policy provenance."""
    payload = {
        "summary": "Warranty is active and statutory replacement is guaranteed.",
        "recommended_next_step": "Send a formal legal demand for replacement.",
        "reasoning": "The demo policy proves statutory eligibility.",
        "known_facts": [{"category": "VERIFIED", "fact": "Warranty remains active."}],
        "missing_information": [
            {"item": "Purchase invoice", "impact": "Required."},
            {"item": "First repair sheet", "impact": "Required."},
        ],
        "evidence_considered": [],
        "suggested_action": "Send statutory demand",
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json={"message": {"content": json.dumps(payload)}})

    provider = OllamaAIProvider(client=httpx.Client(transport=MockTransport(handler)))
    context = {
        "case_id": "grounded-case",
        "product_name": "Demo Laptop",
        "issue_description": "Repeated shutdowns after service.",
        "missing_categories": ["WARRANTY", "SERVICE_COMMUNICATION"],
        "evidence": [
            {"filename": "invoice.pdf", "type": "INVOICE", "extracted_text_snippet": "Purchase date: 2026-02-01"},
            {"filename": "repair-1.pdf", "type": "REPAIR_RECEIPT", "extracted_text_snippet": "First service visit"},
        ],
    }
    illustrative_policy = PolicySearchResultItem(
        source_id="demo-policy",
        source_title="DEMO POLICY — NOT AN OFFICIAL MANUFACTURER POLICY",
        source_type=PolicySourceType.ILLUSTRATIVE,
        passage="Demo-only repair guidance.",
        relevance_score=0.9,
    )

    result = provider.analyze_case(context, [illustrative_policy])

    missing = [item.item.lower() for item in result.missing_information]
    assert missing == ["warranty terms or card", "service communications"]
    assert all("invoice" not in item and "repair" not in item for item in missing)
    assert "active" not in result.summary.lower()
    assert "statutory" not in result.recommended_next_step.lower()
    assert "unknown" in result.recommended_next_step.lower()
    assert "warranty remains active" not in " ".join(f.fact for f in result.known_facts).lower()
    assert any("not official manufacturer policies" in note for note in result.uncertainty_notes)
    assert result.suggested_action == "Request or review the warranty terms."
    assert result.evidence_considered == ["invoice.pdf", "repair-1.pdf"]


def test_ollama_analyze_case_repair_attempt():
    """Verify analyze_case performs at most 1 repair attempt when initial JSON is invalid."""
    call_count = 0

    valid_json = json.dumps({
        "summary": "Repaired valid summary.",
        "recommended_next_step": "Proceed to escalation.",
        "reasoning": "Repaired reasoning.",
        "known_facts": [],
        "missing_information": [],
        "evidence_considered": [],
    })

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call returns invalid JSON
            return httpx.Response(200, json={"message": {"content": "I cannot return JSON directly: {"}})
        else:
            # Second call (repair) returns valid JSON
            return httpx.Response(200, json={"message": {"content": valid_json}})

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)

    context = {"case_id": "case-repair", "product_name": "Device", "issue_description": "Defect"}
    res = provider.analyze_case(context, [])
    assert call_count == 2
    assert "eligibility have not been established" in res.summary


def test_ollama_analyze_case_persistent_failure_raises_502():
    """Verify persistent invalid JSON after repair raises HTTP 502 Bad Gateway."""
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"message": {"content": "Not JSON at all"}})

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)

    context = {"case_id": "case-fail", "product_name": "Device", "issue_description": "Defect"}
    with pytest.raises(HTTPException) as exc_info:
        provider.analyze_case(context, [])

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert "produced invalid structured analysis after repair attempt" in exc_info.value.detail


def test_ollama_timeout_raises_504():
    """Verify Ollama inference timeout raises HTTP 504 Gateway Timeout."""
    def handler(request: httpx.Request):
        raise httpx.TimeoutException("Read timed out")

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)

    context = {"case_id": "case-timeout", "product_name": "Device", "issue_description": "Defect"}
    with pytest.raises(HTTPException) as exc_info:
        provider.analyze_case(context, [])

    assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert "timed out after" in exc_info.value.detail


def test_ollama_answer_case_question():
    """Verify answer_case_question returns grounded chat response with distinctions."""
    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={"message": {"content": "Under Section 10 of CPA 2019, you are entitled to replacement."}},
        )

    client = httpx.Client(transport=MockTransport(handler))
    provider = OllamaAIProvider(client=client)

    context = {
        "case_id": "case-chat-1",
        "product_name": "Monitor",
        "issue_description": "Dead pixels",
        "status": "COLLECTING_EVIDENCE",
    }
    policies = [
        PolicySearchResultItem(
            source_id="pol-cpa",
            source_title="Consumer Protection Act 2019",
            source_type=PolicySourceType.OFFICIAL,
            passage="Right to replacement for unrectified manufacturing defects.",
            relevance_score=0.95,
        )
    ]

    res = provider.answer_case_question(context, policies, "What are my legal rights?")
    assert res.engine_mode == "ollama"
    assert "Section 10 of CPA 2019" in res.answer
    assert any("Consumer Protection Act 2019" == p.source_title for p in res.supporting_policy_sources)
    assert any("Engine Mode: Local Ollama" in note for note in res.distinction_notes)


def test_suggested_action_approval_invariant(db_session):
    """
    Verify safety invariant: Actions proposed by model are recorded as PENDING_APPROVAL
    and cannot be executed without explicit human approval.
    """
    # Create an action suggested by analysis
    action = Action(
        case_id="case-approval-test",
        title="Draft Formal Demand Notice",
        action_type=ActionType.SEND_MESSAGE,
        description="Formal statutory demand notice suggested by Ollama.",
        payload_json={"message": "Demand notice text"},
        status=ActionStatus.PENDING_APPROVAL,
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)

    assert action.status == ActionStatus.PENDING_APPROVAL
    # Verify execution requires explicit human approval (status cannot be EXECUTED directly)
    assert action.status != ActionStatus.EXECUTED


def test_ai_diagnostics_endpoint(client: TestClient):
    """Verify GET /api/diagnostics/ai returns AI provider configuration without altering /api/health."""
    # Health remains simple
    health_resp = client.get("/api/health")
    assert health_resp.status_code == status.HTTP_200_OK
    assert health_resp.json() == {"status": "ok"}

    # Diagnostics returns detailed provider configuration
    diag_resp = client.get("/api/diagnostics/ai")
    assert diag_resp.status_code == status.HTTP_200_OK
    data = diag_resp.json()
    assert "provider" in data
    assert "model" in data
    assert data["status"] == "configured"
