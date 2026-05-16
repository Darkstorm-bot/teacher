import { useState, useEffect } from "react";
import { api } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BookOpen,
  Atom,
  Monitor,
  PenTool,
  Loader2,
  GraduationCap,
  Target,
  ListChecks,
} from "lucide-react";

const subjectConfig = {
  matematik: {
    label: "Matematik",
    color: "#58a6ff",
    icon: <BookOpen className="w-5 h-5" />,
    description: "Fra funktioner og statistik til differentialregning og bevisførelse.",
  },
  fysik: {
    label: "Fysik",
    color: "#3fb950",
    icon: <Atom className="w-5 h-5" />,
    description: "Mekanik, energi, bølger, termodynamik og atomfysik.",
  },
  datalogi: {
    label: "Datalogi",
    color: "#d2a8ff",
    icon: <Monitor className="w-5 h-5" />,
    description: "Python-programmering, algoritmer, datastrukturer og IT-sikkerhed.",
  },
  kommunikation: {
    label: "Kommunikation",
    color: "#f0883e",
    icon: <PenTool className="w-5 h-5" />,
    description: "Medieanalyse, retorik, argumentation og skriftlig fremstilling.",
  },
};

export default function Curriculum() {
  const [topics, setTopics] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [activeSubject, setActiveSubject] = useState("matematik");
  const [curriculumData, setCurriculumData] = useState<any[]>([]);
  const [activeLevel, setActiveLevel] = useState<string>("all");

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeSubject) {
      loadCurriculum(activeSubject);
    }
  }, [activeSubject, activeLevel]);

  const loadData = async () => {
    try {
      const allTopics = await api.getAllTopics();
      setTopics(allTopics);
    } catch (err) {
      console.error("Failed to load topics:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadCurriculum = async (subject: string) => {
    try {
      const level = activeLevel === "all" ? undefined : activeLevel;
      const data = await api.getCurriculum(subject, level);
      setCurriculumData(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load curriculum:", err);
      setCurriculumData([]);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const config = subjectConfig[activeSubject as keyof typeof subjectConfig];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <GraduationCap className="w-6 h-6 text-primary" />
          <h1 className="text-2xl font-bold">HF Curriculum</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Danish HF (Højere Forberedelseseksamen) curriculum overview
        </p>
      </div>

      {/* Subject Selector */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        {Object.entries(subjectConfig).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setActiveSubject(key)}
            className={`p-4 rounded-xl border text-left transition-all ${
              activeSubject === key
                ? "ring-1"
                : "border-border hover:border-primary/30 hover:bg-card/80"
            }`}
            style={activeSubject === key ? {
              borderColor: `${cfg.color}40`,
              backgroundColor: `${cfg.color}08`,
            } : {}}
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
              style={{ backgroundColor: `${cfg.color}18`, color: cfg.color }}
            >
              {cfg.icon}
            </div>
            <h3 className="text-sm font-semibold mb-1">{cfg.label}</h3>
            <p className="text-xs text-muted-foreground line-clamp-2">{cfg.description}</p>
          </button>
        ))}
      </div>

      {/* Active Subject Detail */}
      {config && (
        <Card className="bg-card/50 border-border mb-6">
          <CardHeader className="p-4">
            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ backgroundColor: `${config.color}18`, color: config.color }}
              >
                {config.icon}
              </div>
              <div>
                <CardTitle className="text-lg">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Level Filter */}
      <div className="flex items-center gap-2 mb-6">
        <Target className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground mr-2">Level:</span>
        {["all", "C", "B", "A"].map((level) => (
          <button
            key={level}
            onClick={() => setActiveLevel(level)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeLevel === level
                ? "bg-primary/15 text-primary ring-1 ring-primary/30"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {level === "all" ? "All Levels" : `${level}-niveau`}
          </button>
        ))}
      </div>

      {/* Curriculum Content */}
      <div className="space-y-4">
        {curriculumData.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <ListChecks className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No curriculum data available for this subject/level.</p>
          </div>
        )}

        {curriculumData.map((item: any, i: number) => {
          const content = item.content || "";
          const lines = content.split("\n").filter((l: string) => l.trim());
          const title = lines[0]?.replace("# ", "") || item.topic || "Untitled";
          const objectives = lines
            .filter((l: string) => l.startsWith("- ") && !l.includes("Forudsætninger"))
            .map((l: string) => l.replace("- ", ""));
          const prereqs = lines
            .filter((l: string) => l.startsWith("- ") && content.indexOf(l) > content.indexOf("Forudsætninger"))
            .map((l: string) => l.replace("- ", ""));

          return (
            <Card
              key={i}
              className="bg-card/50 border-border overflow-hidden hover:border-primary/30 transition-all"
              style={{ borderLeftWidth: 3, borderLeftColor: config?.color }}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold">{title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge
                        variant="outline"
                        className="text-[10px]"
                        style={{
                          borderColor: `${config?.color}40`,
                          color: config?.color,
                        }}
                      >
                        {item.difficulty_level || "?"}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">
                        {item.agent_id || activeSubject}
                      </span>
                    </div>
                  </div>
                </div>

                {objectives.length > 0 && (
                  <div className="mb-3">
                    <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5">
                      Learning Objectives
                    </h4>
                    <ul className="space-y-1">
                      {objectives.slice(0, 6).map((obj: string, j: number) => (
                        <li key={j} className="flex items-start gap-2 text-xs">
                          <ListChecks className="w-3 h-3 mt-0.5 text-primary shrink-0" />
                          <span>{obj}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {prereqs.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5">
                      Prerequisites
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {prereqs.map((p: string, j: number) => (
                        <Badge key={j} variant="secondary" className="text-[10px]">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Topics Summary */}
      {topics[activeSubject] && topics[activeSubject].length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold mb-3">All Topics</h2>
          <div className="flex flex-wrap gap-2">
            {topics[activeSubject].map((topic: string) => (
              <Badge
                key={topic}
                variant="outline"
                className="text-xs px-2.5 py-1 cursor-pointer hover:bg-primary/10 hover:border-primary/30 transition-all"
                style={{ borderColor: `${config?.color}30` }}
              >
                {topic.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
