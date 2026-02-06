"""Background processing pipeline for Harvester leads.

Handles async enrichment and qualification of leads pushed via webhook.
Integrates with monitoring endpoints for progress tracking.

PHONES ARE GOLD! Tiered enrichment prioritizes ATL decision-makers.
"""

import asyncio
import logging
from typing import Any

from app.api.routes.monitoring import (
    complete_batch,
    get_batch,
    get_rate_limit_tracker,
    register_batch,
)
from app.services.enrichment.apollo import TieredEnrichmentResult, apollo_client
from app.services.enrichment.audit import (
    EnrichmentAuditLogger,
)
from app.services.langgraph.tools.harvester_mapper import (
    enrich_phone_numbers,
)
from app.services.scoring.atl_detector import is_atl_decision_maker

logger = logging.getLogger(__name__)

# Task queue for background processing
_processing_tasks: dict[str, asyncio.Task[None]] = {}


async def queue_harvester_batch(
    batch_id: str,
    leads: list[dict[str, Any]],
    concurrency: int = 5,
    tiered_enrichment: bool = True,
) -> None:
    """
    Queue a batch of Harvester leads for background processing.

    This is non-blocking - leads are processed asynchronously.
    Track progress via /api/monitoring/batches/{batch_id}.

    Args:
        batch_id: Unique batch identifier
        leads: List of lead dictionaries from Harvester webhook
        concurrency: Max concurrent lead processing
        tiered_enrichment: Use smart tiered enrichment (default True)
    """
    # Register batch for monitoring (idempotent - won't overwrite if already registered)
    if not get_batch(batch_id):
        register_batch(batch_id, len(leads))

    # Start background task
    task = asyncio.create_task(
        _process_harvester_batch(
            batch_id=batch_id,
            leads=leads,
            concurrency=concurrency,
            tiered_enrichment=tiered_enrichment,
        )
    )
    _processing_tasks[batch_id] = task

    logger.info(f"Queued batch {batch_id} with {len(leads)} leads for processing")


