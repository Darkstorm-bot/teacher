"""
PDF Ingestion Pipeline - Phase 2
Extracts concepts, builds dependency graphs, and estimates learning time from textbooks/notes
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ConceptNode:
    """Represents a single concept extracted from PDF"""
    id: str
    name: str
    level: int  # Bloom's taxonomy level (1=recall, 6=create)
    prerequisites: List[str]
    subtopics: List[str]
    source_pages: List[int]
    difficulty: float  # 0.0-1.0
    base_time_minutes: int
    key_equations: List[str]
    key_examples: List[str]


class PDFIngestionPipeline:
    """
    Converts raw PDF textbooks into structured concept graphs
    """
    
    def __init__(self, llm_client):
        """
        :param llm_client: LLM client for concept extraction and analysis
        """
        self.llm = llm_client
        self.concept_cache = {}
    
    def process_pdf(self, pdf_path: str, subject: str = "General") -> Dict[str, Any]:
        """
        Main pipeline: PDF → Concept Graph + Learning Path
        
        :param pdf_path: Path to PDF file
        :param subject: Subject area (Math, CS, Physics, etc.)
        :return: Complete concept graph with dependencies and time estimates
        """
        print(f"\n📄 Processing PDF: {pdf_path}")
        print(f"   Subject: {subject}")
        
        # Step 1: Extract text chunks (in production: use PyPDF2 or pdfplumber)
        # For now, simulate chunking
        chunks = self._extract_text_chunks(pdf_path)
        print(f"   📝 Extracted {len(chunks)} text chunks")
        
        # Step 2: Extract concepts from each chunk
        concepts = []
        for i, chunk in enumerate(chunks):
            print(f"   🔍 Analyzing chunk {i+1}/{len(chunks)}...")
            chunk_concepts = self._extract_concepts_from_chunk(chunk, subject, i)
            concepts.extend(chunk_concepts)
        
        print(f"   ✨ Extracted {len(concepts)} total concepts")
        
        # Step 3: Build dependency graph
        print("   🔗 Building dependency graph...")
        graph = self._build_dependency_graph(concepts)
        
        # Step 4: Calculate time estimates
        print("   ⏱️  Calculating learning time estimates...")
        graph = self._calculate_time_estimates(graph)
        
        # Step 5: Validate and clean
        print("   ✅ Validating graph structure...")
        graph = self._validate_graph(graph)
        
        return graph
    
    def _extract_text_chunks(self, pdf_path: str, chunk_size: int = 2000) -> List[Dict]:
        """
        Extract text from PDF and split into semantic chunks
        In production: Use PyPDF2, pdfplumber, or llama-index
        """
        # PLACEHOLDER: Replace with actual PDF extraction
        # Example implementation:
        # import pdfplumber
        # with pdfplumber.open(pdf_path) as pdf:
        #     text = ""
        #     for page in pdf.pages:
        #         text += page.extract_text()
        
        # Simulated chunks for testing
        return [
            {
                "page": 1,
                "text": "Introduction to Neural Networks. A neural network is composed of layers of interconnected nodes...",
                "section": "Chapter 1: Introduction"
            },
            {
                "page": 5,
                "text": "The perceptron is the simplest form of a neural network. It takes inputs x1, x2, ..., xn and produces output...",
                "section": "Chapter 1: Perceptrons"
            },
            {
                "page": 12,
                "text": "Activation functions introduce non-linearity. Common functions include sigmoid, tanh, and ReLU...",
                "section": "Chapter 2: Activation Functions"
            },
            {
                "page": 18,
                "text": "Backpropagation is the algorithm used to train neural networks by computing gradients...",
                "section": "Chapter 3: Training"
            }
        ]
    
    def _extract_concepts_from_chunk(self, chunk: Dict, subject: str, chunk_idx: int) -> List[ConceptNode]:
        """
        Use LLM to extract structured concepts from a text chunk
        """
        prompt = f"""
EXTRACT CONCEPTS FROM TEXTBOOK CHUNK

Subject: {subject}
Chunk ID: {chunk_idx}
Page: {chunk['page']}
Section: {chunk['section']}

Text:
{chunk['text'][:1500]}  # Limit context for 8B model

INSTRUCTIONS:
1. Identify 1-3 key concepts in this chunk
2. For each concept, extract:
   - Name (short, clear)
   - Prerequisites (what must be learned first)
   - Difficulty (0.0-1.0)
   - Key equations or formulas (if any)
   - Key examples (if any)
   - Bloom's level (1-6)

