"""Outreach email drafting using Challenger Sale + Never Split the Difference.

Generates concise, pain-first emails that teach the prospect something
they don't know about their own problem. No fluff, no AI artifacts.

Methodology stack:
- Challenger Sale: teach-tailor-take control
- Never Split the Difference: tactical empathy, calibrated questions
- Blue Ocean: position in uncontested space
- Business Model Canvas: where video creates value for their model
"""

import logging
from typing import Any

from app.services.autonomous.schemas import DraftEmail
from app.services.llm.clients import llm_router

logger = logging.getLogger(__name__)

CHALLENGER_SYSTEM_PROMPT = """You are Tim Kipper, BDR at Epiphan Video, writing a cold outreach email.

METHODOLOGY:
- Challenger Sale: Lead with a commercial insight that reframes how the prospect thinks about their problem. Teach them something they don't know. Don't sell features.
- Never Split the Difference: Use tactical empathy. Ask one calibrated question. Be respectful but direct. No aggressive closes.
- Blue Ocean: Position Epiphan in uncontested space (hardware+software video capture that just works). Don't compete on feature lists.
- Pain first. Money follows pain. Never lead with the product.

EPIPHAN CONTEXT:
- Epiphan makes Pearl hardware encoders for video capture, streaming, and recording
- Use cases: lecture capture, simulation recording, live events, corporate comms, telemedicine
- Key differentiator: reliable hardware appliance, not fragile software. Set it and forget it.
- Customers: universities, hospitals, law firms, government, corporations

TONE RULES:
- Write like a human texting a colleague they respect. Short sentences.
- No hyphens, no bullet points, no em dashes, no numbered lists.
- No "I hope this email finds you well" or any filler.
- Maximum 3-4 sentences in the body. Every word earns its place.
- Must feel like it was written by someone who genuinely understands their problem.
- Never use words like "leverage", "synergy", "robust", "streamline", "cutting-edge".

OUTPUT FORMAT (respond with exactly this JSON structure):
{
  "subject": "subject line under 40 chars, curiosity-driven",
  "body": "3-4 sentence email body",
  "pain_point": "one phrase describing the pain you led with"
}"""


class OutreachDrafter:
    """Draft personalized outreach using Challenger Sale methodology."""

    def __init__(self) -> None:
        """Initialize with quality LLM for email generation."""
        self._llm = llm_router.get_model("personalization")

    async def draft_email(
        self,
        lead_name: str | None,
        lead_title: str | None,
        lead_company: str | None,
        lead_industry: str | None,
        research_summary: str | None = None,
        qualification_summary: str | None = None,
    ) -> DraftEmail:
        """Draft a concise, pain-first email using Challenger framework.

        Returns structured DraftEmail with subject, body, and pain_point.
        """
        user_prompt = self._build_user_prompt(
            lead_name=lead_name,
            lead_title=lead_title,
            lead_company=lead_company,
            lead_industry=lead_industry,
            research_summary=research_summary,
            qualification_summary=qualification_summary,
        )

        try:
            response = await self._llm.ainvoke([
                {"role": "system", "content": CHALLENGER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ])

            content = response.content if hasattr(response, "content") else str(response)
            return self._parse_response(str(content), lead_name)

        except Exception:
            logger.exception("Email drafting failed for %s at %s", lead_name, lead_company)
            return DraftEmail(
                subject=f"Quick question about video at {lead_company or 'your org'}",
                body=f"Hi {lead_name or 'there'},\n\nI noticed your team might be dealing with video capture challenges. Would it make sense to chat for 10 minutes this week?\n\nTim",
                pain_point="generic_fallback",
            )

    def _build_user_prompt(
        self,
        lead_name: str | None,
        lead_title: str | None,
        lead_company: str | None,
        lead_industry: str | None,
        research_summary: str | None,
        qualification_summary: str | None,
    ) -> str:
        """Build the user prompt with lead context."""
        parts = ["Write a cold outreach email to this prospect:\n"]

        if lead_name:
            parts.append(f"Name: {lead_name}")
        if lead_title:
            parts.append(f"Title: {lead_title}")
        if lead_company:
            parts.append(f"Company: {lead_company}")
        if lead_industry:
            parts.append(f"Industry: {lead_industry}")

        if research_summary:
            parts.append(f"\nResearch context:\n{research_summary}")

        if qualification_summary:
            parts.append(f"\nQualification context:\n{qualification_summary}")

        parts.append("\nRespond with the JSON structure only. No markdown, no code fences.")

        return "\n".join(parts)

    def _parse_response(self, content: str, lead_name: str | None) -> DraftEmail:
        """Parse LLM response into DraftEmail."""
        import json

        # Strip markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data: dict[str, Any] = json.loads(cleaned)
            return DraftEmail(
                subject=data.get("subject", "Quick question"),
                body=data.get("body", ""),
                pain_point=data.get("pain_point", "unknown"),
            )
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse email draft JSON, using raw content")
            return DraftEmail(
                subject=f"Quick question for {lead_name or 'you'}",
                body=cleaned[:500],
                pain_point="parse_error",
            )


# Singleton
outreach_drafter = OutreachDrafter()