async def _process_harvester_batch(
    batch_id: str,
    leads: list[dict[str, Any]],
    concurrency: int,
    tiered_enrichment: bool,
) -> None:
    """
    Process a batch of Harvester leads.

    This runs in the background, updating batch status as it progresses.
    Integrates with the monitoring endpoints for visibility.

    Args:
        batch_id: Unique batch identifier
        leads: List of lead dictionaries
        concurrency: Max concurrent processing
        tiered_enrichment: Use smart tiered enrichment
    """
    semaphore = asyncio.Semaphore(concurrency)
    audit_logger = EnrichmentAuditLogger(batch_id=batch_id)
    audit_logger.set_total_leads(len(leads))
    rate_limit_tracker = get_rate_limit_tracker()

    logger.info(f"Starting batch {batch_id} processing: {len(leads)} leads")

    async def process_single(lead_data: dict[str, Any]) -> dict[str, Any]:
        """Process a single lead with tiered enrichment."""
        async with semaphore:
            external_id = lead_data.get("external_id", "unknown")
            email = lead_data.get("contact_email")
            title = lead_data.get("contact_title")

            result: dict[str, Any] = {
                "external_id": external_id,
                "email": email,
                "success": False,
                "is_atl": False,
                "atl_persona": None,
                "credits_used": 0,
                "phone_revealed": False,
                "direct_phone": None,
                "mobile_phone": None,
                "work_phone": None,
                "error": None,
            }

            # Get batch for updating progress
            batch = get_batch(batch_id)

            try:
                # Check if we have a valid email for enrichment
                has_valid_email = email and "@" in email and "placeholder" not in email

                # Initialize phone data from Harvester
                phone_data = enrich_phone_numbers(
                    apollo_data=None,
                    harvester_direct=lead_data.get("direct_phone"),
                    harvester_mobile=lead_data.get("mobile_phone"),
                    harvester_work=lead_data.get("work_phone"),
                    harvester_company=lead_data.get("company_phone"),
                )

                apollo_data: dict[str, Any] | None = None
                tiered_result: TieredEnrichmentResult | None = None
                is_atl = False
                atl_persona: str | None = None
                atl_confidence = 0.0
                atl_reason: str | None = None
                credits_used = 0
                phone_revealed = False

                if has_valid_email and tiered_enrichment:
                    # TIERED ENRICHMENT: Smart credit allocation
                    # Phase 1 (1 credit): Basic enrichment to identify ATL
                    # Phase 2 (8 credits): Phone reveal ONLY for ATL
                    try:
                        # Track rate limit
                        rate_limit_tracker.record_request()

                        # email is validated above (has_valid_email check)
                        assert email is not None  # Type narrowing for mypy
                        tiered_result = await apollo_client.tiered_enrich(
                            email=email,
                            title=title,
                        )

                        rate_limit_tracker.record_success()

                        apollo_data = tiered_result.data
                        credits_used = tiered_result.credits_used
                        is_atl = tiered_result.is_atl
                        atl_persona = tiered_result.persona_match
                        phone_revealed = tiered_result.phone_revealed

                        if tiered_result.atl_match:
                            atl_confidence = tiered_result.atl_match.confidence
                            atl_reason = tiered_result.atl_match.reason

                        # Update phone data with Apollo results
                        if apollo_data:
                            phone_data = enrich_phone_numbers(
                                apollo_data=apollo_data,
                                harvester_direct=lead_data.get("direct_phone"),
                                harvester_mobile=lead_data.get("mobile_phone"),
                                harvester_work=lead_data.get("work_phone"),
                                harvester_company=lead_data.get("company_phone"),
                            )

                    except Exception as e:
                        error_msg = str(e)
                        if "rate limit" in error_msg.lower():
                            rate_limit_tracker.record_rate_limit()
                            logger.warning(f"Rate limit hit for {external_id}")
                        else:
                            logger.error(f"Enrichment failed for {external_id}: {error_msg}")
                        result["error"] = error_msg

                elif has_valid_email:
                    # Non-tiered: Still detect ATL for reporting
                    atl_match = is_atl_decision_maker(title=title, seniority=None)
                    is_atl = atl_match.is_atl
                    atl_persona = atl_match.persona_id
                    atl_confidence = atl_match.confidence
                    atl_reason = atl_match.reason
                else:
                    # No email: Still detect ATL from title
                    if title:
                        atl_match = is_atl_decision_maker(title=title, seniority=None)
                        is_atl = atl_match.is_atl
                        atl_persona = atl_match.persona_id
                        atl_confidence = atl_match.confidence
                        atl_reason = atl_match.reason

                # Clay fallback: push to Clay if no phone found
                # PHONES ARE GOLD! Clay's 75+ providers may find what Apollo missed
                if not phone_data.get("best_phone"):
                    try:
                        from app.services.enrichment.clay import clay_client

                        if clay_client.is_enabled():
                            await clay_client.push_lead_to_clay({
                                "lead_id": external_id,
                                "email": email,
                                "name": lead_data.get("contact_name"),
                                "company": lead_data.get("company_name"),
                                "title": title,
                            })
                            logger.info(
                                "Pushed lead %s to Clay for phone enrichment (Apollo found no phone)",
                                external_id,
                            )
                    except Exception:
                        logger.warning(
                            "Clay push failed for lead %s",
                            external_id,
                            exc_info=True,
                        )

                # Build result
                result.update({
                    "success": True,
                    "is_atl": is_atl,
                    "atl_persona": atl_persona,
                    "atl_confidence": atl_confidence,
                    "atl_reason": atl_reason,
                    "credits_used": credits_used,
                    "phone_revealed": phone_revealed,
                    "direct_phone": phone_data.get("direct_phone"),
                    "mobile_phone": phone_data.get("mobile_phone"),
                    "work_phone": phone_data.get("work_phone"),
                    "company_phone": phone_data.get("company_phone"),
                    "best_phone": phone_data.get("best_phone"),
                    "phone_source": phone_data.get("phone_source"),
                })

                # Log audit entry
                audit_logger.log_tiered_enrichment(
                    external_id=external_id,
                    email=email,
                    is_atl=is_atl,
                    atl_persona=atl_persona,
                    atl_confidence=atl_confidence,
                    atl_reason=atl_reason,
                    credits_used=credits_used,
                    phone_revealed=phone_revealed,
                    direct_phone=phone_data.get("direct_phone"),
                    mobile_phone=phone_data.get("mobile_phone"),
                    work_phone=phone_data.get("work_phone"),
                    title=title,
                )

                # Update batch progress
                if batch:
                    batch.processed += 1
                    batch.total_credits_used += credits_used
                    if is_atl:
                        batch.atl_leads += 1
                    else:
                        batch.non_atl_leads += 1
                    if phone_revealed:
                        batch.phones_revealed += 1
                    if phone_data.get("direct_phone"):
                        batch.direct_phones_found += 1
                    if phone_data.get("best_phone"):
                        batch.any_phones_found += 1

            except Exception as e:
                result["error"] = str(e)
                result["success"] = False
                logger.error(f"Failed to process lead {external_id}: {e}")

                if batch:
                    batch.processed += 1
                    batch.failed += 1

            return result

    # Process all leads concurrently
    try:
        tasks = [process_single(lead) for lead in leads]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any exceptions
        for _i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Lead processing exception: {result}")

        # Complete the batch
        complete_batch(batch_id)
        audit_logger.log_summary()

        logger.info(
            f"Batch {batch_id} completed: "
            f"{audit_logger.summary.processed} processed, "
            f"{audit_logger.summary.failed} failed, "
            f"{audit_logger.summary.atl_leads} ATL, "
            f"{audit_logger.summary.total_credits_used} credits used"
        )

    except Exception as e:
        logger.error(f"Batch {batch_id} failed: {e}")
        # Still mark as complete (with failures)
        complete_batch(batch_id)

    finally:
        # Clean up task reference
        if batch_id in _processing_tasks:
            del _processing_tasks[batch_id]


async def get_batch_task(batch_id: str) -> asyncio.Task[None] | None:
    """Get the background task for a batch, if still running."""
    return _processing_tasks.get(batch_id)


async def cancel_batch(batch_id: str) -> bool:
    """Cancel a running batch task."""
    task = _processing_tasks.get(batch_id)
    if task and not task.done():
        task.cancel()
        logger.info(f"Cancelled batch {batch_id}")
        return True
    return False
