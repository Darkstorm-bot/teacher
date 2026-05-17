import { useState, useEffect, useRef, useCallback } from "react";
import { api, wsService, type Agent, type ChatMessage } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Send, Bot, User, Loader2, Sparkles, BookOpen, Atom, Monitor, PenTool,
  CircleDot, Zap, Copy, Check,
} from "lucide-react";

// ── Agent config ──────────────────────────────────────────────────────────────

const agentIcons: Record<string, React.ReactNode> = {
  matematik:     <BookOpen className="w-4 h-4" />,
  fysik:         <Atom     className="w-4 h-4" />,
  datalogi:      <Monitor  className="w-4 h-4" />,
  kommunikation: <PenTool  className="w-4 h-4" />,
};

const agentColors: Record<string, string> = {
  matematik:     "#58a6ff",
  fysik:         "#3fb950",
  datalogi:      "#d2a8ff",
  kommunikation: "#f0883e",
};

const protocolLabels: Record<string, string> = {
  DIRECT_TUTORING:    "1-on-1",
  PANEL_DISCUSSION:   "Panel",
  SCAFFOLDING_HANDOFF:"Scaffold",
  PEER_REVIEW:        "Review",
};

// ── Minimal inline markdown renderer ─────────────────────────────────────────
// Supports: **bold**, *italic*, `code`, ```block```, # headers, - lists, numbered lists
// Renders as JSX without an external library.

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      nodes.push(
        <pre key={`cb-${i}`} className="my-2 overflow-x-auto rounded-lg bg-[#0d1117] border border-border/60 p-3 text-xs font-mono leading-relaxed">
          {lang && <span className="block text-[10px] text-muted-foreground mb-1">{lang}</span>}
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    // Header
    const hMatch = line.match(/^(#{1,4})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const cls = [
        "text-base font-bold mt-3 mb-1",
        "text-sm font-semibold mt-2 mb-1",
        "text-xs font-semibold mt-1.5 mb-0.5 text-muted-foreground uppercase tracking-wide",
        "text-xs font-medium mt-1",
      ][level - 1] || "text-xs font-medium";
      nodes.push(<div key={`h-${i}`} className={cls}>{inlineMarkdown(hMatch[2])}</div>);
      i++;
      continue;
    }

    // Unordered list item
    if (/^[-*+]\s/.test(line)) {
      const items: React.ReactNode[] = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
        items.push(
          <li key={i} className="flex gap-2 items-start text-sm leading-relaxed">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
            <span>{inlineMarkdown(lines[i].slice(2))}</span>
          </li>
        );
        i++;
      }
      nodes.push(<ul key={`ul-${i}`} className="my-1.5 space-y-1">{items}</ul>);
      continue;
    }

    // Numbered list item
    if (/^\d+\.\s/.test(line)) {
      const items: React.ReactNode[] = [];
      let num = 1;
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(
          <li key={i} className="flex gap-2 items-start text-sm leading-relaxed">
            <span className="shrink-0 text-primary font-mono text-xs mt-0.5">{num}.</span>
            <span>{inlineMarkdown(lines[i].replace(/^\d+\.\s/, ""))}</span>
          </li>
        );
        i++;
        num++;
      }
      nodes.push(<ol key={`ol-${i}`} className="my-1.5 space-y-1">{items}</ol>);
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      nodes.push(<hr key={`hr-${i}`} className="my-2 border-border/50" />);
      i++;
      continue;
    }

    // Blank line → paragraph break
    if (line.trim() === "") {
      nodes.push(<div key={`br-${i}`} className="h-2" />);
      i++;
      continue;
    }

    // Regular paragraph line
    nodes.push(
      <p key={`p-${i}`} className="text-sm leading-relaxed">
        {inlineMarkdown(line)}
      </p>
    );
    i++;
  }

  return nodes;
}