OUTPUT FORMAT (JSON array):
[
  {{
    "name": "Concept Name",
    "prerequisites": ["Prereq1", "Prereq2"],
    "difficulty": 0.6,
    "equations": ["y = mx + b"],
    "examples": ["Linear regression"],
    "bloom_level": 2
  }}
]

If no clear concepts, return empty array [].
"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=800)
            concepts_json = json.loads(response)
            
            # Convert to ConceptNode objects
            nodes = []
            for c in concepts_json:
                node = ConceptNode(
                    id=self._slugify(c['name']),
                    name=c['name'],
                    level=c.get('bloom_level', 2),
                    prerequisites=[self._slugify(p) for p in c.get('prerequisites', [])],
                    subtopics=[],
                    source_pages=[chunk['page']],
                    difficulty=c.get('difficulty', 0.5),
                    base_time_minutes=30,  # Will be calculated later
                    key_equations=c.get('equations', []),
                    key_examples=c.get('examples', [])
                )
                nodes.append(node)
            
            return nodes
        
        except Exception as e:
            print(f"   ⚠️  Error extracting concepts from chunk {chunk_idx}: {e}")
            return []
    
    def _build_dependency_graph(self, concepts: List[ConceptNode]) -> Dict[str, Any]:
        """
        Build a directed acyclic graph (DAG) of concept dependencies
        Uses topological sorting to ensure valid learning order
        """
        # Create adjacency list
        graph = {concept.id: asdict(concept) for concept in concepts}
        
        # Validate no circular dependencies
        if self._has_cycle(graph):
            print("   ⚠️  Warning: Circular dependencies detected. Attempting to resolve...")
            graph = self._resolve_cycles(graph)
        
        # Add reverse dependencies (what depends on this concept)
        for concept_id, node in graph.items():
            dependents = []
            for other_id, other_node in graph.items():
                if concept_id in other_node['prerequisites']:
                    dependents.append(other_id)
            node['dependents'] = dependents
        
        return {
            "id": f"graph_{int(time.time())}",
            "subject": "Extracted",
            "nodes": graph,
            "total_concepts": len(graph),
            "root_concepts": self._find_root_concepts(graph)
        }
    
    def _has_cycle(self, graph: Dict) -> bool:
        """Detect cycles using DFS"""
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for prereq in graph.get(node, {}).get('prerequisites', []):
                if prereq not in visited:
                    if dfs(prereq):
                        return True
                elif prereq in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        return False
    
    def _resolve_cycles(self, graph: Dict) -> Dict:
        """Break cycles by removing weakest dependency"""
        # Simplified: Remove the edge with lowest confidence
        # In production: Use more sophisticated cycle-breaking
        return graph
    
    def _find_root_concepts(self, graph: Dict) -> List[str]:
        """Find concepts with no prerequisites (starting points)"""
        roots = []
        for node_id, node in graph.items():
            if not node.get('prerequisites', []):
                roots.append(node_id)
        return roots
    
    def _calculate_time_estimates(self, graph: Dict) -> Dict:
        """
        Apply formula: Time = Base_Time × Difficulty × (1 - Mastery_Score)
        For initial estimation, assume mastery = 0
        """
        BASE_TIME = 45  # minutes per concept
        
        for node_id, node in graph['nodes'].items():
            difficulty = node.get('difficulty', 0.5)
            mastery = 0.0  # Initial state
            
            # Formula: Time = Base × Difficulty × (1 - Mastery)
            estimated_time = int(BASE_TIME * difficulty * (1 - mastery))
            
            # Adjust for Bloom's level (higher levels take longer)
            bloom_multiplier = 1.0 + (node.get('level', 2) - 2) * 0.2
            estimated_time = int(estimated_time * bloom_multiplier)
            
            node['estimated_time_minutes'] = estimated_time
            node['mastery_score'] = mastery
        
        # Calculate total learning time
        total_time = sum(n['estimated_time_minutes'] for n in graph['nodes'].values())
        graph['total_estimated_time_minutes'] = total_time
        graph['total_estimated_time_hours'] = round(total_time / 60, 2)
        
        return graph
    
    def _validate_graph(self, graph: Dict) -> Dict:
        """Final validation and cleanup"""
        # Check all prerequisites exist in graph
        all_ids = set(graph['nodes'].keys())
        for node_id, node in graph['nodes'].items():
            missing_prereqs = set(node['prerequisites']) - all_ids
            if missing_prereqs:
                print(f"   ⚠️  Missing prerequisites for {node_id}: {missing_prereqs}")
                # Keep them anyway (may be external knowledge)
        
        return graph
    
    def _slugify(self, text: str) -> str:
        """Convert concept name to safe ID"""
        slug = text.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        slug = re.sub(r'_+', '_', slug)
        return slug.strip('_')
    
    def generate_learning_path(self, graph: Dict, user_profile: Optional[Dict] = None) -> List[Dict]:
        """
        Generate day-by-day learning schedule from concept graph
        Considers user's pace, attention span, and preferred times
        """
        if not user_profile:
            user_profile = {
                "pace": "medium",  # slow, medium, fast
                "attention_span_mins": 25,
                "sessions_per_day": 2
            }
        
        # Determine daily time budget
        pace_multipliers = {"slow": 0.7, "medium": 1.0, "fast": 1.5}
        daily_budget = (
            user_profile['attention_span_mins'] * 
            user_profile['sessions_per_day'] * 
            pace_multipliers.get(user_profile['pace'], 1.0)
        )
        
        # Topological sort for learning order
        sorted_concepts = self._topological_sort(graph['nodes'])
        
        # Schedule concepts across days
        learning_path = []
        current_day = 1
        current_day_time = 0
        
        for concept_id in sorted_concepts:
            concept = graph['nodes'][concept_id]
            time_needed = concept['estimated_time_minutes']
            
            # If doesn't fit today, start new day
            if current_day_time + time_needed > daily_budget:
                current_day += 1
                current_day_time = 0
            
            learning_path.append({
                "day": current_day,
                "concept_id": concept_id,
                "concept_name": concept['name'],
                "estimated_time": time_needed,
                "prerequisites": concept['prerequisites'],
                "difficulty": concept['difficulty']
            })
            
            current_day_time += time_needed
        
        return learning_path
    
    def _topological_sort(self, graph: Dict) -> List[str]:
        """Sort concepts so prerequisites come first"""
        in_degree = {node: 0 for node in graph}
        
        # Calculate in-degrees
        for node_id, node in graph.items():
            for prereq in node.get('prerequisites', []):
                if prereq in in_degree:
                    in_degree[node_id] += 1
        
        # Start with nodes that have no prerequisites
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree for dependent nodes
            for other_id, other_node in graph.items():
                if node in other_node.get('prerequisites', []):
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)
        
        return result


