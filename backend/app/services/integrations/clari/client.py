"""Clari Copilot integration client for conversation intelligence."""

from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings


class ClariCopilotClient:
    """
    Clari Copilot client for pulling conversation intelligence.

    Read-only access to:
    - Call recordings and transcripts
    - Conversation analytics
    - AE performance insights
    - Buying signals and objections
    """

    def __init__(self):
        self.api_key = settings.clari_api_key
        self.api_base = settings.clari_api_base
        self.workspace_id = settings.clari_workspace_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_conversations(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        ae_email: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Fetch conversation records from Clari Copilot.

        Filters:
        - Date range
        - Specific AE (Lex, Phil, etc.)
        - Pagination
        """
        params = {
            "limit": limit,
            "offset": offset,
        }

        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if ae_email:
            params["user_email"] = ae_email

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/conversations",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_conversation_detail(
        self, conversation_id: str
    ) -> dict[str, Any]:
        """Get detailed conversation data including transcript."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/conversations/{conversation_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_conversation_transcript(
        self, conversation_id: str
    ) -> dict[str, Any]:
        """Get full transcript with speaker diarization."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/conversations/{conversation_id}/transcript",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_conversation_insights(
        self, conversation_id: str
    ) -> dict[str, Any]:
        """
        Get AI-extracted insights from a conversation.

        Returns:
        - Buying signals
        - Objections
        - Competitors mentioned
        - Next steps
        - Sentiment analysis
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/conversations/{conversation_id}/insights",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_ae_performance(
        self,
        ae_email: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get performance metrics for a specific AE.

        Metrics:
        - Talk ratio
        - Question frequency
        - Monologue length
        - Engagement scores
        - Win rate trends
        """
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/users/{ae_email}/performance",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_team_analytics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get team-wide conversation analytics."""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/analytics/team",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def search_conversations(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Search conversations by keyword/phrase.

        Useful for finding:
        - Specific objection handling examples
        - Competitor mentions
        - Product feature discussions
        """
        payload = {
            "query": query,
            "filters": filters or {},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/conversations/search",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_deals_with_conversations(
        self,
        deal_stage: str | None = None,
        outcome: str | None = None,  # "won" or "lost"
    ) -> dict[str, Any]:
        """
        Get deals with their associated conversations.

        Useful for win/loss analysis.
        """
        params = {}
        if deal_stage:
            params["deal_stage"] = deal_stage
        if outcome:
            params["outcome"] = outcome

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/deals",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def parse_conversation(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse raw Clari response into our conversation model format."""
        return {
            "clari_id": raw_data.get("id"),
            "ae_name": raw_data.get("host", {}).get("name"),
            "ae_email": raw_data.get("host", {}).get("email"),
            "prospect_name": raw_data.get("participants", [{}])[0].get("name")
            if raw_data.get("participants")
            else None,
            "prospect_email": raw_data.get("participants", [{}])[0].get("email")
            if raw_data.get("participants")
            else None,
            "call_date": raw_data.get("start_time"),
            "duration_seconds": raw_data.get("duration"),
            "recording_url": raw_data.get("recording_url"),
            "transcript": raw_data.get("transcript", {}).get("text"),
            "sentiment_score": raw_data.get("analytics", {}).get("sentiment"),
            "talk_ratio": raw_data.get("analytics", {}).get("talk_ratio"),
            "buying_signals": raw_data.get("insights", {}).get("buying_signals", []),
            "objections": raw_data.get("insights", {}).get("objections", []),
            "competitors_mentioned": raw_data.get("insights", {}).get(
                "competitors", []
            ),
            "next_steps": raw_data.get("insights", {}).get("next_steps", []),
        }


# Singleton instance
clari_client = ClariCopilotClient()