function inlineMarkdown(text: string): React.ReactNode {
  // Split on **bold**, *italic*, `code` spans
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={idx} className="font-semibold">{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={idx} className="italic">{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`"))
      return (
        <code key={idx} className="px-1 py-0.5 rounded bg-[#0d1117] border border-border/60 font-mono text-xs text-emerald-400">
          {part.slice(1, -1)}
        </code>
      );
    return part;
  });
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <button
      onClick={copy}
      title="Copy message"
      className="p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

// ── Chat page ─────────────────────────────────────────────────────────────────

export default function Chat() {
  const [messages, setMessages]         = useState<ChatMessage[]>([]);
  const [inputText, setInputText]       = useState("");
  const [agents, setAgents]             = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | undefined>();
  const [isConnected, setIsConnected]   = useState(false);
  const [isStreaming, setIsStreaming]   = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [showWelcome, setShowWelcome]   = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    api.getAgents().then(setAgents).catch(console.error);
  }, []);

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
            if (
              last &&
              last.type === "agent" &&
              last.agent_id === msg.agent_id &&
              !last.id.endsWith("_done")
            ) {
              return [
                ...prev.slice(0, -1),
                { ...last, text: last.text + msg.text },
              ];
            }
            return [
              ...prev,
              {
                id: `msg_${Date.now()}`,
                type: "agent",
                text: msg.text,
                agent_id:    msg.agent_id,
                agent_name:  msg.agent_name,
                agent_color: msg.color || agentColors[msg.agent_id],
                agent_icon:  msg.icon,
                timestamp:   new Date(),
              },
            ];
          });
          break;

        case "agent_end":
          setIsStreaming(false);
          setCurrentAgent(null);
          // Stamp the final message with topic / teaching_state
          if (msg.topic_detected || msg.teaching_state) {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (!last || last.type !== "agent") return prev;
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  topic:          msg.topic_detected,
                  teaching_state: msg.teaching_state,
                  id: last.id + "_done",
                },
              ];
            });
          }
          break;

        case "error":
          setIsStreaming(false);
          setMessages((prev) => [
            ...prev,
            {
              id: `err_${Date.now()}`,
              type: "system",
              text: `Fejl: ${msg.message}`,
              timestamp: new Date(),
            },
          ]);
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
    setMessages((prev) => [
      ...prev,
      { id: `user_${Date.now()}`, type: "user", text, timestamp: new Date() },
    ]);
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
    "Skriv en Python-funktion der finder primtal",
    "Analyser retoriske virkemidler i en reklame",
  ];

  return (
    <div className="flex h-full">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Agent Selector Bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-card/30 flex-wrap">
          <div className="flex items-center gap-1.5">
            <CircleDot className={`w-3.5 h-3.5 ${isConnected ? "text-emerald-500" : "text-red-500 animate-pulse"}`} />
            <span className="text-xs text-muted-foreground">
              {isConnected ? "Auto-routing" : "Reconnecting…"}
            </span>
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
                  ${selectedAgent === agent.id ? "ring-1" : "text-muted-foreground hover:text-foreground hover:bg-accent"}`}
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
              <span>Tænker…</span>
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
                    onClick={() => { setInputText(prompt); inputRef.current?.focus(); }}
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
              className={`flex gap-3 animate-fade-in group ${msg.type === "user" ? "flex-row-reverse" : ""}`}
            >
              {/* Avatar */}
              <div
                className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
                style={msg.type === "agent" && msg.agent_color
                  ? { backgroundColor: `${msg.agent_color}18` }
                  : {}}
              >
                {msg.type === "user"   ? <User className="w-4 h-4 text-muted-foreground" /> :
                 msg.type === "system" ? <Zap  className="w-4 h-4 text-destructive" /> :
                 <span style={{ color: msg.agent_color }}>
                   {agentIcons[msg.agent_id || ""] || <Bot className="w-4 h-4" />}
                 </span>}
              </div>

              {/* Bubble */}
              <div className="flex flex-col gap-1 max-w-[85%] sm:max-w-[78%]">
                <div
                  className={`rounded-2xl px-4 py-3
                    ${msg.type === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-sm"
                      : msg.type === "system"
                      ? "bg-destructive/10 text-destructive border border-destructive/20"
                      : "bg-card border border-border rounded-tl-sm"
                    }`}
                >
                  {msg.type === "agent" && msg.agent_name && (
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-semibold" style={{ color: msg.agent_color }}>
                        {msg.agent_name}
                      </span>
                      {msg.protocol && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                          {protocolLabels[msg.protocol] || msg.protocol}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Content — markdown for agent, plain for user */}
                  {msg.type === "agent" ? (
                    <div className="text-foreground space-y-0.5">
                      {renderMarkdown(msg.text)}
                    </div>
                  ) : (
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</div>
                  )}

                  {/* Topic / state footer */}
                  {msg.topic && msg.type === "agent" && (
                    <div className="mt-2 pt-2 border-t border-border/50 flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] text-muted-foreground">
                        Emne: {msg.topic.replace(/_/g, " ")}
                      </span>
                      {msg.teaching_state && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">
                          {msg.teaching_state}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Copy button — under bubble, only on agent messages */}
                {msg.type === "agent" && (
                  <div className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"} px-1`}>
                    <CopyButton text={msg.text} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isStreaming && currentAgent && (
            <div className="flex gap-3 animate-fade-in">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center animate-pulse"
                style={{ backgroundColor: `${agentColors[currentAgent]}18` }}
              >
                <Loader2 className="w-4 h-4 animate-spin" style={{ color: agentColors[currentAgent] }} />
              </div>
              <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                <span className="text-xs font-medium" style={{ color: agentColors[currentAgent] }}>
                  {agents.find((a) => a.id === currentAgent)?.name || currentAgent}
                </span>
                <span className="text-xs text-muted-foreground">tænker…</span>
                <span className="flex gap-0.5">
                  {[0, 1, 2].map((d) => (
                    <span
                      key={d}
                      className="w-1 h-1 rounded-full bg-muted-foreground animate-bounce"
                      style={{ animationDelay: `${d * 0.15}s` }}
                    />
                  ))}
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-border px-4 py-4 bg-card/30">
          <div className="flex items-center gap-3 max-w-4xl mx-auto">
            <Input
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Spørg om matematik, fysik, datalogi eller kommunikation…"
              className="flex-1 bg-card border-border focus-visible:ring-primary"
              disabled={isStreaming}
            />
            <Button
              onClick={handleSend}
              disabled={!inputText.trim() || isStreaming}
              size="icon"
              className="shrink-0 bg-primary hover:bg-primary/90"
            >
              {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
          {!isConnected && (
            <p className="text-center text-xs text-amber-500 mt-2">
              WebSocket genforbinder… (beskeder gemmes)
            </p>
          )}
        </div>
      </div>

      {/* Right Sidebar */}
      <div className="hidden xl:block w-72 border-l border-border bg-card/20 overflow-y-auto scrollbar-thin">
        <div className="p-4">
          <h3 className="text-sm font-semibold mb-3">Aktive agenter</h3>
          <div className="space-y-2">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className={`p-3 rounded-lg border transition-all cursor-pointer
                  ${currentAgent === agent.id ? "ring-1" : "border-border hover:border-primary/30"}`}
                style={currentAgent === agent.id ? {
                  borderColor: `${agent.color}40`,
                  backgroundColor: `${agent.color}08`,
                } : {}}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <div className="w-7 h-7 rounded-md flex items-center justify-center"
                       style={{ backgroundColor: `${agent.color}18` }}>
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
                  {currentAgent === agent.id && (
                    <span className="ml-auto w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  )}
                </div>
                <div className="flex items-center gap-1 flex-wrap">
                  {agent.levels.map((level) => (
                    <span key={level}
                          className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                      {level}-niveau
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <h3 className="text-sm font-semibold mt-6 mb-3">Protokoller</h3>
          <div className="space-y-1.5">
            {Object.entries(protocolLabels).map(([key, label]) => (
              <div key={key} className="flex items-center gap-2 text-xs text-muted-foreground">
                <div className="w-1.5 h-1.5 rounded-full bg-primary/50" />
                <span>{label}</span>
                <span className="text-[10px] opacity-50 ml-auto">{key}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
