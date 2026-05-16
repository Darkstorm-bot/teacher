import { useState, useEffect } from "react";
import { api, type StudentProfile } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Settings as SettingsIcon,
  User,
  GraduationCap,
  Brain,
  Gauge,
  Languages,
  Server,
  CircleDot,
  Loader2,
  Save,
} from "lucide-react";

export default function Settings() {
  const [student, setStudent] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [studentId] = useState("default");

  useEffect(() => {
    loadData();
  }, [studentId]);

  const loadData = async () => {
    try {
      const [studentData, healthData] = await Promise.all([
        api.getStudent(studentId),
        api.getHealth(),
      ]);
      setStudent(studentData);
      setHealth(healthData);
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!student) return;
    setSaving(true);
    try {
      // In a real implementation, this would call an update endpoint
      await new Promise((r) => setTimeout(r, 500));
    } catch (err) {
      console.error("Failed to save:", err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <SettingsIcon className="w-6 h-6 text-primary" />
          <h1 className="text-2xl font-bold">Settings</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Manage your profile and system configuration
        </p>
      </div>

      <div className="space-y-6">
        {/* Profile Card */}
        <Card className="bg-card/50 border-border">
          <CardHeader className="p-4">
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-primary" />
              <CardTitle className="text-base">Student Profile</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {student ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Name</Label>
                  <Input
                    value={student.name}
                    onChange={(e) => setStudent({ ...student, name: e.target.value })}
                    className="bg-background"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">HF Year</Label>
                  <div className="flex items-center gap-2">
                    <Button
                      variant={student.hf_year === 1 ? "default" : "outline"}
                      size="sm"
                      onClick={() => setStudent({ ...student, hf_year: 1 })}
                    >
                      1st Year
                    </Button>
                    <Button
                      variant={student.hf_year === 2 ? "default" : "outline"}
                      size="sm"
                      onClick={() => setStudent({ ...student, hf_year: 2 })}
                    >
                      2nd Year
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Target Program</Label>
                  <Input
                    value={student.target_program}
                    onChange={(e) => setStudent({ ...student, target_program: e.target.value })}
                    className="bg-background"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Pace</Label>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min="0.5"
                      max="2"
                      step="0.1"
                      value={student.pace}
                      onChange={(e) => setStudent({ ...student, pace: parseFloat(e.target.value) })}
                      className="flex-1"
                    />
                    <span className="text-sm font-mono w-10 text-right">
                      {student.pace.toFixed(1)}x
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No profile found</p>
            )}
            <Button
              onClick={handleSave}
              disabled={saving}
              className="mt-4"
              size="sm"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              ) : (
                <Save className="w-3.5 h-3.5 mr-1.5" />
              )}
              Save Profile
            </Button>
          </CardContent>
        </Card>

        {/* Learning Preferences */}
        <Card className="bg-card/50 border-border">
          <CardHeader className="p-4">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-primary" />
              <CardTitle className="text-base">Learning Preferences</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Gauge className="w-3 h-3" />
                  Modality
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {["visual", "verbal", "kinesthetic", "balanced"].map((m) => (
                    <Badge
                      key={m}
                      variant={student?.preferred_modality === m ? "default" : "outline"}
                      className="cursor-pointer capitalize text-xs"
                      onClick={() => student && setStudent({ ...student, preferred_modality: m })}
                    >
                      {m}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <GraduationCap className="w-3 h-3" />
                  Explanation Depth
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {["intuitive", "balanced", "formal"].map((d) => (
                    <Badge
                      key={d}
                      variant={student?.preferred_depth === d ? "default" : "outline"}
                      className="cursor-pointer capitalize text-xs"
                      onClick={() => student && setStudent({ ...student, preferred_depth: d })}
                    >
                      {d}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Languages className="w-3 h-3" />
                  Language
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {["da", "en"].map((l) => (
                    <Badge
                      key={l}
                      variant={student?.preferred_language === l ? "default" : "outline"}
                      className="cursor-pointer text-xs"
                      onClick={() => student && setStudent({ ...student, preferred_language: l })}
                    >
                      {l === "da" ? "Dansk" : "English"}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        {health && (
          <Card className="bg-card/50 border-border">
            <CardHeader className="p-4">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-primary" />
                <CardTitle className="text-base">System Status</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/50">
                  <CircleDot
                    className={`w-5 h-5 ${
                      health.ollama === "connected" ? "text-emerald-500" : "text-red-500"
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium">Ollama</p>
                    <p className="text-xs text-muted-foreground">{health.ollama}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/50">
                  <DatabaseIcon className="w-5 h-5 text-primary" />
                  <div>
                    <p className="text-sm font-medium">Database</p>
                    <p className="text-xs text-muted-foreground">{health.database}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50 border border-border/50">
                  <Brain className="w-5 h-5 text-primary" />
                  <div>
                    <p className="text-sm font-medium">Model</p>
                    <p className="text-xs text-muted-foreground truncate max-w-[150px]">
                      {health.default_model}
                    </p>
                  </div>
                </div>
              </div>

              {health.available_models && health.available_models.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-muted-foreground mb-2">Available Models</p>
                  <div className="flex flex-wrap gap-1.5">
                    {health.available_models.map((model: string) => (
                      <Badge
                        key={model}
                        variant={model === health.default_model ? "default" : "outline"}
                        className="text-xs"
                      >
                        {model}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-border">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-medium">Agents:</span>
                  {health.agents?.map((agent: string) => (
                    <Badge key={agent} variant="outline" className="text-[10px] capitalize">
                      {agent}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function DatabaseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5V19A9 3 0 0 0 21 19V5" />
      <path d="M3 12A9 3 0 0 0 21 12" />
    </svg>
  );
}
