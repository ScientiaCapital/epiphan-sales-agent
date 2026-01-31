"""Lead Research Agent for enriching and synthesizing lead intelligence.

Orchestrates multiple enrichment sources (Apollo, web scraping)
to build comprehensive research briefs for sales outreach.
"""

import asyncio
from typing import Any, cast

from app.data.lead_schemas import Lead
from app.services.langgraph.states import LeadResearchState, ResearchBrief
from app.services.langgraph.tools.research_tools import (
    combine_enrichment_data,
    enrich_from_apollo,
    get_company_domain,
    scrape_company_news,
    scrape_company_website,
)
from langgraph.graph import END, StateGraph


class LeadResearchAgent:
    """
    Agent for researching leads and building intelligence briefs.

    Flow: enrich_apis (parallel) → scrape_web (optional) → synthesize → format_brief
    """

    def __init__(self) -> None:
        """Initialize the agent."""
        self._graph: StateGraph[LeadResearchState] | None = None

    def _build_graph(self) -> StateGraph[LeadResearchState]:
        """Build the LangGraph state graph."""
        graph = StateGraph(LeadResearchState)

        # Add nodes
        graph.add_node("enrich_apis", self._enrich_apis_node)
        graph.add_node("scrape_web", self._scrape_web_node)
        graph.add_node("synthesize", self._synthesize_node)

        # Define edges
        graph.set_entry_point("enrich_apis")
        graph.add_conditional_edges(
            "enrich_apis",
            self._should_scrape,
            {
                "scrape": "scrape_web",
                "skip": "synthesize",
            },
        )
        graph.add_edge("scrape_web", "synthesize")
        graph.add_edge("synthesize", END)

        return graph

    def _should_scrape(self, state: LeadResearchState) -> str:
        """Determine if we should do web scraping."""
        if state.get("research_depth") == "quick":
            return "skip"
        return "scrape"

    async def _enrich_apis_node(
        self, state: LeadResearchState
    ) -> dict[str, Any]:
        """Run API enrichment."""
        lead = state["lead"]

        # Enrich from Apollo
        try:
            apollo_data = await enrich_from_apollo(lead.email)
        except Exception:
            apollo_data = None

        return {
            "apollo_data": apollo_data,
        }

    async def _scrape_web_node(
        self, state: LeadResearchState
    ) -> dict[str, Any]:
        """Scrape company website for additional context."""
        lead = state["lead"]
        domain = get_company_domain(lead.email)

        # Run website and news scraping in parallel
        website_task = scrape_company_website(domain)
        news_task = scrape_company_news(domain)

        website_data, news_data = await asyncio.gather(
            website_task, news_task, return_exceptions=True
        )

        # Handle exceptions
        if isinstance(website_data, Exception):
            website_data = None
        if isinstance(news_data, Exception):
            news_data = []

        return {
            "linkedin_context": (website_data or {}).get("about_text"),
            "news_articles": news_data or [],
        }

    async def _synthesize_node(
        self, state: LeadResearchState
    ) -> dict[str, Any]:
        """Synthesize enrichment data into a research brief."""
        lead = state["lead"]
        apollo_data = state.get("apollo_data")
        news_articles = state.get("news_articles", [])
        linkedin_context = state.get("linkedin_context")

        # Combine data from all sources
        combined = combine_enrichment_data(
            apollo_data,
            {"about_text": linkedin_context} if linkedin_context else None,
        )

        # Build research brief
        research_brief = self._build_research_brief(
            lead, combined, news_articles, linkedin_context
        )

        # Extract talking points
        talking_points = self._extract_talking_points(
            lead, combined, news_articles
        )

        # Identify risk factors
        risk_factors = self._identify_risk_factors(lead, apollo_data)

        return {
            "research_brief": research_brief,
            "talking_points": talking_points,
            "risk_factors": risk_factors,
        }

    def _build_research_brief(
        self,
        lead: Lead,
        combined: dict[str, Any],
        news: list[dict[str, Any]],
        linkedin_context: str | None,
    ) -> ResearchBrief:
        """Build a structured research brief."""
        # Company overview
        industry = combined.get("industry", "Unknown")
        employees = combined.get("employees")
        emp_str = f" with ~{employees:,} employees" if employees else ""
        overview = f"{lead.company} operates in {industry}{emp_str}."

        if combined.get("about_text"):
            overview += f" {combined['about_text'][:200]}"

        return {
            "company_overview": overview,
            "recent_news": news[:5],  # Top 5 news items
            "talking_points": [],  # Filled by caller
            "risk_factors": [],  # Filled by caller
            "linkedin_summary": linkedin_context[:500] if linkedin_context else None,
        }

    def _extract_talking_points(
        self,
        lead: Lead,
        combined: dict[str, Any],
        news: list[dict[str, Any]],
    ) -> list[str]:
        """Extract relevant talking points from enrichment data."""
        points = []

        # Tech stack opportunities
        tech_stack = combined.get("tech_stack", [])
        video_tech = [
            t for t in tech_stack
            if any(kw in t.lower() for kw in ["zoom", "teams", "panopto", "kaltura", "video"])
        ]
        if video_tech:
            points.append(f"Currently using {', '.join(video_tech[:3])} - potential integration opportunity")

        # Industry-specific point
        industry = combined.get("industry", "")
        if "education" in industry.lower():
            points.append("Higher education focus - lecture capture and hybrid learning relevant")
        elif "healthcare" in industry.lower():
            points.append("Healthcare vertical - simulation and training applications")
        elif "corporate" in industry.lower() or "enterprise" in industry.lower():
            points.append("Enterprise focus - town halls and executive communications")

        # Company size point
        employees = combined.get("employees", 0)
        if employees and employees > 1000:
            points.append(f"Large organization ({employees:,} employees) - enterprise deployment potential")
        elif employees and employees > 100:
            points.append(f"Mid-size organization ({employees:,} employees) - scalable solution needed")

        # News-based points
        for article in news[:2]:
            title = article.get("title", "")
            if any(kw in title.lower() for kw in ["expand", "invest", "growth", "new", "launch"]):
                points.append(f"Recent news: {title[:80]}")

        # Title-based personalization
        title = combined.get("title") or lead.title or ""
        if "av" in title.lower() or "audio" in title.lower() or "video" in title.lower():
            points.append("AV specialist - focus on technical capabilities and integration")
        elif "director" in title.lower() or "vp" in title.lower():
            points.append("Senior decision maker - emphasize ROI and strategic value")
        elif "it" in title.lower() or "tech" in title.lower():
            points.append("IT focus - discuss deployment, support, and security")

        return points[:5]  # Return top 5 points

    def _identify_risk_factors(
        self,
        lead: Lead,
        apollo_data: dict[str, Any] | None,
    ) -> list[str]:
        """Identify potential risk factors for the deal."""
        risks = []

        # No contact data
        if not apollo_data:
            risks.append("Limited contact information - may need additional research")

        # Company size concerns from Apollo
        if apollo_data:
            employees = apollo_data.get("employees", 0)
            if employees and employees < 100:
                risks.append("Small organization - may have budget constraints")

            # Industry mismatch
            industry = apollo_data.get("industry", "").lower()
            if industry and not any(v in industry for v in [
                "education", "healthcare", "media", "entertainment",
                "government", "corporate", "enterprise", "legal"
            ]):
                risks.append(f"Non-core vertical ({industry}) - may need vertical-specific pitch")

        # Missing key info
        if not lead.phone:
            risks.append("No phone number - email outreach only")

        return risks

    async def run(
        self,
        lead: Lead,
        research_depth: str = "deep",
    ) -> dict[str, Any]:
        """
        Run lead research and return enriched intelligence.

        Args:
            lead: Lead to research
            research_depth: "quick" (API only) or "deep" (API + web scraping)

        Returns:
            Dict with research_brief, talking_points, risk_factors
        """
        # Build graph if needed
        if self._graph is None:
            self._graph = self._build_graph()

        # Compile and run
        compiled = self._graph.compile()

        # Initial state
        initial_state: LeadResearchState = {
            "lead": lead,
            "research_depth": research_depth,
            "apollo_data": None,
            "news_articles": [],
            "linkedin_context": None,
            "research_brief": None,
            "talking_points": [],
            "risk_factors": [],
        }

        # Run the graph
        result = await compiled.ainvoke(cast(Any, initial_state))

        return {
            "research_brief": result.get("research_brief"),
            "talking_points": result.get("talking_points", []),
            "risk_factors": result.get("risk_factors", []),
        }


# Singleton instance
lead_research_agent = LeadResearchAgent()
