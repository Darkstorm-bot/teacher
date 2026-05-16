import { useState, useEffect, useRef, useCallback } from "react";
import { api, wsService, type Agent, type ChatMessage } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Send,
  Bot,
  User,
  Loader2,
  Sparkles,
  BookOpen,
  Atom,
  Monitor,
  PenTool,
  CircleDot,
  Zap,
} from "lucide-react";

const agentIcons: Record<string, React.ReactNode> = {
  matematik: <BookOpen className="w-4 h-4" />,
  fysik: <Atom className="w-4 h-4" />,
  datalogi: <Monitor className="w-4 h-4" />,
  kommunikation: <PenTool className="w-4 h-4" />,
};

const agentColors: Record<string, string> = {
  matematik: "#58a6ff",
  fysik: "#3fb950",
  datalogi: "#d2a8ff",
  kommunikation: "#f0883e",
};

const protocolIcons: Record<string, string> = {
  DIRECT_TUTORING: "1-on-1",
  PANEL_DISCUSSION: "Panel",
  SCAFFOLDING_HANDOFF: "Scaffold",
  PEER_REVIEW: "Review",
};

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | undefined>();
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load agents
  useEffect(() => {
    api.getAgents().then(setAgents).catch(console.error);
  }, []);

  // Setup WebSocket
  useEffect(() => {
    wsService.connect(undefined, "default");

    const unsubMsg = wsService.onMessage((msg) => {
      switch (msg.type) {
        case "connected":
          setIsConnected(true);
          break;

        case "agent_start":
          setIsStreaming(true);
          setCurrentAgent(msg.agent_id);
          setShowWelcome(false);
          break;

        case "token":
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.type === "agent" && last.agent_id === msg.agent_id && !last.id.endsWith("_done")) {
              const updated = [...prev.slice(0, -1), {
                ...last,
                text: last.text + msg.text,
              }];
              return updated;
            }
            return [...prev, {
              id: `msg_${Date.now()}`,
              type: "agent",
              text: msg.text,
              agent_id: msg.agent_id,
              agent_name: msg.agent_name,
              agent_color: msg.color || agentColors[msg.agent_id],
              agent_icon: msg.icon,
              timestamp: new Date(),
            }];
          });
          break;

        case "agent_end":
          setIsStreaming(false);
          setCurrentAgent(null);
          break;

        case "error":
          setIsStreaming(false);
          setMessages((prev) => [...prev, {
            id: `err_${Date.now()}`,
            type: "system",
            text: `Error: ${msg.message}`,
            timestamp: new Date(),
          }]);
          break;
      }
    });

    const unsubStatus = wsService.onStatusChange((connected) => {
      setIsConnected(connected);
    });

    return () => {
      unsubMsg();
      unsubStatus();
      wsService.disconnect();
    };
  }, []);

  const handleSend = () => {
    if (!inputText.trim() || isStreaming) return;

    const text = inputText.trim();
    setInputText("");
    setShowWelcome(false);

    // Add user message
    setMessages((prev) => [...prev, {
      id: `user_${Date.now()}`,
      type: "user",
      text,
      timestamp: new Date(),
    }]);

    // Send via WebSocket
    wsService.sendMessage(text, selectedAgent);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickPrompts = [
    "Forklar mig differentialregning",
    "Hvad er Newtons love?",
    "Hvordan skriver jeg en Python-funktion?",
    "Analyser denne reklame",
  ];

  return (
    <div className="flex h-full">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Agent Selector */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-card/30">
          <div className="flex items-center gap-1.5">
            <CircleDot className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-xs text-muted-foreground">Auto-routing</span>
          </div>
          <div className="w-px h-4 bg-border mx-2" />
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => setSelectedAgent(undefined)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all
                ${!selectedAgent
                  ? "bg-primary/15 text-primary ring-1 ring-primary/30"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
            >
              <Sparkles className="w-3 h-3" />
              Auto
            </button>
            {agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(selectedAgent === agent.id ? undefined : agent.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all
                  ${selectedAgent === agent.id
                    ? "ring-1"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                  }`}
                style={selectedAgent === agent.id ? {
                  backgroundColor: `${agent.color}18`,
                  color: agent.color,
                  borderColor: `${agent.color}40`,
                } : {}}
              >
                <span style={{ color: selectedAgent === agent.id ? agent.color : undefined }}>
                  {agentIcons[agent.id] || <Bot className="w-3 h-3" />}
                </span>
                {agent.name.split("-")[0]}
              </button>
            ))}
          </div>
          {isStreaming && (
            <div className="ml-auto flex items-center gap-2 text-xs text-primary">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-4 space-y-4">
          {showWelcome && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-5">
                <Bot className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-xl font-bold mb-2">Velkommen til HF-Agent</h2>
              <p className="text-sm text-muted-foreground max-w-md mb-8">
                Din multi-agent tutor for den danske HF-læreplan. Spørg om matematik, fysik,
                datalogi eller kommunikation — systemet vælger automatisk den rette ekspert.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {quickPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputText(prompt);
                      inputRef.current?.focus();
                    }}
                    className="text-left px-4 py-3 rounded-lg border border-border bg-card/50
                      hover:bg-accent hover:border-primary/30 transition-all text-sm"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 animate-fade-in ${
                msg.type === "user" ? "flex-row-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
                  ${msg.type === "user"
                    ? "bg-secondary"
                    : msg.type === "system"
                    ? "bg-destructive/10"
                    : "bg-agent-" + msg.agent_id
                  }`}
                style={msg.type === "agent" && msg.agent_color ? {
                  backgroundColor: `${msg.agent_color}18`,
                } : {}}
              >
                {msg.type === "user" ? (
                  <User className="w-4 h-4 text-muted-foreground" />
                ) : msg.type === "system" ? (
                  <Zap className="w-4 h-4 text-destructive" />
                ) : (
                  <span style={{ color: msg.agent_color }}>
                    {agentIcons[msg.agent_id || ""] || <Bot className="w-4 h-4" />}
                  </span>
                )}
              </div>

              {/* Message bubble */}
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3
                  ${msg.type === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : msg.type === "system"
                    ? "bg-destructive/10 text-destructive border border-destructive/20"
                    : "bg-card border border-border rounded-tl-sm"
                  }`}
              >
                {msg.type === "agent" && msg.agent_name && (
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className="text-xs font-semibold"
                      style={{ color: msg.agent_color }}
                    >
                      {msg.agent_name}
                    </span>
                    {msg.protocol && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                        {protocolIcons[msg.protocol] || msg.protocol}
                      </span>
                    )}
                  </div>
                )}
                <div className={`text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.type === "user" ? "" : "text-foreground"
                }`}>
                  {msg.text}
                </div>
                {msg.topic && msg.type === "agent" && (
                  <div className="mt-2 pt-2 border-t border-border/50 flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground">
                      Topic: {msg.topic}
                    </span>
                    {msg.teaching_state && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">
                        {msg.teaching_state}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isStreaming && currentAgent && (
            <div className="flex gap-3 animate-fade-in">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center animate-pulse"
                style={{
                  backgroundColor: `${agentColors[currentAgent]}18`,
                }}
              >
                <Loader2
                  className="w-4 h-4 animate-spin"
                  style={{ color: agentColors[currentAgent] }}
                />
              </div>
              <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                <span className="text-xs text-muted-foreground">
                  {agents.find((a) => a.id === currentAgent)?.name || currentAgent} is thinking...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-border px-4 py-4 bg-card/30">
          <div className="flex items-center gap-3 max-w-4xl mx-auto">
            <Input
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Spørg om matematik, fysik, datalogi eller kommunikation..."
              className="flex-1 bg-card border-border focus-visible:ring-primary"
              disabled={isStreaming}
            />
            <Button
              onClick={handleSend}
              disabled={!inputText.trim() || isStreaming}
              size="icon"
              className="shrink-0 bg-primary hover:bg-primary/90"
            >
              {isStreaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
          {!isConnected && (
            <p className="text-center text-xs text-destructive mt-2">
              WebSocket disconnected. Reconnecting...
            </p>
          )}
        </div>
      </div>

      {/* Right Sidebar - Agent Info */}
      <div className="hidden xl:block w-72 border-l border-border bg-card/20 overflow-y-auto scrollbar-thin">
        <div className="p-4">
          <h3 className="text-sm font-semibold mb-3">Active Agents</h3>
          <div className="space-y-2">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className={`p-3 rounded-lg border transition-all cursor-pointer
                  ${currentAgent === agent.id
                    ? "ring-1"
                    : "border-border hover:border-primary/30"
                  }`}
                style={currentAgent === agent.id ? {
                  borderColor: `${agent.color}40`,
                  backgroundColor: `${agent.color}08`,
                } : {}}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <div
                    className="w-7 h-7 rounded-md flex items-center justify-center"
                    style={{ backgroundColor: `${agent.color}18` }}
                  >
                    <span style={{ color: agent.color }}>
                      {agentIcons[agent.id] || <Bot className="w-3.5 h-3.5" />}
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-semibold">{agent.name}</p>
                    <p className="text-[10px] text-muted-foreground capitalize">
                      {agent.philosophy.replace(/_/g, " ")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-wrap">
                  {agent.levels.map((level) => (
                    <span
                      key={level}
                      className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground"
                    >
                      {level}-niveau
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <h3 className="text-sm font-semibold mt-6 mb-3">Protocol</h3>
          <div className="space-y-1.5">
            {Object.entries(protocolIcons).map(([key, label]) => (
              <div key={key} className="flex items-center gap-2 text-xs text-muted-foreground">
                <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
                <span>{label}</span>
                <span className="text-[10px] opacity-50">{key}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
