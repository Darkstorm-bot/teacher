import { useState, useEffect, useRef, useCallback } from "react";
import { api, type KnowledgeGraph as KGType } from "@/services/api";
import { Badge } from "@/components/ui/badge";
import { GitFork, Loader2, ZoomIn, ZoomOut, Maximize, BookOpen, Atom, Monitor, PenTool } from "lucide-react";

const subjectColors: Record<string, string> = {
  matematik: "#58a6ff",
  fysik: "#3fb950",
  datalogi: "#d2a8ff",
  kommunikation: "#f0883e",
};

const subjectIcons: Record<string, React.ReactNode> = {
  matematik: <BookOpen className="w-4 h-4" />,
  fysik: <Atom className="w-4 h-4" />,
  datalogi: <Monitor className="w-4 h-4" />,
  kommunikation: <PenTool className="w-4 h-4" />,
};

export default function KnowledgeGraph() {
  const [graph, setGraph] = useState<KGType | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLDivElement>(null);
  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());

  useEffect(() => {
    loadGraph();
  }, [selectedSubject]);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const data = await api.getKnowledgeGraph(selectedSubject || undefined);
      setGraph(data);
      // Calculate node positions using simple force-directed layout
      calculatePositions(data);
    } catch (err) {
      console.error("Failed to load graph:", err);
    } finally {
      setLoading(false);
    }
  };

  const calculatePositions = (data: KGType) => {
    const { nodes } = data;
    const positions = new Map<string, { x: number; y: number }>();

    // Group nodes by subject
    const bySubject: Record<string, typeof nodes> = {};
    nodes.forEach((n) => {
      if (!bySubject[n.subject]) bySubject[n.subject] = [];
      bySubject[n.subject].push(n);
    });

    // Position subjects in different quadrants
    const subjectAngles: Record<string, number> = {
      matematik: -Math.PI / 2,
      fysik: 0,
      datalogi: Math.PI,
      kommunikation: Math.PI / 2,
    };

    const centerX = 400;
    const centerY = 300;
    const radius = 200;

    Object.entries(bySubject).forEach(([subject, subjectNodes]) => {
      const baseAngle = subjectAngles[subject] || 0;
      subjectNodes.forEach((node, i) => {
        const angle = baseAngle + (i - subjectNodes.length / 2) * 0.4;
        const r = radius + (node.level === "A" ? 80 : node.level === "B" ? 40 : 0);
        positions.set(node.id, {
          x: centerX + r * Math.cos(angle),
          y: centerY + r * Math.sin(angle),
        });
      });
    });

    nodePositionsRef.current = positions;
  };

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale((s) => Math.min(Math.max(s * delta, 0.3), 3));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === canvasRef.current || (e.target as HTMLElement).closest(".graph-canvas")) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    }
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const getPrereqsForNode = (nodeId: string) => {
    if (!graph) return [];
    return graph.edges.filter(
      (e) => e.target_id === nodeId && e.relation === "prerequisite"
    );
  };

  const getApplicationsForNode = (nodeId: string) => {
    if (!graph) return [];
    return graph.edges.filter(
      (e) => e.source_id === nodeId && e.relation === "applies_to"
    );
  };

  const selectedNodeData = graph?.nodes.find((n) => n.id === selectedNode);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No knowledge graph data available
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Graph Canvas */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-card/30">
          <GitFork className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Knowledge Graph</span>
          <div className="w-px h-4 bg-border mx-1" />
          <div className="flex items-center gap-1">
            <button
              onClick={() => setSelectedSubject(null)}
              className={`px-2.5 py-1 rounded-md text-xs transition-all ${
                !selectedSubject ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All
            </button>
            {["matematik", "fysik", "datalogi", "kommunikation"].map((s) => (
              <button
                key={s}
                onClick={() => setSelectedSubject(selectedSubject === s ? null : s)}
                className={`px-2.5 py-1 rounded-md text-xs transition-all flex items-center gap-1 ${
                  selectedSubject === s ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span style={{ color: subjectColors[s] }}>{subjectIcons[s]}</span>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={() => setScale((s) => Math.min(s * 1.2, 3))}
              className="p-1.5 rounded-md hover:bg-accent text-muted-foreground"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setScale((s) => Math.max(s * 0.8, 0.3))}
              className="p-1.5 rounded-md hover:bg-accent text-muted-foreground"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => { setScale(1); setOffset({ x: 0, y: 0 }); }}
              className="p-1.5 rounded-md hover:bg-accent text-muted-foreground"
            >
              <Maximize className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div
          className="flex-1 overflow-hidden bg-background cursor-grab active:cursor-grabbing graph-canvas"
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          ref={canvasRef}
        >
          <svg
            width="100%"
            height="100%"
            viewBox={`${-offset.x / scale} ${-offset.y / scale} ${800 / scale} ${600 / scale}`}
            style={{ minWidth: "100%", minHeight: "100%" }}
          >
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="20" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="hsl(var(--muted-foreground))" opacity="0.4" />
              </marker>
              <marker id="arrowhead-active" markerWidth="8" markerHeight="6" refX="20" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="hsl(var(--primary))" opacity="0.8" />
              </marker>
            </defs>

            {/* Edges */}
            {graph.edges.map((edge, i) => {
              const source = nodePositionsRef.current.get(edge.source_id);
              const target = nodePositionsRef.current.get(edge.target_id);
              if (!source || !target) return null;

              const isActive = selectedNode && (edge.source_id === selectedNode || edge.target_id === selectedNode);

              return (
                <line
                  key={`edge-${i}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={isActive ? "hsl(var(--primary))" : edge.cross_subject ? "#d2a8ff" : "hsl(var(--muted-foreground))"}
                  strokeWidth={isActive ? 2 : edge.cross_subject ? 1.5 : 1}
                  strokeDasharray={edge.relation === "applies_to" ? "5,5" : "none"}
                  opacity={isActive ? 0.8 : 0.3}
                  markerEnd={`url(#${isActive ? "arrowhead-active" : "arrowhead"})`}
                />
              );
            })}

            {/* Nodes */}
            {graph.nodes.map((node) => {
              const pos = nodePositionsRef.current.get(node.id);
              if (!pos) return null;

              const color = subjectColors[node.subject] || "#58a6ff";
              const isSelected = selectedNode === node.id;
              const radius = 18 + (node.level === "A" ? 6 : node.level === "B" ? 3 : 0);

              return (
                <g
                  key={node.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedNode(isSelected ? null : node.id);
                  }}
                  className="cursor-pointer"
                >
                  {/* Glow effect for selected */}
                  {isSelected && (
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={radius + 8}
                      fill={color}
                      opacity={0.15}
                    />
                  )}
                  {/* Main circle */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={radius}
                    fill={`${color}20`}
                    stroke={color}
                    strokeWidth={isSelected ? 3 : 2}
                  />
                  {/* Label */}
                  <text
                    x={pos.x}
                    y={pos.y + radius + 16}
                    textAnchor="middle"
                    fill="hsl(var(--foreground))"
                    fontSize="10"
                    fontWeight={isSelected ? 700 : 500}
                  >
                    {node.display_name}
                  </text>
                  {/* Level badge */}
                  <circle
                    cx={pos.x + radius - 4}
                    cy={pos.y - radius + 4}
                    r={7}
                    fill={color}
                  />
                  <text
                    x={pos.x + radius - 4}
                    y={pos.y - radius + 7}
                    textAnchor="middle"
                    fill="white"
                    fontSize="8"
                    fontWeight="bold"
                  >
                    {node.level}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-border bg-card/20 text-xs text-muted-foreground">
          <span>Prerequisite —</span>
          <span className="border-b border-dashed border-muted-foreground">Applies to - -</span>
          <span style={{ color: "#d2a8ff" }}>Cross-subject ···</span>
          <div className="ml-auto flex items-center gap-3">
            {["C", "B", "A"].map((l) => (
              <span key={l} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-primary" style={{ opacity: l === "C" ? 0.5 : l === "B" ? 0.75 : 1 }} />
                {l}-niveau
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Node Detail Panel */}
      {selectedNodeData && (
        <div className="w-80 border-l border-border bg-card/20 overflow-y-auto scrollbar-thin">
          <div className="p-4">
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{
                  backgroundColor: `${subjectColors[selectedNodeData.subject]}18`,
                  color: subjectColors[selectedNodeData.subject],
                }}
              >
                {subjectIcons[selectedNodeData.subject]}
              </div>
              <div>
                <h3 className="text-sm font-semibold">{selectedNodeData.display_name}</h3>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {selectedNodeData.subject}
                  </Badge>
                  <Badge
                    className="text-[10px]"
                    style={{
                      backgroundColor: `${subjectColors[selectedNodeData.subject]}20`,
                      color: subjectColors[selectedNodeData.subject],
                      borderColor: `${subjectColors[selectedNodeData.subject]}40`,
                    }}
                  >
                    {selectedNodeData.level}
                  </Badge>
                </div>
              </div>
            </div>

            <p className="text-xs text-muted-foreground mb-4">
              {selectedNodeData.description}
            </p>

            {/* Prerequisites */}
            {selectedNode && getPrereqsForNode(selectedNode).length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold mb-2 text-muted-foreground uppercase">
                  Prerequisites
                </h4>
                <div className="space-y-1.5">
                  {selectedNode && getPrereqsForNode(selectedNode).map((edge) => {
                    const prereq = graph.nodes.find((n) => n.id === edge.source_id);
                    if (!prereq) return null;
                    return (
                      <div
                        key={edge.source_id}
                        className="flex items-center gap-2 p-2 rounded-md bg-background/50 border border-border/50"
                      >
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: subjectColors[prereq.subject] }}
                        />
                        <span className="text-xs">{prereq.display_name}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Applications */}
            {selectedNode && getApplicationsForNode(selectedNode).length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold mb-2 text-muted-foreground uppercase">
                  Applies To
                </h4>
                <div className="space-y-1.5">
                  {selectedNode && getApplicationsForNode(selectedNode).map((edge) => {
                    const app = graph.nodes.find((n) => n.id === edge.target_id);
                    if (!app) return null;
                    return (
                      <div
                        key={edge.target_id}
                        className="flex items-center gap-2 p-2 rounded-md bg-background/50 border border-border/50"
                      >
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: subjectColors[app.subject] }}
                        />
                        <span className="text-xs">{app.display_name}</span>
                        {edge.cross_subject && (
                          <Badge variant="outline" className="text-[9px] ml-auto">cross</Badge>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Stats */}
            <div className="pt-4 border-t border-border">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-2 rounded-lg bg-background/50">
                  <p className="text-lg font-bold text-primary">
                    {(selectedNodeData.mastery * 100).toFixed(0)}%
                  </p>
                  <p className="text-[10px] text-muted-foreground">Mastery</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-background/50">
                  <p className="text-lg font-bold text-primary">
                    {(selectedNodeData as any).times_taught || 0}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Times Taught</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
