"""SearXNG Integration for autonomous research."""
import json
import httpx
from typing import List, Dict, Optional
from api.core.config import SEARXNG_URL


class SearXNGClient:
    """Client for self-hosted SearXNG search engine."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or SEARXNG_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, language: str = "da-DK",
                     categories: str = "general,science,education",
                     limit: int = 5) -> List[Dict]:
        """Search via SearXNG."""
        try:
            response = await self.client.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": language,
                    "categories": categories,
                }
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])[:limit]
            return [{
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "engine": r.get("engine", ""),
            } for r in results]
        except Exception as e:
            return [{"title": "SearXNG ikke tilgængelig", "url": "", "content": str(e), "engine": "error"}]

    async def academic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search academic sources."""
        return await self.search(
            query=f"{query} site:arxiv.org OR site:edu",
            language="en",
            categories="science",
            limit=limit
        )

    async def danish_education_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Danish educational resources."""
        return await self.search(
            query=f"{query} site:emu.dk OR site:uvm.dk",
            language="da-DK",
            categories="education",
            limit=limit
        )


class TutorResearchEngine:
    """Autonomous research engine for tutor agents."""

    def __init__(self):
        self.searxng = SearXNGClient()

    async def should_research(self, topic: str, query: str) -> bool:
        """Decide if research is needed."""
        # Research if query mentions curriculum regulations or recent topics
        research_indicators = [
            "bekendtgørelse", "læreplan", "pensum", "hf reform",
            "opdateret", "nyeste", "2024", "2025"
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in research_indicators)

    async def research(self, agent_id: str, query: str, topic: str) -> Dict:
        """Execute research and return findings."""
        # Formulate domain-specific queries
        search_queries = self._formulate_queries(agent_id, query, topic)

        all_results = []
        for sq in search_queries:
            results = await self.searxng.search(sq, limit=3)
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r["url"] not in seen_urls and r["url"]:
                seen_urls.add(r["url"])
                unique_results.append(r)

        return {
            "query": query,
            "agent_id": agent_id,
            "results": unique_results[:5],
            "synthesis_ready": len(unique_results) > 0,
        }

    def _formulate_queries(self, agent_id: str, query: str, topic: str) -> List[str]:
        """Create domain-specific search queries."""
        queries = []

        if agent_id == "matematik":
            queries = [
                f"{topic} HF pensum dansk",
                f"{query} differentialregning undervisning",
                f"matematik {topic} HF niveau"
            ]
        elif agent_id == "fysik":
            queries = [
                f"{topic} fysik HF pensum",
                f"{query} fysik eksperiment",
                f"fysik {topic} gymnasium"
            ]
        elif agent_id == "datalogi":
            queries = [
                f"{topic} python tutorial dansk",
                f"{query} programmering undervisning",
                f"datalogi {topic} HF"
            ]
        elif agent_id == "kommunikation":
            queries = [
                f"{topic} kommunikation HF",
                f"{query} medieanalyse dansk",
                f"kommunikation {topic} retorik"
            ]
        else:
            queries = [f"{query} {topic} HF dansk"]

        return queries
