"""Review Gate Implementation for Quality Checkpoints.

Gates enforce 100% mandatory quality checks before phase transitions.
Based on Anthropic's harnesses blog pattern for long-running agents.

Key Principles:
- Every check must pass for the gate to proceed
- Failed checks include remediation suggestions
- Gates are stateless and deterministic
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.services.langgraph.states import GateDecision, OrchestratorState, QualificationTier


@dataclass
class CheckResult:
    """Result of a single gate check."""

    name: str
    passed: bool
    reason: str
    severity: str = "error"  # "error" | "warning"
    remediation: str | None = None


@dataclass
class GateEvaluationResult:
    """Complete evaluation result from a gate."""

    proceed: bool
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    remediation: str | None = None
    confidence: float = 1.0


class BaseReviewGate(ABC):
    """
    Abstract base class for review gates.

    Each gate defines a set of checks that must pass before
    the orchestrator can proceed to the next phase.
    """

    @property
    @abstractmethod
    def gate_name(self) -> str:
        """Unique name for this gate."""
        ...

    @abstractmethod
    async def evaluate(self, state: OrchestratorState) -> GateDecision:
        """
        Evaluate the gate against the current state.

        Args:
            state: Current orchestrator state

        Returns:
            GateDecision with proceed/fail and check details
        """
        ...

    def _build_decision(
        self,
        result: GateEvaluationResult,
        next_phase: str | None = None,
    ) -> GateDecision:
        """Build a GateDecision from evaluation result."""
        return {
            "proceed": result.proceed,
            "gate_name": self.gate_name,
            "passed_checks": result.passed_checks,
            "failed_checks": result.failed_checks,
            "remediation": result.remediation,
            "next_phase": next_phase,
        }


class DataCompletenessGate(BaseReviewGate):
    """
    Gate 1: Validates data completeness before outreach.

    Checks:
    - Qualification result exists
    - Research or enrichment data available
    - Phone number enriched (warning if missing)
    - Lead has email (required)
    """

    @property
    def gate_name(self) -> str:
        return "data_completeness"

    async def evaluate(self, state: OrchestratorState) -> GateDecision:
        """Evaluate data completeness."""
        checks: list[CheckResult] = []

        # Check 1: Qualification completed
        if state.get("qualification_result"):
            checks.append(
                CheckResult(
                    name="qualification_completed",
                    passed=True,
                    reason="Lead has been qualified with ICP score",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="qualification_completed",
                    passed=False,
                    reason="Qualification result is missing",
                    remediation="Re-run qualification agent",
                )
            )

        # Check 2: Research data available
        has_research = bool(state.get("research_brief") or state.get("enrichment_data"))
        if has_research:
            checks.append(
                CheckResult(
                    name="research_data_available",
                    passed=True,
                    reason="Research or enrichment data is available",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="research_data_available",
                    passed=False,
                    reason="No research or enrichment data found",
                    remediation="Re-run research agent with different sources",
                )
            )

        # Check 3: Phone number (warning only - PHONES ARE GOLD but not blocking)
        if state.get("has_phone"):
            checks.append(
                CheckResult(
                    name="phone_available",
                    passed=True,
                    reason="Phone number enriched",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="phone_available",
                    passed=True,  # Pass but with warning
                    reason="No phone number - flag for manual research",
                    severity="warning",
                )
            )

        # Check 4: Email exists
        lead = state.get("lead")
        if lead and lead.email:
            checks.append(
                CheckResult(
                    name="email_exists",
                    passed=True,
                    reason="Lead has email address",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="email_exists",
                    passed=False,
                    reason="Lead has no email address",
                    remediation="Cannot proceed without email",
                )
            )

        # Aggregate results
        result = self._aggregate_checks(checks)

        # Determine next phase based on tier
        next_phase = None
        if result.proceed:
            tier = state.get("tier")
            next_phase = "archive" if tier == QualificationTier.NOT_ICP else "outreach"

        return self._build_decision(result, next_phase)

    def _aggregate_checks(self, checks: list[CheckResult]) -> GateEvaluationResult:
        """Aggregate individual check results into gate result."""
        passed = []
        failed = []
        warnings = []
        remediations = []

        for check in checks:
            if check.passed:
                passed.append(check.name)
                if check.severity == "warning":
                    warnings.append(check.reason)
            else:
                failed.append(check.name)
                if check.remediation:
                    remediations.append(check.remediation)

        return GateEvaluationResult(
            proceed=len(failed) == 0,
            passed_checks=passed,
            failed_checks=failed,
            warnings=warnings,
            remediation="; ".join(remediations) if remediations else None,
        )


class OutputQualityGate(BaseReviewGate):
    """
    Gate 2: Validates output quality before sync.

    Checks:
    - At least one outreach asset generated (script OR email)
    - Script has required fields if present
    - Email has subject and body if present
    """

    @property
    def gate_name(self) -> str:
        return "output_quality"

    async def evaluate(self, state: OrchestratorState) -> GateDecision:
        """Evaluate output quality."""
        checks: list[CheckResult] = []

        script_result = state.get("script_result")
        email_result = state.get("email_result")

        # Check 1: Script generated
        if script_result:
            # Validate script has content
            if self._validate_script(script_result):
                checks.append(
                    CheckResult(
                        name="script_generated",
                        passed=True,
                        reason="Call script generated and valid",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="script_generated",
                        passed=False,
                        reason="Script generated but missing required content",
                        severity="warning",
                    )
                )
        else:
            checks.append(
                CheckResult(
                    name="script_generated",
                    passed=False,
                    reason="No call script generated",
                    severity="warning",  # Not blocking if email exists
                )
            )

        # Check 2: Email generated
        if email_result:
            if self._validate_email(email_result):
                checks.append(
                    CheckResult(
                        name="email_generated",
                        passed=True,
                        reason="Email generated and valid",
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name="email_generated",
                        passed=False,
                        reason="Email generated but missing subject or body",
                        severity="warning",
                    )
                )
        else:
            checks.append(
                CheckResult(
                    name="email_generated",
                    passed=False,
                    reason="No email generated",
                    severity="warning",  # Not blocking if script exists
                )
            )

        # Gate passes if at least ONE asset is generated and valid
        has_valid_script = bool(script_result and self._validate_script(script_result))
        has_valid_email = bool(email_result and self._validate_email(email_result))
        proceed = has_valid_script or has_valid_email

        passed_checks = [c.name for c in checks if c.passed]
        failed_checks = [c.name for c in checks if not c.passed]

        remediation = None
        if not proceed:
            remediation = "Generate at least one outreach asset (script or email)"

        return self._build_decision(
            GateEvaluationResult(
                proceed=proceed,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                remediation=remediation,
            ),
            next_phase="sync" if proceed else None,
        )

    def _validate_script(self, script: dict[str, Any]) -> bool:
        """Validate script has required content."""
        return bool(
            script.get("personalized_script")
            or script.get("script_content")
            or script.get("content")
        )

    def _validate_email(self, email: dict[str, Any]) -> bool:
        """Validate email has required content."""
        has_subject = bool(email.get("subject_line") or email.get("subject"))
        has_body = bool(email.get("email_body") or email.get("body"))
        return has_subject and has_body


class EnrichmentQualityGate(BaseReviewGate):
    """
    Optional gate for validating enrichment quality.

    Checks:
    - Minimum confidence in enrichment data
    - Key fields are populated
    - Data freshness (if timestamp available)
    """

    @property
    def gate_name(self) -> str:
        return "enrichment_quality"

    async def evaluate(self, state: OrchestratorState) -> GateDecision:
        """Evaluate enrichment quality."""
        enrichment = state.get("enrichment_data") or {}
        checks: list[CheckResult] = []

        # Check 1: Has company info
        if enrichment.get("company") or enrichment.get("organization"):
            checks.append(
                CheckResult(
                    name="company_info",
                    passed=True,
                    reason="Company information available",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="company_info",
                    passed=False,
                    reason="Company information missing",
                    severity="warning",
                )
            )

        # Check 2: Has title/seniority
        if enrichment.get("title") or enrichment.get("seniority"):
            checks.append(
                CheckResult(
                    name="role_info",
                    passed=True,
                    reason="Title/seniority information available",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="role_info",
                    passed=False,
                    reason="Title/seniority information missing",
                    severity="warning",
                )
            )

        # Check 3: Has contact method
        has_phone = bool(
            enrichment.get("phone")
            or enrichment.get("mobile_phone")
            or enrichment.get("direct_dial")
        )
        has_email = bool(state.get("lead") and state["lead"].email)

        if has_phone or has_email:
            checks.append(
                CheckResult(
                    name="contact_method",
                    passed=True,
                    reason="At least one contact method available",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="contact_method",
                    passed=False,
                    reason="No contact method available",
                    remediation="Manual research required for contact info",
                )
            )

        # Aggregate
        passed = [c.name for c in checks if c.passed]
        failed = [c.name for c in checks if not c.passed and c.severity == "error"]
        warnings = [c.name for c in checks if not c.passed and c.severity == "warning"]

        # This gate is more lenient - only fails on critical errors
        proceed = len(failed) == 0

        return self._build_decision(
            GateEvaluationResult(
                proceed=proceed,
                passed_checks=passed,
                failed_checks=failed + warnings,
                remediation=None,
            ),
            next_phase="continue" if proceed else None,
        )


# Gate registry for easy access
GATES = {
    "data_completeness": DataCompletenessGate(),
    "output_quality": OutputQualityGate(),
    "enrichment_quality": EnrichmentQualityGate(),
}


def get_gate(name: str) -> BaseReviewGate:
    """Get a gate by name."""
    gate = GATES.get(name)
    if not gate:
        raise ValueError(f"Unknown gate: {name}")
    return gate