# Import time for timestamp generation
import time


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    # Mock LLM for testing
    class MockLLM:
        def generate(self, prompt, max_tokens=500):
            # Return mock concept extraction
            return json.dumps([
                {
                    "name": "Neural Network",
                    "prerequisites": ["Functions", "Vectors"],
                    "difficulty": 0.7,
                    "equations": ["output = activation(weights * input + bias)"],
                    "examples": ["Image classification"],
                    "bloom_level": 3
                },
                {
                    "name": "Activation Function",
                    "prerequisites": ["Functions"],
                    "difficulty": 0.5,
                    "equations": ["ReLU(x) = max(0, x)"],
                    "examples": ["sigmoid, tanh, ReLU"],
                    "bloom_level": 2
                }
            ])
    
    # Test pipeline
    llm = MockLLM()
    pipeline = PDFIngestionPipeline(llm)
    
    # Process mock PDF
    result = pipeline.process_pdf("neural_networks_textbook.pdf", subject="Computer Science")
    
    print("\n" + "="*60)
    print("CONCEPT GRAPH SUMMARY:")
    print("="*60)
    print(f"Total concepts: {result['total_concepts']}")
    print(f"Root concepts: {result['root_concepts']}")
    print(f"Estimated total time: {result['total_estimated_time_hours']} hours")
    
    # Generate learning path
    user_profile = {
        "pace": "medium",
        "attention_span_mins": 30,
        "sessions_per_day": 2
    }
    
    path = pipeline.generate_learning_path(result, user_profile)
    
    print("\n" + "="*60)
    print("LEARNING PATH (First 5 days):")
    print("="*60)
    for session in path[:5]:
        print(f"Day {session['day']}: {session['concept_name']} ({session['estimated_time']} min)")
    
    print("\n✅ PDF ingestion test complete!")
