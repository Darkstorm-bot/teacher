"""
MACT v2.0 - Multi-Modal Interface
Features: TTS Pipeline, Diagram DSL Generator, Video Script Prep, Unified Output
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class MediaType(Enum):
    TEXT = "text"
    AUDIO = "audio"
    DIAGRAM = "diagram"
    VIDEO = "video"


@dataclass
class TTSConfig:
    voice_id: str
    speed: float  # 0.5-2.0
    pitch: float  # 0.5-2.0
    volume: float  # 0.0-1.0
    format: str  # wav, mp3, ogg


@dataclass
class DiagramSpec:
    diagram_type: str  # mermaid, graphviz, d3
    content: str  # DSL code
    title: str
    description: str
    complexity: str  # simple, medium, complex


@dataclass
class VideoScene:
    scene_number: int
    duration_seconds: int
    narration_text: str
    visual_description: str
    on_screen_text: Optional[str]
    transitions: List[str]


@dataclass
class MultiModalOutput:
    output_id: str
    timestamp: str
    primary_content: str
    tts_ready: bool
    diagrams: List[DiagramSpec]
    video_scenes: List[VideoScene]
    metadata: Dict


class MultiModalInterface:
    def __init__(self, tts_engine=None, diagram_renderer=None):
        self.tts_engine = tts_engine  # Placeholder for Piper/Coqui
        self.diagram_renderer = diagram_renderer  # Placeholder for Mermaid/Graphviz
        
    def prepare_tts(
        self, 
        text: str, 
        config: Optional[TTSConfig] = None
    ) -> Dict:
        """
        Prepare text for Text-to-Speech synthesis
        Normalizes text, adds pauses, marks emphasis
        """
        if config is None:
            config = TTSConfig(
                voice_id="default",
                speed=1.0,
                pitch=1.0,
                volume=0.9,
                format="wav"
            )
        
        # Text normalization for TTS
        normalized_text = self._normalize_for_tts(text)
        
        # Add SSML-like markers (simplified)
        marked_text = self._add_speech_markers(normalized_text)
        
        return {
            "text": marked_text,
            "config": asdict(config),
            "estimated_duration_seconds": len(normalized_text.split()) * 0.4,  # ~150 wpm
            "word_count": len(normalized_text.split()),
            "ready_for_synthesis": True
        }
    
    def _normalize_for_tts(self, text: str) -> str:
        """
        Normalize text for better TTS pronunciation
        """
        # Replace common abbreviations
        replacements = {
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "and so on",
            "vs.": "versus",
            "Dr.": "Doctor",
            "Mr.": "Mister",
            "Mrs.": "Missus",
            "Ms.": "Miss",
            "Prof.": "Professor",
            "LLM": "L L M",
            "API": "A P I",
            "JSON": "jay-son",
            "HTTP": "H T T P",
        }
        
        normalized = text
        for abbr, full in replacements.items():
            normalized = normalized.replace(abbr, full)
        
        # Remove markdown formatting
        normalized = normalized.replace("**", "")
        normalized = normalized.replace("*", "")
        normalized = normalized.replace("`", "")
        
        # Simplify URLs
        import re
        normalized = re.sub(r'http[s]?://\S+', "link provided in notes", normalized)
        
        return normalized
    
    def _add_speech_markers(self, text: str) -> str:
        """
        Add speech markers for better prosody
        """
        # Add pauses after punctuation
        marked = text.replace(". ", ". <break time='0.3s'/> ")
        marked = marked.replace(", ", ", <break time='0.1s'/> ")
        marked = marked.replace("; ", "; <break time='0.2s'/> ")
        
        # Mark emphasis for key terms (simplified heuristic)
        sentences = marked.split(". ")
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            if len(words) > 5:
                # Emphasize first and last important words
                sentences[i] = f"<emphasis>{words[0]}</emphasis> " + " ".join(words[1:])
        
        return ". ".join(sentences)
    
    def generate_diagram_dsl(
        self,
        concept: str,
        relationships: List[Dict],
        diagram_type: str = "mermaid"
    ) -> DiagramSpec:
        """
        Generate diagram DSL code from concept relationships
        """
        if diagram_type == "mermaid":
            dsl_content = self._generate_mermaid_diagram(concept, relationships)
        elif diagram_type == "graphviz":
            dsl_content = self._generate_graphviz_diagram(concept, relationships)
        else:
            raise ValueError(f"Unsupported diagram type: {diagram_type}")
        
        # Determine complexity
        node_count = len(relationships) + 1
        if node_count < 5:
            complexity = "simple"
        elif node_count < 15:
            complexity = "medium"
        else:
            complexity = "complex"
        
        return DiagramSpec(
            diagram_type=diagram_type,
            content=dsl_content,
            title=f"{concept} - Concept Map",
            description=f"Visual representation of {concept} and related concepts",
            complexity=complexity
        )
    
    def _generate_mermaid_diagram(
        self, 
        concept: str, 
        relationships: List[Dict]
    ) -> str:
        """
        Generate Mermaid.js flowchart
        """
        lines = ["graph TD"]
        lines.append(f"    A[{concept}]")
        
        for i, rel in enumerate(relationships):
            node_id = chr(66 + i)  # B, C, D...
            target = rel.get("target", f"Concept_{i}")
            relation_type = rel.get("type", "relates_to")
            
            lines.append(f"    {node_id}[{target}]")
            
            # Different arrow styles for different relationships
            if relation_type == "prerequisite":
                lines.append(f"    {node_id} -->|requires| A")
            elif relation_type == "subtopic":
                lines.append(f"    A -->|includes| {node_id}")
            elif relation_type == "example":
                lines.append(f"    A -.->|example| {node_id}")
            else:
                lines.append(f"    A --> {node_id}")
        
        return "\n".join(lines)
    
    def _generate_graphviz_diagram(
        self,
        concept: str,
        relationships: List[Dict]
    ) -> str:
        """
        Generate Graphviz DOT format
        """
        lines = ["digraph G {"]
        lines.append("    rankdir=LR;")
        lines.append(f'    main [label="{concept}" shape=box style=filled fillcolor=lightblue];')
        
        for i, rel in enumerate(relationships):
            node_name = f"node_{i}"
            target = rel.get("target", f"Concept_{i}")
            relation_type = rel.get("type", "relates_to")
            
            lines.append(f'    {node_name} [label="{target}"];')
            
            if relation_type == "prerequisite":
                lines.append(f'    {node_name} -> main [label="requires"];')
            elif relation_type == "subtopic":
                lines.append(f'    main -> {node_name} [label="includes"];')
            else:
                lines.append(f'    main -> {node_name};')
        
        lines.append("}")
        return "\n".join(lines)
    
    def prepare_video_script(
        self,
        content: str,
        target_duration_minutes: int = 5
    ) -> List[VideoScene]:
        """
        Prepare content as a video script with scenes
        """
        # Split content into logical segments
        paragraphs = content.split("\n\n")
        words_per_minute = 150
        total_words = target_duration_minutes * words_per_minute
        
        # Distribute content across scenes
        scenes = []
        current_scene = 1
        words_in_scene = 0
        current_narration = []
        current_visual = []
        
        for para in paragraphs:
            words = para.split()
            words_in_scene += len(words)
            current_narration.append(para)
            
            # Generate visual description based on content
            if "example" in para.lower() or "code" in para.lower():
                current_visual.append("Show code snippet or example on screen")
            elif "diagram" in para.lower() or "visual" in para.lower():
                current_visual.append("Display diagram/visualization")
            else:
                current_visual.append("Presenter explains with gestures")
            
            # Create scene when we have enough content (~1 minute per scene)
            if words_in_scene >= words_per_minute or para == paragraphs[-1]:
                duration = min(60, words_in_scene * 0.4)  # seconds
                
                scenes.append(VideoScene(
                    scene_number=current_scene,
                    duration_seconds=int(duration),
                    narration_text=" ".join(current_narration),
                    visual_description="; ".join(current_visual),
                    on_screen_text=None,
                    transitions=["fade"] if current_scene > 1 else ["cut"]
                ))
                
                current_scene += 1
                words_in_scene = 0
                current_narration = []
                current_visual = []
        
        return scenes
    
    def create_multimodal_output(
        self,
        primary_content: str,
        include_tts: bool = True,
        include_diagrams: bool = True,
        include_video_prep: bool = False,
        concept_relationships: List[Dict] = None
    ) -> MultiModalOutput:
        """
        Create unified multi-modal output package
        """
        output_id = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare TTS
        tts_data = None
        if include_tts:
            tts_data = self.prepare_tts(primary_content)
        
        # Generate diagrams
        diagrams = []
        if include_diagrams and concept_relationships:
            diagram = self.generate_diagram_dsl(
                concept="Main Concept",
                relationships=concept_relationships
            )
            diagrams.append(diagram)
        
        # Prepare video script
        video_scenes = []
        if include_video_prep:
            video_scenes = self.prepare_video_script(primary_content)
        
        return MultiModalOutput(
            output_id=output_id,
            timestamp=datetime.now().isoformat(),
            primary_content=primary_content,
            tts_ready=tts_data is not None,
            diagrams=diagrams,
            video_scenes=video_scenes,
            metadata={
                "tts_config": tts_data["config"] if tts_data else None,
                "diagram_count": len(diagrams),
                "scene_count": len(video_scenes),
                "word_count": len(primary_content.split())
            }
        )
    
    def export_for_frontend(self, output: MultiModalOutput) -> Dict:
        """
        Export multi-modal output in frontend-ready format
        """
        return {
            "output_id": output.output_id,
            "timestamp": output.timestamp,
            "content": {
                "text": output.primary_content,
                "tts": output.tts_ready,
                "diagrams": [asdict(d) for d in output.diagrams],
                "video_scenes": [asdict(s) for s in output.video_scenes]
            },
            "metadata": output.metadata,
            "render_hints": {
                "show_diagram_viewer": len(output.diagrams) > 0,
                "show_video_timeline": len(output.video_scenes) > 0,
                "enable_tts_controls": output.tts_ready
            },
            "tts_config": output.metadata.get("tts_config")
        }


# Example usage
if __name__ == "__main__":
    interface = MultiModalInterface()
    
    # Sample educational content
    content = """
    Neural networks are computational models inspired by biological neurons.
    
    They consist of layers: input layer receives data, hidden layers process it, 
    and output layer produces predictions.
    
    For example, in image recognition: the input is pixel values, hidden layers 
    detect edges and patterns, and the output identifies the object.
    
    Training involves adjusting weights through backpropagation to minimize errors.
    """
    
    # Concept relationships for diagram
    relationships = [
        {"target": "Input Layer", "type": "subtopic"},
        {"target": "Hidden Layers", "type": "subtopic"},
        {"target": "Output Layer", "type": "subtopic"},
        {"target": "Backpropagation", "type": "prerequisite"},
        {"target": "Image Recognition", "type": "example"}
    ]
    
    # Create multi-modal output
    output = interface.create_multimodal_output(
        primary_content=content,
        include_tts=True,
        include_diagrams=True,
        include_video_prep=True,
        concept_relationships=relationships
    )
    
    # Export for frontend
    frontend_data = interface.export_for_frontend(output)
    
    print("=== MULTI-MODAL OUTPUT ===\n")
    print(f"Output ID: {frontend_data['output_id']}")
    print(f"Word Count: {frontend_data['metadata']['word_count']}")
    print(f"TTS Ready: {frontend_data['content']['tts']}")
    print(f"Diagrams: {frontend_data['metadata']['diagram_count']}")
    print(f"Video Scenes: {frontend_data['metadata']['scene_count']}")
    
    print("\n=== DIAGRAM DSL (Mermaid) ===")
    if frontend_data['content']['diagrams']:
        print(frontend_data['content']['diagrams'][0]['content'])
    
    print("\n=== VIDEO SCRIPT PREVIEW ===")
    for scene in frontend_data['content']['video_scenes'][:2]:
        print(f"\nScene {scene['scene_number']} ({scene['duration_seconds']}s):")
        print(f"  Visual: {scene['visual_description']}")
        print(f"  Narration: {scene['narration_text'][:100]}...")
    
    print("\n=== RENDER HINTS ===")
    print(json.dumps(frontend_data['render_hints'], indent=2))
