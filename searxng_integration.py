"""
SearXNG Research Integration - Phase 2
Enables self-research when confidence is low or topic not in PDF
"""

import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass
class ResearchResult:
    """Single research result from SearXNG"""
    title: str
    url: str
    content: str
    source: str
    score: float
    published_date: Optional[str] = None


class SearXNGResearcher:
    """
    Integrates SearXNG for self-research capabilities
    Triggers when agent confidence < threshold or topic not in knowledge base
    """
    
    def __init__(self, searxng_url: str = "http://localhost:8080"):
        """
        :param searxng_url: Base URL of SearXNG instance
        """
        self.base_url = searxng_url.rstrip('/')
        self.search_endpoint = f"{self.base_url}/search"
        
    def search(self, query: str, categories: List[str] = None, 
               time_range: str = "None", max_results: int = 5) -> List[ResearchResult]:
        """
        Search SearXNG for relevant information
        
        :param query: Search query
        :param categories: Categories to search (e.g., ['science', 'it'])
        :param time_range: Time range (None, day, week, month, year)
        :param max_results: Maximum results to return
        :return: List of ResearchResult objects
        """
        params = {
            'q': query,
            'format': 'json',
            'pageno': 1
        }
        
        if categories:
            params['categories'] = ','.join(categories)
        
        if time_range != "None":
            params['time_range'] = time_range
        
        try:
            response = requests.get(self.search_endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('results', [])[:max_results]:
                result = ResearchResult(
                    title=item.get('title', 'No title'),
                    url=item.get('url', ''),
                    content=item.get('content', '')[:500],  # Limit content length
                    source=item.get('source', 'Unknown'),
                    score=item.get('score', 0.0),
                    published_date=item.get('publishedDate')
                )
                results.append(result)
            
            return results
        
        except Exception as e:
            print(f"⚠️  SearXNG search error: {e}")
            return []
    
    def summarize_results(self, results: List[ResearchResult], llm_client, 
                         focus_question: str) -> str:
        """
        Use LLM to summarize research results for a specific question
        
        :param results: List of research results
        :param llm_client: LLM client for summarization
        :param focus_question: The original question being researched
        :return: Concise summary
        """
        if not results:
            return "No relevant information found."
        
        # Format results for LLM
        context = ""
        for i, r in enumerate(results, 1):
            context += f"[{i}] {r.title}\nSource: {r.source}\n{r.content}\n\n"
        
        prompt = f"""
RESEARCH SUMMARY TASK

Original Question: {focus_question}

Research Results:
{context[:3000]}  # Limit context for 8B model

INSTRUCTIONS:
1. Extract key information that answers the question
2. Cite sources using [1], [2], etc.
3. Identify any contradictions between sources
4. Note confidence level (high/medium/low)
5. Keep summary under 200 words

OUTPUT FORMAT:
Summary: [concise answer]
Sources: [list of cited sources]
Confidence: [high/medium/low]
Contradictions: [any conflicting info, or "None"]
"""
        
        try:
            summary = llm_client.generate(prompt, max_tokens=600)
            return summary
        except Exception as e:
            print(f"⚠️  Summarization error: {e}")
            return "Error generating summary."
    
    def validate_sources(self, results: List[ResearchResult], 
                        llm_client) -> List[ResearchResult]:
        """
        Use Critic agent logic to validate source reliability
        
        :param results: Research results to validate
        :param llm_client: LLM client for validation
        :return: Filtered list of reliable results
        """
        if not results:
            return []
        
        # Simple heuristic filtering first
        trusted_domains = ['.edu', '.gov', '.org', 'wikipedia.org', 
                          'arxiv.org', 'scholar.google.com']
        
        filtered = []
        for r in results:
            # Check if from trusted domain
            is_trusted = any(domain in r.url for domain in trusted_domains)
            # Check if has reasonable content
            has_content = len(r.content) > 50
            
            if is_trusted or has_content:
                filtered.append(r)
        
        # If too few results, relax criteria
        if len(filtered) < 2:
            filtered = results[:3]  # Take top 3 regardless
        
        return filtered


class ResearchTrigger:
    """
    Decides when to trigger research based on agent confidence and knowledge gaps
    """
    
    def __init__(self, researcher: SearXNGResearcher, confidence_threshold: float = 0.6):
        """
        :param researcher: SearXNGResearcher instance
        :param confidence_threshold: Trigger research if confidence < this value
        """
        self.researcher = researcher
        self.threshold = confidence_threshold
        self.research_history = []
    
    def should_research(self, agent_outputs: Dict[str, Any], 
                       topic: str, concept_graph: Dict) -> bool:
        """
        Determine if research is needed
        
        :param agent_outputs: Outputs from all agents
        :param topic: Current topic
        :param concept_graph: Existing knowledge graph
        :return: True if research should be triggered
        """
        # Check 1: Low confidence from any agent
        for agent, output in agent_outputs.items():
            if hasattr(output, 'confidence') and output.confidence < self.threshold:
                print(f"   🔍 Research trigger: {agent} confidence too low ({output.confidence})")
                return True
        
        # Check 2: Topic not in concept graph
        topic_id = topic.lower().replace(' ', '_')
        if topic_id not in concept_graph.get('nodes', {}):
            print(f"   🔍 Research trigger: Topic '{topic}' not in knowledge base")
            return True
        
        # Check 3: Critic found major issues
        if 'critic' in agent_outputs:
            critic = agent_outputs['critic']
            if hasattr(critic, 'issues_found') and len(critic.issues_found) > 2:
                print(f"   🔍 Research trigger: Critic found {len(critic.issues_found)} issues")
                return True
        
        return False
    
    def conduct_research(self, topic: str, llm_client, 
                        context: str = "") -> Dict[str, Any]:
        """
        Full research workflow: search → validate → summarize
        
        :param topic: Research topic
        :param llm_client: LLM client for summarization
        :param context: Additional context from agents
        :return: Research findings
        """
        print(f"   🔬 Conducting research on: {topic}")
        
        # Step 1: Search
        query = f"{topic} explanation tutorial"
        if context:
            query += f" {context[:100]}"  # Add brief context
        
        results = self.researcher.search(query, max_results=8)
        print(f"      Found {len(results)} results")
        
        if not results:
            return {
                "success": False,
                "reason": "No results found",
                "findings": ""
            }
        
        # Step 2: Validate sources
        validated = self.researcher.validate_sources(results, llm_client)
        print(f"      {len(validated)} sources validated")
        
        # Step 3: Summarize
        summary = self.researcher.summarize_results(
            validated, 
            llm_client, 
            focus_question=f"Explain {topic} clearly"
        )
        
        # Store in history
        self.research_history.append({
            "topic": topic,
            "timestamp": int(time.time()),
            "results_count": len(results),
            "validated_count": len(validated)
        })
        
        return {
            "success": True,
            "raw_results": [asdict(r) for r in validated],
            "summary": summary,
            "sources_count": len(validated)
        }


# Import for timestamp
import time
from dataclasses import asdict


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    # Mock LLM for testing
    class MockLLM:
        def generate(self, prompt, max_tokens=500):
            return """Summary: Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process information using connectionist approaches [1][2].

Sources:
[1] Wikipedia - Neural Network
[2] Britannica - Artificial Neural Network

Confidence: high
Contradictions: None"""
    
    # Test with mock SearXNG (in production: use real instance)
    # For demo, we'll simulate results
    
    class MockResearcher:
        def search(self, query, **kwargs):
            return [
                ResearchResult(
                    title="Introduction to Neural Networks",
                    url="https://en.wikipedia.org/wiki/Neural_network",
                    content="Neural networks are computing systems inspired by biological neural networks...",
                    source="Wikipedia",
                    score=0.95
                ),
                ResearchResult(
                    title="What is a Neural Network?",
                    url="https://www.ibm.com/topics/neural-networks",
                    content="A neural network is a method in artificial intelligence that teaches computers...",
                    source="IBM",
                    score=0.88
                )
            ]
        
        def validate_sources(self, results, llm):
            return results
        
        def summarize_results(self, results, llm, focus_question):
            return "Summary: Neural networks are AI systems inspired by biological brains [1][2]. Confidence: high"
    
    # Test trigger logic
    researcher = MockResearcher()
    trigger = ResearchTrigger(researcher, confidence_threshold=0.6)
    
    # Simulate low confidence scenario
    agent_outputs = {
        "simplifier": type('obj', (object,), {'confidence': 0.85}),
        "builder": type('obj', (object,), {'confidence': 0.72}),
        "critic": type('obj', (object,), {'confidence': 0.55, 'issues_found': ["Missing gradient explanation"]})
    }
    
    concept_graph = {"nodes": {}}
    
    # Should trigger research
    should_research = trigger.should_research(agent_outputs, "Neural Networks", concept_graph)
    print(f"\n🔍 Should research: {should_research}")
    
    if should_research:
        llm = MockLLM()
        findings = trigger.conduct_research("Neural Networks", llm)
        
        print("\n" + "="*60)
        print("RESEARCH FINDINGS:")
        print("="*60)
        print(findings['summary'])
        print(f"\nSources validated: {findings['sources_count']}")
    
    print("\n✅ SearXNG integration test complete!")
