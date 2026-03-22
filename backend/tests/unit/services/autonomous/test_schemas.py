"""Tests for autonomous pipeline Pydantic schemas."""

from app.services.autonomous.schemas import (
    ApprovalPattern,
    ApproveRequest,
    BulkActionRequest,
    DraftEmail,
    EditDraftRequest,
    LeadSource,
    PipelineStats,
    QueueFilter,
    QueueItem,
    QueueStatus,
    RawLead,
    RejectRequest,
    RunConfig,
    RunStatus,
    RunSummary,
)


class TestRunConfig:
    def test_defaults(self) -> None:
        config = RunConfig()
        assert config.prospect_limit == 25
        assert config.credit_budget == 250
        assert LeadSource.APOLLO in config.sources
        assert LeadSource.HUBSPOT in config.sources

    def test_custom_config(self) -> None:
        config = RunConfig(
            sources=[LeadSource.APOLLO],
            prospect_limit=10,
            credit_budget=100,
            verticals=["higher_ed"],
        )
        assert config.prospect_limit == 10
        assert len(config.sources) == 1


class TestRawLead:
    def test_minimal(self) -> None:
        lead = RawLead(email="test@example.com", source=LeadSource.APOLLO)
        assert lead.email == "test@example.com"
        assert lead.source == LeadSource.APOLLO
        assert lead.name is None

    def test_full(self) -> None:
        lead = RawLead(
            email="jane@university.edu",
            first_name="Jane",
            last_name="Doe",
            title="Director of AV",
            company="State University",
            industry="higher education",
            source=LeadSource.HUBSPOT,
            source_id="12345",
        )
        assert lead.company == "State University"
        assert lead.source_id == "12345"


class TestDraftEmail:
    def test_creation(self) -> None:
        draft = DraftEmail(
            subject="Quick question",
            body="Hi Jane, noticed your team records lectures manually.",
            pain_point="manual_recording",
        )
        assert draft.methodology == "challenger"
        assert "Jane" in draft.body


class TestQueueItem:
    def test_defaults(self) -> None:
        item = QueueItem(
            run_id="run-123",
            lead_email="test@example.com",
            lead_source=LeadSource.APOLLO,
        )
        assert item.status == QueueStatus.PENDING
        assert item.qualification_score == 0.0
        assert item.is_atl is False
        assert item.email_methodology == "challenger"

    def test_learning_signals_nullable(self) -> None:
        item = QueueItem(
            run_id="run-123",
            lead_email="test@example.com",
            lead_source=LeadSource.APOLLO,
        )
        assert item.email_opened is None
        assert item.email_replied is None
        assert item.meeting_booked is None


class TestRunSummary:
    def test_creation(self) -> None:
        summary = RunSummary(
            run_id="run-123",
            status=RunStatus.COMPLETED,
            started_at="2026-03-21T02:00:00Z",
            total_processed=25,
            tier_1=5,
            tier_2=10,
        )
        assert summary.total_processed == 25
        assert summary.tier_1 == 5


class TestApprovalWorkflow:
    def test_approve_request(self) -> None:
        req = ApproveRequest(reviewer_notes="looks good")
        assert req.reviewer_notes == "looks good"

    def test_reject_request(self) -> None:
        req = RejectRequest(rejection_reason="too small company")
        assert req.rejection_reason == "too small company"

    def test_edit_draft(self) -> None:
        req = EditDraftRequest(
            email_subject="New subject",
            email_body="New body",
        )
        assert req.email_subject == "New subject"

    def test_bulk_action(self) -> None:
        req = BulkActionRequest(
            filter_tier="tier_1",
        )
        assert req.filter_tier == "tier_1"
        assert req.item_ids == []


class TestQueueFilter:
    def test_defaults(self) -> None:
        f = QueueFilter()
        assert f.limit == 50
        assert f.offset == 0


class TestApprovalPattern:
    def test_creation(self) -> None:
        pattern = ApprovalPattern(
            pattern_type="industry",
            pattern_key="higher_ed",
            approved_count=8,
            rejected_count=2,
            approval_rate=0.8,
        )
        assert pattern.approval_rate == 0.8


class TestPipelineStats:
    def test_defaults(self) -> None:
        stats = PipelineStats()
        assert stats.total_runs == 0
        assert stats.approval_rate == 0.0
