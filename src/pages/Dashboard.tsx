import { useState, useEffect } from "react";
import { api, type DashboardData, type MasteryItem } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  BookOpen,
  Atom,
  Monitor,
  PenTool,
  TrendingUp,
  Award,
  Target,
  Clock,
  BarChart3,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const subjectIcons: Record<string, React.ReactNode> = {
  matematik: <BookOpen className="w-5 h-5" />,
  fysik: <Atom className="w-5 h-5" />,
  datalogi: <Monitor className="w-5 h-5" />,
  kommunikation: <PenTool className="w-5 h-5" />,
};

const subjectColors: Record<string, string> = {
  matematik: "#58a6ff",
  fysik: "#3fb950",
  datalogi: "#d2a8ff",
  kommunikation: "#f0883e",
};

const subjectLabels: Record<string, string> = {
  matematik: "Matematik",
  fysik: "Fysik",
  datalogi: "Datalogi",
  kommunikation: "Kommunikation",
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSubject, setExpandedSubject] = useState<string | null>(null);
  const [studentId] = useState("default");

  useEffect(() => {
    loadDashboard();
  }, [studentId]);

  const loadDashboard = async () => {
    try {
      const dashboard = await api.getDashboard(studentId);
      setData(dashboard);
    } catch (err) {
      console.error("Failed to load dashboard:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2 text-muted-foreground">
          <BarChart3 className="w-5 h-5 animate-pulse" />
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No dashboard data available
      </div>
    );
  }

  const { student, stats, mastery } = data;
  const subjects = Object.keys(stats);

  const getMasteryColor = (score: number) => {
    if (score >= 0.75) return "bg-emerald-500";
    if (score >= 0.5) return "bg-amber-500";
    if (score >= 0.3) return "bg-orange-500";
    return "bg-red-500";
  };

  const getMasteryLabel = (score: number) => {
    if (score >= 0.75) return "Mastered";
    if (score >= 0.5) return "Progressing";
    if (score >= 0.3) return "Started";
    return "Needs Work";
  };

  const totalMastered = Object.values(stats).reduce((sum, s) => sum + s.mastered, 0);
  const totalConcepts = Object.values(stats).reduce((sum, s) => sum + s.total_concepts, 0);
  const overallProgress = totalConcepts > 0 ? (totalMastered / totalConcepts) * 100 : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Learning Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Track your progress across the Danish HF curriculum
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card className="bg-card/50 border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{overallProgress.toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground">Overall Progress</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <Award className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalMastered}</p>
                <p className="text-xs text-muted-foreground">Concepts Mastered</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Target className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalConcepts - totalMastered}</p>
                <p className="text-xs text-muted-foreground">In Progress</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Clock className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">HF {student.hf_year}</p>
                <p className="text-xs text-muted-foreground">Current Year</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Subject Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {subjects.map((subject) => {
          const stat = stats[subject];
          const color = subjectColors[subject] || "#58a6ff";
          const isExpanded = expandedSubject === subject;
          const subjectMastery = mastery.filter((m) => m.subject === subject);

          return (
            <Card
              key={subject}
              className="bg-card/50 border-border overflow-hidden transition-all hover:border-primary/30"
            >
              <CardHeader className="p-4 pb-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${color}18`, color }}
                    >
                      {subjectIcons[subject] || <BookOpen className="w-5 h-5" />}
                    </div>
                    <div>
                      <CardTitle className="text-base font-semibold">
                        {subjectLabels[subject] || subject}
                      </CardTitle>
                      <p className="text-xs text-muted-foreground">
                        {stat.total_concepts} concepts · {stat.mastered} mastered
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold" style={{ color }}>
                      {(stat.avg_score * 100).toFixed(0)}%
                    </p>
                    <p className="text-[10px] text-muted-foreground">avg mastery</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4">
                {/* Progress bar */}
                <div className="mb-3">
                  <Progress
                    value={stat.avg_score * 100}
                    className="h-2"
                  />
                </div>

                {/* Mini stats */}
                <div className="flex items-center gap-4 mb-3">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span className="text-xs text-muted-foreground">{stat.mastered} done</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-amber-500" />
                    <span className="text-xs text-muted-foreground">{stat.in_progress} active</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-red-500/50" />
                    <span className="text-xs text-muted-foreground">{stat.not_started} pending</span>
                  </div>
                </div>

                {/* Expandable concept list */}
                {subjectMastery.length > 0 && (
                  <div>
                    <button
                      onClick={() => setExpandedSubject(isExpanded ? null : subject)}
                      className="flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      {isExpanded ? "Hide" : "Show"} {subjectMastery.length} concepts
                    </button>

                    {isExpanded && (
                      <div className="mt-3 space-y-2 animate-fade-in">
                        {subjectMastery.map((item: MasteryItem) => (
                          <div
                            key={item.concept_id}
                            className="flex items-center gap-3 p-2.5 rounded-lg bg-background/50 border border-border/50"
                          >
                            <div className={`w-2 h-2 rounded-full ${getMasteryColor(item.score)}`} />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium truncate">
                                {item.concept_id.replace(/_/g, " ")}
                              </p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <Progress value={item.score * 100} className="h-1 w-24" />
                                <span className="text-[10px] text-muted-foreground">
                                  {(item.score * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                            <Badge
                              variant="outline"
                              className="text-[10px] shrink-0"
                            >
                              {item.level}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground shrink-0">
                              {getMasteryLabel(item.score)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent Activity */}
      {mastery.length > 0 && (
        <Card className="bg-card/50 border-border">
          <CardHeader className="p-4">
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {mastery
                .filter((m) => m.times_practiced > 0)
                .sort((a, b) => (b.last_practiced || "").localeCompare(a.last_practiced || ""))
                .slice(0, 10)
                .map((item) => (
                  <div
                    key={item.concept_id}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent/50 transition-colors"
                  >
                    <div
                      className="w-8 h-8 rounded-md flex items-center justify-center"
                      style={{
                        backgroundColor: `${subjectColors[item.subject] || "#58a6ff"}18`,
                        color: subjectColors[item.subject] || "#58a6ff",
                      }}
                    >
                      {subjectIcons[item.subject] || <BookOpen className="w-4 h-4" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {item.concept_id.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {subjectLabels[item.subject] || item.subject} · Level {item.level}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">{(item.score * 100).toFixed(0)}%</p>
                      <p className="text-[10px] text-muted-foreground">
                        {item.times_practiced} sessions
                      </p>
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
