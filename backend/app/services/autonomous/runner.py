"""Autonomous BDR pipeline runner.

Orchestrates the nightly prospect-to-outreach loop:
Find → Enrich → Score → Personalize → Queue

Inspired by Karpathy's autoresearch: iterate, evaluate, improve.
The agent runs unattended and queues results for Tim's morning review.

NOT a LangGraph agent. Uses the same asyncio.gather pattern as
CallBriefAssembler for parallel agent composition with graceful degradation.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from app.data.lead_schemas import Lead
from app.services.autonomous.schemas import (
    DraftEmail,
    LeadSource,
    QueueItem,
    QueueStatus,
    RawLead,
    RunConfig,
    RunStatus,
    RunSummary,
)

logger = logging.getLogger(__name__)


class AutonomousBDRRunner:
    """Nightly autonomous BDR pipeline.

    Composes existing agents (research, qualify, email, call_brief)
    into an autonomous loop. Each lead is processed independently
    with graceful degradation — one failure doesn't stop the batch.

    Like autoresearch: humans program the instructions (ICP criteria,
    methodology), agent programs the execution (prospect, enrich, draft).
    """

    def __init__(self) -> None:
        """Initialize with lazy agent references."""
        self._concurrency = 5  # Max parallel lead processing

    async def run(self, config: RunConfig | None = None) -> RunSummary:
        """Execute a full pipeline run.

        Steps:
        1. Source leads from Apollo + HubSpot
        2. Deduplicate
        3. Process each lead (enrich → score → draft → queue)
        4. Record results and update learning patterns
        """
        config = config or RunConfig()
        run_id = str(uuid.uuid4())
        start_time = time.monotonic()
        errors: list[str] = []

        logger.info(
            "Starting autonomous run %s: limit=%d, sources=%s",
            run_id,
            config.prospect_limit,
            [s.value for s in config.sources],
        )

        # Create run record in Supabase
        await self._create_run_record(run_id, config)

        try:
            # Step 1: Source leads
            raw_leads = await self._source_leads(config)
            total_sourced = len(raw_leads)
            logger.info("Sourced %d raw leads", total_sourced)

            # Step 2: Deduplicate
            from app.services.autonomous.dedup import deduplicator

            unique_leads = await deduplicator.deduplicate(raw_leads)
            total_after_dedup = len(unique_leads)

            # Cap at prospect_limit
            if len(unique_leads) > config.prospect_limit:
                unique_leads = unique_leads[: config.prospect_limit]

            # Step 3: Process each lead in parallel
            semaphore = asyncio.Semaphore(self._concurrency)
            results = await asyncio.gather(
                *[
                    self._process_lead(lead, run_id, semaphore)
                    for lead in unique_leads
                ],
                return_exceptions=True,
            )

            # Tally results
            tier_counts: dict[str, int] = {
                "tier_1": 0, "tier_2": 0, "tier_3": 0, "not_icp": 0,
            }
            total_processed = 0
            credits_used = 0
            phones_found = 0

            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                    continue
                if isinstance(result, dict):
                    total_processed += 1
                    tier = result.get("tier", "not_icp")
                    if tier in tier_counts:
                        tier_counts[tier] += 1
                    credits_used += result.get("credits", 0)
                    if result.get("has_phone"):
                        phones_found += 1

            elapsed_ms = (time.monotonic() - start_time) * 1000

            summary = RunSummary(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                total_sourced=total_sourced,
                total_after_dedup=total_after_dedup,
                total_processed=total_processed,
                tier_1=tier_counts["tier_1"],
                tier_2=tier_counts["tier_2"],
                tier_3=tier_counts["tier_3"],
                not_icp=tier_counts["not_icp"],
                credits_used=credits_used,
                phones_found=phones_found,
                errors=errors,
                config=config,
            )

            # Update run record
            await self._update_run_record(run_id, summary)

            logger.info(
                "Run %s completed in %.1fms: %d processed, T1=%d T2=%d T3=%d, %d credits, %d phones",
                run_id,
                elapsed_ms,
                total_processed,
                tier_counts["tier_1"],
                tier_counts["tier_2"],
                tier_counts["tier_3"],
                credits_used,
                phones_found,
            )

            return summary

        except Exception as e:
            logger.exception("Autonomous run %s failed", run_id)
            errors.append(str(e))
            summary = RunSummary(
                run_id=run_id,
                status=RunStatus.FAILED,
                started_at=datetime.now(timezone.utc),
                errors=errors,
                config=config,
            )
            await self._update_run_record(run_id, summary)
            return summary

    async def _source_leads(self, config: RunConfig) -> list[RawLead]:
        """Source leads from configured sources in parallel."""
        from app.services.autonomous.sourcer import lead_sourcer

        tasks = []

        if LeadSource.APOLLO in config.sources:
            tasks.append(
                lead_sourcer.find_apollo_prospects(
                    limit=config.prospect_limit,
                    verticals=config.verticals or None,
                    personas=config.personas or None,
                )
            )

        if LeadSource.HUBSPOT in config.sources:
            # Find last run time for incremental inbound
            last_run = await self._get_last_run_time()
            tasks.append(lead_sourcer.find_hubspot_inbound(since=last_run))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_leads: list[RawLead] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Lead sourcing failed: %s", result)
            elif isinstance(result, list):
                all_leads.extend(result)

        return all_leads

    async def _process_lead(
        self,
        raw_lead: RawLead,
        run_id: str,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        """Process a single lead: enrich → score → draft → queue.

        Each step uses _safe_* wrappers for graceful degradation.
        """
        async with semaphore:
            lead_result: dict[str, Any] = {
                "email": raw_lead.email,
                "tier": "not_icp",
                "credits": 0,
                "has_phone": False,
            }

            # Build Lead model for agent consumption
            lead = Lead(
                hubspot_id=raw_lead.source_id or raw_lead.email,
                email=raw_lead.email,
                first_name=raw_lead.first_name,
                last_name=raw_lead.last_name,
                company=raw_lead.company,
                title=raw_lead.title,
                phone=raw_lead.phone,
                linkedin_url=raw_lead.linkedin_url,
                industry=raw_lead.industry,
            )

            # Run enrichment + qualification in parallel
            research_result, qualification_result = await asyncio.gather(
                self._safe_research(lead),
                self._safe_qualify(lead),
            )

            # Extract tier and score
            tier = "not_icp"
            score = 0.0
            confidence = 0.0
            persona_match: str | None = None
            is_atl = False

            if qualification_result:
                tier_value = qualification_result.get("tier")
                if tier_value:
                    tier = tier_value.value if hasattr(tier_value, "value") else str(tier_value)
                score = float(qualification_result.get("total_score", 0))
                confidence = float(qualification_result.get("confidence", 0))
                persona_match = qualification_result.get("persona_match")
                is_atl = persona_match is not None

            lead_result["tier"] = tier
            lead_result["has_phone"] = bool(raw_lead.phone)

            # Draft email
            research_summary = None
            if research_result:
                brief = research_result.get("research_brief")
                if isinstance(brief, dict):
                    research_summary = brief.get("summary") or brief.get("company_overview")

            qual_summary = None
            if qualification_result:
                qual_summary = f"Tier: {tier}, Score: {score:.0f}, Confidence: {confidence:.0%}"

            draft = await self._safe_draft(
                lead_name=raw_lead.name or raw_lead.first_name,
                lead_title=raw_lead.title,
                lead_company=raw_lead.company,
                lead_industry=raw_lead.industry,
                research_summary=research_summary,
                qualification_summary=qual_summary,
            )

            # Insert into outreach_queue
            queue_item = QueueItem(
                run_id=run_id,
                status=QueueStatus.PENDING,
                lead_email=raw_lead.email,
                lead_name=raw_lead.name or f"{raw_lead.first_name or ''} {raw_lead.last_name or ''}".strip() or None,
                lead_title=raw_lead.title,
                lead_company=raw_lead.company,
                lead_industry=raw_lead.industry,
                lead_phone=raw_lead.phone,
                lead_source=raw_lead.source,
                lead_data=raw_lead.raw_data,
                qualification_tier=tier,
                qualification_score=score,
                qualification_confidence=confidence,
                persona_match=persona_match,
                is_atl=is_atl,
                email_subject=draft.subject if draft else None,
                email_body=draft.body if draft else None,
                email_pain_point=draft.pain_point if draft else None,
                email_methodology=draft.methodology if draft else "challenger",
            )

            await self._insert_queue_item(queue_item)

            return lead_result

    # =========================================================================
    # Safe agent wrappers (graceful degradation)
    # =========================================================================

    async def _safe_research(self, lead: Lead) -> dict[str, Any] | None:
        """Run research agent with graceful degradation."""
        try:
            from app.services.langgraph.agents.lead_research import LeadResearchAgent

            agent = LeadResearchAgent()
            return await agent.run(lead=lead, research_depth="quick")
        except Exception:
            logger.exception("Research agent failed for %s", lead.email)
            return None

    async def _safe_qualify(self, lead: Lead) -> dict[str, Any] | None:
        """Run qualification agent with graceful degradation."""
        try:
            from app.services.langgraph.agents.qualification import QualificationAgent

            agent = QualificationAgent()
            return await agent.run(lead=lead, skip_enrichment=True)
        except Exception:
            logger.exception("Qualification agent failed for %s", lead.email)
            return None

    async def _safe_draft(
        self,
        lead_name: str | None,
        lead_title: str | None,
        lead_company: str | None,
        lead_industry: str | None,
        research_summary: str | None,
        qualification_summary: str | None,
    ) -> DraftEmail | None:
        """Draft email with graceful degradation."""
        try:
            from app.services.autonomous.drafter import outreach_drafter

            return await outreach_drafter.draft_email(
                lead_name=lead_name,
                lead_title=lead_title,
                lead_company=lead_company,
                lead_industry=lead_industry,
                research_summary=research_summary,
                qualification_summary=qualification_summary,
            )
        except Exception:
            logger.exception("Email drafting failed for %s", lead_name)
            return None

    # =========================================================================
    # Supabase operations
    # =========================================================================

    async def _create_run_record(self, run_id: str, config: RunConfig) -> None:
        """Create the autonomous_runs record."""
        try:
            from app.services.database.supabase_client import supabase_client

            supabase_client.client.table("autonomous_runs").insert({
                "id": run_id,
                "status": "running",
                "config": config.model_dump(),
            }).execute()
        except Exception:
            logger.exception("Failed to create run record %s", run_id)

    async def _update_run_record(self, run_id: str, summary: RunSummary) -> None:
        """Update the autonomous_runs record with results."""
        try:
            from app.services.database.supabase_client import supabase_client

            supabase_client.client.table("autonomous_runs").update({
                "status": summary.status.value,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_sourced": summary.total_sourced,
                    "total_after_dedup": summary.total_after_dedup,
                    "total_processed": summary.total_processed,
                    "tier_1": summary.tier_1,
                    "tier_2": summary.tier_2,
                    "tier_3": summary.tier_3,
                    "not_icp": summary.not_icp,
                    "credits_used": summary.credits_used,
                    "phones_found": summary.phones_found,
                },
                "error_log": summary.errors[:50],
            }).eq("id", run_id).execute()
        except Exception:
            logger.exception("Failed to update run record %s", run_id)

    async def _insert_queue_item(self, item: QueueItem) -> None:
        """Insert a queue item into outreach_queue."""
        try:
            from app.services.database.supabase_client import supabase_client

            data: dict[str, Any] = {
                "run_id": item.run_id,
                "status": item.status.value,
                "lead_email": item.lead_email,
                "lead_name": item.lead_name,
                "lead_title": item.lead_title,
                "lead_company": item.lead_company,
                "lead_industry": item.lead_industry,
                "lead_phone": item.lead_phone,
                "lead_source": item.lead_source.value,
                "lead_data": item.lead_data,
                "qualification_tier": item.qualification_tier,
                "qualification_score": item.qualification_score,
                "qualification_confidence": item.qualification_confidence,
                "persona_match": item.persona_match,
                "is_atl": item.is_atl,
                "email_subject": item.email_subject,
                "email_body": item.email_body,
                "email_pain_point": item.email_pain_point,
                "email_methodology": item.email_methodology,
            }

            supabase_client.client.table("outreach_queue").insert(data).execute()
        except Exception:
            logger.exception("Failed to insert queue item for %s", item.lead_email)

    async def _get_last_run_time(self) -> datetime | None:
        """Get the start time of the last completed run for incremental sourcing."""
        try:
            from app.services.database.supabase_client import supabase_client

            result = (
                supabase_client.client.table("autonomous_runs")
                .select("started_at")
                .eq("status", "completed")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )

            rows = cast(list[dict[str, Any]], result.data) if result.data else []
            if rows and rows[0].get("started_at"):
                return datetime.fromisoformat(rows[0]["started_at"])
            return None

        except Exception:
            logger.exception("Failed to get last run time")
            return None


# Singleton
autonomous_runner = AutonomousBDRRunner()
