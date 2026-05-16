"""SearXNG Integration for autonomous research with verification."""
import json
import httpx
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from api.core.config import SEARXNG_URL


@dataclass
class VerifiedKnowledge:
    """Verified knowledge from research."""
    topic: str
    claims: List[str] = field(default_factory=list)
    confidence: float = 0.0
    sources: List[Dict] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    timestamp: str = ""
    agent_id: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


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
                "score": r.get("score", 0.5),
            } for r in results]
        except Exception as e:
            return [{"title": "SearXNG ikke tilgængelig", "url": "", "content": str(e), "engine": "error", "score": 0.0}]

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


class AutonomousResearchAgent:
    """
    Agents can independently research and verify information.
    
    Features:
    - Multi-query search for comprehensive coverage
    - Source credibility scoring
    - Consensus extraction across sources
    - Contradiction detection
    - Confidence scoring
    - Storage in Memory Palace for future reference
    """
    
    def __init__(self):
        self.searxng = SearXNGClient()
        
        # Domain bonuses for credibility scoring
        self.high_credibility_domains = [
            ".edu", ".gov", ".ac.uk", "arxiv.org", "scholar.google.com",
            "doi.org", "pubmed.gov", "nature.com", "science.org",
            "emu.dk", "uvm.dk", "au.dk", "ku.dk", "dtu.dk"
        ]
        
        self.low_credibility_indicators = [
            "blog", "opinion", "comment", "reddit", "quora",
            "facebook", "twitter", "tiktok"
        ]
    
    async def research_and_verify(self, query: str, agent_id: str,
                                  topic: str = "") -> VerifiedKnowledge:
        """
        Research topic and cross-verify across multiple sources.
        
        Phases:
        1. Multi-query search
        2. Source credibility scoring
        3. Claim extraction
        4. Consensus finding
        5. Contradiction detection
        6. Confidence scoring
        """
        # Phase 1: Multi-query search
        queries = self._generate_search_variants(query, agent_id, topic)
        all_results = []
        
        for q in queries:
            results = await self.searxng.search(q, limit=5)
            all_results.extend(results)
        
        # Phase 2: Source credibility scoring
        scored_results = []
        for result in all_results:
            credibility = self._score_source_credibility(result)
            scored_results.append((result, credibility))
        
        # Sort by credibility
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Phase 3: Claim extraction (simplified - would use LLM in production)
        claims = self._extract_claims(scored_results)
        
        # Phase 4: Consensus extraction
        consensus_claims = self._find_consensus(claims, scored_results)
        
        # Phase 5: Contradiction detection
        contradictions = self._detect_contradictions(claims)
        
        # Phase 6: Confidence scoring
        confidence = self._calculate_confidence(consensus_claims, contradictions, scored_results)
        
        final_knowledge = VerifiedKnowledge(
            topic=topic or query,
            claims=consensus_claims,
            confidence=confidence,
            sources=[r for r, _ in scored_results[:5]],
            contradictions=contradictions,
            agent_id=agent_id,
        )
        
        return final_knowledge
    
    def _generate_search_variants(self, query: str, agent_id: str,
                                  topic: str) -> List[str]:
        """Generate multiple search queries for comprehensive coverage."""
        variants = [query]
        
        # Add domain-specific variants
        if agent_id == "matematik":
            variants.extend([
                f"{query} matematik undervisning",
                f"{query} HF pensum matematik",
                f"{topic} matematik bevis" if topic else f"{query} bevis",
            ])
        elif agent_id == "fysik":
            variants.extend([
                f"{query} fysik eksperiment",
                f"{query} fysik princip",
                f"{topic} fysik anvendelse" if topic else f"{query} anvendelse",
            ])
        elif agent_id == "datalogi":
            variants.extend([
                f"{query} python tutorial",
                f"{query} algoritme",
                f"{query} programmering eksempel",
            ])
        elif agent_id == "kommunikation":
            variants.extend([
                f"{query} kommunikation analyse",
                f"{query} medie eksempel",
                f"{query} retorik",
            ])
        
        # Add English variant for broader coverage
        english_translation = query.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
        variants.append(f"{english_translation} education")
        
        return list(set(variants))[:5]  # Limit to 5 queries
    
    def _score_source_credibility(self, result: Dict) -> float:
        """
        Score source credibility based on domain, content, and recency.
        
        Returns score between 0.0 and 1.0
        """
        score = 0.5  # Base score
        
        url = result.get("url", "").lower()
        content = result.get("content", "").lower()
        title = result.get("title", "").lower()
        
        # Domain bonuses
        for domain in self.high_credibility_domains:
            if domain in url:
                score += 0.15
                break
        
        # Domain penalties
        for indicator in self.low_credibility_indicators:
            if indicator in url:
                score -= 0.1
        
        # Content indicators
        if any(word in content for word in ["peer-reviewed", "fagfællebedømt", "research", "studie"]):
            score += 0.1
        
        if any(word in content for word in ["mening", "opinion", "synes", "tror"]):
            score -= 0.05
        
        # Educational context
        if any(word in content for word in ["undervisning", "education", "læreplan", "pensum"]):
            score += 0.1
        
        # Recency bonus (if date mentioned)
        import re
        year_matches = re.findall(r'\b(202[0-9]|201[0-9])\b', content + title)
        if year_matches:
            latest_year = max(int(y) for y in year_matches)
            current_year = datetime.now().year
            if current_year - latest_year <= 2:
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _extract_claims(self, scored_results: List[Tuple[Dict, float]]) -> List[Dict]:
        """Extract claims from search results."""
        claims = []
        
        for result, credibility in scored_results[:10]:  # Top 10 results
            content = result.get("content", "")
            if len(content) > 50:  # Skip very short snippets
                claims.append({
                    "text": content[:300],
                    "source": result.get("title", ""),
                    "url": result.get("url", ""),
                    "credibility": credibility,
                })
        
        return claims
    
    def _find_consensus(self, claims: List[Dict], 
                       scored_results: List[Tuple[Dict, float]]) -> List[str]:
        """Find claims that appear across multiple high-credibility sources."""
        if not claims:
            return []
        
        # Simple consensus: extract key phrases that appear multiple times
        from collections import Counter
        
        # Extract significant words (simplified)
        all_words = []
        for claim in claims:
            if claim["credibility"] > 0.6:  # Only high-credibility sources
                words = claim["text"].lower().split()
                # Filter common words
                significant = [w for w in words if len(w) > 4 and w not in 
                              ["derfor", "mellem", "under", "over", "som", "kan", "vil", "skal"]]
                all_words.extend(significant)
        
        word_counts = Counter(all_words)
        
        # Find most common significant terms
        common_terms = [term for term, count in word_counts.most_common(10) if count >= 2]
        
        # Build consensus statements from top terms
        consensus = []
        if common_terms:
            consensus.append(f"Forskellige kilder er enige om vigtigheden af: {', '.join(common_terms[:5])}")
        
        # Add full claims from highest credibility sources
        for claim in claims[:3]:
            if claim["credibility"] > 0.7:
                consensus.append(claim["text"])
        
        return consensus[:5]
    
    def _detect_contradictions(self, claims: List[Dict]) -> List[str]:
        """Detect contradictory claims."""
        contradictions = []
        
        # Look for contradiction indicators
        contradiction_pairs = [
            ("altid", "nogle gange"),
            ("aldrig", "nogle"),
            ("alle", "nogle"),
            ("ingen", "nogle"),
            ("beviser", "modbeviser"),
            ("støtter", "modsiger"),
        ]
        
        claim_texts = [c["text"].lower() for c in claims]
        
        for pair in contradiction_pairs:
            has_first = any(pair[0] in text for text in claim_texts)
            has_second = any(pair[1] in text for text in claim_texts)
            
            if has_first and has_second:
                contradictions.append(
                    f"Modstridende påstande omkring '{pair[0]}' vs '{pair[1]}' fundet i kilder"
                )
        
        return contradictions
    
    def _calculate_confidence(self, consensus_claims: List[str],
                             contradictions: List[str],
                             scored_results: List[Tuple[Dict, float]]) -> float:
        """Calculate overall confidence in findings."""
        if not consensus_claims:
            return 0.0
        
        # Base confidence from number of consensus claims
        base_confidence = min(0.8, len(consensus_claims) * 0.15)
        
        # Boost from average credibility of top sources
        if scored_results:
            avg_credibility = sum(c for _, c in scored_results[:5]) / min(5, len(scored_results))
            base_confidence *= (0.5 + avg_credibility * 0.5)
        
        # Penalty for contradictions
        if contradictions:
            base_confidence *= (1.0 - len(contradictions) * 0.15)
        
        return max(0.0, min(1.0, base_confidence))
    
    async def should_research(self, topic: str, query: str) -> bool:
        """Decide if research is needed."""
        # Research if query mentions curriculum regulations or recent topics
        research_indicators = [
            "bekendtgørelse", "læreplan", "pensum", "hf reform",
            "opdateret", "nyeste", "2024", "2025", "hvad siger forskning",
            "dokumentation", "evidens", "studier viser"
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in research_indicators)
    
    async def research(self, agent_id: str, query: str, topic: str) -> Dict:
        """Execute research and return findings (legacy method)."""
        verified = await self.research_and_verify(query, agent_id, topic)
        
        return {
            "query": query,
            "agent_id": agent_id,
            "results": verified.sources,
            "claims": verified.claims,
            "confidence": verified.confidence,
            "contradictions": verified.contradictions,
            "synthesis_ready": len(verified.claims) > 0,
        }


class TutorResearchEngine:
    """Autonomous research engine for tutor agents (legacy wrapper)."""

    def __init__(self):
        self.autonomous_agent = AutonomousResearchAgent()
        self.searxng = self.autonomous_agent.searxng

    async def should_research(self, topic: str, query: str) -> bool:
        return await self.autonomous_agent.should_research(topic, query)

    async def research(self, agent_id: str, query: str, topic: str) -> Dict:
        return await self.autonomous_agent.research(agent_id, query, topic)
