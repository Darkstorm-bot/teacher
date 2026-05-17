"""PDF Ingestion Pipeline for extracting concepts and building knowledge graphs."""
import hashlib
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Will be installed: pymupdf (fitz), nltk
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from api.services.llm import LLMClient
from api.services.knowledge_graph import KnowledgeGraph
from api.services.memory_palace import MemoryPalace
from api.core.database import DatabaseManager


class PDFIngestionPipeline:
    """
    Pipeline for processing PDF textbooks/notes into structured concept graphs.
    
    Flow:
    1. Extract text from PDF
    2. Chunk semantically (by section/paragraph)
    3. Extract concepts using LLM
    4. Identify prerequisites and dependencies
    5. Score difficulty
    6. Estimate learning time
    7. Store in Knowledge Graph + Memory Palace
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.kg = KnowledgeGraph()
        self.db = DatabaseManager()
        self.memory = MemoryPalace()
        
        # Ensure NLTK data is available
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF with page-level granularity.
        
        Returns:
            {
                "metadata": {...},
                "pages": [
                    {"page_num": 1, "text": "...", "sections": [...]},
                    ...
                ]
            }
        """
        if not PDF_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        
        # Extract metadata
        metadata = {
            "filename": pdf_path.name,
            "path": str(pdf_path.absolute()),
            "num_pages": len(doc),
            "metadata": doc.metadata,
            "extracted_at": datetime.now().isoformat()
        }
        
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Basic section detection (can be improved with layout analysis)
            sections = self._detect_sections(text, page_num)
            
            pages.append({
                "page_num": page_num + 1,
                "text": text,
                "sections": sections,
                "has_images": len(page.get_images()) > 0,
                "has_tables": self._detect_tables(text)
            })
        
        doc.close()
        
        return {
            "metadata": metadata,
            "pages": pages
        }
    
    def _detect_sections(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Detect sections/chapters in text based on headings."""
        sections = []
        lines = text.split('\n')
        
        current_section = {
            "title": None,
            "start_line": 0,
            "content_lines": []
        }
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            # Detect heading patterns (common in textbooks)
            is_heading = (
                (len(stripped) < 100 and stripped.endswith(':')) or
                (stripped.startswith(('Chapter ', 'Section ', '§', '##', '# '))) or
                (stripped.isupper() and len(stripped) < 80) or
                (re.match(r'^\d+(\.\d+)*\s+[A-Z]', stripped))
            )
            
            if is_heading and current_section["content_lines"]:
                # Save previous section
                sections.append({
                    "title": current_section["title"] or f"Section_{page_num}_{current_section['start_line']}",
                    "start_line": current_section["start_line"],
                    "end_line": i - 1,
                    "content": '\n'.join(current_section["content_lines"])
                })
                # Start new section
                current_section = {
                    "title": stripped.rstrip(':'),
                    "start_line": i,
                    "content_lines": []
                }
            else:
                current_section["content_lines"].append(line)
        
        # Add final section
        if current_section["content_lines"]:
            sections.append({
                "title": current_section["title"] or f"Section_{page_num}_final",
                "start_line": current_section["start_line"],
                "end_line": len(lines) - 1,
                "content": '\n'.join(current_section["content_lines"])
            })
        
        return sections
    
    def _detect_tables(self, text: str) -> bool:
        """Simple heuristic to detect table-like structures."""
        lines = text.split('\n')
        table_indicators = 0
        
        for line in lines[:20]:  # Check first 20 lines
            if '|' in line and line.count('|') >= 3:
                table_indicators += 1
            if re.match(r'^[\s\-+=]+$', line):
                table_indicators += 1
        
        return table_indicators >= 2
    
    def chunk_text(self, extracted_data: Dict[str, Any], 
                   max_chunk_size: int = 1000,
                   overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Chunk text semantically while preserving context.
        
        Strategy:
        - Prefer section boundaries
        - Fall back to paragraph boundaries
        - Ensure chunks don't exceed max size
        """
        chunks = []
        chunk_id = 0
        
        for page in extracted_data["pages"]:
            for section in page["sections"]:
                content = section["content"]
                
                # If section is small enough, keep it as one chunk
                if len(content) <= max_chunk_size:
                    chunks.append({
                        "chunk_id": f"chunk_{chunk_id}",
                        "source": extracted_data["metadata"]["filename"],
                        "page": page["page_num"],
                        "section": section["title"],
                        "content": content,
                        "start_line": section["start_line"],
                        "end_line": section["end_line"]
                    })
                    chunk_id += 1
                else:
                    # Split large sections into paragraphs
                    paragraphs = content.split('\n\n')
                    current_chunk = []
                    current_size = 0
                    
                    for para in paragraphs:
                        para_size = len(para)
                        
                        if current_size + para_size > max_chunk_size and current_chunk:
                            # Save current chunk
                            chunks.append({
                                "chunk_id": f"chunk_{chunk_id}",
                                "source": extracted_data["metadata"]["filename"],
                                "page": page["page_num"],
                                "section": section["title"],
                                "content": '\n\n'.join(current_chunk),
                                "is_partial": True
                            })
                            chunk_id += 1
                            
                            # Keep overlap
                            overlap_text = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk[-1:]
                            current_chunk = overlap_text
                            current_size = sum(len(t) for t in current_chunk)
                        
                        current_chunk.append(para)
                        current_size += para_size
                    
                    # Add final chunk
                    if current_chunk:
                        chunks.append({
                            "chunk_id": f"chunk_{chunk_id}",
                            "source": extracted_data["metadata"]["filename"],
                            "page": page["page_num"],
                            "section": section["title"],
                            "content": '\n\n'.join(current_chunk)
                        })
                        chunk_id += 1
        
        return chunks
    
    def extract_concepts_from_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Use LLM to extract concepts from a text chunk.
        
        Returns list of concepts with:
        - name
        - description
        - difficulty (0-1)
        - type (definition, formula, example, theorem, etc.)
        """
        import asyncio
        
        prompt = f"""
Analyze this textbook excerpt and extract key learning concepts.

TEXT:
{chunk['content'][:2000]}  # Limit to avoid token explosion

For each concept, provide:
1. name: Short identifier (snake_case)
2. display_name: Human-readable name
3. description: One-sentence explanation
4. type: One of [definition, formula, theorem, example, procedure, concept]
5. difficulty: Float 0.0-1.0 (how hard for average student)
6. prerequisites: List of prerequisite concept names (if mentioned)

Return ONLY valid JSON array:
[
  {{
    "name": "concept_name",
    "display_name": "Concept Name",
    "description": "...",
    "type": "definition",
    "difficulty": 0.5,
    "prerequisites": ["prereq1", "prereq2"]
  }}
]

If no clear concepts found, return empty array [].
"""
        
        try:
            # Run async generate in sync context
            response = asyncio.run(self.llm.generate(prompt, temperature=0.3, max_tokens=1000))
            # Parse JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                concepts = json.loads(json_match.group())
                
                # Add metadata
                for concept in concepts:
                    concept["source_chunk"] = chunk["chunk_id"]
                    concept["source_page"] = chunk["page"]
                    concept["source_section"] = chunk["section"]
                    concept["source_file"] = chunk["source"]
                
                return concepts
            return []
        except Exception as e:
            print(f"Error extracting concepts: {e}")
            return []
    
    def build_concept_graph(self, all_concepts: List[Dict[str, Any]], 
                           subject: str, level: str) -> Dict[str, Any]:
        """
        Build concept dependency graph from extracted concepts.
        
        Steps:
        1. Deduplicate concepts
        2. Infer additional prerequisites using LLM
        3. Create nodes and edges
        4. Calculate global difficulty scores
        """
        # Deduplicate by name
        unique_concepts = {}
        for concept in all_concepts:
            key = concept["name"].lower()
            if key not in unique_concepts:
                unique_concepts[key] = concept
            else:
                # Merge: keep higher difficulty, combine prerequisites
                existing = unique_concepts[key]
                existing["difficulty"] = max(existing["difficulty"], concept["difficulty"])
                existing_prereqs = set(existing.get("prerequisites", []))
                new_prereqs = set(concept.get("prerequisites", []))
                existing["prerequisites"] = list(existing_prereqs | new_prereqs)
        
        concepts_list = list(unique_concepts.values())
        
        # Use LLM to infer missing prerequisites and validate
        enriched_concepts = self._enrich_concepts_with_llm(concepts_list, subject)
        
        # Build graph structure
        nodes = []
        edges = []
        
        concept_names = {c["name"].lower() for c in enriched_concepts}
        
        for concept in enriched_concepts:
            # Add node
            nodes.append({
                "id": concept["name"],
                "subject": subject,
                "level": level,
                "display_name": concept["display_name"],
                "description": concept["description"],
                "difficulty": concept["difficulty"],
                "concept_type": concept["type"],
                "source": concept.get("source_file"),
                "page": concept.get("source_page")
            })
            
            # Add prerequisite edges
            for prereq in concept.get("prerequisites", []):
                prereq_lower = prereq.lower()
                # Only add edge if prerequisite exists in our concept set
                if prereq_lower in concept_names:
                    edges.append({
                        "source_id": prereq,
                        "target_id": concept["name"],
                        "relation": "prerequisite",
                        "weight": 1.0,
                        "cross_subject": False
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "subject": subject,
                "level": level,
                "total_concepts": len(nodes),
                "total_dependencies": len(edges),
                "created_at": datetime.now().isoformat()
            }
        }
    
    def _enrich_concepts_with_llm(self, concepts: List[Dict[str, Any]], 
                                   subject: str) -> List[Dict[str, Any]]:
        """Use LLM to validate and enrich concepts with additional prerequisites."""
        if not concepts:
            return []
        
        import asyncio
        
        # Process in batches to avoid token limits
        batch_size = 10
        enriched = []
        
        for i in range(0, len(concepts), batch_size):
            batch = concepts[i:i+batch_size]
            
            prompt = f"""
Given these concepts from {subject} textbook, identify missing prerequisites and validate difficulty scores.

CONCEPTS:
{json.dumps(batch, indent=2)}

For each concept:
1. Verify difficulty score (adjust if needed based on typical {subject} curriculum)
2. Add any obvious prerequisites that are missing
3. Ensure prerequisite names match existing concept names where possible

Return ONLY valid JSON array with same structure but enriched data.
"""
            
            try:
                response = asyncio.run(self.llm.generate(prompt, temperature=0.2, max_tokens=1500))
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    batch_enriched = json.loads(json_match.group())
                    enriched.extend(batch_enriched)
                else:
                    enriched.extend(batch)  # Keep original if parsing fails
            except Exception as e:
                print(f"Error enriching batch: {e}")
                enriched.extend(batch)
        
        return enriched
    
    def estimate_learning_time(self, concept: Dict[str, Any], 
                               user_mastery: float = 0.0) -> float:
        """
        Estimate time (in minutes) to learn a concept.
        
        Formula:
        Time = Base_Time × Difficulty_Multiplier × (1 - Mastery_Score) × Complexity_Factor
        
        Base times by concept type:
        - definition: 15 min
        - concept: 30 min
        - procedure: 45 min
        - formula: 40 min
        - theorem: 60 min
        - example: 20 min
        """
        base_times = {
            "definition": 15,
            "concept": 30,
            "procedure": 45,
            "formula": 40,
            "theorem": 60,
            "example": 20
        }
        
        concept_type = concept.get("type", "concept")
        base_time = base_times.get(concept_type, 30)
        
        difficulty = concept.get("difficulty", 0.5)
        difficulty_multiplier = 0.5 + (difficulty * 1.5)  # Range: 0.5-2.0
        
        mastery_factor = max(0.1, 1.0 - user_mastery)  # Never zero
        
        # Complexity factor based on number of prerequisites
        num_prereqs = len(concept.get("prerequisites", []))
        complexity_factor = 1.0 + (num_prereqs * 0.1)  # +10% per prereq
        
        estimated_time = base_time * difficulty_multiplier * mastery_factor * complexity_factor
        
        return round(estimated_time, 1)
    
    def process_pdf(self, pdf_path: str, subject: str, level: str,
                    store_in_graph: bool = True,
                    store_in_memory: bool = True) -> Dict[str, Any]:
        """
        Full pipeline: PDF → Concepts → Graph → Storage
        
        Args:
            pdf_path: Path to PDF file
            subject: Subject name (e.g., "matematik", "fysik")
            level: Level (e.g., "C", "B", "A")
            store_in_graph: Whether to store in Knowledge Graph
            store_in_memory: Whether to store in Memory Palace
        
        Returns:
            {
                "metadata": {...},
                "concepts": [...],
                "graph": {...},
                "time_estimates": {...},
                "stored": bool
            }
        """
        print(f"Processing PDF: {pdf_path}")
        
        # Step 1: Extract text
        extracted = self.extract_text_from_pdf(pdf_path)
        print(f"Extracted {len(extracted['pages'])} pages")
        
        # Step 2: Chunk text
        chunks = self.chunk_text(extracted)
        print(f"Created {len(chunks)} chunks")
        
        # Step 3: Extract concepts from each chunk
        all_concepts = []
        for chunk in chunks:
            concepts = self.extract_concepts_from_chunk(chunk)
            all_concepts.extend(concepts)
            print(f"Chunk {chunk['chunk_id']}: {len(concepts)} concepts")
        
        print(f"Total concepts extracted: {len(all_concepts)}")
        
        # Step 4: Build concept graph
        graph = self.build_concept_graph(all_concepts, subject, level)
        print(f"Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
        
        # Step 5: Calculate time estimates
        time_estimates = {}
        for concept in graph["nodes"]:
            time_estimates[concept["id"]] = {
                "estimated_minutes": self.estimate_learning_time(concept),
                "difficulty": concept["difficulty"],
                "prerequisites_count": len([e for e in graph["edges"] 
                                           if e["target_id"] == concept["id"]])
            }
        
        # Step 6: Store in database
        stored = False
        if store_in_graph:
            self._store_graph_in_db(graph)
            stored = True
            print("Stored in Knowledge Graph")
        
        if store_in_memory:
            self._store_in_memory_palace(extracted, graph, pdf_path)
            print("Stored in Memory Palace")
        
        return {
            "metadata": extracted["metadata"],
            "concepts": graph["nodes"],
            "graph": graph,
            "time_estimates": time_estimates,
            "stored": stored,
            "stats": {
                "pages_processed": len(extracted["pages"]),
                "chunks_created": len(chunks),
                "concepts_extracted": len(graph["nodes"]),
                "dependencies_found": len(graph["edges"])
            }
        }
    
    def _store_graph_in_db(self, graph: Dict[str, Any]):
        """Store concept graph in database."""
        for node in graph["nodes"]:
            self.db.add_concept_node(
                concept_id=node["id"],
                subject=node["subject"],
                level=node["level"],
                display_name=node["display_name"],
                description=node.get("description"),
                curriculum_ref=node.get("source")
            )
        
        for edge in graph["edges"]:
            self.db.add_concept_edge(
                source_id=edge["source_id"],
                target_id=edge["target_id"],
                relation=edge["relation"],
                weight=edge.get("weight", 1.0),
                cross_subject=edge.get("cross_subject", False)
            )
    
    def _store_in_memory_palace(self, extracted: Dict[str, Any], 
                                 graph: Dict[str, Any],
                                 pdf_path: str):
        """Store processed PDF data in Memory Palace."""
        wing = f"Subject_{graph['metadata']['subject']}"
        room = f"Textbook_{Path(pdf_path).stem}"
        
        # Store metadata
        self.memory.store(
            wing=wing,
            room=room,
            hall="Metadata",
            content=json.dumps(extracted["metadata"], indent=2),
            memory_type="pdf_metadata",
            topic=graph["metadata"]["subject"],
            source=pdf_path
        )
        
        # Store concept graph summary
        graph_summary = {
            "total_concepts": graph["metadata"]["total_concepts"],
            "total_dependencies": graph["metadata"]["total_dependencies"],
            "concept_list": [{"id": n["id"], "name": n["display_name"]} 
                            for n in graph["nodes"]],
            "created_at": graph["metadata"]["created_at"]
        }
        
        self.memory.store(
            wing=wing,
            room=room,
            hall="ConceptGraph",
            content=json.dumps(graph_summary, indent=2),
            memory_type="concept_graph_summary",
            topic=graph["metadata"]["subject"]
        )
        
        # Store detailed concept data (in drawers by concept type)
        concepts_by_type = {}
        for node in graph["nodes"]:
            concept_type = node.get("concept_type", "concept")
            if concept_type not in concepts_by_type:
                concepts_by_type[concept_type] = []
            concepts_by_type[concept_type].append(node)
        
        for concept_type, concepts in concepts_by_type.items():
            drawer = f"{concept_type}s"
            content = json.dumps(concepts, indent=2)
            
            self.memory.store(
                wing=wing,
                room=room,
                hall="ConceptGraph",
                drawer=drawer,
                content=content,
                memory_type="concepts_detailed",
                topic=graph["metadata"]["subject"]
            )


# Convenience function for quick usage
def ingest_pdf(pdf_path: str, subject: str, level: str, 
               llm_client: LLMClient = None) -> Dict[str, Any]:
    """
    Quick function to ingest a PDF and build concept graph.
    
    Example:
        result = ingest_pdf("math_book.pdf", "matematik", "B")
        print(f"Extracted {result['stats']['concepts_extracted']} concepts")
    """
    pipeline = PDFIngestionPipeline(llm_client)
    return pipeline.process_pdf(pdf_path, subject, level)
