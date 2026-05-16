const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Agent {
  id: string;
  name: string;
  color: string;
  icon: string;
  philosophy: string;
  levels: string[];
}

export interface ChatMessage {
  id: string;
  type: "user" | "agent" | "system";
  text: string;
  agent_id?: string;
  agent_name?: string;
  agent_color?: string;
  agent_icon?: string;
  topic?: string;
  teaching_state?: string;
  protocol?: string;
  timestamp: Date;
}

export interface MasteryItem {
  concept_id: string;
  subject: string;
  level: string;
  score: number;
  times_practiced: number;
  last_practiced: string;
}

export interface KnowledgeGraph {
  nodes: Array<{
    id: string;
    subject: string;
    level: string;
    display_name: string;
    description: string;
    mastery: number;
  }>;
  edges: Array<{
    source_id: string;
    target_id: string;
    relation: string;
    weight: number;
    cross_subject: boolean;
  }>;
}

export interface StudentProfile {
  id: string;
  name: string;
  hf_year: number;
  pace: number;
  preferred_modality: string;
  preferred_depth: string;
  preferred_language: string;
  target_program: string;
}

export interface DashboardData {
  student: {
    name: string;
    hf_year: number;
    pace: number;
    modality: string;
  };
  stats: Record<string, {
    total_concepts: number;
    avg_score: number;
    mastered: number;
    in_progress: number;
    not_started: number;
  }>;
  mastery: MasteryItem[];
}

class ApiService {
  async getHealth() {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    return res.json();
  }

  async getAgents(): Promise<Agent[]> {
    const res = await fetch(`${API_BASE}/api/v1/agents`);
    return res.json();
  }

  async getAgent(id: string): Promise<Agent> {
    const res = await fetch(`${API_BASE}/api/v1/agents/${id}`);
    return res.json();
  }

  async getStudent(id: string): Promise<StudentProfile> {
    const res = await fetch(`${API_BASE}/api/v1/students/${id}`);
    return res.json();
  }

  async createStudent(data: { name: string; hf_year?: number }): Promise<StudentProfile> {
    const res = await fetch(`${API_BASE}/api/v1/students`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return res.json();
  }

  async getDashboard(studentId: string): Promise<DashboardData> {
    const res = await fetch(`${API_BASE}/api/v1/students/${studentId}/progress`);
    return res.json();
  }

  async getMastery(studentId: string, subject?: string): Promise<MasteryItem[]> {
    const url = new URL(`${API_BASE}/api/v1/students/${studentId}/mastery`);
    if (subject) url.searchParams.set("subject", subject);
    const res = await fetch(url.toString());
    return res.json();
  }

  async getKnowledgeGraph(subject?: string): Promise<KnowledgeGraph> {
    const url = new URL(`${API_BASE}/api/v1/knowledge-graph`);
    if (subject) url.searchParams.set("subject", subject);
    const res = await fetch(url.toString());
    return res.json();
  }

  async getCurriculum(subject: string, level?: string) {
    const url = new URL(`${API_BASE}/api/v1/curriculum/${subject}`);
    if (level) url.searchParams.set("level", level);
    const res = await fetch(url.toString());
    return res.json();
  }

  async getAllTopics() {
    const res = await fetch(`${API_BASE}/api/v1/curriculum/topics/all`);
    return res.json();
  }

  async getMemoryWings() {
    const res = await fetch(`${API_BASE}/api/v1/memory/wings`);
    return res.json();
  }

  async searchMemory(query: string, wing?: string, agent?: string, topic?: string) {
    const url = new URL(`${API_BASE}/api/v1/memory/search`);
    url.searchParams.set("query", query);
    if (wing) url.searchParams.set("wing", wing);
    if (agent) url.searchParams.set("agent", agent);
    if (topic) url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    return res.json();
  }

  async checkProgression(studentId: string, subject: string, currentLevel: string = "C") {
    const res = await fetch(
      `${API_BASE}/api/v1/students/${studentId}/progression/${subject}?current_level=${currentLevel}`
    );
    return res.json();
  }
}

export const api = new ApiService();

export class WebSocketService {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private studentId: string = "default";
  private messageHandlers: ((msg: any) => void)[] = [];
  private statusHandlers: ((connected: boolean) => void)[] = [];

  connect(sessionId?: string, studentId: string = "default") {
    this.studentId = studentId;
    const wsUrl = API_BASE.replace("http", "ws");
    this.ws = new WebSocket(`${wsUrl}/ws/chat`);

    this.ws.onopen = () => {
      const sid = sessionId || `sess_${Math.random().toString(36).slice(2, 10)}`;
      this.sessionId = sid;
      this.send({
        type: "init",
        session_id: sid,
        student_id: studentId,
      });
      this.statusHandlers.forEach((h) => h(true));
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.messageHandlers.forEach((h) => h(data));
    };

    this.ws.onclose = () => {
      this.statusHandlers.forEach((h) => h(false));
    };

    this.ws.onerror = () => {
      this.statusHandlers.forEach((h) => h(false));
    };
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendMessage(text: string, targetAgent?: string) {
    this.send({
      type: "message",
      session_id: this.sessionId,
      student_id: this.studentId,
      text,
      target_agent: targetAgent,
    });
  }

  onMessage(handler: (msg: any) => void) {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  onStatusChange(handler: (connected: boolean) => void) {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }

  getSessionId() {
    return this.sessionId;
  }
}

export const wsService = new WebSocketService();
